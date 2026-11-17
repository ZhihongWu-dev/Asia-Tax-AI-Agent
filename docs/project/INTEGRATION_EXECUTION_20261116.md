# Li integration and income-tax execution record

## Authorized outcome

Deliver to `Zhihong-Wu`, not directly to `main`. Preserve the current application framework and integrate Li data, rules, optimization and report functionality. Corporate and personal income tax must both cover cn, hk, sg, id, vn, my, th, ae, jp, kr and in. Corporate work comes first; personal income tax is not optional. User approved implementation and disabled brainstorming.

## Pinned inputs

- Delivery baseline: `3dec54b2211fa2c23f18b01d0f47e262a6c474e0`.
- Li reference: `ce87d83973ac5c1fa40409193bee2e9c32a7a850`.
- Working branch: `codex/li-corporate-integration`.
- GitHub ZIP baseline restored against all 1809 Git blob hashes after partial-clone transport failed.

## Implemented so far

Imported latest agent, rule and optimization sources and library tools. Preserved the existing production API and frontend. Fixed optimizer tests to allocate an isolated temporary directory instead of removing a machine-specific path. Both agent harnesses accept provider credentials from process environment; provider credentials remain scoped. Offline orchestration test uses an explicit placeholder credential.

## Observed verification

- Li source rule baseline: 451 rules, 1362 golden tests passed, zero errors, 30 coverage gaps.
- Imported rule source against pinned Li library: same result. This does NOT prove compatibility with the yet-unreconciled application database.
- Li rule MCP interface: passed.
- Provider environment regression tests: 2 passed.
- Li case MCP: two PDF checks failed because xelatex is unavailable.

## Remaining gates

1. Reconcile source tables, original documents and effective dates; do not silently choose conflicting legal rows.
2. Rebuild the unified library and validate all rule citations against that library.
3. Verify optimization, case tools, orchestration and real report rendering.
4. Adapt planning runs to current authentication, ownership, durable storage and frontend.
5. Implement corporate and personal income-tax workflows and supported calculations with jurisdiction-specific official evidence, dates, deductions, losses, credits and filing requirements.
6. Run business cases for every jurisdiction and subject, missing-information cases, date boundaries, isolation and original dividend regressions. Missing coverage is not success.
7. Verify deployability and live end-to-end behavior, then commit and push all deliverables to Zhihong-Wu. No completion or production readiness is claimed by this checkpoint.


## Validation checkpoint — both income-tax subjects confirmed

The user explicitly requires both corporate and personal income tax; corporate remains first priority. Delivery remains the existing Zhihong-Wu branch.

- Income-tax contract, persistence and authenticated API suite: 30 passed (2026-11-16). Includes owner isolation, CSRF header, stale revision and incomplete-information status.
- Full application regression: 683 passed, 36 skipped, 11 deselected, 14 failed and 2 errors. Failures include language preference expectations, UTF-8 reading, Windows permission assertions, tracing and attachment workers. These are unresolved, not waived.
- Merged library rebuild is not accepted: legacy parameter identifiers violate the new naming convention and some legacy citation identifiers remain unresolved. Preserve source records while reconciling references; do not disable validation.
- Corporate/personal tax calculation, complete jurisdiction-specific acceptance and final remote delivery remain unfinished.


## Structural reconciliation checkpoint

- Migrated 37 legacy parameter IDs to the current naming convention with deterministic suffixes; original-to-new mappings are preserved in data-reconciliation/structural-migration-20261116.json. No application, rule, agent or optimizer references to the old IDs were found. Tax values, dates, names and quoted evidence remain unchanged.
- Rebound 13 unique same-document exact quotes automatically and 8 reviewed citations to nested provisions or byte-identical registered sources. Source hashes and quote checks are retained in reviewed-reference-rebindings.json.
- Fixed HTML section slicing that discarded leading text and short sections. Existing hN IDs remain stable; added lead/short IDs preserve previously lost text, including Thai corporate filing obligations.
- Database publication now requires zero validation errors and uses atomic replacement; validation or write failures preserve the prior SQLite file.
- Database migration/slicing/publication tests: 8 passed with the isolated database environment. Full source rebuild is still in progress; it started before the atomic-publication edit, so its output must not be treated as approved.


## Income-tax calculation and source checkpoint

- Current library provenance audit passes: 314 documents, 38,564 clauses, 808 parameters and 51 decisions; no missing source, hash mismatch, missing citation or quote mismatch. This check does not prove substantive legal applicability or extraction completeness.
- Completed full build 2 produced 19 errors using its initial input snapshot. Eight citation fixes landed during that run and the final three were rebound after the recovered leading text was generated; the live CSV provenance audit now has zero errors. Eight source-extraction failures remain: two Korean law HTML shells and six scanned treaty PDFs. Full build acceptance remains pending.
- Added exact Decimal marginal-band arithmetic and Singapore YA 2026 resident-individual and normal-rate corporate calculations. Corporate calculation covers explicit partial/start-up/no exemption selection, allowed tax set-offs, the enhanced 50% CIT rebate with its cap, and separate cash-grant treatment. Inputs must already be legally established chargeable income; this is not yet a complete gross-income-to-return workflow and is not exposed as a final user result.
- Official IRAS corporate and individual rate pages are saved as immutable source snapshots, registered in doc.csv and bound by SHA-256 to the policy manifest and calculation outputs. Current IRAS corporate page explicitly updates the initially announced 40% rebate to 50%.
- Income-tax tests: 69 passed, including published cumulative personal-tax examples, every marginal threshold, corporate rebate examples, exemption caps, invalid inputs, unverified-year rejection and registered-source hashes.
- Design research: https://github.com/openfisca/openfisca-core (AGPL-3.0; no code copied or dependency added). Its open issues concerning top tax-band and period handling informed boundary/date testing. Official sources: https://www.iras.gov.sg/quick-links/tax-rates/corporate-income-tax-rates and https://www.iras.gov.sg/taxes/individual-income-tax/basics-of-individual-income-tax/tax-residency-and-tax-rates/individual-income-tax-rates .
- Remaining scope is unchanged: all 11 jurisdictions, both subjects, complete intake/eligibility/calculation/report workflow, source and temporal review, existing application regression, durable integration and final delivery to Zhihong-Wu.


## Existing-workspace income-tax intake checkpoint

- Added corporate/personal income-tax intake inside the existing Case details panel for all 11 jurisdictions. It reuses the authenticated owner-scoped API and case list. Supports multiple income items, reporting period, residency, source jurisdiction, local currency, deductions, losses and explicit fact confirmation.
- Unknown amounts remain null; entered zero is preserved. Editing revokes confirmation. Changing jurisdiction with entered money is blocked rather than silently relabeling currency. Optimistic revision conflicts preserve the draft and offer an explicit discard-and-reload action.
- Saved income-tax facts are restored through the ordinary case endpoint; internal receipt/history records are excluded from the public case payload. Missing information is presented with readable field labels. No unverified income-tax liability is displayed.
- Validation: TypeScript build and Vite production build passed; 69 backend income-tax tests passed; 8 browser tests passed together on installed Edge (five new income-tax tests plus three existing case-fact regressions). Desktop and 390px phone screenshots were inspected. An earlier run timed out during browser setup with an anomalous 11.5-hour elapsed time; the fresh full eight-test run completed successfully in 37.5 seconds.
- Playwright supports optional PLAYWRIGHT_EXECUTABLE_PATH for an existing browser; no new runtime dependency was added. Vite still reports its existing large-main-chunk warning.
- End-to-end income-tax rule selection, calculation/report integration and country coverage beyond the initial Singapore arithmetic remain unfinished.

### Local OCR and Korean source correction checkpoint

- Completed six treaty scan transcriptions with local Tesseract and pinned tessdata_fast models. Original PDFs remain unchanged. Five bilingual Japan treaty PDFs use explicitly scoped, rotated lower English regions; skipped Japanese contents pages and all excluded regions are recorded in sidecars. Thai–Vietnam uses full pages. Transcriptions remain pending original comparison; successful OCR is not legal acceptance.
- Added source/model/config fingerprints for resumable OCR and source-hash/path checks. Blank cached pages retain an explicit review warning. Database regression: 12 passed.
- Both saved Korean shell headings and the official sequence-specific pages identify July 2026 consolidations (Acts 21217 and 21221). Corrected the legacy personal law's erroneous January date and mapped both shell IDs to existing same-edition official PDFs. Original shells and complete before/after metadata remain available in data-reconciliation/korean-shell-reconciliation.json. Per-provision commencement and image-table limitations remain unresolved.
- Started a fresh full merged-library build after these fixes; its result is not yet accepted. Country coverage, rule semantics, and complete corporate/personal workflow remain outstanding.

### Windows attachment worker checkpoint

- Fixed unconditional Unix resource imports by sharing platform-specific worker limits. Windows uses an unnamed, non-inheritable Job Object with job-wide CPU/memory bounds and kill-on-close; assignment failure stops the worker before parsing. POSIX CPU limits and Linux address-space limits remain. Worker subprocesses explicitly use UTF-8 for JSON output.
- GitHub research: pywin32 win32job interface and Microsoft Win32 Job Object documentation informed the API mapping; no external implementation or new runtime dependency was copied into this change.
- Three real Windows subprocess tests passed: oversized allocation rejected, busy worker terminated on CPU budget, and descendant terminated when parent is killed. Attachment suite before installing the missing declared OCR runtime: 25 passed, one failed (missing numpy/RapidOCR), one skipped (legacy .doc converter absent). Missing xlrd was installed from the project's existing declared range. OCR dependency installation is still running; full attachment result remains pending.
- Short parameter IDs prevent pytest from injecting multi-megabyte fixture bytes into Windows subprocess environment variables.

- Follow-up: declared OCR runtime installation completed. Attachment and OS-limit regression now 27 passed, 1 skipped (legacy .doc converter). Full merged database build 3 exited 0; inspect STATUS and coverage gaps before any business-acceptance claim.

### China income-tax calculation checkpoint

- Identified image-only comprehensive/business rate schedules in the existing IIT law snapshot. Downloaded the government's text-layer comprehensive-income schedule PDF, visually verified seven bands/quick deductions, registered cn.iit.comprehensive-rate-table and pinned its SHA-256 alongside existing law snapshots. Two alternative official downloads returned 403; no bypass used. The business-income image schedule is still unresolved.
- Added China 2026 domestic resident comprehensive-income calculation with separate wages/service/author/royalty inputs, statutory income conversions, annual basic deduction, explicit allowed deductions/reductions, and prepaid-tax reconciliation. Added explicitly confirmed normal corporate 25% calculation on established taxable income. Both return source hashes and policy versions.
- China plus Singapore calculation tests: 64 passed, including quick-deduction equivalence, threshold marginal changes, category conversions, refunds, input confirmation and source hashes. No claim of complete country workflow: preferential regimes, nonresident/foreign-source treatment, business-income schedule, legal entitlement validation, and UI integration remain outstanding.

### Income classification and precision checkpoint

- China jurisdiction library validation completed: PASSED, errors=0, gaps=0. This is structural library acceptance only; income-tax business acceptance remains open.
- Added separate personal service/author remuneration categories in the existing frontend and backend intake. Company inputs reject these personal categories alongside wages; company service revenue remains business income.
- Unified every intake amount with the Decimal calculation boundary: finite nonnegative amounts up to 1e18, at most six decimal places, no float/bool coercion. Confirmation now requires a JSON boolean. Unknown deductions/foreign tax still remain null.
- Income-tax tests: 126 passed; TypeScript build passed. Additional API checks prove rejected amounts leave case revision unchanged. Started application regression excluding live-database integration tests and the separately executed database-tool suite; result pending.

- Application suite initially failed collection because the new income test shared the basename test_api.py with tests/agent. Renamed it test_income_api.py; restarted only after the failed process exited.
- Reconciled two stale language assertions against the pre-existing LI_MAIN_INTEGRATION_STATUS.md rule (English UI preference, overridden by explicit message language directives). No runtime language behavior changed; 33 answer-quality tests pass. Full regression is still running.

### Application regression and Windows log privacy

- Latest completed broad regression: 796 passed, 2 failed, 36 skipped, 11 deselected. Both failures concerned POSIX permission assertions on Windows logs; implemented real protected Windows DACLs for owner/LocalSystem before log writes and rotation. Permission setup failure prevents record writing. Updated tests query actual Windows ACLs; 11 log/tracing tests pass, including existing-file hardening and failure behavior. No business-state behavior changed.
- Research: Microsoft's GitHub security-descriptor API documentation and Windows classic samples compatibility notes informed native API usage; no external source code/package adopted.
- Started fresh broad regression after permission fix. Located the existing pinned engine in the original checkout and started verified copy installation into this worktree, to execute currently skipped integration tests. This legacy engine is still only the older three-jurisdiction bridge, not proof of full latest-Li/11-jurisdiction acceptance.

- Pinned engine installation completed successfully from the existing local release; both expected source and SQLite hashes verified. New worktree path: data/tax_engine/releases/771e4524961bcc36718db1c9331e7a5f4cda0ce7. Broad application regression remains running; subsequent real-engine coverage must be read from its actual skip/results, not inferred from installation.

### Latest Li rule publication checkpoint

- Found that rule/tools/build.py replaced rule.sqlite even when validation failed and deleted the prior artifact before writing. Changed it to publish only after zero validation/golden-test errors, using a unique temporary SQLite file in the target directory and replacement after successful commit/close. A failed write/replacement retains the previous artifact; diagnostic STATUS remains available.
- Regression: 2 real publication tests pass (serialization/write failure, replacement failure, and an actual invalid CSV build). Rebuilt the current unified source: rules=451, variables=94, predicates=11, decisions=203, golden tests=1362, failed=0, errors=0, coverage_gaps=30. Coverage gaps are still reported and remain acceptance work, not suppressed or relabeled.
- Standard-library reference: CPython SQLite documentation on GitHub; no external implementation dependency adopted. Broad application regression is still live and has not produced a final result.

### Hong Kong income-tax arithmetic and broad regression

- Broad application regression after the Windows fixes and verified legacy-engine installation completed: 835 passed, 1 skipped (legacy .doc converter), 11 live-integration tests deselected, 256.69 seconds. Engine-dependent tests actually ran. This does not establish latest Li's eleven-jurisdiction production integration: the existing domain bridge remains the older pinned CN/HK/SG implementation.
- Added sourced 2025/26 Hong Kong ordinary corporate/sole-proprietor profits calculations with explicit two-tier eligibility, and separate salaries calculations comparing progressive tax on net chargeable income against two-tier standard tax on net income before allowances. Verified 2025/26 100% reduction capped at HKD 3,000 against official rate and enacted-measures pages. Source snapshots and SHA-256 manifest retained.
- Income tests before adding official examples: 143 passed. Added IRD example2627.pdf final-assessment examples 1 and 2: final tax/balance HKD 21,160/11,160 and HKD 0/-800 respectively. Hong Kong tests now 19 passed. Provisional 2026/27 tax, partnership allocations, personal/joint assessment optimization, incentives, foreign credits and entitlement workflow remain unimplemented here.

### Git source reproducibility checkpoint

- Audited every current doc.csv registration against working-file SHA-256 and Git HEAD blob SHA-256. Initially 94 document registrations pointed to 92 uncommitted originals (129.68 MiB); no working-file hash mismatch. Saved originals and reconciled registry in b91aa66. Re-audit: 318 registrations, 0 working mismatches, 0 uncommitted originals, 0 committed hash mismatches. Detailed evidence: data-reconciliation/git-source-integrity.json. This proves byte provenance, not legal applicability.
- Saved 30 OCR transcription/sidecar files and the tested local OCR implementation; ignored only resumable .parts caches. All pending-original-comparison labels and scope exclusions remain explicit.
- Started full merged-library build 4 to include the newly registered Chinese comprehensive-rate table and three Hong Kong source snapshots. No acceptance conclusion until its output is inspected.

### UAE arithmetic and completed merged-library build 4

- Added calendar-2026 ordinary UAE CT arithmetic with an explicit established taxable base, verified credit, ordinary-regime and no-relief-election confirmations. The natural-person scope helper aggregates business turnover and separately records statutory wage/personal-investment/real-estate exclusions; it does not misrepresent scope as a computed zero liability. Ordinary company and individual business tax share the 375,000 AED zero-rate band and 9% excess band. Free-zone, exempt, tax-group, minimum-tax and relief-election determinations are not implemented by this component.
- Official FTA natural-person guide example 17 reproduced: business turnover 3.6m, excluded wage 200k, established taxable income 1.8m, CT 128,250 AED. 25 UAE tests passed; full income-tax suite now 170 passed. Existing registered source originals are bound by SHA-256 in the policy manifest. GitHub OpenFisca country-template remains a period-based rule/testing design reference only; no external code copied or dependency adopted.
- Full merged-library build 4 exited 0: 318 documents, 38,837 clauses, 808 parameters, 51 absence decisions, 0 errors, 141 warnings; 6 category gaps, 36 slot gaps, 0 missing treaty pairs, 2 unresolved downloads. Post-build provenance/citation audit found 0 errors (integrity-after-build4.json). Structural validity does not establish legal approval or close coverage gaps.
- Latest eleven-jurisdiction runtime integration, complete personal/corporate income workflows, remaining country policies, cloud durability/business acceptance and final Zhihong-Wu push remain outstanding.

### Authenticated income-tax calculation workflow

- Added discriminated policy contracts and a case-bound calculation adapter for the existing CN corporate/comprehensive, SG corporate/resident, HK profits/salaries and AE ordinary CT components. No new account or standalone host. Explicit tax-basis explanation, confirmation, regime eligibility and exact monetary inputs are required; claimed deductions are not automatically promoted into allowed deductions. Chinese comprehensive gross income is taken from saved facts. UAE individual business turnover must reconcile to saved business income and requires statutory classification confirmation.
- Added POST /api/cases/{case_id}/income-tax/runs and owner-scoped GET of each saved run. Each synchronous calculation is persisted atomically with its input revision, input/basis/result snapshots, policy/source versions, hash and idempotency key in the existing case store. Retry returns the original immutable run; amended inputs clear the current result but preserve historical runs. Status is calculated_basis, not a completed return or legal approval. PostgreSQL production restart/owner validation still needs live testing; local SQLite reopen is verified.
- Added bilingual calculation forms and source-linked results in the existing income-tax case panel. Explicit regime selection; no inferred eligibility, silent amount conversion or floating-point serialization. Changing unsaved facts disables calculation and labels the existing result as based on saved facts.
- Verification: income suite 184 passed before the final additional jurisdiction/residency test; final workflow subset 15 passed. Initial full browser run: 10 passed, including corporate saved calculation, refresh, amendment invalidation and resident personal calculation; final browser run also completed: 10 passed in 43.4 seconds. TypeScript and Vite build passed (existing >500 KB chunk warning). Auth/chat/runtime regressions: 37 passed. An obsolete exact /health response assertion failed in isolation because runtime metadata now exists; replaced it with an explicit allowed-key check and injected-connection-string non-disclosure assertion, retaining the existing runtime behavior.
- Research: official Pydantic GitHub discriminated-union guidance (existing dependency, no copied implementation), OpenFisca period-based test design (no code adoption), IRAS YA/basis-period explanation and IRD assessment-period guidance. Current adapters deliberately enumerate the verified annual bases; non-calendar company periods and other regimes remain work.
- Still outstanding: remaining jurisdictions and complete tax-base determination/relief workflows; latest Li eleven-jurisdiction planning runtime and source overlay; actual cloud persistence/owner/restart acceptance; all-country business validation; final transfer to Zhihong-Wu.

### Cloud library conflict and snapshot gate

- Inspected live cloud metadata and all review statuses: base upload remains 2026-11-13T03:39:52Z; all 107 main-only and 25 different-text records remain candidates. Existing source lookup did not consult this review table. Added read-side exclusion of unresolved different-text IDs before SQL LIMIT, with explicit review_required for an exact blocked citation. Accepted replacement candidates also stay blocked until an overlay is actually published; only a completed rejection allows the existing base text. No candidate was accepted by this change.
- Each read now pins base metadata plus a SHA-256 of the ordered review records in the same REPEATABLE READ READ ONLY transaction. Missing metadata, stale review/base pairing or a caller pin mismatch fails before reading clauses. Existing mainland research stores this pin in its context and rejects later version changes before any model response; bilingual error explains the need to recheck sources in a new case.
- Verified the actual SQL against cloud PostgreSQL: read-only on, repeatable-read isolation, 25 existing rows blocked, zero unresolved exact matches. Executed the application reader with existing local credentials supplied only to the child process: blocked citation returned no passage, ordinary search returned two passages under the same pin, intentional mismatched pin rejected. Evidence: data-reconciliation/cloud-read-gate-20261116.json. No remote schema/content writes.
- Validation: 43 library/auth/chat/runtime tests passed; frontend TypeScript passed. GitHub SQLAlchemy official transaction documentation and current Supabase connection documentation/changelog informed the transaction check; existing dependency only.
- This is a gate for safe integration, not completion of the unified overlay. Main-only publication, review resolutions, a dedicated least-privilege connection role, latest Li planner integration and the remaining income-tax/business acceptance work are still required.

### Main-only citation provenance and gated overlay reader

- Reproduced the 107 main-only citation set from pinned main 78a037f and Li ce87d83 tables. The existing Zhihong-Wu archive contains the exact main clause/doc Git blobs; verified archive bytes against git ls-tree before use. This avoided a redundant missing-object network fetch, which was explicitly stopped after its process identity was checked. Li table contains 38,152 records at this pinned revision.
- Audited all 107 original files against registered SHA-256: every original verified. 42 complete legacy texts are still contained in current extraction with unchanged source bytes; 63 have unchanged original files but extraction differences; the remaining 2 are the previously documented Korean shell-to-PDF substitutions. Full per-citation evidence: data-reconciliation/main-only-source-audit.json. Text containment is not legal equivalence or approval.
- Preserved all 107 original citation texts plus document metadata in config/library/main-only-candidates.json (about 11.37 MB), sourced from verified immutable Git blobs. Added -text Git attributes for byte preservation. This bundle remains candidate_not_approved.
- Added a unified read path for main-only overlay records: admission requires explicit accepted cloud review, review timestamp/note, matching source commit/document/hash/URL, and no collision with the base library. Bundle SHA-256 is part of the pinned version. Unreviewed exact main-only lookups return review_required with no passages. No cloud candidate was accepted or modified.
- Live application validation: ae.fta.natural-persons-2023#all returned review_required and zero passages; ordinary mainland search returned two passages under the same base/review/bundle pin. Bundle SHA-256: 35e66dadd2c9116594ff44b29ae02731d7468719c206cc00bc5e836cdd571b5c. Local library/overlay/audit/auth/chat regressions: 50 passed.
- Research: CPython difflib guidance and Git object-hash documentation. Used exact containment and hashes rather than fuzzy legal-equivalence inference; no external code or dependency adopted. Source/date review, actual overlay admission, planner integration, all-jurisdiction tax workflows and final business/cloud acceptance remain outstanding.

- Follow-up packaging check: Git diff validation detected CRLF in the byte-preserved JSON container. Normalized only container line endings to LF and made the generator write UTF-8 bytes explicitly; decoded JSON and all original citation text hashes are unchanged. Current bundle SHA-256 is ca5f72ed8286e43576ce09e91afba09f4985d357dd17fe4eef0297a1d563842f; the preceding live check used the pre-normalization bundle hash recorded above.

### Malaysia income-tax workflow

- Added YA2026 Malaysia ordinary company (24%), eligible SME tiers (15% first MYR150k, 17% next450k, 24% excess), resident individual progressive bands and ordinary nonresident individual 30% calculations on explicitly established chargeable income. Verified allowed rebates/credits and period prepayments remain separate; nonresident resident-rebate use is rejected. SME eligibility is explicitly attested and not inferred solely from turnover.
- Verified Schedule 1 Part I paragraphs1/1A/2/2A-2C against the already registered official AGC 1 January2026 updated Act53 PDF, including visual inspection of rate tables at printed pages573-574. The manifest retains the original hash and the source's updated-text/not-authentic-reprint qualification. Official HASiL webpages still label older YAs, so they were cross-checks rather than the sole authority for2026. No new raw source or registry mutation was needed.
- Connected both subjects to the typed authenticated calculation endpoint and bilingual saved-case UI for calendar2026. Dividends/capital gains are rejected by the ordinary adapter and require separate treatment; Labuan, reinsurance, special incentives, minimum top-up tax, joint assessment and noncalendar basis adapters remain outside this component. This is a verified-basis calculation, not a complete tax-return workflow.
- Verification: full income-tax suite212 passed; TypeScript passed; browser suite12 passed in53.8seconds, including Malaysia company and individual calculation, source link and refresh persistence. Screenshot inspected.
- Arithmetic/basis UI now has partial ordinary-regime support for CN/HK/SG/AE/MY; ID/VN/TH/JP/KR/IN still require implementation. All eleven remain in scope for both subjects. Tax-base/relief determination, cross-border interactions, latest Li planner integration, overlay reviews/admission, live cloud acceptance and final Zhihong-Wu transfer remain outstanding.

### Thailand income-tax workflow

- Added calendar2026 ordinary corporate 20% and explicitly qualified SME tiers (first THB300k exempt, next THB2.7m at15%, excess at20%), and resident individual progressive rates with the section48(2) non-employment gross-income minimum comparison. SME qualification includes the decree's continuous-period conditions. Bases remain explicitly established after verified tax adjustments/allowances; this does not determine every expense or complete a return.
- Verified the Thai Revenue Department's authentic-language rate schedule, section48, and consolidated Royal Decrees470/480/530. Registered three immutable original HTML sources and retained their hashes in the calculation manifest. Decree480 exempts method48(2) when tax is **not exceeding THB5,000**; the 2024 English PND90 guide's “less than” wording was not used to override the Thai decree. The THB120k gross threshold comes from section48; old English summaries showing THB60k were not adopted.
- GitHub research revisited OpenFisca country-template for period-specific policy organization and explicit inputs; no AGPL code or new dependency copied. The implementation follows the existing exact-Decimal, typed-basis and immutable saved-run architecture.
- Both subjects are wired into the existing authenticated case endpoint and bilingual interface. Resident personal gross income is derived from saved categories, excluding employment from the minimum-tax base; unsupported foreign/separate-rate categories, unconfirmed classification and net income exceeding gross are rejected. Joint assessment, termination lump sums, property disposal and special regimes remain outside this policy.
- Verification: 240 income-tax tests passed, including inclusive THB5,000 exemption and cumulative-band boundaries; TypeScript passed; all14 browser tests passed, including both Thailand subjects, source links, saved results and refresh persistence. Personal calculation screenshot inspected. Library/snapshot and saved-assessment regressions:30 passed. Whitespace validation passed for authored files with CRLF recognized; immutable downloaded HTML was checked by source hashes instead of changing its whitespace.
- Full build5 completed:321 documents,38,856 clauses,808 parameters,51 absence records,zero errors,141 warnings; six category gaps,36 slot gaps and two unresolved blocked downloads remain. Independent source/citation/quote integrity audit:zero errors. All321 original files match both their registered SHA-256 and committed Git bytes; no uncommitted originals. These checks do not establish legal applicability or full business readiness.
- Partial ordinary-basis workflows now cover CN/HK/SG/AE/MY/TH. ID/VN/JP/KR/IN and the previously listed full-business integration/acceptance work remain outstanding. Nothing has been pushed to Zhihong-Wu.

### Indonesia research preceding implementation

- Official DGT ordinary [company](https://pajak.go.id/id/mekanisme-penghitungan-pajak-penghasilan-badan) and [individual](https://www.pajak.go.id/id/mekanisme-penghitungan-pajak-penghasilan-orang-pribadi) computation pages provide cross-check examples. Existing 2022 English law compilation is not sufficient alone for 2026 applicability. Verify article17 base rounding and article31E mandatory proportional relief against current legislation before implementation.
- [PP20/2026 official text](https://pajak.go.id/en/node/120099) amends PP55/2022 final small-business treatment and transitional qualification. Its page metadata date differs from the promulgation text (22April2026); use provision-level applicability rather than page publication dates. Original source registration and detailed review remain pending.
- OpenFisca country-template research included license, changelog, issues and security page. AGPL-3.0; open issue82 concerns Windows bootstrap directory-renaming permissions; no published advisory shown, which is not proof of security. No dependency or code adopted; continue the existing period-specific adapter architecture.

### Indonesia ordinary resident income-tax workflow

- Implemented calendar2026 IDR ordinary resident corporate annual tax with automatic article31E allocation from complete saved gross receipts: up to IDR50bn receipts, the taxable base attributable to the first IDR4.8bn uses11%; the remainder uses22%. The total taxable base and allocated eligible base are rounded down to thousands; the remainder preserves the total. Explicit receipt-scope confirmation includes returns/discounts and absence of omitted final/exempt receipts. Verified withholding and instalments remain refundable prepayments, not capped credits.
- Implemented full-year resident personal annual tax from established net income, confirmed start-of-year PTKP entitlement (TK/K with0–3 qualifying dependents), statutory thousand-rupiah base rounding and the five progressive bands. Combined spouse income, separate spouse allocations, part-year residence, final/exempt/foreign income and special company concessions are not silently included. PP20/2026 transition applicability must be checked before confirming ordinary treatment. Full final-tax and cross-border workflows remain required for overall completion.
- Registered six immutable government originals: UU7/2021, PP20/2026, PER12/2026 text and annex, and DGT corporate/personal computation examples. During currency checking, discovered PER12/2026 replaces the annual forms from1October2026. Downloaded its988-page annex and visually checked article31E form at PDFpage472 (printed504), comparing oldpage510 (printed629); statutory rounding remains in newpage498 (printed530). Removed only this turn's uncommitted PER11/2025 annex registration/source after retaining the original in the audit folder; no existing repository source was deleted. All active policy citations now use the current annex and amendment text.
- Full income-tax suite:281 passed. Including cloud snapshot/overlay regressions:296 passed. TypeScript passed. Browser suite16 passed; after updating current-source links, both Indonesia browser cases passed again (24.1seconds). Company screenshot inspected. Tests cover DGT computation examples, PTKP codes, all rate/relief thresholds, rounding, preserved allocation totals, excessive prepayments, resident/subject/period gates, unsupported income and immutable source hashes.
- Intermediate build6 passed with326 documents and40,097 clauses, but used the subsequently replaced annex and is not final current-source evidence. Final build7 passed with327 documents,40,130 clauses,808 parameters,51 absence records,zero errors and141 warnings. Six category gaps,36 slot gaps and two blocked downloads remain. Independent source/citation/quote integrity audit:zero errors. All327 registered original files match both working files and committed Git bytes.
- Partial ordinary workflows now cover CN/HK/SG/AE/MY/TH/ID; VN/JP/KR/IN remain to implement. All eleven jurisdictions and both taxpayer types, latest Li planner integration, cloud/owner/restart acceptance, source review/admission and final Zhihong-Wu transfer remain in scope. No remote push has occurred.

### Li local orchestration configuration repair

- Reproduced a failing role-server assertion: checked-in generated configurations still referenced legacy tax-db/tax-opt servers and another developer's absolute Python path. A fresh checkout also lacked the untracked .mcp.json required by the generator. Added a portable versioned server manifest, retained explicit local overrides, validated all role definitions before writes, and regenerated the current specifications. An optional --python selects a machine-local interpreter; otherwise activate the project environment before launch.
- Added the MCP 2.3.0 runtime required by Li's MCPServer imports and locked its missing transitive dependencies. Existing opentelemetry-api 1.45.0 was preserved; pip check reports no broken requirements. Reviewed the official Python SDK migration, release and published security advisories, plus Claude Code strict-MCP configuration issues. No external source code copied. The configured transport is stdio; allowedTools is not claimed to be a complete built-in-tool security boundary.
- Validation: 321 tests passed across configuration, income-tax, chat workflow, library snapshot and overlay suites. The real calculation MCP server exposes exactly evaluate and fx. Regenerated role files match current specifications and manifest. Existing no-model orchestrator checks passed, including role routing and timeout child-process cleanup. Authored-file whitespace checks passed.
- This repairs local orchestration construction. It does not establish real model execution, cloud integration, complete legal applicability or business acceptance. Latest Li planner connection to the application and the remaining country workflows are still pending; no remote push occurred.

### Li planner input-version correction

- Integration inspection found that amount, currency and historical payments were missing from the planner's input identity. Version schema2 binds the complete input with a full SHA-256 digest and retains resolved FX hashing. The product checker now rejects mismatches in the recorded schema, rule, database and optimizer versions. This is not a complete runtime/source pin; cloud snapshot admission still needs integration.
- Consulted the maintained CPython official [JSON documentation source](https://github.com/python/cpython/blob/main/Doc/library/json.rst) and [hashlib documentation source](https://github.com/python/cpython/blob/main/Doc/library/hashlib.rst); used existing Python3.11 standard-library APIs, adding no dependency or copied code.
- The regression passed with a real Japan/Singapore cross-border planner run: amount/currency/history changes produce different identities, dictionary order preserves identity, and altered input or version metadata is rejected. The initial unrestricted search exceeded the regression's180-second bound; the focused regression now explicitly considers Japan/Singapore and passed in7.74seconds. The unchanged complete12-case optimizer golden suite is running separately, with no final result yet. This latency is additional evidence that the latest planner must use durable background execution rather than the old synchronous40-second bridge.

### Durable planning-run storage

- Added a separate backend PlanningStore using the existing application's SQLAlchemy engine. Atomic INSERT/SELECT binds the owner, case revision and persisted case document to immutable planner input and library-version snapshots. Owner/request uniqueness provides retry deduplication; changed payloads are rejected. User reads filter by owner and omit worker lease credentials.
- Workers claim in short transactions using PostgreSQL SKIP LOCKED plus a compare-and-update guard. Database timestamps determine leases. Expired jobs can be reclaimed with a new token; stale workers cannot extend or finish them. Attempts are bounded, exhausted jobs fail visibly, and state events/results survive reopening the store. Raw exception text is not accepted as a persisted error code.
- Research: [Graphile Worker](https://github.com/graphile/worker) is maintained and MIT-licensed; reviewed its recovery docs and open issues about outcome-write failures, retry behavior and job-key races. No dependency or implementation copied. Supabase changelog and current direct-connection/RLS documentation were checked; the Python/SQLAlchemy implementation retains the existing stack.
- Verification:33 tests passed across planning storage, Li configuration/version and existing chat workflow. Seven storage tests include competing submissions/workers, two-owner isolation, changed revisions, restart recovery, heartbeat expiry, stale-token fencing and durable completion. Real PostgreSQL checks also passed using session-local temporary tables; the hardened audit holds one outer transaction and rolls it back, keeping a backend pinned through transaction pooling. No production table deployment or browser grant was performed.
- Remaining: provision the production table with RLS/private backend access, add the authenticated API and UI, connect bounded planner execution with lease heartbeats and pinned source validation, and verify live worker/web restart behavior. This module alone is not end-to-end planning integration. The full optimizer golden job remains running separately; no remote push occurred.

### Planning attempt supervision

- Added an asynchronous one-job supervisor around the durable store. It renews the lease while executing, compares freshly returned source snapshots against an independent copy of the queued snapshot before and after execution, and publishes only through the store's current lease token. A timeout or known execution failure produces a bounded error code; failed renewals and shutdown cancel the attempt and leave its durable record recoverable. Executor cancellation cleanup is awaited before returning control.
- Consulted the CPython official asyncio subprocess/task documentation and its issue139373 on communicate cancellation. Kept the existing standard-library stack; the executor contract requires subprocess cleanup, with no new shell or client-controlled command endpoint. The actual Li execution/source-reader adapter is still pending; this supervisor does not itself make the old engine or Li cloud reader safe to use interchangeably.
- Verification:18 tests passed across supervisor, durable store and Windows worker limits. Tests cover pre/post-execution source changes, successful lease renewal, renewal database errors, stale ownership, shutdown, sanitized failures and a real sleeping subprocess killed/reaped on timeout. Existing OS memory, CPU and descendant-cleanup tests passed. Three full optimizer golden-case directories have been generated so far; that separate process remains live and its final verdict is pending.

### Live cloud snapshot verification for planning

- Extracted a shared read-only library-state reader used by both research search and a new standalone current_library_snapshot operation. Both read base metadata and complete review rows in one repeatable-read transaction, hash the current overlay bundle, validate admitted overlays and reject base collisions. The standalone operation avoids an unrelated legal-text search.
- The planning supervisor now defaults to this live reader before and after execution, passing the queued pin and translating a changed source version into a visible library_version_changed failure. The computation result is not saved when the final check fails. Matching metadata still does not prove all planner citations are admitted; the actual Li reader/execution adapter remains required.
- Verification:25 snapshot/overlay/supervisor tests passed, including changed runtime metadata, default live-reader wiring and post-execution changes. A real read-only cloud check read the same snapshot twice and rejected a deliberately stale pin. Base upload remains2026-11-13T03:39:52Z, overlay SHA256 ca5f72ed8286e43576ce09e91afba09f4985d357dd17fe4eef0297a1d563842f, review SHA256 966f3fb4a19df9d408d3e0a96ca18c27fe5caa69f5839e7e29e217c6f86fd9fd. Audit evidence is check_planning_library_snapshot.json in the integration audit directory. No cloud mutation occurred.
- Consulted the SQLAlchemy official GitHub transaction-isolation documentation; retained the existing read-only repeatable-read pattern and dependencies. Complete optimizer golden validation remains running, with no final verdict yet. Production API/UI, execution adapter and remaining tax-country work are still pending.

### Planner/cloud dependency reconciliation

- Before materializing an execution snapshot, compared every citation referenced by current local rule, predicate, rule-decision, parameter and library-absence tables against the same pinned cloud base/review state. The audit includes retained legacy parameters and is deliberately not date-filtered. Evidence: data-reconciliation/planner-cloud-readiness.json.
- 620 unique references; cloud has38,152 clause IDs and zero admitted overlay rows. Eleven referenced clauses are absent and nine references are blocked by review status (two belong to both groups). Local has48 additional parameters; all shared parameter values, units, citation IDs, effective windows and superseded_by fields match cloud, and no cloud-only parameter IDs were found. This does not compare every parameter column or establish legal correctness.
- No missing citation is a direct rule.csv cite_ids entry. Five blocked citations directly affect nine rule rows: China CFC, Indonesia statutory outbound withholding, Japan/UAE PPT and dividend cap, and five Vietnam company residence/inbound/final-tax rules. Other missing/blocked dependencies include retained Japanese/Thai parameters and absence records; these must remain visible instead of being discarded as unused without dependency analysis.
- This changes the integration order: resolve the five directly used source-review conflicts and explicitly account for the additional parameter/absence dependencies before treating the cloud-backed planner as ready. A metadata version match alone is insufficient. The execution snapshot adapter is not yet implemented or enabled. Full optimizer golden validation remains live; four case directories have been produced, with final verdict pending. No cloud write or remote push occurred.

### China CFC source conflict resolved

- Reviewed cn.gsh.2009-37#all against its registered original, complete cloud text and the current State Taxation Administration page. The official page still labels the notice fully effective. Original SHA256 matches the main-candidate metadata, cloud original and independently hashed local file. All operative wording, including the evidence condition and resident-enterprise consequence, is preserved.
- Git lazy retrieval stalled while fetching Li's large clause CSV. Stopped only the audit's Git process trees and used the cached main extraction plus the already extracted Li file. Main1021/Li543 characters; exact diff removes only webpage footer links after the final operative paragraph. All five reviewed local Li text hashes match the corresponding cloud text hashes; the remaining four source decisions are not inferred from that match.
- Updated only this conflict's cloud review metadata with compare-and-update guards for candidate status, base upload, document hash and clause-text hash. Rejected the replacement candidate and retained the existing cloud text; no source, rule or parameter was deleted or replaced. Added the completed diff as a follow-up note. Evidence: data-reconciliation/cn-cfc-source-review.json. This is source-retention approval, not complete CFC business acceptance.
- Application-reader verification succeeded: the pre-review snapshot is rejected and the exact reviewed citation resolves as available. Directly used blocked sources decrease from five to four, affecting eight remaining rule rows. The readiness report from the preceding commit remains a dated pre-review baseline, not the current review state.
- Indonesia's old English article26 page still states a tenth-day payment deadline, whereas current DGT Coretax guidance points to generally the fifteenth day under PMK81/2024. Keep that source blocked pending provision-level comparison with amendments including PMK1/2026; do not globally approve it because extraction differences are only boilerplate. Full optimizer golden validation remains live (five case directories produced); final verdict and remaining integration work are pending. No remote Git push occurred.

### Japan/UAE source reviews and treaty lookup

- Compared the main and Li MLI-explanation and convention-summary bodies. Both are identical after whitespace normalization between explicit body anchors; original-file and cloud-text hashes match. Independently checked the current Japan MOF pages, including the summary table associations and its provisional-translation qualification. MLI withholding effect date matches the directly referenced PPT rule; other-tax and MAP dates remain distinct.
- Retained both cloud source texts and rejected their replacement candidates with base-upload, original-hash and text-hash update guards. No parameter or rule changed. The summary remains explanatory rather than an authentic consolidated convention and does not by itself establish detailed parent-company eligibility. Evidence: data-reconciliation/japan-uae-source-reviews.json.
- Real lookup preparation exposed a functional gap: search_library rejected the treaty document jurisdiction ae-jp. It now accepts strictly validated distinct two-country pairs and canonicalizes reverse order, while retaining bound SQL parameters and the same review/version checks. Single-country behavior is preserved. Consulted CPython official GitHub fullmatch documentation; no dependency or external code introduced.
- Verification:24 snapshot/overlay tests passed, including canonical/reversed treaty pairs and malformed input rejection before database access. Live application-reader checks reject the old pin, resolve both exact treaty citations, and match full passage/original hashes. Remaining directly used blocked sources are Indonesia and Vietnam (six rule rows). Full optimizer golden suite remains live; six case directories have been produced, final verdict pending. API/UI and actual planner adapter remain incomplete; no remote Git push occurred.

### Complete pinned source reads for planning

- Added packages/domain_bridge/planning_sources.py for exact batch retrieval of full legal passages under a mandatory queued snapshot. It uses the existing read-only repeatable-read admission boundary, includes original-file and full-passage hashes, restores complete admitted overlay text, and rejects blocked or missing dependencies instead of returning a partial source set. This removes the 5,000-character conversational search limit from the planned computation source path; the actual Li constructor/data adapter and execution API remain pending.
- Consulted SQLAlchemy official GitHub transaction-isolation documentation. Retained the existing dependency and transaction pattern; no external code or new dependency adopted.
- Validation:27 source-reader/snapshot tests passed. Live application reads matched both reviewed Japan/UAE sources against their recorded full-text and original-file hashes; pending Indonesia source and a deliberately absent citation were rejected. Evidence: integration-audit-20261116/verify_planning_sources.json. No cloud data mutation occurred.
- The full optimizer golden process remains live and has produced seven case directories; this is progress evidence, not a final passing verdict. Optimizer/database inputs were not edited. A repository-wide whitespace scan reported existing generated law-text whitespace; no normalization was applied to those originals/extractions. New source-reader files passed the targeted whitespace check. No remote Git push occurred.

### Planning catalog and source closure

- Extended the materializer to read jurisdiction, document, parameter, treaty and library-decision tables together with review metadata and complete cited passages in one read-only repeatable-read transaction. All catalog columns are retained, SQL NULL is normalized to the legacy reader's empty-string convention, and duplicate keys are rejected. Rule references supplied by the adapter are augmented with every parameter and library-decision citation, including legacy rows. No caller-selected list can omit those dependencies.
- Added deterministic per-table and whole-bundle SHA256 values, so the actual materialized catalog can be recorded alongside the base/review/overlay pin. This does not yet connect the Li constructors, publish a production route, or resolve outstanding source conflicts and missing citations.
- Verification:30 tests passed across planning sources and library snapshots; tests cover same-transaction catalog reads, automatically included references, changed parameter hashes, blocked parameter dependencies and duplicate keys. Live cloud materialization rejected two unresolved sources before reading legal text, as expected. Evidence: integration-audit-20261116/verify_planning_bundle.json. That early rejection does not constitute a fresh complete missing-citation audit. Existing optimizer golden execution is still live; no optimizer/database inputs or cloud data were changed and nothing was pushed.

### Vietnam small-revenue exemption eligibility

- Downloaded and hashed Decree141/2026, then visually checked original pages2-3. Confirmed previous-period statutory revenue, annualization for fewer than12 active months, current-year new-enterprise rules, subsidiary/related-enterprise exclusion, and the separate2025 fiscal-year transition allocation. Updated vietnam-current-law-review.json; no source text was falsely indexed from signature-only PDF extraction.
- Added a calendar2026 CIT eligibility helper using the existing Decimal validation. Annualization eligibility uses exact cross-products rather than rounded division. Explicit establishment, related-enterprise and statutory-revenue facts are required; new enterprises require actual year-end revenue for final eligibility. Consulted CPython official GitHub Decimal documentation; no new dependency or copied code.
- Verification:23 tests passed, including inclusive thresholds, one-dong changes, short-period annualization, low ambient Decimal precision, related-enterprise exclusion, unknown facts and incompatible inputs. This helper is not yet an enabled Vietnam assessment; full calculation, API/UI, personal-income tax and fiscal-year transition handling remain required. Full optimizer golden run remains live; no optimizer inputs changed and no remote push occurred.

### Vietnam annual company and resident-business reductions

- Visually checked Decree398 original pages1-2 for personal business-income scope, actual annual revenue and subsequent adjustment requirements, supplementing previously checked company provisions on pages3-4. Implemented separate company and resident individual business-income annual reduction helpers for2026/2027.
- Company inputs distinguish tax after other incentives, complete statutory current-period revenue, Vietnam establishment and aggregate revenue of entities formed by a post-resolution split. Personal inputs require residence, business-only tax and complete actual annual business revenue. Both apply the inclusive VND10 billion threshold and reduce tax by30%, preserving exact Decimal arithmetic before assessment rounding. No salary or investment income is silently treated as business income.
- Verification:44 Vietnam relief tests passed. Includes threshold plus one dong, both years, split aggregation, absent facts, zero tax, nonresident/foreign-establishment ineligibility and low ambient precision. Consulted CPython official GitHub Decimal context documentation; retained existing dependencies. These helpers still require full Vietnamese base-tax calculations, reviewed source registration and API/UI integration. Provisional adjustments and interest are not implemented by the annual helpers. Full optimizer suite remains live with eight case directories generated; final verdict pending. No remote push.

### Vietnam ordinary-rate eligibility and income exclusions

- Downloaded and hashed the76-page Decree320/2025 original; visually checked Article11 on page41 and Article23 income exclusions on page72. Implemented calendar2026 ordinary15/17/20 percent selection using the specified previous-period revenue basis, exact annualization, current-period new-enterprise actual revenue and separate related-enterprise eligibility.
- Source review exposed a missing guard in the newly added exemption helper: enterprise revenue eligibility alone must not approve excluded income. Added mandatory income-scope confirmation under Article23(9). The ordinary-rate helper requires confirmation that special industry, preferential or revenue-based regimes do not apply; it does not pretend oil/gas or rare resources use20 percent.
- Verification:64 Vietnam relief/rate tests passed, including3bn/50bn equal boundaries and one-dong excess, short periods, new enterprises, relationship/income exclusions and unknown facts. Existing annual reduction helpers remain intact. Full Vietnam assessment, personal base tax, current amendment reconciliation, source indexing and API/UI are still incomplete. Full optimizer golden handle47029 remains live and unchanged; no remote push.

### Vietnam composed ordinary company calculation

- Added calendar2026 ordinary domestic company calculation combining small-revenue exemption, ordinary rate selection, separately verified tax-reduction incentives, Decree398 relief and prepayments. Vietnam establishment and ordinary domestic scope are explicit requirements. Prior-period rate/exemption revenue and current-period reduction revenue remain distinct, as do the two related-enterprise disqualification tests.
- Added sequence tests showing that prepayments affect the balance after relief and that exempt tax cannot also consume another incentive. Exact fractional-base testing exposed an intermediate-precision boundary: six-place bases can produce eight-place rate tax. The relief helper now preserves validated Decimal intermediates without rounding while external string amounts retain existing validation.
- Verification:80 Vietnam tests passed after the final establishment guard, including refund balances, independent revenue periods, differing relationship thresholds, split aggregation and exact fractional calculations. Calculator remains before assessment rounding; statutory source registration, complete base-tax regimes, PIT and API/UI integration remain pending. Consulted CPython official GitHub Decimal documentation and the official Decree320 original; no added dependency. Optimizer golden handle47029 remains live; no input mutation or remote push.

### Vietnam resident employment annual calculation

- Added resident calendar2026 employment calculation using Law109/2025 Articles8-11 and Article29(2): five marginal annual bands, annual personal deduction and verified dependent-month deductions. Insurance and Article11 deductions require prior eligibility verification. Employment does not receive Decree398 business-income relief. Prepayments affect the balance only.
- Verified registered original SHA256 6b4803e79a068a7ed5727cfe174e337bbb8b1dbb1b1e48f72119b5f5825e9685 against database/raw/vn/vn.law.pit2026.vi.pdf; extracted Gazette pages37-38 and43-44 supply rates/deductions/commencement. Official government explanation https://xaydungchinhsach.chinhphu.vn/noi-dung-chinh-cua-luat-thue-thu-nhap-ca-nhan-so-109-2025-qh15-119260123144204743.htm corroborates resident employment applicability from taxyear2026. Its business thresholds are outdated by subsequent amendments and were not reused.
- GitHub research: CPython official Decimal documentation/tests support reuse of the existing exact arithmetic engine; no external code copied or dependency adopted.
- Verification:103 Vietnam tests passed (23 new employment cases), including annual thresholds, fractional boundary, deductions, refund balance and unverified/invalid inputs. This is before assessment rounding, with established chargeable pay rather than payroll classification. Complete implementing-condition review, foreign credits, special exemptions, nonresident/partial-period rules, source bundles and API/UI remain pending. Optimizer handle47029 confirmed live; no remote push.

### Vietnam calculation provenance

- Added scoped company/employment source manifests with official URLs, original SHA256 and provision locators. Rehashed all six source PDFs against the registered PIT original and cached company originals before writing the manifest. Company original registration remains explicitly pending; provenance does not imply complete legal approval.
- Both Vietnam calculators now return independent copies of their source metadata so a result consumer cannot modify later assessments. Employment cites the PIT law only; company cites the base law, 2026 amendment and three implementing decrees. GitHub research consulted CPython JSON/copy documentation; retained standard-library implementation without adopting external code or dependencies.
- Verification: all386 income-tax tests passed, including scoped provenance and cross-result mutation checks. Full optimizer regression session47029 remains live; OS PID20320 CPU5613.55 seconds confirms ongoing work. No database/rule inputs changed, no production enablement and no remote push.

### Vietnam employment saved-case/API integration

- Added vn_employment_2026 to the existing discriminated assessment contract with strict bounded dependent-month integers and explicit verified-basis flags. Followed official Pydantic GitHub union/strict-mode documentation, reusing the installed dependency and existing contract pattern.
- Routed confirmed resident calendar2026 individual employment cases through the existing calculation and persisted-run service. Rejects other income categories, foreign employment, foreign credits, carried losses, wrong subject/period and chargeable pay above saved gross receipts. This ordinary domestic path does not complete foreign/nonresident or special treatment coverage.
- Verification:402 income-tax tests passed after contract/routing changes. Subsequently added API persistence/restart coverage; all17 Vietnam workflow tests passed including that new test. Recorded result retains exact decimal strings and PIT source hash after engine recreation. UI entry and enterprise route remain pending; no remote push.

### Vietnam employment browser workflow

- Added the 2026 resident employment option to the existing bilingual assessment form, with chargeable pay, verified insurance/Article11 deductions, explicit dependent-month list, prepayments and eligibility confirmation. The option is limited to individual resident calendar2026 cases; server-side scope validation remains authoritative. Added personal/dependent deduction result labels.
- Added strict comma-separated month parsing (integer0..12, at most200 entries), rejecting malformed lists before API submission and preserving edits. Fixed empty official-source anchors when metadata has doc_id but no title. Consulted React official controlled-input guidance and GitHub input issue evidence; reused existing state/event patterns without new dependencies or copied code.
- Verification: TypeScript build passed; all14 income-tax Playwright browser tests passed in1.3minutes, including new Vietnam invalid-month correction, exact tax/refund/deduction results, visible official-source link and reopening saved results. Inspected captured viewport image. Vite production build passed with the existing >500KB bundle-size warning. Optimizer session47029 remains live, now producing ten case directories; final comparison verdict pending. Enterprise Vietnam integration and complete legal/business coverage remain unfinished. No remote push.

### Vietnam company saved-case/API integration

- Added vn_company_2026 to the existing strict assessment union and persisted case router. Current statutory revenue is aggregated from all saved ordinary domestic receipts, including qualifying financial/other receipts; callers cannot submit a conflicting duplicate total. Prior-period revenue/months, new-entity status, split aggregation, two distinct relationship exclusions and verified incentives remain explicit inputs.
- Enforces company/resident/calendar2026 scope, Vietnam establishment, ordinary domestic confirmation and existing calculator eligibility checks. Rejects dividend/capital-gain categories, foreign-source receipts and foreign tax credits; Article23(9) classification remains a required verified basis rather than being inferred from the broad income category. Existing/new period nullability is checked by the calculator. Full special-regime and cross-border coverage remains incomplete.
- Verification:416 income-tax tests passed. New tests cover all-receipts aggregation crossing the10bn reduction threshold by one dong without changing the prior-period rate, strict month/money validation, forbidden duplicate current revenue, unsupported income, new-enterprise prior-period consistency, and company API persistence/restart with original source hash. Pydantic official GitHub research from the preceding contract work remains the implementation reference; no new dependencies. Company UI and complete source indexing remain pending; no remote push.

### Vietnam company browser workflow

- Added bilingual ordinary Vietnam company assessment with separate prior/current revenue treatment, relationship exclusions, verified incentive sequence and split aggregation. Current revenue remains derived from saved receipts. New-entity selection hides prior-period fields and submits explicit nulls; non-split selection similarly omits stale aggregate revenue. Prior active months use a bounded integer selector. Added rate, exemption, other incentive and annual reduction result rows.
- Reused the existing controlled React form approach established by the prior official React/GitHub research; no dependency added. Conditional fields retain draft values when toggled back but cannot leak hidden values into requests.
- Verification: TypeScript and Vite production builds passed (existing >500KB chunk warning). Initial16-test browser run passed14 existing tests; two new tests timed out on exact implicit-label lookup. Updated only their selectors to accessible combobox role/name and strengthened the tax assertion to the actual tax row. Both focused tests then passed, covering existing105m tax/refund45m and new split150m tax without annual relief, source links and persisted reopening. Full legal coverage/source registration and remaining jurisdictions/planner integration are unfinished. No remote push.

### Korea national/local income-tax source review

- Verified hashes of the registered corporate/personal law PDFs and NTS2026 corporate rate guidance. Corporate Act21217 supplementary Articles1/5 establish2026-01-01 business-year commencement for the amended national rates, distinct from the July consolidated version date.
- Confirmed ordinary corporate10/20/22/25% schedule and separate Article60-2(1)(1) corporation schedule without the10% band. Personal Article55 has eight national brackets. Downloaded and hashed official local-tax Articles103-20,103-19 and92 to the external audit directory; embedded table images/full commencement still require further review.
- Added korea-income-current-law-review.json with source fingerprints, national/local distinctions and remaining verification. Local tax must be calculated independently from its base/rates/credits, not inferred as10% of net national liability; foreign-tax adjustments can change the corporate local base. No Korea calculator or production approval claimed. Optimizer session47029 re-polled live; database/rule inputs untouched and no remote push.

### Korea separate national/local gross schedules

- Downloaded, hashed and visually inspected the three official local-tax table images (ordinary corporate, Article60-2(1)(1) corporate, resident comprehensive personal). Added immutable image fingerprints to the current-law review.
- Added independently evaluated national/local annual standard schedules with explicit company classification and confirmed applicability. Gross schedule output deliberately has no final-tax field: credits, minimum/additional tax, rounding and municipal/commencement verification remain required for a full assessment. No API/UI policy enabled.
- GitHub research: CPython official Decimal tests support reuse of existing exact marginal arithmetic; no external code copied or dependency added. Verification:27 Korean schedule tests passed, covering statutory bracket totals, one-won excess, specified-company first-band exclusion, independently different local base and invalid/unknown facts. Optimizer47029 confirmed live at turn start; no database/rule mutations or remote push.

### Korea local commencement and calculation provenance

- Downloaded official amendment history and isolated Act21308. Verified supplementary Articles1/11 apply the amended corporate local rate table to business years beginning on/after2026-01-01. Article10 base amendments instead use filing-time applicability; Article12 filing-rule amendment uses business-year commencement. Stored full original hash and scoped references; did not mistake historic amendment text for current operative law.
- Korean gross schedule results now retain scoped national/local original URLs, hashes, table-image versions and corporate commencement evidence. Each result receives independent metadata. Verification:28 Korean tests passed including image fingerprints, subject scoping and mutation isolation. Final assessment rules/API/UI remain pending. Optimizer47029 remains live; no source database/rule input mutation or remote push.

### Korea corporate minimum-tax reference

- Reviewed official Act132(1) and NTS minimum-tax calculation structure. Downloaded and hashed the current article original. Added separate restored-base reference calculation for general marginal bands and explicit SME/graduation regimes. Statutory base restoration and annual applicability require confirmation; no inference from company age or ordinary taxable income.
- Verification:41 Korean tests passed, including all reference regimes,10bn/100bn boundaries and one-won excess. Output remains a reference amount rather than final tax; benefit limitation, excluded credits, local relief, rounding and API/UI remain pending. Reused exact arithmetic approach from the prior CPython official GitHub research. Optimizer47029 confirmed live and PID20320 CPU6821.89sec; no restart, database/rule mutation or remote push.

### Full Li optimizer golden regression completed

- Long-running original session47029 exited0 with failure_count0. Inspected optimization/tools/check.py::run_tests and the unchanged12-row optimization_test.csv: the suite asserts best paths/tax ranges, open items, omitted-remittance cost, conduct-dependent choices and current/later payment sequences. All12 output directories exist. This is golden behavior evidence, not proof of every business scenario or a full Checker.run_all audit.
- Ran Checker.version_hash separately against all12 completed products before changing any database/rule inputs. Every current runtime/database/rule/input version and version-bearing graph/path/tax/ranking/delta/open-item artifact matched; version_failure_count0. Saved per-case expected assertion, input digest and version-file fingerprint in optimizer-golden-20261117.json. Follow-up session2111 exited0.
- The regression-preservation restriction on pending source input changes is now lifted. Subsequent database/rule changes must receive relevant fresh verification; this evidence remains pinned to the recorded versions. Korea minimum-tax sequencing research also located official Act132/Decree126 distinctions, but no unverified credit sequencing was implemented this turn. Full planner integration, source reconciliation, remaining income-tax coverage and final branch transfer remain unfinished; no remote push.

### Vietnam original registration after golden completion

- Registered five already verified Vietnamese law/decree PDFs through the existing fetch.py local-file path, preserving original bytes and official URLs. All327 prior doc.csv rows remain field-identical; five new originals have matching reviewed SHA256. Law09 metadata separates general24April2026 commencement from Articles1-3 application since1January2026.
- Updated company calculation provenance to registered_original_only with repository paths. This does not approve full text: legal bodies are scanned and signature-only extraction is insufficient. OCR/clause indexing and generated library rebuild remain pending; no cloud source is unblocked by this registration.
- Verification:47 Vietnam company/workflow tests passed, including persisted result provenance. Scoped diff check corrected CSV CRLF-only whitespace on added lines. Previous optimizer golden result remains evidence for its recorded327-document input snapshot; subsequent source changes need fresh relevant verification. No remote push.

### Vietnamese OCR started with pinned local model

- Researched official Tesseract tessdata_fast documentation/license; added Vietnamese model at existing pinned revision87416418657359cb625c412a48b6e1d6d41c29bd to external audit tessdata cache, retaining Apache2 license and SHA256. Reused resumable local OCR at300dpi, all pages, no clipping/skips.
- Session96212 remains active across five originals. Completed Law09 two pages and Decree141 four pages; verified source hashes, page counts and every transcription page hash. Outputs explicitly pending original comparison. Sampling shows spacing/diacritic/stamp errors; small-component OCR warnings also occur. No legal approval or full indexing claimed.
- Identified build merge defect: signature-only native text exceeding50characters can override the full OCR page. Do not rebuild/index these originals until explicit full-page OCR handling is fixed and tested. Remaining OCR continues from fingerprinted page cache; no remote push.

### Full-page OCR merge integrity

- Fixed build extraction so fingerprinted full-page local OCR can replace a native signature-only text layer. Validates original hash, source/config/model profile, page sequence/count and every page content hash; incomplete pages fail. Clipped/skipped scopes and legacy image OCR retain their separate merge behavior. Integrity validation does not grant legal-text approval.
- GitHub research: official PyMuPDF full/partial OCR documentation and example informed the scope distinction; no external code or dependency adopted. Verification:12 focused extraction/OCR tests passed. Real Law09 and Decree141 extraction now returns1885/1961 first-page characters including operative articles rather than signature metadata. Whole library rebuild remains pending original comparison.
- OCR session96212 continues with the remaining Vietnamese originals; preserve its resumable page cache. No remote push.

### Vietnamese full-original OCR completed

- OCR session96212 completed with exit0. All five registered originals now have full-page transcriptions: Law09 (2), Decree141 (4), Decree398 (10), Law67 (21), and Decree320 (76), totaling113 pages.
- Independently revalidated original source/model profile, ordered page hashes/counts and whole-transcription hashes against vietnam-ocr-progress.json. All five passed. Trial slicing produced247 clauses; this count is extraction evidence, not proof of legally complete or correct provisions.
- Preserved the remaining three transcripts and provenance metadata. All remain pending_original_comparison; original comparison, corrections and full indexing are pending. No cloud approval, remote push or full business acceptance claimed. Both corporate and personal income-tax coverage remain required across all11 dividend jurisdictions.

### Vietnamese citation segmentation review

- Visually compared Decree398 original page3 with OCR. Article3 paragraph1 was misrecognized as `1,`, so consecutive paragraph slicing omitted all four paragraph-level citations while retaining their text inside Article3.
- Recorded an exact source/transcription-hash-bound correction, preserving raw OCR. In-memory trial correction restores #3.1 through #3.4 and increases this document from11 to15 clauses. Correction application in the build remains pending; this is not approval of the remaining transcription.
- Consulted official PyMuPDF GitHub OCR documentation for extraction scope; no dependency or external code adopted. Evidence: vietnam-ocr-reviewed-corrections.json.

### Reviewed OCR correction build integration

- Build now applies a separate exact-correction manifest after full-page OCR integrity verification. It checks document identity, review status, original and transcription SHA-256, input pages, exact page/unique text match and evidence. Raw OCR remains unchanged; output retains OCR status rather than claiming whole-text legal approval.
- Applied the verified Decree398 Article3 paragraph marker correction. The real-source regression restores all four paragraph citations.21 extraction/correction tests passed, including stale hashes, unreviewed status, wrong/boolean page, missing/ambiguous targets and invalid replacements; scoped diff check passed.
- GitHub research used CPython official hashlib implementation/tests; standard-library SHA-256 retained, no dependency or external code adopted. Full indexing and original comparison of remaining text remain pending; no remote push.

### Income regression and Vietnamese coverage acceptance

- Existing complete tests/income_tax suite passed457 tests in12.72s against af7af9e. This covers implemented behavior, not all-country business completeness. Evidence is income-regression-20261117.json.
- Verified Git byte-preservation attributes for OCR artifacts. Existing slice_all propagates extraction errors into build errors and prevents SQLite publication when errors exist.
- Vietnamese read-only acceptance session95600 finished exit1: zero errors, seven coverage gaps (category10 plus company/individual penalty, restructure and exit parameter slots). No generated library rewrite. These gaps must be resolved with applicable sources and rules, not hidden by claiming OCR completion is business acceptance.

### Vietnamese tax-administration original acquired

- Registered official Gazette38 containing Law108/2025/QH15, original SHA256 ce2ec36223b931f0754d15f23aecd83405b386f36fbd4cbd83d300b45b117662. Native text extraction succeeded; existing multi-law selection correctly isolated53 articles and330 clauses from the145-page issue.
- Confirmed trial references16.2,17.2,52.1,53.2 and the statutory daily-rate text. Category10 now has an original source; no penalty parameter published until implementing legislation, exceptions and transition are checked. Article17 administrative debt settlement must not be substituted for restructuring capital-gains or emigration-tax rules.
- General commencement is1July2026 with Article52 exceptions and Article53 transition. Full library rebuild and coverage recheck pending. Review evidence: vietnam-tax-administration-review.json. No remote push.

### Vietnamese statutory late-payment rate and implementation source

- Registered official Decree252/2026 PDF from the government gazette attachment, SHA256 0ae4bf867af790bab3290df5c3b326a1070500c570a7a78f5cf152f1bf4da390. Native extraction/trial slicing produced428 clauses; reviewed Articles24,26,74,75 alongside Law108 Articles16,52,53.
- Added the statutory0.03 percent/day parameter for both subjects from1July2026 with an exact Article16(2) quotation. Targeted check_params passed. Scope notes retain delegated adjustments, transition, ordinary day-after-due through day-before-payment, distinct clawback timing, offsets, suspensions and exceptions. No claim of complete penalty engine or administrative-fine coverage.
- Official-source amendment search did not establish a later rate change; future-date evaluation still needs version review. Existing source parser reused; CPython GitHub date/Decimal references consulted for subsequent calculation design, no external code adopted. Full library/coverage rerun pending. No remote push.

### Database regression during full local rebuild

- Full database regression suite completed exit0:35 tests passed in9.72s against4de76cf. This verifies implemented extraction/reconciliation behavior, not full legal coverage.
- Full rebuild session41466 remains live. Legacy Office conversion completed and generated text files advanced through multiple jurisdictions; CPU usage increased. Do not start a duplicate build. Prior SQLite/clause/files/status outputs are backed up in before-vietnam-index-20261117 under the external audit folder.
- Final rebuild counts and SQLite integrity/source closure remain unverified until the existing process exits. No generated outputs staged and no remote push.

### Full local rebuild and index consistency verified

- Existing build session41466 completed exit0:334 documents,41139 clauses,809 parameters,51 absence records, zero errors,141 warnings. Remaining global gaps:5 categories,34 subject slots,2 unresolved downloads; no missing treaty pair rows. Vietnamese gaps are now company/individual restructure and exit (four), not seven.
- Independently opened resulting SQLite read-only: PRAGMA integrity_check returned ok; all rows/columns of seven CSV tables matched SQLite; all711 registered files matched size/SHA256. Confirmed restored Decree398 #3.1-#3.4, Law108 #16.2, Decree252 #26.1, and0.03 daily percentage parameter in this database version.
- Database SHA256 0bf4ede77a7385a0f61ec9888ed95ad0fe17ea3d3a521e001ea83035bee827d7. Evidence saved in database-regression-20261117.json; independent verification script/result remain in external audit directory. Generated outputs remain unstaged pending the larger reconciliation review. No remote upload/push or claim of legal/business completeness.

### Vietnam personal capital-transfer parameter coverage

- Verified registered native-text Law109 Articles13,23,29 against current official government explanation. Added six explicitly resident/nonresident parameters:20 percent on established capital gain, conditional2 percent on capital proceeds where purchase price/costs cannot be established, and0.1 percent on securities proceeds. These are distinct methods, not interchangeable rates or elective minima.
- All six exact quotations, citation existence and parameter-schema checks passed against the rebuilt library. Commencement is1July2026 under29(1), not the resident employment/business retroactivity in29(2). Territorial scope and classification limitations are retained in each parameter note.
- Evidence: vietnam-capital-transfer-review.json. This supplies personal transfer inputs but does not complete restructuring calculations, implementing-law exemption/classification review, corporate transfers or emigration tax. SQLite still represents the preceding809-parameter build; rebuild required after new rows. No remote push.

### Vietnam personal transfer implementation source

- Acquired and registered final Decree253/2026 official gazette PDF,61 pages. Native extraction and trial slicing verified key Article10/53/54 paragraph references. Stored original fingerprint and implementation requirements in vietnam-capital-transfer-review.json.
- Final Article10(2) includes personal joint-stock-company shares in securities; unlisted status alone must not trigger non-security capital-gain treatment. The March draft and corporate rules differ. Whole single-owner business transfers linked to real estate require a different classification.
- Reviewed installment-interest exclusion, documented basis/costs, statutory securities valuation/timing and contribution deferral followed by later taxable events. These requirements must precede API calculation support; six statutory rate parameters alone do not implement these events. Full rebuild pending; no remote push.

### Vietnam personal ordinary-transfer calculation core

- Added resident/nonresident ordinary personal transfer calculation with distinct net-capital-gain20%, unknown-cost capital-proceeds2%, and securities-proceeds0.1% methods. Requires explicit verified classification/valuation/territorial scope, ordinary taxable-sale applicability and recognition date July-December2026. Unknown-cost treatment cannot take partial/assumed deductions; securities cannot deduct acquisition costs. Losses produce zero current tax; prepayments remain separately visible.
- Results retain scoped original hashes/URLs and residence-specific statutory references. Source metadata is copied per result. Contributions/deferred realisations, real-estate-linked whole-business sales, derivatives, exemptions and treaty relief remain separate requirements; no API/UI enabled by this module.
- GitHub research: CPython Decimal documentation/tests informed independent precision context; reused existing amount validation, no external code/dependency.22 targeted tests passed; complete income suite479 passed in9.64s. Scoped diff check passed. API/case integration and full special-event coverage remain pending; no remote push.

### Vietnam personal transfers connected to saved-case API

- Added discriminated assessment contract with one basis per saved income item. Router requires exact index coverage, domestic transfer proceeds, personal subject, confirmed residency and costs reconciled to saved deductions. Proceeds come from the immutable case snapshot; clients cannot supply a competing amount. Each transaction is calculated separately, so one transaction's loss cannot offset another's gain.
- Reused authenticated income-tax run persistence and revision controls.13 targeted workflow tests passed, including changed saved proceeds, missing/duplicate/coerced indices, disallowed facts, nonresident provenance and API result/source persistence after store restart. Complete income suite492 passed in9.25s; scoped diff check passed.
- GitHub research: Pydantic official discriminated-union documentation informed reuse of the existing contract; no dependency or copied implementation added. Page/form integration and special transaction coverage remain pending. No remote push.

### Vietnam personal-transfer form connected

- Added bilingual transfer policy for saved personal capital-gain records, with separate date, asset/cost method, costs, prepayment and applicability confirmations for each saved income index. Gross amounts remain in saved facts; conditional costs serialize as null when securities/unknown-cost methods are selected, even after entering costs under the known-cost method.
- Existing saved-result and source rendering reused. TypeScript and production Vite build passed (existing >500KB chunk warning). Real Edge browser test passed after correcting an exact-label test locator to combobox role/name: enters costs, switches to securities, calculates1m tax on1bn proceeds, verifies two original links and reload persistence.
- GitHub research: React official controlled-form examples informed reuse of state/confirmation handling; no dependency or external implementation copied. Multi-transaction visual detail, broader browser regression and special-event coverage remain pending. No remote push.

### Per-transfer results and full income browser regression

- Saved results now expose each transfer's persisted index, recognition date, method, proceeds, base, fractional rate, tax, prepayment and balance in bilingual details. Values come from the saved result, not current draft inputs.
- TypeScript and scoped diff checks passed. Full income-tax Edge browser suite completed17/17 passed in1.0m, including saved/reloaded transfer detail, hidden-cost clearing, company/employment policies, other implemented country flows, conflict recovery, invalidation after edits and mobile intake.
- GitHub research: React official list-rendering documentation informed stable saved-index keys. No dependency added. This is regression evidence for current implemented scenarios, not completion of all11 countries, special-event rules or Li planner integration. No remote push.

### Li optimizer explicit-library injection

- Optimizer -> Query -> RuleTool -> RuleSet now accepts and reuses one explicit library object. Existing callers retain default local/remote behavior. Falsey injected libraries no longer trigger a hidden default Library allocation.
- Injected libraries must provide nonempty version_metadata; Query refuses to label them with unrelated local CSV hashes. The concrete pinned-bundle adapter and executor remain pending; this change alone does not enable cloud planning.
- Isolated integration test passed with default constructors forbidden, including falsey object identity across all layers and missing/empty-version rejection. Existing bounded optimizer input/version/stale-product regression passed (7.31s), confirming original local execution remains functional. Scoped diff check passed.
- GitHub research reviewed CPython sqlite3 snapshot/backup documentation; retained explicit object injection as the bridge seam rather than adding another mutable database copy. No external code or new dependency adopted. No remote push.

### Pinned planner execution and case API checkpoint

- Implemented verified offline PlanningLibrary, complete parameter/factor citation closure, and library injection into the artifact Checker. Full local catalog compatibility runs now execute the bounded JP/SG example and Checker.run_all; they do not establish cloud admission or all-country business acceptance.
- Added a resource-limited child runner, cancellation/reaping, artifact hashes and lossless gzip/base64 persistence payload. A real artifact exceeded the 5 MB store limit as plain JSON; compressed output passes the same limit and all restored file hashes match. The worker still owns lease fencing and live library checks before/after execution.
- Runtime source/CSV fingerprints are persisted at enqueue and required during execution and retries. Missing or changed runtime versions fail before cloud reads. Source admission and execution are connected in execute_job; unresolved cloud source review still prevents production planning.
- Added required-input contracts and revisioned Li inputs in existing case documents. The enqueue wrapper uses only the saved case version. API routes: GET/PUT planning-input, POST planning-runs, GET planning-runs/{run_id}, all beneath /api/cases/{case_id}. Owner isolation, stale revisions, concurrent edits, restart/retry receipts and unauthenticated rejection are covered. HTTP handlers do not execute the optimizer.
- Added scripts/run_planning_worker.py, with --once for one claim, bounded polling, lease recovery, SIGTERM cancellation and fixed-code failure output. It checks the complete planning_runs schema without creating it. Database selection matches API precedence: FSIE_WEB_DATABASE_URL, then FSIE_DATABASE_URL. Worker controls use FSIE_PLANNING_POLL_SECONDS, LEASE_SECONDS, WALL_SECONDS and MAX_ATTEMPTS.
- Deployment remains incomplete: planning_runs (including runtime_snapshot) and its backend-only grants/RLS have not been provisioned in production; no worker service has been launched. UI, cloud source reconciliation, full corporate/personal income coverage and final branch transfer remain outstanding. No remote push.

### Production planning table provisioned

- Generated Alembic revision 0006_planning_runs using the existing migration CLI. Frozen table/index DDL matches the planning store, includes runtime_snapshot, enables RLS and revokes all table privileges from PUBLIC, anon, authenticated and service_role. The database-owner backend remains the access path. Downgrade retains records and RLS; re-upgrade adopts the retained table. Combined migration metadata and round-trip expectations now include planning_runs.
- Applied the generated DDL through Supabase migration tooling to the existing project, with a precondition requiring Alembic version 0005 and an atomic advance to 0006. Verified all 19 columns, four indexes, RLS enabled and all SELECT/INSERT/UPDATE/DELETE checks false for the three API roles. No user data was changed.
- Live PostgreSQL transaction exercised enqueue-shaped insertion, rejection of running status without a lease, valid lease acquisition and result write; rollback left zero synthetic rows. Offline Alembic compilation also passed using a dummy PostgreSQL URL. Full fresh-database migration round-trip was updated but not run in this environment.
- Security advisor adds only the expected RLS-without-policy information for this backend-only table ([explanation](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy)). Existing vector-extension location and leaked-password-protection warnings predate this change. No worker service launched and no application deployment or remote Git push performed.

### Saved planning results in the existing workspace

- Added owner/case-scoped, paginated history and basic planning input UI. Saved inputs retain zero amounts, revision checks and server-side submission receipts. Advanced fact entry remains outstanding.
- Artifact API verifies compressed payload size/hash, individual file hashes, library/runtime pins and successful full Checker marker before returning allowlisted JSON artifacts. The real subprocess/adapter tests exercise restored tax and ranking artifacts; API tests cover pending results and foreign owners.
- Result viewer loads tax, ranking, paths and open questions for one saved task, verifies matching input version/run/revision and branch/path associations, and discards responses after task changes. History results remain independent of unsaved form edits. Conditional order is explicitly distinguished from an execution recommendation; incomplete tax bounds remain unknown, while zero remains zero. Assumptions and unresolved facts are inspectable.
- GitHub reference: React's official useEffect documentation (https://github.com/reactjs/react.dev/blob/main/src/content/reference/react/useEffect.md) informed stale-response cleanup. No external code or dependency was adopted.
- TypeScript and production Vite build passed; existing bundle-size warning remains. Edge browser coverage checks saved inputs/history, zero/unknown values, conditional results, immutable saved amount, mismatched artifact rejection and retry. These UI fixtures do not prove live cloud source admission or production worker operation. Corporate and personal all-country acceptance and final transfer to Zhihong-Wu remain pending; no remote push.
