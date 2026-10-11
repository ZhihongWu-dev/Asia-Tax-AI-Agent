"""engine / bounds (伪代码.md §4–5) over the rule layer: every flow of a graph, two bounds, the cost of each pending group.

engine(graph, ctx, bound, force) -> (total, groups, labels)
bounds(graph, ctx)              -> Bounds(lo, hi, groups, cost, L_lo, L_hi)   # 2 + 2 x |groups| engine runs
The only stops are Reject (入口) and Defect (断言), as the contracts I2–I3 require.
"""
from dataclasses import dataclass
from typing import Dict, Tuple

from .facts import FIXED, facts_for, source_of
from .regions import absolute
from itertools import combinations

from .model import CFC_INCLUSION, IP_TRANSFER, LIQUIDATION, SHARE_TRANSFER, SPLIT_INCOMES, TOPUP, FlowEdge, Graph, Label, topo_order
from .params import Params
from .rules.compile import compile_rules
from .rules.eval import Flow, FlowResult, TaxItem, cond, evaluate_flow, matches, valid_on
from .rules.model import ALL, Mount
from .rules.procedure_common import add_months
from .rules.tri import decide
from .rules.spec import SPEC
from .rules.tri import AND, CEILING, DATA, DISCRETION, F, FLOOR, MISSING, OR, PLAN, Ctx, Need, T, Tri, U, tri
from .data.domain import DESIGNABLE, DESIGNABLE_FLOW

RULES = compile_rules(SPEC, Params())
RULES_BY_ID = {r.id: r for r in RULES}
OPPOSITE = {"ge": "lt", "gt": "le", "lt": "ge", "le": "gt", "is_true": "is_false", "is_false": "is_true"}
_PLAN_FAV = {}


def leaf_signs(rule, field_, pred):
    """Negation parities of the leaves of `rule` that read `field_` with predicate `pred`."""
    from .rules.model import And, Leaf, Not, Or
    out = []

    def walk(c, neg):
        if isinstance(c, Leaf):
            if c.field == field_ and c.pred.name == pred:
                out.append(neg)
        elif isinstance(c, Not):
            walk(c.x, not neg)
        elif isinstance(c, (And, Or)):
            for x in c.xs:
                walk(x, neg)
    if rule.cond is not None:
        walk(rule.cond, False)
    return out


def plan_favourable(field_, pred):
    """The value of a plan leaf (field, predicate) that favours the taxpayer under every rule reading it: the leaf
    supports the condition of a rule that helps, or opposes that of a rule that hurts. None when rules disagree or a
    rule's direction depends on the numbers (decided by computing both)."""
    key = (field_, pred)
    if key not in _PLAN_FAV:
        def one_side(p_):
            vals = set()
            for r in RULES:
                for neg in leaf_signs(r, field_, p_):
                    vals.add(None if r.ambiguous else ((not neg) == bool(r.favourable)))
            return vals
        mine, theirs = one_side(pred), one_side(OPPOSITE.get(pred)) if pred in OPPOSITE else set()
        v = mine.pop() if len(mine) == 1 else None
        if v is not None and len(theirs) == 1 and next(iter(theirs)) == v:
            v = None                                    # both sides favour some rule (direct vs indirect credit): compute
        _PLAN_FAV[key] = v
    return _PLAN_FAV[key]
EX_ANTE, EX_POST = "EX_ANTE", "EX_POST"


class Reject(Exception):
    """Entry: the core fields are not all there."""


class Defect(Exception):
    """Internal: an assertion failed."""


class Undecidable(Defect):
    """Too many interacting open decisions to take a bound exactly (2^k engine runs): `groups` names them with their
    needs, so the planner can ask for what closes them instead of approximating."""

    def __init__(self, msg, groups):
        super().__init__(msg)
        self.groups = groups


SETTLED = ("flow", "_settled")                # injected by engine(): the jurisdictions whose item on this flow is settled


class CaseCtx(Ctx):
    """Ctx with the EX_ANTE rule: a plan-controlled field is a pending PLAN item, not a fact (伪代码.md §3) — except for
    the rules of a jurisdiction whose tax on this flow is already settled: the past is a fact, no plan reaches it."""

    def __init__(self, facts, ticks=None, mode=EX_POST, adjustable=frozenset()):
        super().__init__(facts, ticks)
        self.mode, self.adjustable = mode, adjustable
        self.settled = facts.get(SETTLED, frozenset())
        self.rule = None

    def plan_controlled(self, elem, field):
        """A field the plan sets: adjustable for everyone, or designable for a company the plan creates — unless the
        structure's own flows already fix it (facts.FIXED, 口径 D19): the plan cannot undo its own flows."""
        if self.facts.get((FIXED, "%s.%s" % (elem, field))):
            return False
        if field in self.adjustable:
            return True
        if field in DESIGNABLE and elem in ("payer", "payee"):
            return bool(self.facts.get((elem, "created_by_plan")))
        return field in DESIGNABLE_FLOW and elem == "flow" and bool(self.facts.get(("payee", "created_by_plan")))

    def test(self, elem, field, pred, threshold=None):
        asking = getattr(self.rule, "scope", None)
        settled = asking is not None and asking.taxing in self.settled
        if self.mode == EX_ANTE and not settled and self.plan_controlled(elem, field):
            for p_, same in ((pred.name, True), (OPPOSITE.get(pred.name), False)):   # an action on this field decides
                if p_ is None:                                                   # every leaf on it
                    continue
                a = absolute(elem, field, self.facts, ":" + p_)
                for k in ((Need(PLAN, a),) if a is not None else ()) + (Need(PLAN, "%s.%s:%s" % (elem, field, p_)),):
                    if k in self.ticks:
                        return tri(self.ticks[k] == same)
            v = self.facts.get((elem, field))
            fav = plan_favourable(field, pred.name)
            if v is not None and pred(v, threshold) == (True if fav is None else fav):
                return tri(pred(v, threshold))    # already on the favourable side: doing more of it changes nothing
            return Tri(U, frozenset({Need(PLAN, "%s.%s:%s" % (elem, field, pred.name))}))   # the plan can get there
        return super().test(elem, field, pred, threshold)


@dataclass
class Bounds:
    lo: float
    hi: float
    groups: Dict[Tuple[str, str], frozenset]
    cost: Dict[Tuple[str, str], float]
    L_lo: Dict[str, Label]
    L_hi: Dict[str, Label]


def flow_of(graph, f, facts):
    seat = lambda eid: graph.entities[eid].attrs.get("seat") if eid else None     # 口径 D31
    return Flow(graph.entities[f.payer].loc, graph.entities[f.payee].loc, f.income, on=f.on,
                target_loc=graph.entities[f.target].loc if f.target else None,
                indirect_cn=bool(facts.get(("flow", "indirect_cn_target"))), id=f.id,
                payer_seat=seat(f.payer), payee_seat=seat(f.payee), target_seat=seat(f.target))


def label_tax(f, items):
    return round(sum(f.amount * it.effective / 100.0 for it in items if not it.deferred), 2)


GROUP_FACTS = ("group_revenue_eur",)              # facts of the consolidated group, the same for every member


def group_fact(graph, e, field_):
    """A group-level fact as the entity states it, else as any member states it; members stating different values
    is a conflict the planner asks about (returned as the string 'conflict'). 口径 D12."""
    v = e.attrs.get(field_)
    if v is not None:
        return v
    vals = {m.attrs.get(field_) for m in graph.entities.values()
            if m.id in graph.group() and m.attrs.get(field_) is not None}
    if len(vals) > 1:
        return "conflict"
    return next(iter(vals)) if vals else None


DEDUCTIBLE_OUT = ("INTEREST", "ROYALTY", "SERVICE_FEE")
LEVY_TEXT = {"vat": "增值税", "stamp": "印花税", "income": "所得税"}


def vat_borne(labels, eid, year=None, flow=None):
    """口径 D29. The VAT an entity bears on the modelled flows, signed (its input credits negative), as its accounts see it:
    the seller's is out of what it collected — the output VAT is a liability, not revenue (增值税会计处理规定) — or a
    cost; the payer's on a deductible payment is part of the expense, less what it credits. VAT on a purchase it
    capitalises (the IP it buys) goes into the asset, whose amortisation is a datum (口径 D27). Without labels: 0."""
    total = 0.0
    for lb in (labels or {}).values():
        f = lb.flow
        if f is None or (year is not None and f.on.year != year) or (flow is not None and f.id != flow):
            continue
        if f.payee == eid or (f.payer == eid and f.income in DEDUCTIBLE_OUT):
            total += sum(f.amount * it.effective / 100.0 for it in lb.items
                         if it.levy == "vat" and (f.payer if it.borne_by == "payer" else f.payee) == eid)
    return total


def outside_steps(b, graph):
    """口径 D30. The flows dated before a law the library starts from: a levy there that a group company would bear makes
    the candidate's tax unknown — like an unmodelled step (口径 D19), no plan, listed with its other numbers. A levy borne
    outside the group does not touch the objective: a note. Returns (steps, notes)."""
    group = graph.group()
    steps, notes = set(), set()
    for lb in (b.L_hi or {}).values():
        for (jur, levy, who), (law, since) in (lb.outside or {}).items():
            x = ("before_law", flow_name(lb.flow.id), lb.flow.on.isoformat(), law, since.isoformat(), LEVY_TEXT.get(levy, levy))
            if who in group:
                steps.add(x)
            else:
                notes.add(x + (who,))
    return sorted(steps), sorted(notes)


def own_tax(labels, eid):
    """Income tax the company itself owes on the flows in `labels` — it is the taxpayer of a receipt's items and of its
    own deductions (withholding it bears under a gross-up stays the recipient's tax): 125号 第五条 本层企业就利润和投资
    收益所实际缴纳的税额, as far as the modelled flows carry it."""
    return sum(lb.flow.amount * it.effective / 100.0 for lb in labels.values() for it in lb.items    # 口径 D04, D06
               if it.levy == "income" and not it.deferred and (lb.flow.payer if it.deduction else lb.flow.payee) == eid)


def other_tax(entity):
    """Income tax the company pays on what no modelled flow carries (its own business), before deducting the modelled
    payments: a datum for a real company (None while unknown, never nil by default); nil for a company the plan
    creates, which by design does nothing beyond its modelled flows."""
    if entity.attrs.get("created_by_plan"):
        return 0.0
    v = entity.attrs.get("income_tax_other")
    return None if v is None else float(v)


def cn_tiers(graph, resident, P):
    """财税〔2009〕125号 第六条 / 财税〔2017〕84号 第二条: the foreign companies whose tax stands behind a Mainland resident's
    dividends, by tier — the first held >= 20% directly by the resident; each next one held >= 20% directly by a single
    company of the tier above and >= 20% in total by the resident (directly, or through companies of the tiers).
    Returns {company: tier}. 口径 D05."""
    lim, n = P["cn.ftc.indirect_ratio_min"], int(P["cn.ftc.indirect_tiers"])
    foreign = lambda e: graph.entities[e].loc != "CN"
    tier, total = {}, {}
    for h in graph.holds:
        if h.holder == resident and foreign(h.held) and h.ratio >= lim:
            tier[h.held], total[h.held] = 1, h.ratio
    for k in range(2, n + 1):
        new = {}
        for h in graph.holds:
            z = h.held
            if z in tier or z == resident or not foreign(z) or tier.get(h.holder) != k - 1 or h.ratio < lim:
                continue
            tot = sum((hh.ratio if hh.holder == resident else total[hh.holder] * hh.ratio / 100.0)
                      for hh in graph.holds if hh.held == z and (hh.holder == resident or hh.holder in total))
            if tot >= lim:
                new[z] = tot
        for z, tot in new.items():
            tier[z], total[z] = k, tot
    return tier


def gain_cost(graph, f):
    """The seller's cost of the holding a share transfer disposes of — as stated on the flow, else the holding's own
    cost (the same value the rules read, facts.py)."""
    cost = f.attrs.get("cost_basis")
    if cost is None and f.target:
        h = graph.holding(f.payee, f.target)
        cost = h.cost if h is not None else None
    return cost


def book_amortization(f, year=None):
    """口径 D27. The buyer's book amortisation of the IP it bought on the step f, as the case states it per modelled year
    (ip_book_amortization: no method or useful life is assumed) — in one financial year (from the step's year, within
    the modelled years) or over all of them. None while not stated."""
    per = f.attrs.get("ip_book_amortization")
    if per is None:
        return None
    years = int(f.attrs.get("ip_horizon_years") or 1)
    if year is None:
        return float(per) * years
    return float(per) if 1 <= year - f.on.year + 1 <= years else 0.0


def step_income(graph, eid, year=None, labels=None):
    """口径 D22, D27. What the plan's IP transfer step adds to an existing company's stated profit or GloBE income, which
    describe its present business: the seller's book gain (proceeds less its carrying amount ip_book_value — none in a
    transfer at book value, which recognises no gain in the accounts, 口径 D28; the proceeds net of the VAT it bears,
    口径 D29) and the buyer's book amortisation. `year`: that year only; None: the modelled years. Returns (amount,
    what is still to ask)."""
    total, needs = 0.0, []
    for f in graph.flows:
        if f.income != IP_TRANSFER or eid not in (f.payee, f.payer):
            continue
        key = f.attrs.get("fact_key") or f.id
        if f.payee == eid:                                    # the seller
            if (year is not None and f.on.year != year) or f.attrs.get("ip_transfer_mode") == "BOOK":
                continue
            book = f.attrs.get("ip_book_value")
            if f.attrs.get("amount_unknown") or book is None:     # the price, or the carrying amount, still to ask
                needs += (["flow:%s.amount" % key] if f.attrs.get("amount_unknown") else []) + \
                         (["flow:%s.ip_book_value" % key] if book is None else [])
                continue
            total += f.amount - float(book) - vat_borne(labels, eid, flow=f.id)
        else:                                                 # the buyer
            a = book_amortization(f, year)
            if a is None:
                needs.append("flow:%s.ip_book_amortization" % key)
                continue
            total -= a
    return total, needs


def own_step_tax(labels, eid):
    """The income tax an existing company bears on its IP transfer step (the after-tax part of step_gain)."""
    return sum(lb.flow.amount * it.effective / 100.0 for lb in (labels or {}).values() if lb.flow.income == IP_TRANSFER
               for it in lb.items if it.levy == "income" and not it.deferred
               and (lb.flow.payer if it.borne_by == "payer" else lb.flow.payee) == eid)


def profit_needs(graph, eid):
    """The data a company's after-tax profit waits for: its own figure, or — for a company the plan creates — the cost
    of each holding it disposes of."""
    if not graph.entities[eid].attrs.get("created_by_plan"):
        return ("%s.after_tax_profit" % eid,)
    return tuple(["flow:%s.cost_basis" % f.id for f in graph.flows
                  if f.payee == eid and f.income in (SHARE_TRANSFER, IP_TRANSFER) and gain_cost(graph, f) is None]
                 + ["flow:%s.ip_book_amortization" % (f.attrs.get("fact_key") or f.id) for f in graph.flows
                    if f.payer == eid and f.income == IP_TRANSFER and book_amortization(f) is None])


def designed_profit(graph, labels, eid, year=None):
    """After-tax profit of a company the plan creates (created_by_plan): it has exactly the flows the plan models —
    income received, less deductible payments it makes, less the income taxes it bears (its deductions' saving
    included). None if a gain it realises has no known cost. `year`: that year's flows only. Stated in the plan as a
    design condition ("a pure holding / financing company"). 口径 D06."""
    e = graph.entities[eid]
    if not e.attrs.get("created_by_plan"):
        return None
    income = 0.0
    for f in graph.flows:
        if year is not None and f.on.year != year:
            continue
        if f.payee == eid:
            if f.income in (SHARE_TRANSFER, IP_TRANSFER):
                cost = gain_cost(graph, f)
                if cost is None:
                    return None
                income += f.amount - float(cost)
            else:
                income += f.amount
        elif f.payer == eid and f.income in DEDUCTIBLE_OUT:
            income -= f.amount
        elif f.payer == eid and f.income == IP_TRANSFER:           # 口径 D27: the IP it bought, amortised in its accounts
            a = book_amortization(f, year)
            if a is None:
                return None
            income -= a
    tax = sum(lb.flow.amount * it.effective / 100.0 for lb in labels.values() for it in lb.items
              if it.levy == "income" and not it.deferred and (year is None or lb.flow.on.year == year)
              and (lb.flow.payer if it.borne_by == "payer" else lb.flow.payee) == eid)
    return round(income - tax - vat_borne(labels, eid, year), 2)                # 口径 D29: and the VAT it bears


def pooled_credit(rule, entity, flows, graph, labels, P, bound, choose=None):
    """s50C: one credit = min(sum of foreign tax, sum of Singapore tax) over the pooled flows, never less than the
    item-by-item credits already given; allocated in proportion to the Singapore tax on each flow."""
    jur = entity.loc
    rows = []
    for f in flows:
        if f.income == TOPUP or f.amount <= 0:                  # 口径 D02: Part 14 credits do not reach DTT / MTT; an
            continue                                            # amount still asked for (nil) carries no tax to pool
        if source_of(graph, f) == jur:                          # 口径 D11: Singapore-sourced income is not in the pool
            continue
        it = next((x for x in labels[f.id].items if x.jur == jur and not x.deduction and x.levy == "income"), None)
        if it is None or it.rate * it.base_share <= 0:
            continue                                            # sg.ftc.pooling_sg_tax_not_nil
        foreign_items = [x for x in labels[f.id].items if x.jur != jur and x.jur is not None and not x.deduction and x.levy == "income"]
        foreign = sum(min(x.actual, x.rate * x.base_share) if x.actual is not None else x.effective for x in foreign_items)   # 口径 D01
        if not foreign_items:                                   # ex post: the tax actually borne abroad, as a fact
            rate = facts_for(graph, f).get(("flow", "foreign_tax_rate"))
            if rate is not None:
                foreign = float(rate)
            else:                                               # unknown: pending (at least the Singapore tax, or none)
                fav = choose(rule.id, f.id, ["flow.foreign_tax_rate"]) if choose else False
                foreign = it.rate * it.base_share if fav else 0.0
        rows.append((f, it, f.amount * it.rate * it.base_share / 100.0, f.amount * foreign / 100.0))
    if not rows:
        return
    sg_total, foreign_total = sum(r[2] for r in rows), sum(r[3] for r in rows)
    pooled = min(sg_total, foreign_total)
    if pooled <= sum(f.amount * it.credit / 100.0 for f, it, _, _ in rows) + 1e-9:
        return
    for f, it, sg_tax, _ in rows:
        it.credit = pooled * (sg_tax / sg_total) / f.amount * 100.0
        it.cites.append(rule.id)


def reinvestment_credit(rule, entity, flows, graph, labels, P, bound, choose=None):
    """公告2025年第2号: 10% of each qualifying reinvested dividend (the treaty rate if lower) offsets the Mainland tax
    on later income from the same payer to this investor; what is not used inside the horizon is not counted (I1)."""
    for d in flows:
        item = next((x for x in labels[d.id].items if x.jur == "CN" and not x.deduction and x.levy == "income"), None)
        rate = P[rule.value]
        if item is not None and item.cap is not None and P["cn.reinvest.credit_rate_treaty_lower"]:
            rate = min(rate, item.cap)
        available = d.amount * rate / 100.0
        later = sorted((f for f in graph.flows if f.payer == d.payer and f.payee == d.payee and f.on > d.on), key=lambda f: f.on)
        for f in later:
            it = next((x for x in labels[f.id].items if x.jur == "CN" and not x.deduction and x.levy == "income"), None)
            if it is None or available <= 0:
                continue
            room = f.amount * it.effective / 100.0
            use = min(room, available)
            if use > 0:
                it.credit += use / f.amount * 100.0
                it.cites.append(rule.id)
                available -= use


def carryforward_credit(rule, entity, flows, graph, labels, P, bound, choose=None):
    """财税〔2009〕125号 第九条 / EIT art 23: the Mainland credit is limited per source country and year to the Mainland tax
    on that country's income; the excess carries forward five years against later limits. Pools the item-by-item
    credits of one entity, never below what they already give."""
    from collections import defaultdict
    jur = entity.loc
    rows = []
    for f in flows:
        if f.income == TOPUP or f.amount <= 0:                  # 口径 D02: no top-up tax in the Mainland model; an amount
            continue                                            # still asked for (nil) carries no tax
        it = next((x for x in labels[f.id].items if x.jur == jur and not x.deduction and x.levy == "income"), None)
        if it is None or it.rate * it.base_share <= 0:
            continue
        rows.append((f, it, f.amount * it.rate * it.base_share / 100.0, f.amount * it.creditable / 100.0, source_of(graph, f), f.on.year))
    by_country = defaultdict(list)
    for row in rows:
        by_country[row[4]].append(row)
    horizon = int(P["cn.ftc.carryforward_years"])
    for country, rs in by_country.items():
        carry = []                                               # (year earned, excess still unused)
        for year in sorted({r[5] for r in rs}):
            this = [r for r in rs if r[5] == year]
            limit = sum(r[2] for r in this)
            paid = sum(r[3] for r in this)
            carry = [(y, x) for y, x in carry if year - y <= horizon and x > 1e-9]
            avail = paid + sum(x for _, x in carry)
            used = min(avail, limit)
            # consume this year's own foreign tax first, then the oldest carry
            from_own = min(paid, used)
            left = used - from_own
            new_carry = []
            for y, x in sorted(carry):
                take = min(x, left)
                left -= take
                if x - take > 1e-9:
                    new_carry.append((y, x - take))
            carry = new_carry
            if paid - from_own > 1e-9:
                carry.append((year, paid - from_own))
            given = sum(f.amount * it.credit / 100.0 for f, it, _, _, _, _ in this)
            if used <= given + 1e-9 or limit <= 0:
                continue
            for f, it, cn_tax, _, _, _ in this:
                it.credit = used * (cn_tax / limit) / f.amount * 100.0
                it.cites.append(rule.id)


ENTITY_EVALUATORS = {"sg.ftc.pooling": pooled_credit, "cn.reinvest.credit": reinvestment_credit,
                     "cn.ftc.carryforward": carryforward_credit}


def entity_stage(graph, ctx_of, bound, force, P, rules, labels, groups, only=None):
    """Rules mounted on an entity: their condition is read per flow of that entity, their effect spans the flows
    (those in `only` when given)."""
    for r in rules:
        if r.scope.mount is not Mount.ENTITY:
            continue
        for e in graph.entities.values():
            if r.scope.taxing not in (e.loc, ALL) and r.scope.side != "residence":
                pass
            if r.scope.side == "residence" and e.loc != r.scope.residence:
                continue
            qualifying = []
            for f in (graph.flows if only is None else only):
                if f.payee != e.id or f.income == TOPUP:          # 口径 D02: no entity-level credit reaches a top-up
                    continue
                facts = facts_for(graph, f)
                flow = flow_of(graph, f, facts)
                if not (r.scope.source in (ALL, flow.source_loc) and r.scope.covers(f.income) and valid_on(r, f.on)):
                    continue
                ctx = ctx_of(facts)
                ctx.P = P
                ctx.rule = r
                denied = False
                for d in rules:                       # anti-abuse denials reach entity rules too
                    if d.effect.name == "DENY" and r.id in d.overrides and matches(d.scope, flow) and valid_on(d, f.on):
                        ctx.rule = d
                        td = cond(ctx, lambda on: on, d.cond)
                        ctx.rule = r
                        if decide(td, d.favourable, bound, (d.id, f.id), force or {}):
                            denied = True
                        if td.v == "U":
                            groups[(d.id, f.id)] = td.needs
                if denied:
                    continue
                tri = cond(ctx, lambda on: on, r.cond)
                if tri.v == "U":
                    groups[(r.id, f.id)] = tri.needs
                if decide(tri, r.favourable, bound, (r.id, f.id), force or {}):
                    qualifying.append(f)
            if qualifying:
                def choose(rule_id, flow_id, keys, _g=groups):
                    grp = (rule_id, flow_id)
                    needs = frozenset(Need(MISSING, k) for k in keys)
                    _g[grp] = _g.get(grp, frozenset()) | needs
                    return decide(Tri(U, needs), True, bound, grp, force or {})
                ENTITY_EVALUATORS[r.id](r, e, qualifying, graph, labels, P, bound, choose=choose)


SPLIT_RULE = {"LIQUIDATION": "cn.liquidation.split", "CAPITAL_REDUCTION": "cn.capital_reduction.split"}
SPLIT_FACT = "accumulated_profits_share"          # the holder's share of accumulated profits and reserves, an amount


def split_cost(graph, f):
    """Cost the disposal part carries: the holding's cost (liquidation), or the share of it the withdrawn capital carries."""
    h = graph.holding(f.payee, f.payer)
    if h is None or h.cost is None:
        return None
    if f.income == "CAPITAL_REDUCTION":
        r = f.attrs.get("reduced_capital_ratio")                  # percent of the paid-in capital withdrawn
        return None if r is None else h.cost * float(r) / 100.0
    return h.cost


def parts(f, div, cost):
    """财税〔2009〕60号 第五条 / 公告2011年第34号 第五条: the dividend part, then the disposal of the holding for the rest."""
    from dataclasses import replace
    rest = f.amount - div
    attrs = {k: v for k, v in f.attrs.items() if k not in (SPLIT_FACT, "reduced_capital_ratio", "consideration", "cost_basis")}
    return [replace(f, id=f.id + ".div", income="DIVIDEND", amount=div, target=None, attrs=dict(attrs)),
            replace(f, id=f.id + ".gain", income="SHARE_TRANSFER", amount=rest, target=f.payer,
                    attrs=dict(attrs, consideration=rest, cost_basis=cost, shares_cancelled=True))]   # no transfer instrument


def split_variants(graph, f):
    """One decomposition when the dividend part is a fact. Otherwise the candidates among which the tax over every
    split is extreme: the tax is convex in the dividend part (a linear dividend tax plus a hinge where the gain reaches
    nil), so its maximum sits at an end and its minimum at an end or at the kink where the disposal part equals the cost."""
    cost = split_cost(graph, f)
    div = f.attrs.get(SPLIT_FACT)
    if div is not None:
        return [parts(f, min(max(float(div), 0.0), f.amount), cost)]
    cands = {0.0, f.amount}
    if cost is not None and 0.0 < f.amount - cost < f.amount:
        cands.add(f.amount - cost)
    return [parts(f, d, cost) for d in sorted(cands)]


def cfc_chain_ratio(graph, holder, held):
    """国税发〔2009〕2号 第七十七条: indirect holdings multiply down the chain, but a tier held above 50% counts as 100%."""
    if holder == held:
        return 100.0
    best = 0.0
    for h in graph.holds:
        if h.holder == holder:
            step = 100.0 if h.ratio > 50.0 else h.ratio
            best = max(best, step / 100.0 * cfc_chain_ratio(graph, h.held, held))
    return best


def cfc_flows(graph: Graph, P, needs=None, labels=None):
    """EIT art 45 / 实施条例 第一百一十七条: for every Mainland company controlling (>= 50% jointly, >= 10% singly) a foreign
    company whose after-tax profit it states, the profit not distributed in the horizon is a deemed distribution. The
    engine adds it as a CFC_INCLUSION flow dated after the last real flow; whether the Mainland charges it is for the
    cn.cfc.* rules (low tax, white list, size, business need)."""
    from datetime import timedelta
    out = []
    last = max((f.on for f in graph.flows), default=None)
    if last is None:
        return out
    for parent in graph.entities.values():
        if parent.loc != "CN":
            continue
        for sub_ in graph.entities.values():
            if sub_.loc == "CN":
                continue
            chain = cfc_chain_ratio(graph, parent.id, sub_.id)
            if chain <= 0:
                continue
            if any(f.payer == sub_.id and f.income == LIQUIDATION for f in graph.flows):
                continue                                        # wound up in the horizon: its profits are distributed (D19)
            atp = sub_.attrs.get("after_tax_profit")
            if atp is not None:                                 # 口径 D22, D27: the plan's IP step, after its own tax
                gain, missing = step_income(graph, sub_.id, labels=labels)
                if missing:
                    if needs is not None:
                        needs[("data.cfc_profit", sub_.id)] = frozenset(Need(DATA, k) for k in missing)
                    continue
                if gain:
                    atp = float(atp) + gain - own_step_tax(labels, sub_.id)
            if atp is None and labels is not None:
                atp = designed_profit(graph, labels, sub_.id)   # a company the plan creates: its modelled flows
            if atp is None:                                     # the inclusion is unbounded without it: ask
                if needs is not None:
                    needs[("data.cfc_profit", sub_.id)] = frozenset(Need(DATA, k) for k in profit_needs(graph, sub_.id))
                continue
            direct = max((h.ratio for h in graph.holds if h.holder == parent.id and h.held == sub_.id), default=0.0)
            share_control = chain >= P["cn.cfc.control_joint_min"] and not (direct and direct < P["cn.cfc.control_single_min"])
            distributed = sum(f.amount for f in graph.flows if f.payer == sub_.id and f.income == "DIVIDEND")
            retained = max(0.0, float(atp) - distributed)
            if retained <= 0:
                continue
            out.append(FlowEdge("cfc:%s>%s" % (sub_.id, parent.id), sub_.id, parent.id, CFC_INCLUSION,
                                round(retained * chain / 100.0, 2), last + timedelta(days=1),
                                attrs={"cfc_chain_ratio": chain, "cfc_share_control": share_control}))
    return out


P2_JURISDICTIONS = {"HK", "SG"}  # jurisdictions whose top-up rule is in the spec
JURISDICTION_CODES = frozenset({"CN", "HK", "SG"})   # a group keyed by a jurisdiction, not by a flow
P2_PRE = {"HK": "p2.", "SG": "sg.p2."}             # each jurisdiction's own enactment of the GloBE parameters
P2_THRESHOLD = {"HK": "p2.revenue_threshold", "SG": "sg.p2.revenue_threshold"}   # the rules' own scope parameters
P2_RATE = {"HK": "p2.minimum_rate", "SG": "sg.p2.minimum_rate"}                  # s7 / Art 10.1; 15% in s16(3), s21(1)
P2_IIR = {"HK": "p2.qualified_iir_hk", "SG": "p2.qualified_iir_sg"}              # 口径 D20: the OECD central record


def p2_entities(graph: Graph, loc):
    """The constituent entities located in a jurisdiction: the group's members there (MMT Act s5; GloBE Art 10.3)."""
    members = graph.group()
    return [e for e in graph.entities.values() if e.loc == loc and e.id in members]


def p2_excluded(graph: Graph, f, eid, P, law=None):
    """口径 D16. Income the GloBE computation leaves out of the receiving entity's GloBE income (Art 3.2.1(b)(c)):
    excluded dividends — on an ownership interest other than a portfolio shareholding held under a year at the
    distribution — and excluded equity gains — on disposing of an ownership interest other than a portfolio
    shareholding (MMT Act s2; GloBE Art 10.1.1). Without a holding edge the flow is not known to be on an ownership
    interest: included."""
    if f.payee != eid:
        return False
    pre = P2_PRE.get(law or graph.entities[eid].loc, "p2.")
    if f.income in ("DIVIDEND", "DISTRIBUTION") + SPLIT_INCOMES:    # a liquidation or capital reduction: a dividend part
        # and a disposal of the interest (engine.parts) — excluded on the same ownership interest (口径 D16, D20)
        h = graph.holding(eid, f.payer)
        if h is None:
            return False
        short = h.since is not None and add_months(h.since, int(P[pre + "short_term_months"])) > f.on
        return not (h.ratio < P[pre + "portfolio_shareholding_max"] and short)
    if f.income == SHARE_TRANSFER:
        h = graph.holding(eid, f.target) if f.target else None
        return h is not None and h.ratio >= P[pre + "portfolio_shareholding_max"]
    return False


def p2_tax(labels, graph: Graph, eid, year, P):
    """口径 D16. Covered taxes the entity bears on the modelled flows of a financial year — withheld on its receipts,
    charged where it sits, its deductions' saving included — less the tax on income the GloBE computation leaves out
    (GloBE Art 4.1.3(a); MMT Regulations reg 38(2)(a))."""
    return sum(lb.flow.amount * it.effective / 100.0 for lb in labels.values() if lb.flow.on.year == year for it in lb.items
               if it.levy == "income" and not it.deferred and (lb.flow.payer if it.borne_by == "payer" else lb.flow.payee) == eid
               and not (it.borne_by != "payer" and p2_excluded(graph, lb.flow, eid, P))
               and not (it.deduction and lb.flow.income == IP_TRANSFER)) + p2_step_tax(labels, eid, year, P)   # 口径 D27


def p2_step_tax(labels, eid, year, P):
    """口径 D27. The IP step's tax amortisation in the buyer's covered taxes for a financial year, with GloBE's deferred tax
    (Art 4.4.1): the current saving t x A_t, and deferred tax on A_t - A_b at t, recast at the minimum rate when t is
    higher — A_t the deduction over the modelled years taken evenly, A_b the book amortisation of the year. A buyer with no
    tax amortisation (Hong Kong, from an associate) has a permanent difference: nothing."""
    m, total = P["p2.minimum_rate"], 0.0
    for lb in (labels or {}).values():
        f = lb.flow
        if f.income != IP_TRANSFER or f.payer != eid:
            continue
        years = int(f.attrs.get("ip_horizon_years") or 1)
        if not 1 <= year - f.on.year + 1 <= years:
            continue
        a_b = book_amortization(f, year) or 0.0
        for it in lb.items:
            if it.levy == "income" and it.deduction and not it.deferred and it.borne_by == "payer":
                a_t = f.amount * it.base_share / years
                total += -it.rate / 100.0 * a_t + min(it.rate, m) / 100.0 * (a_t - a_b)
    return total


def p2_other(e):
    """Covered taxes outside the modelled flows: the group's datum (None while unknown); nil for a company the plan
    creates, which by design does nothing beyond its modelled flows (口径 D06, D16)."""
    if e.attrs.get("covered_taxes_other") is not None:
        return float(e.attrs["covered_taxes_other"])
    return 0.0 if e.attrs.get("created_by_plan") else None


def designed_globe_income(graph: Graph, eid, year, P, labels=None):
    """口径 D06, D16. GloBE income of a company the plan creates — exactly its modelled flows — for a financial year:
    what it receives less the deductible payments it makes, before tax (Art 3.2.1(a)), without excluded dividends and
    excluded equity gains (Art 3.2.1(b)(c)); net of the VAT it bears (口径 D29, with the flows' labels). None while the
    cost of an included gain is unknown."""
    income = 0.0
    for f in graph.flows:
        if f.on.year != year:
            continue
        if f.payee == eid and f.income not in (CFC_INCLUSION, TOPUP):
            if p2_excluded(graph, f, eid, P):
                continue
            if f.income in (SHARE_TRANSFER, IP_TRANSFER):
                cost = gain_cost(graph, f)
                if cost is None:
                    return None
                income += f.amount - float(cost)
            else:
                income += f.amount
        elif f.payer == eid and f.income in DEDUCTIBLE_OUT:
            income -= f.amount
        elif f.payer == eid and f.income == IP_TRANSFER:           # 口径 D27: the book amortisation of the IP it bought
            a = book_amortization(f, year)
            if a is None:
                return None
            income -= a
    return round(income - vat_borne(labels, eid, year), 2)


def p2_income(graph: Graph, e, year, P, labels=None):
    """An entity's GloBE income for a financial year: as the group states it (the figure of every modelled year — the
    case's events recur), or, for a company the plan creates, from its modelled flows. None while unknown."""
    if e.attrs.get("globe_income") is not None:
        gain, missing = step_income(graph, e.id, year, labels)    # 口径 D22, D27: the step's gain or amortisation on top
        return None if missing else float(e.attrs["globe_income"]) + gain
    return designed_globe_income(graph, e.id, year, P, labels) if e.attrs.get("created_by_plan") else None


def p2_income_needs(graph: Graph, e, year, P):
    """What an unknown GloBE income waits for: the group's figure, or the cost of a gain a created company includes."""
    if not e.attrs.get("created_by_plan"):
        return ["%s.globe_income" % e.id] if e.attrs.get("globe_income") is None else step_income(graph, e.id, year)[1]
    return ["flow:%s.cost_basis" % f.id for f in graph.flows if f.payee == e.id and f.on.year == year
            and f.income in (SHARE_TRANSFER, IP_TRANSFER) and not p2_excluded(graph, f, e.id, P) and gain_cost(graph, f) is None] + \
        ["flow:%s.ip_book_amortization" % (f.attrs.get("fact_key") or f.id) for f in graph.flows
         if f.payer == e.id and f.income == IP_TRANSFER and book_amortization(f, year) is None]


def p2_shares(graph: Graph, loc, law, ces, years, P, post, bound, force, labels, plan_ticks, ex_ante):
    """One jurisdiction's top-up, year by year, under one law (口径 D14-D17): the constituent entities located in loc are
    blended; with net GloBE income, excess profit = net income less the substance-based exclusion, shared in proportion
    to positive GloBE income (s16(2) A x B / C; Art 5.2.4); without, only an additional current top-up (p2_additional).
    Yields (year, tag, on, attrs, [(entity id, amount, attrs)]), each amount a pseudo-flow's — charged at the minimum
    rate times the shortfall share (p2_facts), an additional top-up's charged in full."""
    from datetime import timedelta
    rev = group_fact(graph, ces[0], "group_revenue_eur")
    if rev == "conflict":                                       # members state different group revenues: ask
        post(("data.group_revenue", "group"), frozenset({Need(DATA, "group.group_revenue_eur")}))
        return
    if rev is not None and float(rev) < P[P2_THRESHOLD[law]]:
        return                                                  # below the revenue threshold: the top-up rule cannot apply
    scope = set()
    if rev is None:                                             # in scope or not: unknown, pending (out of scope at the floor)
        grp = ("data.p2_scope", loc)
        scope = {Need(MISSING, "group.group_revenue_eur")}      # a group fact: one answer serves every member
        post(grp, frozenset(scope))
        if decide(Tri(U, frozenset(scope)), True, bound, grp, force):
            return
    applied = {}                                                # year -> the transitional CbCR safe harbour applied
    for year in years:
        on = max(f.on for f in graph.flows if f.on.year == year) + timedelta(days=2)
        tag = "" if year == years[0] else "@%d" % year
        if p2_relief(graph, loc, ces, year, P, post, bound, force, plan_ticks, ex_ante, applied, law):
            continue                                            # top-up deemed nil (s19(4), s20(2); Art 5.5.1, Sch 61 s4)
        income = {e.id: p2_income(graph, e, year, P, labels) for e in ces}
        unknown = [e for e in ces if income[e.id] is None]
        if unknown:                                             # the jurisdiction's top-up is unbounded without them; the
            for e in unknown:                                   # scope question, when open, comes first
                post(("data.p2_income", e.id), frozenset({Need(DATA, k) for k in p2_income_needs(graph, e, year, P)} | scope))
            continue
        net = sum(income.values())                              # s16(2), s17(1) B; Art 5.1.2
        attrs = {"p2_year": year, "p2_net": round(net, 2)}
        if net <= 0:
            act = {e.id: None if p2_other(e) is None else p2_tax(labels or {}, graph, e.id, year, P) + p2_other(e) for e in ces}
            extra = p2_additional(graph, loc, ces, income, net, act, P, post, bound, force, plan_ticks, ex_ante, on, tag, attrs, law)
            yield year, tag, on, attrs, [(f.payer, f.amount, f.attrs) for f in extra]
            continue
        excess = max(0.0, net - p2_sbie(ces, year, P, post, bound, force, law))     # s16(6); Art 5.2.2
        positive = {k: v for k, v in income.items() if v > 0}
        yield year, tag, on, attrs, [(e.id, round(excess * positive[e.id] / sum(positive.values()), 2), dict(attrs))
                                     for e in ces if e.id in positive]


def iir_entities(graph: Graph, loc):
    """口径 D20. The constituent entities whose top-up an IIR computes in loc: those located there, less any that is a
    Mainland resident only by its place of effective management (a residence variant) — such a company is taxed on its
    worldwide income at the statutory 25% (EIT Law art 3, 4), above the minimum rate, while the covered taxes the case
    states for it are those of its home jurisdiction; it brings no top-up into charge."""
    return [e for e in p2_entities(graph, loc) if not e.attrs.get("resident_by_pem")]


def p2_parents(graph: Graph, P):
    """口径 D20. The parent entities that apply an income inclusion rule, with the share of each low-taxed constituent
    entity they bring into charge (HK GloBE Art 2.1-2.3, Sch 60; SG MEMTA s12-s14). The qualified-IIR jurisdictions are
    those the OECD central record lists (Hong Kong, Singapore; the Mainland has none). The ultimate parent applies it
    when located in one; otherwise each intermediate parent located in one that no parent above it in one controls
    (Art 2.1.2-2.1.3; s13(2)); a partially-owned parent (more than 20% held outside the group) located in one applies
    it in its own right unless wholly owned by another that does (Art 2.1.4-2.1.5; s13(3)). A parent brings into
    charge only entities outside its own jurisdiction (Art 2.1.6; s11(2)). Inclusion ratio: the parent's share of the
    entity through the holding chain (Art 2.2.2), less what a lower applying parent already brings in (Art 2.3; s14(2)).
    Returns {parent id: {entity id: inclusion %}}."""
    members = graph.group()
    qualified = {j for j, pid in P2_IIR.items() if pid in P.rows and P[pid]}
    held = {h.held for h in graph.holds if h.holder in members}
    ents = [e for e in graph.entities.values() if e.id in members]
    parent = lambda e: any(h.holder == e.id for h in graph.holds)
    group_share = lambda e: sum(h.ratio for h in graph.holds if h.held == e.id and h.holder in members)
    applying = set()
    for upe in (e for e in ents if e.id not in held):
        if upe.loc in qualified:
            applying.add(upe.id)
            continue
        for e in ents:
            if e.id != upe.id and e.loc in qualified and parent(e) and graph.chain_ratio(upe.id, e.id) > 0 and not any(
                    x.id != e.id and x.loc in qualified and graph.chain_ratio(x.id, e.id) > 50.0 for x in ents):
                applying.add(e.id)
    popes = [e for e in ents if e.id in held and e.loc in qualified and parent(e) and group_share(e) < 80.0]
    for e in popes:
        if not any(x.id != e.id and x in popes and graph.chain_ratio(x.id, e.id) >= 100.0 - 1e-9 for x in popes):
            applying.add(e.id)
    out = {}
    for r in sorted(applying):
        loc = graph.entities[r].loc
        for e in ents:
            if e.loc == loc or e.id == r or graph.chain_ratio(r, e.id) <= 0 or e.attrs.get("resident_by_pem"):
                continue
            share = graph.chain_ratio(r, e.id) - sum(graph.chain_ratio(r, x) * graph.chain_ratio(x, e.id) / 100.0
                                                       for x in applying if x != r and graph.chain_ratio(r, x) > 0)
            if share > 1e-9:
                out.setdefault(r, {})[e.id] = round(share, 6)
    return out


def p2_flows(graph: Graph, P, needs=None, bound=None, force=None, labels=None, plan_ticks=None, ex_ante=True):
    """口径 D14, D16 — 范围.md 9. The top-up is a jurisdiction's, for a financial year (MMT Act s16-s18 applied to the
    DTT by s30; GloBE Art 5.1-5.3 applied to the HKMTT by Sch 62), computed by p2_shares; each entity's share rides on
    a pseudo-flow p2:<entity>. Financial years: the calendar years the modelled flows fall in (the convention the SBIE
    transition rates use); the first year's pseudo-flows carry no year, later ones @<year>, as recurring flows are
    named. labels: the real flows' labels of this pass (covered taxes). Dated after the year's last real flow.
    口径 D20 — the income inclusion rule: for a parent that applies one (p2_parents), the top-up of a jurisdiction
    without a domestic top-up of its own in the model (the Mainland) is computed under the parent's law, and the
    parent's allocable share of each entity's share (Art 2.2.1; s15) rides on a pseudo-flow iir:<entity>><parent> that
    the parent pays itself — the parent's tax, in its own jurisdiction. Hong Kong and Singapore entities need none:
    their domestic top-ups are qualified with the safe harbour (OECD central record; Sch 61 Pt 3 Div 4), so no IIR
    top-up remains for them (Art 5.2.3)."""
    out = []
    years = sorted({f.on.year for f in graph.flows})
    bound, force = bound or FLOOR, force or {}

    def post(grp, need):
        if needs is not None:
            needs[grp] = need

    if not years:
        return out
    for loc in sorted(P2_JURISDICTIONS):
        ces = p2_entities(graph, loc)
        if not ces:
            continue
        for year, tag, on, attrs, shares in p2_shares(graph, loc, loc, ces, years, P, post, bound, force, labels, plan_ticks, ex_ante):
            out.extend(FlowEdge("p2:%s%s" % (eid, tag), eid, eid, TOPUP, amount, on, attrs=dict(a)) for eid, amount, a in shares)
    for r, held in sorted(p2_parents(graph, P).items()):
        law = graph.entities[r].loc
        for loc in sorted({graph.entities[e].loc for e in held} - set(P2_JURISDICTIONS)):
            ces = iir_entities(graph, loc)
            first = P.rows[P2_RATE[law]]["effective_from"]                 # the IIR applies from the same year (s26AE(6); s8)
            ys = [y for y in years if "%d-01-01" % y >= first]
            if not ys:
                continue
            for year, tag, on, attrs, shares in p2_shares(graph, loc, law, ces, ys, P, post, bound, force, labels, plan_ticks, ex_ante):
                for eid, amount, a in shares:
                    if eid in held:
                        out.append(FlowEdge("iir:%s>%s%s" % (eid, r, tag), r, r, TOPUP, round(amount * held[eid] / 100.0, 2), on,
                                            attrs=dict(a, p2_iir=True, p2_jur=loc, p2_entity=eid)))
    return out


def p2_cmp(graph: Graph, ces, fields, test):
    """Tri of test(*values) over group facts: unknown ones pending, a conflict asked (口径 D12)."""
    vals, needs = [], set()
    for f in fields:
        v = group_fact(graph, ces[0], f)
        if v is None or v == "conflict":
            needs.add(Need(DATA if v == "conflict" else MISSING, "group.%s" % f))
        vals.append(v)
    return Tri(U, frozenset(needs)) if needs else tri(test(*vals))


def p2_election(graph: Graph, loc, ces, field_, P, post, bound, force, plan_ticks, ex_ante):
    """A filing entity's election: the group's statement; else ex ante the plan's action (each of these elections only
    ever lowers the tax), ex post a fact pending."""
    v = group_fact(graph, ces[0], field_)
    if v is not None and v != "conflict":
        return bool(v)
    n = Need(PLAN, "group.%s:elect" % field_) if ex_ante and v is None else Need(MISSING if v is None else DATA, "group.%s" % field_)
    if n in (plan_ticks or {}):
        return bool(plan_ticks[n])
    grp = ("data.%s" % field_, loc)
    post(grp, frozenset({n}))
    return decide(Tri(U, frozenset({n})), True, bound, grp, force)


def p2_tcsh(graph: Graph, loc, ces, year, P, sbie, applied, law=None):
    """口径 D17. Transitional CbCR safe harbour, for a financial year (Singapore regs 69-74 under s20; Hong Kong Sch 61
    Pt 3 ss 2, 4, 6-8, 14): a year of the transition period (the calendar year as the financial year), a qualified CbC
    report for the jurisdiction, the safe harbour applied in every earlier year the rules applied (once out, always
    out: the model's own earlier years, else the group's statement), and one of three tests on the CbC report figures:
    de minimis (revenue < EUR 10m and profit before tax < EUR 1m or a loss), simplified ETR (simplified covered taxes /
    profit before tax at least 16% for a year beginning in 2025, 17% in 2026), routine profits (profit before tax not
    above the substance-based income exclusion, or a loss). EUR comparisons through the year's rate — the average
    reference rate for December of the calendar year before the financial year (Singapore reg 9; OECD Commentary ch.1
    paras 19.2, 20.1, which Hong Kong s26AF follows): p2_eur_rate_<year>; the group's p2_eur_rate serves the first
    modelled year only, a later year's rate is a datum of its own. Hong Kong and Singapore have no eligible
    distribution tax system: reg 70(1)(d) holds. law: whose rules
    test the jurisdiction (its own for the domestic top-up; the parent's for an IIR, 口径 D20)."""
    law = law or loc
    pre, sfx = P2_PRE[law], "_" + loc.lower()
    begins = P.rows[P2_RATE[law]]["effective_from"]                       # the first financial year the rules apply to
    start_from = P[pre + "tcsh_fy_start_from"] if (pre + "tcsh_fy_start_from") in P.rows else begins
    if not (start_from <= "%d-01-01" % year <= P[pre + "tcsh_fy_start_to"] and "%d-12-31" % year <= P[pre + "tcsh_fy_end_by"]):
        return Tri(F)
    if year - 1 in applied:
        history = tri(applied[year - 1])
    elif "%d-01-01" % year <= begins:
        history = Tri(T)
    else:
        history = p2_cmp(graph, ces, ["p2_tcsh_history" + sfx], bool)
    qualified = p2_cmp(graph, ces, ["p2_qualified_cbcr" + sfx], bool)
    rev, pbt, taxes = "p2_cbcr_revenue" + sfx, "p2_cbcr_pbt" + sfx, "p2_cbcr_simplified_taxes" + sfx
    rate = "p2_eur_rate_%d" % year
    if not applied and group_fact(graph, ces[0], rate) is None:
        rate = "p2_eur_rate"                                              # the first modelled year: the group's rate
    de_minimis = p2_cmp(graph, ces, [rev, pbt, rate], lambda r, b, x: float(r) * float(x) < P[pre + "tcsh_dm_revenue_max"]
                        and float(b) * float(x) < P[pre + "tcsh_dm_pbt_max"])
    simplified = p2_cmp(graph, ces, [taxes, pbt], lambda t, b: float(b) > 0 and 100.0 * float(t) / float(b) >= P[pre + "tcsh_etr_%d" % year])
    routine = OR(p2_cmp(graph, ces, [pbt], lambda b: float(b) <= 0), p2_cmp(graph, ces, [pbt], lambda b: float(b) <= sbie()))
    return AND(qualified, history, OR(de_minimis, simplified, routine))


def p2_dm(graph: Graph, ces, loc, P, law=None):
    """口径 D17. De minimis exclusion (Singapore s19(1); Hong Kong GloBE Art 5.5.1-5.5.3): the jurisdiction's average
    revenue below EUR 10m and average GloBE income or loss below EUR 1m (or a loss), each over the year and the two
    before it — the group's averages, in EUR."""
    pre, sfx = P2_PRE[law or loc], "_" + loc.lower()
    return p2_cmp(graph, ces, ["p2_dm_avg_revenue_eur" + sfx, "p2_dm_avg_income_eur" + sfx],
                  lambda r, i: float(r) < P[pre + "dm_revenue_max"] and float(i) < P[pre + "dm_income_max"])


def p2_relief(graph: Graph, loc, ces, year, P, post, bound, force, plan_ticks, ex_ante, applied, law=None):
    """口径 D17. The jurisdiction's top-up for the year is nil when the filing entity elects a relief it is eligible for:
    the transitional CbCR safe harbour (s20(2); Sch 61 s4) or the de minimis exclusion (s19(4); Art 5.5.1). Each
    election is the filing entity's (p2_election). Eligibility the data leave open is pending; a relief known not to
    be available asks nothing. applied[year]: whether the safe harbour applied (for the later years' once-out test)."""
    sb = {}

    def sbie():
        if "v" not in sb:
            sb["v"] = p2_sbie(ces, year, P, post, bound, force, law)
        return sb["v"]

    sfx = "_" + loc.lower()
    for kind, test in (("tcsh", lambda: p2_tcsh(graph, loc, ces, year, P, sbie, applied, law)), ("dm", lambda: p2_dm(graph, ces, loc, P, law))):
        t = test()
        ok = t.v != F
        if t.v == U:
            grp = ("data.p2_%s" % kind, loc)
            post(grp, t.needs)
            ok = decide(t, True, bound, grp, force)
        elect = ok and p2_election(graph, loc, ces, "p2_%s_elected%s" % (kind, sfx), P, post, bound, force, plan_ticks, ex_ante)
        if kind == "tcsh":
            applied[year] = elect
        if elect:
            return True
    return False


def p2_sbie(ces, year, P, post, bound, force, law=None):
    """The jurisdiction's substance-based income exclusion (s16(6) O, s18; Art 5.2.2, 5.3.1): its constituent entities'
    carve-outs summed, a loss-making entity's included. An entity's unknown payroll or assets leave the exclusion
    without an upper limit: the favourable end lets it cover the net income, the other end counts the known parts.
    A company the plan creates has no payroll or assets beyond what the case states for it (口径 D16)."""
    total, unbounded = 0.0, False
    for e in ces:
        if e.attrs.get("sbie") is not None:
            total += float(e.attrs["sbie"])
            continue
        parts = sbie_parts(e, year, P, law)
        missing = sorted(k for k, v in parts.items() if v is None)
        if missing and not e.attrs.get("created_by_plan"):
            grp = ("data.p2_sbie", e.id)
            need = frozenset(Need(MISSING, "%s.%s" % (e.id, k)) for k in missing)
            post(grp, need)
            unbounded = decide(Tri(U, need), True, bound, grp, force) or unbounded
        total += sum(v for v in parts.values() if v is not None)
    return float("inf") if unbounded else total


def p2_additional(graph, loc, ces, income, net, act, P, post, bound, force, plan_ticks, ex_ante, on, tag, attrs, law=None):
    """口径 D15. A jurisdiction without net GloBE income: adjusted covered taxes below zero and below 15% of the net loss
    leave an additional current top-up equal to the difference (MMT Act s21(1); GloBE Art 4.1.5) — the jurisdictional
    top-up then (s16(4) J; Art 5.2.3), shared among the entities whose own covered taxes fall short: Singapore
    s16(3)(a) A x D / E, D = 15% of a loss-making entity's GloBE loss less its negative covered taxes; Hong Kong
    Art 5.4.3, pro rata (GloBE income or loss x minimum rate) - adjusted covered taxes over the entities whose negative
    covered taxes are below that product. Covered taxes can be negative without limit, so unknown ones are asked for.
    Singapore s21(2): under the filing entity's election only the part attributable to the carry back of losses stays
    in the year; the rest becomes negative tax carried forward (s17(4): later years, outside the horizon, at most the
    same amount). The regulations (S 1062/2024) say nothing on the attribution: the part is the group's datum, between
    none and all of it while unknown. Each entity's share rides on a pseudo-flow of share / minimum rate — the GloBE
    income Art 5.4.3 deems — charged in full. No entity sharing (both keys nil): no text allocates it; the authority's
    reading decides between none and all of it."""
    law = law or loc
    unknown = [e for e in ces if act[e.id] is None]
    if unknown:
        post(("data.p2_taxes", loc), frozenset(Need(DATA, "%s.covered_taxes_other" % e.id) for e in unknown))
        return []
    m = P[P2_RATE[law]] / 100.0
    total = sum(act.values())
    if not (total < 0 and total < m * net):
        return []
    extra = m * net - total                                     # s21(1): 15% of A less B, as a positive amount
    if law == "SG":
        key = {k: 0.0 if income[k] > 0 or act[k] >= 0 else max(0.0, m * income[k] - act[k]) for k in act}   # s16(3)(a) D
        elect = p2_election(graph, loc, ces, "p2_negative_tax_election", P, post, bound, force, plan_ticks, ex_ante)   # s21(2)
        if elect:
            cb = group_fact(graph, ces[0], "p2_carry_back_topup")
            if cb is not None and cb != "conflict":
                extra = min(extra, max(0.0, float(cb)))
            else:
                grp = ("data.p2_carry_back", loc)
                need = frozenset({Need(MISSING if cb is None else DATA, "group.p2_carry_back_topup")})
                post(grp, need)
                extra = 0.0 if decide(Tri(U, need), True, bound, grp, force) else extra
    else:
        key = {k: income[k] * m - act[k] if act[k] < 0 and act[k] < income[k] * m else 0.0 for k in act}   # Art 5.4.3
    if extra <= 0:
        return []
    if sum(key.values()) <= 0:
        grp = ("data.p2_allocation", loc)
        need = frozenset({Need(DISCRETION, "%s.p2_additional_allocation" % ces[0].id)})
        post(grp, need)
        if decide(Tri(U, need), True, bound, grp, force):
            return []
        key = {k: -v for k, v in act.items() if v < 0}         # carried by the entities with negative covered taxes
    return [FlowEdge("p2:%s%s" % (e.id, tag), e.id, e.id, TOPUP, round(extra * key[e.id] / sum(key.values()) / m, 2), on,
                     attrs=dict(attrs, p2_additional=True)) for e in ces if key.get(e.id, 0.0) > 0]


def sbie_parts(entity, year, P, law=None):
    """Substance-based income exclusion: payroll x rate + tangible assets x rate, the rates replaced during the
    transition period by the year's values — each jurisdiction's own enactment: Hong Kong GloBE Art 5.3.3, 5.3.4,
    9.2.1, 9.2.2; Singapore MMT Act s18 with the Second Schedule (口径 D13). An unknown base: None. law: whose rules
    compute (the parent's under an IIR, 口径 D20)."""
    pre = P2_PRE.get(law or entity.loc, "p2.")

    def rate(base_pid, table_pid):
        table = dict(kv.split(":") for kv in str(P.rows[table_pid]["value"]).split(";"))
        return float(table.get(str(year), P[base_pid]))
    out = {}
    for k, base, table in (("payroll", "sbie_payroll_rate", "sbie_payroll_transition"),
                           ("tangible_assets", "sbie_tangible_rate", "sbie_tangible_transition")):
        v = entity.attrs.get(k)
        out[k] = None if v is None else float(v) * rate(pre + base, pre + table) / 100.0
    return out


PEM_RULE = "cn.residence.pem"
PEM_CRITERIA = ("senior_management_in_cn", "financial_hr_decisions_in_cn", "records_in_cn", "directors_majority_in_cn")


def pem_candidates(graph: Graph, P):
    """国税发〔2009〕82号 第二条: a company incorporated abroad, controlled from the Mainland, that meets the four criteria
    is a Mainland resident by place of effective management. Candidates: foreign-incorporated entities under Mainland
    control (>= the joint-control share) whose management seat is unknown (a missing fact) or stated in the Mainland
    and no criterion is stated false (the determination itself is the authority's, a judgement)."""
    out = {}
    parents = [e.id for e in graph.entities.values() if e.loc == "CN"]
    for e in graph.entities.values():
        if e.loc == "CN" or e.attrs.get("incorporated_in", e.loc) == "CN":
            continue
        chain = max((cfc_chain_ratio(graph, p, e.id) for p in parents), default=0.0)
        if chain <= 0:
            continue
        needs = set()
        if chain < P["cn.cfc.control_joint_min"]:                   # 82号: "主要控股投资者" names no share: a judgement below a majority
            needs.add(Need(DISCRETION, "%s.cn_main_controlling_investor" % e.id))
        managed = e.attrs.get("managed_from")
        if managed is None and e.attrs.get("placed_by_plan"):
            needs.add(Need(PLAN, "%s.managed_from:not_cn" % e.id))
        elif managed is None:
            needs.add(Need(MISSING, "%s.managed_from" % e.id))
        elif managed == "CN" and not any(e.attrs.get(k) is False for k in PEM_CRITERIA):
            needs.add(Need(DISCRETION, "%s.effective_management_in_cn" % e.id))
        else:
            continue                                                # managed elsewhere, or a criterion fails: no variant
        out[e.id] = frozenset(needs)
    return out


def residence_graph(graph: Graph, resident_in_cn):
    """The graph with the given entities treated as Mainland residents (their flows then meet Mainland rules, the
    credits for their foreign income included: 口径 D09)."""
    from dataclasses import replace
    ents = {k: (replace(v, loc="CN", attrs=dict(v.attrs, resident_by_pem=True, seat=v.loc)) if k in resident_in_cn else v)
            for k, v in graph.entities.items()}                   # 口径 D31: the seat stays for VAT and stamp duty
    return Graph(ents, graph.holds, graph.flows, graph.members)


def normalise(graph: Graph):
    """The graph as the rules see it: every liquidation / capital-reduction flow replaced by its parts, with the
    dividend part taken as stated or, when unknown, as nil (the engine evaluates the other candidates itself)."""
    flows = []
    for f in graph.flows:
        flows += split_variants(graph, f)[0] if f.income in SPLIT_INCOMES else [f]
    return Graph(graph.entities, graph.holds, flows, graph.members)


_FLOW_CACHE = {}
_CACHE_MAX = 300000


def _freeze(v):
    if isinstance(v, dict):
        return ("d",) + tuple(sorted(((k, _freeze(x)) for k, x in v.items()), key=lambda kv: repr(kv[0])))
    if isinstance(v, (set, frozenset)):
        return ("s",) + tuple(sorted(repr(x) for x in v))
    if isinstance(v, list):
        return ("l",) + tuple(_freeze(x) for x in v)
    return v


def _clone(res):
    import copy
    items = []
    for it in res.items:
        c = copy.copy(it)
        c.cites = list(it.cites)
        items.append(c)
    return FlowResult(items, list(res.applied), dict(res.groups), dict(res.deadlines), res.penalty,
                      dict(res.deadline_rules), dict(res.deadline_jur), res.rules, dict(res.gaps), dict(res.outside))


def cached_evaluate(rules, ctx, flow, bound, P, force, amount):
    """evaluate_flow, memoised (J1: a task's result depends only on what it reads). The key holds everything the
    evaluation reads: the rule set, the parameter set, the context's mode and answers, the flow's facts, the flow, the
    bound, the forced decisions that address this flow, and the amount. A hit returns a copy (callers annotate items)."""
    tok = (id(rules), getattr(P, "token", id(P)), type(ctx).__name__, getattr(ctx, "mode", None),
           frozenset(getattr(ctx, "adjustable", ()) or ()), frozenset((ctx.ticks or {}).items()))
    facts_key = tuple(sorted(((k, _freeze(v)) for k, v in ctx.facts.items()), key=lambda kv: kv[0]))
    fkey = (flow.payer_loc, flow.payee_loc, flow.income, flow.on, flow.target_loc, flow.indirect_cn, flow.id,
            flow.payer_seat, flow.payee_seat, flow.target_seat)          # 口径 D31: what VAT and stamp duty match on
    rel = tuple(sorted((k, v) for k, v in (force or {}).items() if isinstance(k, tuple) and len(k) == 2 and k[1] == flow.id))
    key = (tok, facts_key, fkey, bound, rel, amount)
    hit = _FLOW_CACHE.get(key)
    if hit is None:
        hit = evaluate_flow(rules, ctx, flow, bound, P, force=force, amount=amount)
        if len(_FLOW_CACHE) >= _CACHE_MAX:
            _FLOW_CACHE.clear()
        _FLOW_CACHE[key] = hit
    return _clone(hit)


def flow_name(fid):
    """The case's flow name behind a label id: a split part "out.div" belongs to the flow "out"."""
    return fid.split(".", 1)[0]


def engine(graph: Graph, ctx_of, bound, force=None, P=None, rules=None, settled=None, as_at=None, closed=()):
    """ctx_of(facts) builds the Ctx for one flow (mode, ticks and adjustable set come from the caller).
    settled: flow name -> {jurisdiction: tax actually paid} (场景.md §8); as_at: the date clocks are judged against;
    closed: (flow name, jurisdiction) pairs the case declares final whatever the clocks say."""
    P = P or Params()
    rules = rules or RULES
    settled = settled or {}
    labels, groups, flows = {}, {}, {}
    ref, done, trace = None, set(), []     # the previous pass's labels; labels finished in this pass; what readers saw

    def pool():
        """Every label a reader may use now: finished in this pass, else as the previous pass ended (after every
        entity-level credit), else — in the first pass — as far as this pass has got."""
        if ref is None:
            return labels
        out_ = {k: (labels[k] if k in done else lb) for k, lb in ref.items()}
        for k, lb in labels.items():
            out_.setdefault(k, lb)
        return out_

    def visible(g, pool_):
        """What a reader of flow g sees: the real flows (a pseudo-flow carries no company's own tax), g excluded."""
        return {k: lb for k, lb in pool_.items() if k != g.id and lb.flow.income not in (CFC_INCLUSION, TOPUP)}

    plan_ticks = getattr(ctx_of({}), "ticks", None) or {}

    def borne(vw, eid, deductions=False):
        """Income tax the company bears on the flows in view: withheld on its receipts, charged where it sits."""
        return sum(lb.flow.amount * it.effective / 100.0 for lb in vw.values() for it in lb.items
                   if it.levy == "income" and (deductions or not it.deduction) and not it.deferred
                   and (lb.flow.payer if it.borne_by == "payer" else lb.flow.payee) == eid)

    def profit(x, vw, year=None):
        atp = graph.entities[x].attrs.get("after_tax_profit")
        return float(atp) if atp is not None else designed_profit(graph, vw, x, year)

    def tier_tax(x, vw, tiers, needs, year=None):
        """口径 D05, D06 — 125号 第五条, from the lowest tier up: the tax behind company x's after-tax profit — what it paid on its profits
        and investment income, plus what it bears through the dividends it received in view from a qualifying company
        of the next tier. The least value the data allow; `needs` collects the data that would raise it."""
        other = other_tax(graph.entities[x])
        if other is None:
            needs.add("%s.income_tax_other" % x)
        total = max(0.0, own_tax(vw, x) + (other or 0.0))
        for lb in vw.values():
            d, z = lb.flow, lb.flow.payer
            h = graph.holding(x, z)
            if d.payee != x or d.income != "DIVIDEND" or tiers.get(z) != tiers.get(x, 1) + 1 or h is None \
                    or h.ratio < P["cn.ftc.indirect_ratio_min"]:
                continue
            stated = d.attrs.get("underlying_tax_share")
            if stated is not None:                              # the case states the tax behind that dividend
                total += d.amount * float(stated) / 100.0
                continue
            atp_z = profit(z, vw, year)
            if atp_z is None:
                needs.update(profit_needs(graph, z))
            elif atp_z > 0:
                total += tier_tax(z, vw, tiers, needs, year) * d.amount / atp_z
        return total

    def underlying(g, facts, vw):
        """财税〔2009〕125号 第五条: a year's figures — the tax behind the dividend (tier_tax of the paying company for the
        year whose profit it distributes) times dividend / that year's after-tax profit, as % of the dividend. A stated
        company's figures are its stated year's; a company the plan creates distributes the year its resolution names,
        a plan action (the year with the most tax behind it) pending until the plan takes it. A datum missing anywhere
        down the tiers leaves the share pending — the least value it can take kept for the unfavourable end, the data
        named for the question. 口径 D07, D08."""
        if g.income not in ("DIVIDEND", CFC_INCLUSION) or graph.entities[g.payee].loc != "CN" \
                or graph.entities[g.payer].loc == "CN" or facts.get(("flow", "underlying_tax_share")) is not None:
            return                                          # only a foreign company's dividend to a Mainland resident
        if g.income != "DIVIDEND":
            years = [None]                                  # a CFC inclusion: the horizon's figures
        elif graph.entities[g.payer].attrs.get("created_by_plan"):
            years = sorted({f.on.year for f in graph.flows if f.on.year <= g.on.year})
        else:
            years = [g.on.year]
        tiers, shares, needs, unknown = cn_tiers(graph, g.payee, P), [], set(), False
        for y in years:
            vw_y = vw if y is None else {k: lb for k, lb in vw.items() if lb.flow.on.year == y}
            atp = profit(g.payer, vw_y, y)
            if atp is None:
                unknown = True
            elif atp > 0:
                shares.append(round(100.0 * tier_tax(g.payer, vw_y, tiers, needs, y) / atp, 6))
        if unknown:
            needs.update(profit_needs(graph, g.payer))
        if not shares:
            if needs:
                facts[("_needs", "flow.underlying_tax_share")] = tuple(sorted(needs))
            return
        share = shares[0]
        if max(shares) - min(shares) > 1e-9:                # the resolution names the year: the plan's action
            n = Need(PLAN, "flow:%s.distributed_profit_year:most_tax" % g.id)
            grp = ("cn.ftc.dividend_indirect", g.id + "#year")
            if n in plan_ticks:
                fav = bool(plan_ticks[n])
            else:
                groups[grp] = frozenset({n})
                fav = decide(Tri(U, frozenset({n})), True, bound, grp, force or {})
            share = max(shares) if fav else min(shares)
        if needs:
            facts[("flow", "underlying_tax_share_min")] = share
            facts[("_needs", "flow.underlying_tax_share")] = tuple(sorted(needs))
        else:
            facts[("flow", "underlying_tax_share")] = share

    def cfc_facts(g, facts, vw):
        """口径 D10. The foreign company's effective burden as the labels in view show it (what it bore on its receipts, as
        payee), its total profit, and whether it sits in a white-listed jurisdiction (国税函〔2009〕37号)."""
        if g.income != CFC_INCLUSION:
            return
        sub_ = graph.entities[g.payer]
        other = other_tax(sub_)
        tax = max(0.0, own_tax(vw, sub_.id) + (other or 0.0))      # the least it can be while `other` is unknown
        atp = profit(sub_.id, vw)
        pre_tax = atp + tax
        need = ("%s.income_tax_other" % sub_.id,) if other is None else ()
        if ("flow", "cfc_tax_burden_ratio") not in facts and pre_tax > 0:
            ratio = 100.0 * (100.0 * tax / pre_tax) / P["cn.eit.rate"]       # as % of the statutory rate
            if not need or ratio >= P["cn.cfc.low_tax_ratio"]:             # even the least burden is not low: settled
                facts[("flow", "cfc_tax_burden_ratio")] = round(ratio, 6)
            else:
                facts[("_needs", "flow.cfc_tax_burden_ratio")] = need
        if ("flow", "cfc_profit_total") not in facts:
            if not need or pre_tax >= P["cn.cfc.exempt_profit_max"]:       # even the least profit is not small: settled
                facts[("flow", "cfc_profit_total")] = round(pre_tax, 2)
            else:
                facts[("_needs", "flow.cfc_profit_total")] = need
        facts.setdefault(("flow", "cfc_whitelisted"), sub_.loc in str(P.rows["cn.cfc.whitelist"]["value"]).split(";"))
        facts.setdefault(("flow", "direct_ratio"), max((h.ratio for h in graph.holds if h.holder == g.payee and h.held == g.payer), default=0.0))

    def p2_facts(g, facts, vw):
        """口径 D14. The jurisdiction's ETR for a top-up pseudo-flow (s17; Art 5.1.1): the adjusted covered taxes of
        every constituent entity located there — what each bore on its flows here (income levy, deductions included)
        plus what it states outside this model — over their net GloBE income; nil when those taxes are negative
        (s17(3)). An additional current top-up's pseudo-flow carries its own amount (p2_additional)."""
        if g.income != TOPUP:
            return
        e = graph.entities[g.payer]
        if not g.attrs.get("p2_additional"):
            ces = iir_entities(graph, g.attrs["p2_jur"]) if g.attrs.get("p2_iir") else p2_entities(graph, e.loc)   # D20
            year, net = g.attrs["p2_year"], g.attrs["p2_net"]
            unknown = tuple(sorted("%s.covered_taxes_other" % x.id for x in ces if p2_other(x) is None))
            if unknown:                                         # unknown covered taxes: the ETR is pending, not computed on 0
                facts[("flow", "p2_etr_needs")] = unknown
            elif net > 0:                                       # 口径 D16: the year's covered taxes, excluded income's left out
                taxes = sum(p2_tax(vw, graph, x.id, year, P) + p2_other(x) for x in ces)
                facts.setdefault(("flow", "p2_etr"), round(100.0 * max(0.0, taxes) / net, 6))
        rev = group_fact(graph, e, "group_revenue_eur")
        facts.setdefault(("payee", "group_revenue_eur"), None if rev == "conflict" else rev)

    def final_of(name, res, paid):
        out = set()
        for jur in paid:
            clocks = [d for k, (_, d) in res.deadlines.items() if res.deadline_jur.get(k) == jur and d is not None]
            if (name, jur) in closed or (as_at is not None and clocks and all(as_at > d for d in clocks)):
                out.add(jur)
        return out

    def after_reorg(g, facts, vw):
        """口径 D18. What the restructuring step leaves for later flows. A later disposal of the stake HOLD took over (or
        of ULT's shares in HOLD): the Mainland basis is the transferor's original one when the step's Mainland tax was
        deferred as a special reorganisation (59号 §6(2) 1-2), else the consideration — every other jurisdiction's basis
        is the consideration. A dividend from OP to HOLD: whether the step was a special reorganisation of two parties
        in different places (公告2013年第72号 §8)."""
        for r in graph.flows:
            if not r.attrs.get("reorg_step") or r.id == g.id or r.id not in vw:
                continue
            special = any(it.jur == "CN" and it.levy == "income" and it.deferred for it in vw[r.id].items)
            if g.income == SHARE_TRANSFER and ((g.payee == r.payer and g.target == r.target) or (g.payee == r.payee and g.target == r.payer)):
                if special and r.attrs.get("cost_basis") is not None:
                    facts.setdefault(("flow", "cn_cost_basis"), float(r.attrs["cost_basis"]))
            if g.income == "DIVIDEND" and g.payer == r.target and g.payee == r.payer:
                facts[("flow", "reorg_special_applied")] = special
                facts[("flow", "reorg_same_residence")] = graph.entities[r.payer].loc == graph.entities[r.payee].loc

    def read(g, vw):
        """The flow's facts, with what the readers derive from the labels in view."""
        facts = facts_for(graph, g)
        after_reorg(g, facts, vw)
        underlying(g, facts, vw)
        cfc_facts(g, facts, vw)
        p2_facts(g, facts, vw)
        return facts

    def run(g):
        facts = read(g, visible(g, pool()))
        trace.append((g, dict(facts)))                           # the fixpoint test re-reads these with finished labels
        name = flow_name(g.id)
        paid = settled.get(name, {})
        if paid:
            facts[SETTLED] = frozenset(paid)
        res = cached_evaluate(rules, ctx_of(facts), flow_of(graph, g, facts), bound, P, force or {}, g.amount)
        final = final_of(name, res, paid) if paid else set()
        if final:                                             # second pass: the closed amounts stand before credits are computed
            amount = sum(x.amount for x in graph.flows if flow_name(x.id) == name) or g.amount
            facts[("flow", "_final")] = {jur: 100.0 * paid[jur] / amount for jur in final}
            res = cached_evaluate(rules, ctx_of(facts), flow_of(graph, g, facts), bound, P, force or {}, g.amount)
        return res

    def keep(g, res, extra_cites=()):
        src = source_of(graph, g)
        origin = graph.entities[g.target] if g.income == SHARE_TRANSFER and g.target else graph.entities[g.payer]
        src_seat = origin.attrs.get("seat") or src               # 口径 D31: where a levy's source is, by the seat
        fx = facts_for(graph, g)
        gross_up, vat_gross_up = bool(fx.get(("flow", "wht_borne_by_payer"))), bool(fx.get(("flow", "vat_borne_by_payer")))
        for it in res.items:
            it.cites.extend(extra_cites)
            if not it.deduction and ((gross_up and it.levy == "income" and it.jur == src)
                                     or (vat_gross_up and it.levy == "vat" and it.jur == src_seat)):
                it.bearer = "payer"                              # contract: the payer bears the withholding
        outside = {}
        for (jur, levy, bearer), v in res.outside.items():   # 口径 D30: who would bear the levy the library cannot compute
            if bearer == "payee" and ((gross_up and levy == "income" and jur == src) or (vat_gross_up and levy == "vat" and jur == src_seat)):
                bearer = "payer"
            outside[(jur, levy, g.payer if bearer == "payer" else g.payee)] = v
        name = flow_name(g.id)
        paid = dict(settled.get(name, {}))
        final = final_of(name, res, paid) if paid else set()
        groups.update(res.groups)                           # a closed item's pending facts stay when a credit elsewhere turns on them
        labels[g.id] = Label(res.items, [], 0.0, {k: v[1] for k, v in res.deadlines.items()}, flow=g,
                             deadline_jur=dict(res.deadline_jur), actual=paid, final=frozenset(final),
                             applied=[r.id for r in res.applied], gaps=dict(res.gaps), outside=outside)
        flows[g.id] = g

    def phase(edges):
        """Evaluates the edges in order; returns the flows kept (a split's parts stand in for the flow)."""
        before = set(flows)
        for f in edges:
            if f.income not in SPLIT_INCOMES:
                keep(f, run(f))
                continue
            runs = [[(g, run(g)) for g in variant] for variant in split_variants(graph, f)]
            chosen = runs[0]
            if len(runs) > 1:                              # the split is pending: the bound picks the extreme candidate
                group = (SPLIT_RULE[f.income], f.id)
                need = frozenset({Need(MISSING, "flow." + SPLIT_FACT)})
                fav = decide(Tri(U, need), True, bound, group, force or {})
                chosen = (min if fav else max)(runs, key=lambda rr: sum(label_tax(g, res.items) for g, res in rr))
                groups[group] = need
            for g, res in chosen:
                keep(g, res, (SPLIT_RULE[f.income],))
        return [flows[k] for k in flows if k not in before]

    def settled_reads():
        """Every reader, given this pass's finished labels, derives what it used."""
        for g, used in trace:
            if not _same(read(g, visible(g, labels)), used):
                return False
        return True

    # the real flows and their entity-level credits first; the pseudo-flows (CFC inclusion, top-up) then read the
    # taxes the entities bore after those credits (covered taxes, CFC burden), and get their own entity stage. A
    # reader early in a pass sees taxes before a later entity-level credit (a pooled credit cuts what an intermediate
    # company paid, after its dividend upward was read): the passes repeat until every reader sees finished taxes.
    for _pass in range(FIX_MAX):                           # 口径 D04
        labels, groups, flows, done, trace = {}, {}, {}, set(), []
        real = phase(topo_order(graph.flows))
        entity_stage(Graph(graph.entities, graph.holds, list(flows.values()), graph.members), ctx_of, bound, force, P, rules, labels, groups, only=real)
        done = set(labels)
        data_needs = {}
        for f in graph.flows:                              # 口径 D18 / D19: a step's amount, unknown: its tax is unbounded
            if f.attrs.get("amount_unknown"):
                data_needs[("data.amount", f.id)] = frozenset({Need(DATA, "flow:%s.amount" % f.id)})
        pseudo = phase(topo_order(cfc_flows(graph, P, data_needs, labels) + p2_flows(
            graph, P, data_needs, bound, force, labels=labels, plan_ticks=plan_ticks,
            ex_ante=getattr(ctx_of({}), "mode", EX_ANTE) == EX_ANTE)))
        groups.update(data_needs)
        whole = Graph(graph.entities, graph.holds, list(flows.values()), graph.members)
        entity_stage(whole, ctx_of, bound, force, P, rules, labels, groups, only=pseudo)
        for name in {flow_name(fid) for fid in labels}:    # closed items keep what was paid, spread over a split's parts
            parts_ = [lb for fid, lb in labels.items() if flow_name(fid) == name]
            amount = sum(lb.flow.amount for lb in parts_)
            for jur in set.union(set(), *(set(lb.final) for lb in parts_)):
                rate = 100.0 * parts_[0].actual[jur] / amount if amount else 0.0
                for lb in parts_:
                    mine = [it for it in lb.items if it.jur == jur and not it.deduction]
                    if not mine:
                        lb.items.append(TaxItem(jur, 0.0, 0.0, cites=["settled"]))
                        mine = lb.items[-1:]
                    if any(it.actual is not None for it in mine):
                        continue                              # already fixed in the second pass
                    for i, it in enumerate(mine):
                        it.actual = rate if i == 0 else 0.0
        if settled_reads():
            break
        ref = labels
    else:
        raise Defect("the taxes companies bear do not settle across the entity stages in %d passes" % FIX_MAX)
    graph = whole
    members = graph.group()
    total = 0.0
    for fid, lb in labels.items():
        f = flows[fid]
        lb.tax = label_tax(f, lb.items)
        lb.cites = sorted({c for it in lb.items for c in it.cites})
        total += label_tax(f, [it for it in lb.items if (f.payer if it.borne_by == "payer" else f.payee) in members])
    check_citations(labels)
    check_invariants(labels)
    return round(total, 2), groups, labels


FIX_MAX = 8                                                 # passes: a chain of credits longer than this is a Defect


def _same(a, b, tol=1e-6):
    """Two fact dicts equal, numbers within tol."""
    if a.keys() != b.keys():
        return False
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
    return all(abs(x - b[k]) <= tol if num(x) and num(b[k]) else x == b[k] for k, x in a.items())


def check_citations(labels):
    for fid, lb in labels.items():
        for it in lb.items:
            if it.effective != 0 and not it.cites and it.actual is None:
                raise Defect("tax without a rule behind it: %s" % fid)


def check_invariants(labels):
    for fid, lb in labels.items():
        for it in lb.items:
            if it.deduction:
                continue
            if it.rate < 0 or it.rate > it.charge_rate + 1e-9:
                raise Defect("rate above the domestic charge: %s" % fid)
            if it.credit > it.rate * it.base_share + 1e-9:
                raise Defect("credit above the tax it relieves: %s" % fid)


def pem_answered(pem, ticks):
    """Answers that settle a Mainland residence by effective management: (entities known not resident, known resident)."""
    out_, in_ = set(), set()
    for eid, needs in pem.items():
        for n in needs:
            v = (ticks or {}).get(n)
            if v is None:
                continue
            if n.source == PLAN and n.key.endswith("managed_from:not_cn") and v:
                out_.add(eid)
            elif n.key.endswith("effective_management_in_cn"):
                (in_ if v else out_).add(eid)
            elif n.key.endswith("cn_main_controlling_investor") and not v:
                out_.add(eid)
    return out_, in_ - out_


NONMONO_MAX = 8                                            # beyond this many joint decisions: Defect, never a silent shortcut


def nonmonotone(g):
    """A decision whose favourable end is not fixed by the rule: an ambiguous recharacterisation or a split."""
    if g[0] in SPLIT_RULE.values():
        return True
    r = RULES_BY_ID.get(g[0])
    return bool(r is not None and r.ambiguous)


def _split(g, ctx_of, bound, kw, base_force, nm, f0):
    """The decisions that interact, in parts: the decisions of one flow always together (a charge and the exemptions
    that gate it act only jointly — three gates no two of which move anything alone), then x and y interact when taking
    both the other way does not move the total by the sum of taking each alone (the four corners of the pair, from the
    base run)."""
    other = "unfav" if bound == FLOOR else "fav"
    alone = {x: engine(g, ctx_of, bound, force={**base_force, x: other}, **kw)[0] for x in nm}
    parent = {x: x for x in nm}

    def root(x):
        while parent[x] != x:
            x = parent[x]
        return x
    flows = {}
    for x in nm:
        if isinstance(x[1], str) and x[1] not in JURISDICTION_CODES:
            flows.setdefault(x[1].split(".", 1)[0], []).append(x)
    for xs in flows.values():
        for y in xs[1:]:
            parent[root(y)] = root(xs[0])
    for i, x in enumerate(nm):
        for y in nm[i + 1:]:
            both = engine(g, ctx_of, bound, force={**base_force, x: other, y: other}, **kw)[0]
            if abs(both - alone[x] - alone[y] + f0) > 1e-6:
                parent[root(x)] = root(y)
    parts = {}
    for x in nm:
        parts.setdefault(root(x), []).append(x)
    return list(parts.values())


def extreme(g, ctx_of, bound, kw, base_force=None, extra=()):
    """engine() at one bound, with the non-monotone decisions enumerated jointly: the least (FLOOR) or greatest
    (CEILING) group total over all their combinations. `extra`: groups found non-monotone by bounds() — enumerated
    whether this run reaches them or not (a decision may surface only in some branch). Beyond NONMONO_MAX decisions
    they are split by pairwise interaction (_split); each part is enumerated with the rest as in the base run, and the
    parts' best choices are run together: that total must be what the parts add up to, else the decisions interact
    beyond pairs and the bound is Undecidable — never a silent shortcut. Returns (run, chosen forces)."""
    from itertools import product as _product
    base_force = dict(base_force or {})
    run = engine(g, ctx_of, bound, force=base_force or None, **kw)
    is_nm = lambda x: nonmonotone(x) or x in extra
    better = (lambda a, b: a < b - 1e-9) if bound == FLOOR else (lambda a, b: a > b + 1e-9)
    seen = set()
    nm = sorted(({x for x in run[1] if is_nm(x)} | set(extra)) - set(base_force), key=str)
    best, best_force = run, dict(base_force)
    while nm:
        seen |= set(nm)
        parts = [nm] if len(nm) <= NONMONO_MAX else _split(g, ctx_of, bound, kw, base_force, nm, run[0])
        if any(len(part) > NONMONO_MAX for part in parts):
            raise Undecidable("too many joint decisions to enumerate exactly: %d" % max(len(part) for part in parts),
                              {x: best[1].get(x, run[1].get(x, frozenset())) for x in nm})
        def enum(part):
            p_best, p_force = None, None
            for combo in _product(("fav", "unfav"), repeat=len(part)):
                r_ = engine(g, ctx_of, bound, force={**base_force, **dict(zip(part, combo))}, **kw)
                if p_best is None or better(r_[0], p_best[0]):
                    p_best, p_force = r_, dict(zip(part, combo))
            return p_force, p_best[0]

        solved = [(part,) + enum(part) for part in parts]
        while True:
            fz = {**base_force, **{k: v for _, ch, _ in solved for k, v in ch.items()}}
            r = engine(g, ctx_of, bound, force=fz, **kw)
            if len(solved) == 1 or abs(r[0] - (run[0] + sum(t - run[0] for _, _, t in solved))) <= 1e-6:
                break                                     # the parts add up: their best choices together are the bound
            merge = None                                  # parts whose best choices interact (more than pairwise from
            for i in range(len(solved)):                  # the base run showed): merged and enumerated together
                for j in range(i + 1, len(solved)):
                    both = engine(g, ctx_of, bound, force={**base_force, **solved[i][1], **solved[j][1]}, **kw)[0]
                    if abs(both - solved[i][2] - solved[j][2] + run[0]) > 1e-6:
                        merge = (i, j)
                        break
                if merge:
                    break
            if merge is None:
                merge = (0, 1) if len(solved) == 2 else None
            joined = solved[merge[0]][0] + solved[merge[1]][0] if merge else [x for part, _, _ in solved for x in part]
            if len(joined) > NONMONO_MAX:
                raise Undecidable("too many interacting decisions to enumerate exactly: %d of %d" % (len(joined), len(nm)),
                                  {x: best[1].get(x, run[1].get(x, frozenset())) for x in nm})
            rest = [t for k, t in enumerate(solved) if not merge or k not in merge]
            solved = rest + [(joined,) + enum(joined)] if merge else [(joined,) + enum(joined)]
        if better(r[0], best[0]):
            best, best_force = r, fz
        more = [x for x in best[1] if is_nm(x) and x not in seen and x not in base_force]   # decisions that only
        nm = sorted(seen | set(more), key=str) if more else []                                     # appear in some branch
    return best, best_force


def bounds(graph: Graph, ctx_of, P=None, settled=None, as_at=None, closed=(), ticks=None, force=None) -> Bounds:
    """Two bounds over every residence variant (范围.md 6): with k entities whose Mainland residence is undetermined, the
    floor is the least total over the 2^k variants and the ceiling the greatest; each such entity is a pending group
    whose cost is the floor's rise when its residence is decided the other way."""
    P = P or Params()
    kw = dict(P=P, settled=settled, as_at=as_at, closed=closed)
    pem = pem_candidates(graph, P)
    out_, in_ = pem_answered(pem, ticks)
    pem = {e: ns for e, ns in pem.items() if e not in out_ and e not in in_}
    ids = sorted(pem)
    subsets = [frozenset(c) for k in range(len(ids) + 1) for c in combinations(ids, k)]
    extra = set()                                         # groups found non-monotone: enumerated jointly from then on
    for _attempt in range(NONMONO_MAX + 1):
        runs = {}
        for s in subsets:
            s_all = s | frozenset(in_)
            g = residence_graph(graph, s_all) if s_all else graph
            (r_lo, f_lo), (r_hi, f_hi) = extreme(g, ctx_of, FLOOR, kw, force, extra), extreme(g, ctx_of, CEILING, kw, force, extra)
            runs[s] = (r_lo, r_hi, g, f_lo, f_hi)
        s_lo = min(subsets, key=lambda s: runs[s][0][0])
        s_hi = max(subsets, key=lambda s: runs[s][1][0])
        (lo, groups, L_lo), g_lo, force_lo = runs[s_lo][0], runs[s_lo][2], runs[s_lo][3]
        (hi, groups_hi, L_hi), g_hi, force_hi = runs[s_hi][1], runs[s_hi][2], runs[s_hi][4]
        found = set()
        both = {**groups_hi, **groups}                    # a group pending only in the ceiling's run is tested at the floor too
        open_ = [g for g in both if not (g in extra or nonmonotone(g) or all(n.source == DATA for n in both[g]) or g in (force or {}))]

        def moves(gs):
            """Taking these decisions the other way together lowers the floor or raises the ceiling."""
            return (engine(g_lo, ctx_of, FLOOR, force={**force_lo, **{x: "unfav" for x in gs}}, **kw)[0] < lo - 1e-9
                    or engine(g_hi, ctx_of, CEILING, force={**force_hi, **{x: "fav" for x in gs}}, **kw)[0] > hi + 1e-9)

        for g in open_:
            if moves((g,)):
                found.add(g)
        if not found:                                     # two gates of one flow's items, flipped together: judgements that
            by_flow = {}                                  # only jointly let a charge in, a deduction with its charge — the
            for g in open_:                               # pairs first, so only the decisions that matter join
                by_flow.setdefault(g[1], []).append(g)
            for gs in by_flow.values():
                if len(gs) < 2 or not moves(gs):              # the flow's decisions together move nothing: nothing joint here
                    continue
                pairs = [set(c) for c in combinations(gs, 2) if moves(c)] if len(gs) > 2 else [set(gs)]
                found |= set().union(*pairs) if pairs else set(gs)
        if not found and lo > hi + 1e-9:                  # the ceiling's own run is cheaper: decisions interact across flows —
            pairs = [set(c) for c in combinations(open_, 2) if moves(c)]          # a pair that shows it, else all of them
            found = set().union(*pairs) if pairs else set(open_)                   # (beyond NONMONO_MAX: Undecidable, asked)
        if not found:
            break
        extra |= found
    else:
        raise Undecidable("non-monotone interactions keep appearing: %s" % sorted(extra),
                          {x: groups.get(x, groups_hi.get(x, frozenset())) for x in extra})
    groups = dict(groups)
    for g_, ns in groups_hi.items():                     # what is pending in the ceiling's run is pending too: the
        groups[g_] = groups.get(g_, frozenset()) | ns     # guaranteed tax turns on it (its floor cost may be nil)
    for h in graph.holds:
        if h.unknown:
            groups[("data.holding", "%s>%s" % (h.holder, h.held))] = frozenset(
                Need(DATA, "hold:%s>%s.%s" % (h.holder, h.held, a)) for a in h.unknown)
    if lo > hi + 1e-9:
        raise Defect("floor above ceiling: %s > %s" % (lo, hi))
    cost = {}
    for g in groups:
        if all(n.source == DATA for n in groups[g]):
            continue                                            # nothing to decide: the datum must be asked
        if nonmonotone(g) or g in extra:                        # a joint decision: the floor with it taken the other way
            other = "unfav" if force_lo.get(g, "fav") == "fav" else "fav"
            cost[g] = round(extreme(g_lo, ctx_of, FLOOR, kw, {**(force or {}), g: other}, extra)[0][0] - lo, 2)
            continue
        cost[g] = round(engine(g_lo, ctx_of, FLOOR, force={**force_lo, g: "unfav"}, **kw)[0] - lo, 2)   # losing this group
    for eid in ids:
        groups[(PEM_RULE, eid)] = pem[eid]
        flipped = [s for s in subsets if (eid in s) != (eid in s_lo)]
        cost[(PEM_RULE, eid)] = round(min(runs[s][0][0] for s in flipped) - lo, 2)
    return Bounds(lo, hi, groups, cost, L_lo, L_hi)


def by_source(b: Bounds, sources):
    """Pending keys of the given sources, ranked by the cost of losing their group (伪代码.md §6)."""
    rows = []
    for g, needs in b.groups.items():
        keys = sorted(n.key for n in needs if n.source in sources)
        if keys:
            rows.append((b.cost.get(g, 0.0), g, keys))
    rows.sort(key=lambda r: -r[0])
    return rows
