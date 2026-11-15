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
