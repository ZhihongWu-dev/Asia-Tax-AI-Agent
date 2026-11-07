# Orchestration and CLI specification (minimal set)

English copy of `agent/编排CLI规范.md`; when the two differ the Chinese version prevails.

2026-11-01. This document defines only how the four agents are started, the order they run in and when the flow stops. Each agent's duties are in its own spec; case reads, writes and the ledger are in `agent/case_mcp_spec.en.md`. The implementation file is `agent/tools/orchestrate.py`, its checks are in `agent/tools/test_orchestrate.py`.

**Language**: only the body of the Chinese spec is in Chinese. Everything else is in English: code, comments, logs, the task text handed to agents, and the CLI's prompts, status and stop messages.

## 1. Position

| Layer | Uses | Owns |
|---|---|---|
| Execution | Claude Code | Running agents: dialogue, tools, MCP, hooks |
| Orchestration | LangGraph | The next step: nodes, branches, return loops, stops |
| Facts | Case files | Status, products, checklists |

- The front agent is the only interactive session and the only agent the client talks to. Analysis, polish and review are each started by the orchestrator as a headless `claude -p`, with a fresh context every time. The front no longer starts them as subagents.
- The orchestrator makes no tax judgment, changes nothing an agent wrote and does not replace review. It looks only at files, checklist verdicts and the two self-checks.
- LangGraph only: no LangChain model or agent layer, no LangSmith, no account needed.
- All status is derived from the case files and the graph holds no business state, so there is no checkpointer. After an interruption, running `run` again continues from the current status.
- An agent's own report does not count. A node is complete only if the files were updated and the self-check is clean.

## 2. Flow

The order is analysis, review of the draft, polish, review of the final report. Substance is settled before expression changes; after polish, the only question is whether the meaning changed.

**Nodes**

| Node | Run by | Entry status | Does | Complete when |
|---|---|---|---|---|
| `review_intake` | review | intake | First a program gate: `intake_check` clean and `handoff.md` written, otherwise `need_front`; then checks the intake package | `review_intake.md` was updated and has a valid verdict |
| `run` | program | intake_ok | Builds `intake/run_input.json` from facts.json plus `closing_answers(answers.json)` and the constraints of constraints.json (exclude, consider, allow_restructure, payback_max, allowed_subjects), then `validate_input`, optimizer `run`, `round_set_run`; `diff` when there is an earlier round | The ledger has a run_id |
| `analysis` | analysis | ran | Writes the draft and its sources | The draft or its sources were updated and `report_check(draft)` has no problems |
| `review_draft` | review | drafted | Checks the substance of the draft | `review.md` is newer than the draft and has a valid verdict |
| `polish` | polish | reviewed | Rewrites the report and produces the PDF | The report files were updated and `report_check(polished)` has no problems |
| `review_final` | review | polished | Compares the report with the draft | `review_final.md` is newer than the report and has a valid verdict |

**The three review stages**

| Stage | Checks | File | Verdict |
|---|---|---|---|
| 1 | The intake package against the original documents | `intake/review_intake.md` | `RUNNABLE` / `REVISE` |
| 2 | The draft's figures, law, structure, open items and assumptions | `report/<run_id>/review.md` | `POLISHABLE` / `REVISE` |
| 3 | Whether the report changed any meaning, lost any premise and reads clearly for the client. Substance is not reviewed again | `report/<run_id>/review_final.md` | `DELIVERABLE` / `REVISE` |

A `REVISE` checklist carries a line `RETURN: analysis`, `RETURN: polish` or `RETURN: front` before the verdict. Stage 1 always returns to the front and has no such line; stage 2 may not say `polish`. When a checklist involves several parties, name the earliest in the flow, because everything after it is redone.

**Status** (replaces drafted, polished and delivered in §2 of the case spec and adds reviewed; the rest is unchanged)

| Status | Condition |
|---|---|
| drafted | `briefing.md` exists; `review.md` is missing, older than the draft or ends with `REVISE` |
| reviewed | `review.md` ends with `POLISHABLE` and is newer than the draft; the report is missing or older than `review.md` |
| polished | The report is newer than `review.md`; `review_final.md` is missing, older than the report or ends with `REVISE` |
| delivered | `review_final.md` ends with `DELIVERABLE` and is newer than the report |

**Routing**

| Result | Next |
|---|---|
| `RUNNABLE` | `run` |
| Stage 1 `REVISE` | Stop, `need_front` |
| `run` complete | `analysis` |
| Analysis self-check has problems | `analysis` again, with the problem list in the task |
| `POLISHABLE` | `polish` |
| `RETURN: analysis` (stages 2, 3) | `analysis` |
| Polish self-check has problems | `polish` again, with the problem list in the task |
| Polish recorded new `issues` and made no PDF | `analysis`, with the `issues` text in the task |
| `RETURN: polish` (stage 3) | `polish` |
| `RETURN: front` (stages 2, 3) | Stop, `need_front` |
| `DELIVERABLE` | End, `delivered` |

On every `REVISE` return the program first calls `round_revise`, which adds one to the revision number. When analysis rewrites the draft, the file times drop the status back to drafted, so review and polish run again by themselves. A re-check covers only what changed, as the review spec says.

**Stops**

| Stop | Meaning | Who takes over |
|---|---|---|
| `delivered` | The report can be delivered | The front hands it to the client |
| `need_front` | The intake package or the facts must change | The front reads the checklist, fixes the package, asks the client if needed and calls `run` again |
| `revision_limit` | One node has run 6 times in one `run` (raised from 4 on 2026-11-05: a trial stopped one wording fix short; past the limit a person resumes it) | A person |
| `agent_failed` | Process failure, timeout, turn limit, or no file updated | A person |
| `system_defect` | An `affects_result` bug of this round is not cleared | A person: after the fix, `orchestrate.py clear <case_id> <agent/B-n>`, then continue |
| `rate_limited` | The gateway is rate limiting | A person, who calls `run` again when quota returns |
| `busy` | A `run` already holds this case | Wait for it to end |

In a round with a registered run_id, a return to the front means the facts change and the results must be recomputed. The front then calls `round_new` to open a new round with a new run_id. `round_new` requires the status delivered or a report-stage checklist that says `RETURN: front`. With unchanged facts the optimizer gives no new run_id, and the orchestrator stops with `need_front`.

## 3. CLI

**Entry points**

| Command | Does |
|---|---|
| `python agent/tools/orchestrate.py front [case_id]` | Starts the interactive front session |
| `python agent/tools/orchestrate.py run <case_id>` | Walks from the current status to a stop and prints one JSON line: status, stop, detail, run_id, nodes run |
| `python agent/tools/orchestrate.py status <case_id>` | Read only: current status, next node, last stop |
| `python agent/tools/orchestrate.py graph` | Exports the node graph to `agent/orchestration_graph.mmd` |

Python is the `tax` environment's interpreter. Once `handoff.md` is written and `intake_check` is clean, the front runs `run` through Bash in the background and continues according to the stop. The products appear only in the `run` node, so `handoff.md` holds no diff and the analysis agent reads `diff.json` itself.

**Agent settings**

| Agent | Model | Mode | max_turns |
|---|---|---|---|
| front | qwen3.8-flash | interactive | none |
| analysis | qwen3.8-flash | headless | 150 |
| polish | qwen3.8-flash | headless | 90 |
| review | qwen3.8-flash | headless | 80 |

**Headless call**

```
claude -p "<task>" --agents .claude/agents.json --agent <name> --mcp-config .claude/mcp/<name>.json --strict-mcp-config --output-format stream-json --verbose --include-partial-messages --max-turns <n> --allowedTools <list>
```

| Environment variable | Value |
|---|---|
| `ANTHROPIC_BASE_URL` | `https://token-plan.cn-beijing.maas.aliyuncs.com/apps/anthropic` |
| `ANTHROPIC_AUTH_TOKEN` | `qwen_key` in `.env` |
| `ANTHROPIC_MODEL` | The model above |
| `ANTHROPIC_SMALL_FAST_MODEL` | `qwen3.8-flash` |
| `ENABLE_TOOL_SEARCH` | `false`, required by the Qwen gateway |
| `CLAUDE_AGENT_NAME` | The agent's name, the hooks' fallback identity |
| `MCP_SERVER_CONNECTION_BATCH_SIZE` | `8`, one batch |
| `LANGSMITH_TRACING` | `false`, also set in the orchestrator itself |

- The key travels only in the child process environment, never on the command line, in logs or in error messages.
- The working directory is the project root, which the relative paths in `.mcp.json` rely on.
- The executable is found in this order: the `CLAUDE_BIN` variable, `claude` on PATH, the newest `claude.exe` in the VS Code extension folder.
- Besides `.claude/agents/*.md`, `make_agents.py` also generates `.claude/agents.json`, because headless `--agent` does not find project definitions. `--allowedTools` comes from the same tool table.
- `make_agents.py` appends a saving note to each agent's prompt (`SAVE_TOOLS`): the agents have no `Write` tool and save every file through the case server. In a real run the review agent, finding no `Write`, put its checklist in its reply, and the node failed with nothing on disk.
- `make_agents.py` also generates `.claude/mcp/<name>.json` from `.mcp.json`, so each agent connects only its own servers. The CLI connects MCP servers in batches and the first model turn does not wait for all of them; with all eight connected, the agents late in the order start without their tools, with no error, and simply say the tool is unavailable.

**Task text**: the prompts live in the agent specs; the orchestrator hands over one short English task, verbatim as below.

| Node | Task |
|---|---|
| `review_intake` | `Check the intake package of case <case_id>.` |
| `analysis` | `Write the briefing draft for case <case_id>, run <run_id>.` |
| `review_draft` | `Check the briefing draft of case <case_id>, run <run_id>.` |
| `polish` | `Polish the reviewed draft of case <case_id>, run <run_id> and produce the PDF.` |
| `review_final` | `Compare the polished report with the draft of case <case_id>, run <run_id>.` |

A repeat run adds `Revision <n>. Reason: <reason>`, where the reason is the checklist path (`see <path>`), the self-check problems or the `issues` text.

**Processes**

- Each node has a 60-minute timeout. On timeout or when the orchestrator is interrupted, it ends the whole process tree with `taskkill /T /F`. Killing only the outer process leaves `claude.exe` alive and still writing files.
- A network error is retried once. A rate limit is not retried and stops the run.
- One `run` per case at a time: `cases/<case_id>/log/run.lock` holds the PID and is taken over when that PID no longer exists.

## 4. Graph

- The graph state holds flow information only: `case_id`, `next`, `last_node`, `stop`, `detail`, `reason`, `redo`, the node counts and the nodes run.
- The nodes are `dispatch` plus the six in §2. `dispatch` picks the entry from `round_current` and the checklists, so the graph can resume from any status.
- After every node the status is derived from the files again before routing.
- Conditional edges name their legal destinations, so the exported graph shows only real paths.
- `recursion_limit` is 60; the real bound comes from `revision_limit`.
- `need_front` ends a `run`. There is no `interrupt`, so it does not matter how long the client takes to come back.
- Program steps call the case code with the front identity. The optimizer goes through `mcp_call.py` in its own process, because its server shares a module name with the database server.

## 5. Records and visualisation

- `cases/<case_id>/log/runs.jsonl`: one row at the start and one at the end of each node, with time, node, agent, model, round, revision, attempt, session_id, turns, seconds, status_before, status_after and stop.
- `cases/<case_id>/log/runs/<n>-<node>.jsonl`: the CLI event stream, written live; the thinking is here too.
- The node graph comes from `graph`. Progress and history are shown by the UI layer from `runs.jsonl` and `round_current`.

## 6. Build record

Built 2026-11-01: `orchestrate.py`; the case server's new status, three review stages and `RETURN` validation; `make_agents.py` generates `.claude/agents.json`, the front no longer has the `Agent` tool, and a missing English copy is an error; the agent specs follow the new flow. `test_orchestrate.py` plays the agents from a script, so routing, status and limits run for real, and it checks with real child processes that a timeout ends the whole process tree. Wiring test: analysis, polish and review each ran one real `claude -p` and read the case status through MCP under their own model and identity. The full flow has not yet run with real agents, and the interactive front entry has not been tested.

On a re-check the orchestrator writes the difference from what review last read to `log/review_changes-<node>.md`, and the task asks review to check those changes and the items it sent back; within one round only, a new round is checked from scratch.

2026-11-02, first real full flow, through the web host to `delivered`: the English case, 15 documents, about 3 h 17 min of node time, a 7-page PDF, final comparison `DELIVERABLE`. Found and fixed along the way: review put its checklist in its reply because it had no file tool (the saving note); analysis was cut off at 1 hour (the node timeout is now 3 hours); `render_pdf` swallowed the real error on failure (a duplicate argument to `err`). Local fixes the same day: the host filters paths and ids from everything it sends the client; the restart limit, a run outliving a killed server, Stop and Resume passed on real processes; the optimization layer no longer loses facts placed on the entities, expands forks until stable, always has the all-favourable world and treats the stated parent as a known entity; HK and JP companies use marginal schedules. No full real run has covered these fixes yet.

## 7. Out of scope

Agents in parallel; the LangChain agent layer; LangSmith, a checkpointer and LangGraph Studio (it needs `langgraph-cli`, and its account and trace upload questions are unverified); letting a model decide the flow; a client interface (the UI layer's job).

## 8. Web host

`apps/api/server.py` is the API behind `apps/web`: one local user, bound to 127.0.0.1. Start it with `C:/Coding/Anaconda/envs/tax/python.exe apps/api/server.py` and open http://127.0.0.1:8000.

- A client message is one headless front-agent turn, continued with `--resume`. Its event stream goes to `log/runs/<n>-front.jsonl`, is read as it grows, and reaches the page over SSE: the reply as `delta`; thinking, tool calls and text before a tool call as `activity`. The conversation is stored in `cases/<case_id>/chat.json`.
- The host writes each client message to `dialogue.md` word for word, and the case server refuses client entries from the front: in a real run the front wrote an "I do not know" in the client's name to pass a check.
- In web mode `--append-system-prompt` adds a note that replaces the Bash step of the front's step 4: the front does not run `orchestrate.py` itself; when ready it ends its reply with `[[START_RUN]]`. The host removes the mark and starts the orchestrator as its own process, so a server restart or a page reload does not interrupt a run.
- When a run ends: on `delivered` and `need_front` the host sends the front a `[Host]` message and the front tells the client in its own words; on `delivered` the host adds the PDF link. `rate_limited`, `agent_failed` and `revision_limit` call no model; the host posts a fixed text. Without a client message a run restarts automatically at most 3 times; at the limit it stops and tells the client, which prevents a loop.
- Progress is read from files, not from the process. `GET /api/cases/{id}/run?after=<cursor>` returns the node states (`runs.jsonl`, `run.lock`, `round_current`) and the new entries from the agents' event streams. A revision moves the stage back: later nodes return to pending and keep their run counts.
- `POST /api/cases/{id}/run` continues from the current status; `POST /api/cases/{id}/run/stop` ends the whole process tree and logs a `stopped` row.
- The reader removes the key as well: streams are read during a run, and `scrub` only runs when a node ends.

Limits: up to 30 attachments per message; one user, no real sign-in; a run needs Claude Code, xelatex and a persistent disk on the machine, so it cannot sit on stateless hosting.

## 9. Feedback, preview and revised editions (designed 2026-11-02, trial implementation the same day)

### 9.1 Problem and principles

Today every point the client brings back opens a new round, and the report is rewritten in full from the intake review on, about 2 hours. The time goes into the analysis, which writes the report from scratch every round; the optimization takes seconds.

Principles:

1. **One round is one edition of the formal report.** Feedback no longer means one round per point: the points the client brings back accumulate in the current round, and each produces only a program-generated preview card; a new edition is written only when a condition of §9.4 holds.
2. **The program chooses the path, not a model.** Whether to write a report, and whether to rewrite it in full or revise the last edition, is computed from the product differences and the ledger.
3. **When in doubt, rewrite in full.** Every decision has a fallback: a condition not met, a failed alignment, or a review that finds the text inconsistent all fall back to a full rewrite. The worst case is today's speed, never a wrong report.
4. **A revision starts from the last finished edition, not from notes.** The analysis and polish agents may read the last delivered report; no agent reads its notebooks across rounds, as before.
5. **Numbers still come only from this round's products.** Text carried over from the last edition is checked against this round's products like any other text.

### 9.2 Terms

| Term | Meaning |
|---|---|
| Feedback | A client message on which the front agent changed facts, answers or constraints |
| Preview | One optimization run on the current intake package, without registering a run_id; products in `intake/preview/<run_id>/`; only judgment points answered against the client are treated as closed |
| Preview card | `intake/preview/<run_id>/update.json`: a summary of the change, computed by the program from the preview products and the baseline products (§9.3) |
| Baseline edition | The last delivered report: its run_id, draft, sources table, polished report and products. A case's first report has no baseline |
| Revised edition | A new edition made by revising the baseline: only the affected parts are rewritten, the rest is carried over |
| Full rewrite | Written from scratch: today's flow |

### 9.3 Flow

```text
client feedback ── front updates the intake ── intake_check clean ── preview (optimization, about 6 s) ── preview card ── front relays it (1–2 min)
                                                                                                │
                                                                          any condition of §9.4 ┘
                                                                                                ▼
review_intake (light / full) ── run ── impact ──┬── none   : stop no_change, the report stands, the front tells the client
                                               ├── revise : analysis (revise) ── review_draft ── polish (carry unchanged parts) ── review_final
                                               └── full   : today's flow
```

**Preview card** (`update.json`, from a new optimization-layer subcommand `card --products <preview> --against <baseline products> --answers <answers.json>`; JSON only, no prose):

| Field | Meaning |
|---|---|
| `first` | The first structure under the all-favourable scenario: its signature, tax interval, and its name in the baseline edition, such as Plan B (from the naming entries of the sources table, §9.8) |
| `first_changed` | Whether the first structure differs from the baseline edition's |
| `worst` | The first structure and tax under the all-unfavourable scenario |
| `baseline_first_now` | The favourable and unfavourable tax of the structure the baseline edition recommended, and whether an unfavourable answer has closed it |
| `pending` | The judgment points and fact gaps that can still change the first structure, worded as questions the client understands (the rule layer's `question`) |
| `triggers` | True or false for each condition of §9.4, with the reason |
| `time_only` | Figures that changed only because the as-of date moved, such as interest; not shown to the client |

The front agent relays the card in its own words; the host checks the figures against `update.json`, as it checks the delivery note. A preview card has passed the program checks only, not a review, so the front agent must say it is preliminary and that the report is the formal conclusion.

### 9.4 Conditions for a formal report

When any condition holds, the front agent ends its reply with `[[START_RUN]]`. Conditions 1 and 2 are computed by the program and written into `triggers`; when one of them is true and the front agent did not write the marker, the host starts the run itself.

| # | Condition | Decided by |
|---|---|---|
| 1 | Every judgment point that can change the first structure has a yes or no, and every fact gap that can change it is filled; `unknown_asked` does not count as answered | Program |
| 2 | The structure the baseline edition recommended has failed: the client answered against it a judgment point it relies on and the branch is closed; or a new fact makes it break a hard constraint, such as the payback ceiling or an excluded jurisdiction; or its all-favourable tax is now higher than the report states, for example because the law in the library changed | Program |
| 3 | The client needs a formal document to act on, such as for a board, lawyers or the tax authority | Front agent, from the client's words |
| 4 | The client asks for a new report | Front agent, from the client's words |
| — | The case has no report yet | Written as soon as the intake package is complete, as today |

When the first structure changes but none of these conditions holds, for example when the net assets make the transfer uneconomic, only the preview card is issued: the client learns the new direction at once, and the report waits for a condition.

### 9.5 Impact (`impact` node)

A program node `impact` runs after `run` and before `analysis` and writes `report/<run_id>/impact.json`. It aligns this round's products with the baseline products by **structure signature**, not by cand_id: the signature is the path plus the moves plus the kind of restructuring. cand_id and branch_id are renumbered on every run; in the rerun of 2026-11-02 c1 and c2 swapped. The current `diff` aligns by id and must be changed first, see §9.10.

**Levels**

| Level | Condition (checked in order; the first that holds wins) | Next |
|---|---|---|
| `full` | No baseline edition; or rule.csv or doc.csv changed, so the law in the library changed and every citation has to be checked again; or the hash of the analysis or report spec changed; or this round's first structure is not among the structures the baseline edition discussed; or there have been 3 revised editions in a row; or the review asked for a full rewrite (§9.6) | Full rewrite |
| `none` | Nothing in the products that the report uses changed (order, the tax of every scenario, open items, condition trees, one-off cost, and exposure apart from `time_only`), and facts.json and answers.json have no change of content since the baseline | Stop `no_change` |
| `revise` | Otherwise | Revised edition |

**Parts to change**: the program maps product changes to sections and writes them into `sections` of `impact.json`.

| Product change | Sections that must change |
|---|---|
| The first structure changed | 1 Strategy, 4 Optimal, 6 Requirements, 7 Implementation, the table of 5, and the paragraphs of 3 on the old and the new first structure |
| The tax or order of any scenario changed | 1, 5, and the paragraphs that quote those figures |
| The first structure's condition tree or reference_params changed | 6, 7 |
| Open items or answers changed | Appendix A, the first step of 7 |
| One-off cost or exposure changed | 4, 6, and the paragraphs that quote those figures |
| The tax of the current structure or the account of past payments changed | 2 |
| A structure appeared or vanished | 3, 5 |

**Stale figures**: the program takes the values present in the baseline products and absent from this round's, finds where they occur in the whole baseline draft, and lists them in `stale` with section and sentence fragment. Those sentences must change, whether or not their section is in `sections`.

**Changes note**: a revised edition opens Part 1 with a paragraph on what changed since the last edition: which points the client confirmed, whether the conclusion changed, and why. Its content may come only from `impact.json`. A full rewrite has no such paragraph.

### 9.6 Each step in a revised edition

| Step | Light / revise mode | Entry condition | Fallback |
|---|---|---|---|
| `review_intake` | Checks only the changes since the last `RUNNABLE`. The program compares with the snapshot (§9.8), writes `log/intake_changes.md`, and each change is checked against the documents and the client's words | A snapshot exists, no new documents, at most 10 changed leaves | Otherwise a full check |
| `analysis` | Reads the baseline draft and sources table, `impact.json` and this round's products, and delivers a **complete** new draft and sources table. The places listed in `sections` and `stale` must be rewritten; the rest may be carried over as it stands, after confirming against this round's products that it still holds. Structures keep their baseline names: Plan A stays Plan A, a new structure takes the next letter | `impact.level = revise` | When carried text cannot be reconciled with the new facts, the agent records the line `REWRITE: full` in this round's notebook with `notes_append`; the orchestrator then switches to a full rewrite |
| `review_draft` | Checks `sections`, `stale` and the changes note; the program checks every figure of the whole text against this round's products; the reviewer reads the carried parts for contradictions with the changes | Same | The checklist writes `REWRITE: full` before its last line; the analysis is sent back for a full rewrite, which does not count as an ordinary revision |
| `polish` | The program first carries over, verbatim, the sections of the baseline polished report whose draft section is unchanged, aligned by section heading; the polish agent works only on the other sections; `render_pdf` makes the PDF again | The headings of the baseline polished report and the baseline draft correspond one to one | Otherwise the whole report is polished |
| `review_final` | Compares only the changed sections; the program checks that the carried sections are unchanged word for word | Same | As today |

### 9.7 Concurrency and dates

- **Feedback while a run is active**: the host records it verbatim in `dialogue.md` as usual. While `run.lock` exists, the case service refuses the front agent's writes to facts, answers, constraints and notes. The front agent tells the client the point will be taken into the next step. When the run ends, the host's `[Host]` message includes what the client said since the run started; the front agent then writes it into the intake package and issues a preview card.
- **First feedback after a delivery**: the front agent calls `round_new` first, as today, and then edits the intake package. Later feedback stays in that round until a new edition is delivered.
- **As-of drift**: every run's as-of date is the day of the run, so interest moves with it. Figures that change only with the as-of date go into `time_only`; they do not affect the `none` decision and do not trigger a report on their own; once a report is written they are updated from this round.
- **Retracted answers**: when the client changes an answer, answers.json changes with it and a closed branch reopens. The preview card is computed as usual, and the baseline recommendation may come back.

### 9.8 Ledger and files

| Item | Change |
|---|---|
| `rounds.json`, per round | Adds `baseline_run` (the run_id of the last delivered edition, null if none), `mode` (full / revise / none), `revise_chain` (revised editions in a row) and `spec_sha` (hash of the analysis and report specs) |
| Intake snapshot | On `write_review(intake, RUNNABLE)` the service copies facts, answers, sources, constraints and notes to `intake/reviewed/round-N/`, the baseline for the next light check and for the `none` decision |
| Preview directory | `intake/preview/<run_id>/`; not registered, not under `report/`, not counted as an old run's products |
| Sources table | A new entry kind `kind: name`: `{where: "Plan A", ref: <structure signature>}`. The preview card and revised editions keep names through it |
| Read guard hook | With `mode = revise` the analysis agent may read `report/<baseline_run>/briefing.md` and `briefing.sources.json`, and the polish agent `report/<baseline_run>/briefing.polished.md`; other reads of old runs stay refused; the notebook rule is unchanged |
| Stop reasons | Adds `no_change`: the front agent tells the client the report stands and gives the points of the preview card |
| Task text | A revised edition appends `Mode: revise against run <baseline_run>; see report/<run_id>/impact.json` |

### 9.9 Invariants and self-checks

Each is checked by the program, not left to a model.

| Invariant | Check |
|---|---|
| Every figure of the new draft is found in this round's products, the intake package or a registered tool output | `report_check(draft)` checks the whole text, carried paragraphs included |
| Every sentence in `stale` changed in the new draft | `report_check` compares: those fragments may not appear unchanged |
| The sections in `sections` did change, and the changes note quotes only `impact.json` | `report_check` compares with the baseline draft |
| Structure names agree with the baseline | The `kind: name` entries of the sources table are compared with the baseline's: the same signature has the same name |
| Carried polished sections are unchanged word for word | `report_check(polished)` |
| Every figure of a preview card or delivery note is in the matching products | The host's figure check |
| No more than 3 revised editions in a row | `impact` reads `revise_chain` |
| Alignment only by structure signature | `diff`, `impact` and `card` share one signature function, with tests |
| Conditions 1 and 2 for a report can be recomputed by the program | `card` writes the reasons of `triggers`, covered by tests |

### 9.10 Existing problems to fix first

1. `optimize.py diff` aligns by cand_id and branch_id, so once ids are renumbered it treats different structures as the same one and every rank move is wrong. Align by structure signature instead, and branches by signature plus `answers_assumed`.
2. The `ref` of a sources entry names only a product file, not a field. Staleness is therefore found from the values present in the baseline and absent from this round, not from `ref`. `ref` keeps its format; the program only replaces the old run_id with the new one.
3. The `[Host]` message after `delivered` must carry the client's messages received during the run (§9.7).

### 9.11 Expected times

| Case | Time |
|---|---|
| Each feedback to its preview card | 1–2 minutes: one front turn plus 6 s of optimization |
| Revised edition | about 30–50 minutes: light check 5, analysis 15–30, review 5–7, polish 3–5, final comparison 3 |
| Full rewrite | as today, about 2 hours |
| `none` | under 1 minute |

### 9.12 Files to change on implementation

`optimization/tools/optimize.py` (`diff` aligned by signature, the `card` subcommand) and the two optimization-layer specs and its MCP spec; `agent/tools/orchestrate.py` (the `impact` node, modes, `no_change`, the revise task text); `agent/tools/case_server.py` (snapshot, the new `rounds.json` fields, refusing writes during a run, the revise checks of `report_check`, `kind: name`); `agent/tools/guard_hook.py` (baseline reads); `apps/api/server.py` (figure check of the preview card, the conditions, messages received during a run); the four agent specs and the case spec, each with its English copy; regenerate the prompts with `make_agents.py`.

### 9.12a How the trial implementation differs from the above

| Design | Implementation |
|---|---|
| The preview card comes from a new optimization-layer subcommand `card` | It comes from `agent/tools/impact.py`, which shares the structure signature with `impact`; it likewise only reads products and decides by rules |
| Preview products in `intake/preview/` | In `intake/products/<run_id>/`, unregistered; a formal run the same day gets the same run_id and reuses them |
| Feedback during a run is recorded and applied after it | The host refuses client messages while a run is active (409) and the page asks to wait |
| Four new `rounds.json` fields | Recorded in each round's `report/<run_id>/impact.json`: `baseline_run`, `level`, `revise_chain`, `spec_sha`, and the facts, answers and constraints of the time; revised editions in a row are counted from the rounds' impact.json |
| Intake snapshot `intake/reviewed/round-N/` | The existing `log/reviewed/review_intake/`, plus `documents.txt` with the list of documents |
| When a preview card is made | After every front turn the host checks: a baseline edition exists, no run is active, `intake_check` is clean, and the hash of the run input and answers differs from the last preview; then it computes the card and starts one more front turn to relay it |

### 9.13 Relation to the goals

`目标.md` §4.2 item 6 says "open a new round … rerun as a whole … write a new report". This design keeps the full optimization rerun and the comparison of two runs, but changes two things: feedback accumulates before a report is written, and a report may be a revision of the last edition. That item has to be amended with the user's consent; until then this design is not implemented.

## 10. Drafting in parts (2026-11-03)

Why: a full analysis took 87 minutes, and most of it was the model writing: 172 thousand output tokens, of which the sources table (about 46 thousand characters) was sent whole three times. The draft is therefore split so that the program writes what it can, the parts are written at the same time, and nothing is resent whole.

| Step | Who | What |
|---|---|---|
| Frame | program (`agent/tools/sections.py` build_frame) | `report/<run_id>/frame/`: names.json (the structures the report discusses, keyed by cand_id, with signature and plain label; names of the last delivered edition are kept, a new structure takes the next free letter, the as-is structure is "Current structure"), blocks/*.md (tax comparison by step, scenario table, points to confirm, exposure if denied, gaps), blocks.sources.json, frame.md (what the writers read) |
| Section writers | analysis identity, in parallel | groups: Part 2; Parts 3 + 5; Parts 4 + 6; Part 7 + Appendix A. Each writes `report/<run_id>/sections/<part>.md` and `<part>.sources.json` with `write_section`; a table is inserted by its marker `{{block:<name>}}` |
| Assembly | program (assemble) | briefing.md and briefing.sources.json from the parts in order, markers replaced by the tables, the tables' sources added, one kind-name source per structure named, Appendix B from the cite / url / document sources, the internal reference line |
| Integrator | analysis identity, one pass | precommit first; then the heading with the opening declaration (section head) and Part 1; then consistency across the parts with `edit_section` / `write_section`; ends with report_check. Every write after assembly reassembles the draft |
| Return from review | analysis identity, one pass | as before, but on the parts: `edit_section` / `write_section` |

Rules: a sectioned draft refuses `write_report` of the whole briefing and any write of the sources table that is not an append (extra rows go to sections/extra.sources.json). Part B and the reference line are the program's. A revised edition (§9) runs only the groups whose parts impact.json lists; the program carries the other parts from the last delivered draft, with their sources and with product refs moved to this run where the same file exists, and the integrator writes the note of what changed. A failed writer leaves its parts missing; the integrator is told to write them. Products without brief.json (old runs, tests) fall back to one agent writing the whole draft. `SECTIONED` in orchestrate.py switches the whole mechanism off.

## 11. Reading and retrieval hooks (2026-11-03)

The retrieval layer is designed in `agent/retrieval_spec.en.md`. The orchestrator does four things for it, all program steps:

| When | What |
|---|---|
| After an optimizer run is registered (and after a preview run) | Builds the run's products index `intake/products/<run_id>/index/records.sqlite` |
| Before review_intake | Builds the case-file index and reads the scanned documents once by OCR (cached by file hash, `intake/index/`) |
| Before review_intake, analysis, review_draft, review_final (and polish, §12) | Writes the prefetch pack `report/<run_id>/pack/<node>.md` (under `intake/index/pack/` while there is no run) and names the pack and the case's file list in the task |
| Delivery check | report_check runs cite_check on the draft |

A failure of any of these is logged in one line and does not fail the node: the agent can still find things itself with tax-read.

## 12. The legal-reasoning lane and re-check scope (2026-11-03)

review_draft and review_final each run two review agents at the same time: the main review (stages 2 and 3 of the review spec) and the legal-reasoning lane (stage 4, `agent/review_agent_spec.en.md` §3a). Why: the round-3 reviews of CASE-20261102-a032c0 passed a wrong statement of the Singapore headline-rate test three times; checking each sentence's reason against the provision is a separate job from checking figures against products.

| Step | What the program does |
|---|---|
| Before the node | Marks the run (`report/<run_id>/.lanes`), so the stage passes only when both checklists pass; writes the lane's extract with `agent/tools/reasons.py` (`pack/legal_draft.md` or `pack/legal_polished.md`): the sentences that state a legal reason with their rows, the citations each sentence names in words (resolved by the program, back references within the paragraph included), the provisions (thresholds and conditions in full first, shortened only when the extract would be too long), rules with parameter values, and decisions; every provision the recommended structure's all-favourable branch applies is laid out too, so the lane looks there before searching (speed-up of 2026-11-04) |
| Which sentences | review_draft, first check of the run: all; re-check: those on lines changed since the last check of the same run; review_final: those of the polished report not word for word in the draft |
| Nothing to check | When the extract is empty and the last lane checklist passed (or there is none to re-check), the program writes the lane's checklist with the pass verdict and the lane does not run |
| During the node | The lane runs in a thread beside the main review (`review_legal`, `review_final_legal` in log/runs/); its turns and seconds go into the node's row (`lane_turns`, `lane_seconds`) |
| After the node | A lane failure or a lane that wrote nothing fails the node. When either checklist says REVISE, the furthest return wins (front, then analysis, then polish) and the author's task names every checklist that sent it back |

Re-check scope: a review node is told "this is a re-check" only when its last checklist was of the same run of the same round (`log/reviewed/<node>/run.txt`), and only when the difference is under 60% of the files; otherwise it checks the draft as new. (The first draft review of round 3 was handed a 64,000-character diff against another run's draft and treated a new draft as a re-check.)

Polish pack: before polish the program writes `pack/polish.md`: the files it works from, the program tables that the draft's `{{block:<name>}}` markers stand for, what report_check tests on the polished report, and the diagram format, so polish does not read the system's code (round 3: 19 Reads, 16 Greps, mostly of case_server.py and render_pdf.py). report_check expands the markers before comparing the polished report's figures with the draft's.

Incremental polish (2026-11-05): when a polish node succeeds, the program keeps the draft and sources table it worked from in `log/polished/` (with `run.txt`). When analysis later changes the draft of the same run, the next polish task names the difference file `log/polish_changes.md`; polish carries those changes into the polished report with `edit_polished` and sends changed sources rows with append, without rewriting the whole. With no polished report of the same run, an unchanged draft (a return from the final review) or a difference over 60% of the files, polish runs as before. Reason: in trial case CASE-20261104-7e57a1, run 20261104-d2239ced, analysis changed one sentence and polish still rewrote every part (6.2 minutes); the return from the final review, done with edit_polished only, took 1.2 minutes.

## 13. No polish and no final comparison (2026-11-06)

The end-to-end trials (CASE-20261105-a7e298 on GPT, CASE-20261106-3694b3 on qwen) showed polish and the final comparison taking half the delivery time (81 + 71 minutes), with every final-review return caused by polish's own cuts. Changed to:

| Part | Now |
|---|---|
| Graph | `review_intake → run → analysis → review_draft (+ review_legal) → render → delivered`; the `polish`, `review_final` and `review_final_legal` nodes are gone and `LEGAL` is reduced accordingly |
| Analysis | writes the client report itself (spec §3, §5 rule 11); calls `render_pdf` (open to the analysis identity) when done, for the page count |
| Self-check | `self_check` first calls `autofix_draft`: sources rows pointing at a bug or notebook file are dropped by the program and logged; `report_check(target=draft)` also tests the flow block, spoken lead-ins, the optimizer's vocabulary, long sentences, and a current PDF with the body page count |
| Review | the draft check gains an eighth category, readable for the client; the legal lane has the draft lane only; the pass token is `DELIVERABLE` (the old `POLISHABLE` is still read as a pass) |
| Fix to order | a checklist may carry a ```replacements block (`[{"old", "new"}]`); the `render` node has the program `apply_replacements` them to the draft and re-stamp the checklists before typesetting; one that cannot be placed (sentence missing or not unique) goes back to analysis |
| Program gates | `write_review` refuses: a REVISE with no problem entry; on a re-check, a REVISE citing only unchanged lines that the previous checklist did not raise; a `replacements` block that is not a JSON list. `bug_append` with `affects_result=true` requires `effect` (which figure of this case changes, from what to what) |
| Return task | the analysis return task carries the checklists' findings (location, problem, evidence, suggestion; capped at 6,000 characters), to be applied as given |
| render node | program step: apply replacements → `client_copy` (markers expanded, lines carrying the case id or run id removed, written as `briefing.polished.md` for the host and old readers) → `render_pdf` → `report_check` again with the fresh PDF; a failed render stops with `agent_failed`, a failed check returns to analysis |
| Status | `reviewed`: both review lanes passed; `delivered`: `briefing.pdf` newer than the draft and the checklists. `polished` no longer occurs; old cases are read by the old rule |
| Host | the progress panel's node table is `intake, review_intake, run, analysis, review_draft, render`; the relay after delivery still reads Part 1 of `briefing.polished.md` |

`make_agents.py` no longer generates a polish agent; the review prompt has three stages (intake package, draft, legal lane).
