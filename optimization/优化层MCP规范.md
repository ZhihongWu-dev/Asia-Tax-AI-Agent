# 优化层 MCP 规范（tax-opt，最小集）

2026-11-01。四个 MCP 服务之一（另三个：`database/数据库MCP规范.md`、`rule/规则层MCP规范.md`、`agent/案卷MCP规范.md`）。本文只定 `tax-opt`：包装 optimize.py、fx.py、check.py 和产物的分块读取。优化层本身的算法、产物格式见 `优化层规范.md`。

**语言**：本规范用中文，供人阅读；英文副本 `optimization/optimization_mcp_spec.en.md`，两者不一致时以中文版为准，改中文版时同步改英文副本。AI 写进文件的一切自写文字用英文——代码、注释、工具说明、prompt（系统实际递交的是英文副本里的那段）、底稿、核对单、handoff、bug 反馈、日志、产物字段；原件、条文、引文、客户原话保持原文，不翻译。唯一例外是给客户看的文字（对客户的回话、briefing）跟客户的语言。核对单的总判断用英文记号：交接包 `RUNNABLE` / `REVISE`，报告 `DELIVERABLE` / `REVISE`（服务也接受原来的中文记号）。

## 1. 定位

两件事：跑优化（`run`、`evaluate`）和按候选、分支切片读产物。切片读的理由是上下文——分析 Agent 常驻上下文只装产物的 JSON，按 cand_id / branch_id 取比整文件读省得多；分析和复核读产物优先用这里的切片工具，不用案卷服务整文件读。

`run` 是唯一新建产物的工具，`diff` 是前台重跑后的事，两者只在 `--role front` 的进程里注册；`evaluate` 往已有产物目录新增 `x-` 候选，三个身份都开。

## 2. 工具

| 工具 | 参数 → 返回 | 读写 |
|---|---|---|
| `run` | case_id, input（facts.json 路径，相对 `cases/` 根）→ 服务生成 run_id（日期 + 输入哈希前 8 位），写 `cases/<case_id>/intake/products/<run_id>/`，目录已存在则 `conflict`；返回 run_id、ranking 前三行、open_items 里 changes_rank 为真的条数 | 新建；只在 `--role front` 注册；只能写在 `--products-root` 之下；run 不联网：汇率来自输入里的 `fx`（内嵌对象，或相对服务工作目录的文件路径），run 只把它抄成 fx.json；前台先用 `fx` 工具取汇率再写进 facts.json |
| `evaluate` | products, path（`jur:subject;…`）, moves[] → 该路径的 hops / tax / deltas，cand_id `x-<n>` 写进同一产物目录 | 新增；`x-` 候选不进排序（ranking 排除该前缀）、不改已有文件；每次进日志，复核据此知道报告里哪些数来自事后补算 |
| `requirements` | products, cand_id → requirements/<cand_id>.json | 读 |
| `diff` | products, against → 写 `<products>/diff.json` 并返回 | 写进较新的产物目录；前台重跑后调 |
| `version` | products? → 不给 products 回本层版本（规则层 + 数据库版本），给了回该产物的 version.json | 读 |
| `fx` | base, date, jur?, role, subject, symbols? → 汇率与法定口径（fx.py `fetch`），不写文件 | 读（联网） |
| `ranking` | products → ranking.json | 读 |
| `deltas` | products, cand_id? / branch_id? → 只回该候选 / 分支的完整 deltas 条目；都不给时每分支一行摘要 | 读 |
| `scenarios` | products, changes_first? → scenarios.json：所有结构在同一组判断答案下的税、每个情景的第一名和第二名、结构名次；changes_first 只留第一名与全有利不同的情景 | 读 |
| `open_items` | products, changes_rank? → 过滤后的 open_items | 读 |
| `paths` | products, cand_id? → 候选的 path、moves、restructure、dominated_by | 读 |
| `tax` | products, branch_id? → 该分支每跳的税额分量（floor / ceiling） | 读 |
| `transfers` | products, cand_id → transfers/<cand_id>.json | 读 |
| `hops` | products, cand_id → hops/<id>.json；产物里 hops 按分支编号存（`c0.b0.json`），参数接受候选或分支编号，即文件名 | 读 |
| `penalty` | products, jur → penalty/<jur>.json | 读 |
| `product_check` | products → check.py `--products` 的结果 | 读 |
| `validate_input` | input（facts.json 路径）→ 只构造 `Optimizer(inp)` 不跑：合法返回实体、终点、日期摘要，不合法返回 `invalid` 与原因 | 读；案卷服务的 `intake_check` 调它 |

`products` 一律是相对 `cases/` 根的产物目录路径；服务拒绝根以外的路径。

## 3. 约定（四个服务一致）

- Python `mcp` 包的 FastMCP，stdio 传输；直接 import 本层函数，不起子进程。
- `--root`（optimization/）、`--rule`、`--db`、`--products-root`（cases/）在服务配置里定死，Agent 不传。
- `date` 不给默认值（`fx`），缺就报 `invalid`。
- 每个返回带 `version`（优化层构建号，含它依赖的规则层与数据库版本），供报告的 sources.json 引用。
- 错误结构化返回 `{error: invalid | not_found | conflict | forbidden | internal, detail}`。
- 调用日志不由服务记：宿主的 PostToolUse 钩子统一记到 `cases/<case_id>/log/calls.jsonl`（见 `agent/案卷MCP规范.md` §5），服务不碰日志。
- 跨服务同名工具（`requirements`、`version`、`diff`）由宿主按服务名加前缀，不冲突；Agent 规范提到时带服务名。

## 4. 身份与权限

| 工具 | `--role front`（进程 `tax-opt-front`） | `--role reader`（进程 `tax-opt`，分析与复核共用） |
|---|---|---|
| `run`、`diff` | 注册 | 不注册 |
| `evaluate` | 注册 | 注册 |
| 其余读 | 注册 | 注册 |

两个进程写在 `.mcp.json`，前台的子 Agent 白名单挂 `tax-opt-front`，分析和复核挂 `tax-opt`；分析、复核的 deny 里另加 `Bash(*optimize.py run*)` 作第二道保险（案卷规范 §7）。

## 5. 实现

- 文件 `optimization/tools/mcp_server.py`；依赖 `mcp` 和本层已有模块（optimize.py 的 `Optimizer`、`diff`；fx.py 的 `fetch`；check.py 的产物检查）。
- 启动参数：`--root optimization --rule rule --db database --products-root cases --role front|reader`。
- `.mcp.json` 片段（前台）：

```json
"tax-opt-front": {"command": "<tax 环境的 python>", "args": ["optimization/tools/mcp_server.py", "--root", "optimization", "--rule", "rule", "--db", "database", "--products-root", "cases", "--role", "front"]},
"tax-opt":       {"command": "<tax 环境的 python>", "args": ["optimization/tools/mcp_server.py", "--root", "optimization", "--rule", "rule", "--db", "database", "--products-root", "cases", "--role", "reader"]}
```

- 切片工具只做"读文件 → 按键过滤 → 返回"，不改数、不合并、不算总额。

**构建记录（2026-11-01）**：`optimization/tools/mcp_server.py` 与 `test_mcp_server.py` 已建，32 项检查通过。`evaluate` 会把 `x-` 分支列进 ranking.json 但不给名次，已排名的行不变；优化层打印的进度被服务吞掉；层抛出的 `SystemExit` 作 `invalid` 返回。

## 6. 测试（构建的一部分）

`optimization/tools/test_mcp_server.py`：对 `optimization/examples/case001.json` 跑一次 `run`，断言 run_id 格式与目录；同一输入再跑一次返回 `conflict`；`ranking` / `deltas` / `tax` 的切片与整文件对应项相同；`evaluate` 新增 `x-1` 后 `ranking` 不变；`--role reader` 启动时工具表里没有 `run` 和 `diff`；`validate_input` 对合法输入返回摘要、对缺字段的输入返回 `invalid`。

## 7. 不做

不改产物已有文件（`evaluate` 只新增、`diff` 只写 diff.json）；不做汇率以外的联网；不缓存；不把切片结果再加工成报告用的表；不暴露 build / check 以外的内部函数。
