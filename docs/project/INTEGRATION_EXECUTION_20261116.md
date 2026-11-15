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
