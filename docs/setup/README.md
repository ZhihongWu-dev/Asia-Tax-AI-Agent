# Taxora Integrated Setup and Integration Testing

This document describes how to run the current integrated `main`. The goal is to connect chat, structure calculations, source retrieval, and research reports within one case, so team members can install and retest the system using this guide. The tax engine component uses the release specified here; later updates on its branch require separate integration. The current delivery is an internal research prototype, and tax interpretations still require review by the responsible professional. Start testing with the [acceptance testing entry point](../verification/README.md).

## 1. Framework responsibilities

- **Session orchestration** handles interviews, task identification, fact revision/confirmation, pause/resume, case saving, user isolation, and report review. The existing Hybrid/LangGraph workflow is retained.
- **Tax engine orchestration** includes structure search, rule calculations, lower/upper bound analysis, follow-up questions, and post-payment request handling. This integration uses the actual `planner.plan` and fixed-structure calculations; tax engine is not used only as a knowledge retriever.
- **The knowledge interface** connects the tax engine’s statutory/parameter materials to the existing `KnowledgeProvider`. When `combined` is explicitly selected, statutory sources use the tax engine’s read-only service and rulings use the existing PostgreSQL materials. Each source retains its original-text version, citations, and hash.
- **Database responsibilities** remain separate: PostgreSQL stores case progress; the tax engine’s SQLite/CSV files are knowledge dependencies from the pinned release. The 244 MB database has not been committed again to this branch.

```mermaid
flowchart TD
  U[Chat and structure analysis page] --> B[Session orchestration / DomainCoordinator]
  B --> F[Single source of facts: canonical_fact_records]
  F --> P[Legacy FSIE facts compatibility view]
  F --> C[tax engine Case / Answers projection]
  P --> G[Session FSIE rule chain]
  C --> L[tax engine one-shot subprocess: planning or fixed-graph calculation]
  L --> Q[Fact / action / professional judgment questions]
  Q --> B
  B --> K[Unified KnowledgeProvider]
  K --> S[official law sources: read-only HTTP service / SQLite]
  K --> R[Existing PostgreSQL ruling sources]
  G --> O[Research draft / hash / final review using the same fact version]
  L --> O
  B --> DB[PostgreSQL chat_cases: one commit per complete turn]
```

**Only Session orchestration commits a turn.** The tax engine subprocess receives only a case snapshot, with no model or case database keys. When calculations succeed, answers, results, and run records are saved together; if calculations fail, answers are not saved on their own. `owner` isolates cases, `revision` blocks updates based on old versions, and `request_id` supports replay. Reusing a request ID with different content is rejected.

## 2. Implemented features and current boundaries

| Feature | Current behavior |
|---|---|
| Shared fact model | Schema `2.0.0`; records values, addresses, sources, units, statuses, revisions, and confirmations; old cases migrate on demand and retain original facts snapshots |
| Synchronization | Legacy facts and tax engine inputs are projections of the shared records; bindings are created only for manually confirmed field ownership, and a single fact must not be copied to multiple companies |
| Existing structure `assess_current` | Requires explicit `present`; calculates only existing companies/shareholdings and rejects adding or relocating companies; does not silently switch to structure design |
| Structure comparison `plan_structure` | Calls the tax engine planner and preserves upstream candidates, question types, and ordering; prioritizes comparing upper tax bounds within the candidate set and does not imply a real-world global optimum |
| Paid-tax matters `review_paid` | Experimental entry point connected to fixed-graph/claims processing; complete business timing requirements and professional acceptance remain unfinished; do not make this the first acceptance target |
| Answers and recovery | Type validation, unknown facts, deferral, and pause/resume; outdated questions are rejected, and the case can be restored after refresh |
| Main chat integration | Run results and the next question are written to the conversation; answer in the structure panel or enter `结构答复：答案` (Chinese command meaning “structure response: answer”). Ordinary chat continues to use the original orchestration |
| Professional questions | `ruling/library` is unavailable to ordinary users; designated reviewers can submit answers with retrievable evidence, whose hashes are recorded. Current discretion supports only favorable judgments (`yes`), not automatic execution of unfavorable discretionary judgments |
| Combined research draft | Generated after confirming current facts; incomplete drafts require explicit consent. Existing structures with confirmed legacy field ownership also include the session layer’s FSIE rule chain. Both results and gaps are retained. Reports for mapped cases share an evidence cache. Ordinary analysis allows at most 14 evidence retrievals; user-requested combined reports allow 35 (FSIE 7, rulings 7, domain 21). Search is limited to ten attempts (at most five requests, each including one retry). The entire draft shares a 45-second budget; items beyond the budget are recorded individually as gaps |
| Original-text locations | The 21 FSIE locations are retrieved through seven parent provisions, then child passage positions and hashes are validated; unresolved, invalid, or restricted locations remain gaps |
| Source usage | tax engine original text may currently be displayed but must not be sent to the model; technical locatability does not establish professional tax review |
| Calculation currency | Initial support requires explicit **CNY**; missing currency is rejected, and HKD/SGD returns `unsupported`, with no silent currency conversion. Rule fields such as group revenue in euros still use their specified units |

The initial business form covers dividends from direct shareholdings; advanced JSON supports complex structures. API inputs support the other five templates and two-template combinations, but no claim is made that each has passed business acceptance. Vector retrieval, the tax engine’s document extractor, automatic currency conversion, and a multi-user expert collaboration interface are outside this verified delivery. Public hosting is documented in [the deployment guide](../project/RENDER_DEPLOYMENT.md).

## 3. File guide

| Location | Contents |
|---|---|
| `packages/domain_bridge/state.py` | Single source of facts, migration, legacy field bindings, and tax engine projections |
| `packages/domain_bridge/coordinator.py` | Transaction coordination for calls, question expiration, answers, pauses, professional responses, and reports |
| `packages/domain_bridge/bridge.py`, `worker.py` | Case validation, pinned release validation, subprocesses, and actual tax engine calls |
| `packages/domain_bridge/reporting.py` | Combined research drafts and Markdown with frozen facts/results/evidence |
| `apps/knowledge_api/main.py` | the tax engine’s read-only `/search` and `/evidence` services |
| `packages/agent/providers.py`, `knowledge.py` | Combined routing for original and tax engine sources, plus parent/child provision validation |
| `apps/api/chat.py` | Case, structure, report, and review APIs for signed-in users |
| `apps/web/src/components/StructurePanel.tsx`, `DomainResult.tsx` | Forms, questions, calculation results, and research draft downloads |
| `tests/integration/fixtures/holding.synthetic.json` | Shareable synthetic CNY example |
| `tests/integration/`, `apps/web/tests/structure.spec.ts` | Automated integration regression and browser tests |
| `scripts/install_tax_engine_release.py`, `check_combined_live.py`, `check_postgres_acceptance.py` | Pinned dependency installation, live model/database retesting, and complete disposable PostgreSQL acceptance testing |
| `docs/implementation/COMBINED_INTEGRATION_ACCEPTANCE.md` | Actual results from this round, limitations, and follow-up owners |

## 4. Installation for new team members

Requirements: Python 3.11+ (3.12 was used in this round), Node.js 20.19+ or 22.12+, Git, and an accessible PostgreSQL instance. WSL is recommended on Windows; the commands below target macOS/Linux.

```sh
git clone --branch main https://github.com/ZhihongWu-dev/Asia-Tax-AI-Agent.git
cd Asia-Tax-AI-Agent
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python scripts/install_tax_engine_release.py
npm --prefix apps/web ci
npm --prefix apps/web run build
cp .env.example .env
```

The installer downloads code/CSV files and the actual LFS SQLite database from GitHub at pinned commit `771e4524961bcc36718db1c9331e7a5f4cda0ce7`, validates them, and installs them atomically into the ignored directory `data/tax_engine/releases/<commit>/`. It does not automatically follow the latest HEAD of the tax engine branch. If local Python lacks CA certificates, install `truststore` and use `python scripts/install_tax_engine_release.py --system-trust`, keeping TLS verification enabled. In network-restricted environments, use a complete snapshot already obtained:

```sh
python scripts/install_tax_engine_release.py --from-directory /absolute/path/to/tax-engine-release
```

The installation must include `official/labels/*.csv`, which is required for rule compilation. Do not copy only `tax_graph/` or only the database. Do not disable validation after a failure; obtain complete materials from the same commit again. The initial online download includes a database of approximately 244 MB.

## 5. Configuration and startup

The integrated Li CLI tools use the declared MCP 2.3.0 dependency. From the project root with the Python environment activated, run `python agent/tools/make_agents.py` to regenerate role definitions and MCP configurations. A local `.mcp.json` overrides the portable `agent/mcp_servers.json` manifest; incomplete overrides fail before existing generated files are replaced. Use `--python /absolute/path/to/python` only for machine-local configurations, and do not commit those paths. `python agent/tools/test_orchestrate.py` runs scripted routing and child-process checks without calling a model. These local checks do not establish cloud deployment or account isolation.

Fill in the existing environment details in `.env`; do not commit keys or send them in group chats:

```dotenv
FSIE_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DB?sslmode=require
FSIE_MODEL_BASE_URL=https://YOUR_CONFIGURED_PROVIDER/v1
FSIE_MODEL_API_KEY=YOUR_LOCAL_KEY
FSIE_MODEL_NAME=YOUR_MODEL_NAME
FSIE_AUTH_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
FSIE_AUTH_PUBLISHABLE_KEY=YOUR_PUBLISHABLE_KEY
FSIE_AUTH_SITE_URL=http://127.0.0.1:8000
FSIE_AGENT_ORCHESTRATION=hybrid
FSIE_AGENT_DYNAMIC_PLANNER=true
FSIE_AGENT_HARNESS_MODE=tools
FSIE_AGENT_PROVIDER=combined
# JSON array of Supabase user UUIDs (not emails or values prefixed with user:). No one has permission by default.
FSIE_AGENT_REVIEWER_IDS=[]
```

The installation directory is used by default, so `FSIE_TAX_ENGINE_RELEASE_DIR` need not be set. Provide an absolute path when using an external complete snapshot. In managed combined mode the API generates an ephemeral token and loopback URL; do not set `FSIE_AGENT_C_TOKEN` or `FSIE_AGENT_C_URL` manually. A separately operated C-only provider still requires explicit endpoint and token configuration.

Run the existing migrations and knowledge loading workflow against a dedicated test database; see the [cloud research workflow](../project/CLOUD_KNOWLEDGE_SLICE.md) and [authentication guide](../project/TAXORA_AUTH.md). `chat_cases` is created during service initialization; changing the URL is not a migration mechanism for existing cases. The original ruling database needs imported tables such as `legal_units/sources`; an empty database reports ruling materials as unavailable.

Team members with local Docker can first start the database included in the repository:

```sh
docker compose -f infrastructure/postgres/docker-compose.yml up -d
python -m alembic upgrade head
```

The database connection must match this environment. These commands do not configure cloud accounts or populate ruling materials for you.

Start at the repository root with the virtual environment activated. The API now manages its knowledge service automatically; no second terminal is required.

To run the combined workflow accepted in this round directly on one computer, you can instead use a single terminal with `python -m scripts.run_combined`. It is now a compatibility alias for `scripts/run_chat.py`. Every API entry point uses `config/runtime.json` and starts and stops its own local knowledge service. Existing environment overrides still take precedence; inspect `/health` for the effective settings.

```sh
python scripts/run_chat.py
```

Open http://127.0.0.1:8000 and sign in. Check http://127.0.0.1:8000/health; `runtime.knowledge_ready=true` means the managed library service is running. The normal entry point retains email authentication; the test service's identity substitute is not used for normal startup.

## 6. Recommended initial automated checks

```sh
python -m pytest -q
python -m pytest -q tests/integration
npm --prefix apps/web run build
cd apps/web
npx playwright install chromium
FSIE_TEST_PYTHON="../../.venv/bin/python" \
FSIE_TAX_ENGINE_RELEASE_DIR="$(pwd)/../../data/tax_engine/releases/771e4524961bcc36718db1c9331e7a5f4cda0ce7" \
npm test -- --workers=1
```

On macOS with Chrome installed, set `PLAYWRIGHT_CHANNEL=chrome` if needed. Browser tests start a temporary SQLite case database, a deterministic model substitute, and the actual tax engine; they do not establish live model/cloud database acceptance. Legacy PostgreSQL integration tests are skipped by default and must be enabled in a dedicated environment using their `FSIE_RUN_INTEGRATION` switch. Without the tax engine release, related actual-engine tests are skipped; handoff acceptance must inspect skip reasons.

Local retesting of the actual HTTP knowledge service and combined report, without model calls and with a temporary SQLite case database:

```sh
python scripts/check_combined_local.py
```

The current handoff prioritizes database and combined workflow acceptance. Per the user's 2026-10-11 arrangement, live model acceptance is deferred and is not a blocker for this handoff round:

```sh
python scripts/check_combined_live.py --database-only --env-file .env.integration --output data/combined-database-result.json
```

If the database is not ready, add `--model-only` to test two rounds of model and tax engine interaction separately. The output explicitly identifies SQLite and cannot count as PostgreSQL acceptance. If the model is not ready, add `--database-only` to test actual PostgreSQL, actual C HTTP, tax engine, and ruling evidence retrieval; the output explicitly marks the model as `not_called`. These two modes are mutually exclusive. When configurations are stored separately, use `--model-env-file` to specify another local model configuration; the database is still read from `--env-file`.

When live model acceptance resumes, if macOS Python lacks default CA files, install `truststore` and add `--system-trust` to use certificates already trusted by the system. Always retain HTTPS verification. If `401/invalid_api_key` occurs then, the configuration owner should update the valid key locally.

The script creates a random test schema in the specified PostgreSQL instance, tests cases/recovery/isolation/reports, and cleans up that schema afterward. Existing shared knowledge tables are read-only. The runtime account must be able to create schemas. Outputs exclude connection strings/keys and include statutory/ruling coverage counts and statuses. **The current `--database-only` mode does not call the model.** The future full mode calls the configured model API and records fields populated by the model and manual data entry steps, potentially consuming usage. Manual data entry must not be counted as model accuracy.

Complete database acceptance has a separate entry point:

```sh
python scripts/check_postgres_acceptance.py --env-file .env.integration --system-trust
```

First set `FSIE_DATABASE_URL` in the local `.env.integration` to the dedicated PostgreSQL connection. The server needs pgvector, and the account must be able to create databases. If no server is available, use the existing `infrastructure/postgres/docker-compose.yml` to start a local environment. Use `--system-trust` only when `truststore` is installed; omit it on other machines.

This script creates a random database, runs migrations, imports the rule package, builds official sources, runs `tests/persistence` and actual HTTP/tax engine combined acceptance, and finally deletes the database it created. It does not migrate or empty the original database in the connection configuration. Source snapshots are stored in an ignored directory, and hash differences between web pages and manifests are recorded. Model tests are explicitly skipped and must be run separately. Outputs and sanitized substep logs default to `data/`.

On 2026-10-11, this passed with PostgreSQL 17.11 / pgvector 0.8.7: 14 persistence checks passed and two model checks were skipped; ten official source documents produced 697 parsed units; the actual HTTP combined report obtained 21 statutory locations and seven ruling passages. See the sanitized [PostgreSQL acceptance results](../implementation/COMBINED_POSTGRES_RESULT_2026_10_11.json). This round also completed Alembic chat-table metadata and the Source jurisdiction index declaration, verifying that a downgrade preserves chat data and RLS and that an upgrade continues using the same case.

The integration machine also retains an isolated database runtime within the project and `.env.integration`; neither is uploaded. On this machine, start it with `data/local-postgres/runtime/bin/pg_ctl -D data/local-postgres/cluster -l data/local-postgres/server.log start` and stop it with `data/local-postgres/runtime/bin/pg_ctl -D data/local-postgres/cluster stop`. This runtime is machine-specific; other team members should configure connections for their own PostgreSQL environments.

## 7. Manual acceptance: step-by-step testing for the next team member

Use only the synthetic example above. At each step, record case ID, mode, revision, observed behavior, and gaps, without recording keys.

1. **Existing structure**: create a case → structure analysis → load the synthetic example → select “Analyze existing structure only” → confirm synthetic data → save → run. There should be only two companies (`OP/ULT`) and one candidate. Results should show a tax range and gaps rather than add a holding company.
2. **Structure comparison**: create another case with the same example, switch to “Compare new structure options,” save, and run. It should enter the actual planner's candidate comparison and follow-up questions. Record the candidate count; do not treat a needs-input state as a successful tax plan.
3. **Numeric/boolean/date answers**: follow the question prompts. Do not enter “unknown” as 0 or false. Unknown key amounts may result in `blocked`, which is a valid outcome. Explicit false values must be preserved.
4. **Main chat answers**: when a current structure question exists, enter `结构答复：1000000` or `结构答复：未知` (Chinese commands meaning “structure response: 1000000” and “structure response: unknown”). One user message, the fact at the same address, and the new result should be saved. Repeated clicks for the same request must not duplicate commits.
5. **Deferral and pause**: deferring a question should move to other questions. Domain answers are rejected while paused. Resuming recalculates and restores questions. State remains after refresh.
6. **Field mapping**: first record receipt in Hong Kong, payment from mainland China, a CNY amount, and dates in chat/the fact panel, then generate a draft from current facts. Check OP/ULT/shareholding edges and explicit `present`, confirm bindings, and save. Changing the chat amount should synchronize with the structure event and invalidate old results; changing the structure amount should synchronize with the bound chat field. Unmapped legal judgments must not be copied automatically.
7. **Old questions/concurrency**: open two pages, change facts in one, and submit an old revision from the other. This should return 409 and require reloading. An old question must not overwrite new facts.
8. **Research draft**: after running, confirm structure facts first. If gaps remain, select “Consent to a partial research draft.” After generation, inspect the structure, tax amount, evidence, and gaps in the main conversation, and download Markdown. An existing-structure draft with mappings should also show the FSIE rule chain. Fact changes should mark the old draft as stale.
9. **Professional boundaries**: ordinary accounts should not be able to answer ruling/library questions. Configured reviewer accounts may submit evidence citation objects, but cannot use nonexistent or unretrievable evidence. Final reports still require dedicated review and are not automatically approved after successful model calculations.
10. **Knowledge and currency failures**: search FSIE provisions and check 21 locations. After stopping the knowledge service, the system should report unavailability rather than silently substitute other sources. Removing currency should be rejected; HKD/SGD should be explicitly unsupported and must not produce a CNY tax amount.
11. **No commit on failure**: automated tests cover worker timeouts/failures; the case revision and answers should remain unchanged. Manual live retesting may temporarily lower the timeout in a dedicated test environment without changing normal configuration.
12. **Account isolation**: another account must not be able to read the case. Current expert configuration supports only cases owned by that account; cross-account review assignment requires a separate authorization model.

## 8. Handoff completion criteria and remaining work

Retain the following engineering handoff evidence: Python/build/browser results, pinned release hashes, dedicated PostgreSQL and actual C HTTP/tax engine retest results, at least one existing-structure case, and one multi-turn planning case. The initial combined workflow described above is complete. Live model acceptance is deferred according to the user's arrangement; the next team member is not required to supply a key first. Run the complete live script when this item resumes. `needs_input`/`blocked` may be correct results, but must not be described as completed exemption conclusions. Model substitutes, synthetic data, and untested dependencies must still be clearly identified.

| Follow-up item | Owner | Required work |
|---|---|---|
| Live model and combined acceptance (deferred) | Model configuration owner + running team member when resumed | No key or model call is currently required. On resumption, run `--model-only`, then the complete live script with dedicated PostgreSQL; not counted as passed |
| Page acceptance with normal accounts | Environment owner + running team member | Configure Supabase email authentication and complete section 7 with test accounts; existing automated browser tests use test authentication |
| Tax interpretations, applicability periods, and professional discretion | tax engine coordinates knowledge maintainers and the tax lead | Check D14–D31, parameter units, bound conditions, and differences between fixed graphs and the planner; provide sourced approval/rejection records |
| Currency conversion and HKD/SGD | Integration team + tax lead | Define exchange rate sources, dates, threshold units, and tax conversion, then add examples and tests; changing currency labels alone is insufficient |
| Complex templates and paid-tax requests | Integration team + tax engine | Provide actually working synthetic examples, deadline/closure fields, expected results, and professional review for each template before opening business entry points |
| Expert case collaboration and deployment | Integration team / environment owner | Cross-account review authorization, release configuration, logs/backups, and operating procedures; this round defaults to loopback operation |

## 9. Troubleshooting and rollback

- `domain_unavailable`: install the pinned dependency or check the absolute path; do not mistake an LFS pointer for SQLite.
- `release_hash_mismatch`: source files/CSV/database are incompatible. Download and reinstall the same commit, retaining the old package for reproduction.
- `domain_execution_failed`: first run integration tests and inspect `official/labels/observed_rules.csv`; the API does not return internal tracebacks/keys.
- `blocked` with missing `present`: the existing arrangement is not explicit. The holding direct-shareholding example is `HOLD:null, financing:"EQUITY", payment:false`; complex cases must reflect their actual arrangements.
- `blocked` with `unbounded`: key amounts are unknown, preventing calculation of a bounded option. Supply actual supported amounts or retain a blocked research record.
- `knowledge_unavailable`: check the port 8010 service, token, and release files; for rulings under `combined`, also check the original knowledge database.
- `revision_conflict/question_changed`: reload the current case and answer the current question; do not reuse an old question ID.
- `review_incomplete`: gap/evidence gates are unmet. Current tax engine materials have not been professionally validated, and a complete engineering run does not automatically satisfy formal approval requirements.

Before rollback, back up the test/case database, then return to the Git commit before integration. The new schema retains pre-migration fact snapshots. Rolling back the old program does not migrate all domain records back; do not keep editing the same test case to validate the new workflow. A tax engine version upgrade requires a separate change: review matching materials again, update the pinned commit and both hashes, and rerun the matrix above. Do not modify the runtime directory while presenting it as the old release.

## Component naming

Use responsibility-based names: session orchestration, tax engine, and law library.
Install with `python scripts/install_tax_engine_release.py`; optional overrides are
`FSIE_TAX_ENGINE_RELEASE_DIR` and `FSIE_TAX_ENGINE_TIMEOUT_SECONDS`. The default is
`data/tax_engine/releases/<commit>/`. The Render build uses the same installer.

New law references use `law|`; new structure questions use `domain:`. Existing saved
references, question IDs, environment names and default installation directories
remain readable through compatibility code. Do not rewrite stored reports: their
hashes and original references are audit evidence. Historical captured JSON/CSV/log
files and immutable upstream release contents remain unchanged. Git authorship,
third-party attribution and actual repository URLs are not component names.
