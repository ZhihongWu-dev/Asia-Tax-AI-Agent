# Applications

本目录保存可独立运行的应用入口。

主分支的 `api/main.py` 提供 FastAPI 应用和 `/health` 健康检查。业务逻辑位于 `packages/`。

旧 Web 演示及其案例分析 API 保留在 `demo/hk-web` 分支，未合并。

本开发分支的 [`web/`](web/README.md) 是重新实现的中英文税务聊天工作台，使用 React、TypeScript 和 Vite。提供对话输入、手工案例信息和官方来源侧栏，尚未接入后端分析服务；提交时明确显示未发送状态，不生成固定答案。启动方式见该目录 README。
