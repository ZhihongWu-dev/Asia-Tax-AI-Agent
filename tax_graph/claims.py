"""claims (场景.md §8, 伪代码.md §7): what a settled tax item still allows, read off the two bounds.

A settled item is one (flow, taxing jurisdiction) pair the case says was paid. Against the rules' floor and ceiling
for that same item:

    confirmed  = max(0, paid - hi)     recoverable under the most conservative reading
    potential  = max(0, paid - lo)     recoverable if every pending item resolves favourably
    shortfall  = [max(0, lo - paid), max(0, hi - paid)]     what an assessment could still add

A closed item (every clock of that jurisdiction has run out at as_at, or the case declares it) is archived: the
engine already pinned it to what was paid, so nothing is recoverable, exposed or pending. A liquidation or
capital-reduction flow is compared as a whole against its parts' labels."""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .data.paths import OVER_WITHHELD, routes
from .engine import Bounds, flow_name
from .model import TREATY


@dataclass
class Claim:
    flow: str
    jur: str
    actual: float
    lo: float
    hi: float
    confirmed: float
    potential: float
    shortfall: Tuple[float, float]
    deadlines: Dict[str, object] = field(default_factory=dict)      # this jurisdiction's clocks on the flow
    routes: list = field(default_factory=list)                      # (route name, via, deadline or None), in order of use


def _tax(labels, name, jur):
    return round(sum(lb.flow.amount * it.effective / 100.0 for fid, lb in labels.items() if flow_name(fid) == name
                     for it in lb.items if it.jur == jur and it.levy == "income" and not it.deduction and not it.deferred), 2)


PAIRS = {"-".join(sorted(c.lower() for c in pair)): pair for pair in TREATY}   # rule id prefix -> the pair it belongs to


def _for_pair(rs, pair):
    """Keep the routes whose treaty (named in the rule id prefix) is the one between the flow's two jurisdictions."""
    return [r for r in rs if r[3].split(".")[0] not in PAIRS or PAIRS[r[3].split(".")[0]] == pair]


def claims(b: Bounds, settled, as_at, graph=None) -> Tuple[List[Claim], List[Tuple[str, str]]]:
    out, archived = [], []
    for name, paid_by in (settled or {}).items():
        parts = [lb for fid, lb in b.L_lo.items() if flow_name(fid) == name]
        pair = None
        if graph is not None and parts:
            f = parts[0].flow
            pair = frozenset({graph.entities[f.payer].loc, graph.entities[f.payee].loc})
        for jur, paid in paid_by.items():
            if any(jur in lb.final for lb in parts):
                archived.append((name, jur))
                continue
            lo, hi = _tax(b.L_lo, name, jur), _tax(b.L_hi, name, jur)
            route_names = {r.name for r in routes(jur, OVER_WITHHELD)}
            deadlines = {k: d for lb in parts for k, d in lb.deadlines.items() if lb.deadline_jur.get(k) == jur and k in route_names}
            potential = round(max(0.0, paid - lo), 2)
            rs = [(r.name, r.via, deadlines.get(r.name), r.rule) for r in routes(jur, OVER_WITHHELD)] if potential > 0 else []
            if pair is not None:
                rs = _for_pair(rs, pair)
            rs = [r[:3] for r in rs]
            out.append(Claim(name, jur, paid, lo, hi, round(max(0.0, paid - hi), 2), potential,
                             (round(max(0.0, lo - paid), 2), round(max(0.0, hi - paid), 2)), deadlines, rs))
    out.sort(key=lambda c: -c.potential)
    return out, archived
