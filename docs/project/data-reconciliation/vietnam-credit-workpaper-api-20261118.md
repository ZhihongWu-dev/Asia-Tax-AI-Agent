# Vietnam credit workpaper persistence

Added owner-scoped POST/GET `/api/cases/{case_id}/income-tax/credit-workpapers` endpoints (GET includes the workpaper ID). Snapshots retain saved income facts, discriminated calculation bases, decimal-string results and the supplied dossier inventory review. These are partial credit workpapers; they do not update the case assessment status, establish full credit eligibility, or claim filing readiness. The dossier review applies to the supplied credit types and does not prove those types exhaust all requirements of every calculation line.

Request hashes include the input revision and full basis. Replaying a committed request returns its immutable snapshot after a restart or input edit; changed payloads conflict. Revision checks and storage commits reuse the existing case store. No catalog migration or production deployment was performed.

Validation: `python -m pytest tests/income_tax -q` completed with **1331 passed in 18.39 seconds**. New HTTP acceptance covers anonymous and second-account denial, CSRF protection, restart, replay, conflicting request reuse, input edits, stale revisions and failed-calculation atomicity. Existing assessment tests also pass.

GitHub reference: https://github.com/pydantic/pydantic/blob/main/docs/concepts/unions.md — retained string discriminators and ordinary JSON model serialization already used by this repository. No dependency change or external code copied. Full product acceptance remains open: frontend workpaper entry/discovery, complete Vietnam foreign-income assessment, remaining country coverage, deployed acceptance and final branch delivery.

Original optimizer PID16760 was observed live during this change; its log now records five successful exhaustive checks including `cfc_jp.open`. Frozen optimizer inputs were not edited.
