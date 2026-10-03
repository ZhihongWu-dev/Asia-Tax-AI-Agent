# AsiaTax · 税务聊天工作台

中英文聊天界面，真实调用 FastAPI 案件、消息、事实确认和研究分析接口。案例信息与来源按需展开，保留税务图标和手机适配，无地区选择或固定助手答案。

## 启动

从仓库根目录，先安装 Python 3.11+ 依赖及前端依赖：

```sh
python -m pip install -e ".[dev]"
cd apps/web
npm ci
npm run build
cd ../..
python scripts/run_chat.py
```

打开 <http://127.0.0.1:8000>，同一服务提供前端和 API。推荐使用根目录 `.venv` 的 Python。开发时另在 `apps/web` 执行 `npm run dev`，使用 <http://127.0.0.1:5173>；`/api` 同源代理至 8000。

`.env` 的 `FSIE_MODEL_API_KEY` 由后端读取，勿使用 `VITE_` 前缀。填好后下一次发送或重试即重新读取。没有有效模型配置时，发送会明确报错，输入保留；不会回退到固定答案。

## 工作流与边界

1. 描述合成研究案件；首次发送前确认资料范围。
2. 模型提取候选事实，后端提出核心追问；也可打开事实卡补充、修订或标记未知。
3. 保存修改，点击“确认事实并分析”。存在冲突时不能确认。
4. 查看现有规则的研究结果、阻断项、缺失节点、事实/规则版本及来源。
5. 后续修改使旧分析过期；需重新确认和分析。案件与结果可以刷新恢复。

会话默认保存到 `FSIE_DATABASE_URL` 指向的云端 PostgreSQL，可用 `FSIE_WEB_DATABASE_URL` 指定另一数据库。浏览器随机 HttpOnly cookie 用于隔离工作空间；localStorage 只保存语言偏好，未发送的草稿只在本页内存。清除 cookie 会失去原工作空间入口，当前不是完整账号系统。旧 SQLite 会话不会自动迁移。

实际模型、知识数据库和完整专业闭环仍须分别验证。当前只有 5 个业务规则节点；资料库不可用时只展示明确标注的官方索引链接。无完整混合检索、专业审批、报告导出或跨地区能力。详见 [实现与验证记录](../../docs/project/LIVE_CHAT_SLICE.md)。

## 测试

```sh
npm run build
npx playwright install chromium
npm test
```

测试需要已安装项目的 Python；默认用 PATH 的 `python`，可设置 `FSIE_TEST_PYTHON` 为根目录 `.venv` 解释器的绝对路径。Windows 使用已安装 Chrome 时设置 `PLAYWRIGHT_CHANNEL=chrome`。测试自动启动隔离的 8001/5174 服务。

6 项浏览器测试覆盖双语首屏、真实 API 与持久化、确认门槛、规则结果、修改后失效、模型失败重试、冲突修订、案例隔离、输入法及手机焦点。模型边界使用测试返回，不代表真实模型调用通过。截图在未跟踪的 `test-results/`。

## 结构

- `src/api.ts`：同源 API、超时、安全错误码。
- `src/hooks/useWorkspace.ts`：会话恢复、幂等重试与前端状态。
- `src/components/FactEditor.tsx`：词典驱动的事实修订及确认。
- `src/components/Conversation.tsx`：追问、实际规则结果与来源。
- `src/locale.tsx` / `src/locales/`：中英文界面和工作流文案。
- `src/workspace.ts`：接口类型、快捷问题及官方资料索引。

## 参考与授权

对话组织参考 [Vercel Chatbot](https://github.com/vercel/chatbot)（Apache-2.0），API 组织参考 [FastAPI 官方模板](https://github.com/fastapi/full-stack-fastapi-template)（MIT），未复制实现。页面原创，v0 仅用于讨论方向。Lucide 按包内 ISC/MIT 使用，React/Vite 为 MIT；运行时授权见 [THIRD_PARTY_NOTICES.txt](public/THIRD_PARTY_NOTICES.txt)。
