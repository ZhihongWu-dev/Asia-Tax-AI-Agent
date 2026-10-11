"""Mainland evaluators: deadlines, penalties, computed BASE fractions and deduction caps of Mainland rules.

REGISTRY: rule id, or the rule's value text for a deadline named by text -> (effect, evaluator, clauses the evaluator
implements). compile.check_registry checks that every registered rule exists and is a Mainland rule (or a treaty rule
with the Mainland), that every clause is in the library, and that every rule needing an evaluator has one.

Deadlines roll over public holidays per 税收征管法实施细则 第109条, with the State Council calendar in
official/calendars/cn_public_holidays.csv (holidays and adjusted working days)."""
import csv
from datetime import date, timedelta

from ..params import OFFICIAL
from .procedure_common import arms_length_share, gain_share


def cn_gain_share(facts, P, ch):
    """The gain share with the Mainland's own tax basis when it differs (口径 D18: after a special reorganisation the
    acquirer keeps the transferor's basis, 59号 §6(2)); otherwise as for every jurisdiction."""
    basis = facts.get(("flow", "cn_cost_basis"))
    if basis is None:
        return gain_share(facts, P, ch)
    f2 = dict(facts)
    f2[("flow", "cost_basis")] = basis
    return gain_share(f2, P, ch)


def reorg_spread_share(facts, P, ch):
    """59号 §8: the resident's gain spread evenly over ten tax years — the gain share times the share of the ten years
    the horizon holds (the rest falls after it)."""
    years = facts.get(("flow", "reorg_horizon_years")) or 1
    return cn_gain_share(facts, P, ch) * min(1.0, float(years) / P["cn.reorg.resident_spread_years"])

JUR = "CN"


def tech_transfer_share(facts, P, ch, items=()):
    """实施条例 第九十条 (财税〔2010〕111号): a year's technology-transfer income up to 5 million yuan is exempt, the excess
    halved — the taxed share of the gain the charge is on. The case's amounts are turned into yuan by cny_rate (yuan per
    unit; a flow stated in yuan needs none). Unknown: all exempt at the favourable end; at the other the gain is the
    whole proceeds, and with no rate only the halving is certain. 口径 D29: the proceeds are net of the VAT the seller
    takes out of a VAT-inclusive price."""
    c, k = facts.get(("flow", "consideration")), facts.get(("flow", "cost_basis"))
    x = sum(v.rate for v in items if v.levy == "vat" and v.jur == "CN" and not v.deduction and v.borne_by == "payee"
            and v.vat_inclusive) / 100.0
    if not c or c <= 0:
        return 1.0
    rate = 1.0 if facts.get(("flow", "currency")) == "CNY" else facts.get(("flow", "cny_rate"))
    half = P["cn.tech.excess_rate"] / 100.0
    if k is None or rate is None:
        if ch.missing(*["flow." + n for n, v in (("cost_basis", k), ("cny_rate", rate)) if v is None]):
            return 0.0
        if rate is None:
            return half
        k = 0.0
    gain = (float(c) * (1.0 - x) - float(k)) * float(rate)
    if gain <= 0:
        return 1.0
    return max(0.0, gain - P["cn.tech.exempt_max"]) * half / gain


tech_transfer_share.takes_items = True


def transfer_basis_share(facts, P, ch, items):
    """口径 D28. 公告2015年第40号 第三条: under the special treatment the buyer amortises the seller's tax basis, not the
    market value — the share basis / value of its deduction, when the seller's gain was exempted by it on this flow."""
    if not any("cn.reorg.asset_transfer" in it.cites for it in items if it.levy == "income" and not it.deduction):
        return 1.0
    c, k = facts.get(("flow", "consideration")), facts.get(("flow", "cost_basis"))
    if not c or c <= 0:
        return 1.0
    if k is None:
        return 1.0 if ch.missing("flow.cost_basis") else 0.0
    return max(0.0, min(1.0, float(k) / float(c)))


transfer_basis_share.takes_items = True


def amortization_share(facts, P, ch):
    """实施条例 第六十七条: an acquired intangible is amortised straight-line over at least 10 years, or over a shorter life a
    law or the contract sets — the share of the price deducted within the modelled years. An unknown life: the whole
    price within them at the favourable end, ten years at the other."""
    years = float(facts.get(("flow", "ip_horizon_years")) or 1)
    least = P["cn.ip.amortization_years_min"]
    life = facts.get(("flow", "ip_useful_life_years"))
    if life is None:
        return 1.0 if ch.missing("flow.ip_useful_life_years") else min(1.0, years / least)
    return min(1.0, years / max(1e-9, min(float(life), least)))


def load_cn_holidays():
    with open(str(OFFICIAL / "calendars" / "cn_public_holidays.csv"), encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    from datetime import date
    holidays = {date.fromisoformat(r["date"]) for r in rows if r["kind"] == "holiday"}
    years = {int(r["date"][:4]) for r in rows}
    return holidays, years


def roll_cn(start, due, P):
    """第109条: a last day on a statutory holiday moves to the day after the holiday ends; a run of 3 or more
    statutory holidays inside the period extends it by their number of days."""
    if not P["cn.time.holiday_roll"]:
        return due
    holidays, years = load_cn_holidays()
    if due.year not in years:                         # the State Council publishes each year's calendar in November
        from .procedure_sg import gap_date            # of the year before: reported as a gap, not assumed
        return gap_date(due, "CN")
    run, d, extra = 0, start + timedelta(days=1), 0
    while d <= due:                                   # consecutive statutory holidays inside the period
        run = run + 1 if d in holidays else 0
        if run == int(P["cn.time.long_holiday_days"]):
            extra += run
        elif run > int(P["cn.time.long_holiday_days"]):
            extra += 1
        d += timedelta(days=1)
    due = due + timedelta(days=extra)
    while due in holidays:
        due += timedelta(days=1)
    return due


def obligation_date(facts):
    """cn.sta.2017-37 #i4 / #i7: the earlier of actual payment and the date the amount fell due; dividends on payment only."""
    paid, payable = facts.get(("flow", "date_of_payment")), facts.get(("flow", "payable_on"))
    if facts.get(("flow", "income")) == "DIVIDEND":
        return paid
    return min(d for d in (paid, payable) if d) if (paid or payable) else None


def _remit(facts, P, deadlines):
    on = obligation_date(facts)
    if on is None:
        return None
    nominal = on + timedelta(days=int(P["cn.wht.remit_days"]))
    return nominal, roll_cn(on, nominal, P)


def _refund(facts, P, deadlines):
    paid = facts.get(("flow", "tax_paid_on"))
    if paid is None:
        return None
    due = paid.replace(year=paid.year + int(P["cn.refund.limit_years"]))
    return due, due


def _map(facts, P, deadlines, pid):
    first = facts.get(("flow", "first_notification_on"))
    if first is None:
        return None
    due = first.replace(year=first.year + int(P[pid]))
    return due, due


# keyed by the rule's value text where the value is a text, by rule id where the value is a number of years
def _review(facts, P, deadlines):
    """行政复议法第20条: 60 days from knowing of the act; 征管法第88条: the tax (or security) must be in first."""
    d = facts.get(("flow", "assessment_notice_on"))
    if d is None:
        return None
    due = d + timedelta(days=int(P["cn.review.days"]))
    return due, due


def late_surcharge(tax, due, paid_on, P):
    """税收征管法 s32: 0.05% of the tax per day of delay."""
    days = (paid_on - due).days
    if days <= 0:
        return 0.0
    return round(tax * P["cn.tca.late_surcharge_daily"] / 100.0 * days, 2)


def surcharge(rule, facts, P, deadlines, tax):
    due, paid_on = deadlines.get("remit"), facts.get(("flow", "remitted_on"))
    if due is None or paid_on is None or tax is None:
        return None
    return late_surcharge(tax, due[1], paid_on, P)


def deemed_profit_share(facts, P, ch):
    """国税发〔2010〕19号 第五条: the authority fixes a profit rate inside the range for the kind of service. "Other"
    services have a floor only, so their upper end is the whole fee; an unknown kind spans the lowest floor to that."""
    ranges = {"MANAGEMENT": ("cn.service.deemed_profit_min", "cn.service.deemed_profit_max"),
              "ENGINEERING_DESIGN_CONSULTING": ("cn.service.deemed_profit_design_min", "cn.service.deemed_profit_design_max"),
              "OTHER": ("cn.service.deemed_profit_other_min", None)}
    kind = facts.get(("flow", "service_kind"))
    lo, hi = ranges.get(kind, ("cn.service.deemed_profit_other_min", None))
    fav = ch.missing("flow.service_kind") if kind not in ranges else ch.fav
    onshore = facts.get(("flow", "service_onshore_share"))     # 实施条例 第七条: only the work done in the Mainland is sourced there
    if onshore is None:
        onshore = 0.0 if ch.missing("flow.service_onshore_share") else 100.0
    base = (P[lo] / 100.0) if fav else (P[hi] / 100.0 if hi else 1.0)
    return base * float(onshore) / 100.0


def benchmark_share(facts, P, ch):
    """实施条例 第三十八条(二): interest between non-financial enterprises is deductible up to the rate a financial
    enterprise would charge for the same kind of loan over the same period; the share is benchmark / actual."""
    rate, bench = facts.get(("flow", "interest_rate")), facts.get(("flow", "benchmark_rate"))
    if facts.get(("payee", "payee_is_financial_institution")):
        return 1.0                                        # 第三十八条(一): borrowing from a financial enterprise, in full
    if rate is None or bench is None:
        fav = ch.missing(*[k for k, v in (("flow.interest_rate", rate), ("flow.benchmark_rate", bench)) if v is None])
        return 1.0 if fav else 0.0
    return 1.0 if rate <= 0 else max(0.0, min(1.0, float(bench) / float(rate)))


def _june_30_next_year(facts, P, deadlines):
    """公告2016年第42号 第十九条: the local file is ready by 30 June of the year after the related-party dealings."""
    d = facts.get(("flow", "date_of_payment"))
    if d is None:
        return None
    due = date(d.year + 1, 6, 30)
    return due, due


def tp_interest(rule, facts, P, deadlines, tax):
    """公告2017年第6号 第四十四条: interest on a special tax adjustment from 1 June of the year after the tax year to the
    day the tax is paid, at the PBOC benchmark plus five points (benchmark only when documentation was provided)."""
    adj, paid_on, base = facts.get(("flow", "tp_adjustment_tax")), facts.get(("flow", "tp_adjustment_paid_on")), facts.get(("flow", "pboc_benchmark_rate"))
    if adj is None or paid_on is None or base is None:
        return None
    year = facts[("flow", "date_of_payment")].year
    start = date(year + 1, 6, 1)
    days = max(0, (paid_on - start).days)
    spread = 0.0 if facts.get(("payer", "tp_documentation_provided")) else P["cn.tp.interest_spread"]
    return round(float(adj) * (float(base) + spread) / 100.0 * days / 365.0, 2)


GAIN = ("cn.law.eit#16",)
REGISTRY = {
    "cn.gain.base": ("BASE", cn_gain_share, GAIN),
    "cn.resident.ip.charge": ("CHARGE", cn_gain_share, ("cn.law.eit#16", "cn.reg.eit#74")),             # 口径 D22
    "cn.ip.wht": ("CHARGE", cn_gain_share, ("cn.law.eit#19",)),
    "cn.resident.ip.tech": ("BASE", tech_transfer_share, ("cn.reg.eit#90",)),
    "cn.ip.amortization.horizon": ("DEDUCT_BASE", amortization_share, ("cn.reg.eit#67",)),
    "cn.reorg.asset_transfer.basis": ("DEDUCT_BASE", transfer_basis_share, ("cn.sta.2015-40#i3",)),     # 口径 D28
    "cn.indirect.gain.base": ("BASE", cn_gain_share, GAIN),
    "cn.resident.gain.base": ("BASE", cn_gain_share, GAIN),
    "cn.reorg.special_resident": ("BASE", reorg_spread_share, ("cn.cs.2009-59#i8",)),             # 口径 D18
    "cn.service.deemed_profit": ("BASE", deemed_profit_share, ("cn.gsf.2010-19#5", "cn.reg.eit#7")),
    "cn.deduct.interest.benchmark": ("DEDUCT_BASE", benchmark_share, ("cn.reg.eit#38",)),
    "cn.tp.deduction_cap": ("DEDUCT_BASE", arms_length_share, ("cn.law.eit#41",)),
    "cn.review": ("DEADLINE", ("review", _review), ("cn.law.ar#20",)),
    "actual payment or date payable": ("DEADLINE", ("remit", _remit), ("cn.sta.2017-37#i4", "cn.sta.2017-37#i7")),
    "cn.refund": ("DEADLINE", ("refund", _refund), ("cn.law.tca#51",)),
    "cn-hk.map": ("DEADLINE", ("map", lambda f, P, d: _map(f, P, d, "cn-hk.map.limit")), ("treaty.cn-hk.2006.zh#23.1",)),
    "cn-sg.map": ("DEADLINE", ("map", lambda f, P, d: _map(f, P, d, "cn-sg.map.limit")), ("treaty.cn-sg.2007.zh#24.1",)),
    "cn.tp.local_file": ("DEADLINE", ("tp_local_file", _june_30_next_year), ("cn.sta.2016-42#i19",)),
    "cn.wht.late_surcharge": ("PENALTY", surcharge, ("cn.law.tca#32",)),
    "cn.tp.adjustment_interest": ("PENALTY", tp_interest, ("cn.sta.2017-06#44", "cn.reg.eit#122")),
}

# facts each rule reads besides its parameters and condition; compile.py adds them to RuleObj.reads
READS = {
    "cn.review": ("flow.assessment_notice_on",),
    "cn.wht.remit": ("flow.date_of_payment", "flow.payable_on"),
    "cn-hk.map": ("flow.first_notification_on",),
    "cn-sg.map": ("flow.first_notification_on",),
    "cn.wht.late_surcharge": ("flow.remitted_on",),
    "cn.refund": ("flow.tax_paid_on",),
    "cn.gain.base": ("flow.consideration", "flow.cost_basis", "flow.cn_cost_basis"),
    "cn.resident.ip.charge": ("flow.consideration", "flow.cost_basis"), "cn.ip.wht": ("flow.consideration", "flow.cost_basis"),
    "cn.resident.ip.tech": ("flow.consideration", "flow.cost_basis", "flow.cny_rate", "flow.currency"),
    "cn.ip.amortization.horizon": ("flow.ip_horizon_years", "flow.ip_useful_life_years"),
    "cn.reorg.asset_transfer.basis": ("flow.consideration", "flow.cost_basis"),
    "cn.vat.law.service": ("flow.price_includes_vat",), "cn.vat.law.royalty": ("flow.price_includes_vat",),
    "cn.vat.law.lease": ("flow.price_includes_vat",), "cn.vat.law.ip": ("flow.price_includes_vat",),
    "cn.vat.law.ip_sale": ("flow.price_includes_vat",),
    "cn.vat.law.interest": ("flow.price_includes_vat",), "cn.vat.law.interest_received": ("flow.price_includes_vat",),
    "cn.indirect.gain.base": ("flow.consideration", "flow.cost_basis", "flow.cn_cost_basis"),
    "cn.resident.gain.base": ("flow.consideration", "flow.cost_basis", "flow.cn_cost_basis"),
    "cn.reorg.special_resident": ("flow.consideration", "flow.cost_basis", "flow.cn_cost_basis", "flow.reorg_horizon_years"),
    "cn.service.deemed_profit": ("flow.service_kind", "flow.service_onshore_share"),
    "cn.ftc.dividend_indirect": ("flow.underlying_tax_share",),
    "cn.deduct.interest.benchmark": ("flow.interest_rate", "flow.benchmark_rate"),
    "cn.tp.adjustment_interest": ("flow.tp_adjustment_tax", "flow.tp_adjustment_paid_on", "flow.pboc_benchmark_rate", "payer.tp_documentation_provided"),
    "cn.tp.local_file": ("payer.related_party_volume",),
    "cn.tp.deduction_cap": ("flow.arms_length_max",),
}
