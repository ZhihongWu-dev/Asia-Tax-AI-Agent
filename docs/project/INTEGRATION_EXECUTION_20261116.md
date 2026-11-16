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
