"""Graph model (图模型.md): jurisdiction layer as constants, case layer as data. No tax numbers live here."""
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional

CN, HK, SG = "CN", "HK", "SG"
JURISDICTIONS = (CN, HK, SG)            # the one list: templates, coverage matrix, treaty pairs and routes derive from it
ARRANGEMENT, DTA, NONE = "ARRANGEMENT", "DTA", "NONE"
DIVIDEND, INTEREST, ROYALTY, SHARE_TRANSFER = "DIVIDEND", "INTEREST", "ROYALTY", "SHARE_TRANSFER"
SERVICE_FEE, LIQUIDATION, CAPITAL_REDUCTION = "SERVICE_FEE", "LIQUIDATION", "CAPITAL_REDUCTION"
IP_TRANSFER = "IP_TRANSFER"                             # a sale of IP ownership: a one-off step of the ip template (口径 D22)
SPLIT_INCOMES = (LIQUIDATION, CAPITAL_REDUCTION)        # decomposed into a dividend part and a disposal part (engine.normalise)
CFC_INCLUSION = "CFC_INCLUSION"                         # a deemed distribution the engine generates (范围.md 5), never a case input
TOPUP = "TOPUP"                                         # Pillar Two excess profit the engine generates per in-scope entity (范围.md 9)
RECURRING = (DIVIDEND, INTEREST, ROYALTY, SERVICE_FEE)  # flows a multi-year event repeats each year
COMPANY = "COMPANY"

TREATY = {frozenset({CN, HK}): ARRANGEMENT, frozenset({CN, SG}): DTA, frozenset({HK, SG}): NONE}


def treaty(a, b):
    return NONE if a == b else TREATY[frozenset({a, b})]


@dataclass
class Entity:
    id: str
    loc: str
    type: str = COMPANY
    attrs: Dict[str, object] = field(default_factory=dict)      # facts keyed by field id (信息收集.md)


@dataclass
class HoldEdge:
    holder: str
    held: str
    ratio: float                    # percent
    since: Optional[date] = None
    cost: Optional[float] = None    # acquisition cost of the holding
    unknown: tuple = ()             # attributes the case does not state (e.g. ("ratio",)): the planner asks for them
    designed: bool = False          # a relation the plan itself creates (a new, wholly owned company): a plan action


@dataclass
class FlowEdge:
    id: str
    payer: str                      # SHARE_TRANSFER: the buyer
    payee: str                      # SHARE_TRANSFER: the seller
    income: str
    amount: float
    on: date
    currency: str = "CNY"
    target: Optional[str] = None    # SHARE_TRANSFER: the entity whose shares change hands
    attrs: Dict[str, object] = field(default_factory=dict)      # flow-level facts


@dataclass
class Graph:
    entities: Dict[str, Entity]
    holds: List[HoldEdge]
    flows: List[FlowEdge]
    members: Optional[set] = None   # the group whose tax the objective counts, when the case declares it
    unmodelled: tuple = ()          # steps the structure needs whose tax no rule computes (口径 D19): it is no plan

    def holders_of(self, eid):
        return [h for h in self.holds if h.held == eid]

    def group(self):
        """The group whose tax the objective counts: as declared by the case, else every entity the holding graph
        touches. A counterparty with no holding link (an outside buyer, a bank, a client) is evaluated but its tax is
        its own."""
        if self.members is not None:
            return set(self.members)
        return {h.holder for h in self.holds} | {h.held for h in self.holds}

    def holding(self, holder, held):
        return next((h for h in self.holds if h.holder == holder and h.held == held), None)

    def subtree(self, eid, seen=None):
        """Entities held, directly or indirectly, by eid (eid included)."""
        seen = seen or set()
        if eid in seen:
            return seen
        seen.add(eid)
        for h in self.holds:
            if h.holder == eid:
                self.subtree(h.held, seen)
        return seen

    def component(self, eid):
        """Entities connected to eid through holdings in either direction: the group, as the holding graph shows it."""
        seen, todo = set(), [eid]
        while todo:
            x = todo.pop()
            if x in seen:
                continue
            seen.add(x)
            todo += [h.held for h in self.holds if h.holder == x] + [h.holder for h in self.holds if h.held == x]
        return seen

    def chain_ratio(self, holder, held):
        """Product of ratios along the holding chain holder -> ... -> held, in percent; 0 if no chain."""
        if holder == held:
            return 100.0
        best = 0.0
        for h in self.holds:
            if h.holder == holder:
                best = max(best, h.ratio / 100.0 * self.chain_ratio(h.held, held))
        return best


def months(a: date, b: date) -> int:
    """Whole months from a to b."""
    if a is None or b is None:
        return None
    m = (b.year - a.year) * 12 + (b.month - a.month)
    return m - 1 if b.day < a.day else m


def topo_order(flows: List[FlowEdge]) -> List[FlowEdge]:
    """Flows ordered by date, then upstream before downstream (a payee's own payments come after its receipts),
    share transfers last on their day."""
    def depth(f, seen=()):
        if f.id in seen:
            return 0
        feeders = [g for g in flows if g.on == f.on and g.payee == f.payer and g.income != SHARE_TRANSFER]
        return 1 + max((depth(g, seen + (f.id,)) for g in feeders), default=0)
    return sorted(flows, key=lambda f: (f.on, f.income == SHARE_TRANSFER, depth(f)))


@dataclass
class Label:
    items: list
    cites: List[str]
    tax: float                      # cash tax of this element within the horizon (deferred items count 0)
    deadlines: Dict[str, object] = field(default_factory=dict)
    flow: object = None             # the FlowEdge the label is about (a part flow after a split)
    deadline_jur: Dict[str, str] = field(default_factory=dict)   # clock name -> taxing jurisdiction
    actual: Dict[str, float] = field(default_factory=dict)       # jurisdiction -> tax actually paid on this flow (settled items)
    final: frozenset = frozenset()  # jurisdictions whose item is closed: every clock has run out, or the case says so
    applied: List[str] = field(default_factory=list)   # rule ids whose effect was applied (deadlines and penalties included)
    gaps: Dict[str, tuple] = field(default_factory=dict)   # deadline -> (jurisdiction, year) whose holiday calendar is missing
    outside: Dict[tuple, tuple] = field(default_factory=dict)   # 口径 D30: (jur, levy, party bearing it) -> (law, in force from)
