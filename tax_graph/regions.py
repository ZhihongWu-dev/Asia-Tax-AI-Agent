"""Jurisdiction regions (优化方案 v2 §0, §2 item 3): every rule, tax item, question, action and deadline belongs to the
set of jurisdictions whose law produced it. With CN, HK, SG that gives seven regions — CN, HK, SG, CN∩HK, CN∩SG, HK∩SG,
CN∩HK∩SG — and the same construction holds for any number of jurisdictions (v2 adds VN without change here).

    rule_region(rule)          the instruments the rule encodes: a treaty rule -> both sides; a domestic rule -> its own
    item_region(item, ...)     the laws that produced a number: the taxing jurisdiction, the other side of any treaty rule
                               it cites, the jurisdictions whose tax it credits, and a CFC's own jurisdiction
    absolute(elem, field, facts)   a need's address: "HOLD.residence_cert", "flow:up1.holding_months" (not "payee.x")
"""
import re

from .model import CFC_INCLUSION, JURISDICTIONS

TREATY_ID = re.compile(r"^([a-z]{2})-([a-z]{2})\.")
DOMESTIC_ID = re.compile(r"^([a-z]{2})\.")


def rule_region(rule):
    m = TREATY_ID.match(rule.id)
    if m:
        return frozenset({m.group(1).upper(), m.group(2).upper()})
    taxing = getattr(rule.scope, "taxing", None)
    if taxing in JURISDICTIONS:
        return frozenset({taxing})
    m = DOMESTIC_ID.match(rule.id)
    if m and m.group(1).upper() in JURISDICTIONS:
        return frozenset({m.group(1).upper()})
    return frozenset()


def item_region(item, label, rules_by_id, graph=None):
    s = {item.jur} if item.jur else set()
    for c in item.cites:
        r = rules_by_id.get(c)
        if r is not None and TREATY_ID.match(r.id):
            s |= rule_region(r)
    if (item.credit or 0) > 0 or (item.creditable or 0) > 0:
        s |= {x.jur for x in label.items if x.jur and x.jur != item.jur and x.levy == "income" and not x.deduction}
    if graph is not None and label.flow is not None and label.flow.income == CFC_INCLUSION:
        payer = graph.entities.get(label.flow.payer)
        if payer is not None and payer.loc:
            s.add(payer.loc)
    return frozenset(j for j in s if j)


def order_key(region):
    """Single jurisdictions first, then pairs, then the triple; inside each size the jurisdictions' own order."""
    idx = {j: i for i, j in enumerate(JURISDICTIONS)}
    return (len(region), tuple(sorted(idx.get(j, 99) for j in region)))


def name(region):
    return "∩".join(sorted(region, key=lambda j: JURISDICTIONS.index(j) if j in JURISDICTIONS else 99)) or "—"


def all_regions():
    from itertools import combinations
    out = []
    for k in range(1, len(JURISDICTIONS) + 1):
        out += [frozenset(c) for c in combinations(JURISDICTIONS, k)]
    return sorted(out, key=order_key)


def absolute(elem, field, facts, suffix=""):
    """The address of a fact a rule reads on one flow: the role for payer / payee facts, the flow for flow facts."""
    if elem in ("payer", "payee"):
        who = facts.get(("_meta", elem))
        return "%s.%s%s" % (who, field, suffix) if who else None
    if elem == "flow":
        fid = facts.get(("_meta", "flow"))
        return "flow:%s.%s%s" % (fid, field, suffix) if fid else None
    return None


def absolute_key(rel_key, flow):
    """'payee.after_tax_profit' on flow (payer OP, payee HOLD) -> 'HOLD.after_tax_profit'; keys that are already
    absolute (e.g. 'HOLD.managed_from') pass through."""
    elem, _, rest = rel_key.partition(".")
    if elem == "payer":
        return "%s.%s" % (flow.payer, rest)
    if elem == "payee":
        return "%s.%s" % (flow.payee, rest)
    if elem == "flow":
        return "flow:%s.%s" % (flow.attrs.get("fact_key") or flow.id, rest)       # 口径 D21
    return rel_key
