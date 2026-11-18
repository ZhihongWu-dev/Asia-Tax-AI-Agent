# Li/Main integration status (2026-11-18)

## Latest delivery checkpoint

The current combined candidate is on `codex/catalog-closure-delivery`, based on
`c56128c` before the SQLite parity repair. Its clean-checkout regression initially
exposed 308 missing catalog citations; the reviewed candidate CSV snapshot fixes
that failure. The complete offline regression then passed 2,448 tests, with four
environment skips and 27 integration-marked tests deselected. Database tooling
passed all 92 tests. Six catalog CSVs retain exact hashes under Git checkout with
`core.autocrlf=true`, `false` and `input`.

The tracked SQLite artifact was still the older 6,037-clause database. It has now
been rebuilt from the reviewed CSVs: all seven tables, including 45,888 clauses,
358 documents and 811 parameters, match every field and row order. The original
UAE/Hong Kong RTF is included with its verified source hash. See
[candidate validation](data-reconciliation/catalog-delivery-validation-20261118.json)
and [SQLite parity](data-reconciliation/catalog-delivery-sqlite-parity-20261118.json).
These local artifacts do not apply the pending cloud catalog migration.

The combined optimizer v5 has completed seven of twelve cases with no golden or
exhaustive checker failures: `case001.best`, `case001.open`,
`case001.valued.best`, `cfc_jp.best`, `cfc_jp.open`, `exit_jp.best`, and
`remit_sg.not_kept`. The eighth case, `remit_sg_open.conduct`, has passed its
golden assertions but its exhaustive checker is still running; it is not counted
as complete. The v4 comparison has completed five cases and is checking
`exit_jp.best`. These are observations from the live run logs on 2026-11-18,
not a final suite verdict. All twelve cases remain required. The original and
v4 processes retain their frozen inputs.
Hosted identity/provider/worker-recovery acceptance, final remote delivery and
`main` promotion remain incomplete.

### Earlier checkpoint retained for traceability

Implementation HEAD at this checkpoint: `c1f109a`, on
`codex/li-corporate-integration`. Final `Zhihong-Wu` delivery and `main`
promotion remain incomplete.

- The complete offline application regression passed 2,436 tests in 507.02
  seconds, with two skips (local legacy Word converter and PostgreSQL-specific
  lock semantics) and 25 integration-marked tests deselected. The lock behavior
  has separate PostgreSQL evidence below; hosted acceptance remains outstanding.
  The separately executed database-tool suite passed all 92 tests in 32.02
  seconds in its dedicated environment. The application environment lacks its
  extraction dependencies and could not collect that suite.
- The full two-worker browser run passed 118 of 119 cases. One initial-page
  load failed because Edge could not fetch the development React refresh module
  (`ERR_NO_BUFFER_SPACE`); the preserved trace shows the subsequent preamble
  error. Both Thai dividend elections then passed three times each (six checks)
  without code changes or retries. This is not recorded as a green full run.
  The subsequent complete single-worker browser run passed all 119 cases in
  11.9 minutes with zero retries. It used the same scenarios and assertions;
  the earlier failed run remains recorded. The source-reader transaction change
  made during that run is supported separately by focused/PostgreSQL tests.
- The income-tax suite now passes 1,406 tests (23.46 seconds). Vietnam ordinary
  business and property rental have saved-case APIs and bilingual intake/results.
  The 59-test income browser regression passed before rental UI integration;
  the subsequent three-test business/rental regression also passed. These are
  local fixture-account checks, not hosted identity/provider acceptance.
- The repaired optimizer v4 has completed `case001.best`, `case001.open` and
  `case001.valued.best`, each with zero golden and checker failures. The same
  live process has entered `cfc_jp.best`; the twelve-case run is not complete.
  Five independent validation-branch commits still await final integration.
- `render.acceptance.yaml` provides independent web/worker services targeting
  `Zhihong-Wu`, with automatic deployment disabled. Its structure passed the
  official schema validator. No cloud services were created by preparing it.
- Catalog execution remains pending. The older 404-operation plan would duplicate
  two newly admitted overlay clauses in the base table. A revised 402-operation
  plan omits those duplicate inserts, preserves all other operations and passes
  fresh read-only before-state checks plus compatibility checks against all 44
  admitted overlays. The old collision was reproduced explicitly. The revised
  full plan also passed isolated PostgreSQL commit and forced-postflight rollback
  rehearsal; seven PostgreSQL executor/lock tests passed. This fixture is not a
  clone of hosted constraints or roles, and no hosted catalog migration occurred.
  A subsequent repeatable-read snapshot comparison simulated the full revised
  plan and compared every resulting row in jurisdiction (11), doc (358), param
  (811), treaty (55), and decision (43) with the frozen validation CSVs: no
  missing, extra, or changed rows. This comparison normalizes SQL nulls to CSV
  empty strings; it does not establish full clause-table equality or hosted
  transaction acceptance.
  Subsequent
  repaired-reference verification found neither old blocked citation among its
  662 dependencies. Twelve missing Indonesian procedure passages were reviewed
  and admitted through the private overlay. The dedicated reader now returns
  all 662 dependencies, verifies the twelve exact new passages and rejects the
  old snapshot. However, 34 existing live passages differ byte-for-byte from the
  staged optimizer passages. Follow-up review classified all 34 as extraction
  differences: 24 whitespace-only, nine Korean PDF page footers and one Japanese
  navigation wrapper. The bounded legal-body comparisons and document hashes
  match. Exact source bytes and version pins remain unchanged; no production
  reader was taught to ignore mismatches.
  Source closure can now be checked using the caller's uncommitted migration
  transaction. The shared reader passed 43 focused tests; nine real local
  PostgreSQL executor/source tests verified visibility, rejection and rollback.
  This mechanism does not replace the outstanding deployment and legal gates.
  A subsequent 402-operation local rehearsal used a fresh consistent cloud
  snapshot, all 173 review records and all required clause rows. The real
  postflight reader returned 662 sources and all 1,278 catalog rows matched the
  frozen inputs. The 34 reviewed extraction differences matched their exact
  recorded hashes. Forced postflight rejection restored every fixture table;
  the successful transaction rejected the old local snapshot. Local/hosted
  review digests differ because of database sort order, with exact review rows
  verified independently. Hosted constraints and deployment remain untested.
  The older runtime still references the two blocked sources until repaired-rule
  integration. No base catalog tables were changed by this source admission.
- Next delivery work is source admission/rebinding, completed optimizer
  acceptance and repair integration, then deployed migration, two-account,
  provider and worker-restart acceptance. Remaining income-tax eligibility,
  credits, mixed-income and filing gaps remain open; adding an unrelated tax
  such as VAT is not required merely because an income-tax component excludes it.

Evidence: [rental implementation](data-reconciliation/vietnam-business-consolidation-20261118.md),
[full offline regression](data-reconciliation/full-offline-regression-20261118.json),
[database-tool regression](data-reconciliation/database-tools-regression-20261118.json),
[full browser run and failure reproduction](data-reconciliation/full-browser-regression-20261118.json),
[transactional source validation](data-reconciliation/catalog-transaction-source-reader-20261118.md),
[complete transaction/source rehearsal](data-reconciliation/catalog-source-transaction-rehearsal-20261118.json),
[business implementation](data-reconciliation/vietnam-business-individual-review-20261118.md),
[deployment preparation](RENDER_DEPLOYMENT.md),
[current catalog plan](data-reconciliation/catalog-migration-plan-overlay-safe-20261118.json),
[current catalog guards](data-reconciliation/catalog-overlay-safe-preflight-20261118.json),
[complete simulated catalog comparison](data-reconciliation/catalog-simulated-full-comparison-20261118.json),
[PostgreSQL transaction rehearsal](data-reconciliation/catalog-overlay-safe-postgres-rehearsal-20261118.json),
[earlier live source blockers](data-reconciliation/atlas-live-catalog-preflight-20261118.json),
[repaired-source admission](data-reconciliation/indonesia-procedure-source-admission-20261118.json),
[reviewed extraction differences](data-reconciliation/live-staged-source-comparison-20261118.json).

## Earlier delivery checkpoints (superseded where noted above)

Work is on `codex/li-corporate-integration`, tracking `origin/Zhihong-Wu`.
The final integration has not been pushed or merged to `main`. The historical
2026-11-15 record below is retained as baseline evidence, not current status.

- Scope remains Li data/function integration plus both corporate and personal
  income tax across cn, hk, sg, id, vn, my, th, ae, jp, kr and in. Passing ordinary
  calculations does not complete special regimes or production acceptance.
- Saved income facts, explicit calculation bases, revision-bound results and
  bilingual forms are implemented. The latest complete `tests/income_tax` suite passed 1159 tests
  in 16.65 seconds, including Thai remittance validation and domestic assessment
  reconciliation. The log is `integration-audit-20261116/income-tax-regression-20261118-latest.log`.
  Thai remittance preparation is not yet connected to the public assessment/UI
  or complete foreign-credit/treaty settlement.
  Singapore employment settlement additionally passed three browser scenarios
  (two save/reopen cases and the existing rate-only entry). These use local
  fixtures, not production identity/provider acceptance.
- Cross-module offline regression completed with Python UTF-8 mode: `python -X utf8
  -m pytest tests -m 'not integration' --ignore=tests/database -q` returned
  2068 passed, 1 skipped and 11 deselected in 454.46 seconds. The skip is the unavailable legacy attachment converter; the
  deselections are live-database integration tests. Database extraction tests
  passed 76 separately in 12.16 seconds after the Indonesian compilation parser repair. These results do not establish live account isolation,
  provider availability or hosted-worker acceptance.
- After Thai dividend integration, the complete `apps/web/tests/income-tax.spec.ts`
  browser file passed35 scenarios in2.2minutes using Edge and local fixtures.
  This covers the existing case save/reopen, revision conflict, phone viewport
  and country calculations in that file; it is not the entire frontend suite or
  deployed-account acceptance.
- Malaysia individual domestic dividends now have annual threshold, proportional
  chargeable-income allocation, ordinary-income remainder and settlement, with
  saved-case reconciliation and bilingual UI. Two resident/nonresident save/reopen
  browser cases and two existing company/individual browser regressions passed.
  Joint assessment, automatic entitlement determination, special/foreign regimes
  and assessment rounding are still incomplete. See
  [workflow evidence](data-reconciliation/malaysia-dividend-workflow-20261118.json).
- Isolated database rebuild before the five UAE/Korean legacy retirements completed
  with 353 documents, 44995 clauses, 816 parameters and 44 absence records;
  errors=0, warnings=88, category gaps=5, slot gaps=35, blocked downloads=2.
  Five superseded overview parameters were then retired with full before-row
  archives and retained-primary comparisons (811 parameters). A subsequent
  rebuild is still running; zero build errors do not resolve coverage gaps.
- Indonesian PMK112/2025 original and DGT transitional guidance are archived.
  The signed original establishes commencement on 2025-12-31; a conditional
  primary-law parameter migration is prepared, not applied. Earlier valid
  certificate formats must retain the documented transitional treatment.
- Planning runs are connected to the signed-in case API and UI, with a durable
  queue, worker leases, cancellation and pinned artifacts. The hosted worker
  has not been provisioned or accepted. A manual-deploy worker definition is
  now prepared and validated against Render's published JSON Schema; actual
  provisioning, shared secrets and matching deployed commits remain outstanding.
  See [worker deployment](PLANNING_WORKER_DEPLOYMENT.md).
- A dedicated cloud law-library reader has verified read-only grants and cannot
  access private cases/jobs. Its deployment secret still needs installation.
- Earlier point-in-time cloud source review on 2026-11-18 (superseded by
  subsequent admissions; these are not current totals): different-text records have 2 accepted
  replacements, 16 candidates and 7 rejected decisions; main-only records have
  7 accepted sources, 104 candidates and 3 rejected decisions. Total is 139. A rejected
  different-text candidate normally retains the base; explicit exclusions are
  essential for sources that are obsolete or corrupt. The repealed CN2008-112
  notice is explicitly excluded in both search and planning readers.
- The two accepted repairs are CN2026-27 item3 and the UAE top-up-tax whole-page
  citation. Both are hash-bound replacements; the base cloud text is unchanged.
- Vietnam Law108 Articles16,16.2,52 and53 are admitted as reviewed source overlays.
  All four texts were reconstructed exactly from the official gazette and read
  through the dedicated reader; the previous snapshot was rejected. This admits
  source text, not a complete penalty calculator or the pending catalog parameter.
  See [admission evidence](data-reconciliation/vietnam-tax-administration-overlay-20261118.json).
- Japan NTA No2260 tax-rate section and No2875 domestic residence section are
  admitted with complete-text and stale-snapshot checks through the dedicated
  reader. Their whole-page candidates remain unapproved; this does not approve
  treaty residence decisions or pending catalog parameters. See
  [section evidence](data-reconciliation/japan-guidance-section-review-20261118.json).
- An earlier dedicated-reader audit included625 local citation dependencies,
  including factor citations:8 are missing from cloud admission,6 are blocked
  (some overlap), and55 local parameters are absent from the cloud catalog. See
  [dependency evidence](data-reconciliation/planner-source-readiness-20261118.json).
  These counts predate subsequent admissions and isolated-stage changes;
  refresh source readiness before deployment rather than treating them as current.
- Japan's2026 Tax Law Introduction page55 (printed44) is admitted after a fresh
  official download matched the archived PDF hash, exact page reconstruction,
  dedicated-reader verification and stale-snapshot rejection. General foreign
  income scope retains the non-permanent-resident exclusion; this does not
  establish complete foreign-credit or treaty calculations. See
  [source evidence](data-reconciliation/japan-international-scope-source-20261118.json).
- The missing Japanese consolidated-tax research citation has an exact quote,
  but describes the former regime. Current article132-3 uses group-tax-sharing
  corporations and includes acts of other group corporations. Its undated legacy
  parameter requires historical quarantine and current statutory rebinding,
  rather than automatic source admission. See
  [scope review](data-reconciliation/japan-group-tax-scope-review-20261118.json).
- Thai PIT overview review found conflicting legacy parameters: its residence
  wording excludes day180, while Revenue Code section41 includes it; its fixed
  dividend credit3/7 omits section47bis's distributing-company rate dependency.
  The active residence rule already uses the correct >=180 boundary. Legacy
  catalog quarantine is now applied in the isolated copy and awaits the current
  rebuild; runtime promotion and full business acceptance remain pending. The
  outdated overview has not been admitted to close missing sources.
  See [conflict evidence](data-reconciliation/thailand-pit-overview-conflicts-20261118.json).
- A Thai section47bis dividend-component calculator now computes each certified
  tranche's own corporate-rate gross-up, separates shareholder withholding and
  preserves non-creditable tranches. Annual settlement now supports aggregation
  with refundable dividend credit and a separate fully-withheld10% election,
  preserving minimum-tax gross-up and requiring complete election-scope review.
  Case contracts and the calculation adapter now reconcile every dividend
  against indexed certificate tranches and saved deductions, rejecting missing,
  duplicate, foreign or unsupported income. The full income suite passed1082.
  The bilingual UI now accepts indexed certificate tranches, clears hidden rates
  for non-creditable dividends and displays refundable credit and final dividend
  tax separately. TypeScript checking and two Edge save/reopen scenarios passed
  (aggregation and final withholding,28.2seconds). Production identity/provider
  acceptance and return rounding remain separate gates. The existing
  ordinary individual adapter continues to reject dividend income.
- The original twelve-row optimizer regression is still running. As of the latest
  process check, PID16760 is live and the log reports three successful checks:
  case001.best, case001.open and case001.valued.best. This is not twelve-row
  completion. Generated CSV/SQLite and optimizer inputs remain frozen.
- The independent physical data copy completed parser and authentic HK-UAE
  treaty rebuilds, with151 treaty clauses and zero citation-integrity errors.
  A later rebuild verified removal of the repealed Chinese notice's three
  clauses and the redundant Japanese individual anti-abuse absence record:
  349documents,42786clauses,815parameters,50decisions. The Japanese statutory
  anti-abuse parameter remains. Source hashes were unchanged after copying;
  no rebuilt files have been promoted into live optimizer inputs. See
  [snapshot provenance](data-reconciliation/isolated-rebuild-20261118.json).
- The next isolated rebuild passed with the official PMK81/2024 original,
  three Indonesian current deadline/holiday parameters, historical tenth-day
  parameter expiry, corrected Chinese document exclusive-end date, and quarantine
  of two conflicting Thai legacy parameters. Its350documents,44886clauses,
  816parameters and50decisions passed citation/hash checks; every cell of seven
  CSV tables matches SQLite, whose integrity and foreign-key checks passed.
  These outputs remain isolated and unpromoted. See
  [rebuild evidence](data-reconciliation/current-parameter-rebuild-20261118.json).
  The Indonesia-only check had zero
  errors but seven existing category/subject-slot gaps, so country acceptance
  did not pass. MLI applicability, source admission and final citation closure
  remain outstanding.
- Legacy live persistence tests include unqualified table deletion fixtures.
  They must run against an isolated disposable database, never the current
  cloud case store. No such destructive test was executed against the cloud.
- A separate real PostgreSQL test used a unique disposable schema and explicit
  SQLAlchemy schema translation, without production table initialization. It
  passed enqueue idempotency, owner-filter rejection, reconnect persistence,
  expired-lease recovery, stale-worker fencing and persisted result retrieval.
  Cleanup completed. This verifies storage behavior across new connections,
  not real JWT/account isolation or a deployed worker restart. See
  [PostgreSQL evidence](data-reconciliation/planning-schema-acceptance-20261118.json).

## Latest isolated source verification

The dedicated read-only cloud reader checked all 635 distinct citation dependencies
in the isolated parameter, absence, rule, predicate and decision CSVs after the
Vietnam distribution and Indonesian statutory/historical-payment source changes.
None are missing or blocked. The statutory-rate and historical payment parameters
now use admitted primary text; the latter retains its inclusive 2014-12-24 through
2024-12-31 applicability window. Full historical penalty-transition handling is
still incomplete. See [current source audit](data-reconciliation/isolated-planner-source-readiness-20261118.json).
This verifies citation availability and admission only, not legal completeness,
cloud parameter parity, runtime promotion or final business acceptance.

The conditional Vietnam distribution exemption has 1,375 passing isolated rule
tests and 30 remaining coverage gaps. Explicit probes verify that unknown
qualification does not produce a definite zero-tax result. The fresh isolated SQLite build and all seven CSV tables now match exactly,
with 357 documents, 45,884 clauses, 811 parameters and 43 absence records.
The build has zero errors, 88 warnings, 5 category gaps, 36 slot gaps and 2
blocked downloads. The 1,375 rule tests also passed against this fresh build.
See [current parity evidence](data-reconciliation/isolated-historical-payment-build-parity-20261118.json). The original optimizer remains running with
four completed cases and no checker failures in those four; its full result is
still pending.

## Cloud parameter catalog synchronization

A fresh dedicated-reader comparison found 760 cloud parameters versus 811 in the
isolated catalog: 51 additions, no removals, 641 identical rows and 119 changed
rows. Of the changed rows, 110 differ only in quote whitespace; nine include
source, scope-note or temporal metadata changes. This is a prepared diff, not an
applied migration. See [exact before/after rows](data-reconciliation/isolated-cloud-parameter-diff-20261118.json).

The local library reader now includes optional `database.meta.catalog_revision`
in pinned snapshots. This preserves the source upload identity and accepted
reviews while rejecting queued snapshots after a catalog revision changes.
All catalog writers must update the revision atomically with their rows. The
44 snapshot/planning-source tests passed; the reader change is not deployed,
and no cloud parameter rows or catalog revision have been changed by this work.
Deploy the revision-aware reader before applying a catalog migration.

## Optimizer validation detail

All twelve golden expectations passed against the original run's existing
products using the original assertion logic. Every saved input exactly matched
its fixture, and product JSON hashes were unchanged before/after this read-only
check. This does not prove exhaustive checker completion or validate staged rules.
See [expectation evidence](data-reconciliation/original-golden-expectations-20261118.json).

The original checker remains active in pairwise exhaustive-baseline comparison.
An independent exact-duplicate compression helper passed 45 tests against the
actual original dominance predicate, including epsilon boundaries and distinct
obligations. A real-case isolated probe is still enumerating paths; no real-case
speedup or full-check success is claimed yet. The frozen checker is unchanged.

## Remaining delivery gates

1. Finish the live optimizer baseline, rebuild the frozen data with the reviewed
   repairs, and validate source hashes, citation closure and CSV/SQLite parity.
2. Resolve remaining source admission and temporal applicability; complete the
   income business scenarios, including individual entitlement and special regimes.
3. Run cross-module regression, deployed two-account isolation, worker recovery,
   actual provider/report execution and end-to-end business acceptance.
4. Deliver the finished integration to `Zhihong-Wu`, then merge reviewed changes
   to `main` after acceptance. Do not equate local commits with remote delivery.

## Historical baseline: 2026-11-15

This is the trial integration on `Zhihong-Wu`. `main` has not been changed.

## Data

- The existing private Supabase `database` schema contains 38,152 clauses and 287 documents from the 2026-11-13 Li upload. The existing chat's `public.sources` / `public.legal_units` are separate.
- Compared the immutable `main` and Li clause CSVs by `cite_id`: 107 main-only citations and 25 shared citations with different text. All 107 main-only citations are whole-document (`#all`) records. The cloud library already has the parent document for 82 of them; 25 parent documents are missing there.
- Created private `database_integration.source_review` through migration `li_data_overlay_20261115` and registered all 132 differences as `candidate`. No candidate has been accepted or exposed to user answers. The table records the main commit, base upload identifier, and document metadata. `anon` and `authenticated` have no table grants.
- The 25 missing documents are predominantly Japan and Thailand sources, plus two Korea documents. Their original content and the 25 conflicting texts still require source, date and hash review before publication. Re-running Li's upload would drop and rebuild the base schema, so it is not an integration mechanism.

## Feature

- The authenticated `/api/library/search` endpoint reads the private cloud library with a bounded query and explicit jurisdiction.
- Explicit mainland-China tax questions in ordinary chat now use a separate source-grounded path. It only admits official `.gov.cn` URLs, requires exact quoted evidence in the model output, and saves the library version and citations with the conversation. A model failure returns links to the source excerpts, not an ungrounded conclusion. Hong Kong-only and mixed Hong Kong/mainland questions remain on the existing workflow.
- English interface selection is honored for new answers even when the question is in Chinese, unless the user explicitly requests another language.

## Acceptance evidence

- Live cloud lookup for `中国内地企业所得税税率是多少？` found `cn.law.eit#4` and related official passages. The generated answer cited Article 4 and distinguished the 25% general rate from conditional rates.
- A local account-scoped FastAPI request created a case and posted the same question: HTTP 201 then 200, saved revision 1, answer status `source_grounded`, workflow `library-cn-0.1.0`. The streaming route also returned a `done` event and an English answer when `locale=en`.
- Compile and staged diff checks passed. The full existing test suite, cloud account isolation, Li planner/report flow, rule evaluation, and Render deployment have not yet been verified.

## Next gates

1. Validate each missing/conflicting source against its official original and effective period, then publish accepted overlay data with an immutable text hash. Keep rejected candidates out of retrieval.
2. Resolve Li's added and changed rule citations against the accepted source version; run its golden cases without replacing the existing HK workflow.
3. Adapt Li's planner and report flow behind the signed-in case API with durable runs and account isolation; add a frontend entry without switching to Li's standalone local-user server.
4. Run regression and cross-account tests on `Zhihong-Wu`, verify the deployed branch, then merge reviewed commits to `main`.
