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
