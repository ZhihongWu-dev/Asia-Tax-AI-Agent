"""ex_post (伪代码.md §7): what was actually withheld or assessed against what the rules say, flow by flow.

confirmed = actual - L_hi   (recoverable under the most conservative reading)
potential = actual - L_lo   (recoverable if every pending item resolves favourably)
A flow is archived when every clock the rules attach to it (refund, MAP) has run out at t0. `subject` restricts the
claims to the flows the subject is party to (a role / entity id) or the items of one jurisdiction; the default is
the whole group. A liquidation or capital-reduction flow is compared as a whole against its parts' labels."""
from dataclasses import dataclass
from typing import Dict, List

from .data.paths import OVER_WITHHELD, routes
from .engine import EX_POST, Bounds, CaseCtx, Defect, bounds, by_source
from .ex_ante import validate_core
from .model import Graph
from .rules.tri import DISCRETION, MISSING
from .scenarios import GROUP


@dataclass
class Claim:
    flow: str
    confirmed: float
    potential: float
    deadlines: Dict[str, object]
    routes: list                         # (route name, via, deadline or None) from PATHS, in order of use


@dataclass
class ExPostOutput:
    claims: List[Claim]
    needs: list
    conditions: list
    archived: List[str]
    b: Bounds


def _parts(labels, fid):
    """The labels that stand for one flow of the case graph: itself, or its dividend and disposal parts."""
    if fid in labels:
        return [labels[fid]]
    return [lb for k, lb in labels.items() if k in (fid + ".div", fid + ".gain")]


def _tax(labels, subject):
    """Tax payable on the flow as the labels say it: positive items only (a deduction or an input credit is the payer's
    own return, not something paid on the flow)."""
    return sum(lb.flow.amount * it.effective / 100.0 for lb in labels for it in lb.items
               if not it.deferred and not it.deduction
               and (subject == GROUP or it.jur == subject or subject in (lb.flow.payer, lb.flow.payee)))


def ex_post(graph: Graph, actual: Dict[str, float], t0, ticks=None, P=None, subject=GROUP) -> ExPostOutput:
    """actual: flow id -> tax actually paid on that flow (all jurisdictions together, or the subject's share)."""
    validate_core(graph)
    b = bounds(graph, lambda facts: CaseCtx(facts, ticks or {}, EX_POST), P)
    claims, archived = [], []
    for fid, paid in actual.items():
        lo, hi = _parts(b.L_lo, fid), _parts(b.L_hi, fid)
        if not lo:
            raise Defect("actual tax on a flow the graph does not have: %s" % fid)
        if subject != GROUP and not any(subject in (lb.flow.payer, lb.flow.payee) or any(it.jur == subject for it in lb.items) for lb in lo):
            continue
        clocks = [d for lb in lo for d in lb.deadlines.values() if d is not None]
        if clocks and all(t0 > d for d in clocks):
            archived.append(fid)
            continue
        confirmed = round(max(0.0, paid - _tax(hi, subject)), 2)
        potential = round(max(0.0, paid - _tax(lo, subject)), 2)
        if confirmed > paid + 1e-9:
            raise Defect("refund above tax paid: %s" % fid)
        if potential > 0:
            jurs = {it.jur for lb in lo for it in lb.items if not it.deduction}
            deadlines = {k: v for lb in lo for k, v in lb.deadlines.items()}
            rs = [(r.name, r.via, deadlines.get(r.name)) for j in sorted(jurs) for r in routes(j, OVER_WITHHELD)]
            claims.append(Claim(fid, confirmed, potential, deadlines, rs))
    claims.sort(key=lambda c: -c.potential)
    return ExPostOutput(claims, by_source(b, {MISSING}), by_source(b, {DISCRETION}), archived, b)
