# Rule promotion checkpoint

Prepared commit 3e9c767 on codex/repaired-rule-validation in the independent
Asia-Tax-AI-Agent-rule-validation worktree, based on b3fd7b1. It promotes the
reviewed isolated CSV rule inputs and their rebuilt SQLite/status artifacts.
The original optimizer continues in this integration worktree, unmodified.

Rebuilt results: 453 rules, 97 variables, 11 predicates, 204 decisions,
1,375 tests, zero failures/errors, 30 coverage gaps. The repaired authored
reference closure contains 494 citations and no longer includes either live
blocked legacy citation. Full hashes are in that commit's audit artifacts.

Outstanding integration action: bring 3e9c767 into this branch after preserving
and comparing the original baseline; verify replacement citations against the
coordinated migrated cloud catalog. Do not omit this commit from final
Zhihong-Wu delivery. No production deploy or remote push has occurred.

## Follow-up runtime and source closure

The validation branch additionally contains commit0778b0c, integrating exact
duplicate destination-state compression into the checker and adding its helper
to the planning runtime fingerprint. Its47 focused optimizer/equivalence tests
passed. Full repaired golden expectations plus exhaustive checks are running
under session70240; do not restart or alter those inputs without terminal evidence.
The original baseline remains separately live under PID16760.

Rechecked the repaired runtime against the staged catalog and fresh live review
exclusions. All635 required references are present, nonempty and not blocked.
The exact snapshot and runtime fingerprint are preserved in
repaired-source-closure-20261118.json. This supersedes the older source-readiness
artifact's stale overlay fingerprint for this check. It is not proof that the
unmigrated cloud tables can supply these rows: a separate live bundle read still
failed on the two legacy catalog dependencies. Both validation commits remain
required for final integration; catalog migration and end-to-end acceptance
remain open.

## Full-suite harness correction

Session70240 terminated with an error before completing golden expectations:
the harness injected common.Library, which lacks the mandatory version_metadata
interface. This is not a passing or completed tax/optimizer validation.

Replaced the harness with a verified PlanningLibrary bundle containing the full
635-reference staged source closure. Bundle SHA256:
0d2b620d1c307586fffbc03fc8ee662f4876cfaa869834a9e5783a75a5504127.
The v2 harness logs START, golden result and exhaustive checker result per row,
and checks the runtime fingerprint after each case. It is now running under
session28744 in the independent validation worktree. Script and log:
integration-audit-20261116/run_repaired_golden_v2.py and
repaired-compressed-golden-v2-20261118.log. Preserve inputs until terminal.
The original optimizer run remains separate and has not been restarted.

## Procedure citation correction and rejection

Session 28744 (v2) terminated before the first golden result because procedure
clause dependencies were omitted from capture_runtime. Validation-branch commit
f5415b2 adds procedure clause references and a regression test. All 19 runtime
tests pass; all 453 rules expand with the 649-reference staged bundle.

The v3 diagnostic run is live as session 66099, using
run_repaired_golden_v3.py and repaired-compressed-golden-v3-20261118.log in the
external audit directory. Its bundle digest is
694feb1a4b028ee12cdb9725c5dd177e4c416af5df7aa5bcf4a50c1c9f29dabe.

A fresh read of live source reviews REJECTS this expanded dependency set:
id.dgt.article26#all remains in Indonesian treaty rules' procedure fields.
See repaired-procedure-source-closure-20261118.json. The previous 635-reference
closure did not cover procedure references and is insufficient for promotion.
The running v3 suite is diagnostic only, even if its optimizer checks pass.
Replace the obsolete procedure dependency with reviewed current legal support,
rebuild and validate rule artifacts, and rerun the complete source-admission
and optimizer checks before promotion. Do not alter the current running inputs.
