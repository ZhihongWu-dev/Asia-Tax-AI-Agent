# Taxrora

Cross-border dividend tax planning. A client states the background in a chat; three agents and an optimizer produce a recommendation report. The full product runs on this machine; a light edition runs on the cloud (see below).

| Folder | What it is |
|---|---|
| `database/` | Income-tax law of CN, HK, SG, JP, TH, AE, ID, IN, KR, MY and VN, with the MCP server `tax-db` |
| `rule/` | Structured rules and evaluation, with `tax-rule` |
| `optimization/` | Candidate structures, tax table and ranking, with `tax-opt` |
| `agent/` | The three agents (front, analysis, review), the case server `tax-case`, the LangGraph orchestrator and the Codex harness that runs the agents |
| `apps/api/` | The web host |
| `apps/web/` | The chat interface and the progress panel |
| `case_end2end/` | A fictitious test case |
| `cases/` | Runtime data, not in git |

## Run

Requirements: the conda environment `tax` (`pip install -r requirements.txt`), the Codex CLI (the agents' executor, driving qwen; see `.codex/README.md`), xelatex, Node.js 20.19+ or 22.12+, and a `.env` in the project root (see "Keys and .env" below). Claude Code is needed only to run the earlier path (`TAX_HARNESS=claude`).

```sh
cd apps/web
npm ci
npm run build
cd ../..
C:/Coding/Anaconda/envs/tax/python.exe apps/api/server.py
```

Open <http://127.0.0.1:8000>. To work on the page itself, keep the server running and use `npm run dev` in `apps/web`, then open <http://127.0.0.1:5173>.

## How a case runs

1. Each client message is one turn of the front agent. Its thinking and tool calls appear in the chat.
2. When the intake is ready, the front agent hands over and the orchestrator starts. The progress panel opens on the right.
3. The chat shows each agent's process as it works; the panel shows the graph nodes, retries and revisions.
4. The front agent reports back in the chat, with the PDF on delivery.

Runs can take hours. They are separate processes: closing the page or restarting the server does not stop them. A run stopped by a usage limit resumes from the panel without redoing finished steps.

The design is in `agent/orchestration_cli_spec.en.md`, section 8 for the web host.

## Keys and .env

Keys live in `.env` at the project root. `qwen_key` is read only from there; the library settings are read from the process environment first, then `.env`. You can set up your own: copy `.env.example` to `.env` and fill in your values.

| Name | Needed for | Service |
|---|---|---|
| `qwen_key` | Always: every agent call | Alibaba Cloud Model Studio, Token Plan (qwen3.8-flash and qwen3.8-max). Codex uses the OpenAI-compatible endpoint set in `agent/harness.json`; the Claude Code path uses the Anthropic-compatible one in `agent/tools/orchestrate.py` |
| `tax_db` | Optional | `supabase` reads the law library from the shared remote; anything else, or no entry, reads the local `database/` folder |
| `database_url`, `supabase_url`, `supabase_key` | `tax_db=supabase`, and `database/tools/upload.py` | Supabase: Postgres connection string, project URL and key. `upload.py` overwrites the shared remote; run it only on purpose |
| `site_url` | The cloud only | The deployment's public address (`render.yaml` sets it there) |

Settings read from the process environment only (not from `.env`):

| Name | Default | Meaning |
|---|---|---|
| `TAX_HARNESS` | `codex` | `claude` runs the agents on Claude Code instead |
| `TAX_HARNESS_CONFIG` | `agent/harness.json` | Another harness file (models and reasoning per node) |
| `TAX_CODEX_BIN` | the Codex app's bundled `codex.exe` | Path of the Codex CLI |
| `CLAUDE_BIN` | `claude` on PATH | Path of Claude Code, for `TAX_HARNESS=claude` |
| `TAXRORA_PORT` | `8000` | Port of the web host |

`OPENAI_API_KEY` in a separate `.env.codex` is needed only for the alternative harness `agent/harness.gpt-luna.json`. The retrieval and OCR models (BGE-M3, Qwen3-Reranker, Qwen3-VL) run locally and need no key.

## Agents and their prompts

Each agent's prompt is the `text` block in section "The prompt handed over" of its spec. Edit the Chinese spec (it prevails) and the English copy together, then regenerate the definitions the CLIs load:

```sh
python agent/tools/make_agents.py    # .claude/agents/*.md and .claude/agents.json, from the English specs
python agent/tools/make_codex.py     # .codex/agents/*.md, from the same English specs plus a Codex tool bridge
```

Do not edit `.claude/agents/` or `.codex/agents/` by hand.

| Agent | Where it runs, model and reasoning (`agent/harness.json`) | Prompt | Spec (Chinese prevails) |
|---|---|---|---|
| Front | each chat turn (`front`): qwen3.8-flash, medium | one block, §8 | `agent/前台Agent规范.md`, `agent/front_agent_spec.en.md` |
| Analysis | graph node `analysis`: qwen3.8-max, high | one block, §8 | `agent/分析Agent规范.md`, `agent/analysis_agent_spec.en.md` |
| Review | graph node `review_intake` (stage 1, intake package) and `review_draft` (stage 2, briefing draft): qwen3.8-flash, high; the lane `review_legal` beside `review_draft` (stage 3, legal reasoning): qwen3.8-max, xhigh | three blocks, §7 | `agent/复核Agent规范.md`, `agent/review_agent_spec.en.md` |

The web host adds short notes of its own to the front agent's turns (the web procedure, the cover note on delivery and its 200-word limit, the rewrite request); they are the `*_NOTE` and `RELAY_*` strings near the top of `apps/api/server.py`. The polish agent (`agent/润色Agent规范.md`) was removed on 2026-11-06; its spec is kept for the record.

## Local and cloud editions

The full product runs locally only. The cloud deployment (Render) runs a light edition:

| | Local | Cloud |
|---|---|---|
| Law retrieval | keyword, graph and dense search (BGE-M3), reranking (Qwen3-Reranker) | keyword and graph search only |
| Scanned uploads | OCR with Qwen3-VL | not read (marked "needs OCR"); text PDFs are read |
| Long runs | keep going when the page is closed | the free plan sleeps after 15 minutes without requests: keep the page open during a run |
| Sign-in | one local user | Supabase email accounts, cases kept per user |

The tax computation (library, rules, optimizer) and the three agents are the same in both; both run the agents on the Codex CLI with qwen, which on the cloud means a Linux Codex CLI installed by the build (`deploy_guide.en.md`, step 4). The full product on the cloud
needs a larger Render plan.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/auth/session` | `{ configured, user }` |
| POST | `/api/auth/login`, `/api/auth/logout` | Local sign-in |
| GET, POST | `/api/cases` | List or create cases |
| GET | `/api/cases/{id}` | One case |
| PATCH | `/api/cases/{id}/organization` | Rename or archive |
| POST | `/api/cases/{id}/messages` | One front turn; server-sent events `delta`, `reset`, `activity`, `error`, `done` |
| POST | `/api/attachments?filename=` | Upload a file |
| GET | `/api/cases/{id}/run?after=` | Node states, new process entries, stop |
| POST | `/api/cases/{id}/run`, `/api/cases/{id}/run/stop` | Resume or stop a run |
| GET | `/api/cases/{id}/report/{run_id}/briefing.pdf` | The report |
