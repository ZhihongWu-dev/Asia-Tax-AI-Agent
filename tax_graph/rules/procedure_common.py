"""Arithmetic several jurisdictions' rules share. It belongs to no jurisdiction: each jurisdiction's module registers it
for its own rules, with the clauses it implements there (REGISTRY; compile.check_registry checks every registration).

A fact an evaluator needs and does not find is reported through the chooser (eval.Chooser): it becomes a pending
item of the rule, and `ch.missing(keys)` says which end to take — the favourable one under FLOOR, the other under
CEILING, or whatever a forced run asks for. Rates and caps come from params; nothing is hard-coded."""
from datetime import date, timedelta


def add_months(d, k):
    y, m = divmod(d.year * 12 + d.month - 1 + k, 12)
    m += 1
    last = (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)).day
    return date(y, m, min(d.day, last))


def months_after(facts, P, fact, pid):
    """A deadline a number of months (a parameter) after a dated fact."""
    d = facts.get(("flow", fact))
    if d is None:
        return None
    due = add_months(d, int(P[pid]))
    return due, due


def gain_share(facts, P, ch):
    """Share of the consideration that is gain: (consideration - cost) / consideration (the profit, not the proceeds)."""
    c, k = facts.get(("flow", "consideration")), facts.get(("flow", "cost_basis"))
    if c is None or k is None:
        fav = ch.missing(*[k2 for k2, v in (("flow.consideration", c), ("flow.cost_basis", k)) if v is None])
        return 0.0 if fav else 1.0
    if c <= 0:
        return 0.0
    return max(0.0, min(1.0, (c - k) / c))


def ip_basis(facts, ch):
    """口径 D22. An IP sale: (proceeds, basis, allowances) — basis the seller's expenditure not yet allowed (the
    Mainland's net value, 实施条例 第七十四条), allowances the deductions already allowed on it (Hong Kong s16E/16EA,
    Singapore s19B). Unknown ones are decided together: the favourable end has the basis cover the proceeds, the other
    no basis and allowances as large as the proceeds. None when there are no proceeds."""
    c = facts.get(("flow", "consideration"))
    if not c or c <= 0:
        return None
    k, a = facts.get(("flow", "cost_basis")), facts.get(("flow", "ip_allowances_claimed"))
    if k is None or a is None:
        fav = ch.missing(*["flow." + n for n, v in (("cost_basis", k), ("ip_allowances_claimed", a)) if v is None])
        k = (c if fav else 0.0) if k is None else k
        a = (0.0 if fav else c) if a is None else a
    return float(c), float(k), float(a)


def ip_recapture_share(facts, P, ch):
    """Hong Kong s16E(3), s16EB(2); Singapore s19B(4), (5): the proceeds above the expenditure still unallowed, up to the
    deductions already allowed, are taxed (as a trading receipt / a balancing charge) — as a share of the proceeds."""
    parts = ip_basis(facts, ch)
    if parts is None:
        return 0.0
    c, k, a = parts
    return max(0.0, min(c - k, a)) / c


def ip_gain_share(facts, P, ch):
    """The whole gain over the seller's tax basis, as a share of the proceeds (a gain of revenue nature)."""
    parts = ip_basis(facts, ch)
    if parts is None:
        return 0.0
    c, k, _ = parts
    return max(0.0, c - k) / c


def profit_share(facts, P, ch):
    """The profit in a fee, a fact of the recipient's accounts; unknown: none or the whole fee."""
    m = facts.get(("flow", "profit_margin"))
    if m is None:
        return 0.0 if ch.missing("flow.profit_margin") else 1.0
    return max(0.0, min(1.0, float(m) / 100.0))


def arms_length_share(facts, P, ch):
    """A stated arm's-length ceiling (from the taxpayer's own study) caps the deductible amount; without one the
    deduction's own judgement condition carries the uncertainty, so nothing is registered here."""
    cap, amount = facts.get(("flow", "arms_length_max")), facts.get(("flow", "amount"))
    if cap is None or amount is None or amount <= 0:
        return 1.0
    return max(0.0, min(1.0, float(cap) / float(amount)))


def p2_shortfall_share(facts, P, ch, rate_pid="p2.minimum_rate"):
    """Top-up percentage = minimum rate - jurisdictional ETR; as a share of the minimum rate it scales a charge at the
    minimum rate on the entity's share of the excess profit. The ETR is the engine's fact from the labels and stated
    covered taxes. An additional current top-up's pseudo-flow already carries the amount: charged in full."""
    if facts.get(("flow", "p2_additional")):
        return 1.0
    etr = facts.get(("flow", "p2_etr"))
    if etr is None:
        keys = facts.get(("flow", "p2_etr_needs")) or ("flow.p2_etr",)
        return 1.0 if not ch.missing(*((keys,) if isinstance(keys, str) else keys)) else 0.0
    m = P[rate_pid]
    return max(0.0, min(1.0, (m - float(etr)) / m))
