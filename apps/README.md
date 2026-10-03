# Applications

本目录保存可独立运行的应用入口。

`api/main.py` 提供 FastAPI 应用、健康检查和构建后的前端。`api/chat.py` 提供案件、消息、事实确认与分析 API；编排和持久化位于 `packages/chat/`，复用原有规则引擎与模型适配器。

旧 Web 演示及其案例分析 API 保留在 `demo/hk-web` 分支，未合并。

本开发分支的 [`web/`](web/README.md) 是中英文税务聊天工作台，使用 React、TypeScript 和 Vite，已连接上述 API。模型配置不足时明确报错，不生成固定替代答案。完整运行和验证边界见 [网页研究链路记录](../docs/project/LIVE_CHAT_SLICE.md)。
