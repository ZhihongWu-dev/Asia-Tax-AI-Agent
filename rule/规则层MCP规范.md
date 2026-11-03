# 规则层 MCP 规范（tax-rule，最小集）

2026-11-01。四个 MCP 服务之一（另三个：`database/数据库MCP规范.md`、`optimization/优化层MCP规范.md`、`agent/案卷MCP规范.md`）。本文只定 `tax-rule`：给 Agent 层用的服务化接口，包装规则层现有函数，不加新语义。规则层本身的表、求值语义、函数集见 `规则层规范.md`。

**语言**：本规范用中文，供人阅读；英文副本 `rule/rule_mcp_spec.en.md`，两者不一致时以中文版为准，改中文版时同步改英文副本。AI 写进文件的一切自写文字用英文——代码、注释、工具说明、prompt（系统实际递交的是英文副本里的那段）、底稿、核对单、handoff、bug 反馈、日志、产物字段；原件、条文、引文、客户原话保持原文，不翻译。唯一例外是给客户看的文字（对客户的回话、briefing）跟客户的语言。核对单的总判断用英文记号：交接包 `RUNNABLE` / `REVISE`，报告 `DELIVERABLE` / `REVISE`（服务也接受原来的中文记号）。

## 1. 定位

只读。把 `rule/tools/` 下 query.py、eval.py、trace.py、rule_tool.py 的能力按原名暴露成 MCP 工具，参数由 CLI 的 `;` 拼串改成 JSON 对象。它不判断、不写文件、不碰数据库以外的任何东西；对输入的唯一要求与规则层一致——合法（变量名、slot_key、三值答案），不合法报错不猜。

三个 Agent 都挂它：前台主要用 variables / predicates / judgment_points / gap / eval_flow，分析用 requirements / options / what_if / trace / rule_tool，复核用 trace / eval_* 重跑。

## 2. 工具

| 工具 | 包装 | 参数 → 返回 |
|---|---|---|
| `variables` | query.py | 无 → 字段字典（变量、类型、value_kind、问法、含义） |
| `predicates` | query.py | 无 → 谓词表（问法、factor_vars、所属格） |
| `version` | query.py | 无 → 规则层构建号、规则 / 变量 / 谓词 / 口径 / 金标数 |
| `cells_for_flow` | query.py | payer_jur, payee_jur, subject → 该流经过的格（slot_key 列表） |
| `judgment_points` | query.py | flow{payer_jur, payee_jur, subject} 或 slot, date, facts{}, answers{}, mode → 卡住的谓词、问法、因素变量、答成哪边的后果 |
| `requirements` | query.py | slot 或 rule, date → 成立条件、要交的文件、期限、证明年度、reference_params |
| `options` | query.py | flow, date, facts{} → 可选待遇与各自条件 |
| `what_if` | query.py | flow, date, facts{}, answers{}, set{}, answer_set{}, mode → 改前改后对照 |
| `gap` | query.py | flow, date, facts{}, answers{} → 还缺的事实与谓词 |
| `eval_cell` | eval.py | slot, date, facts{}, answers{}, mode, assume[] → 三值结果、ceiling / floor、value_kind、items。facts 可用案卷 facts.json 的嵌套形状；收款方居民身份从它的事实算出 |
| `eval_flow` | eval.py | payer_jur, payee_jur, subject, date, facts{}, answers{}, mode, assume[] → 同上，整条流。facts 可用案卷 facts.json 的嵌套形状 |
| `eval_transfer` | eval.py | target_jur, home_jur, subject, date, facts{}, answers{}, mode, assume[] → 同上，一笔股权转让 |
| `trace` | trace.py | items（eval 输出对象，或优化层 hops / transfers 文件路径，相对 `cases/` 根）或 flow + date + facts{} + answers{} → 每条规则命中 / 未命中与条文原句 |
| `rule_tool` | rule_tool.py | slot / rule / variable / predicate, date, brief → 规则正文、口径（decisions）、reference_params、变量说明 |

`mode` 取 record / plan，默认 record；`assume` 是声明为假设的键列表，语义同 CLI `--assume`。facts 里的实体前缀（`payer.` / `payee.` / `target.` / `transferor.`）与 CLI 相同。

## 3. 约定（四个服务一致）

- Python `mcp` 包的 FastMCP，stdio 传输；直接 import 本层函数，不起子进程。
- `--root`（rule/）与 `--db`（database/）在服务配置里定死，Agent 不传。
- `date` 不给默认值，缺就报 `invalid`。
- 每个返回带 `version`（规则层构建号），供报告的 sources.json 引用。
- 错误结构化返回 `{error: invalid | not_found | internal, detail}`，供 Agent 原样贴进 bug 反馈。
- 调用日志不由服务记：宿主的 PostToolUse 钩子统一记到 `cases/<case_id>/log/calls.jsonl`（见 `agent/案卷MCP规范.md` §5），服务不碰日志。
- 跨服务同名工具（`requirements`、`version`、`diff`）由宿主按服务名加前缀，不冲突；Agent 规范提到时带服务名。

## 4. 身份与权限

没有写工具，不区分身份，一个进程三个 Agent 共用；隔离由各子 Agent 的工具白名单管（案卷规范 §7）。`--cases` 只用来解析 `trace` 的 items 相对路径。

## 5. 实现

- 文件 `rule/tools/mcp_server.py`；依赖只有 `mcp` 和本层已有模块。启动参数：`--root rule --db database --cases cases`。
- `.mcp.json` 片段：

```json
"tax-rule": {"command": "<tax 环境的 python>", "args": ["rule/tools/mcp_server.py", "--root", "rule", "--db", "database", "--cases", "cases"]}
```

- 参数转换是服务的全部逻辑：JSON 对象 → 现有函数的参数；返回值原样加 `version`。不在服务里做任何合并、过滤、改写。

**构建记录（2026-11-01）**：`rule/tools/mcp_server.py` 与 `test_mcp_server.py` 已建，29 项检查通过。两点实现细节：MCP 每次调用在工作线程里跑，而 `common.Library` 的 sqlite 连接是惰性、绑定线程的，服务启动时用 `check_same_thread=False` 预开连接，否则第二次调用报 `sqlite3.ProgrammingError`（tax-opt 复用 Library 时同样要做）；返回值统一包一层对象（`{"variables": [...]}`、`{"items": [...]}`、`{"traces": [...]}`、`{"cells": [...]}`），好放 `version`。facts 里的 bool / 数值按 CLI 的字符串形式转换（true / false、整数去小数点）。

## 6. 测试（构建的一部分）

`rule/tools/test_mcp_server.py`：对每个工具各一条，用金标里现成的一个格 / 流 / 转让，断言 MCP 返回与直接调用本层函数的结果相同；一条缺 date 的调用返回 `invalid`。

## 7. 不做

不写文件；不缓存求值结果；不替 Agent 补事实或默认答案；不把多次调用合成"一键分析"；不暴露 build.py。
