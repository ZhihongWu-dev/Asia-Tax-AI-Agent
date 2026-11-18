# Li upstream refresh

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
