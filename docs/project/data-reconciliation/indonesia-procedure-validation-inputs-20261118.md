# Indonesian procedure validation inputs

This validation branch now includes the isolated dated-procedure candidate:
477 rules and 1,452 rule tests, with rebuilt rule.sqlite and STATUS.md.
The isolated build returned zero failures/errors and 30 existing coverage gaps.
The 24 affected rule IDs retain their current-period identity; historical
branches use `.pre_pmk112`. Current-period procedures include the DGT certificate
transition announcement, preserving valid old-format certificates.

The external candidate database under
`integration-audit-20261116/indonesia-dated-procedure-repair/database` is required
for this run: the previous staged database lacks the new announcement clauses.
The candidate closure contains 662 nonempty references, no missing or currently
blocked references; all 477 rules expand. This is offline source materialization,
not cloud admission. The primary integration branch preserves its older baseline.

All twelve optimization golden inputs have dates in 2026 (April 30 or December
25). The prepared v4 runner injects this candidate library through the supported
run_tests keyword argument, retains the optimizer class, and preflights rule
expansion before execution. It has not yet produced a passing suite result.

Historical limitation remains explicit: PER-25/PJ/2018 commenced on 2019-01-01
per the official DGT announcement. Some inherited treaty rule start dates are
earlier. The pre-PMK112 candidate branches do not establish procedure validity
before 2019. Do not claim historical readiness from the 2026 regression.
Official source: https://www.pajak.go.id/kurangi-beban-administrasi-wajib-pajak-djp-permudah-penerapan-p3b

These inputs require final integration, catalog migration updates, source
admission and broader business acceptance before production delivery.
