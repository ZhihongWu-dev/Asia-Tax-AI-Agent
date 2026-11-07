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
| `run` | 程序 | intake_ok | 由 facts.json 加 `closing_answers(answers.json)` 和 constraints.json 里的约束（exclude、consider、allow_restructure、payback_max、allowed_subjects）生成 `intake/run_input.json`，再 `validate_input`、优化层 `run`、`round_set_run`；有上一轮时再做 `diff` | 账本登记了 run_id |
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
| `revision_limit` | 同一节点在一次 `run` 内已跑 6 次（2026-11-05 由 4 提高：试验中差一处措辞就停；超过由人恢复） | 人 |
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
| 前台 | qwen3.8-flash | 交互 | 不设 |
| 分析 | qwen3.8-flash | 无头 | 150 |
| 润色 | qwen3.8-flash | 无头 | 90 |
| 复核 | qwen3.8-flash | 无头 | 80 |

**无头调用**

```
claude -p "<task>" --agents .claude/agents.json --agent <name> --mcp-config .claude/mcp/<name>.json --strict-mcp-config --output-format stream-json --verbose --include-partial-messages --max-turns <n> --allowedTools <list>
```

| 环境变量 | 值 |
|---|---|
| `ANTHROPIC_BASE_URL` | `https://token-plan.cn-beijing.maas.aliyuncs.com/apps/anthropic` |
| `ANTHROPIC_AUTH_TOKEN` | `.env` 的 `qwen_key` |
| `ANTHROPIC_MODEL` | 上表的模型 |
| `ANTHROPIC_SMALL_FAST_MODEL` | `qwen3.8-flash` |
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

## 9. 反馈、预览与改版（2026-11-02 设计，同日试验实现）

### 9.1 要解决的问题与原则

现状：客户每带回一点，就新开一轮，从入口复核起整份重写，约 2 小时。慢在分析：每轮从零写报告；优化只要几秒。

原则：

1. **一轮等于一版正式报告。** 反馈不再一点一轮：客户带回的点在当前轮里累积，每次只出一张程序生成的预览卡；满足 §9.4 的条件才出新版报告。
2. **走哪条路由程序定，不由模型定。** 出不出报告、整份重写还是在上一版上改，都由程序从产物差异和账本算出。
3. **拿不准就整份重写。** 每个判定都有兜底：条件不满足、对不齐、复核说前后矛盾，都退回整份重写。最坏情况等于现在的速度，不会出错。
4. **改版的起点是上一版成品，不是底稿。** 分析和润色可以读上一版已交付的报告；各 Agent 的底稿仍然跨轮不读。
5. **数字仍然只来自本轮产物。** 沿用上一版的文字时，里面的数字照样按本轮产物核对。

### 9.2 名词

| 名词 | 含义 |
|---|---|
| 反馈 | 客户的一条消息，前台据此改了事实、答案或约束 |
| 预览 | 对当前交接包跑一次优化，不登记 run_id，产物放 `intake/preview/<run_id>/`；判断点只把已答成不利的点当作关闭 |
| 预览卡 | `intake/preview/<run_id>/update.json`：程序从预览产物和基线产物算出的变化摘要（§9.3） |
| 基线版 | 最近一次交付的报告：它的 run_id、草稿、出处表、成稿和产物。案卷第一版没有基线 |
| 改版 | 在基线版上修改出新版：只重写受影响的部分，其余沿用 |
| 全写 | 从零写，即现在的流程 |

### 9.3 流程

```text
客户反馈 ── 前台改交接包 ── intake_check 干净 ── 预览（优化，约 6 秒）── 预览卡 ── 前台转告客户（1~2 分钟）
                                                                      │
                                                    满足 §9.4 任一条件 ┘
                                                                      ▼
review_intake（轻 / 全）── run ── impact ──┬── none   ：停止 no_change，报告不变，前台告诉客户
                                          ├── revise ：analysis（改版）── review_draft ── polish（沿用未改部分）── review_final
                                          └── full   ：现在的流程
```

**预览卡**（`update.json`，优化层的新子命令 `card --products <预览> --against <基线产物> --answers <answers.json>`，纯 JSON，不写文字）：

| 字段 | 含义 |
|---|---|
| `first` | 全有利情景下第一名的结构签名、税额区间，以及它在基线版里的名字，如 Plan B（取自出处表的命名条目，§9.8） |
| `first_changed` | 第一名是否和基线版不同 |
| `worst` | 全不利情景下的第一名和税额 |
| `baseline_first_now` | 基线版推荐的结构现在的有利、不利税额，以及是否已被不利答案关闭 |
| `pending` | 还会改变第一名的判断点和事实缺口，用客户能懂的问题措辞，取自规则层 `question` |
| `triggers` | §9.4 各条件的真假和理由 |
| `time_only` | 只因核算日变动的数，如利息；客户看不到 |

前台转告时用自己的话，宿主按 `update.json` 核数字，规则同交付说明的数字检查。预览卡只算到“程序检查通过”这一步，没有经过复核，所以前台必须说明这是初步结果，正式结论以报告为准。

### 9.4 出正式报告的条件

满足任一条，前台就在回复末尾写 `[[START_RUN]]`。条件 1、2 由程序算，写进 `triggers`；宿主看到其中为真而前台没写标记时，宿主自己启动。

| # | 条件 | 由谁判定 |
|---|---|---|
| 1 | 会改变第一名的判断点都有了 yes 或 no，会改变第一名的事实缺口都补上了。`unknown_asked` 不算已答 | 程序 |
| 2 | 基线版推荐的结构失效：客户把它依赖的判断点答成了不利，分支被关闭；或新事实使它违反硬约束，如超过回本上限、地区被排除；或它在全有利情景下的税比报告写的高了，例如库里的法律变了 | 程序 |
| 3 | 客户要拿正式文件去执行，如董事会、律师、税局 | 前台按客户的话 |
| 4 | 客户要求出新报告 | 前台按客户的话 |
| — | 案卷还没有任何报告 | 交接包齐了就出，同现在 |

第一名变了但上面的条件都不满足时，例如净资产使转股不划算，只出预览卡：客户立刻知道新方向，报告等条件满足再出。

### 9.5 影响判定（`impact` 节点）

`run` 之后、`analysis` 之前加一个程序节点 `impact`，写 `report/<run_id>/impact.json`。它把本轮产物和基线产物按**结构签名**对齐，不按 cand_id 对齐：签名等于路径加动作加重组方式。cand_id 和 branch_id 每次运行会重排；2026-11-02 的重跑里 c1、c2 就互换过，现行 `diff` 按 id 对齐，必须先改，见 §9.10。

**等级**

| 等级 | 条件（按顺序判定，先满足者为准） | 去向 |
|---|---|---|
| `full` | 没有基线版；或 rule.csv、doc.csv 变了，库里的法律变了，引文要全部重核；或分析规范、报告规范的哈希变了；或本轮第一名的签名不在基线版讨论过的结构里；或连续改版已达 3 版；或复核要求全写（§9.6） | 全写 |
| `none` | 与报告有关的产物内容全部不变（排序、各情景的税额、未决项、条件树、一次性成本、暴露额里除 `time_only` 以外的数），并且 facts.json 和 answers.json 自基线以来没有内容变化 | 停止 `no_change` |
| `revise` | 其余情况 | 改版 |

**要改的部分**：程序按产物的变化标出章节，写进 `impact.json` 的 `sections`。

| 产物变化 | 必改的章节 |
|---|---|
| 第一名变了 | 1 策略、4 最优、6 条件、7 执行，以及 5 的表和 3 里新旧第一名两段 |
| 任一情景的税额或排序变了 | 1、5，以及引用这些数的段落 |
| 第一名的条件树或 reference_params 变了 | 6、7 |
| 未决项或答案变了 | 附录 A、第七节第一步 |
| 一次性成本、暴露额变了 | 4、6，以及引用这些数的段落 |
| 现状结构的税额、往年付款的核算变了 | 2 |
| 新增或消失的结构 | 3、5 |

**过期的数**：程序取“基线产物里有、本轮产物里没有”的数值，在基线草稿全文里找出现处，列进 `stale`，含章节和句子片段。这些句子必须改，与它们在不在 `sections` 里无关。

**版本说明**：改版的第 1 部分开头加一段“与上一版相比的变化”，内容只能来自 `impact.json`：哪些点客户确认了、结论变没变、为什么变。全写版不加这一段。

### 9.6 各环节在改版里怎么做

| 环节 | 轻 / 改版模式 | 进入条件 | 兜底 |
|---|---|---|---|
| `review_intake` | 只核自上次 `RUNNABLE` 以来的改动。程序比对快照（§9.8）写 `log/intake_changes.md`，逐条对单据和对话原文 | 有快照，没有新单据，改动的叶子不超过 10 个 | 否则全核 |
| `analysis` | 读基线草稿、出处表、`impact.json` 和本轮产物；交出**完整的**新草稿和新出处表。`sections` 和 `stale` 列出的地方必须重写，其余可以原样沿用，但要对照本轮产物确认仍然成立。结构沿用基线版的名字，Plan A 仍是 Plan A，新结构用下一个字母 | `impact.level = revise` | 发现沿用部分和新事实不能自洽时，用 `notes_append` 在本轮底稿里记一行 `REWRITE: full`，编排器读到后改为全写 |
| `review_draft` | 核 `sections`、`stale` 和版本说明；程序对全文所有数字照本轮产物核对；通读沿用部分是否与改动矛盾 | 同上 | 核对单在末句前写 `REWRITE: full`，退回分析全写，不算一次普通修订 |
| `polish` | 程序先把基线成稿里对应草稿未变的章节原样搬过来，以章节标题对齐；润色只改其余章节，PDF 由 `render_pdf` 重出 | 基线成稿与基线草稿的章节标题一一对应 | 对不齐就整份润色 |
| `review_final` | 只比对改过的章节；程序核搬过来的章节逐字未变 | 同上 | 同现在 |

### 9.7 并发与时点

- **运行中来了反馈**：宿主照常逐字记进 `dialogue.md`。`run.lock` 存在时，案卷服务拒绝前台写 facts、answers、constraints、notes。前台告诉客户这一点会并进下一步。运行结束后，宿主的 `[Host]` 消息附上“运行开始后客户说的话”，前台再落到交接包，接着出预览卡。
- **交付后的第一条反馈**：前台先 `round_new`，同现在，再改交接包。之后的反馈都留在这一轮里，直到出了新版报告。
- **核算日漂移**：每次运行的核算日是当天，利息随之变动。只因核算日变化的数记进 `time_only`，不影响 `none` 的判定，也不单独触发报告；一旦出报告，这些数照本轮更新。
- **撤回答案**：客户改口时，answers.json 跟着改，关闭的分支重新打开。预览卡照常算，基线推荐的结构可能因此恢复。

### 9.8 账本与文件

| 项 | 改动 |
|---|---|
| `rounds.json` 每轮 | 加 `baseline_run`（上一版交付的 run_id，无则为 null）、`mode`（full / revise / none）、`revise_chain`（连续改版的版数）、`spec_sha`（分析规范与报告规范的哈希） |
| 交接包快照 | `write_review(intake, RUNNABLE)` 时，服务把 facts、answers、sources、constraints、notes 复制到 `intake/reviewed/round-N/`，作为下次轻核和 `none` 判定的比较基准 |
| 预览目录 | `intake/preview/<run_id>/`，不登记，不进 `report/`，不算“旧 run 的产物” |
| 出处表 | 加一类条目 `kind: name`：`{where: "Plan A", ref: <结构签名>}`。预览卡和改版靠它沿用名字 |
| 读权限钩子 | 分析在 `mode = revise` 时可读 `report/<baseline_run>/briefing.md` 和 `briefing.sources.json`；润色可读 `report/<baseline_run>/briefing.polished.md`；其余旧 run 的读取照旧拒绝；底稿规则不变 |
| 停止原因 | 加 `no_change`：前台告诉客户报告不变，附上预览卡的要点 |
| 任务说明 | 改版时追加 `Mode: revise against run <baseline_run>; see report/<run_id>/impact.json` |

### 9.9 不变式与自检

每条都由程序检查，不靠模型自觉。

| 不变式 | 检查 |
|---|---|
| 新草稿里的每个数都能在本轮产物、交接包或已登记的工具输出里找到 | `report_check(draft)` 全文核数，沿用的段落也核 |
| `stale` 里的句子在新草稿里都改了 | `report_check` 比对：这些片段不得原样出现 |
| `sections` 里的章节确实改了，版本说明只引 `impact.json` 的内容 | `report_check` 比对基线草稿 |
| 结构名字与基线一致 | 出处表的 `kind: name` 条目与基线逐项比对，签名相同则名字相同 |
| 搬过来的成稿章节逐字未变 | `report_check(polished)` |
| 预览卡和交付说明里的数都在对应产物里 | 宿主数字检查 |
| 改版不能连续超过 3 版 | `impact` 读 `revise_chain` |
| 对齐只按结构签名 | `diff`、`impact`、`card` 共用同一个签名函数，并有测试 |
| 出报告的条件 1、2 程序可复算 | `card` 输出 `triggers` 的理由，测试覆盖 |

### 9.10 先要修的现有问题

1. `optimize.py diff` 按 cand_id 和 branch_id 对齐，id 一重排就把不同结构当成同一个，名次变化全错。改为按结构签名对齐；分支按签名加 `answers_assumed` 对齐。
2. 出处表的 `ref` 只写到产物文件，没有字段。过期判定因此改用“基线里有、本轮没有的数值”，不依赖 `ref`。`ref` 本身不改格式，程序只把旧 run_id 换成新的。
3. `delivered` 之后的 `[Host]` 消息，要带上运行期间客户的新消息（§9.7）。

### 9.11 预计用时

| 情形 | 用时 |
|---|---|
| 每条反馈到预览卡 | 1~2 分钟，前台一个回合加 6 秒优化 |
| 改版报告 | 约 30~50 分钟：轻核 5、分析 15~30、复核 5~7、润色 3~5、终审 3 |
| 全写 | 同现在，约 2 小时 |
| `none` | 1 分钟内 |

### 9.12 实现时要改的文件

`optimization/tools/optimize.py`（签名对齐的 `diff`、`card` 子命令）及优化层两份规范和 MCP 规范；`agent/tools/orchestrate.py`（`impact` 节点、模式、`no_change`、改版任务说明）；`agent/tools/case_server.py`（快照、`rounds.json` 新字段、运行中拒写、`report_check` 的改版检查、`kind: name`）；`agent/tools/guard_hook.py`（基线读取）；`apps/api/server.py`（预览卡的数字检查、条件触发、运行期间的消息）；前台、分析、润色、复核四份规范和案卷规范，各带英文副本；`make_agents.py` 重新生成提示词。

### 9.12a 试验实现与上文的出入

| 设计 | 实现 |
|---|---|
| 预览卡由优化层新子命令 `card` 生成 | 由 `agent/tools/impact.py` 生成，和 `impact` 共用结构签名；同样只读产物、只按规则算 |
| 预览产物放 `intake/preview/` | 放 `intake/products/<run_id>/`，不登记；同一天正式运行得到同一个 run_id，直接沿用 |
| 运行中来的反馈先记下，结束后再落 | 宿主在运行中拒收客户消息（409），页面提示等运行结束 |
| `rounds.json` 加四个字段 | 记在每轮的 `report/<run_id>/impact.json`：`baseline_run`、`level`、`revise_chain`、`spec_sha`，以及当时的 facts、answers、constraints；连续改版数从各轮的 impact.json 数出 |
| 交接包快照 `intake/reviewed/round-N/` | 沿用 `log/reviewed/review_intake/`，加 `documents.txt` 记单据清单 |
| 预览卡何时出 | 宿主在每个前台回合后检查：有基线版、没有运行在跑、`intake_check` 干净、运行输入和答案的哈希比上次预览变了；满足就算卡，再起一个前台回合转告 |

### 9.13 和目标的关系

`目标.md` §4.2 第 6 条写的是“新开一轮……整体重跑……出新报告”。本设计保留了整体重跑优化和两轮差异的对比，但改了两处：反馈先累积再出报告，报告可以在上一版上改。这一条要在用户同意后同步修改；修改前本设计不实现。

## 10. 分节起草（2026-11-03）

为什么：一次完整分析要 87 分钟，大部分是模型在输出：17.2 万个输出 token，其中出处表（约 4.6 万字符）整张发了三次。所以把草稿拆开：程序能写的程序写，各部分同时写，任何东西都不整份重发。

| 步骤 | 谁 | 做什么 |
|---|---|---|
| 框架 | 程序（`agent/tools/sections.py` build_frame） | `report/<run_id>/frame/`：names.json（报告讨论的结构，按 cand_id，带签名和白话标签；沿用上一版交付报告的名字，新结构取下一个空字母，现状叫 "Current structure"）、blocks/*.md（分步税负比较、情景表、待确认点、被否后的暴露额、缺口）、blocks.sources.json、frame.md（给写作者读的） |
| 分节写作 | 分析身份，并行 | 分组：第 2 部分；第 3 + 5 部分；第 4 + 6 部分；第 7 部分 + 附录 A。各用 `write_section` 写 `report/<run_id>/sections/<部分>.md` 和 `<部分>.sources.json`；表格用标记 `{{block:<名>}}` 插入 |
| 拼装 | 程序（assemble） | 按顺序把各部分拼成 briefing.md 和 briefing.sources.json，标记换成表格并带上表格的出处，每个提到的结构一条 kind 为 name 的出处，附录 B 按 cite / url / document 出处生成，加内部编号行 |
| 统稿 | 分析身份，一次 | 先写 precommit；再写抬头和开头的假设声明（section head）与第 1 部分；然后用 `edit_section` / `write_section` 使各部分一致；最后跑 report_check。拼装后的每次写入都会重新拼装 |
| 复核退回 | 分析身份，一次 | 照旧，但改在各部分上：`edit_section` / `write_section` |

规则：分节的草稿拒绝用 `write_report` 写整份 briefing，也拒绝非追加方式写出处表（额外的出处进 sections/extra.sources.json）。附录 B 和编号行归程序。改版（§9）只跑 impact.json 列到的部分所在的分组；其余部分由程序从上一版交付的草稿沿用，连同出处，产物引用在本轮有同名文件时改指本轮；变化说明由统稿写。某个写作者失败，它的部分就缺着，统稿会被告知要补写。产物没有 brief.json（旧 run、测试）时退回由一个 agent 写整份。orchestrate.py 的 `SECTIONED` 可整体关掉这一机制。

## 11. 阅读与检索的接入（2026-11-03）

检索层的设计见 `agent/检索规范.md`。编排器为它做四件事，全是程序步骤：

| 时机 | 做什么 |
|---|---|
| 优化器 run 结束、run 登记之后（以及预览卡的 run） | 建这个 run 的产物索引 `intake/products/<run_id>/index/records.sqlite` |
| review_intake 开始前 | 建案卷索引并对扫描单据做一次 OCR（按文件哈希缓存，`intake/index/`） |
| review_intake、analysis、review_draft、review_final（以及 polish，§12）开始前 | 写预取包 `report/<run_id>/pack/<节点>.md`（还没有 run 时写在 `intake/index/pack/`），任务文本里写包的路径和案卷的文件清单 |
| 交付检查 | report_check 对草稿跑 cite_check |

任何一步失败只记一行日志，不让节点失败：agent 仍可用 tax-read 自己找。

## 12. 法律理由一路与再核范围（2026-11-03）

review_draft 和 review_final 各自同时跑两个复核 agent：主复核（复核规范第二、三段）和法律理由一路（第四段，`agent/复核Agent规范.md` §3a）。原因：CASE-20261102-a032c0 第 3 轮的复核三次放过了一句把新加坡税率门槛说错的话；逐句核对理由和条文，与核对数字和产物是两件事。

| 步骤 | 程序做什么 |
|---|---|
| 节点开始前 | 给这个 run 打标记（`report/<run_id>/.lanes`），此后这一段要两张核对单都通过才算过；用 `agent/tools/reasons.py` 写这一路的材料（`pack/legal_draft.md` 或 `pack/legal_polished.md`）：讲法律理由的句子，以及它们的出处行、句子里用文字写出的条文引用（程序解析，含同段回指）、条文（门槛和条件先给全文，超长才截短）、带参数值的规则和决定；推荐结构有利分支用到的全部条文也预先放进去，复核线先在这里找，找不到才自己检索（2026-11-04 提速） |
| 哪些句子 | review_draft 在本 run 的初核：全部；再核：同一 run 上次核对之后改动的行上的句子；review_final：润色稿里与草稿不逐字相同的句子 |
| 无可核时 | 材料为空、且上一张这一路的核对单是通过的（或者没有可再核的），程序直接写一张通过的核对单，这一路不跑 |
| 节点进行中 | 这一路在线程里与主复核并行（log/runs/ 里记为 `review_legal`、`review_final_legal`）；它的轮数和秒数记进节点那一行（`lane_turns`、`lane_seconds`） |
| 节点结束后 | 这一路失败或什么都没写，节点算失败。任一张核对单写 REVISE 时，退得最远的去向优先（front，其次 analysis，再次 polish），作者的任务里列出所有退回它的核对单 |

再核范围：只有上一张核对单是本轮同一个 run 的（`log/reviewed/<节点>/run.txt`），且差异不到文件的 60%，复核节点才会被告知"这是再核"；否则按新稿初核。（第 3 轮的第一次草稿复核拿到的是对另一个 run 草稿的 64,000 字符差异，把新稿当成了再核。）

润色预取包：润色开始前，程序写 `pack/polish.md`：它要用的文件、草稿里 `{{block:<名>}}` 标记所代表的程序表格、report_check 对润色稿检什么、流程图的格式，免得润色去读系统代码（第 3 轮：19 次 Read、16 次 Grep，大多读的是 case_server.py 和 render_pdf.py）。report_check 比较润色稿和草稿的数字前，先把标记展开。

润色增量（2026-11-05）：润色节点成功后，程序把它所依据的草稿和出处表存进 `log/polished/`（带 `run.txt`）。同一 run 的草稿之后又被分析改过时，下一次润色的任务附上差异文件 `log/polish_changes.md`，润色只用 `edit_polished` 把改动搬进成稿，改过的出处行用 append 发，不重写全文；没有同一 run 的成稿、草稿没变（终审退回润色）、或差异超过文件的 60% 时照常润色。原因：试验案卷 CASE-20261104-7e57a1 的 run 20261104-d2239ced 中，分析只改了一句，润色仍按节重写全文，用了 6.2 分钟；终审退回润色那一次只用 edit_polished，1.2 分钟。

## 13. 取消润色与终审（2026-11-06）

试验（CASE-20261105-a7e298 GPT 端到端、CASE-20261106-3694b3 qwen 端到端）表明润色和终审占了交付时间的一半（81 + 71 分钟），而终审退回的都是润色自己删坏的内容。改为：

| 环节 | 现在 |
|---|---|
| 图 | `review_intake → run → analysis → review_draft（+ review_legal）→ render → delivered`；`polish`、`review_final`、`review_final_legal` 节点取消，`LEGAL` 相应缩减 |
| 分析 | 直接写交给客户的报告（规范 §3、§5 第 11 条）；写完自己调 `render_pdf`（分析身份可用）看页数 |
| 自检 | `self_check` 先调 `autofix_draft`：指向 bug 或底稿文件的出处行由程序丢弃并记日志；`report_check(target=draft)` 加查流程图块、口语标签、优化层用语、长句、以及 PDF 是否最新和正文页数 |
| 复核 | 草稿核对加第八类"客户可读"；法律线只有草稿一路；核对单通过记号 `DELIVERABLE`（旧的 `POLISHABLE` 仍按通过读） |
| 照单改 | 核对单可带 ```replacements 块（`[{"old", "new"}]`）；`render` 节点先由程序 `apply_replacements` 改进草稿并重盖核对单时间，再排版；改不上的（原句找不到或不唯一）退回分析 |
| 程序把关 | `write_review` 拒收：没有任何问题条目的 REVISE；再核时只引用未改动行且上次未退回的 REVISE；`replacements` 块不是合法 JSON 列表。`bug_append` 的 `affects_result=true` 必须带 `effect`（本案哪个数从多少变成多少） |
| 退回任务 | 分析的退回任务里附上核对单的逐条位置、问题、证据、建议（上限 6,000 字符），照改即可 |
| render 节点 | 程序步：应用替换 → `client_copy`（展开 `{{block:...}}`、删去含案号或 run_id 的行，写成 `briefing.polished.md` 供宿主与旧读者）→ `render_pdf` → 带新 PDF 再 `report_check`；排版失败停 `agent_failed`，检查失败退回分析 |
| 状态 | `reviewed`：复核两线通过；`delivered`：`briefing.pdf` 比草稿和核对单都新。`polished` 状态不再出现；旧案卷按原规则读 |
| 宿主 | 进度面板的节点表改为 `intake、review_intake、run、analysis、review_draft、render`；交付后的转述仍读 `briefing.polished.md` 的第 1 部分 |

`make_agents.py` 不再生成润色 agent；复核的 prompt 由三段组成（交接包、草稿、法律线）。
