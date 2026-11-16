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
