# STATUS

Written by `rule/tools/build.py` at every build; do not edit.

| What | Count |
|---|---|
| Rules | 451 |
| Variables / predicates | 94 / 11 |
| Interpretation decisions (rows) | 203 |
| Golden tests (passed / total) | 1362 / 1362 |
| Errors | 0 |
| Coverage gaps (jurisdiction, subject, slot) | 30 |
| Conditioned rules without a T, F and U test | 0 |

## Rules by jurisdiction

| Jurisdiction | Rules |
|---|---|
| cn | 71 |
| hk | 16 |
| sg | 22 |
| id | 41 |
| vn | 46 |
| my | 43 |
| th | 44 |
| ae | 14 |
| jp | 72 |
| kr | 51 |
| in | 31 |

## Errors

None.

## Golden tests

All passed.

## Coverage

Cells jurisdiction | subject | slot with neither a rule nor an absence record in database/decision.csv:

- id|company|penalty
- id|company|restructure
- id|individual|penalty
- id|individual|restructure
- id|individual|exit
- vn|company|penalty
- vn|company|restructure
- vn|individual|penalty
- vn|individual|restructure
- vn|individual|exit
- my|company|penalty
- my|company|restructure
- my|individual|penalty
- my|individual|restructure
- my|individual|exit
- ae|company|penalty
- ae|company|restructure
- ae|individual|penalty
- ae|individual|restructure
- ae|individual|exit
- kr|company|penalty
- kr|company|restructure
- kr|individual|penalty
- kr|individual|restructure
- kr|individual|exit
- in|company|penalty
- in|company|restructure
- in|individual|penalty
- in|individual|restructure
- in|individual|exit

## Conditioned rules without a T, F and U test

None.

## sqlite

`rule.sqlite`: tables rule, variable, predicate, decision, rule_test; on rule the generated columns requires and predicates, and the list columns cite_ids, decision_ids, overrides, as JSON arrays (`SELECT rule_id FROM rule, json_each(rule.requires) WHERE json_each.value = 'holding_pct'`).
