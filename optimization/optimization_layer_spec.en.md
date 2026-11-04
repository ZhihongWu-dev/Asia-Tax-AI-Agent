# Optimization Layer Specification (Minimal Set)

English copy of `optimization/优化层规范.md`; when the two differ the Chinese version prevails.

2026-10-31 (first version, not implemented; replaces the withdrawn strategy layer). The optimization layer lives in `optimization/`. It reads the functions and fact inputs of the rule layer (`rule/`, see `rule/规则层规范.md`) and produces a set of intermediate products written to disk: graph, label frontier, paths, branches, tax table, ranking, deltas, open items. The rule layer does not depend on the optimization layer; the optimization layer does not depend on any caller.

**Language**: this specification is written in Chinese for human readers; the English copy is `optimization/optimization_layer_spec.en.md`; when the two differ the Chinese version prevails, and when the Chinese version is changed the English copy is updated in step. Everything the AI writes into files in its own words is in English — code, comments, tool descriptions, prompts (what the system actually submits is the passage in the English copy), working notes, checklists, handoffs, bug reports, logs, product fields; originals, statutory provisions, quotations and the client's own words stay in the original language and are not translated. The only exception is text shown to the client (replies to the client, briefings), which follows the client's language. The overall verdict of a checklist uses English markers: handoff package `RUNNABLE` / `REVISE`, report `DELIVERABLE` / `REVISE` (the service also accepts the original Chinese markers).

## 0. Functional positioning and scope

Like the rule layer, the optimization layer gives AI agents programmatic help with logic and computation, to mitigate hallucination and context limits: it works out "under the laws in the library, which routes can this dividend take, what is the tax burden range of each, where do they differ, and what is still missing before it can be settled" and lays it on the table; the agent reads the products, it does not search paths or compute tax itself. It only provides the shovel; it makes no judgments and does not prescribe how it is used. It guarantees exactly one thing: **the same input always yields the same products, and every number in the products can be traced back to a rule-layer output item and from there to the statutory text**.

| # | Function | Use | Where |
|---|---|---|---|
| 1 | Build the graph: jurisdiction × subject as nodes, a one-hop dividend flow as an edge, edge weights computed live by the rule layer, destination set given by the background | Turns "routes" into paths on a graph | §4.1, §4.4 |
| 2 | Shortest path: resource-constrained multi-label label-setting, returning the non-dominated frontier to the destination set | Misses nothing, exact, grows with scale | §4.2–4.3 |
| 3 | Branches: unanswered judgment points on frontier paths are expanded by yes / no, the answers marked as assumptions | Assumptions visible | §4.6 |
| 4 | Objective, ranking, deltas and open items: the tax per payment, ranked by the favourable side (the same order as the saving per payment against the baseline); the one-off cost of restructuring (share-transfer income tax + stamp duty, plus the exit tax when an individual moves) computed separately, payback in payments = one-off cost ÷ saving per payment, ordering only structures of equal tax; all structures compared under the same judgment answers (scenarios), which open items would replace the first structure | Comparable; know what to ask, how much each payment saves, how many payments repay a restructuring | §4.5, §4.7 |
| 5 | Products: all intermediate results written to disk with version and provenance; on demand, evaluate any specified path, the requirements to execute each path, the diff between two runs of products | Agent and report are read-only; "what about going via Japan" gets an answer in the same format | §4.10, §5 |
| 6 | Checks: invariants, exhaustive baseline, golden tests, trace-back | The shovel itself does not break | §7 |

Removed, as unnecessary: metaheuristic search (the problem is exactly solvable); a cost model of the problem; probabilities for predicate answers; multiple objectives (the only objective is tax; the two sides of an interval are not two objectives; the one-off cost is not a second objective: it only orders structures of equal tax, through the payback in payments; the user's decision of 2026-11-04); a holding horizon and N-year totals (the client is not asked how long the structure is kept; the payback is given in payments; the user's decision of 2026-11-04); discounting (the payback is not discounted; the user's decision of 2026-11-04); valuation (the consideration is the input net assets or appraised value, this layer does not value); land-transfer tax and stamp duty other than on share transfers (land-transfer tax concerns only immovable property). Not part of the optimization layer: answering judgment points, verifying the sources of facts, readable text and the report, inventing new structures outside the move vocabulary (the vocabulary is data; anyone may propose a row, and entering the table requires passing validation), the interface.

**Terms** (shared by the layer specs, the products and the report; the `terms` of `brief.json` is the same list):

| Word | Meaning |
|---|---|
| structure | a candidate: one holding path from the paying company to a destination, with the share transfers or moves it needs; c0 is the as-is structure |
| scenario | one set of answers to the judgment points, the same for every structure: all favourable, one point against the client, all against |
| branch | the tax of one structure under one scenario |
| range | floor and ceiling of one branch, from facts not known and progressive tables; not the spread between scenarios |
| worst case | the all-unfavourable scenario |
| judgment point | `key@jur`: the predicate and the jurisdiction that decides it; about = whom it is asked of |
| plan | a word of the report layer: the chosen structure plus what to do, conditions, timing and fallbacks; the optimization layer gives structures only |

## 1. Flowchart

```text
Input
  Facts (payment, payer.*, payee.*, incl. predicate answers and grounds)   destination set T   evaluation date   mode   assumption list
  Move vocabulary optimization/move.csv   jurisdictions whose six dividend slots are all present in the library (rule-layer coverage; the penalty and restructure slots are not conditions for building an edge)
      │
      ▼
[1] Build graph ────── node (jurisdiction, subject, resource state); edge = one hop; edge weight w = −ln(1 − t), t computed live by rule.eval_flow, an interval ── graph.json
      │
      ▼
[2] Label algorithm ── from the source node, each node keeps a non-dominated label set (w_floor, w_ceiling, needs, resources); frontier to T ─── labels.json
      │
      ▼
[3] Paths ────── each label on the frontier is traced back into a path = one candidate; the as-is path is candidate 0, always in the products ──────────── paths.json
      │
      ▼
[4] Branches ────── DISCRETION pending items of each frontier path → yes/no assignment → recompute hop by hop (answers passed in as assumptions) ──── branches.json
      │
      ▼
[5] Tax table ──── per branch per hop wht / incl / rate / credit / tax, floor and ceiling sides, total tax per 100 and amount ── tax.json
      │
      ▼
[6] Ranking, deltas, open items ── floor ↑, ceiling ↑, no deferred payment ↑, no restructuring ↑, hops ↑; dominance; delta; flip each open item to see whether the ranking changes ── ranking.json, deltas.json, open_items.json
      │
      ▼
Product directory products/<case>/ + version.json (input hash, rule-layer and library versions, generation time)
      │
      ▼
Read-only consumers: agent, report, checking (optimization/tools/check.py re-verifies the frontier by exhaustion; item-by-item trace-back uses rule/tools/trace.py)
```

## 2. Structure diagram

```text
optimization/
├── 优化层规范.md
├── move.csv                     move vocabulary (data)
├── optimization_test.csv        golden tests
└── tools/
    ├── optimize.py              run | graph | labels | paths | evaluate | fork | transfers | requirements | rank | delta | exposure | one_off | open_items | diff | version   (read-only functions + CLI)
    ├── fx.py                    exchange-rate fetching: public API → fx.json (every number with source and date); implemented
    └── check.py                 the checks of §7 (incl. exhaustive baseline)

Data dependencies
  database/ ──→ rule/ (eval_flow, query.gap, coverage, treaty) ──→ optimization/tools/optimize.py
  facts + destination set + move.csv ────────────────────────────────┘
                                                                  │
                                                                  ▼
  products/<case>/
    graph.json        {nodes:[{node_id, jur, subject, resources}], edges:[{edge_id, tail, head, hop_facts, w:{floor, ceiling}, t:{floor, ceiling}, needs, items_ref}]}
    labels.json       {node_id: [{label_id, w:{floor, ceiling}, needs, resources, pred_label, edge}]}   non-dominated set
    paths.json        [{cand_id, path:[node_id], edges:[edge_id], moves, restructure, path_complete}]   candidate 0 = as-is
    edges/<edge_id>.json  the eval_flow output items of each edge (as-is; amount_dependent edges are additionally stored per label and side as edges/<edge_id>.<label_id>.<side>.json)
    hops/<cand_id>.json   the eval_flow output items of each hop (as-is, incl. assumptions, value_kind, pending, cite_ids)
    transfers/<cand_id>.json   the eval_transfer output items for each holding change of the candidate (the transferor's cells in both jurisdictions, source cell and residence cell, as-is); output items of penalty cells go to penalty/<jur>.json
    requirements/<cand_id>.json   the condition tree (rule-layer requirements) for each favourable effect of each hop of the candidate, procedure sentences verbatim, reference parameters (deadlines, certificate years), as-is
    diff.json         differences against another product directory (§4.10): candidates swapping places, interval changes, new / vanished open items, which items of the input hash changed
    branches.json     [{branch_id, cand_id, answers_assumed:{predicate: yes/no}, hops: references to the recomputed output items}]
    tax.json          [{branch_id, per_100:{floor, ceiling}, amount:{floor, ceiling}, hops:[{wht, incl, rate, credit, tax}×2 sides], path_complete, cfc_flag}]
    ranking.json      [{branch_id, rank, dominated_by, keys}]
    deltas.json       [{branch_id, vs_as_is, vs_fallback, vs_best, baseline_branch, saving_per_payment:{floor, ceiling}, payback_payments, vs_best_no_restructure:{branch_id, saving_per_payment, payback_payments}, exposure_if_denied:{tax, interest, fine:{floor, ceiling}, total:{floor, ceiling}, cells}, one_off_cost:{transfers:[{target, home, consideration, gain, income_tax, stamp, items_ref}], total:{floor, ceiling}}}]
    open_items.json   [{kind: tax | derived | exposure | one_off, need, key, about (which payee node the judgment point asks about), question, blocks:[branch_id], changes_rank:bool, narrows_best:bool, factor_vars, if_yes / if_no or if_favourable / if_unfavourable or if_as_derived / if_opposite, tried_values, hidden_by_assumption, value / from / confirm (derived)}]
    gap.json          the rule-layer gap result for each edge; jurisdictions excluded because the library is incomplete
    fx.json           {base, date, jur, role, rule:[fx_rate_* parameters], rule_day, rates:{currency:{rate, source, url, date, note, rule_cites}}, missing}   the exchange rates used in this run, saved as-is
    version.json      {inputs_sha256, rule_version, database_version, engine_sha256, generated_at, limits, inputs:[the hashes of each of: facts, destination set, move.csv, limits, hard constraints, exchange-rate table, as-of date, valuation input, payback ceiling]}
```

Products reference each other only by id and do not copy values; tax amounts appear only once (in the tax table); everything else points to rule-layer output items.

## 3. Inputs

| Input | Content |
|---|---|
| Facts | Same as the rule layer: payment facts (holding_pct, holding_months, amount, date…), `payer.*`, `payee.*`, predicate answers (yes / no / unknown + grounds), structure variables |
| Destination set T | Whose hands the money may finally end up in: one or more (jurisdiction, subject), such as "Singapore company" and "Singapore individual"; if absent, T = {current payee} and only a single hop is done |
| Evaluation date, mode | The payment date; `plan` (structure variables of newly inserted entities are PLAN) or `record` |
| Assumption list | Fact / answer keys the caller declares as assumptions, passed as-is to the rule layer's `assume` |
| move.csv | Move vocabulary, see §4.4 |
| Limits | Hop limit (default 3, i.e. ≤ 2 intermediate jurisdictions), move-stacking limit (default 3), label count limit per node |
| Hard constraints | Optional: set of excluded jurisdictions (those nodes are not built), or the set of jurisdictions to consider, `consider` (only those are built, with the jurisdictions of the as-is structure, the destinations and the known entities), whether restructuring moves are allowed, subject types not allowed to stop outside the destination set. Filters only, no preference weights — the objective remains the single total tax |
| As-of date | The date used for computing exposure (§4.7): interest runs from each hop's filing deadline (the deadline parameters in the rule layer's `reference_params`) to the as-of date; if absent, = evaluation date and interest is 0 |
| Exchange rates | Optional: a table of exchange rates from the payment currency to each jurisdiction's currency (the fx.json of `tools/fx.py`, or filled in by the caller by hand, every number with source and date). Used in two places: converting the amount arriving at an individual destination into the payee's currency (`amount_payee_ccy`) for progressive rate schedules; converting the inputs of the one-off cost (net assets, cost, appraised value, in the currency of the transferred company) and each jurisdiction's transfer taxes into the payment currency, so that they can be divided by and added to the annual dividend tax (§4.7). If a currency is missing, the former does not pass that variable (the rule layer gives the bracket interval and records MISSING), and the latter marks the whole one-off cost item MISSING with `fx_missing`. Jurisdictions whose tax law prescribes the exchange rate take it as prescribed: the library parameters `<jur>.<slot>.fx_rate_*` record which quote, which day and whose quote is used (Mainland: the RMB central parity rate on the day the withholding obligation arises, the payee by month-end / previous month-end; Japan: the TTM of the principal bank on the transaction day; Thailand: the commercial-bank selling rate on the payment day or the Bank of Thailand's reference average selling rate, once chosen it may not be changed; Singapore and Hong Kong have no rule); `fx.py --jur` reads these parameters to choose the date and source: Mainland takes the CFETS central parity (official figure), Thailand takes the central bank API (needs a key, otherwise the market rate is used and noted), Japan has no official TTM, the midpoint of MUFG Bank's TTS / TTB is used as representative and noted; every number in fx.json carries rule_cites |
| Facts of destination individuals | Individual nodes in the destination set need `other_taxable_income` (other net taxable income of that year, in the payee's currency); if absent it goes to open items as above |
| Valuation for restructuring | Optional: owners' equity in the transferred company's latest audited statements (`net_assets`, a client fact, with provenance), the cost of the holding (`cost_base`) and its currency (`currency`; if absent, the company's local currency); a cost stated in another currency goes in `cost_currency` and is converted by fx.json, marked `cost_converted` (the statutory conversion date is a matter for the rules); with a valuation report, `appraised_value` replaces net assets as the consideration. Without net assets the candidate's whole one-off cost is MISSING; the candidate stays, only its one-off cost is unknown. A missing cost is an open item only where some side actually taxes the transfer gain |
| Past dividends | `past_payments`: one row for each earlier dividend (date, gross, payee_share, withheld, net_received, treaty_claimed, source), see the product `past_payments.json` |
| Known entities | The parent_jur and parent_holding_pct in the payee's facts count as a known entity, and paying up to it is no restructuring. `entities`: companies and individuals already existing in the group (e.g. the parent company, the ultimate shareholder), each with facts, whom it holds, holding percentage and holding period. They determine which holding changes are share transfers, the group-relationship percentage of indirect transfers, and the residence facts of individual destinations |
| Facts for CFC and moves | For an intermediate or retaining company acting as payer, `payer_etr` (effective tax burden) and `specified_cfc`, in that entity's facts; for an individual who moves, `exit_assets_value`, `exit_assets_cost` (currency of the jurisdiction left) and `years_resident_last_10`. An individual destination that is no known entity while the known individual lives elsewhere is read as that person moving (§4.7) |
| Payback ceiling | Optional hard constraint: restructuring candidates repaying in more than X payments are filtered out; none unless the client gives one |

A newly inserted intermediate entity has no facts: of its client_fact variables only those set by a move have values, the rest are MISSING; its structure variables are PLAN. The optimization layer does not invent facts for it; what is missing goes into needs.

## 4. Algorithm

**Name**: resource-constrained multi-label shortest path (resource-constrained shortest path, label-setting), i.e. multi-criteria Dijkstra (Martins 1984; the label algorithms of Desrochers–Soumis 1988). **Principle**: under the convention that "an intermediate entity redistributes the whole after-tax net amount", the retained fraction is the product of (1 − t_k) over the hops, so minimising total tax is equivalent to minimising Σ −ln(1 − t_k); edge weights are therefore additive and shortest path holds. Edge weights are intervals and carry open items, so each node keeps not one optimal value but a non-dominated label set, and the algorithm returns the Pareto frontier to the destinations rather than a single path.

### 4.1 Building the graph

- **Node** = (jurisdiction, subject, resource state). Subject ∈ {company, individual}; resource state = hops used, moves made (see §4.4). Individuals are nodes: "an individual in Singapore" is a destination node.
- **Source** = the payer (S, company). **Destination set T** comes from the input.
- **Edge** = a one-hop dividend flow (tail → head), generated only between jurisdictions for which all six dividend slots (outbound_wht, inbound, final, residence, cfc, anti_abuse) are present in the library (rule-layer `coverage`); when the penalty or restructure cell is absent the edge is still built, only exposure and one-off cost are marked missing; different move combinations on the same pair of jurisdictions are different edges.
- **Edge facts** hop_facts: tail's facts as payer (if it is the previous hop's payee, take the previous hop's `payee.*`), head's facts as payee (as-is entities take their facts; new entities only what moves set), payment facts.
- **Edge weight**: the rule layer's `eval_flow(tail.jur, head.jur, head.subject, date, hop_facts, answers, mode, assume)` gives the eight output items of the hop; they are composed into the combined tax rate t = [t_floor, t_ceiling] per §4.5, w = −ln(1 − t), each side computed separately. Requires t < 1 (there is no 100% tax in the library; if one appears the edge is infeasible). The edge also carries needs (the union of the needs of the hop's output items) and items_ref.
- **Edge locality**: t depends only on tail's facts, head's facts and the payment facts, not on earlier hops; this is the premise for shortest path to hold. There are four kinds of cross-hop dependency; the first two are recomputed at candidate level (the candidate's hops/ use the recomputed facts, the label weight may be optimistic, the product note says so): first, the payer's "income already taxed / tax rate" can be inferred from the previous hop's inbound and final output items (`payer_income_taxed`, `payer_tax_rate`, inferred and inserted by this layer when the caller did not give them); second, when the as-is payee changes holder on the path (the downstream node is not its known parent company), the safe-harbour facts about the parent (parent_*) in the hop upstream of it no longer hold; they are replaced per the new holder, and whether the treatment is no worse is recorded as MISSING. The latter two: first, the Mainland's multi-tier indirect credit, handled as a resource dimension (§4.2), not enabled in this version. Second, edges entering an individual node: the individual's final cell may be a progressive rate schedule (rule-layer `schedule`), the effective rate depends on the amount received, and the amount received = source amount × the retained fractions of the preceding hops. An individual is a destination and does not distribute further, so such edges are not weighted in advance: graph.json marks them `amount_dependent`, and the weight is computed live for the label during label relaxation (§4.3) — `amount_payee_ccy = amount × exp(−w_label) × exchange rate`, the floor side using w_floor and the ceiling side using w_ceiling, passed together with `other_taxable_income` as head's facts to `eval_flow`. Without an exchange rate or other income they are not passed; the rule layer gives the bracket interval and records MISSING.

### 4.2 Labels and dominance

A label L = (node, w_floor, w_ceiling, needs, resources, pred_label, edge).

- `w_floor`, `w_ceiling`: cumulative weight from the source to node, each side accumulated separately (the monotonicity of §4.5 guarantees that computing each side once gives the endpoints).
- `needs`: the union of the needs of the edges along the way (variable names, predicate keys).
- `resources`: hops used; restructure moves made; the set of transfers implied by the path (whose shares are sold: the source company changes holder = `sell:source`, the as-is payee changes holder = `sell:payee`, an increase of holding = `acquire:<move>`); (optional dimension) creditable tax. The transfer set enters the dominance condition (⊆), because the one-off costs of selling different companies are not comparable, and the cost is not yet known at the label stage.
- **Dominance**: L1 ≽ L2 if and only if w_floor₁ ≤ w_floor₂ and w_ceiling₁ ≤ w_ceiling₂ and needs₁ ⊆ needs₂ and resources₁ is no worse than resources₂ (no more hops, no more restructuring). Labels whose needs differ and neither contains the other are incomparable; both are kept.
- **Resource constraints**: labels with hops > limit or stacked moves > limit are discarded.

### 4.3 Label algorithm

```text
labels(graph, source, T, limits):
  init: L0 = (source, 0, 0, ∅, hops 0, None, None); open = {L0}; labels[source] = {L0}
  while open ≠ ∅:
    L = the label in open with the lexicographically smallest (w_ceiling, w_floor)           # label-setting: pop by the unfavourable side; a popped label never changes again
    for edge in out_edges(L.node):
      if edge violates the resource constraints given L.resources: continue
      if edge.amount_dependent: edge = eval_edge(edge, amount × exp(−L.w_floor) × fx, amount × exp(−L.w_ceiling) × fx)   # §4.1, edges entering an individual destination are evaluated live per label, the result is recorded in hops/
      L' = (edge.head, L.w_floor + edge.w_floor, L.w_ceiling + edge.w_ceiling, L.needs ∪ edge.needs, L.resources + edge, L, edge)
      if there exists M ∈ labels[edge.head] with M ≽ L': continue           # dominated, discard
      delete the labels in labels[edge.head] dominated by L'; labels[edge.head] += L'; open += L'
  frontier = ∪_{n ∈ T} labels[n]
  return labels, frontier
```

Edge weights are non-negative (t ≥ 0 ⇒ w ≥ 0), so the "popped means settled" property of label-setting holds: a label popped by w_ceiling will not be improved later by a smaller w_ceiling; the non-dominated set over both sides and needs guarantees the frontier is complete. When there is a label count limit per node, labels are truncated by (w_ceiling, w_floor) and marked `truncated` in the products.

### 4.4 Moves and destinations

`move.csv` columns: move_id, kind (path / fact / entity), sets (`name=value` or `name=<arg>`, semicolon-separated), arg_domain (`jur` / `pct:25;50;100` / `months:6;12` / `bool` / `company;individual`), precondition (infix condition, same syntax as rule layer §3, evaluated against the as-is facts), restructure (`transfer` / `acquire` / `no`, see §4.7), note. Minimal vocabulary: `via(jur)` (pass through a new jurisdiction = insert a holding company, restructure=transfer), `direct` (remove the intermediate company, restructure=transfer), `holding_pct(pct)` (increase holding, restructure=acquire), `wait_months(months)`, `remit(bool)`, `payee_type`.

How moves enter the graph:
- `via` / `direct` are not moves but the path itself: passing through a jurisdiction is taking that edge; the as-is path is candidate 0 and is written into the products whether or not it is on the frontier.
- `fact` moves (raise the holding, defer payment, do not remit) change the hop_facts of one hop and generate parallel edges on the same pair of jurisdictions; each edge records which moves it used; the stacking limit is a resource constraint.
- `entity` moves (change the payee subject) change the subject of the head node, i.e. choose another edge.
- Every holding change outside the as-is path counts as restructuring: each place on a candidate path where the holding relationship differs from the as-is corresponds to one share transfer — the transferor is the as-is holder, the transferred company is the one it holds. Each transfer calls the rule layer's `eval_transfer(jurisdiction of the transferred company, jurisdiction of the transferor, subject of the transferor)`, obtaining the two output items of the source cell and the residence cell, which are composed into the one-off cost (§4.7). The cost of relocation (an individual changing residence) is recorded by name only.
- `restructure` is a resource dimension: the transfers and acquisitions made are recorded in the label; at ranking, "no restructuring" comes first at equal total tax; the two kinds have different cost algorithms (§4.7).

### 4.5 Combined tax rate of an edge and the objective

Hop (edge) k is composed from the rule layer's output items:

```text
wht_k     = value of the outbound_wht item (%); absent or None → 0 and a note
incl_k    = value of the inbound item (inclusion percentage, %); absent → 0
rate_k    = value of the final item (rate × this cell's inclusion percentage, %); absent or None → 0 and a note
s_k       = the share of the income's gross already taken by tax before this hop: the source company's own income tax (payer_etr, else payer_tax_rate) and the taxes of earlier hops, those of the recipient's own jurisdiction left out
u_k       = s_k / (1 − s_k)                                               # underlying tax per unit of dividend
base_k    = 100 × (1 + u_k)  if inbound carries credit_underlying and the library's <jur>.inbound.underlying_gross_up is yes, otherwise 100
res_k     = incl_k / 100 × rate_k × base_k / 100
credit_k  = min(res_k, wht_k·[credit] + 100·u_k·[credit_underlying])     # ordinary credit limited to the residence-state tax; credit_underlying also credits the underlying tax (Mainland art. 24, Hong Kong s50AAAB)
t_k       = (wht_k + res_k − credit_k) / 100                              # combined tax rate of this hop
w_k       = −ln(1 − t_k)
total tax per 100 = 100 × (1 − Π_k (1 − t_k)) = 100 × (1 − exp(−Σ_k w_k))
```

Both sides are computed once each: floor uses the floor of every cell, ceiling the ceiling of every cell. The premise is that t_k is monotonically non-decreasing in each component (t rises as wht, incl, rate rise; t falls as credit rises, and credit itself is monotone in wht and res), so taking the extreme on each side gives the interval endpoints without enumerating combinations. Hops whose cfc item is yes are marked `cfc_flag` (tax on attributed income is not in the formula; the library has no attribution-percentage parameter). Hops where None appears are marked `value_missing` in the tax table, the branch is marked incomplete and is ranked after all complete ones. "Full redistribution" is the definition of a candidate; what the client wants to retain is handled with `remit(no)` or by adding the retention location to the destination set as another candidate.

**A domestic hop** (payer and recipient in the same jurisdiction): no withholding, inclusion 100, the final cell sets the tax.

**CFC inclusion**: when the cfc cell of the hop's recipient jurisdiction includes the payer's profit, the hop is taxed as an inclusion (paid out in full in the same period, the later dividend excluded, nothing counted twice). With a credit, t_k = max(wht_k, (r − s)/(1 − s)), r being the cfc cell's inclusion rate; s is s_k under `credit_underlying` and, under `credit`, only the tax the payer bore itself (the previous hop's tax; for the source company its own income tax). Without a credit, t_k = wht_k + r. A pending inclusion is the ceiling, its absence the floor. It does not apply when the payer is in the recipient's own jurisdiction. When money stays in a destination company whose known shareholder's cfc cell includes it, a retention pseudo-hop closes the path (destination → shareholder, only the cfc cell, nothing paid) and is taxed the same way. Several controlled companies in a chain included by the same shareholder hop by hop may be counted twice; the products show it as it is.

**Path-dependent edge weights**: s_k depends on the path. Building the graph, only the hop out of the source company knows s; other edges are computed with s = 0 (an upper bound) and marked `prior_dependent`; the label algorithm recomputes them from the label's accumulated weight (whoever levied it), and the hop-by-hop recomputation of a candidate path leaves out exactly the taxes of the recipient's own jurisdiction.

### 4.6 Branches (scenario enumeration)

```text
fork(path, items):
  D = {key : some item of some hop has ("DISCRETION", key) in its pending}     # already past the rule layer's counterfactual filter; only items of dividend hops (hops/) are taken, predicates of restructure and penalty cells are not branched
  evaluate with D all favourable, add the points that open, up to three rounds   # a denial in doubt hides the rule it denies; that rule's point opens only once the denial settles
  if D = ∅: return [branch(path, {})]
  branches = []
  for assignment in {yes, no}^D:                               # |D| usually ≤ 3; beyond the limit: all favourable, all unfavourable and each point going against the client alone, marked; the favourable side comes from the predicate's favourable column
    items' = hop by hop eval_flow(…, answers ∪ assignment, mode, assume ∪ keys(D))
    branches.append(branch(path, assignment, items'))
  return branches
```

Judgment points are expanded as `key@jur`: the jurisdiction of the cell that asks the point decides it (Mainland and Hong Kong anti-avoidance are the two points gaar@cn and gaar@hk). A client's answer without a jurisdiction holds for all of them.

Branching is done only for frontier paths and candidate 0 and does not enter the label state (otherwise the number of labels grows exponentially). The answers fixed in a branch are passed in via `assume`; the rule layer's output items list them under assumptions and attach the interval without the assumptions — a branch does not treat a predicate as a fact, it treats it as a marked assumption. MISSING and PLAN are not branched: they are facts to be asked or decided and stay in the open items.

### 4.7 Ranking, deltas, open items

```text
rank(branches):
  complete branches are sorted by (floor ↑, payback in payments ↑ (no restructuring = 0, unknown last), ceiling ↑, deferred payment (no first; the wait_months move), hops ↑, branch_id), deterministic     # lexicographic; the time cost of a deferred payment is not in the tax figures
  dominance: A.ceiling ≤ B.floor and A.path_complete = B.path_complete → B.dominated_by += A        # interval dominance
  incomplete branches (value_missing or path not reaching a destination) are listed separately and take no part in dominance

delta(a, b) = {floor: a.floor − b.floor, ceiling: a.ceiling − b.ceiling, amount likewise}           # side-by-side subtraction
deltas: each branch against the corresponding branch of candidate 0, against the all-unfavourable branch of its own candidate (fallback), against the first-ranked

open_items(ranking):                                                                            # one-factor-at-a-time sensitivity
  for need in ∪ the needs of each candidate's best branch ∪ the needs hidden by assumptions (the output item's without_assumptions.needs, marked hidden_by_assumption):
    A = recompute the ranking with the item set favourable; B = set unfavourable      # values of a variable: bool takes true / false; numeric takes every threshold the rules compare it with and either side of it; enum takes the allowed values; the affected branches are rerun hop by hop, taking the result with the lowest / highest ceiling
    changes_rank = the first-ranked differs between A and B
    narrows_best = the first-ranked's interval narrows under A or B
  sort by (changes_rank, narrows_best, occurrence count) descending; attach the variable's question / the predicate's question and the current values of factor_vars (from rule-layer judgment_points)
  judgment points are listed separately by (predicate key, which payee is asked about) (the same bo for the HK company and for the SG company are two questions); if_yes / if_no take the respective best among all complete branches of that payee
  facts inferred by this layer (payer_income_taxed, payer_tax_rate of §4.1; owner_safe_harbour (item 4(4) of STA 2018 No. 9) and passes_on_within_12m (the structure itself pays the dividend on to a third jurisdiction), both from the holding chain; future_cn_tax_not_reduced in transfers) are listed separately as kind = derived: value, derivation grounds, the rules that read it, whom to confirm with; for bool the opposite is recomputed once to see whether the first-ranked changes
  open items of transfer cells (PLAN consideration_in_shares, DISCRETION reasonable business purpose, MISSING group-relationship percentage, etc.) are listed as kind = one_off, the one-off cost is recomputed for each value; they order only structures of equal tax (through the payback) and changes_rank is false
```

Intervals are not collapsed into expected values; The ranking uses the favourable side: judgment points take the favourable answer and pending facts the favourable side, which is the planning room the client's conditions give; the facts and judgment points the favourable side relies on are listed as the structure's premises (relies_on and judgment_points of the brief), and the unfavourable side is shown alongside as risk information only, not used to compare. No cost is computed; the order expresses only discriminating power. Decided by the user on 2026-11-02.

**Scenarios** (`scenarios.json`): every structure is compared under the same answers: all favourable, one point against the client at a time (the points of all structures together), all against; a structure without a point keeps its all-favourable value in that scenario. Each scenario names its first and second structure by the ranking key above. The structure rank (`structure_rank`) is the order under all favourable answers; a branch rank is only a row number of ranking.json. ranking.json sorts first by the number of answers against the client in the branch (`answers_against`), then by the ranking key, so rank 1 is the first structure under all favourable answers; a branch that happens to be cheaper with an answer against the client never moves ahead, it appears only in its scenario row. The `changes_rank` of a judgment point becomes: does the first structure with this point against the client differ from the first under all favourable answers; both firsts are attached (amount, restructuring, one-off cost, payback in payments) with `value_at_stake` (what the all-favourable first pays more when the point goes against). A one-off open item (net assets, cost, exit-tax inputs) changes the decision when its structure is first in some scenario. It is still one objective: the table only says who is cheapest if those answers hold; no probabilities.

**One-off cost** (one_off_cost): computed once per candidate and shared by all branches of the candidate (branches only change the assumptions of the dividend hops). Each holding change k on a candidate falls into one of two kinds — `transfer`: an intra-group transfer (inserting or removing an intermediate holding company; the transferor is the as-is holder); `acquire`: an increase of holding from a third party (moves of the `holding_pct(pct)` kind); the seller's tax is not the client's cost, only the buyer-side stamp duty counts. All amounts are converted into the payment currency per fx.json:

```text
consideration_k = appraised_value (when appraised) otherwise net_assets × changed holding percentage / 100 (input; if absent the whole item is MISSING, marked valuation_missing; open_items carries one entry per target company lacking the figure, with that company in about)
gain_k          = consideration_k − cost_base (if cost_base is absent, = consideration, i.e. the ceiling of the tax base, marked cost_missing); for the acquire kind gain_k = 0
income_tax_k    = gain_k × (source.rate + home.rate − credit_k) / 100   # transfer kind: the two restructure cells of eval_transfer, each side computed; when the residence cell has a credit effect (Mainland Article 23, Japan Article 69) credit_k = min(source.rate, home.rate), otherwise 0 and marked no_credit
stamp_k         = consideration_k × stamp / 100                    # transfer kind: the stamp of the source cell (both parties combined); acquire kind: only the buyer-side stamp rule (rule ids ending in transferee / bought_note; seller transferor / sold_note; if indistinguishable the full amount, marked stamp_side_unknown)
one_off_cost    = Σ_k (income_tax_k + stamp_k), floor / ceiling each computed; DISCRETION in restructure cells (e.g. reasonable business purpose) is not expanded into branches, it is carried as an interval and goes into open_items (kind = one_off)
indirect transfer: when the transferred company holds a company in another jurisdiction, a further `indirect` item is computed for the underlying company (target = the underlying company, `indirect_transfer = true`, the group-relationship percentage computed from the holding chain of the known entities, recorded MISSING if it cannot be computed); income tax only, no stamp duty (there is no instrument at the underlying level); and "indirect transfer reporting" is listed in `costs_unquantified`
Article 6, item (2) of STA Announcement 2015 No. 7 (the Chinese tax burden is not reduced on a subsequent indirect transfer) is inferred by this layer: the ceiling of the cn restructure cell is computed for a direct transfer of the Chinese company by the new holder and by the old holder respectively; if new ≥ old then `future_cn_tax_not_reduced = true`; the derivation is recorded in the derived section of transfers and listed in open_items (kind = derived, about = the transferred Chinese company); if either side cannot be computed the variable is left empty and goes to PLAN
when the transferor is an individual, the restructure cell of its residence may be a progressive schedule (Thai residents): this layer converts the transfer gain into the residence currency at the exchange rate and fills `amount_payee_ccy`; `other_taxable_income` is taken from that entity's facts; without an exchange rate the two ends of the schedule form the interval
baseline        = under the same answers (points the branch does not raise take the favourable answer): the structure as it is when it reaches a destination, else the cheapest structure that reaches one without restructuring
saving          = tax(baseline) − tax(branch of the candidate), both sides     # tax saved per payment, on amount, assuming the same amount each time (written into the product note)
payback_payments = one_off.floor / saving.floor (favourable side: the one-off cost at its floor, i.e. discretion answered favourably; the tax at its floor); a one-off cost of 0 → 0; saving.floor ≤ 0 → none (never repaid). Not discounted
```

Ranking: the primary key is the tax per payment (floor); equal taxes are ordered by the payback in payments (shorter first, no restructuring = 0, unknown one-off cost last); a payback ceiling X filters. A second payback against the "best complete branch without restructuring" (under the same assumptions), `vs_best_no_restructure`, is also computed. A candidate's restructure mark is determined by the transfers it implies (transfer / acquire / holder_unknown), not by the move table. The inputs of the one-off cost (net assets, cost, appraised value, exchange rate) all carry a source or assumption mark and go into the products; missing net_assets and cost_base are listed as open_items (kind = one_off). The one-off cost counts only the taxes the restructuring triggers at once; a DISCRETION in a restructure cell (such as the indirect-transfer tax if the reasonable commercial purpose is denied) takes the favourable answer at the floor and carries the denied figure at the ceiling, as an open item (kind = one_off); the report writes it as an assumption, not as a cost range.

**Exit tax**: an individual destination outside the residence of the known individual means that person moves: restructure records `relocate`, and the shares the person holds are not transferred; the one-off cost adds the tax of the exit cell of the jurisdiction left (`<jur>|individual|exit|*`): (exit_assets_value − exit_assets_cost) × rate, converted from that jurisdiction's currency into the payment currency. Missing inputs mark `exit_inputs_missing`; without exit rules the absence record gives 0; with more than one known individual `exit_person_unknown` is marked.

**Exposure** (exposure_if_denied): if a treatment obtained in a branch under a yes assumption (treaty ceiling, exemption, credit) is later denied, how much has to be paid back. For each such branch b and its all-unfavourable branch b⁻:

```text
tax      = tax(b⁻) − tax(b)                                   # additional tax, each side computed
split by cell: for the cells of each hop that carry an assumption — source-state cells (outbound_wht, anti_abuse) get the amount arriving at the hop × Δwht, residence-state cells (inbound, final, anti_abuse) get the amount arriving at the hop × Δ(res − credit); the arriving amount is computed by the retained fraction of b⁻
for each cell: penalty cell = <jur>|all|penalty|* of the cell's jurisdiction (rule-layer eval_cell); source-state cells accrue interest from the filing deadline, residence-state cells without a deadline parameter are marked deadline_missing
interest = tax_cell × Σ_i pct_i × periods_i(deadline → as-of date) / 100, then capped by interest_cap; period = once is added only once
fine     = tax_cell × [fine_min, fine_max] / 100
offset   = tax − Σ_cells tax_cell                             # cells of b⁻ without an assumption that move the other way (a larger foreign credit downstream); no interest or fine; marked offset_elsewhere when non-zero
total    = tax + Σ_cells (interest + fine) = Σ_cells (tax_cell + interest + fine) + offset, floor / ceiling each computed; listed cell by cell in the products
```

Deadlines come from the `withholding_deadline_*` parameters in the hop's `reference_params` (if absent the interest item is marked `deadline_missing` and only the fine is given); the facts for the penalty cell are `overdue_months` (= months from the deadline to the as-of date, computed by this layer and passed in) and the plan's own conduct (`PLAN_CONDUCT`): the treatment was claimed through the required filing (claim_reported = true), nothing concealed (concealment = false), no negligence (negligence = false), the return filed (return_filed = true) — a plan's steps prescribe the filing (the Mainland then recovers tax and late-payment interest only, STA 2019 No. 35 art. 16, D-cn-9). The remaining circumstance variable (voluntary_payment) is not passed, letting the rule layer answer with an interval: the floor of exposure uses the cell's floor, the ceiling the cell's ceiling. If the penalty cell is absent the whole item is marked `penalty_missing`; if the cell exists but has no interest item (e.g. Japan has not yet registered next year's special rate), the interest item is marked `interest_missing` and the fine is still computed. The remaining circumstance variables go into open_items with kind `exposure`: they do not change the ranking (changes_rank is always false), only narrow the exposure, and rank after the tax open items. Heavier cases such as evasion and concealment need facts a plan does not create; the products only name them. This is an interval, not a probability: it answers "how much would have to be made up if wrong", not "will it be wrong".

### 4.8 Exhaustive baseline

`check.py` performs a depth-first complete enumeration of the same graph (hops ≤ limit), computes the total-tax interval of each path per §4.5, takes the non-dominated set and compares it with the frontier in labels.json: the frontier must equal the enumerated non-dominated set (with label truncation, frontier ⊆ enumerated set is allowed and marked). At the current scale (11 jurisdictions, hops ≤ 3, stacked moves ≤ 3) the enumeration is 10³–10⁴ paths and takes seconds, so the baseline can always be run; the value of the label algorithm is that it stays exact as the scale grows, not that it is faster today.

### 4.9 Scale

Nodes ≤ 11 × 2 × number of resource states; edges = jurisdiction pairs × move combinations; one `eval_flow` per edge (milliseconds); the number of labels is bounded by the non-dominated set and the limit; branches ≤ 2³ × number of frontier paths. A whole run takes seconds to minutes and can be rerun in full.

### 4.10 Specified path, requirements, diff between two runs

Three on-demand read-only functions; none changes the search, they are only calls of existing functions plus writing to disk:

- **Specified path** (`evaluate --path <node;node;…> [--moves …]`): the caller gives a path (it need not be on the frontier; it may be the client's own idea); this layer builds its edges per §4.1, computes tax per §4.5, branches per §4.6, and computes deltas, exposure and one-off cost per §4.7; the product format is identical to that of frontier candidates, cand_id starts with `x-` and is written into paths.json (marked `requested`); it takes part in deltas but does not change the positions in ranking (ranking covers only the frontier and candidate 0); if a jurisdiction used by the path does not have all six cells, an error is raised and nothing is guessed.
- **Requirements** (`requirements`): for each hop of each candidate (incl. `x-` paths), take the favourable effects used in the hop's output items (cap, exempt, share, credit, treaty reading), call the rule layer's `requirements(slot_key, effect)` to obtain the condition tree (variables, parameters, predicates, procedure sentences verbatim) and `reference_params` (deadlines, certificate years, thresholds), written as-is to `requirements/<cand_id>.json`, each item with cite_ids. No sequencing of steps, no date computation; the report's action list is taken from here, in the same version as the tax amounts.
- **Diff between two runs** (`diff --against <another product directory>`): aligns the products of the two runs by cand_id / branch_id and lists: ranking changes (who moved up or down, newly appeared, vanished), changes of the both-side intervals of each branch, open items added / vanished / changed in discriminating power, changes in one-off cost and exposure, which input items' hashes changed in version.json, and `engine_changed` (whether optimize.py, rule.csv, param.csv and doc.csv each changed; version.json records `engine_sha256`), so a rank move with unchanged inputs has a cause. Lists differences only, does not explain causes. When the two runs' move.csv or rule-layer versions differ, marks `incomparable` and still outputs.

## 5. Products

All JSON, UTF-8, English key names. Each file carries `version` in its header (the same hash as version.json); products of different runs are not mixed.

- `graph.json`, `labels.json`, `paths.json`: structure of §2; hop_facts saved as-is (incl. the provenance fields given by the caller, which the optimization layer does not alter).
- `hops/<cand_id>.json`: rule-layer output items as-is (eight items per hop); items recomputed by branches go to `hops/<branch_id>.json`.
- `transfers/<cand_id>.json`: the `eval_transfer` output items of each holding change, as-is; `penalty/<jur>.json`: the output items of the penalty cells used, as-is. `items_ref` in deltas points to these two places.
- `tax.json`: the per-hop components and totals of §4.5, both sides; each hop also carries prior and prior_own (the tax borne before it), underlying and cfc_inclusion, and the retention pseudo-hop is marked retention; each component marks which output item it comes from (`hop, slot_key`).
- `brief.json`: the short version to read first: the terms, the winner, the as-is structure, the structures first or second in some scenario (tax with all favourable and all unfavourable answers, one-off cost, saving per payment, payback in payments, the scenarios where they come first), the scenario table (only scenarios that replace the first structure or change an amount; the rest counted), the judgment points of the recommended and the as-is structure (the first structure either way and what is at stake), the gaps that change the decision, the number of other structures. No new numbers: everything is taken from the other products.
- `scenarios.json`: the full scenario table of §4.7.
- `past_payments.json`: only with the `past_payments` input. Each payment re-evaluated on the as-is hop at its own date: statutory tax, treaty rate, refundable amount (if every judgment of that year goes the client's way), refund limit (`<jur>.outbound_wht.refund_claim_years`), and what does not reconcile.
- `ranking.json`, `deltas.json`, `open_items.json`: §4.7; each ranking row also has `answers_assumed` and `range_all_branches` (the widest range of the candidate over every judgment outcome) and `structure_rank`; each component of `exposure_if_denied` in deltas marks which penalty cell and which rule it comes from.
- `gap.json`: the rule-layer `gap` result for each edge, and the jurisdictions excluded because the library is incomplete.
- `requirements/<cand_id>.json`, `diff.json`: §4.10.
- `version.json`: input hashes — facts, destination set, move.csv, limits, hard constraints, exchange-rate table (fx.json), as-of date, valuation input, payback ceiling, each hashed and then combined into a total hash, omitted items hashing the empty string — `rule.version()`, generation time, limit parameters. If any item changes the total hash changes; "same input, same products" is judged by the total hash.

The products contain no textual conclusions. In the one-off cost, what can be computed (share-transfer income tax, stamp duty) has numbers and provenance; what cannot be computed has only a name (`costs_unquantified: ["indirect transfer reporting"]`), no number.

## 6. Function set and interface

All functions are read-only and deterministic. The CLI is `optimization/tools/optimize.py`:

| Function | Input → Output |
|---|---|
| `run` | facts file, destination set, date, mode, assumptions, limits → the whole product directory |
| `graph` | as above (no search) → graph.json |
| `labels` | graph.json → labels.json |
| `paths` | labels.json + as-is → paths.json, hops/ |
| `fork` | one candidate + its hops → branches |
| `evaluate` | one specified path + the same inputs as run → the path's hops / transfers / branches / tax / deltas, cand_id `x-…`, written into the same product directory |
| `transfers` | one candidate + as-is + valuation input + fx.json → transfers/<cand_id>.json (one set of `rule.eval_transfer` output items per holding change) |
| `requirements` | one candidate + its hops → requirements/<cand_id>.json (rule-layer requirements and reference_params as-is) |
| `rank` | tax.json (+ one_off, when N is given) → ranking.json |
| `delta` | two branch_ids → delta |
| `exposure` | one branch + its all-unfavourable branch + penalty cells + as-of date → exposure_if_denied in deltas |
| `one_off` | transfers/<cand_id>.json + valuation input + fx.json → one_off_cost, saving_per_payment, payback_payments in deltas |
| `diff` | this product directory + another product directory → diff.json |
| `version` | → version.json |

The exchange-rate table is generated separately by `tools/fx.py` (§3); `run` only reads it in; it is not a subcommand of optimize.py. For the MCP form see `优化层MCP规范.md`.

Where the facts come from, how judgment points are answered and how the products are written up into a report are all outside this specification; the only requirement on the input is validity (variable names, jurisdiction codes, three-valued answers); invalid input raises an error, nothing is guessed.

## 6a. MCP service `tax-opt`

See `optimization/优化层MCP规范.md` (2026-11-01, minimal set: run / evaluate / diff / fx and product slice reading).

## 7. Checks

`optimization/tools/check.py` reports an error on a product directory in the following cases:

1. Candidate 0 is missing; a move used by a path is not in move.csv; an edge whose precondition does not hold appears in the graph; duplicate edges;
2. Any hop's output items differ from a live rerun of `rule.eval_flow` (values, rules_applied, pending, assumptions); transfers/ differs from a live rerun of `rule.eval_transfer`, penalty/ from a live rerun of `rule.eval_cell`;
3. An edge weight does not equal the value recomputed from the output items per §4.5 (`amount_dependent` and `prior_dependent` edges recomputed for the label they belong to, in the exhaustive baseline too); a label's cumulative weight does not equal the sum of the edge weights traced back along pred_label; floor > ceiling; `amount_payee_ccy` in hops does not equal amount × exp(−w) × the exchange rate in fx.json;
4. The frontier differs from the non-dominated set of the exhaustive baseline of §4.8 (truncation excepted); a dominated label exists in a label set;
5. tax.json does not equal the value recomputed from the output items and each hop's recorded prior per §4.5; the ranking does not follow the keys of §4.7; deltas do not equal the differences recomputed from tax.json; an incomplete branch took part in dominance;
6. A branch's answers do not appear as assumptions in the corresponding output items (an assumption treated as a fact);
7. A number appears in the products that is in neither the output items nor move.csv; the version hash does not match the inputs;
8. Exposure does not equal the value recomputed from tax.json and the penalty cells per §4.7; interest exceeds interest_cap; a fine is outside [fine_min, fine_max]; the one-off cost does not equal the value recomputed from the restructure cells and the inputs per §4.7; when N is given, the ranking key is not total_N;

9. Any condition tree in requirements/ differs from a live rerun of the rule layer's `requirements`; an `x-` path took part in the positions of ranking; any difference in diff.json cannot be matched in the products of the two runs;
10. Any row of `optimization_test.csv` fails: `test_id, facts, destinations, date, answers, expect`, where expect is `<branch description> <floor> <ceiling> <rank>` or `open <key,key>`.

**Invariants**: same input, same products (equal hashes); every number can be traced back to an output item and from there via `rule/tools/trace.py` to the statutory text; candidate 0 always exists; edge weights are non-negative.

## 8. Build and delivery

- `python optimization/tools/optimize.py run --facts <facts.json> --destinations '<jur>:<subject>;…' --date YYYY-MM-DD [--mode plan] [--assume …] [--max-hops 3] [--max-moves 3] [--max-labels N] [--exclude jur,jur] [--no-restructure] [--fx fx.json] [--as-of YYYY-MM-DD] [--valuation <valuation.json>] [--payback-max X] --out products/<case>/` (each input of §3 has its own switch; `--valuation` is the file of net assets, cost and appraised value)
- `python optimization/tools/optimize.py evaluate --products products/<case>/ --path 'cn:company;jp:company;sg:individual' [--moves …]`; `… requirements --products …`; `… diff --products products/<case>/ --against products/<case>-v1/`.
- `python optimization/tools/check.py --products products/<case>/`: the checks of §7, exit code 1 on error.
- Tables: `optimization/move.csv`, `optimization/optimization_test.csv`.
- Environment: Python 3.11, standard library only; read-only calls to `rule/tools/eval.py`, `query.py`.
- Delivery = the whole `optimization/` folder.

**Input file** (`run --input`, JSON): `date`, `mode`, `amount`, `currency`; `payer {jur, facts}`, `payee {jur, subject, facts}`, `payment {…}` (payment facts, incl. the payer_* facts), `answers`, `assume`; `entities {"jur:subject": {facts, holds, holding_pct, holding_months}}` (known group entities, e.g. the parent company); `destinations [[jur, subject], …]`; `limits`, `constraints {exclude, allow_restructure, payback_max}`, `as_of`, `fx` (path to fx.json or an object), `valuation {"jur:subject": {net_assets, cost_base, appraised_value, property_rich_ratio}}`. Examples: `optimization/examples/case001.json` (CASE-001 as-is) and `case001_valued.json` (with an illustrative valuation added; the numbers are not from the case documents). In the products, `payback_payments` null means no payback (saving ≤ 0 each payment) or an unknown one-off cost.

**Implementation status (2026-10-31)**: implemented and passing the §7 checks and the golden tests: `move.csv` (6 moves), `optimize.py` (run / evaluate / requirements / diff / version; internally graph / labels / paths / fork / transfers / tax / rank / delta / exposure / one_off / open_items), `check.py` (the main checks of §7 items 1–9, exhaustive baseline, golden tests), `optimization_test.csv` (3 rows), `fx.py`. CASE-001: 10 nodes, 1080 edges, 9 frontier candidates, 48 branches, seconds to minutes; the specified path run through `evaluate` (via Japan) goes into the same product directory. Boundaries (not simplifications): a new entity's facts are only the two set by moves (place of incorporation, place of management) plus the inherited group facts, the rest go to open items; acquisition moves count only the buyer-side stamp duty, the seller's tax is not the client's cost; the residence-state credit is computed by the credit effect of the residence cell, jurisdictions without that effect are marked no_credit; when the as-is is not in the destination set it is listed as incomplete (deltas are still computed against it); all hops except the as-is single hop are evaluated in plan mode, structure variables with missing values go to PLAN rather than defaulting to no. Round six (evening of 2026-10-31): the inference of Article 6, item (2) of STA Announcement 2015 No. 7, the progressive-schedule input for individual transferors, the open_items for transfer-cell open items (kind = one_off) and the recomputation of derived items (`rerun_branch_with` recomputes the one-off cost together with the variables read by transfers, the scores read the recomputed one_off); CASE-001-valued: 9 candidates, 40 branches. Implemented: `tools/fx.py` (exchange-rate fetching, §3; source: Frankfurter's ECB reference rates by date, open.er-api fills in VND, AED etc., marked as latest rather than same-day rates).

**2026-11-02**: judgment points by deciding jurisdiction; underlying credit (`credit_underlying`) and the Mainland gross-up; CFC inclusion (intermediate hops and the retention pseudo-hop; Japan credits only the controlled company's own tax, the Mainland down the tiers); the exit tax of an individual who moves; a domestic hop includes 100%; a progressive table reads the amount itself when the recipient uses the payment currency; scenarios, structure ranks, open items and gaps judged against the scenarios; the brief rebuilt around the scenarios with the terms list. Examples `examples/case_cfc_jp.json`, `examples/case_exit_jp.json`; golden tests in optimization_test.csv.
