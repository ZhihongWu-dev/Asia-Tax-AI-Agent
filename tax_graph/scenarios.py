"""scenarios.py (场景.md §2): a scenario is a template instantiated on a case.

    Template    the roles the case must place, the roles the plan may add or place (with their candidate jurisdictions),
                the structural variables, and a builder (event, assignment, case) -> Graph
    Case        the client's facts: jurisdiction and attrs per role it already has, holdings per (holder, held) pair,
                flow facts per flow name
    candidate   one assignment of the free roles and the live structural variables; only assignments that describe
                no graph are pruned (D4) — a role placed in the payer's own jurisdiction is evaluated like any other
                (its flows are domestic, which the rules do not charge), never reasoned away
    subject     an output view only: the group, one role, or one jurisdiction (the objective stays the group total, I1)

Entity ids are role names, so edits and outputs speak in roles. Any role may sit in any jurisdiction: the case fixes
OP / ULT / BUYER wherever the client is; check_coverage guarantees every (jurisdiction, side, income) cell has a rule or
a declaration, so no placement falls through silently.
"""
from dataclasses import dataclass, field, replace
from itertools import product
from typing import Callable, Dict, List, Optional, Tuple

from .data.domain import DEBT, DIRECT, DIVIDEND_OUT, EQUITY, INDIRECT, Event
from .engine import Bounds
from .model import (CAPITAL_REDUCTION, COMPANY, DIVIDEND, INTEREST, IP_TRANSFER, JURISDICTIONS, LIQUIDATION, RECURRING,
                    ROYALTY, SERVICE_FEE, SHARE_TRANSFER, Entity, FlowEdge, Graph, HoldEdge, months)

OP, HOLD, ULT, IPCO, LENDER, BUYER, SERVICER, CLIENT = "OP", "HOLD", "ULT", "IPCO", "LENDER", "BUYER", "SERVICER", "CLIENT"
ANYWHERE = list(JURISDICTIONS)                 # a role the plan places: any jurisdiction in the list
OPTIONAL = [None] + ANYWHERE                   # ... or absent
GROUP = "GROUP"
NEW = "_NEW"                                   # 口径 D19: the new company that takes a group role over in another jurisdiction
GROUP_ROLES = (HOLD, IPCO, SERVICER)           # roles a group company plays (BUYER, LENDER, CLIENT are counterparties)

# 口径 D21: flow facts that describe one party of the flow. The case states them for the parties of its own structure;
# where the candidate's party is a company the plan creates (a new HOLD, IPCO_NEW, ...), they describe another company
# or none, so they are not carried: the law gives what it can (facts.py), the plan designs what it controls
# (DESIGNABLE_FLOW), the rest is asked under the flow's own fact key "<flow>~<company>-<jurisdiction>"
PAYER_SIDE = frozenset({"foreign_taxed", "underlying_profits_taxed", "underlying_tax_share", "deductible_at_payer",
                        "foreign_headline_rate", "foreign_tax_rate", "listed_market_trade"})
PAYEE_SIDE = frozenset({"receipt_kind", "held_as_trading_stock", "qualifying_rd_expenditure", "non_qualifying_expenditure",
                        "ip_never_owned_by_hk_business", "lender_interest_taxable_in_hk",
                        "profit_margin"})                       # the profit in a fee: the recipient's own accounts
# (whether a dividend is reinvested in the Mainland describes the event's money, not the recipient: it is carried)
BUYER_SIDE = frozenset({"acquirer_chargeable_in_hk"})                    # a share transfer's payer
SELLER_SIDE = PAYEE_SIDE | {"foreign_taxed", "foreign_tax_rate"}          # its payee: was the gain taxed at source
TARGET_SIDE = frozenset({"listed_market_trade", "foreign_headline_rate", "underlying_profits_taxed", "deductible_at_payer"})

# facts that belong to an entity in one jurisdiction; a role placed elsewhere does not carry them (they become pending)
JURISDICTION_BOUND = frozenset({"residence_cert", "cert_years", "circumstances_changed_on", "substance_ruled_adequate",
                                "sch17k_elected", "registration_filing_compliant", "fixed_place_in_sg", "fixed_place_in_cn",
                                "fixed_place_in_hk", "ftc_pooling_election", "is_excluded_entity"})


@dataclass
class RoleFacts:
    loc: Optional[str]
    attrs: dict = field(default_factory=dict)
    type: str = COMPANY


@dataclass
class Case:
    roles: Dict[str, RoleFacts]
    holds: Dict[Tuple[str, str], HoldEdge] = field(default_factory=dict)      # (holder role, held role) -> ratio, since, cost
    flows: Dict[str, dict] = field(default_factory=dict)                      # flow name -> stated flow facts
    present: dict = field(default_factory=dict)                               # the client's present assignment of the template
    members: Optional[set] = None                                             # the group's roles, when holdings do not show it
    settled: Dict[str, Dict[str, float]] = field(default_factory=dict)        # flow name -> {jurisdiction: tax actually paid}
    closed: frozenset = frozenset()                                           # (flow name, jurisdiction) declared final
    extra: Dict[str, dict] = field(default_factory=dict)                      # answered facts of companies the plan creates

    def entity(self, role, loc=None):
        """The role as an entity in loc: the client's own facts when it already sits there, otherwise only the facts
        that are not bound to a jurisdiction (no assumption is carried across a border)."""
        rf = self.roles.get(role)
        if rf is None:                                   # a company the plan creates: only what the plan gives it
            return Entity(role, loc, attrs=dict({"placed_by_plan": True, "created_by_plan": True}, **self.extra.get(role, {})))
        loc = loc or rf.loc
        if rf.loc == loc:
            return Entity(role, loc, rf.type, dict(rf.attrs))
        attrs = {k: v for k, v in rf.attrs.items() if k not in JURISDICTION_BOUND and k != "managed_from"}
        attrs["placed_by_plan"] = True
        return Entity(role, loc, rf.type, attrs)

    def place(self, role, loc):
        """The group company that plays `role` in loc (口径 D19): the client's own when it sits there; a company the plan
        creates when the client has none; when the client's own sits elsewhere, a new company ROLE_NEW — none of the
        three jurisdictions lets a company take its place of incorporation out (HK CO Part 17A and SG CA Part 10A admit
        foreign companies only; the Mainland has no such regime), so the client's own company cannot simply move."""
        rf = self.roles.get(role)
        if role in GROUP_ROLES and rf is not None and rf.loc != loc:
            return self.entity(role + NEW, loc)
        return self.entity(role, loc)

    def hold(self, holder, held, fallback=None, carries_stake=False):
        """The holding as the case states it; else the stake it carries over (fallback); else, when the plan creates
        one of the two companies, the plan's own design (wholly owned); else unknown — the ratio is asked, never filled.
        carries_stake: the edge takes over an existing stake, so a missing fallback is an unknown, not a design."""
        h = self.holds.get((holder, held))
        if h is not None:
            return HoldEdge(holder, held, h.ratio, h.since, h.cost)
        if fallback is not None:
            return HoldEdge(holder, held, fallback.ratio, fallback.since, fallback.cost)
        new = holder not in self.roles or held not in self.roles
        if new and not carries_stake:
            return HoldEdge(holder, held, 100.0, None, None, designed=True)
        return HoldEdge(holder, held, 100.0, None, None, unknown=("ratio",))   # the 100 is a placeholder; no plan is output

    def facts(self, name):
        return dict(self.flows.get(name, {}))


@dataclass
class Template:
    name: str
    fixed: tuple                                  # roles the case must place
    free: Dict[str, list]                         # role -> jurisdictions the plan may choose (None = role absent)
    structure: Dict[str, list]                    # structural variable -> values
    live: Callable[[Event], list]                 # event -> structural variables that matter for it
    infeasible: Callable[[Event, dict, Case], bool]
    build: Callable[[Event, dict, Case], Graph]

    def vars(self, event):
        return list(self.free) + self.live(event)

    def candidates(self, event, case):
        keys = self.vars(event)
        domains = [self.free[k] if k in self.free else self.structure[k] for k in keys]
        for values in product(*domains):
            a = dict(zip(keys, values))
            if not self.infeasible(event, a, case):
                yield a

    def check_case(self, event, case):
        missing = [r for r in self.fixed if r not in case.roles or not case.roles[r].loc]
        if event.exit and BUYER not in case.roles:
            missing.append(BUYER)
        return missing


def finish(graph: Graph, case) -> Graph:
    """口径 D21. Each flow with a party the plan creates drops the case's facts about that party's side and takes the
    facts stated under its own key instead; the key rides on the flow (attrs["fact_key"]) so that questions and answers
    about that side never touch the facts of the case's own structure."""
    for f in graph.flows:
        made = lambda x: x is not None and graph.entities[x].attrs.get("created_by_plan")
        if f.income == SHARE_TRANSFER:
            sides = ((f.payer, BUYER_SIDE), (f.payee, SELLER_SIDE), (f.target, TARGET_SIDE))
        elif f.income == IP_TRANSFER:                  # 口径 D22: its facts are the IP's and the present owner's (never created)
            sides = ((f.payer, frozenset()), (f.payee, PAYEE_SIDE))
        else:
            sides = ((f.payer, PAYER_SIDE), (f.payee, PAYEE_SIDE))
        new = sorted({x for x, fields in sides if made(x) and fields})
        if not new:
            continue
        drop = set().union(*(fields for x, fields in sides if made(x)))
        key = "%s~%s" % (f.id, "+".join("%s-%s" % (x, graph.entities[x].loc) for x in new))
        f.attrs = dict({k: v for k, v in f.attrs.items() if k not in drop}, **case.facts(key))
        f.attrs["fact_key"] = key
    return graph


def _repeat(flows, event, case=None):
    """A multi-year event repeats its recurring flows once a year; a repeat carries the year in its id ("up1@2027") and
    the first year's facts, overridden by any the case states under that id."""
    out = list(flows)
    for k in range(1, int(getattr(event, "years", 1) or 1)):
        for f in flows:
            if f.income in RECURRING:
                fid = "%s@%d" % (f.id, f.on.year + k)
                attrs = dict(f.attrs)
                if case is not None:
                    attrs.update(case.facts(fid))
                out.append(replace(f, id=fid, on=f.on.replace(year=f.on.year + k), attrs=attrs))
    return out


def _shift(flows, cross_year):
    """payment = cross_year: recurring payments are made in the following calendar year (dates move, flows do not vanish)."""
    if not cross_year:
        return flows
    return [replace(f, on=f.on.replace(year=f.on.year + 1)) if f.income not in (SHARE_TRANSFER, IP_TRANSFER) else f for f in flows]


def restructuring(event, case, hid=HOLD):
    """口径 D18. The plan puts a holding company hid between ULT and OP — one it creates (HOLD; HOLD_NEW when the
    client's own HOLD sits elsewhere) or the client's own HOLD that holds no stake in OP yet: ULT transfers its stake in
    OP to hid — a share transfer at the consideration the case states (unknown: the step's tax is unbounded, the engine
    asks), on the first modelled date, never repeated. hid's holding starts with the step: its length is the plan's to
    arrange (the step early enough), never ULT's. ULT holds a created hid wholly (the client's own: as stated); the new
    holdings carry the consideration as cost — the Mainland basis after a special reorganisation is the engine's reading
    (engine.read). None when there is no such step: ULT holds no stake in OP today, or the case states hid's stake."""
    stake = case.holds.get((ULT, OP))
    if stake is None or (hid, OP) in case.holds:
        return None
    facts = case.facts("reorg")
    value = facts.pop("amount", None)
    attrs = dict(facts, reorg_step=True, ratio=stake.ratio, max_ratio_12m=stake.ratio, reorg_horizon_years=int(event.years or 1))
    if stake.cost is not None:
        attrs["cost_basis"] = stake.cost
    if stake.since is not None:
        attrs["holding_months"] = months(stake.since, event.on)
    if value is None:
        attrs["amount_unknown"] = True
    v = None if value is None else float(value)
    step = FlowEdge("reorg", hid, ULT, SHARE_TRANSFER, v or 0.0, event.on, target=OP, attrs=attrs)
    up = case.hold(ULT, hid) if hid in case.roles else HoldEdge(ULT, hid, 100.0, None, v, designed=True)
    return step, up, HoldEdge(hid, OP, stake.ratio, None, v)


def unwinding(event, case, a):
    """口径 D19. The client's holding company HOLD (at L0) leaves the chain: dissolved (a[HOLD] None) or replaced by a new
    company HOLD_NEW in another jurisdiction (a[HOLD] = L1 != L0; Case.place). HOLD passes its stake in OP on and is
    wound up, both on the first modelled date, never repeated:
        unwind  HOLD's stake in OP to ULT (dissolution) or to HOLD_NEW, at its market value (the case's "unwind" amount)
        wind    HOLD's liquidation distribution to ULT: everything it distributes (the case's "wind" amount), split by the
                engine into a dividend part and a disposal of ULT's shares in HOLD
    An amount the case does not state leaves the step's tax unbounded: asked, never filled. The stake's new holder holds
    it from the step (the length is the plan's to arrange, as in D18), with the market value as cost; a new HOLD_NEW is
    wholly owned by ULT, which funds the purchase. No special reorganisation fits either step (59号 第七条 needs the
    transferee wholly owned by the transferor, 第五条 the equity received kept 12 months — the wound-up HOLD keeps
    nothing): they are plain disposals. Returns (entities, holds, flows, holder id), or None when HOLD stays where it
    is or the case states no stake of HOLD in OP."""
    rf, down = case.roles.get(HOLD), case.holds.get((HOLD, OP))
    if rf is None or down is None or a.get(HOLD) == rf.loc:
        return None
    old = case.entity(HOLD)
    old.attrs["wound_up_by_plan"] = True
    up = case.hold(ULT, HOLD)
    facts = case.facts("unwind")
    value = facts.pop("amount", None)
    attrs = dict(facts, unwind_step=True, ratio=down.ratio, max_ratio_12m=down.ratio)
    if down.cost is not None:
        attrs["cost_basis"] = down.cost
    if down.since is not None:
        attrs["holding_months"] = months(down.since, event.on)
    if value is None:
        attrs["amount_unknown"] = True
    v = None if value is None else float(value)
    wind = case.facts("wind")
    paid = wind.pop("amount", None)
    if paid is None:
        wind["amount_unknown"] = True
    ents = {HOLD: old}
    if a.get(HOLD) is None:                                 # dissolution: ULT holds its share of the stake directly
        holder = ULT
        holds = [up, HoldEdge(ULT, OP, up.ratio * down.ratio / 100.0, None, None if v is None else v * up.ratio / 100.0,
                              unknown=up.unknown)]
    else:
        ents[HOLD + NEW] = case.place(HOLD, a[HOLD])
        holder = HOLD + NEW
        holds = [up, HoldEdge(ULT, holder, 100.0, None, v, designed=True), HoldEdge(holder, OP, down.ratio, None, v)]
    flows = [FlowEdge("unwind", holder, HOLD, SHARE_TRANSFER, v or 0.0, event.on, target=OP, attrs=attrs),
             FlowEdge("wind", HOLD, ULT, LIQUIDATION, float(paid) if paid is not None else 0.0, event.on, attrs=wind)]
    return ents, holds, flows, holder


def chain(event, a, case):
    """Who holds OP under the candidate (holding and repatriation): ULT directly; the client's own HOLD where it sits;
    a holding company the restructuring step puts in (D18); or, when the client's HOLD leaves the chain, the
    unwinding (D19). Returns (entities, holds, flows, holder id)."""
    ents = {OP: case.entity(OP), ULT: case.entity(ULT)}
    un = unwinding(event, case, a)
    if un is not None:
        more, holds, flows, holder = un
        ents.update(more)
        return ents, holds, flows, holder
    if not a.get(HOLD):
        return ents, [case.hold(ULT, OP)], [], ULT              # as stated; unstated: the ratio is asked
    e = case.place(HOLD, a[HOLD])
    ents[e.id] = e
    step = restructuring(event, case, e.id)
    if step is None:
        # ULT owns the holding company (as stated); the holding company holds OP (as stated for that pair, else the
        # stake ULT holds today)
        return ents, [case.hold(ULT, e.id), case.hold(e.id, OP, case.holds.get((ULT, OP)), carries_stake=True)], [], e.id
    return ents, list(step[1:]), [step[0]], e.id


# ---- holding: ULT -> (HOLD) -> OP; upward distribution as dividend or interest; exit by selling OP or HOLD
def build_holding(event, a, case):
    ents, holds, flows, holder = chain(event, a, case)
    if event.dividend:
        income = INTEREST if a.get("financing") == DEBT else DIVIDEND
        flows.append(FlowEdge("up1", OP, holder, income, event.dividend, event.on, attrs=case.facts("up1")))
        if holder != ULT:
            flows.append(FlowEdge("up2", holder, ULT, DIVIDEND, event.onward or event.dividend, event.on, attrs=case.facts("up2")))
    if event.exit:
        ents[BUYER] = case.entity(BUYER)
        if a.get("exit_route") == INDIRECT:
            flows.append(FlowEdge("exit", BUYER, ULT, SHARE_TRANSFER, event.exit, event.exit_on or event.on, target=holder, attrs=case.facts("exit")))
        else:
            flows.append(FlowEdge("exit", BUYER, holder, SHARE_TRANSFER, event.exit, event.exit_on or event.on, target=OP, attrs=case.facts("exit")))
    return finish(Graph(ents, holds, _shift(_repeat(flows, event, case), a.get("payment")), case.members), case)


HOLDING = Template(
    "holding", fixed=(OP, ULT), free={HOLD: OPTIONAL},
    structure={"financing": [EQUITY, DEBT], "payment": [False, True], "exit_route": [DIRECT, INDIRECT]},
    live=lambda e: (["financing", "payment"] if e.dividend else []) + (["exit_route"] if e.exit else []),
    infeasible=lambda e, a, c: a.get(HOLD) is None and a.get("exit_route") == INDIRECT,   # nothing to sell indirectly
    build=build_holding)


# ---- ip: ULT holds OP and IPCO; OP pays a royalty to IPCO (IPCO absent = OP owns the IP itself)
def ip_owner(case):
    """Who holds the IP OP uses in the client's present structure: its IP company (stated, or placed by the present
    assignment), else OP itself. (id, jurisdiction)."""
    rf = case.roles.get(IPCO)
    if rf is not None:
        return IPCO, rf.loc
    if case.present.get(IPCO):
        return IPCO, case.present[IPCO]
    return OP, case.roles[OP].loc


MARKET, BOOK = "MARKET", "BOOK"                       # the IP step: a sale at market value, or a transfer at book value (D28)


def book_transfer_ok(case, a):
    """口径 D28. 财税〔2014〕109号 第三条 with 公告2015年第40号 第一条: a transfer at book value only between resident
    enterprises one of which holds the other wholly and directly, or which the same resident enterprise(s) hold wholly
    and directly. In the ip template OP and the IP company are both held by ULT: both in the Mainland, ULT a Mainland
    company holding each wholly (a company the plan creates: by design)."""
    buyer = case.place(IPCO, a[IPCO]) if a.get(IPCO) else case.entity(OP)
    now = ip_owner(case)
    ult = case.roles.get(ULT)
    if (buyer.id, buyer.loc) == now or buyer.loc != "CN" or now[1] != "CN" or ult is None or ult.loc != "CN":
        return False

    def whole(role):
        h = case.holds.get((ULT, role))
        if h is not None:
            return h.ratio >= 100.0 - 1e-9
        return role not in case.roles                   # created by the plan: wholly ULT's

    return whole(now[0]) and whole(buyer.id)


def ip_transfer(event, case, buyer, seller, mode=MARKET):
    """口径 D22. The step `iptx`: the new owner buys the IP from the present one at the price the case states (its market
    value at the transfer; unknown: the step's tax is unbounded, the engine asks — never filled), on the first modelled
    date, never repeated. Its facts (the IP's kind, the seller's tax basis and allowances, the contract's terms) are the
    case's "iptx" facts; ip_horizon_years: the modelled years the buyer's amortisation falls in."""
    facts = case.facts("iptx")
    value = facts.pop("amount", None)
    attrs = dict(facts, ip_transfer_step=True, ip_horizon_years=int(event.years or 1), ip_transfer_mode=mode)
    if value is None:
        attrs["amount_unknown"] = True
    return FlowEdge("iptx", buyer, seller, IP_TRANSFER, float(value) if value is not None else 0.0, event.on, attrs=attrs)


def build_ip(event, a, case):
    """口径 D22 (replacing D19's marker): a candidate in which another company holds the IP than today has the IP
    transferred (ip_transfer) — the seller's gain, the Mainland's withholding, VAT and stamp duty and the buyer's
    amortisation are computed like every flow's tax. The present owner stays in the graph: it keeps the proceeds, and
    what it does with them is outside the template."""
    ents = {OP: case.entity(OP), ULT: case.entity(ULT)}
    holds, flows = [case.hold(ULT, OP)], []
    owner = (OP, ents[OP].loc)
    if a.get(IPCO):
        e = case.place(IPCO, a[IPCO])
        ents[e.id] = e
        holds.append(case.hold(ULT, e.id))
        flows.append(FlowEdge("roy", OP, e.id, ROYALTY, event.royalty, event.on, attrs=case.facts("roy")))
        owner = (e.id, e.loc)
    now, steps = ip_owner(case), ()
    if owner != now:
        if now[0] not in ents:                          # the present owner, which this candidate no longer uses
            ents[now[0]] = case.entity(now[0]) if now[0] in case.roles else Entity(now[0], now[1])
            holds.append(case.hold(ULT, now[0]))
        flows.append(ip_transfer(event, case, owner[0], now[0], a.get("ip_transfer") or MARKET))
    return finish(Graph(ents, holds, _shift(_repeat(flows, event, case), a.get("payment")), case.members, steps), case)


IP = Template(
    "ip", fixed=(OP, ULT), free={IPCO: OPTIONAL}, structure={"payment": [False, True], "ip_transfer": [MARKET, BOOK]},
    live=lambda e: ["payment", "ip_transfer"],
    infeasible=lambda e, a, c: a.get("ip_transfer") == BOOK and not book_transfer_ok(c, a),   # 口径 D28
    build=build_ip)


# ---- services: a group company (held by ULT like OP) performs services for OP against a fee
def build_services(event, a, case):
    """The servicer the candidate places: the client's own where it sits, else a new company (Case.place) — taking the
    service over needs no asset to move, so there is no step to tax; the client's own servicer just stops serving OP."""
    srv = case.place(SERVICER, a[SERVICER])
    ents = {OP: case.entity(OP), ULT: case.entity(ULT), srv.id: srv}
    holds = [case.hold(ULT, OP), case.hold(ULT, srv.id)]
    flows = [FlowEdge("svc", OP, srv.id, SERVICE_FEE, event.service_fee, event.on, attrs=case.facts("svc"))]
    return finish(Graph(ents, holds, _shift(_repeat(flows, event, case), a.get("payment")), case.members), case)


SERVICES = Template(
    "services", fixed=(OP, ULT), free={SERVICER: ANYWHERE}, structure={"payment": [False, True]},
    live=lambda e: ["payment"],
    infeasible=lambda e, a, c: False,
    build=build_services)


# ---- repatriation: the same chain as holding, but the money comes out as a dividend, a capital reduction or a liquidation
def build_repatriation(event, a, case):
    ents, holds, flows, holder = chain(event, a, case)
    flows.append(FlowEdge("out", OP, holder, a["repatriation"], event.dividend, event.on, attrs=case.facts("out")))
    if holder != ULT:
        flows.append(FlowEdge("up2", holder, ULT, DIVIDEND, event.onward or event.dividend, event.on, attrs=case.facts("up2")))
    return finish(Graph(ents, holds, _shift(_repeat(flows, event, case), a.get("payment")), case.members), case)


REPATRIATION = Template(
    "repatriation", fixed=(OP, ULT), free={HOLD: OPTIONAL},
    structure={"repatriation": [DIVIDEND, CAPITAL_REDUCTION, LIQUIDATION], "payment": [False, True]},
    live=lambda e: ["repatriation", "payment"],
    infeasible=lambda e, a, c: False,
    build=build_repatriation)

# ---- financing: OP borrows from an outside bank (no holding link, so its tax is its own); the loan terms are facts
def build_financing(event, a, case):
    ents = {OP: case.entity(OP), ULT: case.entity(ULT), LENDER: case.entity(LENDER, a[LENDER])}
    if LENDER not in case.roles:
        ents[LENDER].type = "BANK_FI"                             # an outside lender the plan places is a bank by default
    holds = [case.hold(ULT, OP)]
    flows = [FlowEdge("int", OP, LENDER, INTEREST, event.interest, event.on, attrs=case.facts("int"))]
    return finish(Graph(ents, holds, _shift(_repeat(flows, event, case), a.get("payment")), case.members), case)


FINANCING = Template(
    "financing", fixed=(OP, ULT), free={LENDER: ANYWHERE}, structure={"payment": [False, True]},
    live=lambda e: ["payment"],
    infeasible=lambda e, a, c: False,
    build=build_financing)

# ---- inbound services: the subject performs services for an outside client abroad (no holding link; the group is declared)
def build_inbound_services(event, a, case):
    ents = {SERVICER: case.entity(SERVICER), CLIENT: case.entity(CLIENT)}
    flows = [FlowEdge("fee", CLIENT, SERVICER, SERVICE_FEE, event.service_fee, event.on, attrs=case.facts("fee"))]
    return finish(Graph(ents, [], _shift(_repeat(flows, event, case), a.get("payment")), case.members or {SERVICER}), case)


INBOUND_SERVICES = Template(
    "inbound_services", fixed=(SERVICER, CLIENT), free={}, structure={"payment": [False, True]},
    live=lambda e: [],
    infeasible=lambda e, a, c: False,
    build=build_inbound_services)

TEMPLATES = {t.name: t for t in (HOLDING, IP, SERVICES, REPATRIATION, FINANCING, INBOUND_SERVICES)}
CHAIN = ("holding", "repatriation")                # the templates that decide who holds OP


def composite(names):
    """A case running several activities at once: one template each, over the same group. Their roles,
    holdings and flows together; one candidate per combination of the parts' structures, every combination evaluated —
    the activities couple through what a jurisdiction or a company sees as a whole (Pillar Two by jurisdiction, the
    Mainland's indirect credit and CFC test, pooled credits), so they are not planned one by one. A free role two parts
    share must sit in one place; the cross-year payment choice is one for every recurring flow (named "payment" in each
    part). OP's holder is the chain part's (holding or repatriation) when there is one: another part's direct ULT -> OP
    edge is not added beside it. Two parts building a flow of the same name (holding and repatriation both distribute
    OP's profit) cannot be combined."""
    names = list(dict.fromkeys(names))
    parts = sorted((TEMPLATES[n] for n in names), key=lambda t: (t.name not in CHAIN, names.index(t.name)))
    flows_of = {"holding": {"up1", "up2", "exit", "reorg", "unwind", "wind"}, "repatriation": {"out", "up2", "reorg", "unwind", "wind"}, "ip": {"roy"},
                "services": {"svc"}, "financing": {"int"}, "inbound_services": {"fee"}}
    for i, a in enumerate(parts):
        for b in parts[i + 1:]:
            if flows_of[a.name] & flows_of[b.name]:
                raise ValueError("templates %s and %s build the same flows: not combinable" % (a.name, b.name))
    free, structure = {}, {}
    for t in parts:
        for role, dom in t.free.items():
            free[role] = [x for x in free[role] if x in dom] if role in free else list(dom)
        for k, dom in t.structure.items():
            structure.setdefault(k, list(dom))

    def own(t, a):
        return {k: v for k, v in a.items() if k in t.free or k in t.structure}

    def live(e):
        return list(dict.fromkeys(k for t in parts for k in t.live(e)))

    def infeasible(e, a, c):
        return any(t.infeasible(e, own(t, a), c) for t in parts)

    def build(event, a, case):
        ents, holds, flows, held_by, steps = {}, [], [], {}, ()
        for t in parts:
            g = t.build(event, own(t, a), case)
            steps += tuple(x for x in g.unmodelled if x not in steps)
            for k, e in g.entities.items():
                ents.setdefault(k, e)
            for h in g.holds:
                if h.held in held_by and held_by[h.held] != t.name:
                    continue                                # the chain part already decided who holds this company
                if any((x.holder, x.held) == (h.holder, h.held) for x in holds):
                    continue
                held_by.setdefault(h.held, t.name)
                holds.append(h)
            flows.extend(g.flows)
        return Graph(ents, holds, flows, case.members, steps)

    return Template("+".join(t.name for t in parts), fixed=tuple(dict.fromkeys(r for t in parts for r in t.fixed)), free=free,
                    structure=structure, live=live, infeasible=infeasible, build=build)


def template_of(name):
    """A template by name; "a+b" composes them (composite)."""
    if name in TEMPLATES:
        return TEMPLATES[name]
    if name not in _COMPOSED:
        _COMPOSED[name] = composite(name.split("+"))
    return _COMPOSED[name]


_COMPOSED = {}


# ---- settled flows pin the structure: a candidate that would undo a flow some jurisdiction has already taxed is no plan
def same_settled(g: Graph, g0: Graph, settled) -> bool:
    for name in settled:
        f, f0 = next((x for x in g.flows if x.id == name), None), next((x for x in g0.flows if x.id == name), None)
        if f is None or f0 is None:
            return False
        key = lambda gr, x: (x.income, x.amount, x.on, gr.entities[x.payer].loc, gr.entities[x.payee].loc,
                             gr.entities[x.target].loc if x.target else None, x.payer, x.payee, x.target)
        if key(g, f) != key(g0, f0):
            return False
    return True


# ---- subject view
def bearer(flow: FlowEdge, item):
    """Who bears an item: the payer for its deduction or under a gross-up clause, otherwise the recipient."""
    return flow.payer if item.borne_by == "payer" else flow.payee


def view(labels, subject=GROUP, members=None):
    """Cash tax within the horizon borne by the subject: the group (its members, from the holding graph), one role,
    or one jurisdiction code (every bearer, group or not)."""
    total = 0.0
    for lb in labels.values():
        for it in lb.items:
            if it.deferred:
                continue
            who = bearer(lb.flow, it)
            if (subject == GROUP and (members is None or who in members)) or subject == who or subject == it.jur:
                total += lb.flow.amount * it.effective / 100.0
    return round(total, 2)


def views(b: Bounds, subject=GROUP, graph=None):
    members = graph.group() if graph is not None else None
    return view(b.L_lo, subject, members), view(b.L_hi, subject, members)
