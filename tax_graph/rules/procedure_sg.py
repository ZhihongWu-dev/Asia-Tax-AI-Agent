"""Singapore evaluators: deadlines, penalties, computed BASE fractions and deduction caps of Singapore rules.

REGISTRY: the rule's value text for a deadline named by text, else the rule id -> (effect, evaluator, clauses the
evaluator implements); an unknown rule text raises instead of guessing. compile.check_registry checks that every
registered rule exists and is a Singapore rule (or a treaty rule with Singapore), that every clause is in the library,
and that every rule needing an evaluator has one. Numbers come from params; dates from official/calendars."""
import csv
from datetime import date, timedelta

from ..params import OFFICIAL
from .procedure_common import (add_months, arms_length_share, gain_share, ip_gain_share, ip_recapture_share,  # noqa: F401
                               months_after, p2_shortfall_share, profit_share)

JUR = "SG"


def load_holidays(P):
    """Public holidays from the official calendar, plus the day after a holiday that falls on a Sunday."""
    with open(str(OFFICIAL / "calendars" / "sg_public_holidays.csv"), encoding="utf-8-sig", newline="") as f:
        days = {date.fromisoformat(r["date"]) for r in csv.DictReader(f)}
    years = {d.year for d in days}
    if P["sg.holiday.sunday_substitute"]:
        for h in sorted(days):
            if h.weekday() == 6:
                nxt = h + timedelta(days=1)
                while nxt in days:
                    nxt += timedelta(days=1)
                days.add(nxt)
    return days, years


class GapDate(date):
    """A nominal date that could not be rolled because that year's holiday calendar is missing; .gap names it."""
    gap = None


def gap_date(d, jur):
    g = GapDate(d.year, d.month, d.day)
    g.gap = (jur, d.year)
    return g


def roll_forward(d, P):
    """Interpretation Act s50: a last day that is an excluded day moves to the next day that is not."""
    kinds = P["sg.time.excluded_days"].split(";")
    if not P["sg.time.act_on_excluded_day"]:
        return d
    holidays, years = load_holidays(P)
    while True:
        if d.year not in years:
            return gap_date(d, "SG")                          # calendar for that year not in the library: reported, not assumed
        if ("sunday" in kinds and d.weekday() == 6) or ("public_holiday" in kinds and d in holidays):
            d += timedelta(days=1)
        else:
            return d


def saturday_roll(d, P):
    """IRAS practice under s45(2)(a): a Saturday also moves to the next working day (observed_rules.csv)."""
    while True:
        if d.weekday() == 5:
            d += timedelta(days=1)
        rolled = roll_forward(d, P)
        if rolled == d and d.weekday() != 5:
            return d
        d = rolled


# DEADLINE evaluators: value text -> (deadline name, fn(facts, P, deadlines) -> (nominal, date) or None)
def _filing(facts, P, deadlines):
    paid = facts.get(("flow", "date_of_payment"))
    if paid is None:
        return None
    nominal = add_months(paid, 2).replace(day=15)
    return nominal, roll_forward(nominal, P)


def _filing_practice(facts, P, deadlines):
    cur = deadlines.get("filing")
    return (cur[0], saturday_roll(cur[1], P)) if cur else None


def _cor_current(facts, P, deadlines):
    end = facts.get(("flow", "period_to"))
    return (date(end.year + 1, 3, 31),) * 2 if end else None


def _cor_prior(facts, P, deadlines):
    sub = facts.get(("flow", "as_at"))
    return (add_months(sub, 3),) * 2 if sub else None


def late_penalty(tax, due, as_at, P):
    """s45(4): 5% once the due date is missed; from 30 days after it, 1% per completed month, capped."""
    if as_at <= due:
        return 0.0
    start = due + timedelta(days=int(P["sg.wht.late_penalty_monthly_starts_after_days"]))
    months = 0
    while add_months(start, months + 1) <= as_at:
        months += 1
    extra = min(months * P["sg.wht.late_penalty_monthly"], P["sg.wht.late_penalty_monthly_cap"])
    return round(tax * (P["sg.wht.late_penalty"] + extra) / 100.0, 2)


def penalty(rule, facts, P, deadlines, tax):
    due, as_at = deadlines.get("filing"), facts.get(("flow", "as_at"))
    if due is None or as_at is None or tax is None:
        return None
    return late_penalty(tax, due[1], as_at, P)


def _sg_return_due(facts, P, deadlines):
    """ITA s34F(5)(a): documentation by the time for making the return. The Act sets no date (s62: by notice); the case's
    stated return date wins, else IRAS practice (sg.corp.return_due: 30 Nov of the year of assessment)."""
    due = facts.get(("payer", "return_due_on"))
    if due is not None:
        return due, due
    d = facts.get(("flow", "date_of_payment"))
    if d is None:
        return None
    due = date(d.year + 1, 11, 30)
    return due, due


def sg_tp_surcharge(rule, facts, P, deadlines, tax):
    """ITA s34E(1): 5% of the increase in income or the reduction of a deduction the Comptroller makes."""
    adj = facts.get(("flow", "tp_adjustment_amount"))
    if adj is None:
        return None
    return round(float(adj) * P["sg.tp.surcharge_rate"] / 100.0, 2)


def _objection(f, P, d):
    return months_after(f, P, "assessment_notice_on", "sg.objection.months_company")


def _p2(f, P, ch):
    return p2_shortfall_share(f, P, ch, "sg.p2.minimum_rate")


S10, S45 = ("sg.ita1947.full#s10",), ("sg.ita1947.full#s45",)
def wda_share(facts, P, ch):
    """s19B(1AA), (2): the price is written down in equal parts over the period the company elects — the shortest, 5
    years — the share falling within the modelled years."""
    years = float(facts.get(("flow", "ip_horizon_years")) or 1)
    return min(1.0, years / P["sg.ip.wda_years"])


REGISTRY = {
    "sg.gain.base": ("BASE", gain_share, S10),
    "sg.ip.recapture": ("CHARGE", ip_recapture_share, ("sg.ita1947.full#s19B",)),                     # 口径 D22
    "sg.ip.revenue": ("CHARGE", ip_gain_share, S10),
    "sg.ip.wda.horizon": ("DEDUCT_BASE", wda_share, ("sg.ita1947.full#s19B",)),
    "sg.fsie.gain.base": ("BASE", gain_share, S10),
    "sg.service.base": ("BASE", profit_share, S10),
    "sg.p2.base": ("BASE", _p2, ("sg.memta2024.s16#s16", "sg.memta2024.s17#s17", "sg.memta2024.s21#s21",
                                 "sg.memta2024.s30#s30")),                           # 口径 D13, D14, D15
    "sg.tp.deduction_cap": ("DEDUCT_BASE", arms_length_share, ("sg.ita1947.full#s34D",)),
    "15th day of the second month following payment": ("DEADLINE", ("filing", _filing), S45),
    "observed:sg.wht.due_date_saturday_rolls": ("DEADLINE", ("filing", _filing_practice), S45),
    "31 Mar of the following year": ("DEADLINE", ("cor", _cor_current), ("sg.iras.wht.dta-relief#h3",)),
    "3 months from WHT submission": ("DEADLINE", ("cor", _cor_prior), ("sg.iras.wht.dta-relief#h3",)),
    "sg.tp.documentation": ("DEADLINE", ("tp_local_file", _sg_return_due), ("sg.ita1947.full#s34F", "sg.iras.formc#h2")),
    "sg.objection": ("DEADLINE", ("objection", _objection), ("sg.ita1947.full#s76",)),
    "sg.objection.source": ("DEADLINE", ("objection", _objection), ("sg.ita1947.full#s76",)),
    "sg.wht.penalty": ("PENALTY", penalty, S45),
    "sg.tp.surcharge": ("PENALTY", sg_tp_surcharge, ("sg.ita1947.full#s34E",)),
}

# facts each rule reads besides its parameters and condition; compile.py adds them to RuleObj.reads
READS = {
    "sg.ftc.dta": ("flow.foreign_tax_rate",),
    "sg.ip.recapture": ("flow.consideration", "flow.cost_basis", "flow.ip_allowances_claimed"),
    "sg.ip.revenue": ("flow.consideration", "flow.cost_basis"),
    "sg.ip.wda.horizon": ("flow.ip_horizon_years",),
    "sg.ftc.unilateral": ("flow.foreign_tax_rate",),
    "sg.wht.due": ("flow.date_of_payment",),
    "sg.wht.due_practice": ("flow.date_of_payment",),
    "sg.wht.penalty": ("flow.as_at",),
    "sg.dtr.cor": ("flow.period_to",),
    "sg.dtr.cor_prior_years": ("flow.as_at",),
    "sg.objection": ("flow.assessment_notice_on",), "sg.objection.source": ("flow.assessment_notice_on",),
    "sg.fsie.gain.base": ("flow.consideration", "flow.cost_basis"),
    "sg.gain.base": ("flow.consideration", "flow.cost_basis"),
    "sg.service.base": ("flow.profit_margin",),
    "sg.p2.base": ("flow.p2_etr", "flow.p2_additional"),
    "sg.tp.surcharge": ("flow.tp_adjustment_amount",),
    "sg.tp.documentation": ("payer.gross_revenue", "payer.return_due_on"),
    "sg.tp.deduction_cap": ("flow.arms_length_max",),
}
