"""Hong Kong evaluators: computed BASE fractions, deadlines and deduction caps of Hong Kong rules.

REGISTRY: rule id -> (effect, evaluator, clauses the evaluator implements). compile.check_registry checks that every
registered rule exists and is a Hong Kong rule (or a treaty rule with Hong Kong), that every clause is in the library,
and that every rule needing an evaluator has one. Arithmetic shared with other jurisdictions is in procedure_common."""
from datetime import date

from .procedure_common import (add_months, arms_length_share, gain_share, ip_basis, ip_gain_share, ip_recapture_share,
                               months_after, p2_shortfall_share, profit_share)

JUR = "HK"


def nexus_taxable_share(facts, P, ch):
    """IP income: the excepted portion is F = min(100%, QE x uplift / (QE + NE)); the taxable share is 1 - F."""
    qe, ne = facts.get(("flow", "qualifying_rd_expenditure")), facts.get(("flow", "non_qualifying_expenditure"))
    if qe is None or ne is None:
        fav = ch.missing(*[k for k, v in (("flow.qualifying_rd_expenditure", qe), ("flow.non_qualifying_expenditure", ne)) if v is None])
        return 0.0 if fav else 1.0
    if qe + ne <= 0:
        return 1.0
    f = min(P["hk.fsie.nexus_cap"] / 100.0, qe * P["hk.fsie.nexus_uplift"] / 100.0 / (qe + ne))
    return 1.0 - f


def ip_nexus_fraction(facts, P, ch):
    """Sch 17FC: the excepted portion of a qualifying IP disposal gain (a patent or a software copyright) is its R&D
    fraction; any other IP's gain has none."""
    kind = facts.get(("flow", "ip_kind"))
    if kind is None:
        if not ch.missing("flow.ip_kind"):
            return 0.0
    elif kind not in str(P["hk.fsie.qualifying_ip_kinds"]).split(";"):
        return 0.0
    return 1.0 - nexus_taxable_share(facts, P, ch)


def ip_fsie_share(facts, P, ch):
    """s15I with s16E(3) / s16EB(2): the recaptured part is a trading receipt sourced here; the gain above the original
    cost (still unallowed plus allowed) is an IP disposal gain charged when received here, less the excepted portion."""
    parts = ip_basis(facts, ch)
    if parts is None:
        return 0.0
    c, k, a = parts
    rest = max(0.0, c - k - a) / c
    return ip_recapture_share(facts, P, ch) + rest * (1.0 - ip_nexus_fraction(facts, P, ch))


def _nine_months_after_period(facts, P, deadlines):
    """Cap 112 s58C(2)(a): master and local file within 9 months after the end of the entity's accounting period."""
    end = facts.get(("payer", "accounting_period_end"))
    if end is None:
        d = facts.get(("flow", "date_of_payment"))
        if d is None:
            return None
        end = date(d.year, 12, 31)                      # calendar-year period unless the entity states its own
    due = add_months(end, int(P["hk.tp.local_file_months"]))
    return due, due


def _objection(f, P, d):
    return months_after(f, P, "assessment_notice_on", "hk.objection.months")


def _appeal(f, P, d):
    return months_after(f, P, "determination_on", "hk.appeal.months")


def _p2(f, P, ch):
    return p2_shortfall_share(f, P, ch, "p2.minimum_rate")


S14 = ("hk.cap112.en#s14",)
REGISTRY = {
    "hk.gain.base": ("BASE", gain_share, S14),
    "hk.fsie.gain.base": ("BASE", gain_share, S14),
    "hk.service.base": ("BASE", profit_share, S14),
    "hk.service.base_resident": ("BASE", profit_share, S14),
    "hk.fsie.ip_nexus": ("BASE", nexus_taxable_share, ("hk.cap112.en#sch17FC",)),
    "hk.ip.recapture": ("CHARGE", ip_recapture_share, ("hk.cap112.en#s16E", "hk.cap112.en#s16EB")),      # 口径 D22
    "hk.ip.fsie": ("CHARGE", ip_fsie_share, ("hk.cap112.en#s15I", "hk.cap112.en#s16E", "hk.cap112.en#sch17FC")),
    "hk.ip.onshore": ("CHARGE", ip_gain_share, S14),
    "hk.p2.base": ("BASE", _p2, ("hk.ord.2025-21#p82", "hk.ord.2025-21#p83", "hk.ord.2025-21#p84", "hk.ord.2025-21#p85",
                                 "hk.ord.2025-21#p71", "hk.ord.2025-21#p91")),        # 口径 D14, D15
    "hk.tp.deduction_cap": ("DEDUCT_BASE", arms_length_share, ("hk.cap112.en#s50AAF",)),
    "hk.tp.local_file": ("DEADLINE", ("tp_local_file", _nine_months_after_period), ("hk.cap112.en#s58C",)),
    "hk.objection": ("DEADLINE", ("objection", _objection), ("hk.cap112.en#s64",)),
    "hk.objection.source": ("DEADLINE", ("objection", _objection), ("hk.cap112.en#s64",)),
    "hk.appeal": ("DEADLINE", ("appeal", _appeal), ("hk.cap112.en#s66",)),
}

# facts each rule reads besides its parameters and condition; compile.py adds them to RuleObj.reads
READS = {
    "hk.objection": ("flow.assessment_notice_on",), "hk.objection.source": ("flow.assessment_notice_on",),
    "hk.appeal": ("flow.determination_on",),
    "hk.ftc.dta": ("flow.foreign_tax_rate",),
    "hk.ftc.unilateral": ("flow.foreign_tax_rate",),
    "hk.gain.base": ("flow.consideration", "flow.cost_basis"),
    "hk.fsie.gain.base": ("flow.consideration", "flow.cost_basis"),
    "hk.p2.base": ("flow.p2_etr", "flow.p2_additional"),
    "hk.service.base": ("flow.profit_margin",), "hk.service.base_resident": ("flow.profit_margin",),
    "hk.tp.local_file": ("payer.accounting_period_end",),
    "hk.tp.deduction_cap": ("flow.arms_length_max",),
    "hk.fsie.ip_nexus": ("flow.qualifying_rd_expenditure", "flow.non_qualifying_expenditure"),
    "hk.ip.recapture": ("flow.consideration", "flow.cost_basis", "flow.ip_allowances_claimed"),
    "hk.ip.fsie": ("flow.consideration", "flow.cost_basis", "flow.ip_allowances_claimed", "flow.ip_kind",
                   "flow.qualifying_rd_expenditure", "flow.non_qualifying_expenditure"),
    "hk.ip.onshore": ("flow.consideration", "flow.cost_basis"),
}
