"""The thin evaluator (规则层.md §5): cond() over a condition tree, apply() by effect type, one flow at a time.

Stage order is fixed (STAGES); inside a stage the order of rules does not matter. A rule is suppressed when a
rule that overrides it is decided True. Grade-B rules are used only on the bound that runs in their direction.
"""
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Tuple

from .model import (ALL, PROCEDURE, STAGES, And, Discretion, Effect, Grade, Leaf, Mount, Not, Or, RuleObj)
from .tri import AND, CEILING, FLOOR, NOT, OR, Tri, U, decide, MISSING, Need
from . import procedure_cn, procedure_hk, procedure_sg

PSEUDO_INCOMES = ("CFC_INCLUSION", "TOPUP")       # the engine's pseudo-flows (model.CFC_INCLUSION, model.TOPUP)

PROCEDURE_MODULES = (procedure_cn, procedure_hk, procedure_sg)    # one per jurisdiction; compile.check_registry checks them


def _registered(effect):
    return {k: v[1] for m in PROCEDURE_MODULES for k, v in m.REGISTRY.items() if v[0] == effect}


DEADLINE_EVALUATORS = _registered("DEADLINE")       # rule id or value text -> (deadline name, fn(facts, P, deadlines))
PENALTY_EVALUATORS = _registered("PENALTY")         # rule id -> fn(rule, facts, P, deadlines, tax)
BASE_EVALUATORS = _registered("BASE")               # rule id -> fn(facts, P, chooser) -> fraction in [0, 1]
NET_OF_VAT = ("cn.wht.base_excludes_vat",           # 口径 D26: a non-resident's income net of the VAT
              "cn.eit.revenue_excludes_output_vat")  # 口径 D29: a Mainland company's revenue net of the VAT on its sale
CHARGE_EVALUATORS = _registered("CHARGE")           # rule id -> fn(facts, P, chooser): the charged share of the amount, for a
                                                    # charge whose base is its own (the parts of one disposal, 口径 D22)
# 口径 D23: whether a flow's price includes the VAT is one fact for the VAT on it and for the input credit of that VAT —
# decided once per flow (a group of its own, not a rule's); the jurisdiction the planner files the question under
VAT_PRICE = "cn.vat.law.price_includes_vat"
SHARED_GROUPS = {VAT_PRICE: "CN"}
INCLUSIVE_BY_FACT = ("cn.vat.law.inclusive_price",)   # 销售额 = 含税销售额 ÷ (1 + 税率) when the contract prices the VAT in
                                                     # (口径 D23, D25)
DEDUCT_BASE_EVALUATORS = _registered("DEDUCT_BASE")
EVALUATOR_READS = {k: v for m in PROCEDURE_MODULES for k, v in m.READS.items()}


@dataclass
class Flow:
    payer_loc: str
    payee_loc: str
    income: str
    on: Optional[object] = None          # date the rule version is taken at
    target_loc: Optional[str] = None     # SHARE_TRANSFER: where the investee sits; the gain is sourced there (cn.reg.eit#7)
    indirect_cn: bool = False            # SHARE_TRANSFER of an offshore holder whose subtree holds Mainland taxable property
    id: str = "flow"
    payer_seat: Optional[str] = None     # 口径 D31: where a party moved to the Mainland for income tax (effective management)
    payee_seat: Optional[str] = None     # is established — what VAT and stamp duty see; None: its location
    target_seat: Optional[str] = None

    @property
    def source_loc(self):
        return self.target_loc if self.income == "SHARE_TRANSFER" and self.target_loc else self.payer_loc


@dataclass
class TaxItem:
    """tax = amount x base_share x rate / 100. A treaty cap limits the tax to cap x cap_base x amount."""
    jur: str
    charge_rate: float                   # the domestic rate before any cap
    rate: float
    base_share: float = 1.0              # domestic base (deemed profit, gain over consideration, nexus)
    cap_base: float = 1.0                # treaty base the cap applies to (60% of equipment rent)
    cap: Optional[float] = None          # treaty cap applied, in % of cap_base x amount
    credit: float = 0.0                  # foreign tax credited, in % of amount; never above rate x base_share
    deferred: bool = False               # tax computed but not payable while the deferral condition holds
    deduction: bool = False              # the payer's deduction: counts negative
    cites: List[str] = field(default_factory=list)
    vat_inclusive: bool = False          # a VAT item taken out of a VAT-inclusive price: its rate is r / (1 + r) (口径 D26)
    actual: Optional[float] = None       # a closed item: what was paid, in % of amount; the rules no longer move it
    bearer: Optional[str] = None         # "payer" | "payee"; None = the payer for a deduction, the payee otherwise
    levy: str = "income"                 # "income" | "stamp" | "vat": caps, exemptions and credits touch income items only
    creditable: float = 0.0              # foreign tax (and underlying tax) available against this item, in % of amount

    @property
    def borne_by(self):
        return self.bearer or ("payer" if self.deduction else "payee")

    @property
    def effective(self):
        if self.actual is not None:
            return self.actual
        if self.deduction:
            return -self.rate * self.base_share
        return max(0.0, self.rate * self.base_share - self.credit)


@dataclass
class FlowResult:
    items: List[TaxItem]
    applied: List[RuleObj]               # rules whose effect was applied, in stage order
    groups: Dict[Tuple[str, str], frozenset]     # (rule_id, flow) -> needs, for rules that evaluated to U
    deadlines: Dict[str, Tuple[object, object]] = field(default_factory=dict)   # name -> (nominal, date)
    penalty: Optional[float] = None
    deadline_rules: Dict[str, str] = field(default_factory=dict)                # name -> value text used
    deadline_jur: Dict[str, str] = field(default_factory=dict)                  # name -> taxing jurisdiction of the clock
    rules: Dict[str, RuleObj] = field(default_factory=dict)                     # id -> rule, for every applicable rule
    gaps: Dict[str, tuple] = field(default_factory=dict)                        # deadline -> (jurisdiction, year) of a missing calendar
    outside: Dict[tuple, tuple] = field(default_factory=dict)                   # 口径 D30: (jur, levy, bearer) -> (law, in force from)

    def needs(self, jur=None):
        """Pending keys, optionally only from rules acting on one jurisdiction's tax (a shared group: its own, 口径 D23)."""
        return sorted({n.key for (rid, _), ns in self.groups.items() for n in ns
                       if jur is None or (SHARED_GROUPS[rid] if rid in SHARED_GROUPS else self.rules[rid].scope.taxing) in (jur, ALL)})

    def item(self, jur):
        """The income-tax item of one jurisdiction (since 口径 D26 the VAT stage runs first: a VAT item is no answer)."""
        return next((it for it in self.items if it.jur == jur and not it.deduction and it.levy == "income"), None)

    def total(self, jur=None):
        """Sum of effective rates (percent of the amount) over the items, deductions negative."""
        return round(sum(it.effective for it in self.items if jur is None or it.jur == jur), 6)


def cond(ctx, elem_of, c) -> Tri:
    """elem_of maps a Leaf's `on` to the element id the facts are keyed by."""
    if isinstance(c, Leaf):
        threshold = ctx.P[c.param] if c.param else None
        return ctx.test(elem_of(c.on), c.field, c.pred, threshold)
    if isinstance(c, Discretion):
        return ctx.discretion(elem_of(c.on), c.key)
    if isinstance(c, And):
        return AND(*(cond(ctx, elem_of, x) for x in c.xs))
    if isinstance(c, Or):
        return OR(*(cond(ctx, elem_of, x) for x in c.xs))
    if isinstance(c, Not):
        return NOT(cond(ctx, elem_of, c.x))
    raise TypeError("not a condition: %r" % (c,))


def matches(scope, f: Flow):
    if scope.mount is Mount.SUBGRAPH:                 # rules about what the flow's target holds, not about the flow itself
        if not f.indirect_cn:
            return False
    elif scope.mount is not Mount.FLOW:
        return False
    return (scope.source in (ALL, f.source_loc) and (scope.residence is None or scope.residence == f.payee_loc)
            and scope.covers(f.income))


def valid_on(r: RuleObj, on):
    if on is None:
        return True
    lo, hi = r.valid
    return (lo is None or lo <= on) and (hi is None or on <= hi)          # hi: the last day in force (effective_to)


ENTITY_RATE = {"cn.eit.rate_entity", "hk.profits.rate_entity", "sg.corp.rate_entity"}    # 范围.md 1: the entity's own rate
INCOME_EFFECTS = (Effect.NOCHARGE, Effect.SPLIT, Effect.CHARGE, Effect.BASE, Effect.RATE_CAP, Effect.EXEMPT, Effect.CREDIT, Effect.DEFER, Effect.DENY)


def entity_rate(r, P, facts, elem):
    """A rule that charges an entity's own income tax, or values its deduction, uses the rate the entity actually
    bears (a fact: incentive rate, two-tier, partial exemption) when the case states it; else the headline rate."""
    if facts and any(m in r.uses for m in ENTITY_RATE):
        v = facts.get((elem, "cit_rate"))
        if v is not None:
            return float(v)
    return P[r.value]


class Chooser:
    """Hands an evaluator the decision for a fact it cannot find: registers the need under the rule and returns
    True when the favourable end is to be taken (伪代码.md §4 decide, so a forced run can flip it)."""

    def __init__(self, rule_id, flow_id, bound, force, pending=None, invert=False):
        self.group, self.bound, self.force, self.pending = (rule_id, flow_id), bound, force, pending
        self.invert = invert                  # a final item: the end that raises the tax due is the favourable one

    @property
    def fav(self):
        return decide(Tri(U), not self.invert, self.bound, self.group, self.force)

    def missing(self, *keys):
        needs = frozenset(Need(MISSING, k) for k in keys)
        if self.pending is not None:
            self.pending[self.group] = self.pending.get(self.group, frozenset()) | needs
        return decide(Tri(U, needs), not self.invert, self.bound, self.group, self.force)


def apply(items, r: RuleObj, P, facts=None, bound=FLOOR, ch=None):
    jur = r.scope.taxing if r.scope.taxing != ALL else None
    if r.effect is Effect.CHARGE:
        rate = entity_rate(r, P, facts, "payee")
        it = TaxItem(jur, rate, rate, cites=[r.id])
        if r.id in CHARGE_EVALUATORS:
            it.base_share = CHARGE_EVALUATORS[r.id](facts or {}, P, ch or Chooser(r.id, "flow", bound, {}))
        final = (facts or {}).get(("flow", "_final"))                 # a closed item: what was paid, known to later stages
        if final and jur in final and not any(x.jur == jur and x.levy == "income" and not x.deduction and x.actual is not None for x in items):
            it.actual = final[jur]
        return items + [it]
    if r.effect is Effect.DEDUCTION:
        rate = entity_rate(r, P, facts, "payer")
        return items + [TaxItem(jur, rate, rate, deduction=True, cites=[r.id])]
    if r.effect is Effect.STAMP:
        rate = P[r.value]
        return items + [TaxItem(jur, rate, rate, levy="stamp", bearer=r.bearer or "payee", cites=[r.id])]
    if r.effect is Effect.VAT:
        rate = P[r.value]
        inclusive = False
        if any(m in r.uses for m in INCLUSIVE_BY_FACT):   # 口径 D23: only for a VAT-inclusive price — a fact of the contract
            inc = (facts or {}).get(("flow", "price_includes_vat"))
            if inc is None:
                c0 = ch or Chooser(r.id, "flow", bound, {})
                inc = Chooser(VAT_PRICE, c0.group[1], bound, c0.force, c0.pending, c0.invert).missing("flow.price_includes_vat")
            if inc:
                rate, inclusive = 100.0 * (rate / 100.0) / (1.0 + rate / 100.0), True
        if r.bearer == "payer" and ".input_credit" in r.id:   # the payer's input credit: negative, its own — the VAT this
            borne = sum(x.rate for x in items if x.levy == "vat" and x.jur == jur and not x.deduction and x.borne_by == "payee")
            if borne <= 0 or any(x.levy == "vat" and x.jur == jur and x.deduction for x in items):   # flow bears, once
                return items
            return items + [TaxItem(jur, borne, borne, levy="vat", bearer="payer", deduction=True, cites=[r.id])]
        if "sg.gst.recovery_ratio_basis" in r.uses:              # reverse charge: output tax less the recoverable share (s19, s20)
            ratio = (facts or {}).get(("payer", "gst_recovery_ratio"))
            if ratio is None:
                fav = (ch or Chooser(r.id, "flow", bound, {})).missing("payer.gst_recovery_ratio")
                rate = 0.0 if fav else rate                          # nearly all recoverable ... none recoverable
            else:
                rate = rate * max(0.0, 1.0 - float(ratio) / 100.0)
        return items + [TaxItem(jur, rate, rate, levy="vat", bearer=r.bearer or "payee", cites=[r.id], vat_inclusive=inclusive)]
    if r.effect is Effect.DEDUCT_BASE:
        fn = DEDUCT_BASE_EVALUATORS[r.id]
        c1 = ch or Chooser(r.id, "flow", bound, {})
        share = fn(facts or {}, P, c1, items) if getattr(fn, "takes_items", False) else fn(facts or {}, P, c1)
        for it in items:
            if it.jur == jur and it.deduction and it.levy == "income":     # a VAT input credit is no income deduction
                it.base_share *= share
                it.cites.append(r.id)
        return items
    if r.effect in (Effect.NOCHARGE, Effect.SPLIT):
        return items
    mine = [it for it in items if it.jur == jur and not it.deduction and it.levy == "income"]
    treaty_rule = r.scope.residence is not None and r.scope.side == "source"
    if r.effect is Effect.BASE and any(m in r.uses + ((r.value,) if r.value else ()) for m in NET_OF_VAT):
        # 口径 D26 (公告2013年第9号), D29 (增值税会计处理规定): with a VAT-inclusive price the income is the price net of
        # the VAT — the base (and a treaty cap's base) shrink to 1 / (1 + r); a gain is the net price less the basis
        x = sum(v.rate for v in items if v.levy == "vat" and v.jur == jur and not v.deduction and v.borne_by == "payee"
                and v.vat_inclusive) / 100.0
        if x > 0:
            for it in mine:
                if (facts or {}).get(("flow", "income")) == "IP_TRANSFER":
                    it.base_share = max(0.0, it.base_share - x)
                else:
                    it.base_share *= 1.0 - x
                    it.cap_base *= 1.0 - x
                it.cites.append(r.id)
        return items
    if r.effect is Effect.BASE:
        if r.id in BASE_EVALUATORS:                   # fraction computed from facts (gain / consideration, nexus)
            fn, c1 = BASE_EVALUATORS[r.id], ch or Chooser(r.id, "flow", bound, {})
            share = fn(facts or {}, P, c1, items) if getattr(fn, "takes_items", False) else fn(facts or {}, P, c1)
        else:
            share = P[r.value] / 100.0
        for it in mine:
            if treaty_rule:
                it.cap_base *= share                  # the treaty narrows the base its cap applies to
            else:
                it.base_share *= share                # domestic law narrows what is taxed
            it.cites.append(r.id)
    elif r.effect is Effect.RATE_CAP:
        cap = P[r.value]
        for it in mine:
            it.cap = cap if it.cap is None else min(it.cap, cap)
            it.rate = min(it.rate, cap * it.cap_base / it.base_share) if it.base_share else it.rate
            it.cites.append(r.id)
    elif r.effect is Effect.EXEMPT:
        for it in mine:
            it.rate = 0.0
            if treaty_rule:
                it.cap = 0.0                          # a treaty exemption is a cap of zero
            it.cites.append(r.id)
    elif r.effect is Effect.CREDIT:                   # s50-type limit: credit <= residence tax on the same income
        foreign = [x for x in items if x.jur != jur and x.jur is not None and not x.deduction and x.levy == "income"]
        paid = sum(min(x.actual, x.rate * x.base_share) if x.actual is not None else x.effective for x in foreign)   # 口径 D01
        if not foreign and facts and facts.get(("flow", "foreign_tax_rate")) is not None:
            paid = float(facts[("flow", "foreign_tax_rate")])       # ex post: the tax actually borne abroad
        if "cn.ftc.indirect" in r.uses and facts:                   # EIT art 24: the tax the payer bore on the profits behind
            u = facts.get(("flow", "underlying_tax_share"))           # the dividend, as % of the dividend (125号 第五条)
            if u is None:                                             # unknown: pending; the favourable end credits in full,
                keys = facts.get(("_needs", "flow.underlying_tax_share")) or ("flow.underlying_tax_share",)
                if (ch or Chooser(r.id, "flow", bound, {})).missing(*keys):
                    paid = max(paid, max((it.rate * it.base_share for it in mine), default=0.0))
                else:                                                 # the other end the least the data allow
                    u = facts.get(("flow", "underlying_tax_share_min"))
            if u is not None:
                paid += float(u)
                if "cn.ftc.gross_up" in r.uses:                       # 操作指南 4: the dividend is grossed up by the tax behind it
                    for it in mine:
                        it.base_share += float(u) / 100.0
        for it in mine:
            it.credit = min(paid, it.rate * it.base_share)
            it.creditable = paid
            it.cites.append(r.id)
    elif r.effect is Effect.DEFER:
        for it in mine:
            it.deferred = True
            it.cites.append(r.id)
    return items


LEVY_OF = {Effect.VAT: "vat", Effect.STAMP: "stamp"}


def levy_view(f: Flow):
    """口径 D31. The flow as VAT and stamp duty see it: each party where it is established. The effective-management
    variant makes a foreign company a Mainland resident for income tax only (国税发〔2009〕82号 第二条)."""
    if not (f.payer_seat or f.payee_seat or f.target_seat):
        return f
    return replace(f, payer_loc=f.payer_seat or f.payer_loc, payee_loc=f.payee_seat or f.payee_loc,
                   target_loc=f.target_seat or f.target_loc)


def seen_by(r, f, fl):
    return fl if r.effect in LEVY_OF else f


def outside_of(rules, applicable, f: Flow):
    """口径 D30. The library keeps current law only: a rule whose law replaced rules it does not keep (RuleObj.before)
    cannot speak for a flow dated before it takes effect — whatever the old rules said, that levy is outside the library
    there, never nil. An income base that turns on the VAT (口径 D26, D29) is outside with it. (jur, levy, bearer) ->
    (law, in force from); the engine turns the bearer into the party that bears it."""
    out = {}
    if f.on is None:
        return out
    fl = levy_view(f)
    for r in rules:
        lo = r.valid[0]
        if r.before and lo is not None and f.on < lo and matches(r.scope, seen_by(r, f, fl)):
            jur = r.scope.taxing if r.scope.taxing != ALL else None
            out.setdefault((jur, LEVY_OF.get(r.effect, "income"), r.bearer or "payee"), (r.before[0], lo))
    for r in applicable:
        if r.effect is Effect.BASE and any(m in r.uses + ((r.value,) if r.value else ()) for m in NET_OF_VAT):
            jur = r.scope.taxing if r.scope.taxing != ALL else None
            vat = next((v for (j, levy, _), v in out.items() if j == jur and levy == "vat"), None)
            if vat is not None:
                out.setdefault((jur, "income", "payee"), vat)
    return out


def evaluate_flow(rules, ctx, f: Flow, bound, P, force=None, amount=None) -> FlowResult:
    force = force or {}
    ctx.P = P
    elem_of = lambda on: on                       # facts are keyed ("flow"|"payer"|"payee", field)
    final = ctx.facts.get(("flow", "_final")) or {}   # jurisdictions whose tax on this flow is paid and closed

    def inverted(r):                              # 口径 D03
        """A final item's tax is sunk; its jurisdiction's income rules now only move the tax *due*, and with it the
        credit elsewhere (125号 第四条(二), s50(1)) - so the end that raises the tax due is the favourable one."""
        return r.scope.taxing in final and r.effect in INCOME_EFFECTS

    fav_of = lambda r: (not r.favourable) if inverted(r) else r.favourable
    fl = levy_view(f)                             # 口径 D31: VAT and stamp duty match by the seat
    applicable = [r for r in rules if matches(r.scope, seen_by(r, f, fl)) and valid_on(r, f.on)]
    applicable = [r for r in applicable if r.grade is not Grade.B_PRACTICE or (bound == FLOOR) == fav_of(r)]
    tri = {}
    seat_facts = dict(ctx.facts.get(("_meta", "seat")) or ())   # and read the facts that turn on a party's place by it
    for r in applicable:
        ctx.rule = r                              # a settled item's rules read plan-controlled fields as facts (engine.CaseCtx)
        if seat_facts and r.effect in LEVY_OF:
            saved = {k: ctx.facts[k] for k in seat_facts if k in ctx.facts}
            ctx.facts.update(seat_facts)
            try:
                tri[r.id] = cond(ctx, elem_of, r.cond)
            finally:
                for k in seat_facts:
                    if k in saved:
                        ctx.facts[k] = saved[k]
                    else:
                        ctx.facts.pop(k, None)
        else:
            tri[r.id] = cond(ctx, elem_of, r.cond)
    on = {r.id: decide(tri[r.id], fav_of(r), bound, (r.id, f.id), force) for r in applicable}
    pending = {}                                  # (rule id, flow id) -> needs raised by evaluators on the main run
    memo = {}                                     # (rule ids, this flow's forced groups) -> result, for side-effect-free runs

    def run(rule_set, force_=None, record=False):
        if not record:
            fz = force_ if force_ is not None else force
            mk = (tuple(r.id for r in rule_set), tuple(sorted((k, v) for k, v in fz.items() if k[1] == f.id)))
            if mk in memo:
                return memo[mk]
        its, done = [], []
        for stage in STAGES:
            for r in sorted(rule_set, key=lambda x: ".input_credit" in x.id):     # a credit after the VAT it mirrors
                if r.effect is stage:
                    its = apply(its, r, P, ctx.facts, bound, Chooser(r.id, f.id, bound, force_ if force_ is not None else force,
                                                                      pending if record else None, invert=inverted(r)))
                    done.append(r)
        for jur, rate in final.items():           # a closed item with no charge behind it: what was paid stands, nothing is due
            if not any(x.jur == jur and x.levy == "income" and not x.deduction for x in its):
                its.append(TaxItem(jur, 0.0, 0.0, actual=rate, cites=["settled"]))
        if not record:
            memo[mk] = (its, done)
        return its, done

    def live_of(on_):
        sup = {rid for r in applicable if on_[r.id] for rid in r.overrides}
        return [r for r in applicable if on_[r.id] and r.id not in sup]

    for r in applicable:                          # ambiguous rules: which decision favours the taxpayer is read off the numbers
        if not r.ambiguous or tri[r.id].v != U:
            continue
        totals = {}
        for flag in (True, False):
            on_ = dict(on)
            on_[r.id] = flag
            totals[flag] = sum(x.effective for x in run(live_of(on_))[0] if x.levy == "income" and not x.deduction)
        fav_flag = totals[True] <= totals[False]
        g = (r.id, f.id)
        if g in force:
            on[r.id] = fav_flag if force[g] == "fav" else (not fav_flag)
        else:
            on[r.id] = fav_flag if bound == FLOOR else (not fav_flag)
    live = live_of(on)
    live_ids = {r.id for r in live}
    other = CEILING if bound == FLOOR else FLOOR    # the same flow with every open item decided the other way
    on_other = {r.id: decide(tri[r.id], fav_of(r), other, (r.id, f.id), force) for r in applicable}
    for r in applicable:
        if r.ambiguous and tri[r.id].v == U and (r.id, f.id) not in force:
            on_other[r.id] = not on[r.id]

    open_ids = [r.id for r in applicable if tri[r.id].v == U]

    items, applied = run(live, record=True)
    live_other = live_of(on_other)
    run(live_other, record=True)                  # evaluator needs that only surface at the other end register too

    def bases(exclude=None):
        """(decisions, forces) to test a pending item against: every resolution of the other open rules and of the
        other evaluator-read facts while they are few (<= 7 dimensions), else just this bound's and the other bound's."""
        others = [rid for rid in open_ids if rid != exclude]
        evals = [g for g in pending if g != exclude]
        if len(others) + len(evals) <= 7:
            from itertools import product as _product
            for combo in _product((True, False), repeat=len(others) + len(evals)):
                base = dict(on)
                base.update(zip(others, combo[:len(others)]))
                fz = dict(force)
                fz.update({g: ("fav" if v else "unfav") for g, v in zip(evals, combo[len(others):])})
                yield base, fz
        else:
            yield on, force
            yield on_other, force

    def relevant(r):
        """A pending rule is worth resolving only if deciding it the other way would change this flow's taxes."""
        if r.effect in PROCEDURE:                     # a clock is pending only once its trigger facts exist
            trig = [tuple(k.split(".", 1)) for k in EVALUATOR_READS.get(r.id, ())]
            return (any(x.effective > 0 for x in items if r.scope.taxing in (ALL, x.jur))
                    and all(ctx.facts.get(k) is not None for k in trig))
        key = lambda its: sorted((x.jur or "", x.deduction, round(x.effective, 9), x.deferred) for x in its)
        for base, fz in bases(r.id):                  # some resolution of the other open items must make it matter
            flipped = dict(base)
            flipped[r.id] = not base[r.id]
            if key(run(live_of(base), fz)[0]) != key(run(live_of(flipped), fz)[0]):
                return True
        return False
    groups = {(r.id, f.id): tri[r.id].needs for r in applicable if tri[r.id].v == U and relevant(r)}
    key = lambda its: sorted((x.jur or "", x.deduction, round(x.effective, 9), x.deferred) for x in its)
    for group, needs in list(pending.items()):    # an evaluator's missing fact matters if some resolution of the rest
        if group in groups:                       # makes flipping it change the outcome
            groups[group] = groups[group] | needs
            continue
        for base, fz in bases(group):
            lv = live_of(base)
            if key(run(lv, {**fz, group: "fav"})[0]) != key(run(lv, {**fz, group: "unfav"})[0]):
                groups[group] = needs
                break
    res = FlowResult(items, applied, groups, rules={r.id: r for r in applicable}, outside=outside_of(rules, applicable, f))
    # procedure: deadlines first (grade A, then B which post-processes), then penalties
    procs = sorted((r for r in live if r.effect in PROCEDURE), key=lambda r: (PROCEDURE.index(r.effect), r.grade.value))
    if f.income in PSEUDO_INCOMES:                # a deemed inclusion or a top-up is no payment: no withholding clock runs
        procs = []
    def tax_of(r):                       # the tax a procedure rule acts on: this jurisdiction's, deductions aside
        its = [it for it in items if not it.deduction and r.scope.taxing in (ALL, it.jur)]
        return round(sum(amount * it.effective / 100.0 for it in its), 2) if amount is not None and its else None

    for r in procs:
        if r.value.startswith("observed:") or r.id in DEADLINE_EVALUATORS:
            key = r.value if r.value.startswith("observed:") else r.id
        else:
            key = P[r.value]                  # a text value names the evaluator; an unknown text raises
        if r.effect is Effect.DEADLINE:
            name, fn = DEADLINE_EVALUATORS[key]
            got = fn(ctx.facts, P, res.deadlines)
            if got is not None:
                gap = getattr(got[1], "gap", None)
                if gap:                                   # the date is the nominal one: that year's calendar is missing
                    res.gaps[name] = gap
                res.deadlines[name] = got
                res.deadline_rules[name] = key
                res.deadline_jur[name] = r.scope.taxing
                applied.append(r)
        elif r.effect is Effect.PENALTY:
            pen = PENALTY_EVALUATORS[r.id](r, ctx.facts, P, res.deadlines, tax_of(r))
            if pen is not None:
                res.penalty = (res.penalty or 0.0) + pen
                applied.append(r)
    return res
