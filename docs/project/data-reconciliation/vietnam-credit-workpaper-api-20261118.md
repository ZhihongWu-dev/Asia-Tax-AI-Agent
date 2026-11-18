# Vietnam credit workpaper persistence

Added owner-scoped POST/GET `/api/cases/{case_id}/income-tax/credit-workpapers` endpoints (GET includes the workpaper ID). Snapshots retain saved income facts, discriminated calculation bases, decimal-string results and the supplied dossier inventory review. These are partial credit workpapers; they do not update the case assessment status, establish full credit eligibility, or claim filing readiness. The dossier review applies to the supplied credit types and does not prove those types exhaust all requirements of every calculation line.

Request hashes include the input revision and full basis. Replaying a committed request returns its immutable snapshot after a restart or input edit; changed payloads conflict. Revision checks and storage commits reuse the existing case store. No catalog migration or production deployment was performed.

Validation: `python -m pytest tests/income_tax -q` completed with **1331 passed in 18.39 seconds**. New HTTP acceptance covers anonymous and second-account denial, CSRF protection, restart, replay, conflicting request reuse, input edits, stale revisions and failed-calculation atomicity. Existing assessment tests also pass.

GitHub reference: https://github.com/pydantic/pydantic/blob/main/docs/concepts/unions.md — retained string discriminators and ordinary JSON model serialization already used by this repository. No dependency change or external code copied. Full product acceptance remains open: frontend workpaper entry/discovery, complete Vietnam foreign-income assessment, remaining country coverage, deployed acceptance and final branch delivery.

Original optimizer PID16760 was observed live during this change; its log now records five successful exhaustive checks including `cfc_jp.open`. Frozen optimizer inputs were not edited.

## History discovery and browser acceptance

Added owner-scoped GET on the workpaper collection. Summaries compare saved income contents, rather than case revision numbers: saving a workpaper itself increments the revision without invalidating its facts. Changed incomes mark previous snapshots as historical. Collection responses exclude full basis and document references; individual records remain accessible through the existing owner-scoped detail endpoint.

The Vietnam company case panel now lists saved workpapers and shows original per-income gross amounts, credit limits, credit amounts, basis explanations, partial coverage and document inventory status. It distinguishes historical facts and incomplete assessment. This is a history viewer; creating workpapers through a user-facing form remains unfinished.

Validation: HTTP workflow test passed (5.25 seconds), frontend TypeScript/production build passed (existing large-bundle warning), and real-browser `Vietnam saved credit history survives reload and marks changed income` passed (21.7 seconds including servers). The browser test creates a real API snapshot, reopens the case, checks its150 VND subtotal, changes income through the API, reopens again and verifies the original150 VND snapshot and historical label. Initial browser assertion required a literal150 rather than decimal150.00; corrected the assertion to preserve decimal precision.

React reference: https://github.com/reactjs/react.dev/blob/main/src/content/reference/react/useEffect.md — cleanup prevents prior case/detail requests overwriting newer state. No external code copied or new dependency introduced.

## Workpaper entry form

Added a bilingual Vietnam resident-company calendar2026 workpaper form to the existing case panel. It derives eligible route candidates from saved income categories and jurisdictions, preserves decimal amounts as strings, requests per-income treaty/basis confirmations, includes Singapore paid-tax and underlying dividend pool fields, and records document references and form/content confirmations. Users explicitly select income items and document categories; missing documents and unselected foreign income remain outstanding. The form is disabled while case facts have unsaved edits and uses revision-bound request IDs for retry. Backend remains authoritative for all monetary and eligibility checks.

The browser acceptance now creates its workpaper through this actual UI (including an application reference and verification flag), then reopens the case and changes its saved income to verify history. It passed; frontend TypeScript and production build also passed, with the existing bundle-size warning. This establishes one Indonesian dividend UI path; Singapore and underlying dividend form branches still need browser acceptance. All-country complete assessments, source promotion, deployment and branch delivery remain open.
