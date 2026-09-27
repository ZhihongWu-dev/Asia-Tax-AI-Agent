# AsiaTax · 税务聊天工作台

简洁的中英文聊天前端：深蓝导航、中央输入框、三个快捷问题，以及按需展开的案例信息与官方来源。使用 Lucide 税务相关图标，适配桌面和手机，无地区选择。

**当前尚未连接分析服务，不能生成税务回答。** 提交消息时显示未发送状态，不使用固定答案模拟分析。消息、草稿和手工事实仅存在页面内存，刷新清空；语言偏好单独保存在 `asiatax.language`。后端闭环差距见 [核查记录](../../docs/reviews/2026-09-27-agent-closure-audit.md)。旧 `demo/hk-web` 未合并。

## 本地运行

需要 Node.js 20.19+ 或 22.12+，建议 Node 22。从仓库根目录执行：

```sh
cd apps/web
npm ci
npm run dev
```

打开 <http://127.0.0.1:5173>。运行当前界面无需数据库或模型密钥。端口占用会明确报错。

快捷问题只填入输入框，用户可修改再提交。右上角分别提供语言切换、来源和案例信息。案例字段允许留空；保存不触发分析，不代表后端顾问确认。语言切换保留用户原文及各会话草稿。来源为官方资料索引，不是实时检索或本次问题的分析引证。

## 验证

```sh
npm run build
npx playwright install chromium
npm test
```

Windows 已安装 Chrome 时可跳过浏览器下载：

```powershell
$env:PLAYWRIGHT_CHANNEL = 'chrome'
npm test
```

8 项浏览器测试覆盖简洁首屏及无外部请求、提交后的真实未连接状态、案例与草稿隔离、手工事实保存、来源链接与折叠元数据、中英文切换及偏好、中文输入法、手机布局与键盘焦点。截图保存到未跟踪的 `test-results/`。CI 使用 Playwright Chromium。

## 结构与接入边界

- `src/App.tsx`：案例、草稿、布局与面板状态。
- `src/workspace.ts`：会话数据、空事实、快捷问题和来源元数据，无预设答案。
- `src/locale.tsx` / `src/locales/en.ts`：语言上下文和英文词典。
- `src/components/`：聊天、输入框、手工事实编辑、来源和导航。
- `src/hooks/useOverlayFocus.ts`：弹层键盘与焦点管理。
- `src/styles.css`：布局、配色和响应式样式。

来源元数据引用 `knowledge/hong_kong/fsie/source_manifest.json`。后续须新增后端案件/访谈/确认/分析接口和真实生命周期，并处理持久化、错误、重试与版本变化。模型密钥只能由后端读取，不得使用 `VITE_` 前缀暴露给浏览器。当前没有上传、税额计算、认证或报告导出。

## 参考与授权

- 对话组织参考 [Vercel Chatbot](https://github.com/vercel/chatbot)（Apache-2.0），未复制实现。
- 原创页面；v0 模板仅用于讨论交互方向，未复制代码、图形或样式。
- [Lucide](https://github.com/lucide-icons/lucide) 按包内 ISC/MIT 授权使用；React 为 MIT。
- 完整运行时授权见 [THIRD_PARTY_NOTICES.txt](public/THIRD_PARTY_NOTICES.txt)，随构建产物发布。
- [Vite](https://github.com/vitejs/vite) 为 MIT；开发依赖授权保留在各安装包内。
