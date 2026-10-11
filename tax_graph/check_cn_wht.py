"""Scenario check for the Mainland rules.

  python -m tax_graph.check_cn_wht          (conda env "pytorch")

oracle_kind = text_derived: there is no official Mainland calculator, so every expected value below is read by
hand from the cited text (the rate or base the clause states). This is a regression harness for the rule layer's
behaviour, not an independent oracle like official/labels/.
"""
import io
import sys
from datetime import date

from .cn_wht import CN, HK, SG, cn_wht

D, I, R = "DIVIDEND", "INTEREST", "ROYALTY"


def payee(cert=True, safe=False, via=False, onpay=0.0, fi=False, gov=False, gov_ok=None):
    """Ratios are in percent, the unit params.csv uses. A case states that the dividend is not reinvested unless it says so."""
    return {("payee", "residence_cert"): cert, ("payee", "bo_safe_harbour"): safe, ("payee", "bo_via_100pct_owner"): via,
            ("payee", "onpay_ratio_12m"): onpay, ("payee", "payee_is_financial_institution"): fi,
            ("payee", "payee_is_government"): gov, ("payee", "government_exempt_condition_met"): gov_ok,
            ("flow", "reinvested_in_cn"): False, ("payee", "payee_is_related"): False}


def hold(ratio, months):
    return {("flow", "direct_ratio"): ratio, ("flow", "holding_months"): months}


ON = date(2026, 3, 10)
# (name, payee_loc, income, facts, expected lo rate, expected hi rate, expected pending keys under lo, cite)
CASES = [
    ("HK dividend, 30% for 24 months, listed parent (safe harbour)", HK, D, {**payee(safe=True), **hold(30, 24)},
     5.0, 10.0, {"payee.ppt"}, "treaty.cn-hk.2006.zh#10.2; cn.sta.2018-09#i4"),
    ("HK dividend, 20% holding: the 10% cap equals the domestic rate, nothing pending", HK, D, {**payee(safe=True), **hold(20, 24)}, 10.0, 10.0, set(),
     "treaty.cn-hk.2006.zh#10.2 其它情况 10%"),
    ("HK dividend, 30% for 6 months only", HK, D, {**payee(safe=True), **hold(30, 6)}, 10.0, 10.0, set(),
     "cn.gsh.2009-81#i3 连续12个月"),
    ("HK dividend, no safe harbour, on-pays 30%: beneficial owner is a judgement", HK, D, {**payee(onpay=30), **hold(30, 24)},
     5.0, 10.0, {"payee.no_adverse_bo_factors", "payee.ppt"}, "cn.sta.2018-09#i2"),
    ("HK dividend, on-pays 60%: the 50% factor fails, no 5%", HK, D, {**payee(onpay=60), **hold(30, 24)},
     10.0, 10.0, set(), "cn.sta.2018-09#i2 50%以上"),
    ("HK dividend without a residence certificate", HK, D, {**payee(cert=False, safe=True), **hold(30, 24)},
     10.0, 10.0, set(), "cn.reg.eit#91 减按10%"),
    ("HK dividend reinvested in the Mainland (capital increase, paid directly)", HK, D,
     {**payee(safe=True), **hold(30, 24), ("flow", "reinvested_in_cn"): True, ("flow", "reinvestment_form"): "capital_increase",
      ("flow", "direct_payment"): True, ("flow", "reinvestment_from_distributed_profit"): True},
     5.0, 10.0, {"payee.ppt", "payee.reasonable_commercial_purpose_absent"}, "cn.cs.2018-102#i2; cn.law.eit#47"),
    ("SG interest to a bank", SG, I, payee(fi=True), 7.0, 10.0, {"payee.no_adverse_bo_factors", "payee.ppt", "flow.price_includes_vat", "flow.unified_borrowing_relending"},
     "treaty.cn-sg.2007.zh#11.2 百分之七; the interest VAT's questions (口径 D23, D25)"),
    ("SG interest to a company: the 10% cap equals the domestic rate; only the payer's benchmark test is pending", SG, I, payee(), 10.0, 10.0,
     {"flow.benchmark_rate", "flow.interest_rate", "flow.price_includes_vat", "flow.unified_borrowing_relending"}, "treaty.cn-sg.2007.zh#11.2 百分之十; 实施条例 第三十八条"),
    ("SG interest to the Monetary Authority (listed body, conditions met)", SG, I, payee(gov=True, gov_ok=True),
     0.0, 10.0, {"payee.ppt", "flow.benchmark_rate", "flow.interest_rate", "flow.price_includes_vat", "flow.unified_borrowing_relending"}, "treaty.cn-sg.2007.p2.zh#2.1"),
    # the floor takes a VAT-inclusive rent: the withholding is on the rent net of the 13% VAT (公告2013年第9号, 口径 D26)
    ("SG equipment rent", SG, R, {**payee(), ("flow", "is_equipment_lease"): True}, round(6.0 / 1.13, 6), 10.0,
     {"payee.no_adverse_bo_factors", "payee.ppt", "payer.reasonable_royalty", "payer.vat_general_taxpayer",
      "flow.input_vat_documents_kept", "flow.price_includes_vat"},
     "treaty.cn-sg.2007.zh#12.2 + 议定书第三条 60%; EIT art 8; 13% VAT on the rent withheld, credited to a general VAT "
     "taxpayer holding the documents (增值税法 第十条, 公告2026年第13号); base net of the VAT (公告2013年第9号)"),
    ("HK aircraft lease", HK, R, {**payee(), ("flow", "is_aircraft_or_ship_lease"): True}, round(5.0 / 1.13, 6), 10.0,
     {"payee.no_adverse_bo_factors", "payee.ppt", "payer.reasonable_royalty", "payer.vat_general_taxpayer",
      "flow.input_vat_documents_kept", "flow.price_includes_vat"},
     "treaty.cn-hk.2006.p4.zh#2 5%; EIT art 8; base net of the 13% VAT (公告2013年第9号)"),
]


def main():
    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    out.write("oracle_kind = text_derived\n")
    bad = 0
    for name, loc, income, facts, lo, hi, pending, cite in CASES:
        r = cn_wht(loc, income, facts, on=ON)
        wrong = []
        if r.lo.rate != lo:
            wrong.append(("lo", lo, r.lo.rate))
        if r.hi.rate != hi:
            wrong.append(("hi", hi, r.hi.rate))
        if set(r.conditions) != pending:
            wrong.append(("pending", sorted(pending), r.conditions))
        bad += bool(wrong)
        out.write("%-4s %s  [%s]\n" % ("ok" if not wrong else "DIFF", name, cite))
        for k, a, b in wrong:
            out.write("        %s: expected %s, got %s\n" % (k, a, b))

    # deferral and procedure
    f = {**payee(safe=True), **hold(30, 24), ("flow", "reinvested_in_cn"): True, ("flow", "reinvestment_form"): "capital_increase",
         ("flow", "direct_payment"): True, ("flow", "reinvestment_from_distributed_profit"): True,
         ("flow", "date_of_payment"): ON}
    r = cn_wht(HK, D, f, on=ON, amount=1000.0)
    checks = [("deferred under lo", True, r.lo.deferred), ("not deferred under hi (GAAR)", False, r.hi.deferred),
              ("remit by payment + 7 days", date(2026, 3, 17), r.lo.deadlines.get("remit"))]
    f = {**payee(), ("flow", "date_of_payment"): ON, ("flow", "payable_on"): date(2026, 2, 1),
         ("flow", "remitted_on"): date(2026, 2, 18), ("flow", "tax_paid_on"): date(2024, 5, 1),
         ("flow", "first_notification_on"): date(2025, 1, 15), ("flow", "authority_action"): "assessment"}
    r = cn_wht(SG, I, f, on=ON, amount=10000.0)
    checks += [("interest: obligation on the earlier payable date + 7", date(2026, 2, 8), r.lo.deadlines.get("remit")),
               ("surcharge 0.05%/day x 10 days on 1000", 5.0, r.lo.penalty),
               ("refund clock 3 years from payment", date(2027, 5, 1), r.lo.deadlines.get("refund")),
               ("MAP clock 3 years from first notification", date(2028, 1, 15), r.lo.deadlines.get("map"))]
    # remedy clocks: review 60 days from the assessment notice once the tax is paid or secured (征管法第88条, 行政复议法第20条)
    f = {**payee(), ("flow", "date_of_payment"): ON, ("flow", "assessment_notice_on"): date(2026, 5, 4), ("flow", "tax_paid_or_secured"): True}
    r = cn_wht(SG, I, f, on=ON, amount=10000.0)
    checks.append(("administrative review: 60 days from the assessment notice", date(2026, 7, 3), r.lo.deadlines.get("review")))
    f[("flow", "tax_paid_or_secured")] = False
    r = cn_wht(SG, I, f, on=ON, amount=10000.0)
    checks.append(("administrative review: no clock before the tax is paid or secured", None, r.lo.deadlines.get("review")))
    # the 10% "other" cap equals the domestic rate, so only the rules relied upon can show it was not claimed
    r = cn_wht(HK, D, {**payee(cert=False, safe=True), **hold(30, 24)}, on=ON)
    checks.append(("no treaty rule relied upon without a residence certificate", [],
                   [x for x in r.lo.rules + r.hi.rules if x.endswith("@cn")]))
    for name, want, got in checks:
        ok = want == got
        bad += not ok
        out.write("%-4s %s%s\n" % ("ok" if ok else "DIFF", name, "" if ok else "  expected %s, got %s" % (want, got)))
    out.write("%d checks, %d with differences\n" % (len(CASES) + len(checks), bad))
    out.flush()
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
