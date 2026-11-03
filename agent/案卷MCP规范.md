# 案卷 MCP 规范（tax-case，最小集）

2026-11-01。四个 MCP 服务之一（另三个：`database/数据库MCP规范.md`、`rule/规则层MCP规范.md`、`optimization/优化层MCP规范.md`；本文只定案卷服务）。案卷服务是四个 Agent 对 `cases/<case_id>/` 的**唯一写入口**；读不经它——宿主自带的 Read（文件、PDF 按页、图片）、Glob、Grep 比服务做得好，直接用。写权限按 Agent 身份在服务里硬编码，读权限靠宿主的子 Agent 工具白名单加一个 PreToolUse 守卫钩子（`agent/tools/guard_hook.py`，按钩子输入里的 `agent_type` 判）。联网不建服务，用宿主自带的搜索与抓取，策略写在三份 Agent 规范的 prompt 里。调用日志也不由服务记，由宿主的 PostToolUse 钩子记（§5）。

**语言**：本规范用中文，供人阅读；英文副本 `agent/case_mcp_spec.en.md`，两者不一致时以中文版为准，改中文版时同步改英文副本。AI 写进文件的一切自写文字用英文——代码、注释、工具说明、prompt（系统实际递交的是英文副本里的那段）、底稿、核对单、handoff、bug 反馈、日志、产物字段；原件、条文、引文、客户原话保持原文，不翻译。唯一例外是给客户看的文字（对客户的回话、briefing）跟客户的语言。核对单的总判断用英文记号：交接包 `RUNNABLE` / `REVISE`，草稿 `POLISHABLE` / `REVISE`，成稿 `DELIVERABLE` / `REVISE`。

## 1. 定位

- 一个案子一个目录 `cases/<case_id>/`，四块：`intake/`（前台交接包）、`report/<run_id>/`（分析草稿、润色稿、PDF、复核单）、`notes/<agent>/round-N/`（底稿）、`bugs/<agent>.md`（bug 反馈）。
- 服务启动时带两个参数：`--root cases` 和 `--agent front|analysis|polish|review`。同一份代码起四个进程，各一个身份；每个子 Agent 的工具白名单只挂自己身份的那个，所以拿不到别的身份。
- 服务做四件事：带语义的写（追加不覆盖、.prev、JSON 校验、总判断末句校验）、账本（round、run_id、状态推导）、两个只读自检、润色身份的 PDF 渲染（`render_pdf` 子进程调 `agent/tools/render_pdf.py`，固定模板，服务本身不做排版判断）。不做读、不做日志、不做税务判断、不调另外三层；优化层 `run` 的产物由 `tax-opt` 直接写进 `intake/products/<run_id>/`，案卷服务只登记 run_id。
- 路径约定与另三个服务一致：凡是路径参数，一律相对 `cases/` 根（即带 case_id）。工具的 `case_id` 参数显式传。

## 2. 目录与账本

```
cases/<case_id>/
  rounds.json                 账本：当前 round、每轮的 run_id、修订号；状态从文件推出
  log/calls.jsonl             调用日志：宿主钩子写（§5），服务不碰
  log/runs.jsonl  log/runs/  log/run.lock   运行记录、CLI 原始输出、运行锁：编排器写
  intake/
    prompt.md  dialogue.md  documents/
    facts.json  sources.json  answers.json  notes.md  constraints.json
    handoff.md  to_collect.md  review_intake.md
    products/<run_id>/
  report/<run_id>/
    briefing.md  briefing.sources.json                    分析草稿（润色不覆盖）
    briefing.polished.md  briefing.polished.sources.json  润色稿（客户看的）
    briefing.pdf                                          润色出的 PDF
    review.md  review_final.md                            复核第二、三段的核对单
  notes/front/round-N/  notes/analysis/round-N/  notes/polish/round-N/  notes/review/round-N/
  bugs/front.md  bugs/analysis.md  bugs/polish.md  bugs/review.md
```

`rounds.json`：`{"current": N, "rounds": [{"round": N, "revision": k, "run_id": "...|null", "opened": 日期, "intake_dirty": bool}]}`。由服务维护，Agent 只能通过 `case_new` / `round_new` / `round_revise` / `round_set_run` 改；读它用 Read。

状态不存、不手改，`round_current` 现场从文件推出：

| 状态 | 判定 |
|---|---|
| intake | 本轮无 run_id，且不满足 intake_ok；或本轮已有 run_id，但交接包在上次接收复核之后又被写过（要重新复核、重新计算） |
| intake_ok | review_intake.md 末句 `RUNNABLE` 且写入晚于最后一次 facts / sources / answers / notes / constraints 写入；本轮已有 run_id 时，还要晚于登记它的时间（`run_registered`），这时旧产物作废 |
| ran | 有 run_id，`briefing.md` 不存在 |
| drafted | `briefing.md` 存在，`review.md` 不存在、旧于草稿或末句不是 `POLISHABLE`（草稿以 `briefing.md` 和出处表中较新者为准） |
| reviewed | `review.md` 末句 `POLISHABLE` 且不旧于草稿，成稿不存在或旧于 `review.md` |
| polished | 成稿新于 `review.md`，`review_final.md` 不存在、旧于成稿或末句不是 `DELIVERABLE`（成稿以 `briefing.polished.md`、出处表和 PDF 中最新者为准） |
| delivered | `review_final.md` 末句 `DELIVERABLE` 且不旧于成稿 |

这张表同时是编排器的决策依据（见 `编排CLI规范.md`）。`round_current` 另返回 `return_to`：当前状态正在等的 `REVISE` 核对单，形如 `{which, to, path}`，没有时为空。

## 3. 权限

**写**（服务强制，按 `--agent`）

| 路径 | front | analysis | polish | review |
|---|---|---|---|---|
| `intake/` 的 facts、sources、answers、notes、constraints、handoff | 写（留 .prev） | — | — | — |
| `intake/documents/`、`prompt.md` | 放入（首轮） | — | — | — |
| `intake/dialogue.md` | 追加 | — | — | — |
| `intake/to_collect.md` | 追加 | 追加 | — | — |
| `intake/review_intake.md` | — | — | — | 写（留 .prev） |
| `report/<run_id>/briefing.md`、`briefing.sources.json` | — | 写（留 .prev） | — | — |
| `report/<run_id>/briefing.polished.md`、`.polished.sources.json`、`briefing.pdf` | — | — | 写 / 出（留 .prev） | — |
| `report/<run_id>/review.md`、`review_final.md` | — | — | — | 写（留 .prev） |
| `notes/<own>/round-N/` | 追加 | 追加 | 追加 | 追加 |
| `bugs/<own>.md` | 追加 | 追加 | 追加 | 追加 |
| `rounds.json` | 经 case_new / round_* | — | — | — |
| 其余 | 拒绝 | 拒绝 | 拒绝 | 拒绝 |

"追加"= 只能在文件末尾加条目，服务比对现有内容是前缀才写；"写"= 整文件覆盖，上一版留 `<文件>.prev`（只保留一版，供复核"只核改动处"；暂不提供 diff 工具，复核自己比）。

**读**（宿主强制：子 Agent 定义不支持按身份的路径拒绝，所以用 PreToolUse 钩子 `guard_hook.py` 实现——它只在钩子输入带 `agent_type` ∈ front / analysis / polish / review 时动作，按下表拒绝并给出理由；另外拒绝这四个身份对 `cases/` 下任何 Edit / Write，以及没有 path 或 path 在 case 根及以上的 Grep / Glob）

| 读什么 | front | analysis | polish | review |
|---|---|---|---|---|
| `intake/`、`report/`、`rounds.json` | 可 | 可（旧 run 的 `report/`、`intake/products/` 拒绝；新旧差别只读当前产物的 diff.json） | 可（旧 run 的 `report/`、`intake/products/` 拒绝；润色只读本轮草稿、出处表、handoff，不读产物） | 可 |
| `notes/<own>/round-<当前>/` | 可 | 可 | 可 | 可 |
| `notes/<own>/round-<旧>/`、`notes/<other>/` | 拒绝 | 拒绝 | 拒绝 | `notes/analysis/round-<当前>/` 在本轮 review.md 写出后可读（时间先后靠复核规范约束）；其余拒绝 |
| `bugs/<own>.md` | 可 | 可 | 可 | 可 |
| `log/calls.jsonl` | — | — | — | 本轮 review.md 写出后可读 |

守卫钩子从 `rounds.json` 读当前 round 与 run_id 判"旧轮"、"旧 run"，从 `report/<run>/review.md` 是否存在判复核是否已出单。宿主的 `permissions.deny` 是会话级的，不按子 Agent 分，所以不用它。

## 4. 工具

全部工具显式传 `case_id`。返回 JSON；出错返回 `{"error": 类型, "detail": 说明, "path": 涉及路径}`，类型只有 `forbidden`（身份不允许）、`not_found`、`conflict`（覆盖追加文件、账本状态不对、目录已存在）、`invalid`（JSON 不合法、字段缺、末句不合法）。

**写（按身份）**

| 工具 | 身份 | 参数 |
|---|---|---|
| `write_intake` | front | case_id, name ∈ {facts, sources, answers, notes, constraints, handoff}, content → 覆盖写，留 .prev；facts / sources / answers / constraints 必须是合法 JSON，sources 每条必含 key, doc, page, quote；写 handoff 以外的文件后账本 intake_dirty = true |
| `put_document` | front | case_id, name, bytes → 放进 `intake/documents/`；`name = prompt` 写 `intake/prompt.md` |
| `dialogue_append` | front | case_id, speaker ∈ {client, front}, text → 追加 `### 日期 \| round N.k \| speaker`，返回条目号 |
| `to_collect_append` | front, analysis | case_id, law, jur, url, why → 追加一条 |
| `write_report` | analysis | case_id, run_id, name ∈ {briefing, sources}, content, mode? → 写 `briefing.md` / `briefing.sources.json`；run_id 必须是本轮账本里的；mode=append 给草稿追加一节，或给出处表按 id 增改 |
| `edit_report`、`edit_polished` | analysis、polish | case_id, run_id, edits[{old, new}] → 改草稿或润色稿的句子；每段 old 必须恰好出现一次，全部成立才写 |
| `write_polished` | polish | case_id, run_id, name ∈ {polished, sources}, content, mode? → mode=append 时出处表按 id 增改； 写 `briefing.polished.md` / `briefing.polished.sources.json`；`briefing.polished.sources.json` 只提交保留条目的 id 和 where，claim、kind、ref 由服务从草稿复制，不能新增条目；草稿 briefing.md 原样保留；草稿未通过复核时 `conflict` |
| `render_pdf` | polish | case_id, run_id → 先跑文字检查（`report_check` text_only），有问题就不渲染；用固定模板（`agent/tools/render_pdf.py`）把润色稿排成 `briefing.pdf`，返回总页数、附录之前的正文页数（应为 5 到 10 页）、各节和流程图所在页、每页填充比例、latex_errors 和 overfull；流程图用 flow 代码块的 JSON 由模板绘制 |
| `write_review` | review | case_id, which ∈ {intake, draft, final}, content, run_id? → `review_intake.md`、`report/<run_id>/review.md` 或 `review_final.md`；末句必须是该段的总判断（`RUNNABLE` / `REVISE`；`POLISHABLE` / `REVISE`；`DELIVERABLE` / `REVISE`），draft 和 final 的 `REVISE` 在末句之前要有 `RETURN: <去向>` 行（draft 可写 analysis、front；final 可写 polish、analysis、front），否则 `invalid`；被核对的文件不存在时 `conflict` |
| `notes_append` | 本人 | case_id, book, text → `notes/<agent>/round-N/<book>.md` 追加，自动写条目头 `### <book>-<n> \| 日期 \| round N.k \| run_id`，返回编号；book 限本 Agent 规范里的那几本 |
| `bug_append` | 本人 | case_id, layer, symptom, expected, repro, workaround, affects_result? → affects_result 为真时写入标记（只认分析和复核的 bug），运行在清除前停在 `system_defect`（`clear_defect` 写 `bugs/cleared.md`，只由编排器 CLI 调用）；先在本人 bugs 文件里按 symptom 查重，重复则在原条下追加 `再现 round N`，否则新条 `### B-<n>` |

**账本（front）**

| 工具 | 说明 |
|---|---|
| `case_new` | case_id → 建 `cases/<case_id>/` 全部子目录、空 rounds.json（current = 1）、四个 `notes/*/round-1/`；已存在则 `conflict` |
| `round_new` | case_id → current + 1，建四个 `notes/*/round-N/`；要求状态是 delivered，或报告阶段的核对单写着 `RETURN: front` |
| `round_revise` | case_id → 修订号 + 1（复核退回后改完再交） |
| `round_set_run` | case_id, run_id → 登记到当前轮；要求推出的状态是 intake_ok，且 `intake/products/<run_id>/version.json` 存在；登记后 intake_dirty 清零 |

**状态与自检（任何身份，只读）**

| 工具 | 返回 |
|---|---|
| `round_current` | case_id → 账本当前条目加推出的状态（§2 表）和 `return_to` |
| `review_status` | case_id, which ∈ {intake, draft, final} → 对应核对单的总判断、退回去向与写入时间；不存在返回 `none` |
| `intake_check` | case_id → 列表：facts.json 能被优化层读入（调 `tax-opt` 的 `validate_input`）；不带 answers，有 instructed_on，past_payments 每行有 date、payee_share；answers.json 的键都是谓词；sources 覆盖 facts 每个键且每条有 doc + page + quote；answers 的 yes / no / unknown_asked 都有原话且原话在 dialogue.md 里；confirmed_by_client 为真的有 confirmed_note；推出的状态是否 intake_ok |
| `report_check` | case_id, run_id, target ∈ {auto, draft, polished}（auto = 有润色稿就核润色稿）→ 列表：抬头日期等于 instructed_on；past_payments 的可退金额和对不上的数字在报告里；润色稿正文没有优化层用语、没有超过 55 词的句子；报告头、一到七节、附录 A / B 都在；无系统标识；出处表每条有 where、ref 存在（产物路径可打开；cite_id 用 `tax-db` 的 `clause` 查）；核润色稿时额外报：`number_drift`（润色稿里草稿没有的数字）、`claims_changed`、`where_unlocated`、口语标签、案号或 run_id 留在成稿里、PDF 过期或正文不在 5 到 10 页之间；`numbers_omitted` 和 `sources_cut` 只列出被删内容，不算问题 |

自检只报不改，结果是列表，Agent 自己决定怎么办；复核仍按自己的规范逐条核，不以自检通过为准。两个自检是服务里唯一调用另两个服务的地方（import 它们的读函数，不经 MCP）。

## 5. 日志（宿主钩子，不在服务里）

- `.claude/settings.json` 配一个 PostToolUse 钩子，matcher 为空（所有工具，含 Read 和各 MCP），命令是 `agent/tools/log_hook.py`：读 stdin 的 JSON，从 `tool_input` 里出现的第一个 `cases/<case_id>/` 路径或 `case_id` 参数推出 case_id，追加一行到 `cases/<case_id>/log/calls.jsonl`：`{time, session_id, agent, tool, input_summary}`；推不出 case_id 的记 `cases/_log/calls.jsonl`。`agent` 取钩子输入的 `agent_type`（宿主在子 Agent 内触发钩子时给出），没有就从工具名前缀（`mcp__tax-case-<agent>__`）推，再没有记 `unknown`。`input_summary` 只留路径、name、book、run_id 等键，不留正文。
- 这样记的好处是覆盖宿主的 Read：Agent 直接 Read 了 `ranking.json` 也在日志里，服务端日志做不到。
- 复核在本轮 review.md 写出后读 `log/calls.jsonl`，核一件事：分析的 `notes_append(book = precommit)` 时间早于它第一次读 ranking / deltas（`tax-opt` 的 `ranking` / `deltas`，或 Read `…/ranking.json`）。不早的，在核对单补一条"存疑：预判晚于看结果"。这是预登记唯一的客观核法。

## 6. 隔离规则（服务强制的部分）

1. 身份外的写一律 `forbidden`。
2. `dialogue.md`、`notes/*`、`bugs/*`、`to_collect.md` 只追加；服务比对文件现有内容是前缀才写入。
3. `notes_append` 只写当前 round 的目录；非当前 round 一律 `forbidden`。
4. 写 handoff 以外的交接包文件后标 `intake_dirty = true`；`round_set_run` 要求推出的状态为 intake_ok，否则 `conflict`。这是"可跑才能 run"的机器保证。
5. `write_report` 的 run_id 必须是当前轮登记的；`write_review(draft / final)` 的 run_id 同。
6. `write_polished` 要求草稿已通过复核。这是"先复核再润色"的机器保证。

读的隔离（分析不读旧轮、复核出单前不读分析底稿、谁都不读别人的底稿）由宿主权限规则承担，见 §3。

## 7. 身份绑定与配置

- `.mcp.json` 是项目级的总表；编排器和前台入口只给每个 Agent 连自己的服务（`make_agents.py` 生成的 `.claude/mcp/<name>.json`，配 `--strict-mcp-config`），隔离靠这份清单和子 Agent 定义的工具白名单：前台挂 `tax-case-front`、`tax-db`、`tax-rule`、`tax-opt-front`；分析挂 `tax-case-analysis`、`tax-db`、`tax-rule`、`tax-opt`；复核挂 `tax-case-review`、`tax-db`、`tax-rule`、`tax-opt`；润色只挂 `tax-case-polish`、`tax-db`。四者都挂 Read、Glob、Grep，前台、分析、复核另挂 WebSearch、WebFetch；Bash 只给前台（放单据、起 run 之外基本用不到），且分析、复核的 deny 里加 `Bash(*optimize.py run*)` 作第二道保险。
- 跨服务同名工具（`requirements`、`version`、`diff`）宿主会按服务名加前缀，不冲突；Agent 规范提到时写"规则层的 requirements"、"优化层的 diff"。

```json
{
  "mcpServers": {
    "tax-case-front":    {"command": "C:/Coding/Anaconda/envs/tax/python.exe", "args": ["agent/tools/case_server.py", "--root", "cases", "--agent", "front"]},
    "tax-case-analysis": {"command": "C:/Coding/Anaconda/envs/tax/python.exe", "args": ["agent/tools/case_server.py", "--root", "cases", "--agent", "analysis"]},
    "tax-case-polish":   {"command": "C:/Coding/Anaconda/envs/tax/python.exe", "args": ["agent/tools/case_server.py", "--root", "cases", "--agent", "polish"]},
    "tax-case-review":   {"command": "C:/Coding/Anaconda/envs/tax/python.exe", "args": ["agent/tools/case_server.py", "--root", "cases", "--agent", "review"]},
    "tax-db":            {"command": "C:/Coding/Anaconda/envs/tax/python.exe", "args": ["database/tools/mcp_server.py", "--root", "database"]},
    "tax-rule":          {"command": "C:/Coding/Anaconda/envs/tax/python.exe", "args": ["rule/tools/mcp_server.py", "--root", "rule", "--db", "database", "--cases", "cases"]},
    "tax-opt-front":     {"command": "C:/Coding/Anaconda/envs/tax/python.exe", "args": ["optimization/tools/mcp_server.py", "--root", "optimization", "--rule", "rule", "--db", "database", "--products-root", "cases", "--role", "front"]},
    "tax-opt":           {"command": "C:/Coding/Anaconda/envs/tax/python.exe", "args": ["optimization/tools/mcp_server.py", "--root", "optimization", "--rule", "rule", "--db", "database", "--products-root", "cases", "--role", "reader"]}
  }
}
```

- 环境：四个服务同一个 Python（`tax`），`conda activate tax` 后 `pip install "mcp[cli]"`（2026-11-01 查过还没装）；`<tax env python>` 填该环境的解释器路径。
- 文件 `agent/tools/case_server.py`，依赖只有 `mcp` 和标准库；自检 import `optimization/tools/optimize.py` 与 `database/tools/mcp_server.py` 的读函数。
- 四个子 Agent 定义由 `agent/tools/make_agents.py` 从四份 Agent 规范的 ```text prompt 块生成到 `.claude/agents/<front|analysis|polish|review>.md`（frontmatter：name、description、tools 白名单、model: inherit；复核的 body 含三段 prompt，由编排器的任务说明指定用哪段）。它同时生成 `.claude/agents.json`，供无头调用的 `--agents` 使用。改了规范就重跑它，不手改生成文件。
- 钩子在 `.claude/settings.json`：PreToolUse（matcher `Read|Grep|Glob|Edit|Write|MultiEdit|NotebookEdit` → guard_hook.py）和 PostToolUse（matcher 空 → log_hook.py），exec 形式，命令是 `tax` 环境解释器的绝对路径，脚本路径用 `${CLAUDE_PROJECT_DIR}`。
- 测试（构建的一部分，不是测试批）：`agent/tools/test_case_server.py` 起四个身份对一个临时 case 跑一遍写权限表（每格一个断言）、追加文件的前缀检查、状态推导的六种情形、"可跑才能 run"的 conflict、末句校验的 invalid；`log_hook.py` 用一段伪造的钩子输入测 case_id 与 agent 的推断；`guard_hook.py` 对一棵合成的 case 树跑 21 种读写情形（见构建记录）。

**构建记录（2026-11-01）**：case_server、log_hook、guard_hook、make_agents、`.mcp.json`、`.claude/settings.json`、三个子 Agent 定义都已建；test_case_server 52 项、守卫 21 项通过；三个身份的 stdio 握手实测通过。状态推导的一处修正：intake_ok 看 `review_intake_written` 严格晚于 `last_intake_write`（微秒级时间戳），复核写入后 intake_dirty 清零。

**构建记录（2026-11-01 晚，加润色 Agent）**：第四个身份 polish 加入——流程改为分析写草稿（状态 drafted）→ 润色重写出 polished.md / polished.sources.json + PDF（状态 polished）→ 复核核润色稿（对比草稿确认结论和数字没变）→ delivered；状态按文件 mtime 推（草稿重写 → 回 drafted，润色重写 → 回 polished）。`write_polished`、`render_pdf`（子进程调 render_pdf.py，ctexart 模板；不用 `-halt-on-error`，否则一个未定义控制序列就把整份截成 1 页；flow 代码块的 JSON 由模板用 TikZ 按固定版式绘制流程图，润色不画图；其他代码块原样保留空格；支持编号列表、跨页长表）、report_check 加 target 和三项对账（`number_drift` 比两版正文全部数字，`claims_changed` 比两张出处表，`where_unlocated` 查片段逐字定位），系统自用语进 LEAKS。第一次实跑（qwen3.7-max，CASE-E2E-001）：10 页，数字一致，但 40 / 81 条 where 定位不到、正文留有规则工具和模型等词、散文 6,130 字超目标，尚未重跑。guard / log / make_agents / .mcp.json 加 polish；test_case_server 更新后通过。润色用 qwen3.7-max。

**构建记录（2026-11-01 深夜，改为先复核再润色）**：状态加 reviewed，复核分三段（`review.md` 核草稿，`review_final.md` 比对成稿），`RETURN` 行校验，`round_current` 返回 `return_to`，`round_new` 放宽，`write_polished` 要求草稿已通过，sources 和 notes 的写入也会让交接包回到待复核；中文总判断记号不再接受；`report_check` 能读英文报告的口语标签和过程性说明。编排器 `agent/tools/orchestrate.py` 见 `编排CLI规范.md`。

## 8. 不做

不做读（宿主 Read / Glob / Grep）；不做日志（宿主钩子）；不做搜索与联网；不做税务判断；不改另外三层的任何文件；不替 Agent 合并底稿；不给客户直接访问（客户界面是 UI 层的事）。
