# Native Codex harness (the default since 2026-11-07)

The agents run on the native Codex CLI. By default it drives qwen3.8-flash (the analysis node qwen3.8-max since 2026-11-08, the legal-reasoning review lane since 2026-11-12) through Token Plan's OpenAI-compatible
endpoint (`agent/harness.json`: base `https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1`,
`wire_api = responses`, key `qwen_key` from `.env`); `agent/harness.gpt-luna.json` is the GPT alternative (key in the
ignored `.env.codex`). The web host starts on this harness unless `TAX_HARNESS=claude`. The Claude Code path
(`agent/tools/orchestrate.py`) still works on its own. The harness was built in a separate worktree on branch
`codex/native-harness` and merged here on 2026-11-07.

## Model catalog and compaction (2026-11-13)

Codex does not know qwen's window by itself. Every generated `config.toml` therefore carries
`model_catalog_json` pointing at `agent/codex_model_catalog.json`, the entries for qwen3.8-max and qwen3.8-flash as
Alibaba Cloud's page "Codex 接入 Token Plan" gives them (https://help.aliyun.com/zh/model-studio/codex-token-plan):
`context_window` 983,616 (the thinking-mode maximum input of the model pages), `effective_context_window_percent` 95,
reasoning levels low / medium / xhigh. It also carries `model_auto_compact_token_limit = 840000` (harness.json
`auto_compact_token_limit`): the model pages give a context of 1,000,000 and a maximum output of 131,072, so the history
may reach 868,928 before a full-length answer no longer fits; 840,000 leaves room for one more turn's input, and lies below
the catalog's usable window (983,616 x 95% = 934,435). Checked with Codex 0.167.0-alpha under `--strict-config`: both keys
are read (a missing catalog is an error), and the reasoning level `high` the harness uses for some nodes still runs.

## Tool output limit (2026-11-25)

Every generated `config.toml` also carries `tool_output_token_limit = 40000` (harness.json `tool_output_token_limit`).
Above its default limit Codex cuts the middle out of a tool result and leaves "…N tokens truncated…" in its place; a
reader page is at most 32,000 characters, which in Japanese or Chinese law text is more tokens than the default, so the
legal lane lost the middle of its extract (case CASE-20261125-a1b2c3). Checked with Codex 0.167.0-alpha under
`--strict-config`: the key is read, a misspelt key is refused.

## Run

Use the Python interpreter in the `tax` conda environment. The original
`agent/tools/orchestrate.py` entry point is unchanged and still uses Claude.
This optional entry point installs a CLI selector in memory and uses that same
module's graph, routing, optimizer, prefetch and mechanical checks.

```powershell
conda activate tax
python agent/tools/make_codex.py

# Native GPT for every agent node; persistent client dialogue in this worktree.
python agent/tools/orchestrate_codex.py front CASE-CODEX-001 --harness codex
python agent/tools/orchestrate_codex.py run CASE-CODEX-001 --harness codex

# Default Claude/Qwen, with GPT for analysis and its independent review.
python agent/tools/orchestrate_codex.py run CASE-CODEX-001 --node analysis=codex:gpt-6-luna --node review=codex:gpt-6-luna

# Default GPT, with one particular review node on Qwen.
python agent/tools/orchestrate_codex.py run CASE-CODEX-001 --harness codex --node review_final=claude:qwen3.8-flash

# One front turn, or a bounded diagnostic task without advancing the graph.
python agent/tools/orchestrate_codex.py front CASE-CODEX-001 --harness codex --task "Hello."
python agent/tools/orchestrate_codex.py call CASE-CODEX-001 --harness codex --role review --task "Read the current round status and stop."
```

`agent/run_codex.ps1` is a convenience entry point with `--harness codex`.
Activate `tax` first, or set `TAX_PYTHON` to its Python executable.
`TAX_CODEX_BIN` can pin the Codex executable. On Windows the adapter prefers the
app-bundled executable over an older npm executable when no override is set.
The tested executable is `0.165.0-alpha.1.2`; no global installation was updated.

`agent/harness.json` supplies the defaults. A role override covers all its nodes;
an exact node name overrides the role. `--harness` changes the default backend,
while `--node` remains more specific. Review lanes and section workers use their
role's selection unless their call label has an explicit override. GPT model,
reasoning effort and timeout are configurable. Claude model overrides are passed
per thread and do not mutate the shared model dictionary.

## Isolation and native MCP

- Each Codex call has an immutable configuration and a fresh `CODEX_HOME` under
  ignored `.codex/runtime/`. Global `~/.codex` auth, plugins, sessions and config
  are not loaded or changed. Mixed Claude calls have their own ignored
  `.codex/claude-runtime/` configuration directories too.
- GPT receives only its provider credential, from `OPENAI_API_KEY` or ignored
  `.env.codex`. Claude receives Qwen's existing `ANTHROPIC_*` settings and no
  inherited OpenAI credentials. Provider credentials are removed from the MCP
  child environment. Never put credential values in a command argument.
- The CLI connects to native stdio MCP servers. `codex_mcp.py` starts the existing
  implementations from `.mcp.json`, using the tax interpreter. It adds a fixed
  role/case binding and audit records; it does not use `mcp_call.py` as an agent
  transport. The shared orchestrator's deterministic optimizer call is unchanged.
- Each role gets the same server set as `make_agents.SERVERS`, plus `tax-files`.
  The latter replaces host Read/Glob/Grep with controlled reads, using the same
  `access.py` policy. Case links and traversal are resolved before access checks.
  Library and product retrieval remain in the existing retrieval service.
- Shell, built-in image reading, built-in delegation, apps, plugins and bundled
  skills are disabled for case sessions. Images use the controlled file server;
  polish has no image tool. All writes go through that role's existing case MCP.
  Known role-server tools are approved explicitly for unattended use; unknown
  tools are not granted by a wildcard. Every required MCP must initialize.
- These are CLI/tool boundaries, not separate Windows accounts or containers.
  Existing Claude tools retain their original permissions; this change does not
  claim protection against arbitrary administrator code running on the machine.

## Evidence and limits

Native JSONL stays in `cases/<case>/log/runs/`; `runs.jsonl` includes backend,
model, session and usage metadata. Server audit records are in `log/codex-tools/`.
Each MCP server's stderr goes to `.codex/runtime/<case>/mcp-stderr/<role>-<server>-<pid>.log`
(UTF-8), never to the CLI's pipe: when the CLI stopped reading that pipe, a write failed
with OSError or, the pipe full, blocked the call until the 1200 s tool timeout
(2026-11-11). `tax-files` takes typed paging arguments and paths relative to the
project or to the cases root, and `search` takes a file as well as a folder.
Logs are redacted after each process exits. Codex currently records the completed
CLI turn count; it is not comparable to Claude's internal `num_turns`.
Codex has no equivalent `--max-turns` flag in this build. The supervisor enforces
the configured wall-clock timeout and kills the child process tree on timeout.
Each call is fresh; client continuity comes from the recorded case dialogue.

The existing web host still launches its original Claude entry point. This
implementation provides CLI selection; it does not switch the running web app.
A full tax-report end-to-end run is a separate exercise and has not been claimed
by these integration checks. Initial auth/config/approval diagnostic attempts are
preserved in temporary cases `CASE-CODEX-MCP-001` through `005`; the successful
four-role exercise is `CASE-CODEX-MCP-006`.

```powershell
python agent/tools/test_codex.py
python agent/tools/test_orchestrate.py
```

The English role definitions in `.codex/agents/` are generated from the same
English business specification blocks as Claude. Edit the authoritative Chinese
spec and its English counterpart together, then regenerate. No business or legal
specifications were changed by this integration.

The implementation follows the official OpenAI documentation for
[non-interactive execution](https://learn.chatgpt.com/docs/non-interactive-mode),
[configuration](https://learn.chatgpt.com/docs/config-file/config-reference), and
[native MCP configuration](https://learn.chatgpt.com/docs/extend/mcp).

## Sessions, structured replies and hooks (2026-11-17)

- **Resume within a round.** `codex_adapter.plan` keeps one record per node in `cases/<case_id>/log/sessions/<scope>/<key>.json`
  (scope: the round for the front, round and run_id for the others). A record found means `codex exec resume <id> -` in the
  same runtime folder, whose `CODEX_HOME` holds the session; `resume` and `fork` take neither `--cd` nor `--color`, so the
  process runs in the folder's `work/`. A new round or run starts fresh.
- **Fork for the analysis.** Nodes in `codex.sessions.fork` fork the first session of the round instead
  (`codex exec fork <first> -`).
- **Fallback.** A resumed or forked call that hits the context limit or completes no turn drops the record and runs fresh.
- **`--output-schema`.** `codex.output_schemas` names `agent/schemas/*.json` per node; the parsed reply is returned as
  `reply` and logged. A provider that refuses the schema gets the call again without it. Not yet tested on Token Plan.
- **Hooks.** `[features] hooks = true` plus `[[hooks.PreToolUse]]` / `[[hooks.PostToolUse]]` calling
  `agent/tools/codex_hook.py --role <role> --case <case> --event pre|post`; `--dangerously-bypass-hook-trust` because the
  hooks are generated per call and their hash is never trusted ahead. The command is unquoted (the hook shell differs by
  platform), so `prepare` refuses a Python or project path with a space.
- **Browser.** `browser_use = true` is written explicitly.
- To measure later: MCP start-up per session (SDK or `app-server`), `reasoning_effort_override` low for wording fixes,
  `--ephemeral` for one-shot turns.
