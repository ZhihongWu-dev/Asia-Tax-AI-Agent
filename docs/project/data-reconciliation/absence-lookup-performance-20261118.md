# Copy only the matching absence record

Candidate change on `codex/absence-lookup-validation`; not integrated into the
active original or repaired exhaustive golden runs.

A 15-second, 20 Hz nonblocking py-spy profile found the original checker in
pairwise dominance comparison (299 samples, zero errors). The repaired checker
was still enumerating paths and repeatedly copied the complete decision table
through `Optimizer.absence` / `PlanningLibrary.absences` (228 successful samples,
71 sampling errors). Sampling is indicative, not an exact CPU-time measurement.

`PlanningLibrary.find_absence` scans its already detached immutable table in
the original order and deep-copies only the first matching record. It does not
prefer subject-specific entries over an earlier `all` entry. Optimizer callers
use this capability when available; the legacy library loop remains unchanged
for other providers. Returned records remain detached. No DFS path, tax rule,
dominance condition or check is removed.

The actual 43-row candidate decision table gave identical results for all 297
country/subject/slot queries. Three samples of 2,970 calls took 1.710–1.733 seconds
through the old whole-table-copy path and 0.025–0.027 seconds through the selected
row path: about 67.5 times faster for this lookup only. This is not a claimed
end-to-end speedup. The isolated worktree passed 46 source/library/optimizer
selection tests in 4.99 seconds. Earlier focused testing also passed the real
zero-amount optimizer/checker scenario.

The candidate was initially exercised in the development worktree. A full-path
profile then confirmed the original golden process still refers to that
worktree's engine file, so the candidate was moved into this separate worktree.
The original engine was restored byte-for-byte to its frozen fingerprint
`6873f531a18e5ca7`, including CRLF line endings. Its log remained at the same
in-progress case throughout; no process was restarted. The repaired validation
worktree was never modified. Integrate only after the frozen acceptance runs,
and validate the resulting combined version before delivery.

References: [py-spy](https://github.com/benfred/py-spy) (MIT, external diagnostic
tool, no application dependency) and [CPython data structures documentation](https://github.com/python/cpython/blob/main/Doc/tutorial/datastructures.rst).
No external implementation was copied. The audit environment's existing
py-spy 0.4.3 was restored after an unnecessary temporary installation of 0.4.2.
