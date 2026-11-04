# Case MCP specification (tax-case, minimal set)

English copy of `agent/案卷MCP规范.md`; when the two differ the Chinese version prevails.

2026-11-01. One of four MCP services (the other three: `database/数据库MCP规范.md`, `rule/规则层MCP规范.md`, `optimization/优化层MCP规范.md`; this document defines only the case service). The case service is the **sole write entry point** of the four agents to `cases/<case_id>/`; reads do not go through it — the host's built-in Read (files, PDF by page, images), Glob and Grep do this better than a service could, so use them directly. Write permissions are hard-coded in the service by agent identity; read permissions rely on the host's subagent tool allowlist plus one PreToolUse guard hook (`agent/tools/guard_hook.py`, which decides by the `agent_type` in the hook input). No service is built for internet access; use the host's built-in search and fetch, with the policy written in the prompts of the three agent specifications. Call logs are not recorded by the service either; the host's PostToolUse hook records them (§5).

**Language**: this specification is written in Chinese for human readers; the English copy is `agent/case_mcp_spec.en.md`; when the two differ the Chinese version prevails, and when the Chinese version is changed the English copy is updated in step. Everything the AI writes into files in its own words is in English — code, comments, tool descriptions, prompts (what the system actually submits is the passage in the English copy), working papers, checklists, handoff, bug reports, logs, product fields; originals, clauses, quotations and the client's own words stay in their original language and are not translated. The only exception is text shown to the client (replies to the client, the briefing), which follows the client's language. The overall verdict of a checklist uses English tokens: intake package `RUNNABLE` / `REVISE`, draft `POLISHABLE` / `REVISE`, final report `DELIVERABLE` / `REVISE`.

## 1. Positioning

- One directory per case, `cases/<case_id>/`, in four parts: `intake/` (the front agent's intake package), `report/<run_id>/` (analysis draft, polished report, PDF, review checklist), `notes/<agent>/round-N/` (working papers), `bugs/<agent>.md` (bug reports).
- The service starts with two parameters: `--root cases` and `--agent front|analysis|polish|review`. The same code is started as four processes, one identity each; each subagent's tool allowlist mounts only the one for its own identity, so it cannot get hold of the other identities.
- The service does four things: writes with semantics (append, never overwrite; .prev; JSON validation; validation of the overall verdict in the last sentence), the ledger (round, run_id, status derivation), two read-only self-checks, and PDF rendering for the polish identity (the `render_pdf` subprocess calls `agent/tools/render_pdf.py`, a fixed template; the service itself makes no typesetting judgment). It does not read, does not log, does not make tax judgments, and does not call the other three layers.
- The path convention is the same as in the other three services: every path parameter is relative to the `cases/` root (i.e. it includes the case_id). The tools' `case_id` parameter is passed explicitly.

## 2. Directory and ledger

```
cases/<case_id>/
  rounds.json                 ledger: current round, each round's run_id, revision number; status is derived from the files
  log/calls.jsonl             call log: written by the host hook (§5), the service does not touch it
  log/runs.jsonl  log/runs/  log/run.lock   run records, raw CLI output, run lock: written by the orchestrator
  intake/
    prompt.md  dialogue.md  documents/
    facts.json  sources.json  answers.json  notes.md  constraints.json
    handoff.md  to_collect.md  review_intake.md
    products/<run_id>/
  report/<run_id>/
    briefing.md  briefing.sources.json                    analysis draft (not overwritten by polish)
    briefing.polished.md  briefing.polished.sources.json  the polished, client-facing report
    briefing.pdf                                          rendered by polish
    review.md  review_final.md                            checklists of review stages 2 and 3
  notes/front/round-N/  notes/analysis/round-N/  notes/polish/round-N/  notes/review/round-N/
  bugs/front.md  bugs/analysis.md  bugs/polish.md  bugs/review.md
```

`rounds.json`: `{"current": N, "rounds": [{"round": N, "revision": k, "run_id": "...|null", "opened": date, "intake_dirty": bool}]}`. Maintained by the service; agents can change it only through `case_new` / `round_new` / `round_revise` / `round_set_run`; read it with Read.

The status is not stored and not edited by hand; `round_current` derives it on the spot from the files:

| Status | Determination |
|---|---|
| intake | this round has no run_id and intake_ok does not hold; or it has a run_id but the intake package was written after the last intake review (check it and compute again) |
| intake_ok | the last sentence of review_intake.md is `RUNNABLE` and it was written later than the last write of facts / sources / answers / notes / constraints; when the round already has a run_id, also later than its registration (`run_registered`), and the old products no longer count |
| ran | has a run_id, `briefing.md` does not exist |
| drafted | `briefing.md` exists; `review.md` does not exist, is older than the draft or does not end with `POLISHABLE` (the draft's time is the newer of `briefing.md` and its sources table) |
| reviewed | `review.md` ends with `POLISHABLE` and is not older than the draft; the report does not exist or is older than `review.md` |
| polished | the report is newer than `review.md`; `review_final.md` does not exist, is older than the report or does not end with `DELIVERABLE` (the report's time is the newest of `briefing.polished.md`, its sources table and the PDF) |
| delivered | `review_final.md` ends with `DELIVERABLE` and is not older than the report |

This table is at the same time what the orchestrator decides from (see `agent/orchestration_cli_spec.en.md`). `round_current` also returns `return_to`: the `REVISE` checklist the current status is waiting on, as `{which, to, path}`, empty when there is none.

## 3. Permissions

**Write** (enforced by the service, by `--agent`)

| Path | front | analysis | polish | review |
|---|---|---|---|---|
| facts, sources, answers, notes, constraints, handoff in `intake/` | write (keeps .prev) | — | — | — |
| `intake/documents/`, `prompt.md` | put (first round) | — | — | — |
| `intake/dialogue.md` | append | — | — | — |
| `intake/to_collect.md` | append | append | — | — |
| `intake/review_intake.md` | — | — | — | write (keeps .prev) |
| `report/<run_id>/briefing.md`, `briefing.sources.json` | — | write (keeps .prev) | — | — |
| `report/<run_id>/briefing.polished.md`, `.polished.sources.json`, `briefing.pdf` | — | — | write / render (keeps .prev) | — |
| `report/<run_id>/review.md`, `review_final.md` | — | — | — | write (keeps .prev) |
| `notes/<own>/round-N/` | append | append | append | append |
| `bugs/<own>.md` | append | append | append | append |
| `rounds.json` | via case_new / round_* | — | — | — |
| everything else | refused | refused | refused | refused |

"Append" = entries may only be added at the end of the file; the service writes only if the existing content is a prefix of the new content. "Write" = the whole file is overwritten and the previous version is kept as `<file>.prev` (only one version is kept, so that review can "check only the changed places"; no diff tool is provided for now, review compares by itself).

**Read** (enforced by the host: subagent definitions do not support per-identity path refusal, so this is implemented with the PreToolUse hook `guard_hook.py` — it acts only when the hook input carries `agent_type` ∈ front / analysis / polish / review, refuses according to the table below and gives the reason; it additionally refuses any Edit / Write by these four identities under `cases/`, and any Grep / Glob without a path or whose path is at the case root or above)

| What is read | front | analysis | polish | review |
|---|---|---|---|---|
| `intake/`, `report/`, `rounds.json` | allowed | allowed (`report/` and `intake/products/` of old runs refused; for the old–new difference read only the current products' diff.json) | allowed (`report/` and `intake/products/` of old runs refused; polish reads only this round's draft, sources table and handoff, not the products) | allowed |
| `notes/<own>/round-<current>/` | allowed | allowed | allowed | allowed |
| `notes/<own>/round-<old>/`, `notes/<other>/` | refused | refused | refused | `notes/analysis/round-<current>/` readable after this round's review.md has been written (the ordering in time is constrained by the review specification); everything else refused |
| `bugs/<own>.md` | allowed | allowed | allowed | allowed |
| `log/calls.jsonl` | — | — | — | readable after this round's review.md has been written |

The guard hook reads the current round and run_id from `rounds.json` to decide "old round" and "old run", and decides whether review has already issued its checklist from whether `report/<run>/review.md` exists. The host's `permissions.deny` is session-level and does not distinguish subagents, so it is not used.

## 4. Tools

All tools take `case_id` explicitly. They return JSON; on error they return `{"error": kind, "detail": explanation, "path": path involved}`, and the kind is only one of `forbidden` (identity not allowed), `not_found`, `conflict` (overwriting an append-only file, wrong ledger status, directory already exists), `invalid` (malformed JSON, missing field, invalid last sentence).

**Write (by identity)**

| Tool | Identity | Parameters |
|---|---|---|
| `write_intake` | front | case_id, name ∈ {facts, sources, answers, notes, constraints, handoff}, content → overwrite, keeping .prev; facts / sources / answers / constraints must be valid JSON, and every sources entry must contain key, doc, page, quote; after writing anything but the handoff the ledger's intake_dirty = true |
| `put_document` | front | case_id, name, bytes → put into `intake/documents/`; `name = prompt` writes `intake/prompt.md` |
| `dialogue_append` | front | case_id, speaker ∈ {client, front}, text → appends `### date \| round N.k \| speaker`, returns the entry number |
| `to_collect_append` | front, analysis | case_id, law, jur, url, why → appends one entry |
| `edit_report`, `edit_polished` | analysis, polish | case_id, run_id, edits[{old, new}] → change sentences of the draft or the polished report; each old text must occur exactly once, all or none |
| `write_report` | analysis | case_id, run_id, name ∈ {briefing, sources}, content, mode? → mode=append adds a part to the draft or adds and replaces source rows by id; writes `briefing.md` / `briefing.sources.json`; run_id must be the one in this round's ledger |
| `write_polished` | polish | case_id, run_id, name ∈ {polished, sources}, content, mode? → mode=append adds and replaces source rows by id; writes `briefing.polished.md` / `briefing.polished.sources.json`; for `briefing.polished.sources.json` polish submits only the id and where of the entries it keeps; the service copies claim, kind and ref from the draft, and it cannot add entries; the draft briefing.md is kept as is; requires the draft to exist already; `conflict` while the draft has not passed review |
| `render_pdf` | polish | case_id, run_id → runs the text checks first (`report_check` text_only) and renders nothing while they fail; renders the polished report into `briefing.pdf` with the fixed template (`agent/tools/render_pdf.py`), returns the total pages, the body pages before the appendices (5 to 10 expected), the page of each section and of the flowchart, the fill of each page, latex_errors and overfull; flowcharts come from the JSON in a flow block and are drawn by the template |
| `write_review` | review | case_id, which ∈ {intake, draft, final}, content, run_id? → `review_intake.md`, `report/<run_id>/review.md` or `review_final.md`; the last sentence must be that stage's verdict (`RUNNABLE` / `REVISE`; `POLISHABLE` / `REVISE`; `DELIVERABLE` / `REVISE`), and a `REVISE` in draft or final needs a `RETURN: <target>` line just before it (draft: analysis, front; final: polish, analysis, front), otherwise `invalid`; `conflict` when the file under review does not exist |
| `notes_append` | self | case_id, book, text → appends to `notes/<agent>/round-N/<book>.md`, automatically writing the entry header `### <book>-<n> \| date \| round N.k \| run_id`, returns the number; book is limited to the notebooks named in that agent's specification |
| `bug_append` | self | case_id, layer, symptom, expected, repro, workaround, affects_result? → with affects_result (honoured from analysis and review) the entry is marked and the run stops at `system_defect` until cleared (`clear_defect` writes `bugs/cleared.md`, called only by the orchestrator CLI); first checks the agent's own bugs file for a duplicate by symptom; if it is a duplicate, appends `recurrence round N` under the original entry, otherwise a new entry `### B-<n>` |

**Ledger (front)**

| Tool | Description |
|---|---|
| `case_new` | case_id → creates all subdirectories of `cases/<case_id>/`, an empty rounds.json (current = 1), and the four `notes/*/round-1/`; `conflict` if it already exists |
| `round_new` | case_id → current + 1, creates the four `notes/*/round-N/`; requires the status delivered, or a report-stage checklist that says `RETURN: front` |
| `round_revise` | case_id → revision number + 1 (resubmission after fixing what review sent back) |
| `round_set_run` | case_id, run_id → registers it in the current round; requires the derived status to be intake_ok and `intake/products/<run_id>/version.json` to exist; after registration intake_dirty is cleared |

**Status and self-checks (any identity, read-only)**

| Tool | Returns |
|---|---|
| `round_current` | case_id → the ledger's current entry plus the derived status (table in §2) and `return_to` |
| `review_status` | case_id, which ∈ {intake, draft, final} → the verdict of that checklist, its return target and its write time; returns `none` if it does not exist |
| `intake_check` | case_id → list: facts.json can be read in by the optimization layer (calls `validate_input` of `tax-opt`); it carries no answers, has instructed_on, past_payments is a top-level list and each row has date and payee_share; destinations are written; the jurisdictions of payer, payee, entities and destinations are inside the rule layer's scope; the fact keys of payer, payee, payment and entities are rule-layer variables; the payee's parent (parent_jur) is in entities; constraints.json holds only consider, exclude, allow_restructure, payback_max, allowed_subjects; the keys of answers.json are predicates; sources cover every key of facts and every entry has doc + page + quote; yes / no / unknown_asked in answers all have the client's words and those words appear in dialogue.md; entries with confirmed_by_client true have a confirmed_note; whether the derived status is intake_ok |
| `report_check` | case_id, run_id, target ∈ {auto, draft, polished} (auto = check the polished report when it exists) → list: the heading date equals instructed_on; the refundable amount and the figures that do not reconcile from past_payments are in the report; the polished body has no optimizer vocabulary and no sentence over 55 words; report header, sections one to seven, appendices A / B all present; no system identifiers; every sources entry has where and its ref exists (product paths can be opened; cite_id looked up with `clause` of `tax-db`); when checking the polished report it also reports `number_drift` (numbers in the report that are not in the draft), `claims_changed`, `where_unlocated`, spoken lead-ins, a case id or run_id left in the report, and a PDF that is stale or a body outside 5 to 10 pages; `numbers_omitted` and `sources_cut` only list what was cut and are not problems |

Self-checks only report, never change anything; the result is a list and the agent decides what to do; review still checks item by item according to its own specification and does not take a passed self-check as the standard. The two self-checks are the only place in the service that calls the other two services (importing their read functions, not via MCP).

## 5. Logging (host hook, not in the service)

- `.claude/settings.json` configures one PostToolUse hook with an empty matcher (all tools, including Read and every MCP), whose command is `agent/tools/log_hook.py`: it reads the JSON from stdin, derives the case_id from the first `cases/<case_id>/` path or `case_id` parameter appearing in `tool_input`, and appends one line to `cases/<case_id>/log/calls.jsonl`: `{time, session_id, agent, tool, input_summary}`; calls whose case_id cannot be derived are recorded in `cases/_log/calls.jsonl`. `agent` is taken from the hook input's `agent_type` (given by the host when a hook fires inside a subagent); failing that it is derived from the tool-name prefix (`mcp__tax-case-<agent>__`), and failing that it is recorded as `unknown`. `input_summary` keeps only keys such as path, name, book, run_id, not the body text.
- The advantage of logging this way is that it covers the host's Read: when an agent Reads `ranking.json` directly, that is in the log too, which a server-side log could not do.
- After this round's review.md is written, review reads `log/calls.jsonl` and checks one thing: the time of analysis's `notes_append(book = precommit)` is earlier than its first read of ranking / deltas (`ranking` / `deltas` of `tax-opt`, or Read of `…/ranking.json`). If it is not earlier, review adds an entry to the checklist: "doubt: pre-commitment later than viewing the results". This is the only objective way to check pre-registration.

## 6. Isolation rules (the part enforced by the service)

1. Any write outside one's identity is `forbidden`.
2. `dialogue.md`, `notes/*`, `bugs/*`, `to_collect.md` are append-only; the service writes only if the file's existing content is a prefix.
3. `notes_append` writes only to the current round's directory; any non-current round is `forbidden`.
4. After writing any intake file but the handoff, `intake_dirty = true` is set; `round_set_run` requires the derived status to be intake_ok, otherwise `conflict`. This is the machine guarantee of "run only when RUNNABLE".
5. The run_id of `write_report` must be the one registered in the current round; likewise the run_id of `write_review(draft / final)`.
6. `write_polished` requires a draft that passed review. This is the machine guarantee of "review before polish".

Read isolation (analysis does not read old rounds, review does not read analysis's working papers before issuing its checklist, nobody reads anyone else's working papers) is borne by the host's permission rules, see §3.

## 7. Identity binding and configuration

- `.mcp.json` is the project-level master list; the orchestrator and the front entry connect each agent only to its own services (`.claude/mcp/<name>.json`, generated by `make_agents.py`, with `--strict-mcp-config`), and isolation relies on that list and the tool allowlist in each subagent definition: the front agent mounts `tax-case-front`, `tax-db`, `tax-rule`, `tax-opt-front`; the analysis agent mounts `tax-case-analysis`, `tax-db`, `tax-rule`, `tax-opt`; the review agent mounts `tax-case-review`, `tax-db`, `tax-rule`, `tax-opt`; the polish agent mounts only `tax-case-polish` and `tax-db`. All four mount Read, Glob, Grep, and the front, analysis and review agents also mount WebSearch and WebFetch; Bash is given only to the front agent (hardly needed except for placing documents and starting a run), and `Bash(*optimize.py run*)` is added to the deny list of analysis and review as a second safeguard.
- Tools with the same name across services (`requirements`, `version`, `diff`) are prefixed by the host with the service name, so they do not clash; when the agent specifications mention them they write "the rule layer's requirements", "the optimization layer's diff".

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

- Environment: all four services use the same Python (`tax`); after `conda activate tax` run `pip install "mcp[cli]"` (checked 2026-11-01: not yet installed); `<tax env python>` is filled with that environment's interpreter path.
- File `agent/tools/case_server.py`, dependencies only `mcp` and the standard library; the self-checks import the read functions of `optimization/tools/optimize.py` and `database/tools/mcp_server.py`.
- The four subagent definitions are generated by `agent/tools/make_agents.py` from the ```text prompt blocks of the four agent specifications into `.claude/agents/<front|analysis|polish|review>.md` (frontmatter: name, description, tools allowlist, model: inherit; the review body contains three prompt passages, and the orchestrator's task names which one to use). Rerun it whenever a specification changes; do not hand-edit the generated files.
- Hooks are in `.claude/settings.json`: PreToolUse (matcher `Read|Grep|Glob|Edit|Write|MultiEdit|NotebookEdit` → guard_hook.py) and PostToolUse (empty matcher → log_hook.py), in exec form, the command being the absolute path of the `tax` environment's interpreter and the script path using `${CLAUDE_PROJECT_DIR}`.
- Tests (part of the build, not a test battery): `agent/tools/test_case_server.py` starts the four identities against a temporary case and runs through the write-permission table (one assertion per cell), the prefix check of append-only files, the six status-derivation cases, the "run only when RUNNABLE" conflict, and the invalid of the last-sentence validation; `log_hook.py` is tested with a forged hook input for the inference of case_id and agent; `guard_hook.py` runs 21 read/write cases against a synthetic case tree (see the build record).

**Build record (2026-11-01)**: case_server, log_hook, guard_hook, make_agents, `.mcp.json`, `.claude/settings.json` and the three subagent definitions are all built; test_case_server 52 items and guard 21 items pass; the stdio handshake of the three identities tested and passed. One correction in status derivation: intake_ok looks at `review_intake_written` being strictly later than `last_intake_write` (microsecond timestamps), and intake_dirty is cleared after review writes.

**Build record (2026-11-01, evening, polish agent added)**: the fourth identity, polish, is added — the flow becomes analysis writes the draft (status drafted) → polish rewrites polished.md / polished.sources.json + PDF (status polished) → review checks the polished report (comparing it to the draft to confirm the conclusions and the numbers have not changed) → delivered; status is derived from file mtimes (a re-drafted draft → back to drafted, a re-polished report → back to polished). `write_polished`, `render_pdf` (a subprocess calling render_pdf.py, ctexart template; no `-halt-on-error`, as otherwise a single undefined control sequence truncates the whole thing to one page; the JSON in a flow block is drawn by the template with TikZ in a fixed layout, so polish does not draw; other fenced blocks keep their spaces; numbered lists and multi-page tables are supported), and report_check gained target and three reconciliations (`number_drift` compares all numbers of both bodies, `claims_changed` compares both sources tables, `where_unlocated` requires verbatim fragments), with internal vocabulary added to the identifier check. First live run (qwen3.7-max on CASE-E2E-001): 10 pages and all numbers intact, but 40 of 81 where fragments unlocated, internal words left in the body and 6,130 characters of prose over target; not rerun yet. guard / log / make_agents / .mcp.json updated for polish; test_case_server updated and passes. Polish runs on qwen3.7-max.

**Build record (2026-11-01, night, review moved before polish)**: status gains reviewed; review has three stages (`review.md` on the draft, `review_final.md` comparing the report); `RETURN` line validation; `round_current` returns `return_to`; `round_new` widened; `write_polished` requires a passed draft; writes of sources and notes also send the package back for review; Chinese verdict tokens are no longer accepted; `report_check` reads spoken labels and process wording in English reports. The orchestrator `agent/tools/orchestrate.py` is in `agent/orchestration_cli_spec.en.md`.

## 8. Not done

No reading (host Read / Glob / Grep); no logging (host hook); no search or internet access; no tax judgments; no changes to any file of the other three layers; no merging of working papers on the agents' behalf; no direct client access (the client interface is the UI layer's business).
