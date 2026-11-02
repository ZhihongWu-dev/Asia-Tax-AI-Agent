# Optimization layer MCP specification (tax-opt, minimal set)

English copy of `optimization/优化层MCP规范.md`; when the two differ the Chinese version prevails.

2026-11-01. One of four MCP services (the other three: `database/数据库MCP规范.md`, `rule/规则层MCP规范.md`, `agent/案卷MCP规范.md`). This document defines only `tax-opt`: it wraps optimize.py, fx.py, check.py and sliced reading of the products. The optimization layer's own algorithm and product formats are in `优化层规范.md`.

**Language**: this specification is written in Chinese for human readers; the English copy is `optimization/optimization_mcp_spec.en.md`; when the two differ the Chinese version prevails, and when the Chinese version is changed the English copy is updated in step. Everything the AI writes into files in its own words is in English — code, comments, tool descriptions, prompts (what the system actually submits is the passage in the English copy), working papers, checklists, handoff, bug reports, logs, product fields; originals, clauses, quotations and the client's own words stay in their original language and are not translated. The only exception is text shown to the client (replies to the client, the briefing), which follows the client's language. The overall verdict of a checklist uses English tokens: intake package `RUNNABLE` / `REVISE`, report `DELIVERABLE` / `REVISE` (the service also accepts the original Chinese tokens).

## 1. Positioning

Two things: running the optimization (`run`, `evaluate`) and reading the products in slices by candidate and branch. The reason for sliced reading is context — the analysis agent's resident context holds only the products' JSON, and fetching by cand_id / branch_id saves far more than reading whole files; when reading products, analysis and review should prefer the slice tools here rather than whole-file reads through the case service.

`run` is the only tool that creates new products, and `diff` is what the front agent does after a rerun; both are registered only in the `--role front` process; `evaluate` adds `x-` candidates to an existing products directory and is open to all three identities.

## 2. Tools

| Tool | Parameters → returns | Read/write |
|---|---|---|
| `run` | case_id, input (path of facts.json, relative to the `cases/` root) → the service generates the run_id (date + first 8 characters of the input hash), writes `cases/<case_id>/intake/products/<run_id>/`, `conflict` if the directory already exists; returns run_id, the top three rows of ranking, and the number of open_items entries whose changes_rank is true | creates; registered only in `--role front`; may write only under `--products-root`; run does not access the internet: exchange rates come from `fx` in the input (an embedded object, or a file path relative to the service's working directory), and run merely copies it to fx.json; the front agent first fetches the rates with the `fx` tool and then writes them into facts.json |
| `evaluate` | products, path (`jur:subject;…`), moves[] → the hops / tax / deltas of that path, cand_id `x-<n>` written into the same products directory | adds; `x-` candidates do not enter the ranking (ranking excludes that prefix) and do not change existing files; every call goes into the log, from which review knows which numbers in the report come from after-the-fact computation |
| `requirements` | products, cand_id → requirements/<cand_id>.json | read |
| `diff` | products, against → writes `<products>/diff.json` and returns it | writes into the newer products directory; called by the front agent after a rerun |
| `version` | products? → without products returns this layer's version (rule layer + database versions); with products returns that product's version.json | read |
| `fx` | base, date, jur?, role, subject, symbols? → exchange rates and the statutory reading (fx.py `fetch`), writes no file | read (internet) |
| `ranking` | products → ranking.json | read |
| `deltas` | products, cand_id? / branch_id? → the full deltas rows of that candidate / branch; with neither, a one-line summary per branch | read |
| `open_items` | products, changes_rank? → the filtered open_items | read |
| `paths` | products, cand_id? → the candidate's path, moves, restructure, dominated_by | read |
| `tax` | products, branch_id? → the tax components of every hop of that branch (floor / ceiling) | read |
| `transfers` | products, cand_id → transfers/<cand_id>.json | read |
| `hops` | products, cand_id → hops/<id>.json; in the products, hops are stored by branch number (`c0.b0.json`), and the parameter accepts a candidate or branch number, i.e. the file name | read |
| `penalty` | products, jur → penalty/<jur>.json | read |
| `product_check` | products → the result of check.py `--products` | read |
| `validate_input` | input (path of facts.json) → only constructs `Optimizer(inp)` without running: if valid returns a summary of entities, endpoints and dates, if invalid returns `invalid` with the reason | read; the case service's `intake_check` calls it |

`products` is always the products directory path relative to the `cases/` root; the service refuses paths outside the root.

## 3. Conventions (shared by the four services)

- FastMCP of the Python `mcp` package, stdio transport; imports this layer's functions directly, starts no subprocess.
- `--root` (optimization/), `--rule`, `--db`, `--products-root` (cases/) are fixed in the service configuration; agents do not pass them.
- `date` has no default value (`fx`); if it is missing, `invalid` is reported.
- Every return carries `version` (the optimization layer build number, including the rule layer and database versions it depends on), for citation in the report's sources.json.
- Errors are returned structured as `{error: invalid | not_found | conflict | forbidden | internal, detail}`.
- Call logs are not recorded by the service: the host's PostToolUse hook records them uniformly to `cases/<case_id>/log/calls.jsonl` (see `agent/案卷MCP规范.md` §5); the service does not touch logs.
- Tools with the same name across services (`requirements`, `version`, `diff`) are prefixed by the host with the service name, so they do not clash; agent specifications include the service name when mentioning them.

## 4. Identity and permissions

| Tool | `--role front` (process `tax-opt-front`) | `--role reader` (process `tax-opt`, shared by analysis and review) |
|---|---|---|
| `run`, `diff` | registered | not registered |
| `evaluate` | registered | registered |
| other reads | registered | registered |

Both processes are written in `.mcp.json`; the front subagent's allowlist mounts `tax-opt-front`, analysis and review mount `tax-opt`; `Bash(*optimize.py run*)` is additionally added to the deny list of analysis and review as a second safeguard (case specification §7).

## 5. Implementation

- File `optimization/tools/mcp_server.py`; dependencies `mcp` and this layer's existing modules (`Optimizer` and `diff` of optimize.py; `fetch` of fx.py; the product check of check.py).
- Start parameters: `--root optimization --rule rule --db database --products-root cases --role front|reader`.
- `.mcp.json` fragment (front agent):

```json
"tax-opt-front": {"command": "<tax env python>", "args": ["optimization/tools/mcp_server.py", "--root", "optimization", "--rule", "rule", "--db", "database", "--products-root", "cases", "--role", "front"]},
"tax-opt":       {"command": "<tax env python>", "args": ["optimization/tools/mcp_server.py", "--root", "optimization", "--rule", "rule", "--db", "database", "--products-root", "cases", "--role", "reader"]}
```

- The slice tools only do "read the file → filter by key → return"; they do not change numbers, merge, or compute totals.

**Build record (2026-11-01)**: `optimization/tools/mcp_server.py` and `test_mcp_server.py` are built, 32 checks pass. `evaluate` lists `x-` branches in ranking.json but gives them no rank, and the already-ranked rows are unchanged; the progress printed by the optimization layer is swallowed by the service; a `SystemExit` raised by the layer is returned as `invalid`.

## 6. Tests (part of the build)

`optimization/tools/test_mcp_server.py`: runs `run` once on `optimization/examples/case001.json`, asserting the run_id format and the directory; running the same input again returns `conflict`; the slices of `ranking` / `deltas` / `tax` are the same as the corresponding items of the whole files; after `evaluate` adds `x-1`, `ranking` is unchanged; when started with `--role reader` the tool table has no `run` and `diff`; `validate_input` returns a summary for valid input and `invalid` for input with missing fields.

## 7. Not done

No changes to existing product files (`evaluate` only adds, `diff` only writes diff.json); no internet access other than for exchange rates; no caching; no reworking of slice results into tables for the report; no exposure of internal functions other than build / check.
