# Taxrora

Cross-border dividend tax planning. A client states the background in a chat; four agents and an optimizer produce a recommendation report. Everything runs on this machine.

| Folder | What it is |
|---|---|
| `database/` | Income-tax law of CN, HK, SG, JP and TH, with the MCP server `tax-db` |
| `rule/` | Structured rules and evaluation, with `tax-rule` |
| `optimization/` | Candidate structures, tax table and ranking, with `tax-opt` |
| `agent/` | The four agents, the case server `tax-case` and the LangGraph orchestrator |
| `apps/api/` | The web host |
| `apps/web/` | The chat interface and the progress panel |
| `case_end2end/` | A fictitious test case |
| `cases/` | Runtime data, not in git |

## Run

Requirements: the conda environment `tax`, Claude Code, xelatex, Node.js 20.19+ or 22.12+, and a `.env` in the project root holding `qwen_key`.

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
