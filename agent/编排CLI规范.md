# 编排与 CLI 规范（最小集）

2026-11-01。本文只定四个 Agent 怎么启动、按什么顺序走、什么时候停。各 Agent 的职责见各自规范，案卷的读写和账本见 `agent/案卷MCP规范.md`。实现文件是 `agent/tools/orchestrate.py`，检查是 `agent/tools/test_orchestrate.py`。

**语言**：本规范用中文，供人阅读；英文副本 `agent/orchestration_cli_spec.en.md`，两者不一致时以中文版为准，改中文版时同步改英文副本。只有规范正文用中文。其余一律用英文：代码、注释、日志，递交给 Agent 的任务说明，CLI 的提示、状态和停止说明。

## 1. 定位

| 层 | 用什么 | 管什么 |
|---|---|---|
| 执行 | Claude Code | 跑 Agent：对话、工具、MCP、钩子 |
| 编排 | LangGraph | 定下一步：节点、分支、退回循环、停止 |
| 事实 | 案卷文件 | 状态、产物、核对单 |

- 前台是唯一的交互式会话，客户只和它说话。分析、润色、复核由编排器各起一次无头 `claude -p`，每次全新上下文。前台不再用子 Agent 起它们。
- 编排器不做税务判断，不改 Agent 写的内容，不替代复核。它只看文件、核对单末句和两个自检的结果。
- 只用 LangGraph，不用 LangChain 的模型和 Agent 层，不用 LangSmith，不需要账号。
- 状态全部从案卷文件推出，图里不存业务状态，所以不用 checkpointer。中断后再跑一次 `run`，就从当前状态接上。
- Agent 的自述不算数。节点是否完成只看文件有没有更新、自检有没有问题。

## 2. 流程

顺序是分析、复核草稿、润色、复核成稿。先把实质定下来，再改表达；润色之后只比对意思有没有变。

**节点**

| 节点 | 执行者 | 进入状态 | 做什么 | 完成判定 |
|---|---|---|---|---|
| `review_intake` | 复核 | intake | 先过程序关：`intake_check` 无问题，`handoff.md` 已写，否则 `need_front`；再核交接包 | `review_intake.md` 已更新，末句合法 |
| `run` | 程序 | intake_ok | 由 facts.json 加 `closing_answers(answers.json)` 生成 `intake/run_input.json`，再 `validate_input`、优化层 `run`、`round_set_run`；有上一轮时再做 `diff` | 账本登记了 run_id |
| `analysis` | 分析 | ran | 写草稿和出处表 | 草稿或出处表已更新，`report_check(draft)` 无问题 |
| `review_draft` | 复核 | drafted | 核草稿的实质 | `review.md` 新于草稿，末句合法 |
| `polish` | 润色 | reviewed | 改写成稿，出 PDF | 成稿文件已更新，`report_check(polished)` 无问题 |
| `review_final` | 复核 | polished | 比对成稿和草稿 | `review_final.md` 新于成稿，末句合法 |

**复核三段**

| 段 | 核什么 | 文件 | 末句 |
|---|---|---|---|
| 一 | 交接包对单据原件 | `intake/review_intake.md` | `RUNNABLE` / `REVISE` |
| 二 | 草稿的数字、法律、结构、未决项、假设 | `report/<run_id>/review.md` | `POLISHABLE` / `REVISE` |
| 三 | 成稿的意思是否变了，前提是否丢了，客户能否读懂。不重审实质 | `report/<run_id>/review_final.md` | `DELIVERABLE` / `REVISE` |

`REVISE` 的核对单在末句之前写一行 `RETURN: analysis`、`RETURN: polish` 或 `RETURN: front`。第一段固定退前台，不写这一行；第二段不能写 `polish`。一张单子涉及多方时，写流程上最靠前的一方，因为后面的环节都会重做。

**状态**（替换案卷规范 §2 的 drafted、polished、delivered，新增 reviewed；其余不变）

| 状态 | 判定 |
|---|---|
| drafted | `briefing.md` 存在，`review.md` 不存在、旧于草稿或末句 `REVISE` |
| reviewed | `review.md` 末句 `POLISHABLE` 且新于草稿，成稿不存在或旧于 `review.md` |
| polished | 成稿新于 `review.md`，`review_final.md` 不存在、旧于成稿或末句 `REVISE` |
| delivered | `review_final.md` 末句 `DELIVERABLE` 且新于成稿 |

**去向**

| 结果 | 下一步 |
|---|---|
| `RUNNABLE` | `run` |
| 第一段 `REVISE` | 停止，`need_front` |
| `run` 完成 | `analysis` |
| 分析的自检有问题 | `analysis` 再跑，问题列表写进任务说明 |
| `POLISHABLE` | `polish` |
| `RETURN: analysis`（第二、三段） | `analysis` |
| 润色的自检有问题 | `polish` 再跑，问题列表写进任务说明 |
| 润色记了新的 `issues` 且没有出 PDF | `analysis`，`issues` 原文写进任务说明 |
| `RETURN: polish`（第三段） | `polish` |
| `RETURN: front`（第二、三段） | 停止，`need_front` |
| `DELIVERABLE` | 结束，`delivered` |

每次因 `REVISE` 退回，程序先调 `round_revise`，修订号加一。分析改了草稿，文件时间会让状态回到 drafted，后面的复核和润色自然重走。再核时只核改动处，规则见复核规范。

**停止**

| 停止原因 | 含义 | 谁接手 |
|---|---|---|
| `delivered` | 成稿可交付 | 前台交给客户 |
| `need_front` | 交接包或事实要改 | 前台读核对单，改交接包，必要时问客户，再 `run` |
| `revision_limit` | 同一节点在一次 `run` 内已跑 4 次 | 人 |
| `agent_failed` | 进程失败、超时、超轮次，或跑完文件没更新 | 人 |
| `system_defect` | 本轮有未清除的 `affects_result` 缺陷 | 人，修好后 `orchestrate.py clear <case_id> <agent/B-n>`，再继续 |
| `rate_limited` | 网关限流 | 人，额度恢复后再 `run` |
| `busy` | 这个案卷已有 `run` 在跑 | 等它结束 |

已登记 run_id 的一轮，退回前台意味着事实要改、结果要重算。这时前台调 `round_new` 开新一轮，走新的 run_id。`round_new` 的前提是：状态是 delivered，或报告阶段的核对单写着 `RETURN: front`。事实没变时优化层不会产出新 run_id，编排器按 `need_front` 停下。

## 3. CLI

**入口**

| 命令 | 作用 |
|---|---|
| `python agent/tools/orchestrate.py front [case_id]` | 起前台交互会话 |
| `python agent/tools/orchestrate.py run <case_id>` | 从当前状态走到某个停止原因，向 stdout 输出一行 JSON：status、stop、detail、run_id、本次跑过的节点 |
| `python agent/tools/orchestrate.py status <case_id>` | 只读：当前状态、下一节点、上次停止原因 |
| `python agent/tools/orchestrate.py graph` | 导出节点图到 `agent/orchestration_graph.mmd` |

Python 是 `tax` 环境的解释器。前台写好 `handoff.md`、`intake_check` 无问题后，用 Bash 后台跑 `run`，结束后按停止原因继续。优化层产物在 `run` 节点才生成，所以 `handoff.md` 不写 diff，分析 Agent 自己读 `diff.json`。

**Agent 配置**

| Agent | 模型 | 运行方式 | max_turns |
|---|---|---|---|
| 前台 | qwen3.7-plus | 交互 | 不设 |
| 分析 | qwen3.8-max | 无头 | 80 |
| 润色 | qwen3.7-max | 无头 | 60 |
| 复核 | qwen3.7-plus | 无头 | 80 |

**无头调用**

```
claude -p "<task>" --agents .claude/agents.json --agent <name> --mcp-config .claude/mcp/<name>.json --strict-mcp-config --output-format stream-json --verbose --include-partial-messages --max-turns <n> --allowedTools <list>
```

| 环境变量 | 值 |
|---|---|
| `ANTHROPIC_BASE_URL` | `https://token-plan.cn-beijing.maas.aliyuncs.com/apps/anthropic` |
| `ANTHROPIC_AUTH_TOKEN` | `.env` 的 `qwen_key` |
| `ANTHROPIC_MODEL` | 上表的模型 |
| `ANTHROPIC_SMALL_FAST_MODEL` | `qwen3.7-plus` |
| `ENABLE_TOOL_SEARCH` | `false`，Qwen 网关需要 |
| `CLAUDE_AGENT_NAME` | Agent 名，钩子的后备身份来源 |
| `MCP_SERVER_CONNECTION_BATCH_SIZE` | `8`，一批连完 |
| `LANGSMITH_TRACING` | `false`，编排器自身也设 |

- 密钥只经子进程环境传递，不上命令行，不进日志和报错。
- 工作目录是项目根，`.mcp.json` 的相对路径才成立。
- 可执行文件按顺序找：环境变量 `CLAUDE_BIN`、PATH 上的 `claude`、VS Code 扩展目录里最新版本的 `claude.exe`。
- `make_agents.py` 除 `.claude/agents/*.md` 外，再生成 `.claude/agents.json`，因为无头模式的 `--agent` 不认项目级定义。`--allowedTools` 取同一张工具表。
- `make_agents.py` 在每个 Agent 的提示词后追加一段存盘说明（`SAVE_TOOLS`）：Agent 没有 `Write` 工具，文件都经案卷服务写。实跑中复核 Agent 找不到 `Write`，就把核对单写在回复里，节点因没有落盘而失败。
- `make_agents.py` 还从 `.mcp.json` 生成 `.claude/mcp/<name>.json`，每个 Agent 只连自己的服务。CLI 按批连接 MCP，第一轮模型调用不等全部连完；八个服务全连时，排在后面的 Agent 开局看不到自己的工具，不会报错，只会说工具不可用。

**任务说明**：prompt 在 Agent 规范里，编排器只递一句英文短任务，下表是原文。

| 节点 | 任务 |
|---|---|
| `review_intake` | `Check the intake package of case <case_id>.` |
| `analysis` | `Write the briefing draft for case <case_id>, run <run_id>.` |
| `review_draft` | `Check the briefing draft of case <case_id>, run <run_id>.` |
| `polish` | `Polish the reviewed draft of case <case_id>, run <run_id> and produce the PDF.` |
| `review_final` | `Compare the polished report with the draft of case <case_id>, run <run_id>.` |

再次运行时在后面加一句 `Revision <n>. Reason: <reason>`，reason 是核对单路径（`see <path>`）、自检问题列表或 `issues` 原文。

**进程**

- 单个节点 60 分钟超时。超时或编排器被中断时，用 `taskkill /T /F` 结束整棵进程树。只杀外层进程，`claude.exe` 会活着继续写文件。
- 网络错误重试 1 次。限流不重试，直接停止。
- 同一案卷同时只跑一个 `run`：`cases/<case_id>/log/run.lock` 记 PID，PID 已不存在时接管。

## 4. 图

- 图的状态只放流程信息：`case_id`、`next`、`last_node`、`stop`、`detail`、`reason`、`redo`、节点计数和跑过的节点。
- 节点是 `dispatch` 加 §2 的六个。`dispatch` 按 `round_current` 和核对单选入口，所以从任何状态都能接上。
- 每次节点结束都重新从文件推状态，再决定去向。
- 条件边写明合法去向，导出的图才只有真实路径。
- `recursion_limit` 设 60，上限由 `revision_limit` 决定。
- `need_front` 是结束一次 `run`，不用 `interrupt` 挂起，客户隔多久回来都没关系。
- 程序步骤以 front 身份调用案卷代码。优化层走 `mcp_call.py`，单开进程，因为它和数据库服务的模块同名。

## 5. 记录与可视化

- `cases/<case_id>/log/runs.jsonl`：每个节点开始和结束各一行，含 time、node、agent、model、round、revision、attempt、session_id、turns、seconds、status_before、status_after、stop。
- `cases/<case_id>/log/runs/<n>-<node>.jsonl`：CLI 的事件流，运行中实时写入；思考内容也在这里。
- 节点图看 `graph` 的导出。运行进度和历史由 UI 层读 `runs.jsonl` 和 `round_current` 展示。

## 6. 构建记录

2026-11-01 建成：`orchestrate.py`；案卷服务的新状态、三段复核和 `RETURN` 校验；`make_agents.py` 生成 `.claude/agents.json`，前台不再有 `Agent` 工具，缺英文副本时直接报错；各 Agent 规范按新流程改写。`test_orchestrate.py` 用脚本扮演 Agent，真实走路由、状态和上限，并用真实子进程验证超时能结束整棵进程树。接线实测：分析、润色、复核各跑一次真实 `claude -p`，用各自模型和身份经 MCP 读到案卷状态。尚未用真实 Agent 跑完整流程；前台的交互入口没有实测。

复核再核时，编排器把与上次核对内容的差异写进 `log/review_changes-<node>.md`，任务里要求只核改动和退回的条目；同一轮内有效，新一轮从头核。

2026-11-02 第一次真实全流程，经网页宿主跑到 `delivered`：英文案例，15 份文档，节点累计约 3 小时 17 分，产出 7 页 PDF，终稿比对 `DELIVERABLE`。这次发现并修掉：复核没有写文件工具时把清单写在回复里（存盘说明）；分析跑满 1 小时被截断（单节点超时放宽到 3 小时）；`render_pdf` 失败时吞掉真实错误（`err` 重复传参）。同日的局部修复：宿主发给客户的文字一律过滤路径和编号；进程实测通过自动重跑上限、服务被杀后运行继续、Stop 和 Resume；优化层修了事实放在实体上读不到、分叉只看第一轮、全有利世界缺失、母公司算重组四处，香港和日本公司改为边际税率表；这些修复没有经过一次完整的真实运行。

## 7. 不做

不并行跑 Agent；不用 LangChain 的 Agent 层；不用 LangSmith、checkpointer 和 LangGraph Studio（需另装 `langgraph-cli`，账号和轨迹外传问题未核实）；不让模型决定流程走向；不做客户界面（UI 层的事）。

## 8. 网页宿主

`apps/api/server.py` 是 `apps/web` 背后的接口，本机单用户，只绑 127.0.0.1。启动：`C:/Coding/Anaconda/envs/tax/python.exe apps/api/server.py`，打开 http://127.0.0.1:8000。

- 客户的一句话是前台 Agent 的一个无头回合，用 `--resume` 接续会话。回合的事件流写进 `log/runs/<n>-front.jsonl`，边写边读，经 SSE 推给页面：回复走 `delta`，思考、工具调用和工具前的话走 `activity`。对话存在 `cases/<case_id>/chat.json`。
- 客户的每条消息由宿主逐字写进 `dialogue.md`，案卷服务拒绝前台写 client 条目：实跑中前台为了过检查，代客户写过一段"不知道"。
- 网页模式用 `--append-system-prompt` 追加一段说明，替换前台第 4 步的 Bash：前台不自己跑 `orchestrate.py`，准备好后在回复末尾写 `[[START_RUN]]`。宿主去掉这个标记，再把编排器作为独立进程启动，所以服务重启或页面刷新都不中断运行。
- 运行结束后：`delivered` 和 `need_front` 由宿主发一条 `[Host]` 消息给前台，前台用自己的话告诉客户，`delivered` 时宿主附上 PDF 下载链接；`rate_limited`、`agent_failed`、`revision_limit` 不调模型，宿主直接发固定文字。没有客户发言时最多自动重跑 3 次，到上限就停下并告诉客户，避免循环。
- 进度从文件读，不从进程读。`GET /api/cases/{id}/run?after=<cursor>` 返回节点状态（`runs.jsonl`、`run.lock`、`round_current`）和各 Agent 事件流里新增的条目。修订时阶段回退，后面的节点回到待运行，并保留运行次数。
- `POST /api/cases/{id}/run` 从当前状态继续，`POST /api/cases/{id}/run/stop` 结束整棵进程树并记一行 `stopped`。
- 读日志时也要去掉密钥：事件流是运行中读的，`scrub` 要到节点结束才执行。

限制：一条消息最多 30 个附件；单用户，没有登录；运行需要本机的 Claude Code、xelatex 和持久磁盘，不能放在无状态托管上。
