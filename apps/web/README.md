# AsiaTax · 税务研究聊天工作台

以聊天为中心的原创中文前端：案例导航、虚构示例、事实确认卡、收取情况选项、研究清单和法规来源侧栏。浅色界面配合深蓝导航，使用 Lucide 的天平、机构、硬币、账簿和核验图标。适配桌面与手机。

**当前是交互预览，不是已连接 AI 的税务系统。** 回答和研究清单来自固定演示逻辑；自由文本不会被自动提取为事实。仅允许虚构案例，对话保存在页面内存中，刷新即清空，不向外部服务发送。主分支 FastAPI 目前只有健康检查，未接入本前端；旧的 `demo/hk-web` 未被合并。

## 本地运行

需要 Node.js 20.19+ 或 22.12+（建议 Node 22）。从仓库根目录执行，PowerShell、macOS 和 Linux 均可：

```sh
cd apps/web
npm ci
npm run dev
```

打开 <http://127.0.0.1:5173>。无需数据库或模型密钥。端口占用时会明确报错，避免打开错误的应用。

选择「境外股息」示例 → 发送 → 核对事实 → 确认并继续 → 选择收取情况 → 打开法规来源。
点击「编辑事实」修改金额等字段会撤回旧研究清单，重新确认后才能继续。新案例与历史案例互相独立。

## 验证

```sh
npm run build
npx playwright install chromium
npm test
npm audit
```

如果 Windows 已安装 Chrome，可跳过浏览器下载并使用：

```powershell
$env:PLAYWRIGHT_CHANNEL = 'chrome'
npm test
```

7 项浏览器测试覆盖：桌面首屏与无外部请求、事实到来源的完整流程、修改后失效与重新确认、案例隔离与搜索、自由文本未知事实、中文输入法和换行、手机导航与焦点约束。截图保存在未跟踪的 `test-results/`。CI 使用 Playwright Chromium 运行相同检查。

## 结构与接入边界

- `src/App.tsx`：案例状态、页面布局与面板切换。
- `src/demo.ts`：显式的演示状态与虚构预设；后续真实接入应替换此边界。
- `src/components/`：聊天、输入框、事实编辑、官方来源和导航。
- `src/styles.css`：配色、金融图标构图和响应式样式。
- 来源元数据引用仓库 `knowledge/hong_kong/fsie/source_manifest.json`；面板是资料索引，未展示伪造原文、实时检索结果或税务结论。

后续接入需要新增后端案例/事实确认接口及真实分析生命周期，明确错误、等待和版本变化处理。不得把示例清单替换为模型文字后直接当作专业结论。当前不含上传、税额计算、持久化、身份认证或导出。

## 参考与授权

- 对话组织参考 [Vercel Chatbot](https://github.com/vercel/chatbot)（Apache-2.0），未复制其实现。
- 页面为原创实现；v0 模板只用于讨论交互方向，未复制模板代码、图形或样式。
- [Lucide](https://github.com/lucide-icons/lucide) 图标按包内 ISC/MIT 授权使用，React 采用 MIT。
- 完整运行时依赖授权见 [THIRD_PARTY_NOTICES.txt](public/THIRD_PARTY_NOTICES.txt)，构建时随静态产物发布。
- [Vite](https://github.com/vitejs/vite) 采用 MIT；开发依赖的授权保留在各安装包内。
