# MRR 独立版本预览

独立公开静态演示仓库，不包含医疗生产数据或私有配置，不修改 [MRR 正式 Pages](https://weepwood.github.io/MRR/) 或其 main / integration 分支。

- V1.1: `integration/v1.1`，预览路径 `/MRR-preview/v1.1/#/archive-workbench`
- V1.2: `integration/v1.2`，预览路径 `/MRR-preview/v1.2/#/archive-workbench`

GitHub Actions 每15分钟查询两个公开分支（GitHub 调度可能延迟）；仅发现 SHA 变化或手动强制时构建。精确 checkout、锁定依赖、源项目 Pages Mock 构建、静态 CSP 校验、实际 Chromium 工作台及只读隔离验收；两版本均成功才原子部署，失败保留上一版。部署后核对两份公开身份清单。手动入口为 Actions → MRR version previews → Run workflow。

使用同一个独立预览 Pages 站点的不同路径，页面资产与路由按版本分开。GitHub Pages 同账号站点共享 origin，浏览器的本地主题/演示状态可能共享；需要完全独立体验时使用不同浏览器配置文件。源项目 Pages 模式禁用生产 PWA，禁止真实后端连接。不配置 PAT、第三方托管令牌、生产环境变量或私有数据。

仅跟踪上述两个分支；不会构建正式 main，不覆盖原 Pages。回滚：停止 schedule 或重新部署此前已确认的预览制品；不要重置源项目分支。
