# B 自由对话工具执行循环

## 技术选择与开源参考

2026-10-04 查阅以下官方开源方案：

- [LangGraph Workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents)：状态图承载动态模型与工具循环。
- [LangChain middleware](https://docs.langchain.com/oss/python/langchain/middleware/built-in)：工具错误、重试、模型/工具调用限制与上下文管理。
- [Deep Agents architecture](https://github.com/langchain-ai/deepagents/blob/main/libs/ARCHITECTURE.md)：在运行时上组织工具、中间件、规划与上下文；无需在本项目启用文件系统、Shell 或委派能力。
- [OpenAI Agents SDK runner](https://github.com/openai/openai-agents-python/blob/main/docs/running_agents.md) 和 [tool guardrails](https://github.com/openai/openai-agents-python/blob/main/docs/guardrails.md)：模型选动作、工具执行、结果回传、最大轮次及执行前后校验。

本项目沿用 LangGraph 与现有模型适配器，增加自定义工具循环；不迁移 SDK，不增加框架依赖。工具选择使用结构化 JSON，兼容当前模型供应商；这不是供应商原生 function calling。未来可增加原生调用适配而保留同一执行契约。

## 运行路径

固定入口、普通聊天、既有追问、更正、权限与分析准入保持现有流程。自由业务对话可切换为：

意图/事实处理 → 工具目录 → 模型提出一个动作 → 服务端参数及权限校验 → 工具执行 → 安全观察 → 下一动作或结束 → 原有输出校验与一次提交。

工具：read_case_facts、check_fact_gaps、search_law、search_guidance、search_cases、prepare_analysis。finish 是控制动作。数据层仍为 KnowledgeProvider，不给模型 SQL、连接信息、任意账号/案件 ID。

模型观察仅包含结构化状态、字段名、证据数量、缺口原因、已执行工具和剩余预算，不含证据原文与账号密钥。最终答复由已校验工具结果组成，调度器不能自由撰写税务结论。

## 强制边界

- 仅支持当前香港股息范围；查询不得改变用户地区、期间、编号；独立查询不继承旧案过滤。
- read_case_facts/check_fact_gaps 为只读，读取当前请求案件；不确认事实、不改变缺口许可。
- prepare_analysis 只有用户明确要求且事实确认/部分许可准入满足时可执行；本轮事实变化必须重新确认。
- 保留一次一个主要追问，等待用户时结束本轮；最终顾问复核仍是唯一人工节点。
- 统一 RunBudget；工具参数签名去重，检索改写最多一次；达到预算停止并保留结果。
- 工具异常转换为不含原始异常文本的状态；不自动切 Mock。JSON 与 SSE 共用准备/提交路径。

## 开关与回滚

```dotenv
FSIE_AGENT_ORCHESTRATION=hybrid
FSIE_AGENT_DYNAMIC_PLANNER=true
FSIE_AGENT_HARNESS_MODE=tools
```

默认 harness_mode=rewrite，保留上一版无匹配查询改写。tools 模式仅用于 entry_hint=auto 的业务请求，三个快捷入口保持现有子图。部署先在测试环境启用；切回 rewrite 或关闭 dynamic_planner 即回滚。真实模型未配置时应返回明确失败，不冒充在线成功。

## 验收

多工具顺序、不同资料类型查询、只读事实/缺口、重复工具停止、非法参数/编号/范围/越权分析拒绝、入模/展示受限原文不进入规划、部分成功后模型失败保留、预算停止、普通聊天/固定入口不触发额外调度；已有 JSON/SSE、追问与最终复核回归。真实 C 和真实模型仍需另行在线验收。

## 实现与验证记录

- `packages/agent/tools.py`：工具目录、严格参数契约、允许动作与查询校验。
- `packages/agent/tool_harness.py`：LangGraph plan/execute 循环、元数据观察、去重、结果保存和停止。
- `packages/agent/harness.py::plan_tool`：生产模型选择与有限 JSON 修复，修复时使用剩余期限。
- `packages/agent/hybrid.py`：接入父图，自由对话可启用；已有明确多任务队列保持一次执行，减少重复和额外模型请求。
- `tests/agent/test_tool_harness.py`：31 项工程验收；测试模型选择用脚本，检索为合成 Mock。
- `tests/agent/test_real_eval.py`：额外保留生产 Prompt、解析器、LangGraph、实际消息 API 和持久化，替换模型 HTTP 响应进行流程验收。不是在线成功。

在线验收命令（私有 `.env` 先配置 OpenRouter 密钥，每脚本最多四次请求；小额度先只选一条）：

```sh
.venv/bin/python scripts/evaluate_b_workflow.py --dataset evals/b_workflow/v0.1/tool_harness.json --harness-mode tools --select BWF-TOOLS-001 --max-calls 4 --output evals/b_workflow/runs/tool-live.json
```

评测严格检查工具序列；如果生产意图解析选择了预先分解任务队列，而未进入工具循环，将记录为不满足本次工具循环验收，不伪装成功。两种路径的任务重复执行工程检查已覆盖。

这次配置预检为两个脚本 blocked、零模型调用。真实模型工具选择质量、C 真实服务、专业税务正确性及 PostgreSQL 验收仍需继续；没有新自由生成法律解释节点，也未实现相似案例比较算法。

最终工程回归（2026-10-04）：318 项 Python 通过、11 项真实 PostgreSQL 测试未运行；26 项既有页面兼容回归通过；TypeScript/Vite 构建、知识包及两套评测集格式检查通过。新工具循环的 JSON 与 SSE API 验收包含在 Python 测试中，页面兼容回归使用原测试服务，不作为真实模型工具选择质量证明。
