"""Verify public demo identity and assemble an atomic two-version Pages site."""
import datetime
import html
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
import urllib.request

ROOT = 'https://weepwood.github.io/MRR-preview/'
VERSIONS = {'v1.1': 'integration/v1.1', 'v1.2': 'integration/v1.2'}

def identity(version, sha):
    assert version in VERSIONS and re.fullmatch(r'[a-f0-9]{40}', sha)
    return {'version': version, 'branch': VERSIONS[version], 'sha': sha}

def stamp(directory, version, sha):
    path = Path(directory)
    index = (path / 'index.html').read_text()
    assert re.search(r'(?:src|href)="/MRR-preview/' + re.escape(version) + r'/assets/', index), 'incorrect asset base'
    assert re.search(r'connect-src (?:&#39;|&apos;|\x27)none(?:&#39;|&apos;|\x27)', index), 'missing static-demo CSP'
    assert not re.search(r'(?:src|href)="/(?:MRR/|assets/)', index), 'unexpected asset base'
    assert not any(path.rglob('*.map')), 'source maps are not permitted'
    (path / 'preview-build.json').write_text(json.dumps(identity(version, sha), indent=2) + '\n')

def expected():
    entries = json.loads(os.environ['EXPECTED_MATRIX'])['include']
    assert len(entries) == 2
    assert {e['version'] for e in entries} == set(VERSIONS)
    assert all(identity(e['version'], e['sha']) == e for e in entries)
    return entries

def site(source, destination):
    items = expected()
    root = Path(destination)
    root.mkdir(exist_ok=False)
    for item in items:
        folder = Path(source) / ('preview-' + item['version'])
        assert json.loads((folder / 'preview-build.json').read_text()) == item
        stamp(folder, item['version'], item['sha'])
        shutil.copytree(folder, root / item['version'])
    (root / '.nojekyll').touch()
    (root / 'versions.json').write_text(json.dumps({'versions': items}, indent=2) + '\n')
    cards = ''.join(f'<a href="./{e["version"]}/#/archive-workbench"><strong>{e["version"].upper()} 病案工作台</strong><small>合成数据 · {html.escape(e["sha"][:12])}</small><span>打开预览 →</span></a>' for e in items)
    (root / 'index.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none';style-src 'unsafe-inline'"><title>MRR 版本预览</title><style>body{margin:0;background:#f6f7fa;color:#172033;font:16px/1.6 system-ui,sans-serif}main{max-width:750px;margin:12vh auto;padding:24px}h1{font-size:30px;letter-spacing:-.03em}p,small{color:#596579}section{display:grid;gap:12px}a{display:flex;flex-direction:column;gap:8px;padding:20px;color:inherit;background:white;border:1px solid #dce1ea;border-radius:12px;text-decoration:none}a:hover,a:focus-visible{border-color:#2563eb}span{color:#2455b8;font-size:14px}footer{margin-top:24px;font-size:13px;color:#596579}@media(prefers-color-scheme:dark){body{background:#141821;color:#eef1f7}a{background:#1d2533;border-color:#3b4557}p,small,footer{color:#aeb8cb}span{color:#9ab7ff}}</style><main><h1>MRR 版本预览</h1><p>独立开发预览，仅使用合成数据，不连接医院后端。</p><section>''' + cards + '''</section><footer>开发版本 · 正式演示站保持独立。建议在不同浏览器配置文件中体验各版本。</footer></main></html>''')

def online():
    items = expected()
    for attempt in range(12):
        try:
            for item in items:
                url = ROOT + item['version'] + '/preview-build.json?run=' + os.environ['GITHUB_RUN_ID']
                with urllib.request.urlopen(url, timeout=20) as response:
                    assert json.load(response) == item
                print('online identity verified:', item)
            return
        except (OSError, ValueError, AssertionError):
            if attempt == 11: raise
            time.sleep(10)

if __name__ == '__main__':
    command, *args = sys.argv[1:]
    {'stamp': stamp, 'site': site, 'online': online}[command](*args)
