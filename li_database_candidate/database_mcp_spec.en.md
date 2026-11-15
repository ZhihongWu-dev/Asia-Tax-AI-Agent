# Library MCP specification (tax-db, minimal set)

English copy of `database/数据库MCP规范.md`; when the two differ the Chinese version prevails.

2026-11-01. One of four MCP services (the other three: `rule/规则层MCP规范.md`, `optimization/优化层MCP规范.md`, `agent/案卷MCP规范.md`). This document defines only `tax-db`: read-only queries for the agent layer. The library's tables, collection and acceptance are in `数据库规范.md`; this file and `tools/mcp_server.py` are maintained by the collectors under the rules of `数据库规范.md` §4.9.

**Language**: this specification is written in Chinese for human readers; the English copy is `database/database_mcp_spec.en.md`; when the two differ the Chinese version prevails, and when the Chinese version is changed the English copy is updated in step. Everything the AI writes into files in its own words is in English — code, comments, tool descriptions, prompts (what the system actually submits is the passage in the English copy), working papers, checklists, handoff, bug reports, logs, product fields; originals, clauses, quotations and the client's own words stay in their original language and are not translated. The only exception is text shown to the client (replies to the client, the briefing), which follows the client's language. The overall verdict of a checklist uses English tokens: intake package `RUNNABLE` / `REVISE`, report `DELIVERABLE` / `REVISE` (the service also accepts the original Chinese tokens).

## 1. Positioning

Read-only. It reads the eight tables doc, clause, param, treaty, jurisdiction, superseded, decision, blocked and STATUS.md, and does not go through build / fetch / upload. Agents want three things: find clauses by word, fetch the original sentence by cite_id, fetch the value and its source by param_id; the remaining tools are auxiliaries around these three (document metadata, treaties, currencies, parameter history, library-level readings, originals that could not be obtained, library version).

When an agent finds a law missing from the library or outdated, that does not go through here; it goes through the case service's `to_collect_append` and is handled by the collectors; the library still takes only official originals that have passed acceptance.

## 2. Tools

| Tool | Parameters → returns |
|---|---|
| `find` | words[], jur?, doc?, max → list of matching clauses (cite_id, doc_id, label, the sentence containing the word, matched): most of the words first, then by BM25; a word that finds nothing is split into shorter words and listed under relaxed; each query goes to `cases/_log/find.jsonl` |
| `clause` | cite_id, offset?, max_chars? → the full clause text (the text of clause.csv; long clauses are fetched in segments by offset / max_chars), doc_id, label, the document's validity interval, the cite_ids of the preceding and following clause |
| `doc` | doc_id → the whole row of doc.csv: title, jurisdiction, type, category, source URL, original file path, language, validity interval, note |
| `param` | param_id → the whole row of param.csv: value, unit, quote, cite_id, validity interval, note, changed_on, superseded_by |
| `params_for` | jur, slot?, subject? → all parameters of that jurisdiction and slot (including absence records) |
| `absent` | jur, slot? → slot absence records (the record that this jurisdiction has no such tax / treatment in this slot) |
| `treaty` | jur_a, jur_b? → all rows of treaty.csv for that jurisdiction pair (doc_id of the treaty and protocols, articles, validity interval); when only one jurisdiction is given, lists all its treaties |
| `jurisdictions` | none → jurisdiction.csv: code, name, currency, whether companies / individuals are in scope |
| `param_history` | param_id → all versions along the superseded_by chain (value, validity interval, changed_on, note), plus the entries of superseded.csv involving its cite |
| `decision` | id? → one row or all rows of decision.csv (library-level readings) |
| `blocked` | none → blocked.csv: documents whose original could not be obtained, the reason, the alternatives tried |
| `version` | none → STATUS.md summary: build time, PASSED status of each jurisdiction, table row counts |

quote and text in the returns are always the original, word for word, not translated, not rewritten, not truncated (except for `clause`'s segmentation; a segmented return carries `total_chars` and `offset`).

## 3. Conventions (shared by the four services)

- FastMCP of the Python `mcp` package, stdio transport; reads the csv directly, starts no subprocess.
- `--root` (database/) is fixed in the service configuration; agents do not pass it.
- Every return carries `version` (library build time and the status of each jurisdiction), for citation in the report's sources.json.
- Errors are returned structured as `{error: invalid | not_found | internal, detail}`.
- Call logs are not recorded by the service: the host's PostToolUse hook records them uniformly to `cases/<case_id>/log/calls.jsonl` (see `agent/案卷MCP规范.md` §5); the service does not touch logs.
- Tools with the same name across services (`requirements`, `version`, `diff`) are prefixed by the host with the service name, so they do not clash; agent specifications include the service name when mentioning them.

## 4. Identity and permissions

No write tools, no distinction of identity, one process shared by the three agents; isolation is managed by each subagent's tool allowlist (case specification §7).

## 5. Implementation

- File `database/tools/mcp_server.py`; dependencies `mcp` and the standard library (csv reading and the existing functions of find.py). Start parameters: `--root database`.
- `.mcp.json` fragment:

```json
"tax-db": {"command": "<tax env python>", "args": ["database/tools/mcp_server.py", "--root", "database"]}
```

- At startup the eight tables are read into memory; restart the service after the library is rebuilt. No incremental updates, no processing beyond indexing.

**Build record (2026-11-01)**: `database/tools/mcp_server.py` and `test_mcp_server.py` are built, 18 checks pass (the chained param_history item is skipped because the library has no superseded parameter yet). stdio handshake, tools/list and tools/call tested and passed.

## 6. Tests (part of the build)

`database/tools/test_mcp_server.py`: one test per tool — `find` hits a known cite_id with a known word; the text returned by `clause` is identical to clause.csv word for word, and identical after the segments are joined back together; `param`'s quote is a substring of the text of `clause(cite_id)`; `treaty` returns non-empty for cn–hk; `param_history` returns two versions for a parameter with superseded_by; `version` agrees with STATUS.md.

## 7. Not done

No writing to the library, no fetching, no uploading; no semantic retrieval (find is word matching with BM25 ranking; semantic retrieval waits until the query log shows a need); no translation or summarising of clauses; no deciding on the agents' behalf which clause applies.
