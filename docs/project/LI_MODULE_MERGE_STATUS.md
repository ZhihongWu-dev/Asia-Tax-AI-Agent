# Li module merge status

This merge preserves the existing Taxora web app, Supabase authentication, deployment configuration, and the newly merged tax database. It incorporates the standalone `.claude/`, `agent/`, `rule/`, `optimization/`, and `case_end2end/` modules from LiZiheng's safe code commit `0973ce1`.

These modules are **not connected to the production chat API**. The rule snapshot covers fewer jurisdictions than the current database, and its generated SQLite/status files need to be rebuilt and revalidated against that database before use. The agent's Claude Code MCP configuration contains a machine-specific Python path and needs portable configuration before running on another machine. The end-to-end case uses fictional parties and amounts plus public official documents.

The later `.env` commit was excluded. Never commit runtime credentials; use the existing root `.env.example` for configuration names. The agent's isolated orchestration test passed with a placeholder key and local test configuration; the 22 imported Python files passed syntax compilation. This does not validate rule accuracy or live application integration.