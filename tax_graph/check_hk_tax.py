"""Scenario check for the Hong Kong rules.

  python -m tax_graph.check_hk_tax          (conda env "pytorch")

oracle_kind = text_derived: expected values are read by hand from the cited provisions (rates, deemed-profit
shares, the nexus formula). A regression harness for the rule layer, not an independent oracle.
"""
import io
import sys
from datetime import date

from .hk_tax import CN, HK, SG, hk_tax

D, I, R, G = "DIVIDEND", "INTEREST", "ROYALTY", "SHARE_TRANSFER"
ON = date(2026, 3, 10)


def inbound(mne=True, kind="REMITTED", pure=False, compliant=True, resident=True, ratio=10, months=24,
            taxed=True, underlying=False, headline=25, deductible=False):
    """Hong Kong-side facts, plus determinate source-side facts so the credited foreign tax is known:
    Mainland: certificate held, listed parent (safe harbour), direct holding = ratio; Singapore: no fixed place."""
    return {("payee", "is_mne_member"): mne, ("flow", "receipt_kind"): kind, ("payee", "pure_equity_holding"): pure,
            ("payee", "registration_filing_compliant"): compliant, ("payee", "hk_resident_or_pe"): resident,
            ("flow", "ratio"): ratio, ("flow", "holding_months"): months, ("flow", "foreign_taxed"): taxed,
            ("flow", "underlying_profits_taxed"): underlying, ("flow", "foreign_headline_rate"): headline,
            ("flow", "deductible_at_payer"): deductible,
            ("payee", "residence_cert"): True, ("payee", "bo_safe_harbour"): True, ("payee", "onpay_ratio_12m"): 0,
            ("flow", "direct_ratio"): ratio, ("flow", "max_ratio_12m"): ratio, ("flow", "immovable_ratio"): 0,
            ("flow", "listed_market_trade"): False, ("flow", "is_aircraft_or_ship_lease"): False, ("flow", "is_equipment_lease"): False,
            ("payee", "payee_is_government"): False, ("payee", "payee_is_financial_institution"): False,
            ("flow", "reinvested_in_cn"): False, ("payee", "fixed_place_in_sg"): False, ("payee", "substance_ruled_adequate"): False,
            ("flow", "intragroup_transfer"): False}


def royalty(used_in_hk=True, deductible=False, associate=False, never_hk_owned=False, cert=True):
    return {("flow", "ip_used_in_hk"): used_in_hk, ("flow", "royalty_deductible_in_hk"): deductible,
            ("payee", "payee_is_associate"): associate, ("flow", "ip_never_owned_by_hk_business"): never_hk_owned,
            ("payee", "residence_cert"): cert}


def gain(consideration=1000.0, cost=600.0, ratio=20, months=30, trading_stock=False, elected=True):
    return {("flow", "consideration"): consideration, ("flow", "cost_basis"): cost, ("flow", "ratio"): ratio,
            ("flow", "holding_months"): months, ("flow", "held_as_trading_stock"): trading_stock,
            ("payee", "sch17k_elected"): elected}


# a transfer of Hong Kong stock between parties the facts do not relate: the SDO s45 relief stays open (口径 D18)
S45 = {"flow.associated_ratio", "flow.clawback_event_within_2y", "flow.stamp_relief_claimed"}

# (name, payer, payee, income, facts, lo, hi, pending under lo, cite)
CASES = [
    # outbound royalties
    ("HK royalty to CN, IP used in HK, not an associate: 16.5% x 30%, cap 7% not binding", HK, CN, R, royalty(),
     4.95, 4.95, set(), "s15(1)(b), s21A 30%, Arrangement 12(2) 7% not binding, so nothing is pending"),
    ("HK royalty to CN, associate: 16.5% on 100%, capped at 7% for a beneficial owner", HK, CN, R, royalty(associate=True),
     7.0, 16.5, {"payee.beneficial_owner", "payee.ppt"}, "s21A(a) 100%; Arrangement 12(2)"),
    ("HK royalty to CN, associate, IP never owned by a HK business: proviso keeps 30%", HK, CN, R,
     royalty(associate=True, never_hk_owned=True), 4.95, 4.95, set(), "s21A(a) proviso"),
    ("HK royalty to SG, associate: no treaty, 16.5%", HK, SG, R, royalty(associate=True), 16.5, 16.5, set(), "s21A(a); no HK-SG DTA"),
    ("HK royalty to SG, IP neither used in HK nor deductible: not deemed", HK, SG, R, royalty(used_in_hk=False), None, None, set(), "s15(1)(b), (ba)"),
    ("HK dividend to CN: no Hong Kong charge", HK, CN, D, {}, None, None, set(), "no charging provision"),
    # inbound FSIE
    ("CN dividend to HK, not an MNE entity: outside FSIE", CN, HK, D, inbound(mne=False), None, None, set(), "s15I(3)"),
    ("CN dividend to HK MNE, kept offshore: not received in HK", CN, HK, D, inbound(kind="NONE"), None, None, set(), "s15H(5), s15I(1)"),
    ("CN dividend to HK MNE, remitted, participation met: exempt under lo; under hi 16.5% less the 10% Mainland tax", CN, HK, D, inbound(),
     0.0, 6.5, {"payee.adequate_substance", "payee.no_main_purpose_of_tax_benefit"}, "s15M(2) 5%/12 months, s15N(2),(3),(4); s50"),
    ("CN dividend to HK MNE, 3% holding, non-pure entity: only substance can except", CN, HK, D, inbound(ratio=3),
     0.0, 6.5, {"payee.adequate_substance"}, "s15K(2)(b); s50"),
    ("CN dividend to HK MNE, 3% holding, pure equity-holder not compliant: charged, Mainland tax credited", CN, HK, D,
     inbound(ratio=3, pure=True, compliant=False), 6.5, 6.5, set(), "s15K(2)(a)(i); s50"),
    ("CN dividend deductible for the payer: anti-hybrid, participation fails", CN, HK, D, inbound(deductible=True),
     0.0, 6.5, {"payee.adequate_substance"}, "s15N(3); s50"),
    ("SG interest to HK MNE, remitted: offshore, substance is the only exception; 15% Singapore tax credited unilaterally", SG, HK, I, inbound(),
     0.0, 1.5, {"payee.adequate_substance", "payee.income_sourced_in_hk"},
     "s15K; s50AAA; whether the credit was provided in Hong Kong (s14) is a judgement, charged 16.5% less 15% if so"),
    ("CN IP income to HK MNE, QE 80 / NE 20: F = 100%, nothing taxable if foreign-sourced", CN, HK, R,
     {**inbound(), ("flow", "qualifying_rd_expenditure"): 80.0, ("flow", "non_qualifying_expenditure"): 20.0},
     0.0, 6.5, {"payee.income_sourced_in_hk"},
     "Sch 17FC s3: F = QE x 130% / (QE + NE), capped at 100%; if the royalty arises in Hong Kong (s14) 16.5% less the 10% Mainland tax"),
    ("CN IP income to HK MNE, QE 50 / NE 50: F = 65%, 35% taxable at 16.5% if foreign-sourced", CN, HK, R,
     {**inbound(), ("flow", "qualifying_rd_expenditure"): 50.0, ("flow", "non_qualifying_expenditure"): 50.0},
     0.0, 6.5, {"payee.income_sourced_in_hk"},
     "Sch 17FC s3: 16.5% x 35% = 5.775%, absorbed by the credit for the 7% Mainland tax; Hong Kong-sourced under hi: 16.5% less the 10% Mainland tax credited", 10.0),
    ("CN share gain to HK MNE, remitted, 40% gain, participation met", CN, HK, G,
     {**inbound(), ("flow", "consideration"): 1000.0, ("flow", "cost_basis"): 600.0},
     0.0, 2.6, {"payee.adequate_substance", "payee.no_main_purpose_of_tax_benefit"},
     "s15I(1)(b); s15M; 16.5% x 40%; under hi the PPT denies the Art 13 exemption, so 10% x 40% Mainland tax is credited"),
    # onshore gains
    ("HK onshore gain, 20% for 30 months, elected: tax certainty", HK, CN, G, gain(), 0.0, 0.0, S45, "Sch 17K s5"),
    ("HK onshore gain, no election: capital or revenue is a judgement", HK, CN, G, gain(elected=False),
     0.0, 6.6, {"payee.capital_asset"} | S45, "s14 capital assets excluded; 16.5% x 40%"),
    ("HK onshore gain, 10% holding, elected: below 15%, judgement again", HK, CN, G, gain(ratio=10),
     0.0, 6.6, {"payee.capital_asset"} | S45, "Sch 17K s5(1)(a) 15%"),
]


def main():
    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    out.write("oracle_kind = text_derived\n")
    bad = 0
    for case in CASES:
        name, payer, payee, income, facts, lo, hi, pending, cite = case[:9]
        credit = case[9] if len(case) > 9 else None            # expected credit under hi, where it matters
        target = CN if (payer, income) == (CN, G) else None
        r = hk_tax(payer, payee, income, facts, on=ON, target_loc=target)
        wrong = []
        if r.lo != lo:
            wrong.append(("lo", lo, r.lo))
        if r.hi != hi:
            wrong.append(("hi", hi, r.hi))
        if credit is not None and r.hi_credit != credit:
            wrong.append(("credit", credit, r.hi_credit))
        if set(r.conditions) != pending:
            wrong.append(("pending", sorted(pending), r.conditions))
        bad += bool(wrong)
        out.write("%-4s %s  [%s]\n" % ("ok" if not wrong else "DIFF", name, cite))
        for k, a, b in wrong:
            out.write("        %s: expected %s, got %s\n" % (k, a, b))
    out.write("%d checks, %d with differences\n" % (len(CASES), bad))
    out.flush()
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
