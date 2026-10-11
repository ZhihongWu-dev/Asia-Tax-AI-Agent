"""Mainland withholding on a dividend, interest or royalty paid to a Hong Kong or Singapore company: the two bounds.

A consumer of the rule layer (规则层.md), like sg_s45. Facts in, (lo, hi) out; every number is a parameter.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .params import Params
from .rules.compile import compile_rules
from .rules.eval import Flow, evaluate_flow
from .rules.spec import SPEC
from .rules.tri import CEILING, FLOOR, Ctx

CN, HK, SG = "CN", "HK", "SG"
RULES = compile_rules(SPEC, Params())


@dataclass
class Side:
    rate: float                          # effective rate in % of the gross amount
    deferred: bool
    rules: List[str]                     # rule ids applied, in stage order
    deadlines: Dict[str, object] = field(default_factory=dict)
    penalty: Optional[float] = None


@dataclass
class CnWhtResult:
    lo: Side
    hi: Side
    conditions: List[str]                # pending items under the favourable bound
    cites: List[str]


def _side(res):
    it = res.item(CN)
    return Side(round(it.effective, 6), it.deferred, [r.id for r in res.applied],
                {k: v[1] for k, v in res.deadlines.items()}, res.penalty)


def cn_wht(payee_loc, income, facts, on=None, amount=None, params=None, ticks=None):
    """facts: {(elem, field): value} with elem in flow | payer | payee; None or absent = unknown."""
    P = params or Params()
    P.used = []
    facts = dict(facts)
    facts[("flow", "income")] = income
    facts.setdefault(("payee", "payee_in_source_jur"), payee_loc == CN)
    facts.setdefault(("flow", "authority_action"), "none")
    facts.setdefault(("flow", "prior_map_outcome"), "none")
    f = Flow(CN, payee_loc, income, on=on)
    lo = evaluate_flow(RULES, Ctx(facts, ticks), f, FLOOR, P, amount=amount)
    hi = evaluate_flow(RULES, Ctx(facts, ticks), f, CEILING, P, amount=amount)
    return CnWhtResult(_side(lo), _side(hi), sorted(set(lo.needs(CN)) | set(hi.needs(CN))), list(P.used))
