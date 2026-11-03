# Rule layer MCP specification (tax-rule, minimal set)

English copy of `rule/规则层MCP规范.md`; when the two differ the Chinese version prevails.

2026-11-01. One of four MCP services (the other three: `database/数据库MCP规范.md`, `optimization/优化层MCP规范.md`, `agent/案卷MCP规范.md`). This document defines only `tax-rule`: a service interface for the agent layer that wraps the rule layer's existing functions and adds no new semantics. The rule layer's own tables, evaluation semantics and function set are in `规则层规范.md`.

**Language**: this specification is written in Chinese for human readers; the English copy is `rule/rule_mcp_spec.en.md`; when the two differ the Chinese version prevails, and when the Chinese version is changed the English copy is updated in step. Everything the AI writes into files in its own words is in English — code, comments, tool descriptions, prompts (what the system actually submits is the passage in the English copy), working papers, checklists, handoff, bug reports, logs, product fields; originals, clauses, quotations and the client's own words stay in their original language and are not translated. The only exception is text shown to the client (replies to the client, the briefing), which follows the client's language. The overall verdict of a checklist uses English tokens: intake package `RUNNABLE` / `REVISE`, report `DELIVERABLE` / `REVISE` (the service also accepts the original Chinese tokens).

## 1. Positioning

Read-only. It exposes the capabilities of query.py, eval.py, trace.py and rule_tool.py under `rule/tools/` as MCP tools under their original names, with the parameters changed from the CLI's `;`-joined strings to JSON objects. It does not judge, does not write files, and touches nothing other than the database; its only requirement on input is the same as the rule layer's — validity (variable names, slot_key, three-valued answers); invalid input raises an error, it does not guess.

All three agents mount it: the front agent mainly uses variables / predicates / judgment_points / gap / eval_flow, the analysis agent uses requirements / options / what_if / trace / rule_tool, and the review agent uses trace / eval_* for reruns.

## 2. Tools

| Tool | Wraps | Parameters → returns |
|---|---|---|
| `variables` | query.py | none → field dictionary (variable, type, value_kind, question wording, meaning) |
| `predicates` | query.py | none → predicate table (question wording, factor_vars, owning cell) |
| `version` | query.py | none → rule layer build number, counts of rules / variables / predicates / readings / golden tests |
| `cells_for_flow` | query.py | payer_jur, payee_jur, subject → the cells this flow passes through (list of slot_key) |
| `judgment_points` | query.py | flow{payer_jur, payee_jur, subject} or slot, date, facts{}, answers{}, mode → the blocked predicates, question wording, factor variables, consequences of answering either way |
| `requirements` | query.py | slot or rule, date → conditions for applying, documents to file, deadlines, years to prove, reference_params |
| `options` | query.py | flow, date, facts{} → the available treatments and their respective conditions |
| `what_if` | query.py | flow, date, facts{}, answers{}, set{}, answer_set{}, mode → before/after comparison |
| `gap` | query.py | flow, date, facts{}, answers{} → the facts and predicates still missing |
| `eval_cell` | eval.py | slot, date, facts{}, answers{}, mode, assume[] → three-valued result, ceiling / floor, value_kind, items. facts may use the nested shape of the case's facts.json; the recipient's residence is computed from its facts. |
| `eval_flow` | eval.py | payer_jur, payee_jur, subject, date, facts{}, answers{}, mode, assume[] → same, for the whole flow. facts may use the nested shape of the case's facts.json. |
| `eval_transfer` | eval.py | target_jur, home_jur, subject, date, facts{}, answers{}, mode, assume[] → same, for one share transfer |
| `trace` | trace.py | items (eval output object, or path of an optimization-layer hops / transfers file, relative to the `cases/` root) or flow + date + facts{} + answers{} → hit / miss for every rule with the clause's original sentence |
| `rule_tool` | rule_tool.py | slot / rule / variable / predicate, date, brief → rule text, readings (decisions), reference_params, variable descriptions |

`mode` takes record / plan, default record; `assume` is the list of keys declared as assumptions, with the same semantics as the CLI's `--assume`. Entity prefixes in facts (`payer.` / `payee.` / `target.` / `transferor.`) are the same as in the CLI.

## 3. Conventions (shared by the four services)

- FastMCP of the Python `mcp` package, stdio transport; imports this layer's functions directly, starts no subprocess.
- `--root` (rule/) and `--db` (database/) are fixed in the service configuration; agents do not pass them.
- `date` has no default value; if it is missing, `invalid` is reported.
- Every return carries `version` (the rule layer build number), for citation in the report's sources.json.
- Errors are returned structured as `{error: invalid | not_found | internal, detail}`, so the agent can paste them verbatim into a bug report.
- Call logs are not recorded by the service: the host's PostToolUse hook records them uniformly to `cases/<case_id>/log/calls.jsonl` (see `agent/案卷MCP规范.md` §5); the service does not touch logs.
- Tools with the same name across services (`requirements`, `version`, `diff`) are prefixed by the host with the service name, so they do not clash; agent specifications include the service name when mentioning them.

## 4. Identity and permissions

No write tools, no distinction of identity, one process shared by the three agents; isolation is managed by each subagent's tool allowlist (case specification §7). `--cases` is used only to resolve the relative paths of `trace`'s items.

## 5. Implementation

- File `rule/tools/mcp_server.py`; dependencies only `mcp` and this layer's existing modules. Start parameters: `--root rule --db database --cases cases`.
- `.mcp.json` fragment:

```json
"tax-rule": {"command": "<tax env python>", "args": ["rule/tools/mcp_server.py", "--root", "rule", "--db", "database", "--cases", "cases"]}
```

- Parameter conversion is the whole logic of the service: JSON object → the arguments of the existing functions; the return value is passed through unchanged with `version` added. No merging, filtering or rewriting is done in the service.

**Build record (2026-11-01)**: `rule/tools/mcp_server.py` and `test_mcp_server.py` are built, 29 checks pass. Two implementation details: MCP runs each call in a worker thread, while the sqlite connection of `common.Library` is lazy and bound to a thread, so the service pre-opens the connection at startup with `check_same_thread=False`, otherwise the second call raises `sqlite3.ProgrammingError` (tax-opt must do the same when it reuses Library); return values are uniformly wrapped in one object (`{"variables": [...]}`, `{"items": [...]}`, `{"traces": [...]}`, `{"cells": [...]}`) to make room for `version`. bool / numeric values in facts are converted following the CLI's string form (true / false, integers without the decimal point).

## 6. Tests (part of the build)

`rule/tools/test_mcp_server.py`: one test per tool, using a ready-made cell / flow / transfer from the golden tests, asserting that the MCP return is the same as the result of calling this layer's function directly; one call without date returns `invalid`.

## 7. Not done

No writing of files; no caching of evaluation results; no filling in of facts or default answers on the agents' behalf; no combining of multiple calls into a "one-click analysis"; build.py is not exposed.
