# Rule Layer Specification (Minimal Set)

English copy of `rule/规则层规范.md`; when the two differ the Chinese version prevails.

2026-10-31 (third edition, replacing the 2026-10-29 edition: the functional positioning changes to providing AI agents with logical and computational assistance; tables, syntax, evaluation semantics and build are unchanged). The rule layer lives in `rule/`. It reads the jurisdiction, doc, clause, param, treaty and decision produced by the library (`database/`, see `database/数据库规范.md`), maintains five tables of its own — rule, variable, predicate, decision, rule_test — and on that basis provides a set of read-only query and computation functions (section 5). The library does not depend on the rule layer; the rule layer does not depend on any caller. The reference implementation is in `rule/tools/`; the old engine (`tax_graph/`, `official/`) is not used and not migrated.

**Language**: this specification is written in Chinese for human readers; the English copy is `rule/rule_layer_spec.en.md`; when the two differ the Chinese version prevails, and when the Chinese version is changed the English copy is updated in step. Everything the AI writes into files in its own words is in English — code, comments, tool descriptions, prompts (what the system actually submits is the passage in the English copy), drafts, checklists, handoffs, bug reports, logs, product fields; originals, clauses, quotations and the client's own words stay in the original language and are not translated. The only exception is text shown to the client (replies to the client, briefings), which follows the client's language. The overall verdict of a checklist uses English markers: handoff package `RUNNABLE` / `REVISE`, report `DELIVERABLE` / `REVISE` (the service also accepts the original Chinese markers).

## 0. Functional positioning and scope

The rule layer provides AI agents with programmatic assistance in logic and computation, helping to mitigate hallucination and context limits: it turns the law in the library into queryable, computable, traceable data and functions. It only provides "shovels"; it makes no judgments and does not prescribe how it is used. It guarantees one thing only: **the same input always yields the same output, and every output can be traced back to clauses and quotations**.

| # | Function | Use | Where |
|---|---|---|---|
| 1 | Structured supply of the law: rules, variables, judgment points and readings as data, with clauses, parameters and quotations available on demand | No need to load a whole statute into the context; figures do not rely on memory | §2, §5 |
| 2 | Locate: given jurisdiction, subject, slot, flow direction and date, return the rules in force on that day | Read only the few relevant rules | §5 |
| 3 | Evaluation: three-valued evaluation, stacking within a cell, intervals and pending groups; assumptions in the input are carried out explicitly | Compute correctly, state clearly what is missing | §4 |
| 4 | Reverse and differential: what is needed for a given effect, which effects are attainable on this hop, how the result changes when one fact changes, what the library lacks | Know where to look, what to ask, what to check outside the library | §5 |
| 5 | Trace: every output item back to rules, parameter quotations, clauses and readings | Statements are verifiable | §5, §7 |
| 6 | Self-check: build checks, coverage, golden tests | The "shovel" itself is not broken | §7 |

Not part of the rule layer: answering judgment points; verifying the source of facts; generating, forking and ranking candidate structures; report wording; the interface; full-text and vector retrieval. Removed as unnecessary (carried over from the previous edition): precision grades, fallback / priority, fingerprint tracking, evidence channels and mount columns, `credit:<p>`.

## 1. Process

```text
database/ (jurisdiction, doc, clause, param, treaty, decision)
   ▼
Write rules (data, not code): five csv files — rule, variable, predicate, decision, rule_test — with only the author-filled columns
   ▼
Build: python rule/tools/build.py
   parse condition; validate references, effects against slots, types, effective periods (section 7)
   run rule_test with the reference evaluator; the build succeeds only if all pass
   coverage check: every cell of jurisdiction × subject × slot has a rule, or the library has an absence record for that cell
   write rule.sqlite (five tables + generated columns requires, predicates), STATUS.md
   ▼
Read-only function set (section 5): locate, evaluation, reverse and differential, trace, field dictionary
```

## 2. Tables

The csv files contain only the author-filled columns; build-generated columns go only into `rule.sqlite`. Text written by the author is in English; quotations stay in the original.

### 2.1 rule

| Column | Meaning |
|---|---|
| rule_id | `<jurisdiction or jurisdiction pair>.<slot>.<name>`, e.g. `cn-hk.outbound_wht.cap_5`; treaty rules begin with `<source>-<counterparty>` |
| slot_key | `jurisdiction\|subject\|slot\|flow`. Jurisdiction = whose law the rule belongs to; subject = company / individual / all, meaning the payee (for the residence slot, the person being determined); flow = the counterparty jurisdiction code, `*` for unrestricted. For treaty rules the jurisdiction is the source (`cn`) and the flow is the counterparty (`hk`); the parameters of one treaty are shared by both directions (parameters with scope `hk-jp` serve both `jp|…|hk` and `hk|…|jp`; the latter has no rules because Hong Kong does not tax) |
| condition | Infix expression (section 3); write `true` for unconditional |
| effect | Effect, restricted per slot (section 2.2) |
| overrides | Filled only for `deny`: the ids of the suppressed rules (semicolon-separated), or `cap:*`, `exempt:*`, `share:*`, `exclude:*`, `credit:*` (all effects of one kind in the same jurisdiction and the same flow; when the deny's flow is `*` it suppresses all flows of that jurisdiction) |
| procedure | Procedural sources, semicolon-separated; each item is: the doc_id of a certificate / filing document (library categories 7 and 8), the cite_id of a specific clause in that document (the clause holding the retained materials, filing method or deadline), or the id of a library category-7 absence record ("the jurisdiction has no filing procedure" is also a source); mandatory for `cap` rules that depend on a predicate (treaty benefits), optional otherwise. Queries return the original sentence per item; no dates are computed and no steps are ordered |
| cite_ids | Clause cite_ids, semicolon-separated, at least one from law / regulation / treaty |
| decision_ids | Ids of this layer's decisions, semicolon-separated; filled only when a reading is used |
| effective_from, effective_to | Dates of the rule itself (treaty application start date, MLI effective date for withholding at source); blank means following the referenced parameters. Both are checked: the rule participates only if the rule date is within the period and all referenced parameters are in force on the evaluation date |
| note | Explanation, English |

Generated columns (sqlite): requires (array of variable names), predicates (array of predicate keys).

### 2.2 Effects and slots

One rule, one effect; with a parameter write `<effect>:<param_id>`; the parameter's slot must equal the rule's slot and its unit must be numeric.

| Slot | Effect | Meaning | Direction |
|---|---|---|---|
| residence | `resident` | If the condition holds, the subject is a resident of this jurisdiction | unfavourable |
| outbound_wht, final | `rate:<p>` | Tax rate | unfavourable; a conditional rate below the cell's unconditional rate is a reduced rate and is treated as favourable |
| outbound_wht, final | `surtax:<p>` | Surtax, p% of the tax (Japan's special reconstruction income tax 2.1) | unfavourable |
| outbound_wht | `cap:<p>` | Treaty ceiling, the lesser of it and the rate (including surtax); when several hold, take the minimum | favourable |
| outbound_wht, inbound, final | `exempt` | Exemption, set to zero | favourable |
| inbound | `taxable` | Foreign dividends are included in the resident's income | unfavourable |
| inbound, final | `share:<p>` | Inclusion at the parameter's proportion (parameter = inclusion proportion, %; Japan foreign dividends 5, Thailand domestic dividends 50) | favourable |
| inbound, final | `exclude:<p>` | Exclusion at the parameter's proportion (parameter = excluded proportion, %; Japan non-controlling-purpose shares 20). Used when the statute states the excluded proportion: the rule layer does not compute 100 − p | favourable |
| inbound | `credit_underlying` | Indirect credit: the credit also covers the tax borne by the paying company's profits (Mainland art. 24, Hong Kong s50AAAB); thresholds and tiers sit in the condition; whether the dividend is first grossed up to the pre-tax income is the library parameter `<jur>.inbound.underlying_gross_up` | favourable |
| inbound, restructure | `credit` | Foreign tax credit; thresholds and tiers are written in the condition; in the restructure cell it means the residence jurisdiction grants an ordinary credit for the foreign transfer tax | favourable |
| final, restructure | `schedule:<p>` | Progressive schedule (for individuals, and company bands such as the HK two tiers and the JP small-company rate); p is the parameter of the schedule's first bracket rate (`<schedule name>_bracket_1_rate`; one schedule per jurisdiction per subject type, placed in the final slot, and restructure rules may reference it); the evaluator fetches the whole schedule by its name. The cell's rate = the effective rate of this dividend (restructure cell: this transfer gain) stacked on top of the payee's other taxable income, reading the variables `other_taxable_income` and `amount_payee_ccy` (both in the payee jurisdiction's currency; conversion is the caller's job); if either is missing, the floor takes the lowest bracket and the ceiling the highest, with pending MISSING. It is an alternative to `rate` for the same value: a conditional `rate` (e.g. listed dividends 15%, Thailand's 10% election) takes precedence when it holds | unfavourable |
| cfc | `include` | If the condition holds, undistributed profits are attributed to the shareholder | unfavourable |
| cfc | `rate:<p>`, `surtax:<p>`, `schedule:<p>`, `credit`, `credit_underlying` | The shareholder's rate on the included income, the surtax, the progressive table (referring to the table of the final slot) and the foreign tax credit: `credit` covers only the taxes the controlled company bore itself (Japan SMA 66-7), `credit_underlying` also those of lower tiers (Mainland art. 24); taken only on the side where include holds | rate unfavourable, credit favourable |
| exit | `rate:<p>`, `surtax:<p>` | The income tax rate on the assets an individual is deemed to transfer when leaving; the base is computed by the caller according to the parameter `gain_base` (text). Individuals only: relocating companies is out of scope (`goals.en.md` §6) | unfavourable |
| anti_abuse | `deny` | If the condition holds, the benefits listed in `overrides` are suppressed | unfavourable |
| restructure | `rate:<p>`, `exempt`, `cap:<p>`, `credit` | Income tax on a share transfer: the rate on the transfer gain (transfer proceeds − cost); `exempt` is used for treaty Article 13 residence-only taxation and for safe harbours; stacking as in outbound_wht. In the cell's facts, `target_in_jurisdiction` (the transferred company is in this jurisdiction) and `transferor_resident` (the transferor is a resident of this jurisdiction) are carried in by `eval_transfer`: source-jurisdiction rule conditions write `target_in_jurisdiction = true and transferor_resident = false`, residence-jurisdiction rules write `transferor_resident = true` | unfavourable / favourable |
| restructure | `stamp:<p>` | Stamp duty on the share transfer, p% of the consideration (or net assets, whichever is higher); the stamp rules taken are summed (where both parties pay, write two rules or one combined rule, see note); it does not take part in the rate stacking and is listed separately as `stamp` in the cell value | unfavourable |
| penalty | `interest:<p>` | Late-payment surcharge / interest / additional charge on overdue tax, p% of the tax; the period is determined by the parameter name: `_per_day`, `_per_month`, `_per_year`, `_initial` or `_once` (one-off). The interest rules taken are summed (Singapore 5% once + 1% per month, Hong Kong 5% + a further 10% after six months); alternative brackets (Japan's lower rate for the first two months, Thailand's 0.75% after deferral) are not written as rules but left as reference parameters; the rule takes the ceiling of the whole period at the higher rate | unfavourable |
| penalty | `interest_cap:<p>` | Ceiling on total interest, p% of the tax | unfavourable |
| penalty | `fine:<p>`, `fine_min:<p>`, `fine_max:<p>` | Fine, p% of the tax (fixed, or the floor / ceiling of a range). The cell value takes the envelope of all rules taken: fine_min = the minimum, fine_max = the maximum. A conditional fine rule below the cell's unconditional fine is treated as favourable (Japan voluntary payment 5% vs 10%), above it as unfavourable (multiples for evasion, concealment, negligence, failure to file); when the condition is unanswered, the floor is the ordinary case and the ceiling the heavier case | unfavourable; favourable when below the unconditional one |

Direction decides which side a pending rule goes to (section 4). The residence rules do not produce a tax amount but a fact (`payer_resident`, `payee_resident`), read by the conditions of other cells; the cfc cell says whether income is included and, when it is, carries the shareholder's rate and the credit flag, from which the caller computes the tax on the inclusion. "The law has no such provision" is not written as a rule: the absence record in the library's `decision` already cites the charging-scope clause, and the coverage check accepts it.

Each cell's value: outbound_wht = the rate on the gross dividend; inbound = the inclusion proportion (0 if no taxable rule is taken) and the credit flag; final = rate × the inclusion proportion after this cell's share / exclude / exempt; residence = yes / no; cfc = yes / no, with `rate` (the shareholder's rate when inclusion holds, surtax included) and `credit`; exit = the rate on the gain of the deemed transfer (surtax included); anti_abuse = whether suppressed and the suppression list; restructure = the rate on the transfer gain (after stacking rate / exempt) plus `stamp` (the summed stamp duty rate); the tax bases are computed by the caller according to the parameters `gain_base` / `stamp_base` (text) — transfer gain = consideration − cost; the consideration defaults to the share of net assets (the appraised value when there is an appraisal report); these two items are inputs, not rules; penalty = `{interest: [{param, pct, period}], interest_cap, fine_min, fine_max}`, all rules taken are summed (Singapore 5% once + 1% per month); with only `fine_max`, `fine_min` = 0. The penalty cell writes only the ordinary case (benefit denied, tax recovered); the heavier multiples for evasion, concealment etc. stay in the library as reference parameters (`reference_params`). The penalty cell is not among the nine cells of `cells_for_flow`; the caller evaluates it separately as needed (`S|all|penalty|*`, `R|all|penalty|*`). When no rate rule is taken, the value of outbound_wht and final is empty (`-`), meaning the library has no rate parameter for this situation (e.g. the progressive rate for a Japanese individual receiving unlisted dividends).

### 2.3 variable

| Column | Meaning |
|---|---|
| name | lower snake case, unique across the library |
| kind | `client_fact` (a client fact; missing → pending MISSING), `structure` (a structural condition: in planning it is decided by the candidate structure, undecided → pending PLAN; when recording a transaction that has already happened it takes its value from the described structure — for bool, absence from the description means false; other types that are missing are still MISSING), `derived` (computed from other variables or other cells, never asked of a person; when inputs are missing the pending item points to the input variable) |
| type | bool / number / date / text / enum |
| allowed_values | enum values, semicolon-separated |
| inputs | Filled only for derived: the variables it is computed from, semicolon-separated; when at evaluation it has no value and the inputs are also missing, needs points to the missing inputs |
| question | The question to ask the client, English |
| meaning | Relative to the payment being evaluated, what this variable denotes and where it usually comes from (e.g. "ratio of the payer's shares held by the payee; shareholder register"); for derived, write the algorithm |

The derived variables at present: `payer_resident`, `payee_resident` (carried in by the flow evaluator from the result of the residence cell: T / F; if the cell is pending, its needs are carried in; if the jurisdiction has no residence rule, MISSING pointing to the variable itself), and `payer_low_tax` (computed from parameters by the extraction / flow according to the algorithm written in meaning). `parent_treaty_not_worse` is computed by the flow evaluator in eval_flow and is not asked: take the dividend parameters of two treaty pairs, source with the payee's jurisdiction and source with parent_jur; a holding that reaches holding_pct_min takes dividend_rate_reduced, otherwise dividend_rate_other or dividend_rate; the parent's holding counts as holding_pct × parent_holding_pct / 100; true when the parent's rate is not higher than the payee's, false when the parent's pair has no dividend parameter or the parent is in the source jurisdiction, pending with needs on holding_pct when the holding is missing and decides the rate; a value already in the facts is not overwritten (added 2026-11-03; before that no program computed it). The field dictionary for extraction and questioning = the core fields (parties, holding, payment) ∪ the variables with kind client_fact; no separate field table is maintained. `mode` is not a variable but the evaluation mode (record / plan).

### 2.4 predicate

| Column | Meaning |
|---|---|
| key | e.g. `bo`, `ppt`, `gaar`, `substance`; one key per determination question, not split by jurisdiction. An answer may be given for one deciding jurisdiction: `key@jur` (such as `gaar@hk`) applies only to that jurisdiction's cells and is looked up first, then the key without a jurisdiction; so a question that two jurisdictions decide separately on the same hop (Mainland and Hong Kong anti-avoidance) can take different values |
| question | How it is asked, English |
| factors_cite | The clauses holding the officially listed factors to consider, semicolon-separated, at least one |
| favourable | yes or no: the answer that favours the client. The optimization layer orders its branches by it, the orchestrator uses it to decide whether a client's answer closes a fork |
| factor_vars | Fact variables relevant to the determination, semicolon-separated, may be empty (e.g. for bo, `passes_on_within_12m`, `substantive_business`). They do not enter conditions — the statute says they are factors to be weighed, not determining conditions — but `judgment_points` lays them out together with their current values; a variable appearing only here counts as read |

Answers are fixed to yes / no / unknown, with reasons attached; who answers and how is outside this specification (section 6). Determinations that can be written as facts are not written as predicates: the beneficial owner safe harbours (listed, government, resident individual, held 100% by such persons, 100%-held resident parent) are client_fact variables and `or` conditions; only the remaining holistic judgment is `pred(bo)`. A tax authority's "认为 / satisfied" (considers / is satisfied) is not a predicate: write the rule by the objective conditions listed in the clause and write a decision explaining the reading (e.g. D-hk-1, D-sg-1). Objective conditions such as the beneficial owner safe harbours (STA Announcement 2018 No. 9, Articles 3 and 4) should likewise be written as conditional rules rather than folded into the predicate — the existing rules have not done so, see §10.

### 2.5 decision (interpretive readings)

| Column | Meaning |
|---|---|
| id | `D-<jurisdiction or jurisdiction pair>-<n>`; one row per source; the same id may have several rows |
| statement | The content of the reading and its reasons, English; where a clause admits two readings, state which one is taken and what the other would mean; for inferred dates, state the inference; state unmodelled branches (e.g. partial aggregation under Japan's CFC) |
| cite_id, quote | The supporting clause and its verbatim quotation |

Rules reference readings via `decision_ids`; a reading does not choose for anyone, it only records what someone chose.

### 2.6 rule_test

| Column | Meaning |
|---|---|
| test_id | `<rule_id>.<n>` |
| slot_key, date | The cell and date evaluated; rules for the `all` subject are tested with a company or individual cell |
| facts | `name=value;name=value`, variables per the variable table; `mode=plan` may be added (default record) |
| answers | `predicate=yes/no/unknown;…`, may be empty |
| expect | `<effect> <value> <status>`: effect = the effect word of the rule under test; value = the value on the cell's ceiling side (unfavourable side), a number, `yes` / `no` or `-`; status = the rule-under-test condition's `T`, `F`, `U:<needs keys, comma-separated>`, or `-` meaning the rule does not apply on that date. E.g. `cap 5 T`, `cap 10 U:bo`, `share 100 F` (the condition fails, falling back to taxable's 100), `rate 20 -` |
| source | The cite_id of an official worked example, or `authored` |

Every rule that reads a variable or predicate has at least three tests: holds, fails, pending. Official worked examples take priority.

## 3. Writing conditions

There is only one notation, infix expressions; stored as text in csv and sqlite and parsed into a tree when the program reads them.

| Component | Notation |
|---|---|
| Variable | `holding_pct` |
| Parameter | `$cn-hk.outbound_wht.holding_pct_min` |
| Constant | `25`, `'company'`, `'2026-01-01'`, `true` (only on the right side of a comparison) |
| Comparison | `left >= right`, operators `=`, `!=`, `<`, `<=`, `>`, `>=` |
| Membership | `left in ['a', 'b']` |
| List | `listed(cn.cfc.cfc_whitelist, payer_jur)`: the parameter `cn.cfc.cfc_whitelist_<value of payer_jur>` exists, is within its period and is yes (the library's list convention: one bool row per country) |
| Predicate | `pred(bo)` |
| And, or, not | `and`, `or`, `not`, parentheses for grouping |

Four rules:

1. Both sides of a comparison or `in` may only be variables, parameters or constants; no arithmetic; quantities that need computing become `derived` variables.
2. Precedence `not` > `and` > `or`; parameters begin with `$`, so the hyphen in `cn-hk` is unambiguous.
3. Strings and dates use single quotes, dates `'YYYY-MM-DD'`; the build checks that both sides have consistent types according to variable.type and param.unit (bool against bool, numeric against numeric, text / enum / date interchangeable; an enum constant must be in allowed_values; `<`, `<=`, `>`, `>=` only for numbers and dates).
4. Variables are in `variable`, parameters in the library's `param`, predicates in `predicate`; errors report the `rule_id`.

## 4. Evaluation semantics

The rule layer defines the meaning; the evaluator merely executes it, and every implementation must pass the same `rule_test` set.

**Values**: `T`, `F`, `U`. `U` carries `needs`; a need is (kind, key):

| kind | Source | key |
|---|---|---|
| MISSING | A client_fact variable has no value, or has a value without a source | The variable name (for a derived variable missing inputs, the input variable; if the inputs are all present but the value was not computed, or the cell it depends on has no rules in that jurisdiction, the derived variable itself) |
| PLAN | A structure variable is decided by the candidate structure in plan mode and is not yet decided | The variable name |
| DISCRETION | A predicate is unanswered or answered `unknown` | The predicate key |

**Connectives**: Kleene three-valued logic. `AND`: any F → F; otherwise any U → U with the union of needs; otherwise T. `OR` symmetrically. `NOT` flips T/F, U unchanged. Known values short-circuit pending ones: `AND(F, U) = F`; when the holding falls short, the beneficial owner is not asked.

**Leaves**: a comparison with a missing side → U; a parameter not in force on the evaluation date → the rule does not apply (the whole rule is skipped, not U); predicate yes → T, no → F, otherwise U(DISCRETION); `listed` with a missing variable → U, otherwise T / F by whether the parameter exists.

**Stacking within one cell** (given slot_key, date, facts, answers). Candidates = the rules of that cell whose subject matches exactly or is `all` and whose flow matches exactly or is `*`, in force on the date. Evaluate each `cond` and decide by direction whether to take it: T taken, F not taken, U taken on the floor side by the favourable direction and on the ceiling side by the unfavourable direction (a favourable effect is taken on the floor and not on the ceiling; an unfavourable effect the reverse). The rules taken are stacked in fixed stages:

```text
rate → surtax (×(1 + p/100)) → cap (take the minimum) → share (× p/100), exclude (× (100 − p)/100) → exempt (set to zero) → credit → deny
```

Within a stage the order is interchangeable; the exception is several rules for the same value in the same cell (`rate` with `schedule`, several `share`, several `exclude`): a conditional rule whose condition is T beats the `true` rule; two conditional rules both T is a Defect (the rules are mis-written, e.g. a mutually exclusive enum not written properly); a conditional rule whose condition is U is an alternative, not a conflict, and both sides participate: the floor takes the alternative with the lowest tax, the ceiling the one with the highest tax, and the `true` rule is also one of the alternatives (the conditional ones might all fail). When there is no `true` rule, "no rule applies" is also an alternative: for rate its value is unknown (floor empty); for share / exclude it is full inclusion (the ceiling takes none). When the enum is unknown, Japan's domestic dividend 50% / 20% rules both pending, and Japan's individual listed 15% and the progressive schedule both pending, are such cases. When `deny` is taken, the effects it `overrides` do not apply.

**Cross-cell order** is fixed: residence (payer in the source jurisdiction, payee in the residence jurisdiction, payer in the residence jurisdiction) → outbound_wht (source) → anti_abuse (source) → inbound (residence) → anti_abuse (residence) → final → cfc. Treaty rule conditions all contain `payee_resident = true`: when the payee's residence determination in the counterparty jurisdiction is F, the whole rule is F, neither participating nor entering a pending group; when U, it is pending carrying the residence cell's needs. `deny` acts across cells: the source anti_abuse suppresses outbound_wht; the residence anti_abuse suppresses inbound and final.

**Intervals and pending groups**: the result is `[floor, ceiling]`. Every rule whose cond is U records a group `(rule_id, needs)`; a group is meaningful only as a whole. Only groups that "can still change the result" are recorded: flip that rule's decision (flip only that one, leaving the other pending rules unchanged) and recompute; if neither side changes, do not record it (when a 10% ceiling equals the statutory rate, bo is not asked for it; a treaty whose ceiling exceeds the statutory rate, and its PPT, never enter a pending group). The counterfactual for a `deny` rule is computed at the flow level: flip it and see whether the suppressed cell changes; if it does, record it in the anti_abuse cell and also in the affected cell (that cell's status becomes U and the needs are merged in). The cost of a group is computed outside the rule layer.

**This layer fills in no values**: MISSING takes no default; the rule layer gives no variable a default; a structure variable in record mode takes its value from the described structure, which is the definition of the input, not a fill-in. To assume, pass the assumption in as input and declare it as an assumption (`assume` in §5); the output item carries the list of assumptions out unchanged and gives the result with the assumptions removed.

**Output items**: each cell produces one item `(jur, subject, slot, counterparty, rules_applied{floor, ceiling}, floor, ceiling, status, needs, pending, cite_ids, decision_ids, assumptions)`; status ∈ {T, U, absent}, absent = the cell has no rules; rules_applied lists on each side only the rules that determine that side's value (alternatives for the same value that were not selected are not listed, so cite_ids, decision_ids and value_kind all follow only the rules that actually take effect); a cell with a schedule rule additionally carries schedule_inputs (the two inputs it read) so that the trace can verify the recomputation; assumptions = the inputs this item depends on that were declared as assumptions. Numbers come only from parameters; this is the start of the trace chain.

## 5. Function set: locate, evaluation, reverse, sources

All functions are read-only, without side effects, same input same output. Every output carries cite_ids / param_id; there are no bare numbers.

**Locate and supply**

- `cells_for_flow(S, R, subject)`: the nine cells to look up for one dividend (payer jurisdiction S, payee jurisdiction R, payee subject): `S|company|residence|*` (payer), `R|subject|residence|*` (payee), `R|company|residence|*` (whether the payer is also an R resident), `S|subject|outbound_wht|R` and `|*`, `S|subject|anti_abuse|R` and `|*`, `R|subject|inbound|S` and `|*`, `R|subject|anti_abuse|S` and `|*`, `R|subject|final|*`, `R|subject|cfc|*`.
- `cell(slot_key, date?)`, `rule(rule_id)`, `by_variable(name)`, `by_predicate(key)`: the rule rows + the text of the cited clauses + the parameter rows in the effect and condition (value, unit, quotation, effective period) + the decision rows + the procedure documents; anything not found is marked NOT FOUND (`rule/tools/rule_tool.py`).
- `variables()`, `predicates()`: the field dictionary (name, kind, type, question, meaning; for predicates the question, the full text of factors_cite, factor_vars) (`rule/tools/query.py`).
- `coverage()`: per cell, has rules / has an absence record / empty (STATUS).
- `reference_params(slot_key)`: the parameters of the cell's jurisdiction (and jurisdiction pairs), same slot, not referenced by any rule — filing deadlines, certificate years, thresholds of determination factors — returned as they are with their quotations; cited only, not computed (`rule_tool.py --slot` returns them as well).

**Evaluation**

- `eval_transfer(target_jur, home_jur, subject, date, facts, answers, mode, assume?)`: the four cells of one share transfer — the transferred company in target_jur, the transferor (subject) in home_jur: the transferor's residence cells in both jurisdictions, the source cell `target|subject|restructure|home`, the residence cell `home|subject|restructure|target`; facts are grouped into the payment (transfer_gain, transferred_pct, consideration), `target.*` (the transferred company: listed, property_rich_ratio), `transferor.*` (incorporated_in, managed_in, holding_pct, holding_months). The derived variables `transferor_resident`, `target_in_jurisdiction`, `payee_resident` are carried in by it (`eval.py --transfer`).
- `eval_cell(slot_key, date, facts, answers, mode, assume?)`, `eval_flow(S, R, subject, date, facts, answers, mode, assume?)`: the semantics of section 4; `facts` are grouped into the payment, `payer.*` and `payee.*`; `assume` is the set of keys in facts / answers declared as assumptions; the output item lists those actually used in assumptions and attaches "the interval and status with the assumptions removed" (`rule/tools/eval.py --assume`). The output item also carries `value_kind`: statutory (on the ceiling side only rules that read no fact and no predicate are taken) / conditional / none.
- `judgment_points(flow or cell, date, facts, answers)`: the predicates that block the result under the current input — key, question, factor clauses, the current values of factor_vars, the rules they block, and for answering yes / no the respective interval and remaining open items. It is just another arrangement of the pending groups (`query.py judgment_points`).

**Reverse and differential** (`rule/tools/query.py`)

- `requirements(slot_key[, effect] | rule_id)`: the expanded condition tree of an effect in a cell (or of one rule) — every leaf carries the variable's question, the parameter's value and quotation, the predicate's question and factors — plus the original sentence of each procedure item and the cell's reference parameters.
- `options(S, R, subject, date)`: the favourable rules of every cell on this hop and their requirements.
- `what_if(flow or cell, baseline input, changes)`: change one or several facts / answers and see how each cell's interval, status and needs change.
- `gap(S, R, subject)`: for every cell of this flow, how many rules there are, which effects appear, which effects the slot allows but do not appear, which variables and predicates are read; for cells without rules, distinguish "the library has an absence record" from "not collected"; flows whose treaty text is missing are flagged. An effect that does not appear may be absent in the law or simply unmodelled; the library records absences only per slot, and `gap` does not judge on its behalf.
- `version()`: rule layer counts, the rule.csv hash, the library's file count / parameter count / hash, generation time.

**Sources**

- Rules do not store text; `cite_ids` point to the library's `clause`, fetched on demand. `explain` = the output of `cell` / `rule`.
- `trace(items)`: the trace of section 7, PASS / FAIL per item (`rule/tools/trace.py`).
- After the library is re-uploaded, rerun the build: broken references, mismatched quotations and failing golden tests are all reported.

## 6. Judgment points and readings

- **Judgment points** (predicate) are an interface the rule layer exposes, not questions it answers: every key is fixed to three values yes / no / unknown; `unknown` and unanswered are the same in evaluation (U); every key carries `factors_cite`, so the official factors to consider are at hand. Who answers, on what basis, and where the answer is recorded are outside this specification.
- **Readings** (decision) are the readings the author took when writing the rules: where a clause admits two readings, a date must be inferred, or a branch is not modelled, write one and have the rule reference it; evaluation follows the reading. A reading only records what the author chose. Scope rulings (a class of income not modelled) are not written as rules.
- **Guidance and web pages** may be cited, but cite_ids must contain at least one law / regulation / treaty clause.

## 7. Completeness and validation

Any of the following at build time is an error:

1. The condition cannot be parsed, or a referenced variable is not in `variable`, a parameter not in the library's `param`, a predicate not in `predicate`, a reading not in `decision`; the two sides of a comparison have inconsistent types; the prefix of `listed` has no parameter at all in `param`;
2. The effect is not among those allowed for the slot; the effect parameter is not in `param`, its slot does not match the rule's slot, or it is not numeric; `cite_ids` is empty, not in `clause`, or none is from law / regulation / treaty; `procedure` is neither a `doc` nor a category-7 absence record;
3. `slot_key` does not have four segments, or the jurisdiction, subject, slot or flow value is invalid; the flow is a jurisdiction but the library's `treaty` has no row with text for that pair; a treaty rule's id does not begin with the jurisdiction pair;
4. A `cap` rule that depends on a predicate has no `procedure`; a `deny` has no `overrides`, or a non-`deny` has one; the rules pointed to by `overrides` do not exist, are not in the same jurisdiction, or have incompatible flows;
5. The rule dates have no intersection with the effective period of any referenced parameter; a date is not in YYYY-MM-DD format;
6. A reading's quotation is not in the cited clause; a variable name is invalid or duplicated, kind / type invalid, question or meaning empty, derived without inputs or with inputs that are not variables; a duplicate predicate key, factors_cite empty or not in `clause`; a variable read by no rule; a csv has columns outside the specification;
7. Any `rule_test` fails, or a rule reading a variable / predicate lacks the three tests T, F, U; a fact in a test is not a variable, an answer is not a predicate or not one of the three values.

**Coverage**: jurisdiction × {company, individual} (per the in_scope column of jurisdiction) × 6 slots; every cell either has rules or has an absence record for that cell (subject + slot) in the library's `decision`. Empty cells are listed in STATUS and are not errors.

**Runtime invariants** (the evaluator must check them; a violation is a Defect): floor ≤ ceiling; an item with status T has no needs; an item that took rules has at least one cite; one item per cell per flow. Recomputation from parameters equalling the output value is guaranteed by the determinism of the stacking function.

**Trace**: `rule/tools/trace.py` walks, for every output item: item → rule_id in the rule table → effect and condition parameters in `param`, `param.quote` verbatim in `clause.text`, parameters in force on the evaluation date → the `cite_ids` clauses exist and their documents are in force on the evaluation date → the quotations of decision_ids verbatim in the clauses → recomputation from the rules and parameters taken equals the output value; any broken link is FAIL. The input is the output file of `eval.py --json`, or `--slot` / `--flow` given directly to compute and check on the spot.

## 8. Interfaces

| Form | Content |
|---|---|
| CLI | `rule/tools/eval.py`, `trace.py`, `rule_tool.py`, `query.py`, `build.py` (section 10) |
| MCP | `rule/tools/mcp_server.py` (`规则层MCP规范.md`) |
| Products | `rule.sqlite` (five tables + generated columns), `STATUS.md` |

How facts are obtained, how predicates are answered and how results are used are all outside this specification. The rule layer's only requirement on inputs is validity: an unknown variable name, an invalid slot_key, an answer that is not one of the three values — these are errors, not guesses.

Scope = the library's scope (dividends, 11 jurisdictions, companies and individuals). Extensions do not change the evaluator core: a new slot or effect = a change to this specification's vocabulary + `common.EFFECTS` + one branch in the evaluator's stacking function; a new jurisdiction = a jurisdiction added in the library + rule rows; a new subject = rule rows.

## 8a. MCP service `tax-rule`

See `rule/规则层MCP规范.md` (2026-11-01, minimal set, read-only service wrapping this layer's functions without adding semantics).

## 9. Worked examples

A Mainland company paying dividends to a Hong Kong company (parameters already in the library):

```text
rule_id                     slot_key                    condition                                                                                 effect                                        overrides  procedure
cn.outbound_wht.statutory   cn|company|outbound_wht|*   true                                                                                      rate:cn.outbound_wht.dividend_wht_rate        —          —
cn-hk.outbound_wht.cap_10   cn|all|outbound_wht|hk      payee_resident = true and pred(bo)                                                        cap:cn-hk.outbound_wht.dividend_rate_other    —          cn.sta.2019-35
cn-hk.outbound_wht.cap_5    cn|company|outbound_wht|hk  payee_resident = true and holding_pct >= $cn-hk.outbound_wht.holding_pct_min and pred(bo)  cap:cn-hk.outbound_wht.dividend_rate_reduced  —          cn.sta.2019-35
cn-hk.anti_abuse.ppt        cn|all|anti_abuse|hk        payee_resident = true and $cn-hk.anti_abuse.ppt_applies = true and pred(ppt)              deny                                          cap:*      cn.sta.2019-35
```

When both cap rules are taken, the minimum is taken. bo pending: the floor takes both caps (5%), the ceiling takes neither (10% statutory). The only pending group is `(cap_5, {bo})`: cap_10 equals the statutory rate, flipping it does not change the result, so it is not recorded. ppt pending: the floor does not suppress, the ceiling does; flipping ppt would move the floor from 5 to 10, so `(ppt, {ppt})` is recorded in the anti_abuse cell and merged into the outbound_wht cell. Whether the payee is a Hong Kong resident is first determined by `hk|company|residence|*`; when the derived variable `payee_resident` is F, all three treaty rules are F as a whole.

A Japanese company receiving foreign dividends (`jp|company|inbound|*`): `$jp.inbound.foreign_dividend_taxable = true → taxable`; `holding_pct >= $jp.inbound.exemption_holding_pct_min and holding_months >= $jp.inbound.exemption_holding_months_min → share:jp.inbound.exemption_expense_share` (5% inclusion); `true → credit`. The three coexist: taxable is the base, share multiplies it, credit gives the credit.

A Japanese company receiving domestic dividends (`jp|company|final|*`): `domestic_dividend_class in ['wholly_owned', 'affiliated'] → exempt`, `= 'other' → exclude:…share.other` (50 excluded), `= 'noncontrolling' → exclude:…share.noncontrolling` (20 excluded, i.e. 80 included). When the class is unknown all three are pending; the floor takes exempt's 0, the ceiling takes 23.2 unreduced.

Thailand–Vietnam treaty (`th|all|outbound_wht|vn`): `payee_resident = true and pred(bo) → cap:th-vn.outbound_wht.dividend_rate` (15%), default `rate:th.outbound_wht.dividend_wht_rate` (10%). The ceiling exceeds the statutory rate, so under the counterfactual criterion neither this rule nor its PPT ever enters a pending group.

## 10. Build and delivery

- First `python database/tools/build.py`, then `python rule/tools/build.py [--root rule/] [--db database/]`; exit code 1 on error.
- `python rule/tools/eval.py --slot <slot_key> --date YYYY-MM-DD --facts 'a=1;b=x' --answers 'bo=yes' [--mode record|plan] [--json]`: one cell; `--flow <payer jurisdiction> <payee jurisdiction> <subject>` with `--facts 'payer.incorporated_in=cn;payee.incorporated_in=hk;holding_pct=30'`: the nine cells of one dividend (eight items output; the payer's residence cell in R is used only to compute `payer_resident`).
- `python rule/tools/trace.py --items out.json` (or `--flow` / `--slot` with the same parameters as eval): trace check.
- `python rule/tools/rule_tool.py --slot <slot_key> [--date] | --rule <rule_id> | --variable <name> | --predicate <key> [--brief] [--json]`.
- `python rule/tools/query.py judgment_points | requirements | options | what_if | gap | variables | predicates | version | cells_for_flow …` (same parameters as eval; `what_if` adds `--set 'k=v'`, `--answer-set 'k=v'`; `requirements` uses `--slot [--effect]` or `--rule`).
- The requires of `schedule` rules automatically include `other_taxable_income`, `amount_payee_ccy`; the golden-test expect for the penalty slot writes the rule's own number (`interest 0.05 T`), because the cell value is a dictionary.
- Products: `rule.sqlite` (five tables + requires, predicates; list columns stored as JSON arrays), `STATUS.md` (counts, errors, golden test results, empty coverage cells, rules without tests).
- Code: `tools/common.py`, `tools/build.py`, `tools/eval.py`, `tools/trace.py`, `tools/rule_tool.py`, `tools/query.py`; Python 3.11, standard library only.
- Delivery = the whole `rule/` folder.

**Implementation status (2026-10-31, after revision)**: 134 rules (cn 47, hk 12, sg 10, jp 42, th 23), 41 variables, 9 predicates, 17 readings, 354 golden tests all passing, 0 errors; 72 empty coverage cells = the 6 jurisdictions not yet collected. All functions of section 5 are implemented: `eval.py` (with `assume`, `value_kind`), `trace.py`, `rule_tool.py` (with multi-item procedure and `reference_params`), `query.py` (judgment_points, requirements, options, what_if, gap, variables, predicates, version, cells_for_flow). Gaps fixed this round: the beneficial owner safe harbours (STA Announcement 2018 No. 9, Articles 3, 4 and 5) are written as conditional rules; the beneficial owner condition of every Mainland treaty ceiling rule = factor determination (pred(bo)) or the government / listed company / 100% parent safe harbour (new predicate parent_bo, new variables parent_jur, parent_holding_pct, parent_holding_months, parent_treaty_not_worse, payee_listed_in_partner, payee_is_government); for individual payees it holds automatically under Article 4(3) (every `all` ceiling is split into a company rule and an individual rule); pass-on, substance, employees and premises are carried out as factor_vars; filing deadlines (Mainland 7 days, Thailand 7 days after month end, Japan the 10th of the following month), residence certificate years, and Japan's one-third / 5% / 100 million yen / 50% thresholds went into library parameters (16 in total), referenced directly by rules or returned as reference parameters; the three variables bypassing the library, `sme`, `domestic_dividend_class`, `foreign_related_company`, were deleted. Unmodelled branches are recorded in readings (Article 4(4) and multi-tier intermediate holdings in D-cn-5, Hong Kong's s15M permanent establishment path, Japan's CFC partial aggregation, the progressive rate for individuals' unlisted dividends, etc.). All rule_tests are `authored`.

**2026-10-31 second revision** (further additions in the second half: 161 rules, 48 variables, 404 golden tests): 150 rules, 43 variables, 18 readings, 377 golden tests all passing, 0 errors. Added the penalty slot (14 rules across five jurisdictions, citing Tax Collection and Administration Law Articles 32 and 69, IRO s71 and s82A, ITA s87 and s95, Act on General Rules for National Taxes (国税通則法) Articles 60 and 67, Thai Revenue Code Sections 22 and 27) and the progressive schedule effect `schedule` (the seven brackets of Japan's Income Tax Act (所得税法) Article 89, the seven brackets of the Thai Revenue Code rate table, two rules each; readings D-jp-4 and D-th-3 record the unmodelled dividend credit (配当控除), inhabitant tax, Thailand's THB 150,000 exemption and the s47 bis credit); the two-sided treatment of alternative rules was changed to a unified rule (§4). The library at the same time added document categories 10 (penalties) and 11 (interpretive sources, which may not serve as parameter sources) and the two columns changed_on / superseded_by on param. All 26 jurisdiction pairs' treaty texts in the library were checked: no most-favoured-nation clause; the only limitation-on-benefits clause is hk-kr Article 26 (Korea not yet collected); the other pairs have only the MLI's PPT or a protocol PPT (cn-in Article 27A), all already modelled, so no LOB rules are added.

**2026-10-31 penalty rule refinement**: heavier / lighter cases changed from reference parameters to conditional rules — Mainland tax evasion 50%–500% (`concealment`), Singapore negligence 200% (`negligence`) and wilful 300% (`concealment`), Japan voluntary payment 5% (`voluntary_payment`, favourable) and concealment 35% (`concealment`), Thailand failure to file 200% (`return_filed = false`), Hong Kong a further 10% after six months (`overdue_months`, cumulative); Japan's delinquent tax (延滞税) now uses the annual special rates published by the National Tax Agency (8.8% for 2021, 8.7% for 2022–2025, 9.1% for 2026; Act on Special Measures Concerning Taxation (租税特別措置法) Article 94); the statutory 14.6% is in force only for dates before 2021, and from 2027 there is no interest rule until supplemented. Category 11 interpretive sources took in five documents: the full OECD 2017 Model Commentary (217 paragraphs, coarsely segmented), the STA's interpretation of Announcement 2018 No. 9 (reposted by the Jiangsu bureau), the IRAS treaty guide fourth edition, IRD Advance Ruling Case No. 72, Thai Revenue Department ruling กค 0811/6620; all for citation by readings only.

**2026-10-31 round six (direct citations replacing indirect ones, unmodelled branches added)**: 192 rules, 58 variables, 10 predicates, 21 readings, 501 golden tests all passing, 0 errors. The three conditions of STA Announcement 2015 No. 7 Article 6 are complete: item (2) "再次间接转让时中国所得税负担不会减少" (the Chinese income tax burden would not be reduced on a further indirect transfer) as the structure variable `future_cn_tax_not_reduced` (the optimization layer derives it by comparing the rates of a direct transfer of the Chinese company by the old and the new holder; if it cannot be derived it goes to PLAN), item (3) `consideration_in_shares`, plus item (1)'s 80% relationship; a Thai resident individual's share transfer gain is included under s40(4)(ช) in the s48(1) progressive schedule (new rule `th.restructure.resident.individual`; the effect `schedule` is allowed into the restructure slot; the parameter is still the schedule of the final slot); Japan's 25% / 5% thresholds for non-resident individuals directly cite the Income Tax Act Enforcement Order (所得税法施行令) Article 281, paragraph 6 (new document jp.ita.order, three `.individual` parameters), no longer borrowing Corporation Tax Act Enforcement Order (法人税法施行令) Article 178; Thailand's exchange rate rule directly cites the Ministry of Finance Notification B.E. 2548 Articles 2 and 3 (new document th.mof.fx.2548). A further normal request for the Singapore Stamp Duties Act was refused again (blocked.csv, second row); the 0.2% remains a parameter only.

**2026-10-31 restructure slot**: 191 rules, 56 variables, 10 predicates, 20 readings, 494 golden tests all passing (including the credit effect of the residence credit rules for cn / jp). The new slot `restructure` holds the one-off tax burden of a share transfer: Mainland direct transfer 10%, indirect transfer under STA Announcement 2015 No. 7 (predicate `indirect_transfer_purpose`, the group 80% and public market safe harbours), resident 25%, individual 20%, stamp duty 0.05% for each party; Hong Kong no capital gains tax (absence record), stamp duty 0.1% each for buyer and seller; Singapore no capital gains tax (absence record), s13W safe harbour, s10L foreign asset gains 17%, stamp duty 0.2% as a parameter only (the Stamp Duties Act could not be downloaded); Japan 23.2% under the 25% / 5% thresholds, individual 15%, resident the same rate; Thailand s70 withholding 15%, resident 20%, individual 15%, stamp duty 0.1%; treaty Article 13 exemption for cn-hk, cn-sg, hk-jp, jp-sg, hk-th, sg-th (cn-jp, cn-th, jp-th: the source country may tax). New function `eval_transfer`, new effect `stamp`. Pricing is not a rule: net assets (default) or the appraised value are passed in by the caller; the relevant clauses (STA Announcement 2014 No. 67 Articles 12 and 14, Japan's Circular (通達) 9-1-13) are text parameters for citation.

**2026-11-04 safe harbour item 4(4), penalty on a reported claim**: 200 rules, 60 variables, 10 predicates, 27 readings, 529 golden tests all passing, 0 errors. Item 4(4) of STA 2018 No. 9 (payee held 100%, directly or indirectly, by the government, a listed company or resident individuals of the partner, intermediate holders resident in China or the partner, held for the 12 months of item 5) is added to the company dividend caps of every Mainland treaty, variable `owner_safe_harbour`, derived by the optimization layer from the holding chain (D-cn-5 rewritten). The withholding agent's fine of TCA art. 69 now applies only where the treaty claim was not reported under STA 2019 No. 35 art. 6 (variable `claim_reported`); a reported claim later denied is recovered with tax and late-payment interest only, under art. 16 (D-cn-9).
