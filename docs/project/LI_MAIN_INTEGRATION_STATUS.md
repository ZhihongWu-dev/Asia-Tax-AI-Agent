# Li/Main integration status (2026-11-18)

## Current delivery state

Work is on `codex/li-corporate-integration`, tracking `origin/Zhihong-Wu`.
The final integration has not been pushed or merged to `main`. The historical
2026-11-15 record below is retained as baseline evidence, not current status.

- Scope remains Li data/function integration plus both corporate and personal
  income tax across cn, hk, sg, id, vn, my, th, ae, jp, kr and in. Passing ordinary
  calculations does not complete special regimes or production acceptance.
- Saved income facts, explicit calculation bases, revision-bound results and
  bilingual forms are implemented. The latest income suite passed 1034 tests.
  Singapore employment settlement additionally passed three browser scenarios
  (two save/reopen cases and the existing rate-only entry). These use local
  fixtures, not production identity/provider acceptance.
- Cross-module offline regression completed: `pytest tests -m 'not integration'
  --ignore=tests/database -q` returned1943 passed,1 skipped and11 deselected in
  439.31seconds. The skip is the unavailable legacy attachment converter; the
  deselections are live-database integration tests. Database extraction tests
  passed69 separately. These results do not establish live account isolation,
  provider availability or hosted-worker acceptance.
- Planning runs are connected to the signed-in case API and UI, with a durable
  queue, worker leases, cancellation and pinned artifacts. The hosted worker
  has not been provisioned or accepted. See [worker deployment](PLANNING_WORKER_DEPLOYMENT.md).
- A dedicated cloud law-library reader has verified read-only grants and cannot
  access private cases/jobs. Its deployment secret still needs installation.
- Cloud source review queried on 2026-11-18: different-text records have 2 accepted
  replacements, 16 candidates and 7 rejected decisions; main-only records have
  6 accepted sources, 104 candidates and 3 rejected decisions. Total is 138. A rejected
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
- A fresh dedicated-reader audit includes625 current local citation dependencies,
  including factor citations:9 are missing from cloud admission,6 are blocked
  (some overlap), and55 local parameters are absent from the cloud catalog. See
  [dependency evidence](data-reconciliation/planner-source-readiness-20261118.json).
  These counts replace the older audit that reconstructed admission rules itself.
- Thai PIT overview review found conflicting legacy parameters: its residence
  wording excludes day180, while Revenue Code section41 includes it; its fixed
  dividend credit3/7 omits section47bis's distributing-company rate dependency.
  The active residence rule already uses the correct >=180 boundary. Legacy
  catalog quarantine/rebinding and dividend-credit business acceptance remain
  pending; the outdated overview has not been admitted to close missing sources.
  See [conflict evidence](data-reconciliation/thailand-pit-overview-conflicts-20261118.json).
- A Thai section47bis dividend-component calculator now computes each certified
  tranche's own corporate-rate gross-up, separates shareholder withholding and
  preserves non-creditable tranches. Annual settlement now supports aggregation
  with refundable dividend credit and a separate fully-withheld10% election,
  preserving minimum-tax gross-up and requiring complete election-scope review.
  Case contracts and the calculation adapter now reconcile every dividend
  against indexed certificate tranches and saved deductions, rejecting missing,
  duplicate, foreign or unsupported income. The full income suite passed1082.
  UI integration and browser acceptance remain required before claiming a usable
  dividend workflow. The existing
  ordinary individual adapter continues to reject dividend income.
- The original twelve-row optimizer regression is still running. As of the latest
  process check, PID16760 is live and the log reports three successful checks:
  case001.best, case001.open and case001.valued.best. This is not twelve-row
  completion. Generated CSV/SQLite and optimizer inputs remain frozen.
- Parser fixes are committed but await generated-data rebuild: Chinese inline
  numbers, malformed HTML main containers and Indonesian standalone legal
  numbers. Pending data work includes HK-UAE originals/MLI applicability,
  Indonesia's fifteenth-day payment deadline, source admission and citation closure.

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
