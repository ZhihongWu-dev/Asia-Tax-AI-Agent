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
| `run` | program | intake_ok | Builds `intake/run_input.json` from facts.json plus `closing_answers(answers.json)`, then `validate_input`, optimizer `run`, `round_set_run`; `diff` when there is an earlier round | The ledger has a run_id |
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
| `revision_limit` | One node has run 4 times in one `run` | A person |
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
| front | qwen3.7-plus | interactive | none |
| analysis | qwen3.8-max | headless | 80 |
| polish | qwen3.7-max | headless | 60 |
| review | qwen3.7-plus | headless | 80 |

**Headless call**

```
claude -p "<task>" --agents .claude/agents.json --agent <name> --mcp-config .claude/mcp/<name>.json --strict-mcp-config --output-format stream-json --verbose --include-partial-messages --max-turns <n> --allowedTools <list>
```

| Environment variable | Value |
|---|---|
| `ANTHROPIC_BASE_URL` | `https://token-plan.cn-beijing.maas.aliyuncs.com/apps/anthropic` |
| `ANTHROPIC_AUTH_TOKEN` | `qwen_key` in `.env` |
| `ANTHROPIC_MODEL` | The model above |
| `ANTHROPIC_SMALL_FAST_MODEL` | `qwen3.7-plus` |
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
