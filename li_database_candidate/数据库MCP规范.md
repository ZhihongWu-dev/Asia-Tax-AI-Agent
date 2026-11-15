# 数据库 MCP 规范（tax-db，最小集）

2026-11-01。四个 MCP 服务之一（另三个：`rule/规则层MCP规范.md`、`optimization/优化层MCP规范.md`、`agent/案卷MCP规范.md`）。本文只定 `tax-db`：给 Agent 层的只读查询。库的表、采集、验收见 `数据库规范.md`；本文件和 `tools/mcp_server.py` 由采集方按 `数据库规范.md` §4.9 的规矩维护。

**语言**：本规范用中文，供人阅读；英文副本 `database/database_mcp_spec.en.md`，两者不一致时以中文版为准，改中文版时同步改英文副本。AI 写进文件的一切自写文字用英文——代码、注释、工具说明、prompt（系统实际递交的是英文副本里的那段）、底稿、核对单、handoff、bug 反馈、日志、产物字段；原件、条文、引文、客户原话保持原文，不翻译。唯一例外是给客户看的文字（对客户的回话、briefing）跟客户的语言。核对单的总判断用英文记号：交接包 `RUNNABLE` / `REVISE`，报告 `DELIVERABLE` / `REVISE`（服务也接受原来的中文记号）。

## 1. 定位

只读。读 doc、clause、param、treaty、jurisdiction、superseded、decision、blocked 八张表和 STATUS.md，不走 build / fetch / upload。Agent 要的是三件事：按词找条文、按 cite_id 取原句、按 param_id 取数和出处；其余工具都是围着这三件事的辅助（文档元数据、协定、币种、参数历史、口径、取不到的原文、库版本）。

Agent 发现库里缺的或过时的法规不经这里，走案卷服务的 `to_collect_append`，由采集方处理；库仍只收官方原文、过验收。

## 2. 工具

| 工具 | 参数 → 返回 |
|---|---|
| `find` | words[], jur?, doc?, max → 命中条文列表（cite_id、doc_id、label、含词句子、matched）：含词多的在前，再按 BM25；一个词查不到时拆成更短的词并列在 relaxed；每次查询记入 `cases/_log/find.jsonl` |
| `clause` | cite_id, offset?, max_chars? → 条文全文（clause.csv 的 text，长条文按 offset / max_chars 分段取）、doc_id、label、文档生效区间、前后各一条的 cite_id |
| `doc` | doc_id → doc.csv 整行：标题、法域、类型、类别、来源 URL、原件路径、语言、生效区间、note |
| `param` | param_id → param.csv 整行：值、单位、quote、cite_id、生效区间、note、changed_on、superseded_by |
| `params_for` | jur, slot?, subject? → 该法域该槽位的全部参数（含缺项记录） |
| `absent` | jur, slot? → 槽位缺项记录（该地该槽位没有这项税 / 待遇的登记） |
| `treaty` | jur_a, jur_b? → treaty.csv 该法域对的全部行（协定与议定书的 doc_id、条款、生效区间）；只给一个法域时列它的全部协定 |
| `jurisdictions` | 无 → jurisdiction.csv：代码、名称、币种、公司 / 个人是否在范围 |
| `param_history` | param_id → 沿 superseded_by 链的全部版本（值、生效区间、changed_on、note），加 superseded.csv 里涉及其 cite 的条 |
| `decision` | id? → decision.csv 一条或全部（库层口径） |
| `blocked` | 无 → blocked.csv：取不到原文的文档、原因、试过的替代 |
| `version` | 无 → STATUS.md 摘要：构建时间、各法域 PASSED 状态、表行数 |

返回里的 quote、text 一律原文逐字，不翻译、不改写、不截断（`clause` 的分段除外，分段返回带 `total_chars` 与 `offset`）。

## 3. 约定（四个服务一致）

- Python `mcp` 包的 FastMCP，stdio 传输；直接读 csv，不起子进程。
- `--root`（database/）在服务配置里定死，Agent 不传。
- 每个返回带 `version`（库构建时间与各法域状态），供报告的 sources.json 引用。
- 错误结构化返回 `{error: invalid | not_found | internal, detail}`。
- 调用日志不由服务记：宿主的 PostToolUse 钩子统一记到 `cases/<case_id>/log/calls.jsonl`（见 `agent/案卷MCP规范.md` §5），服务不碰日志。
- 跨服务同名工具（`requirements`、`version`、`diff`）由宿主按服务名加前缀，不冲突；Agent 规范提到时带服务名。

## 4. 身份与权限

没有写工具，不区分身份，一个进程三个 Agent 共用；隔离由各子 Agent 的工具白名单管（案卷规范 §7）。

## 5. 实现

- 文件 `database/tools/mcp_server.py`；依赖 `mcp` 和标准库（csv 读取与 find.py 现有函数）。启动参数：`--root database`。
- `.mcp.json` 片段：

```json
"tax-db": {"command": "<tax 环境的 python>", "args": ["database/tools/mcp_server.py", "--root", "database"]}
```

- 启动时把八张表读进内存；库重建后重启服务。不做增量、不做索引以外的加工。

**构建记录（2026-11-01）**：`database/tools/mcp_server.py` 与 `test_mcp_server.py` 已建，18 项检查通过（param_history 的链式一项因库里尚无 superseded 参数而跳过）。stdio 握手、tools/list、tools/call 实测通过。

## 6. 测试（构建的一部分）

`database/tools/test_mcp_server.py`：每个工具一条——`find` 用一个已知词命中已知 cite_id；`clause` 返回的 text 与 clause.csv 逐字相同，分段拼回后相同；`param` 的 quote 是 `clause(cite_id)` text 的子串；`treaty` 对 cn–hk 返回非空；`param_history` 对一个有 superseded_by 的参数返回两版；`version` 与 STATUS.md 一致。

## 7. 不做

不写库、不抓取、不上传；不做语义检索（find 是词匹配加 BM25 排序，语义检索等查询日志说明确有需要再议）；不翻译、不摘要条文；不替 Agent 判断哪条适用。
