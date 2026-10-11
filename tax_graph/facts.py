"""facts_for(graph, flow): the (element, field) -> value dictionary one flow's rules read.

Stated facts come from Entity.attrs and FlowEdge.attrs; derived facts come from the graph itself (holding ratios,
holding periods, residence in the source jurisdiction, what a transferred target holds). Absent = unknown = U.
"""
from .model import IP_TRANSFER, ROYALTY, SHARE_TRANSFER, CN, HK, SG, Graph, FlowEdge, months
from .params import Params
from .rules.procedure_common import add_months

_P = []


def params():
    if not _P:
        _P.append(Params())
    return _P[0]


def onpay_ratio(graph: Graph, f: FlowEdge, window_months):
    """cn.sta.2018-09 #i2(一): share of the income the recipient pays on, within the window after receipt, to
    residents of a third jurisdiction (neither the source state nor the recipient's own), as the flow graph shows it."""
    src, own = source_of(graph, f), graph.entities[f.payee].loc
    paid = 0.0
    for g in graph.flows:
        if g.payer != f.payee or g.income in (SHARE_TRANSFER, IP_TRANSFER):       # a purchase price is not income passed on
            continue
        gap = months(f.on, g.on)
        if gap is None or gap < 0 or gap > window_months or g.on < f.on:
            continue
        if graph.entities[g.payee].loc in (src, own):
            continue
        paid += g.amount
    return round(100.0 * paid / f.amount, 6) if f.amount else 0.0


def own_later(graph: Graph, f: FlowEdge, within_months):
    """The structure's own share transfers in the window after f (口径 D19): what they break is a fact, not a plan item."""
    end = add_months(f.on, within_months)
    return [g for g in graph.flows if g.income == SHARE_TRANSFER and g.id != f.id and g.target and f.on <= g.on <= end]


def leaves(graph: Graph, g: FlowEdge, y):
    """g takes y out of the group: y itself, or a company above it, sold to a buyer outside the group."""
    return g.payer not in graph.group() and (g.target == y or graph.chain_ratio(g.target, y) > 0)


# the window after an intragroup transfer within which the transferee's leaving the group undoes the relief, by the
# regime that gives it: stamp duty where the target is (HK SDO s45(5A); SG 2014 Rules r 7(1)), else Hong Kong's FSIE
# intragroup relief of the seller (s15OB)
CLAWBACK_YEARS = {HK: "hk.stamp.clawback_years", SG: "sg.stamp.clawback_years"}
HEADLINE = {CN: "cn.eit.rate", HK: "hk.profits.rate_corp", SG: "sg.corp.rate"}      # each jurisdiction's statutory rate
FIXED = "_fixed"            # (FIXED, "flow.field"): a plan-controlled field the structure's own flows fix — a fact


def fix(facts, field, value):
    facts[("flow", field)] = value
    facts[(FIXED, "flow." + field)] = True


def source_of(graph: Graph, f: FlowEdge):
    """Where the income arises: the investee for a share transfer (cn.reg.eit#7), otherwise the payer."""
    if f.income == SHARE_TRANSFER and f.target:
        return graph.entities[f.target].loc
    return graph.entities[f.payer].loc


def facts_for(graph: Graph, f: FlowEdge):
    payer, payee = graph.entities[f.payer], graph.entities[f.payee]
    facts = {("_meta", "flow"): f.attrs.get("fact_key") or f.id, ("_meta", "payer"): f.payer, ("_meta", "payee"): f.payee}
    for k, v in payer.attrs.items():
        facts[("payer", k)] = v
    for k, v in payee.attrs.items():
        facts[("payee", k)] = v
    for k, v in f.attrs.items():
        facts[("flow", k)] = v
    src = source_of(graph, f)
    # 口径 D21: a company the plan creates on the source side — the source jurisdiction's statutory rate is its headline
    # rate; a new company is not listed and its dividends (ordinary shares, by design) are not deductible
    origin = graph.entities[f.target] if f.income == SHARE_TRANSFER and f.target else payer
    if origin.attrs.get("created_by_plan"):
        Pp = params()
        facts.setdefault(("flow", "foreign_headline_rate"), Pp[HEADLINE[src]] if src in HEADLINE else None)
        facts.setdefault(("flow", "listed_market_trade"), False)
        if f.income in ("DIVIDEND", "DISTRIBUTION") or f.income == SHARE_TRANSFER:
            facts.setdefault(("flow", "deductible_at_payer"), False)
    facts[("payee", "payee_in_source_jur")] = payee.loc == src
    facts[("payee", "payee_resident_in_cn")] = payee.loc == CN
    # a residence certificate is a fact about years: valid for the flow's year unless circumstances changed before it
    years, changed = payee.attrs.get("cert_years"), payee.attrs.get("circumstances_changed_on")
    if years is not None and "residence_cert" not in payee.attrs:
        facts[("payee", "residence_cert")] = f.on.year in years and not (changed and changed <= f.on)
    accrued = f.attrs.get("accrued_on") or f.on         # holding periods are measured at accrual (hk s15M(2))
    facts.setdefault(("payee", "payee_is_government"), payee.type == "GOVERNMENT")
    facts.setdefault(("payee", "payee_is_financial_institution"), payee.type == "BANK_FI")
    facts[("flow", "income")] = f.income
    facts[("flow", "amount")] = f.amount
    facts[("flow", "date_of_payment")] = f.on
    facts.setdefault(("flow", "authority_action"), "none")          # a dispute exists only when stated
    facts.setdefault(("flow", "prior_map_outcome"), "none")
    as_at, period_to = f.attrs.get("as_at"), f.attrs.get("period_to") or f.on
    facts.setdefault(("flow", "claim_is_for_prior_year"), bool(as_at) and period_to.year < as_at.year)
    if f.income == SHARE_TRANSFER:
        facts.setdefault(("flow", "consideration"), f.amount)
        h = graph.holding(f.payee, f.target) if f.target else None
        if h is not None:
            facts.setdefault(("flow", "cost_basis"), h.cost)
            facts.setdefault(("flow", "max_ratio_12m"), h.ratio)        # any holding within the look-back counts
            facts.setdefault(("flow", "ratio"), h.ratio)
            facts.setdefault(("flow", "holding_months"), months(h.since, accrued))
        # association (HK SDO s45(2); SG 2014 Rules r 3): one owns the other, or a third owns both, at the least link
        facts.setdefault(("flow", "associated_ratio"), max(
            [graph.chain_ratio(f.payer, f.payee), graph.chain_ratio(f.payee, f.payer)]
            + [min(graph.chain_ratio(e, f.payer), graph.chain_ratio(e, f.payee)) for e in graph.entities if e not in (f.payer, f.payee)]))
        facts.setdefault(("flow", "reorg_step"), False)             # 口径 D18: only the step the template generates is one
        if f.attrs.get("reorg_step"):                               # the transfer that puts HOLD between ULT and OP
            ctl = graph.holding(f.payee, f.payer)
            acq = graph.holding(f.payer, f.target) if f.target else None
            facts.setdefault(("flow", "reorg_control_ratio"), ctl.ratio if ctl else 0.0)
            facts.setdefault(("flow", "reorg_acquired_ratio"), acq.ratio if acq else 0.0)
            facts.setdefault(("flow", "reorg_same_residence"), payer.loc == payee.loc)
            facts.setdefault(("flow", "reorg_buyer_resident_in_cn"), payer.loc == CN)
            # 59号 第五条(五) / 第七条(一): the transferor keeps the equity it received 12 months, its shares in the
            # transferee 3 years — the structure's own later sale of the transferee breaks them
            Pp = params()
            sold = [g for g in own_later(graph, f, 12 * int(Pp["cn.reorg.commitment_years"]))
                    if g.payee == f.payee and g.target == f.payer]
            if sold:
                fix(facts, "reorg_commitment_3y", False)
            if any(g.on <= add_months(f.on, int(Pp["cn.reorg.keep_months"])) for g in sold):
                fix(facts, "reorg_shares_kept_12m", False)
        if f.target:
            # intragroup: buyer and seller linked through the holding graph (either direction or a common holder)
            linked = graph.chain_ratio(f.payer, f.payee) > 0 or graph.chain_ratio(f.payee, f.payer) > 0 or any(
                graph.chain_ratio(e, f.payer) > 0 and graph.chain_ratio(e, f.payee) > 0
                for e in graph.entities if e not in (f.payer, f.payee))
            facts.setdefault(("flow", "intragroup_transfer"), linked)
            Pp = params()
            years = int(Pp[CLAWBACK_YEARS.get(graph.entities[f.target].loc, "hk.fsie.intragroup_clawback_years")])
            later = own_later(graph, f, 12 * years)
            if any(leaves(graph, g, f.payer) for g in later):          # the transferee sold out of the group in the window
                fix(facts, "clawback_event_within_2y", True)
            if any(g.payee == f.payer and g.target == f.target for g in later):   # SG r 7(1)(b): the asset disposed of
                fix(facts, "asset_disposed_within_2y", True)
            ca, cc = f.attrs.get("ceased_associated_on"), f.attrs.get("ceased_chargeable_on")
            if ca is not None or cc is not None:
                facts.setdefault(("flow", "clawback_event_within_2y"),
                                 any(d is not None and 0 <= (d - f.on).days <= 2 * 365 for d in (ca, cc)))
            under = graph.subtree(f.target) - {f.target}
            facts.setdefault(("flow", "indirect_cn_target"),
                             graph.entities[f.target].loc != CN and any(graph.entities[e].loc == CN for e in under))
    else:
        if f.income == "DIVIDEND":                                  # 口径 D18: no restructuring step behind it unless the
            facts.setdefault(("flow", "reorg_special_applied"), False)   # engine finds one (engine.read)
        h = graph.holding(f.payee, f.payer)                         # the recipient's holding in the payer
        if h is not None:
            facts.setdefault(("flow", "direct_ratio"), h.ratio)
            facts.setdefault(("flow", "ratio"), h.ratio)
            facts.setdefault(("flow", "holding_months"), months(h.since, accrued))
        else:                                                       # holdings are core: no edge means no direct holding
            facts.setdefault(("flow", "direct_ratio"), 0.0)
            facts.setdefault(("flow", "ratio"), 0.0)
        # back-to-back payments: what the recipient pays on to third-jurisdiction residents inside the window
        facts.setdefault(("payee", "onpay_ratio_12m"), onpay_ratio(graph, f, int(params()["cn.bo.onpay_window"])))
    if f.income == IP_TRANSFER:                                     # 口径 D22: the IP transfer step
        facts.setdefault(("flow", "consideration"), f.amount)
        # 财税〔2010〕111号 第四条: one holds the other wholly (directly or indirectly) — the reduction is denied; sisters
        # wholly held by one holder are not named there (a judgement, the rule's Discretion)
        held = max(graph.chain_ratio(f.payer, f.payee), graph.chain_ratio(f.payee, f.payer))
        facts.setdefault(("flow", "ip_parties_100pct_held"), held >= 100.0 - 1e-9)
        facts.setdefault(("flow", "ip_parties_100pct_sisters"), any(
            graph.chain_ratio(e, f.payer) >= 100.0 - 1e-9 and graph.chain_ratio(e, f.payee) >= 100.0 - 1e-9
            for e in graph.entities if e not in (f.payer, f.payee)))
        # 印花税法 第一条: a party in the Mainland writes or uses the instrument there
        facts.setdefault(("flow", "cn_party"), payer.loc == CN or payee.loc == CN)
        # ITA s19B(10A)(a)(i): only a seller with Singapore deductions for creating the IP can bar the buyer's allowance
        if payee.loc != SG:
            facts.setdefault(("flow", "seller_had_sg_creation_deductions"), False)
        if f.attrs.get("ip_transfer_mode") == "BOOK":              # 口径 D28: 增值税法 第五条、第十九条 — a deemed sale at
            facts.setdefault(("flow", "price_includes_vat"), False)   # market value, no price that could include the VAT
        if payer.loc == CN:                                         # 111号 第三条: only an export can be a restricted one
            facts.setdefault(("flow", "technology_export_restricted"), False)
    if f.income == ROYALTY and payee.attrs.get("created_by_plan"):
        # 口径 D22: an IP company the plan creates holds IP it bought (the iptx step) and does no R&D of its own in the
        # model: no qualifying R&D expenditure (Cap 112 Sch 17FC s5(3)(c) excludes the acquisition) — the R&D fraction is
        # nil whatever the other expenditure is, so the acquisition price stands for it (0 while unknown changes nothing)
        bought = [g for g in graph.flows if g.income == IP_TRANSFER and g.payer == f.payee]
        facts.setdefault(("flow", "qualifying_rd_expenditure"), 0.0)
        facts.setdefault(("flow", "non_qualifying_expenditure"), float(bought[0].amount) if bought else 0.0)
    # residence-side status the graph knows: a Hong Kong entity is a Hong Kong resident person; an entity whose
    # holding group reaches another jurisdiction belongs to an MNE group (hk s15H) / is a relevant group entity (sg s10L)
    group = graph.component(f.payee)
    multi = any(graph.entities[e].loc != payee.loc for e in group)
    facts.setdefault(("payee", "hk_resident_or_pe"), payee.loc == HK)
    facts.setdefault(("payee", "is_mne_member"), multi)
    facts.setdefault(("payee", "is_relevant_group_entity"), multi and payee.loc == SG)
    # Cap 112 s58C(1): an entity below any two of the three Schedule 17I thresholds keeps no master / local file
    rev, assets, staff = (payer.attrs.get(k) for k in ("revenue", "total_assets", "employees"))
    if rev is not None and assets is not None and staff is not None and ("payer", "hk_tp_small_entity") not in facts:
        Pp = params()
        below = sum([rev <= Pp["hk.tp.threshold_revenue"], assets <= Pp["hk.tp.threshold_assets"], staff <= Pp["hk.tp.threshold_employees"]])
        facts[("payer", "hk_tp_small_entity")] = below >= 2
    loc = f.attrs.get("service_location")                   # where the work was physically done, a jurisdiction code
    share = f.attrs.get("service_onshore_share")            # or the share of the work done in the source jurisdiction, %
    if loc is not None:
        facts.setdefault(("flow", "service_performed_in_source"), loc == src)
        if loc == src:                                              # 口径 D23: done in the Mainland, not consumed on site abroad
            facts.setdefault(("flow", "service_consumed_on_site_abroad"), False)
        facts.setdefault(("flow", "service_performed_in_residence"), loc == payee.loc)
        facts.setdefault(("flow", "service_onshore_share"), 100.0 if loc == src else 0.0)
    elif share is not None:
        facts.setdefault(("flow", "service_performed_in_source"), float(share) > 0)
        facts.setdefault(("flow", "service_performed_in_residence"), float(share) < 100 and payee.loc != src)
    if ("payee", "payee_is_related") not in facts:         # ownership link in either direction or a common holder
        related = graph.chain_ratio(f.payee, f.payer) > 0 or graph.chain_ratio(f.payer, f.payee) > 0 or any(
            graph.chain_ratio(e, f.payer) > 0 and graph.chain_ratio(e, f.payee) > 0
            for e in graph.entities if e not in (f.payer, f.payee))
        facts[("payee", "payee_is_related")] = related
    if f.income == "INTEREST" and facts.get(("payee", "payee_is_related")) is False:   # 口径 D25: 统借统还 is a group's
        facts.setdefault(("flow", "unified_borrowing_relending"), False)               # own on-lending
    # beneficial owner through a 100% owner in the same jurisdiction (cn.sta.2018-09 #i3), from the holding chain
    if ("payee", "bo_via_100pct_owner") not in facts:
        owners = [e for e in graph.entities.values()
                  if e.id != payee.id and graph.chain_ratio(e.id, payee.id) >= 100.0 - 1e-9]
        facts[("payee", "bo_via_100pct_owner")] = any(
            o.loc == payee.loc and o.attrs.get("bo_safe_harbour") is True for o in owners) if owners else False
    # 口径 D31: a party the effective-management variant moved to the Mainland is a Mainland resident for income tax only;
    # VAT and stamp duty read where it is established (its seat) — the facts that turn on a party's place, by the seat
    target = graph.entities[f.target] if f.target else None
    if any(e is not None and e.attrs.get("seat") for e in (payer, payee, target)):
        seat = lambda e: e.attrs.get("seat") or e.loc
        ssrc = seat(target) if f.income == SHARE_TRANSFER and target is not None else seat(payer)
        over = {("payee", "payee_in_source_jur"): seat(payee) == ssrc}
        if f.income == IP_TRANSFER and "cn_party" not in f.attrs:
            over[("flow", "cn_party")] = seat(payer) == CN or seat(payee) == CN
        facts[("_meta", "seat")] = tuple(sorted(over.items()))
    return facts
