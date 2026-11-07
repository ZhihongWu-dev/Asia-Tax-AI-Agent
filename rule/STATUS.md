# STATUS

Written by `rule/tools/build.py` at every build; do not edit.

| What | Count |
|---|---|
| Rules | 201 |
| Variables / predicates | 60 / 10 |
| Interpretation decisions (rows) | 27 |
| Golden tests (passed / total) | 532 / 532 |
| Errors | 0 |
| Coverage gaps (jurisdiction, subject, slot) | 92 |
| Conditioned rules without a T, F and U test | 0 |

## Rules by jurisdiction

| Jurisdiction | Rules |
|---|---|
| cn | 68 |
| hk | 16 |
| sg | 19 |
| id | 0 |
| vn | 0 |
| my | 0 |
| th | 35 |
| ae | 0 |
| jp | 63 |
| kr | 0 |
| in | 0 |

## Errors

None.

## Golden tests

All passed.

## Coverage

Cells jurisdiction | subject | slot with neither a rule nor an absence record in database/decision.csv:

- id|company|outbound_wht
- id|company|inbound
- id|company|final
- id|company|residence
- id|company|cfc
- id|company|anti_abuse
- id|company|penalty
- id|company|restructure
- id|individual|outbound_wht
- id|individual|inbound
- id|individual|final
- id|individual|residence
- id|individual|cfc
- id|individual|anti_abuse
- id|individual|penalty
- id|individual|restructure
- id|individual|exit
- vn|company|inbound
- vn|company|final
- vn|company|residence
- vn|company|anti_abuse
- vn|company|penalty
- vn|company|restructure
- vn|individual|outbound_wht
- vn|individual|inbound
- vn|individual|final
- vn|individual|residence
- vn|individual|penalty
- vn|individual|restructure
- vn|individual|exit
- my|company|outbound_wht
- my|company|inbound
- my|company|final
- my|company|residence
- my|company|anti_abuse
- my|company|penalty
- my|company|restructure
- my|individual|outbound_wht
- my|individual|inbound
- my|individual|final
- my|individual|residence
- my|individual|anti_abuse
- my|individual|penalty
- my|individual|restructure
- my|individual|exit
- ae|company|outbound_wht
- ae|company|inbound
- ae|company|final
- ae|company|residence
- ae|company|anti_abuse
- ae|company|penalty
- ae|company|restructure
- ae|individual|outbound_wht
- ae|individual|inbound
- ae|individual|final
- ae|individual|residence
- ae|individual|anti_abuse
- ae|individual|penalty
- ae|individual|restructure
- ae|individual|exit
- kr|company|outbound_wht
- kr|company|inbound
- kr|company|final
- kr|company|residence
- kr|company|cfc
- kr|company|anti_abuse
- kr|company|penalty
- kr|company|restructure
- kr|individual|outbound_wht
- kr|individual|inbound
- kr|individual|final
- kr|individual|residence
- kr|individual|cfc
- kr|individual|anti_abuse
- kr|individual|penalty
- kr|individual|restructure
- kr|individual|exit
- in|company|outbound_wht
- in|company|inbound
- in|company|final
- in|company|residence
- in|company|anti_abuse
- in|company|penalty
- in|company|restructure
- in|individual|outbound_wht
- in|individual|inbound
- in|individual|final
- in|individual|residence
- in|individual|anti_abuse
- in|individual|penalty
- in|individual|restructure
- in|individual|exit

## Conditioned rules without a T, F and U test

None.

## sqlite

`rule.sqlite`: tables rule, variable, predicate, decision, rule_test; on rule the generated columns requires and predicates, and the list columns cite_ids, decision_ids, overrides, as JSON arrays (`SELECT rule_id FROM rule, json_each(rule.requires) WHERE json_each.value = 'holding_pct'`).
