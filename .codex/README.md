# Native Codex harness (the default since 2026-11-07)

The agents run on the native Codex CLI. By default it drives qwen3.8-flash through Token Plan's OpenAI-compatible
endpoint (`agent/harness.json`: base `https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1`,
`wire_api = responses`, key `qwen_key` from `.env`); `agent/harness.gpt-luna.json` is the GPT alternative (key in the
ignored `.env.codex`). The web host starts on this harness unless `TAX_HARNESS=claude`. The Claude Code path
(`agent/tools/orchestrate.py`) still works on its own. The harness was built in a separate worktree on branch
`codex/native-harness` and merged here on 2026-11-07.

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
