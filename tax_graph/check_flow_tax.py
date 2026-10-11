"""Scenario check for the cross-side behaviour: share transfers at the Mainland, Singapore's receiving side, and
the foreign tax credits of both hubs.

  python -m tax_graph.check_flow_tax          (conda env "pytorch")

oracle_kind = text_derived (hand-read from the cited provisions; no official calculator covers these).
"""
import io
import sys
from datetime import date

from .flow_tax import flow_tax

CN, HK, SG = "CN", "HK", "SG"
D, I, R, G = "DIVIDEND", "INTEREST", "ROYALTY", "SHARE_TRANSFER"
ON = date(2026, 3, 10)


def seller(cert=True, consideration=1000.0, cost=600.0, immovable=20, max_ratio=30, listed=False):
    return {("payee", "residence_cert"): cert, ("flow", "consideration"): consideration, ("flow", "cost_basis"): cost,
            ("flow", "immovable_ratio"): immovable, ("flow", "max_ratio_12m"): max_ratio, ("flow", "listed_market_trade"): listed,
            ("flow", "indirect_cn_target"): False}


def indirect(value=80, asset=95, income_ratio=50, limited=True, lower=True, listed=False, reorg=0, equity=False, not_reduced=False):
    return {("flow", "indirect_cn_target"): True, ("payee", "payee_resident_in_cn"): False, ("flow", "consideration"): 1000.0, ("flow", "cost_basis"): 600.0,
            ("flow", "cn_value_ratio"): value, ("flow", "cn_asset_ratio"): asset, ("flow", "cn_income_ratio"): income_ratio,
            ("flow", "limited_functions_and_risks"): limited, ("flow", "foreign_tax_lower_than_cn"): lower,
            ("flow", "listed_market_trade"): listed, ("flow", "intragroup_reorg_ratio"): reorg,
            ("flow", "reorg_consideration_in_equity"): equity, ("flow", "later_cn_tax_not_reduced"): not_reduced}


def recipient_sg(kind="REMITTED", taxed=True, headline=25, group=True, excluded=False):
    return {("flow", "receipt_kind"): kind, ("flow", "foreign_taxed"): taxed, ("flow", "foreign_headline_rate"): headline,
            ("payee", "is_relevant_group_entity"): group, ("payee", "is_excluded_entity"): excluded,
            ("flow", "consideration"): 1000.0, ("flow", "cost_basis"): 600.0, ("flow", "intragroup_transfer"): False}


def recipient_hk(ratio=3, months=24, pure=False, compliant=True):
    return {("payee", "is_mne_member"): True, ("flow", "receipt_kind"): "REMITTED", ("payee", "pure_equity_holding"): pure,
            ("payee", "registration_filing_compliant"): compliant, ("payee", "hk_resident_or_pe"): True,
            ("flow", "ratio"): ratio, ("flow", "holding_months"): months, ("flow", "foreign_taxed"): True,
            ("flow", "underlying_profits_taxed"): False, ("flow", "foreign_headline_rate"): 25, ("flow", "deductible_at_payer"): False,
            ("payee", "fixed_place_in_sg"): False, ("payee", "substance_ruled_adequate"): False, ("flow", "intragroup_transfer"): False}


# (name, payer = buyer, payee = seller / recipient, income, facts, jur, lo, hi, pending, cite, target for share transfers)
CASES = [
    # Mainland: direct share transfers (gain 40% of consideration)
    ("CN shares sold by a HK company, 30% held, no immovable: Mainland may tax, 10% x 40%", SG, HK, G, seller(), CN,
     4.0, 4.0, set(), "Arrangement 13(5) >= 25%; EIT 10% on the gain; no treaty benefit, so no PPT item", CN),
    ("CN shares sold by a HK company, 20% held, no immovable: residence state only", SG, HK, G, seller(max_ratio=20), CN,
     0.0, 4.0, {"payee.ppt"}, "Arrangement 13(7) (p4) residence only", CN),
    ("CN shares sold by a HK company, 20% held, 60% immovable: Mainland may tax", SG, HK, G, seller(max_ratio=20, immovable=60), CN,
     4.0, 4.0, set(), "Arrangement 13(4) (p5) > 50% immovable", CN),
    ("CN listed shares bought and sold on the same exchange by a HK company", SG, HK, G, seller(listed=True), CN,
     0.0, 4.0, {"payee.ppt"}, "Arrangement 13(6) (p4)", CN),
    ("CN shares sold by a SG company, 20% held: residence only", HK, SG, G, seller(max_ratio=20), CN, 0.0, 4.0, {"payee.ppt"},
     "Agreement 13(5)", CN),
    # Mainland: indirect transfers
    ("offshore holdco sold, four-factor case: deemed no commercial purpose, 10% x 40%", SG, SG, G, indirect(), CN,
     4.0, 4.0, set(), "公告2015年第7号 第四条", HK),
    ("offshore holdco sold, value 60%: judged, not deemed", SG, SG, G, indirect(value=60), CN,
     None, 4.0, {"payee.no_reasonable_commercial_purpose"}, "第三条 综合分析", HK),
    ("offshore holdco sold on a public market", SG, SG, G, indirect(listed=True), CN, 0.0, 0.0, set(), "第五条(一)", HK),
    ("intragroup reorganisation, 100% owned, paid in equity, no tax reduction later", SG, SG, G,
     indirect(reorg=100, equity=True, not_reduced=True), CN, 0.0, 0.0, set(), "第六条", HK),
    ("no Mainland property under the target", SG, SG, G, {**indirect(value=0, asset=0, income_ratio=0), ("flow", "indirect_cn_target"): False},
     CN, None, None, set(), "第一条 scope", HK),
    # Singapore receiving side
    ("CN dividend remitted to SG, taxed abroad at 25%: exempt if the Comptroller agrees, else 17% less credit", CN, SG, D,
     recipient_sg(), SG, 0.0, 7.0, {"payee.exemption_beneficial"}, "s13(8),(9); s50 credit for 10% Mainland tax", None),
    ("CN dividend kept offshore: no Singapore charge", CN, SG, D, recipient_sg(kind="NONE"), SG, None, None, set(), "s10(25)", None),
    ("HK dividend remitted to SG, headline 16.5%, underlying taxed: exempt or 17% (no HK tax to credit)", HK, SG, D,
     recipient_sg(headline=16.5), SG, 0.0, 17.0, {"payee.exemption_beneficial"}, "s13(8),(9),(10); s50A", None),
    ("CN interest remitted to SG by a corporate lender: 17% less the 10% Mainland tax (Agreement cap 10%)", CN, SG, I,
     {**recipient_sg(), ("payee", "residence_cert"): True, ("payee", "payee_is_government"): False,
      ("payee", "payee_is_financial_institution"): False, ("payee", "onpay_ratio_12m"): 0, ("payee", "fixed_place_in_sg"): False},
     SG, 7.0, 7.0, set(), "s10(1)(d), s50; Agreement 11(2) 10%", None),
    ("CN share gain remitted to SG by a group entity without substance: s10L", CN, SG, G, recipient_sg(), SG,
     0.0, 2.8, {"payee.adequate_substance"}, "s10L; 17% x 40% less Mainland 10% x 40% credited", CN),
    # Hong Kong credits
    ("CN dividend to HK MNE, 3% holding: 16.5% less 10% Mainland tax when substance fails", CN, HK, D, recipient_hk(), HK,
     0.0, 6.5, {"payee.adequate_substance"}, "s15K; s50 credit", None),
    ("SG interest to HK MNE: 16.5% less 15% Singapore withholding when substance fails or the credit was provided in Hong Kong", SG, HK, I, recipient_hk(), HK,
     0.0, 1.5, {"payee.adequate_substance", "payee.income_sourced_in_hk"}, "s15K; s14 source is a judgement; s50AAA unilateral credit", None),
]


def lender(ratio=2.0, related=True):
    return {("payee", "residence_cert"): True, ("payee", "payee_is_government"): False, ("payee", "payee_is_financial_institution"): False,
            ("payee", "onpay_ratio_12m"): 0, ("payee", "fixed_place_in_sg"): False, ("payee", "payee_is_related"): related,
            ("payer", "related_party_debt_equity_ratio"): ratio}


# (name, payer, payee, income, facts, jur, expected (lo_total, hi_total), pending, cite): the payer's deduction counts negative
DEDUCTION_CASES = [
    ("CN pays interest to a related HK lender within 2:1: 10% withheld (or 7%), 25% deducted while the rate is within the benchmark", CN, HK, I, lender(), CN,
     (7.0 - 25.0, 10.0 + 6.0), {"payee.no_adverse_bo_factors", "payee.ppt", "flow.benchmark_rate", "flow.interest_rate", "flow.price_includes_vat", "flow.unified_borrowing_relending"},
     "EIT art 4 25%; 财税〔2008〕121号 一 2:1; 实施条例 第三十八条(二): the loan rate is unknown, so the ceiling keeps no deduction; "
     "the ceiling's 6% interest VAT, never credited (口径 D25)"),
    ("CN pays interest to a related HK lender at 3:1: deduction only if arm's length and within the benchmark", CN, HK, I, lender(ratio=3.0), CN,
     (7.0 - 25.0, 10.0 + 6.0), {"payee.no_adverse_bo_factors", "payee.ppt", "payer.arms_length_interest", "flow.benchmark_rate",
                                "flow.interest_rate", "flow.price_includes_vat", "flow.unified_borrowing_relending"},
     "121号 二; EIT art 46; 实施条例 第三十八条; 6% interest VAT at the ceiling (口径 D25)"),
    ("CN pays interest to an unrelated HK lender at 3:1: no thin-cap limit, benchmark test still", CN, HK, I, lender(ratio=3.0, related=False), CN,
     (7.0 - 25.0, 10.0 + 6.0), {"payee.no_adverse_bo_factors", "payee.ppt", "flow.benchmark_rate", "flow.interest_rate", "flow.price_includes_vat", "flow.unified_borrowing_relending"},
     "EIT art 46 applies to related parties; 实施条例 第三十八条 to every non-financial lender; 6% interest VAT at the ceiling (口径 D25)"),
    ("HK pays a deductible royalty to a SG associate: 16.5% deemed on 100%, 16.5% deducted", HK, SG, R,
     {("flow", "ip_used_in_hk"): True, ("flow", "royalty_deductible_in_hk"): True, ("payee", "payee_is_associate"): True,
      ("flow", "ip_never_owned_by_hk_business"): False, ("payee", "residence_cert"): True}, HK,
     (16.5 - 16.5, 16.5 - 16.5), set(), "s21A(a); s16(1)"),
    ("HK pays interest to a SG lender: no withholding; deduction needs s16(2) (lender taxable in HK or a financial institution) and is a judgement", HK, SG, I,
     {("payee", "residence_cert"): True}, HK, (-16.5, 0.0), {"payer.incurred_in_production_of_profits", "payee.lender_interest_taxable_in_hk", "payee.payee_is_financial_institution"}, "s16(1); no HK interest withholding"),
]


def main():
    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    out.write("oracle_kind = text_derived\n")
    bad = 0
    # remedy clocks on the receiving side: HK objection 1 month after the notice (s64), appeal 1 month after the
    # determination (s66); SG company objection 2 months (s76(3)(a))
    from .flow_tax import RULES
    from .rules.eval import Flow, evaluate_flow
    from .rules.tri import FLOOR, Ctx
    from .params import Params
    hk = {**recipient_hk(), ("flow", "assessment_notice_on"): date(2026, 5, 4), ("flow", "determination_on"): date(2026, 9, 30)}
    res = evaluate_flow(RULES, Ctx(hk), Flow(CN, HK, D, on=ON), FLOOR, Params(), amount=1000.0)
    sg = {**recipient_sg(), ("flow", "assessment_notice_on"): date(2026, 5, 4), ("payee", "fixed_place_in_sg"): False}
    res_sg = evaluate_flow(RULES, Ctx(sg), Flow(CN, SG, D, on=ON), FLOOR, Params(), amount=1000.0)
    for name, want, got in (("HK objection 1 month after the notice", date(2026, 6, 4), res.deadlines.get("objection", (None, None))[1]),
                            ("HK appeal 1 month after the determination", date(2026, 10, 30), res.deadlines.get("appeal", (None, None))[1]),
                            ("SG company objection 2 months after the notice", date(2026, 7, 4), res_sg.deadlines.get("objection", (None, None))[1])):
        ok = want == got
        bad += not ok
        out.write("%-4s %s%s\n" % ("ok" if ok else "DIFF", name, "" if ok else "  expected %s, got %s" % (want, got)))
    for name, payer, payee, income, facts, jur, (lo, hi), pending, cite in DEDUCTION_CASES:
        r = flow_tax(payer, payee, income, facts, jur, on=ON)
        wrong = []
        if abs(r.lo_total - lo) > 1e-6:
            wrong.append(("lo_total", lo, r.lo_total))
        if abs(r.hi_total - hi) > 1e-6:
            wrong.append(("hi_total", hi, r.hi_total))
        if set(r.conditions) != pending:
            wrong.append(("pending", sorted(pending), r.conditions))
        bad += bool(wrong)
        out.write("%-4s %s  [%s]\n" % ("ok" if not wrong else "DIFF", name, cite))
        for k, a, b in wrong:
            out.write("        %s: expected %s, got %s\n" % (k, a, b))
    for name, payer, payee, income, facts, jur, lo, hi, pending, cite, target in CASES:
        r = flow_tax(payer, payee, income, facts, jur, on=ON, target_loc=target)
        wrong = []
        if r.lo != lo:
            wrong.append(("lo", lo, r.lo))
        if r.hi != hi:
            wrong.append(("hi", hi, r.hi))
        if set(r.conditions) != pending:
            wrong.append(("pending", sorted(pending), r.conditions))
        bad += bool(wrong)
        out.write("%-4s %s  [%s]\n" % ("ok" if not wrong else "DIFF", name, cite))
        for k, a, b in wrong:
            out.write("        %s: expected %s, got %s\n" % (k, a, b))
    out.write("%d checks, %d with differences\n" % (len(CASES) + len(DEDUCTION_CASES) + 3, bad))
    out.flush()
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
