# Preliminary extension baseline

Acceptance: NOT RUN. The original prescribed collection/build tools and superseded.csv are missing.

These checks are supplementary and do not replace the checks in spec.zh.md sections 4.9 and 5.

## Existing data

- jurisdiction: 11 rows
- doc: 95 rows
- files: 190 rows
- clause: 5911 rows
- param: 124 rows
- decision: 14 rows
- treaty: 19 rows
- Indexed files verified: 190/190
- Findings: 50

## Coverage gaps

| Region | Documents | Domestic parameters | Missing categories | Missing subject/slot cells | Missing owned pairs |
|---|---:|---:|---|---:|---:|
| cn | 24 | 36 | none | 0 | 0 |
| hk | 10 | 18 | none | 0 | 0 |
| sg | 5 | 12 | none | 0 | 0 |
| id | 0 | 0 | 1, 2, 3, 4, 5, 6, 7, 8, 9, page_treaties, page_rates, page_deadlines | 12 | 7 |
| vn | 0 | 0 | 1, 2, 3, 4, 5, 6, 7, 8, 9, page_treaties, page_rates, page_deadlines | 12 | 0 |
| my | 0 | 0 | 1, 2, 3, 4, 5, 6, 7, 8, 9, page_treaties, page_rates, page_deadlines | 12 | 3 |
| th | 0 | 0 | 1, 2, 3, 4, 5, 6, 7, 8, 9, page_treaties, page_rates, page_deadlines | 12 | 1 |
| ae | 0 | 0 | 1, 2, 3, 4, 5, 6, 7, 8, 9, page_treaties, page_rates, page_deadlines | 12 | 10 |
| jp | 0 | 0 | 1, 2, 3, 4, 5, 6, 7, 8, 9, page_treaties, page_rates, page_deadlines | 12 | 5 |
| kr | 0 | 0 | 1, 2, 3, 4, 5, 6, 7, 8, 9, page_treaties, page_rates, page_deadlines | 12 | 4 |
| in | 0 | 0 | 1, 2, 3, 4, 5, 6, 7, 8, 9, page_treaties, page_rates, page_deadlines | 12 | 6 |

## Required source files

- database/tools/build.py
- database/tools/fetch.py
- database/tools/find.py
- database/tools/clause_diff.py
- database/tools/upload.py
- database/samples/slicers-2026-10-23/run_slicers.py
- database/superseded.csv

## Original-tool discovery

All 11 visible branches of ZhihongWu-dev/Asia-Tax-AI-Agent were checked. None contains database/, clause_diff.py, or the required slicer sample runner.
Local official/tools/build.py belongs to a different data package and has not been substituted.

## Next action

Obtain the matching source database/ package, including tools/, samples/, superseded.csv, blocked.csv and session_log.md if present. Preserve the existing downloaded rows when merging. Run the original baseline build and per-region acceptance before collecting missing data.

No business data or remote data was changed. See baseline.json for each missing slot and pair.
