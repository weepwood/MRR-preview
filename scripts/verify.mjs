import assert from 'node:assert/strict'
import { chromium } from '@playwright/test'
import { preview } from 'vite'

const version = process.env.PREVIEW_VERSION
const sha = process.env.MRR_GIT_COMMIT
const base = process.env.PREVIEW_BASE
assert.ok(['v1.1', 'v1.2'].includes(version))
assert.equal(base, '/MRR-preview/' + version + '/')
const live = process.env.PREVIEW_LIVE === 'true'
const app = live ? 'https://weepwood.github.io' + base : 'http://127.0.0.1:4178' + base
const server = live ? null : await preview({ mode: 'pages', base, preview: { host: '127.0.0.1', port: 4178, strictPort: true } })
const receivedApi = []
server?.httpServer.prependListener('request', request => {
  if (/^\/proxy\/|\/api\/v1\//.test(request.url || '')) receivedApi.push(request.url)
})
let browser
try {
  const res = await fetch(app + 'preview-build.json')
  assert.equal(res.status, 200)
  assert.deepEqual(await res.json(), { version, branch: 'integration/' + version, sha })
  const html = await (await fetch(app)).text()
  assert.ok(html.includes(base + 'assets/'))
  assert.match(html, /connect-src (?:&#39;|&apos;|')none(?:&#39;|&apos;|')/)
  browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const errors = [], attempts = [], apiResponses = []
  const isApi = request => /^https?:/.test(request.url()) && /\/proxy\/|\/api\/v1\//.test(new URL(request.url()).pathname)
  page.on('pageerror', error => errors.push(error.message))
  page.on('request', request => { if (isApi(request)) attempts.push(request) })
  page.on('response', response => { if (isApi(response.request())) apiResponses.push(response.url()) })
  const cdp = await page.context().newCDPSession(page)
  const networkRequests = new Map(), cspBlocked = new Set()
  await cdp.send('Network.enable')
  cdp.on('Network.requestWillBeSent', event => networkRequests.set(event.requestId, event.request.url))
  cdp.on('Network.loadingFailed', event => {
    if (event.blockedReason === 'csp') cspBlocked.add(networkRequests.get(event.requestId))
  })
  await page.goto(app + '#/archive-workbench', { waitUntil: 'domcontentloaded' })
  const search = page.getByRole('textbox', { name: '病案查询值' })
  await search.waitFor({ timeout: 45_000 })
  await search.fill('26070000')
  await search.press('Enter')
  const samples = page.getByRole('group', { name: '有效影像列表' })
  await samples.getByRole('button').first().click({ timeout: 30_000 })
  const image = page.getByAltText('待核对影像')
  await image.waitFor({ timeout: 30_000 })
  await page.waitForFunction(() => { const image = document.querySelector('img[alt="待核对影像"]'); return image?.complete && image.naturalWidth > 0 })
  assert.match(await image.getAttribute('src'), /^blob:/)
  await page.getByRole('button', { name: '专注原图' }).click()
  const controls = page.getByRole('group', { name: '原图显示控制' })
  await controls.getByRole('button', { name: '放大', exact: true }).click()
  assert.ok(await controls.getByText('125%', { exact: true }).isVisible())
  if (version === 'v1.2') {
    await controls.getByRole('button', { name: '实际大小' }).click()
    assert.equal(await controls.getByRole('button', { name: '实际大小' }).getAttribute('aria-pressed'), 'true')
    await controls.getByRole('button', { name: '逆时针旋转' }).click()
    assert.ok(await controls.getByText('270°', { exact: true }).isVisible())
    const divider = page.getByRole('separator', { name: '调整检索栏宽度' })
    await divider.focus()
    await divider.press('End')
    assert.equal(await divider.getAttribute('aria-valuenow'), '360')
    await divider.press('Enter')
    assert.equal(await divider.getAttribute('aria-valuenow'), '260')
  } else {
    assert.ok(await page.getByRole('slider', { name: '检索栏目标宽度' }).isVisible())
  }
  await page.reload({ waitUntil: 'domcontentloaded' })
  await search.waitFor({ timeout: 45_000 })
  const denied = await page.evaluate(async () => (await fetch('/proxy/api/v1/patients/1', { method: 'PUT' })).json())
  assert.equal(denied.code, 503)
  assert.deepEqual(receivedApi, [], 'no API traffic reached the static server')
  assert.deepEqual(apiResponses, [], 'no API network responses')
  for (const request of attempts) {
    const url = new URL(request.url())
    assert.equal(url.origin, new URL(app).origin)
    assert.equal(url.pathname, '/proxy/api/v1/public/status/developer-mode', 'unexpected network attempt')
    assert.equal(request.method(), 'GET')
    assert.ok(request.failure(), 'status request must fail locally')
    assert.ok(cspBlocked.has(request.url()) || /CSP/i.test(request.failure().errorText), 'status request must be blocked by CSP')
  }
  console.log('CSP-blocked read-only status probes:', attempts.length, '; server received API traffic:', receivedApi.length)
  assert.deepEqual(errors, [], 'no unhandled browser errors')
  console.log('PASS: ' + version + ' ' + sha + ' ' + app + '#/archive-workbench')
} finally {
  await browser?.close()
  if (server) await new Promise((resolve, reject) => server.httpServer.close(error => error ? reject(error) : resolve()))
}
