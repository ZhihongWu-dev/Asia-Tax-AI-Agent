# Dated Indonesian procedure candidate

Candidate files are preserved in the external audit directory
`integration-audit-20261116/indonesia-dated-procedure-repair/{rule,database}`.
They are not yet promoted into either running-baseline or validation worktree.

Twenty-four rules retain their existing IDs for the current period beginning
2025-12-31; separate `.pre_pmk112` records preserve the previous condition/effect
with an end date of 2025-12-30. The obsolete undated Article 26 FAQ is removed
from both branches. Current references use PMK 112 Articles 2, 8–14, 16 and 18,
plus the official DGT transition announcement items 2 and 3. The catalog candidate
adds the archived, hash-verified transition document and its four exact items.

Validation: 477 rules, 1,452 tests, zero failures/errors, 30 existing coverage gaps.
Seventy-two branch-selection checks cover the day before commencement,
commencement itself and 2026-01-01, with no overlap or gap. All 477 rules expand
against a complete 662-reference bundle. A fresh live-review read finds zero
blocked references, zero missing passages and zero empty passages; the precise
review snapshot and bundle digest are in the adjacent closure JSON.

This does not establish live source admission or full historical correctness.
Earlier treaty dates precede PER-25/2018 in some existing rules; the historical
procedure bindings require further review. Transition announcement publication
date is not inferred from the PDF directory. Its content preserves qualifying
pre-promulgation forms for their stated validity, not automatic treaty eligibility.

Before promotion: resolve historical procedure applicability, admit the new
source through the existing review process, regenerate the catalog migration
plan including the new document and clauses, integrate the candidate rule and
test CSVs with rebuilt artifacts, then execute the repaired golden runner.
The original baseline remains separate. No new full golden run was started.
