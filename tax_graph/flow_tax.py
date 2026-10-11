"""One flow, one jurisdiction's tax, both bounds. The generic consumer of the rule layer (规则层.md).

    r = flow_tax(payer_loc, payee_loc, income, facts, jur)
    r.lo, r.hi      effective rate in % of the gross amount under FLOOR / CEILING; None = that jurisdiction charges nothing
    r.conditions    pending items on that jurisdiction's tax, union of both bounds
sg_s45, cn_wht and hk_tax are thin presentations over the same evaluation.
"""
from dataclasses import dataclass
from typing import List, Optional

from .params import Params
from .rules.compile import compile_rules
from .rules.eval import Flow, evaluate_flow
from .rules.spec import SPEC
from .rules.tri import CEILING, FLOOR, Ctx

RULES = compile_rules(SPEC, Params())


@dataclass
class FlowTax:
    lo: Optional[float]
    hi: Optional[float]
    lo_rules: List[str]
    hi_rules: List[str]
    conditions: List[str]
    cites: List[str]
    lo_credit: float = 0.0
    hi_credit: float = 0.0
    lo_total: float = 0.0                # all items of the jurisdiction, deductions negative
    hi_total: float = 0.0


def flow_tax(payer_loc, payee_loc, income, facts, jur, on=None, amount=None, params=None, ticks=None, rules=None, target_loc=None):
    """For a SHARE_TRANSFER, payer is the buyer, payee the seller and target_loc the investee's jurisdiction."""
    P = params or Params()
    P.used = []
    facts = dict(facts)
    facts[("flow", "income")] = income
    f = Flow(payer_loc, payee_loc, income, on=on, target_loc=target_loc,
             indirect_cn=bool(facts.get(("flow", "indirect_cn_target"))))
    facts.setdefault(("payee", "payee_in_source_jur"), payee_loc == f.source_loc)
    facts.setdefault(("flow", "authority_action"), "none")
    facts.setdefault(("flow", "prior_map_outcome"), "none")
    rules = rules or RULES
    lo = evaluate_flow(rules, Ctx(facts, ticks), f, FLOOR, P, amount=amount)
    hi = evaluate_flow(rules, Ctx(facts, ticks), f, CEILING, P, amount=amount)
    rate = lambda res: None if res.item(jur) is None else round(res.item(jur).effective, 6)
    credit = lambda res: 0.0 if res.item(jur) is None else round(res.item(jur).credit, 6)
    pick = lambda res: [r.id for r in res.applied if r.scope.taxing in (jur, "ALL")]
    return FlowTax(rate(lo), rate(hi), pick(lo), pick(hi), sorted(set(lo.needs(jur)) | set(hi.needs(jur))), list(P.used),
                   credit(lo), credit(hi), lo.total(jur), hi.total(jur))
