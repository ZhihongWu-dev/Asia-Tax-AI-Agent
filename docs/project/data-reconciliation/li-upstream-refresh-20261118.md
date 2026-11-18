# Li upstream refresh

## Current integration checkpoint (after e2c0f4e)

The sections below retain the original inspection chronology. Their statements
that individual ports are pending describe those earlier checkpoints, not the
current implementation state.

Implemented locally and committed:

- Atlas projection, isolated execution, authenticated routes, views and snapshot
  pinning: afa24d3 through 23a16f1. Hosted catalog admission is still required.
- Remote collection-log reader and MCP behavior, followed by notes-only/full
  upload lifecycle and malformed-log rejection: 860f134 and e28132c complete
  the uploader portion. No hosted upload was executed.
- Multiple attachment selection/drop, evidence extraction, display and reload:
  073b353. The API message-size boundary is retained.
- Owner/revision-scoped case deletion with atomic job cleanup: ef28e87;
  PostgreSQL lock-race checks and CI wiring: 932849a and 3580073.
- Temporary drafts adapted to the existing income and structure editors:
  e2c0f4e. See the dedicated draft checkpoint for validation and remaining limits.

The incoming useRun.ts change only resets its polling callback on case changes.
The integrated product does not contain that hook; it uses the durable planner
API and PlanningPanel. Copying the standalone hook is not an applicable patch.
This is not evidence that all planner lifecycle behavior has been accepted.
Documentation/config reconciliation, hosted acceptance, full data/rule
reconciliation and final branch delivery remain open. These feature commits do
not establish completion of the corporate/personal income-tax business goal.

## Original upstream inspection

`git fetch origin --prune` advanced `origin/LiZiheng` fromce87d83 to140a9efa53a4bce3f2899a20edfa77be8ec55e8b. It is not an ancestor of the current integration branch. Two incoming commits remain to integrate:

- d31a7b9: tax atlas map, country detail pages, glossary, clause dialog and frontend navigation; backend `apps/api/atlas.py` and standalone-server routes.
- 140a9ef: documentation/config examples, deployment guide rename, and remote blocked/status/session-note handling in database source/upload tools.

Diff scope:28 files,1689 insertions,49 deletions. The fetched target `origin/Zhihong-Wu` is an ancestor of the integration branch (0 remote-only,274 local-only at fetch). No remote push or database upload performed.

Integration requirements:

1. Port atlas features into the existing authenticated product and `apps/api/main.py` rather than switching to Li's standalone host. Preserve existing income-tax forms and case ownership.
2. Atlas rates and clauses must use the reviewed, version-pinned library adapter. Upstream's singleton state/current-upload caching and optimistic scenario assumptions require adaptation; preserve visible assumptions and unresolved eligibility.
3. Review mutable remote blocked/status/session-note changes against catalog revision and review fingerprinting before changing readers. Do not run the upstream upload tool.
4. Review frontend dependencies/licenses and map assets, then run map/country/glossary/source UI acceptance alongside existing income and chat cases.
5. Reconcile documentation/config examples without copying secret-bearing files or treating upstream documentation as user authorization to publish credentials.

The original optimizer remains live on frozen inputs. No incoming engine/database mutation was applied during this inspection. This incoming feature set is not yet integrated, so final delivery remains incomplete.

## Atlas projection port

Adapted the upstream atlas projection code into `packages/domain_bridge/tax_atlas.py`. Removed implicit local/cloud source construction, background warming and singleton cache; the caller must supply a verified library/engine state from an isolated process. Adapted source, treaty and absence lookups to the existing immutable PlanningLibrary interface. Clause results preserve complete text, passage hash and bundle/review version. Invalid dates fail explicitly; missing rates stay unresolved. Country scenario output exposes the favourable judgment assumptions. Current headline/condition parameter selection excludes obsolete or out-of-period rows. Returned scenario constants are detached to prevent caller mutation affecting later requests.

Validation:20 projection/library tests passed in1.54 seconds, including invalid calendar dates, missing-source rejection, exact passage/version retention, unknown rates and detached state. This module is not yet wired to an isolated executor, authenticated API or frontend; those remain required.

Research: inspected upstream map dependencies against https://github.com/topojson/topojson-client and its ISC license, and https://github.com/topojson/world-atlas/blob/master/README.md for the Natural Earth50m geometry format. No new map dependency or third-party asset installed in this step. Dependency maintenance/security review and frontend license attribution remain pending before adoption.
# Remote collection-log integration follow-up

Adapted Li's new remote blocked.csv reader. Inspection of the actual CSV schema
(`id,jur,title,url,reason,alt_tried,logged_at`) confirms that it records failed
collection attempts; it is not the application's citation admission list.
The application continues to use source_review and reviewed overlay policy.

Remote.rows('blocked') now fetches the operational log on every call because
notes-only uploads can change it without advancing uploaded_at. Unlike the Li
implementation, transport errors are propagated rather than converted to an
empty log; malformed headers/rows are rejected. Older uploads without this
object will explicitly fail when the log is requested. Other table reads and
local-folder calculations are unchanged. No uploader or cloud data was changed.

Seven focused tests passed: notes-only updates, detached reads, genuinely empty
logs, unavailable storage and malformed CSV. These are local mocked-storage
tests, not a claim that the current hosted bucket has the object. Reviewed
Supabase changelog and Storage error-code documentation: an HTTP failure cannot
be interpreted as proof that no failures were logged.

References: https://supabase.com/changelog.md and
https://supabase.com/docs/guides/storage/debugging/error-codes .
Upstream upload/notes lifecycle and final hosted acceptance remain outstanding.

## MCP consumer verification

The MCP Library previously fetched and retained blocked rows at startup. It now
loads remote collection logs on demand; the local-folder snapshot remains local.
An unavailable log is returned as collection_log_unavailable only by the log
query and does not prevent catalog initialization. Error detail is fixed text,
not a storage exception or credential-bearing message. The existing database
version describes the catalog, not the mutable operational log.

Validation: all 84 database-tool tests passed in 18.30 seconds. The strengthened
consumer test additionally exercises actual Library initialization, confirms
that startup never requests blocked rows, verifies subsequent log refreshes and
checks the scoped failure response; its eight-test module passed in 0.46 seconds.
No cloud mutation or hosted verification was performed.
