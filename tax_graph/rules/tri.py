"""Three-valued conditions (伪代码.md §2–3). U is a value, not a stop; known values short-circuit unknowns."""
from dataclasses import dataclass
from typing import FrozenSet

T, F, U = "T", "F", "U"
MISSING, PLAN, DISCRETION = "MISSING", "PLAN", "DISCRETION"
DATA = "DATA"          # missing data that leaves a tax unbounded (a CFC's profit, GloBE income, a holding ratio): always asked
FLOOR, CEILING = "FLOOR", "CEILING"


@dataclass(frozen=True)
class Need:
    source: str                         # MISSING | PLAN | DISCRETION
    key: str


@dataclass(frozen=True)
class Tri:
    v: str
    needs: FrozenSet[Need] = frozenset()


def tri(b):
    return Tri(T if b else F)


def AND(*xs):
    if any(x.v == F for x in xs):
        return Tri(F)
    us = [x for x in xs if x.v == U]
    return Tri(U, frozenset().union(*(x.needs for x in us))) if us else Tri(T)


def OR(*xs):
    if any(x.v == T for x in xs):
        return Tri(T)
    us = [x for x in xs if x.v == U]
    return Tri(U, frozenset().union(*(x.needs for x in us))) if us else Tri(F)


def NOT(x):
    return Tri({T: F, F: T, U: U}[x.v], x.needs)


# facts of the modelled structure, not data: the template or the engine sets them where the structure has the thing
# (the restructuring step, a special reorganisation behind a dividend); absent, the structure has none (口径 D18)
STRUCTURAL = frozenset({"reorg_step", "reorg_special_applied", "shares_cancelled", "p2_iir"})


class Ctx:
    """Facts are keyed by (element, field); a missing or None value is U(MISSING) — a structural fact reads false."""

    def __init__(self, facts, ticks=None):
        self.facts = facts
        self.ticks = ticks or {}

    def test(self, elem, field, pred, threshold=None):
        v = self.facts.get((elem, field))
        if v is None and field in STRUCTURAL:
            v = False
        if v is None:                                     # a derived fact waits for the data it is derived from
            keys = self.facts.get(("_needs", "%s.%s" % (elem, field))) or ("%s.%s" % (elem, field),)
            return Tri(U, frozenset(Need(MISSING, k) for k in keys))
        return tri(pred(v, threshold))

    def discretion(self, elem, key):
        n = Need(DISCRETION, "%s.%s" % (elem, key))
        who = self.facts.get(("_meta", elem)) if elem in ("payer", "payee") else None
        if elem == "flow" and self.facts.get(("_meta", "flow")):
            who = "flow:" + self.facts[("_meta", "flow")]
        a = Need(DISCRETION, "%s.%s" % (who, key)) if who else None
        if a is not None and a in self.ticks:                 # an answer addressed to this role or flow
            return tri(self.ticks[a])
        return tri(self.ticks[n]) if n in self.ticks else Tri(U, frozenset({n}))


def decide(t, favourable, bound, group, force):
    """伪代码.md §4: a known value decides; U follows the bound, unless the group is forced."""
    if t.v != U:
        return t.v == T
    if group in force:
        return favourable if force[group] == "fav" else not favourable
    return favourable if bound == FLOOR else not favourable
