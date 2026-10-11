"""Checks of the 范围.md v1.1 mechanics on hand-built graphs: Pillar Two top-up, the CFC inclusion, residence variants,
VAT withholding with the input credit, an outside lender (financing template), stamp duty on both sides, recurring
years. Expected values are read off the texts the params cite (oracle_kind = text_derived); the engine is run directly.

    python -m tax_graph.check_scope          (conda env "pytorch")
"""
import io
import sys
from dataclasses import replace
from datetime import date

from .cases import CASE_A, EVENT_A, BASE_A
from .data.domain import ADJUSTABLE, Event
from .engine import EX_ANTE, EX_POST, CaseCtx, bounds, engine
from .model import CN, HK, SG, DIVIDEND, INTEREST, ROYALTY, SERVICE_FEE, SHARE_TRANSFER, Entity, FlowEdge, Graph, HoldEdge
from .rules.tri import CEILING, DISCRETION, FLOOR, Need
from .scenarios import BUYER, FINANCING, HOLD, HOLDING, LENDER, OP, ULT, Case, RoleFacts

ON = date(2026, 3, 31)
NO_RELIEF = {"p2_qualified_cbcr_hk": False, "p2_qualified_cbcr_sg": False, "p2_dm_avg_revenue_eur_hk": 1e9, "p2_dm_avg_income_eur_hk": 1e9,
             "p2_dm_avg_revenue_eur_sg": 1e9, "p2_dm_avg_income_eur_sg": 1e9}   # neither Pillar Two relief available (口径 D17)


def run(g, bound, mode=EX_POST):
    return engine(g, lambda facts: CaseCtx(facts, {}, mode, ADJUSTABLE), bound)


def main():
    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    bad = n = 0

    def check(ok, text):
        nonlocal bad, n
        bad += 0 if ok else 1
        n += 1
        out.write("%-4s %s\n" % ("ok" if ok else "FAIL", text))

    # ---- Pillar Two: a Hong Kong entity of an in-scope group with ETR 10% owes 5% of its excess profit (GloBE Art 5.2; HKMTT)
    g = Graph({"E": Entity("E", HK, attrs={**NO_RELIEF, "globe_income": 1000.0, "covered_taxes_other": 100.0, "group_revenue_eur": 1e9, "sbie": 0.0,
                                           "managed_from": HK}),
               "U": Entity("U", SG, attrs={"managed_from": SG})},
              [HoldEdge("U", "E", 100.0, date(2020, 1, 1), 100.0)],
              [FlowEdge("d", "E", "U", DIVIDEND, 100.0, ON, attrs={"receipt_kind": "NONE"})])
    lo = run(g, FLOOR)[2]
    check("p2:E" in lo and abs(lo["p2:E"].tax - 50.0) < 1e-6, "Pillar Two: (15%% - 10%%) x 1000 = 50 top-up on the HK entity (got %s)" % lo.get("p2:E", type("x", (), {"tax": None})).tax)
    with_sbie = replace(g.entities["E"], attrs={k: v for k, v in g.entities["E"].attrs.items() if k != "sbie"})
    with_sbie.attrs.update(payroll=1000.0, tangible_assets=1000.0)              # 2026: 9.4% + 7.4% = 168 excluded
    lo3 = run(Graph({**g.entities, "E": with_sbie}, g.holds, g.flows), FLOOR)[2]
    check(abs(lo3["p2:E"].tax - 0.05 * (1000.0 - 168.0)) < 1e-6, "Pillar Two: SBIE from payroll and tangible assets at the 2026 transition rates (got %s)" % lo3["p2:E"].tax)
    small = replace(g.entities["E"], attrs=dict(g.entities["E"].attrs, group_revenue_eur=1e8))
    lo2 = run(Graph({**g.entities, "E": small}, g.holds, g.flows), FLOOR)[2]
    check("p2:E" not in lo2 or lo2["p2:E"].tax == 0.0, "Pillar Two: below EUR 750 million the top-up rule does not apply")

    # ---- CFC: a Mainland parent's low-taxed Hong Kong subsidiary retaining 10m: nothing at the floor (judgements), 25% less
    #      the underlying tax at the ceiling, grossed up (EIT art 45; 实施条例 117-118; 2009-2 第八十四条; 125号 第五条)
    g = Graph({"ULT": Entity("ULT", CN), "SUB": Entity("SUB", HK, attrs={"after_tax_profit": 10_000_000.0, "managed_from": HK, "residence_cert": True,
                                                                          "bo_safe_harbour": True}),
               "OP": Entity("OP", CN)},
              [HoldEdge("ULT", "SUB", 100.0, date(2020, 1, 1), 1.0), HoldEdge("ULT", "OP", 100.0, date(2020, 1, 1), 1.0)],
              [FlowEdge("i", "OP", "SUB", INTEREST, 1_000_000.0, ON, attrs={"receipt_kind": "NONE", "interest_rate": 5.0, "benchmark_rate": 5.0})])
    lo, hi = run(g, FLOOR)[2], run(g, CEILING)[2]
    cfc = "cfc:SUB>ULT"
    check(cfc in lo and lo[cfc].tax == 0.0, "CFC: floor leaves the inclusion uncharged (active income / business need are judgements)")
    cn_hi = sum(hi[cfc].flow.amount * it.effective / 100.0 for it in hi[cfc].items if it.jur == CN) if cfc in hi else None
    # at the ceiling SUB bore 10% Mainland withholding on the 1m (treaty cap denied) and 16.5% Hong Kong FSIE tax less that
    # credit: 100,000 + 65,000 = 165,000; underlying share 1.65% grosses the 10m up and is credited
    expect = 0.25 * 10_000_000 * 1.0165 - 165_000
    check(cn_hi is not None and abs(cn_hi - expect) < 1.0, "CFC: ceiling charges 25%% on the grossed-up 10m less the 165k the subsidiary bore = %.0f (got %s)" % (expect, cn_hi))

    # ---- residence by effective management: a Mainland-controlled HK company managed from the Mainland is a pending group
    g = Graph({"ULT": Entity("ULT", CN), "HOLD": Entity("HOLD", HK, attrs={"managed_from": CN, "residence_cert": True, "bo_safe_harbour": True}),
               "OP": Entity("OP", SG, attrs={"managed_from": SG})},
              [HoldEdge("ULT", "HOLD", 100.0, date(2020, 1, 1), 1.0), HoldEdge("HOLD", "OP", 100.0, date(2020, 1, 1), 1.0)],
              [FlowEdge("d", "OP", "HOLD", DIVIDEND, 1000.0, ON, attrs={"receipt_kind": "REMITTED", "foreign_taxed": True, "foreign_headline_rate": 17})])
    b = bounds(g, lambda facts: CaseCtx(facts, {}, EX_POST))
    check(("cn.residence.pem", "HOLD") in b.groups and b.lo <= b.hi, "residence: the determination is a pending group, floor %.2f <= ceiling %.2f" % (b.lo, b.hi))
    check(b.cost[("cn.residence.pem", "HOLD")] >= 0, "residence: deciding it the other way never lowers the floor (cost %.2f)" % b.cost[("cn.residence.pem", "HOLD")])

    # ---- VAT: a fee for services performed in the Mainland carries 6/106 withheld from the payee and the same input credit for the payer
    g = Graph({"OP": Entity("OP", CN, attrs={"vat_general_taxpayer": True}), "ULT": Entity("ULT", SG, attrs={"managed_from": SG}),
               "S": Entity("S", SG, attrs={"managed_from": SG, "residence_cert": True, "fixed_place_in_cn": False})},
              [HoldEdge("ULT", "OP", 100.0, date(2020, 1, 1), 1.0), HoldEdge("ULT", "S", 100.0, date(2020, 1, 1), 1.0)],
              [FlowEdge("f", "OP", "S", SERVICE_FEE, 1060.0, ON, attrs={"service_location": CN, "service_days_12m": 10, "service_kind": "MANAGEMENT",
                                                                       "profit_margin": 20, "receipt_kind": "REMITTED", "foreign_taxed": True,
                                                                       "foreign_headline_rate": 25, "price_includes_vat": True})])
    lo = run(g, FLOOR)[2]["f"]
    vat = [it for it in lo.items if it.levy == "vat"]
    check(len(vat) == 2 and abs(sum(1060.0 * it.effective / 100.0 for it in vat)) < 1e-6 and any(abs(1060.0 * it.effective / 100.0 - 60.0) < 1e-6 for it in vat),
          "VAT: 1060 x 6/106 = 60 withheld from the payee and credited to the payer (net nil in the group)")

    # ---- an outside bank: its withholding is its own unless the loan grosses it up
    case = Case(roles={OP: RoleFacts(CN), ULT: RoleFacts(SG, {"managed_from": SG}), LENDER: RoleFacts(SG, {"residence_cert": True, "managed_from": SG}, type="BANK_FI")},
                holds={(ULT, OP): HoldEdge(ULT, OP, 100.0, date(2020, 1, 1), 1.0)},
                flows={"int": {"interest_rate": 5.0, "benchmark_rate": 5.0, "price_includes_vat": False}})
    ev = Event(interest=1000.0, on=ON)
    g = FINANCING.build(ev, {LENDER: SG, "payment": False}, case)
    total_lo = run(g, FLOOR, EX_ANTE)[0]
    check(abs(total_lo - (-250.0)) < 1e-6, "financing: the bank's 7%% withholding is outside the group; the group's floor is the 25%% deduction alone (got %.2f)" % total_lo)
    case2 = replace(case, flows={"int": {"interest_rate": 5.0, "benchmark_rate": 5.0, "wht_borne_by_payer": True, "price_includes_vat": False}})
    total_lo2 = run(FINANCING.build(ev, {LENDER: SG, "payment": False}, case2), FLOOR, EX_ANTE)[0]
    check(abs(total_lo2 - (70.0 - 250.0)) < 1e-6, "financing: with a gross-up clause the group bears the 7%% (got %.2f)" % total_lo2)

    # ---- stamp duty: a Hong Kong share sale stamps both contract notes at 0.1%; the outside buyer's note is not the group's
    g = HOLDING.build(replace(EVENT_A, dividend=None, onward=None), {**BASE_A, "exit_route": "INDIRECT"}, CASE_A)
    lo = run(g, FLOOR, EX_ANTE)[2]["exit"]
    stamps = [(it.borne_by, 5000.0 * it.effective / 100.0) for it in lo.items if it.levy == "stamp"]
    check(sorted(stamps) == [("payee", 5.0), ("payer", 5.0)], "stamp: 0.1%% on the seller's and the buyer's notes (got %s)" % stamps)

    # ---- Singapore: the buyer's 0.2% on a share transfer (an outside buyer: its own), GST reverse charge for a partially
    #      exempt payer, the domestic top-up tax at the same shortfall logic
    g = Graph({"S": Entity("S", SG, attrs={"managed_from": SG}), "U": Entity("U", HK, attrs={"managed_from": HK, "residence_cert": True}),
               "B": Entity("B", CN)},
              [HoldEdge("U", "S", 100.0, date(2020, 1, 1), 1000.0)],
              [FlowEdge("x", "B", "U", SHARE_TRANSFER, 5000.0, ON, target="S", attrs={"receipt_kind": "NONE"})])
    lb = run(g, FLOOR)[2]["x"]
    st = [(it.borne_by, round(5000.0 * it.effective / 100.0, 2)) for it in lb.items if it.levy == "stamp"]
    check(st == [("payer", 10.0)], "SG stamp: 0.2%% on the transferee only (got %s)" % st)
    g = Graph({"P": Entity("P", SG, attrs={"managed_from": SG, "gst_input_fully_recoverable": False}),
               "U": Entity("U", SG, attrs={"managed_from": SG}), "V": Entity("V", HK, attrs={"managed_from": HK, "residence_cert": True, "fixed_place_in_sg": False})},
              [HoldEdge("U", "P", 100.0, date(2020, 1, 1), 1.0), HoldEdge("U", "V", 100.0, date(2020, 1, 1), 1.0)],
              [FlowEdge("f", "P", "V", SERVICE_FEE, 1000.0, ON, attrs={"service_location": HK, "service_days_12m": 0, "profit_margin": 20})])
    hi = run(g, CEILING)[2]["f"]
    gst = [round(1000.0 * it.effective / 100.0, 2) for it in hi.items if it.levy == "vat" and it.borne_by == "payer"]
    check(gst == [90.0], "SG GST: a partially exempt payer with an unknown recovery ratio: 9%% at the ceiling, nil at the floor (got %s)" % gst)
    g = Graph({"E": Entity("E", SG, attrs={**NO_RELIEF, "globe_income": 1000.0, "covered_taxes_other": 100.0, "group_revenue_eur": 1e9, "sbie": 0.0, "managed_from": SG}),
               "U": Entity("U", HK, attrs={"managed_from": HK})},
              [HoldEdge("U", "E", 100.0, date(2020, 1, 1), 100.0)],
              [FlowEdge("d", "E", "U", DIVIDEND, 100.0, ON, attrs={"receipt_kind": "NONE"})])
    lo = run(g, FLOOR)[2]
    check("p2:E" in lo and abs(lo["p2:E"].tax - 50.0) < 1e-6, "SG Pillar Two: (15%% - 10%%) x 1000 = 50 domestic top-up (got %s)" % lo.get("p2:E", type("x", (), {"tax": None})).tax)

    # ---- Pillar Two by jurisdiction (口径 D14): the constituent entities located in Hong Kong are blended (GloBE Art 5.1.1,
    #      5.2.3) and the top-up shared by GloBE income (Art 5.2.4; MMT Act s16(2) A x B / C)
    def p2_graph(loc, rows, **extra):
        ents = {k: Entity(k, loc, attrs=dict({**NO_RELIEF, "group_revenue_eur": 1e9, "sbie": 0.0, "managed_from": loc}, globe_income=inc,
                                             **({"covered_taxes_other": tax} if tax is not None else {}), **extra))
                for k, inc, tax in rows}
        ents["U"] = Entity("U", CN)
        return Graph(ents, [HoldEdge("U", k, 100.0, date(2020, 1, 1), 100.0) for k, _, _ in rows],
                     [FlowEdge("d", rows[0][0], "U", DIVIDEND, 100.0, ON, attrs={"receipt_kind": "NONE"})])

    def tax_of(labels, fid):
        return labels[fid].tax if fid in labels else None

    lo = run(p2_graph(HK, [("E1", 1000.0, 50.0), ("E2", 1000.0, 250.0)]), FLOOR)[2]
    check(tax_of(lo, "p2:E1") == 0.0 and tax_of(lo, "p2:E2") == 0.0,
          "P2 blending: ETRs 5%% and 25%% blend to 15%%: no top-up in the jurisdiction (got %s, %s)" % (tax_of(lo, "p2:E1"), tax_of(lo, "p2:E2")))
    lo = run(p2_graph(HK, [("E1", 3000.0, 0.0), ("E2", 1000.0, 0.0)]), FLOOR)[2]
    check(tax_of(lo, "p2:E1") == 450.0 and tax_of(lo, "p2:E2") == 150.0,
          "P2 allocation: 15%% x 4000 = 600 shared 3:1 by GloBE income = 450 / 150 (got %s, %s)" % (tax_of(lo, "p2:E1"), tax_of(lo, "p2:E2")))
    lo = run(p2_graph(SG, [("E1", 1000.0, 100.0), ("E2", -400.0, 0.0)]), FLOOR)[2]
    check(tax_of(lo, "p2:E1") == 0.0 and "p2:E2" not in lo,
          "P2 blending: a loss-making entity lowers the net GloBE income: 100 / 600 = 16.7%%, no top-up (got %s)" % tax_of(lo, "p2:E1"))

    # ---- additional current top-up (口径 D15): no net GloBE income, covered taxes below 15% of the net loss
    lo = run(p2_graph(SG, [("E", -1000.0, -300.0)], p2_negative_tax_election=False), FLOOR)[2]
    check(tax_of(lo, "p2:E") == 150.0, "SG s21(1): 15%% x -1000 - (-300) = 150, all on the entity (s16(3)(a)) (got %s)" % tax_of(lo, "p2:E"))
    lo = run(p2_graph(SG, [("E", -1000.0, -300.0)], p2_negative_tax_election=True, p2_carry_back_topup=40.0), FLOOR)[2]
    check(tax_of(lo, "p2:E") == 40.0, "SG s21(2) election: only the part attributable to the carry back of losses stays (got %s)" % tax_of(lo, "p2:E"))
    g = p2_graph(SG, [("E", -1000.0, -300.0)])
    _, grp_lo, lo = run(g, FLOOR, EX_ANTE)
    hi = run(g, CEILING, EX_ANTE)[2]
    check(("data.p2_negative_tax_election", "SG") in grp_lo and tax_of(lo, "p2:E") is None and tax_of(hi, "p2:E") == 150.0,
          "SG s21(2) unstated ex ante: the election is a plan action; electing with the attribution unknown: nil .. 150 (got %s .. %s)"
          % (tax_of(lo, "p2:E"), tax_of(hi, "p2:E")))
    lo = run(p2_graph(HK, [("E1", 200.0, -100.0), ("E2", -1000.0, -50.0)]), FLOOR)[2]
    check(tax_of(lo, "p2:E1") == 30.0 and "p2:E2" not in lo,
          "HK Art 4.1.5 / 5.4.3: 15%% x -800 - (-150) = 30, all on the entity whose covered taxes fall below its own 15%% (got %s)" % tax_of(lo, "p2:E1"))
    grp = run(p2_graph(HK, [("E", -100.0, None)]), FLOOR)[1]
    check(("data.p2_taxes", "HK") in grp, "P2: a jurisdiction without net GloBE income asks for unknown covered taxes (they may be negative without limit)")

    # ---- 口径 D16: one top-up per financial year; a company the plan creates has exactly its modelled flows; the tax on
    #      excluded dividends is no covered tax (GloBE Art 3.2.1(b), 4.1.3(a); MMT Act s2, reg 38(2)(a))
    g = p2_graph(HK, [("E1", 1000.0, 0.0)])
    g = Graph(g.entities, g.holds, g.flows + [FlowEdge("d@2027", "E1", "U", DIVIDEND, 100.0, date(2027, 3, 31), attrs={"receipt_kind": "NONE"})])
    lo = run(g, FLOOR)[2]
    check(tax_of(lo, "p2:E1") == 150.0 and tax_of(lo, "p2:E1@2027") == 150.0,
          "P2 per year: the 2026 and the 2027 top-up, 150 each (got %s, %s)" % (tax_of(lo, "p2:E1"), tax_of(lo, "p2:E1@2027")))
    ents = {"ULT": Entity("ULT", HK, attrs={**NO_RELIEF, "group_revenue_eur": 1e9, "sbie": 0.0, "managed_from": HK, "globe_income": 1000.0,
                                            "covered_taxes_other": 0.0}),
            "HOLD": Entity("HOLD", HK, attrs={"created_by_plan": True, "placed_by_plan": True, "managed_from": HK}),
            "OP": Entity("OP", CN)}
    g = Graph(ents, [HoldEdge("ULT", "HOLD", 100.0, None, None, designed=True), HoldEdge("HOLD", "OP", 100.0, date(2020, 1, 1), 100.0)],
              [FlowEdge("d", "OP", "HOLD", DIVIDEND, 1000.0, ON, attrs={"receipt_kind": "NONE", "listed_market_trade": False})])
    _, grp, lo = run(g, FLOOR)
    check(tax_of(lo, "p2:ULT") == 150.0 and "p2:HOLD" not in lo and ("data.p2_income", "HOLD") not in grp,
          "P2: a created holding company's GloBE income comes from its flows (the dividend excluded): 15%% x 1000 on ULT (got %s)" % tax_of(lo, "p2:ULT"))
    ents["E"] = Entity("E", HK, attrs={**NO_RELIEF, "group_revenue_eur": 1e9, "sbie": 0.0, "managed_from": HK, "globe_income": 1000.0,
                                       "covered_taxes_other": 0.0, "residence_cert": True})
    g = Graph({"E": ents["E"], "OP": ents["OP"]}, [HoldEdge("E", "OP", 100.0, date(2020, 1, 1), 100.0)],
              [FlowEdge("d", "OP", "E", DIVIDEND, 1000.0, ON, attrs={"receipt_kind": "NONE", "listed_market_trade": False})])
    lo, hi = run(g, FLOOR)[2], run(g, CEILING)[2]
    wht = sum(1000.0 * it.effective / 100.0 for it in lo["d"].items if it.jur == "CN" and it.levy == "income")
    check(wht > 0 and tax_of(lo, "p2:E") == 150.0 and tax_of(hi, "p2:E") == 150.0,
          "P2: the Mainland tax withheld on an excluded dividend (%.0f) is no covered tax: the top-up stays 150 (got %s .. %s)"
          % (wht, tax_of(lo, "p2:E"), tax_of(hi, "p2:E")))

    # ---- 口径 D17: transitional CbCR safe harbour (SG regs 69-74; HK Sch 61 Pt 3 Div 2) and de minimis (s19; Art 5.5)
    cbcr = {"p2_qualified_cbcr_sg": True, "p2_tcsh_history_sg": True, "p2_cbcr_revenue_sg": 500000000.0, "p2_cbcr_pbt_sg": 1000.0,
            "p2_cbcr_simplified_taxes_sg": 0.0, "p2_eur_rate": 0.125, "p2_dm_avg_revenue_eur_sg": 62500000.0, "p2_dm_avg_income_eur_sg": 6250000.0}
    lo = run(p2_graph(SG, [("E", 1000.0, 0.0)], **dict(cbcr, p2_tcsh_elected_sg=False)), FLOOR)[2]
    check(tax_of(lo, "p2:E") == 150.0, "TCSH: no test met (CbC profit 1000 above the nil carve-out, ETR 0%%): top-up 150 (got %s)" % tax_of(lo, "p2:E"))
    lo = run(p2_graph(SG, [("E", 1000.0, 0.0)], **dict(cbcr, p2_cbcr_pbt_sg=-5.0, p2_tcsh_elected_sg=True)), FLOOR)[2]
    check("p2:E" not in lo, "TCSH: a CbC loss meets the routine profits test (reg 73(1)(b)); elected: SG top-up nil")
    lo = run(p2_graph(SG, [("E", 1000.0, 0.0)], **dict(cbcr, p2_cbcr_simplified_taxes_sg=170.0, p2_tcsh_elected_sg=True)), FLOOR)[2]
    check("p2:E" not in lo, "TCSH: simplified ETR 170 / 1000 = 17% meets the 2026 test (reg 72(1)(b)): top-up nil")
    lo = run(p2_graph(SG, [("E", 1000.0, 0.0)], **dict(cbcr, p2_cbcr_simplified_taxes_sg=160.0, p2_tcsh_elected_sg=True)), FLOOR)[2]
    check(tax_of(lo, "p2:E") == 150.0, "TCSH: 16%% is below the 2026 test of 17%%: top-up 150 (got %s)" % tax_of(lo, "p2:E"))
    _, grp, lo = run(p2_graph(SG, [("E", 1000.0, 0.0)], p2_tcsh_elected_sg=True, p2_qualified_cbcr_sg=None), FLOOR)
    hi = run(p2_graph(SG, [("E", 1000.0, 0.0)], p2_tcsh_elected_sg=True, p2_qualified_cbcr_sg=None), CEILING)[2]
    check(("data.p2_tcsh", "SG") in grp and "p2:E" not in lo and tax_of(hi, "p2:E") == 150.0,
          "TCSH: CbC data unknown: pending, nil at the floor, 150 at the ceiling (got %s)" % tax_of(hi, "p2:E"))
    g = p2_graph(SG, [("E", 1000.0, 0.0)], **dict(cbcr, p2_cbcr_pbt_sg=-5.0, p2_tcsh_elected_sg=True))
    g = Graph(g.entities, g.holds, [replace(f, on=date(2027, 3, 31)) for f in g.flows])
    lo = run(g, FLOOR)[2]
    check(tax_of(lo, "p2:E") == 150.0, "TCSH: a financial year beginning in 2027 is outside the transition period: top-up 150 (got %s)" % tax_of(lo, "p2:E"))
    _, grp, lo = run(p2_graph(SG, [("E", 1000.0, 0.0)], **dict(cbcr, p2_cbcr_pbt_sg=-5.0)), FLOOR, EX_ANTE)
    check(("data.p2_tcsh_elected_sg", "SG") in grp and "p2:E" not in lo,
          "TCSH: eligible ex ante, the election is the plan's action (pending; nil at the floor)")
    lo = run(p2_graph(HK, [("E", 1000.0, 0.0)], p2_dm_avg_revenue_eur_hk=5000000.0, p2_dm_avg_income_eur_hk=500000.0,
                      p2_dm_elected_hk=True, p2_qualified_cbcr_hk=False), FLOOR)[2]
    check("p2:E" not in lo, "HK de minimis (Art 5.5.1): averages EUR 5m revenue and EUR 0.5m income, elected: top-up nil")
    lo = run(p2_graph(HK, [("E", 1000.0, 0.0)], p2_dm_avg_revenue_eur_hk=5000000.0, p2_dm_avg_income_eur_hk=1000000.0,
                      p2_dm_elected_hk=True, p2_qualified_cbcr_hk=False), FLOOR)[2]
    check(tax_of(lo, "p2:E") == 150.0, "HK de minimis: an average income of EUR 1m is not below EUR 1m: top-up 150 (got %s)" % tax_of(lo, "p2:E"))

    # ---- 口径 D18: the restructuring step — ULT transfers OP to the new HOLD (财税〔2009〕59号 §5, §7(1); 109号; 公告2013年第72号)
    def reorg_case(op_loc, ult_loc, value=4000.0, reorg_facts=None, up1=None):
        flows = {"up1": dict({"receipt_kind": "NONE"}, **(up1 or {})), "up2": {"receipt_kind": "NONE"}, "exit": {"receipt_kind": "NONE"}}
        flows["reorg"] = dict({"amount": value} if value is not None else {}, **(reorg_facts or {}))
        return Case(roles={OP: RoleFacts(op_loc, {"managed_from": op_loc}), ULT: RoleFacts(ult_loc, {"managed_from": ult_loc, "residence_cert": True}),
                           BUYER: RoleFacts(CN if op_loc != CN else HK, {"managed_from": CN if op_loc != CN else HK})},
                    holds={(ULT, OP): HoldEdge(ULT, OP, 100.0, date(2020, 1, 1), 3000.0)}, flows=flows)

    ev = Event(dividend=1000.0, onward=900.0, exit=5000.0, exit_on=date(2026, 12, 31), on=ON)
    g = HOLDING.build(ev, {HOLD: SG, "financing": "EQUITY", "payment": False, "exit_route": "DIRECT"}, reorg_case(CN, HK))
    step = next((f for f in g.flows if f.id == "reorg"), None)
    check(step is not None and (step.payer, step.payee, step.target, step.amount) == (HOLD, ULT, OP, 4000.0),
          "restructuring: a new HOLD between ULT and OP makes ULT transfer OP to HOLD at the stated consideration")
    lo, hi = run(g, FLOOR, EX_ANTE)[2], run(g, CEILING, EX_ANTE)[2]
    cn = lambda lb: round(sum(4000.0 * it.effective / 100.0 for it in lb.items if it.jur == CN and it.levy == "income" and not it.deferred), 2)
    check(cn(hi["reorg"]) == 100.0 and cn(lo["reorg"]) == 0.0,
          "restructuring: 10%% on the 1000 gain in general, deferred as a special reorganisation (59号 §7(1)) (got %s .. %s)" % (cn(lo["reorg"]), cn(hi["reorg"])))
    met = {"reorg_equity_payment_share": 100.0, "reorg_operations_unchanged_12m": True, "reorg_shares_kept_12m": True,
           "reorg_commitment_3y": True, "reorg_filed": True}
    g = HOLDING.build(ev, {HOLD: HK, "financing": "EQUITY", "payment": False, "exit_route": "DIRECT"}, reorg_case(CN, HK, reorg_facts=met))
    t = {Need(DISCRETION, "payee.reorg_reasonable_commercial_purpose"): True}
    lb = engine(g, lambda facts: CaseCtx(facts, t, EX_POST, ADJUSTABLE), CEILING)[2]
    exit_cn = round(sum(5000.0 * it.effective / 100.0 for it in lb["exit"].items if it.jur == CN and it.levy == "income"), 2)
    check(all(it.deferred for it in lb["reorg"].items if it.jur == CN and it.levy == "income") and exit_cn == 200.0,
          "restructuring: special treatment met — the step deferred, HOLD keeps ULT's basis 3000: 10%% x 2000 on the exit (got %s)" % exit_cn)
    g = HOLDING.build(ev, {HOLD: HK, "financing": "EQUITY", "payment": False, "exit_route": "DIRECT"}, reorg_case(CN, HK, value=None))
    grp = run(g, FLOOR, EX_ANTE)[1]
    check(("data.amount", "reorg") in grp, "restructuring: the consideration unknown: asked (the step's tax is unbounded without it)")
    g = HOLDING.build(ev, {HOLD: CN, "financing": "EQUITY", "payment": False, "exit_route": "DIRECT"}, reorg_case(HK, SG))
    lo, hi = run(g, FLOOR, EX_ANTE)[2], run(g, CEILING, EX_ANTE)[2]
    stamp = lambda lb: round(sum(4000.0 * it.effective / 100.0 for it in lb.items if it.jur == HK and it.levy == "stamp"), 2)
    check(stamp(lo["reorg"]) == 0.0 and stamp(hi["reorg"]) == 8.0,
          "restructuring: HK stock to an associated body (SDO s45, 90%%): no duty when claimed, 0.1%% x 2 otherwise (got %s .. %s)" % (stamp(lo["reorg"]), stamp(hi["reorg"])))
    g = HOLDING.build(ev, {HOLD: SG, "financing": "EQUITY", "payment": False, "exit_route": "DIRECT"},
                      reorg_case(CN, HK, reorg_facts=met, up1={"dividend_from_pre_reorg_profits": True}))
    t = {Need(DISCRETION, "payee.reorg_reasonable_commercial_purpose"): True, Need(DISCRETION, "payee.reorg_wht_burden_unchanged"): True}
    lb = engine(g, lambda facts: CaseCtx(facts, t, EX_POST, ADJUSTABLE), FLOOR)[2]
    up1_cn = round(sum(1000.0 * it.effective / 100.0 for it in lb["up1"].items if it.jur == CN and it.levy == "income"), 2)
    check(up1_cn == 100.0, "restructuring: special treatment across HK / SG, a dividend of pre-transfer profits: no treaty rate (公告2013年第72号 §8): 10%% (got %s)" % up1_cn)

    # ---- several activities in one case (scenarios.composite): one group, the chain part deciding who holds OP
    from .scenarios import IPCO, composite
    hip = composite(["ip", "holding"])
    c = reorg_case(CN, HK)
    c.flows["roy"] = {"receipt_kind": "NONE"}
    g = hip.build(replace(ev, royalty=500.0), {HOLD: HK, IPCO: SG, "financing": "EQUITY", "payment": False, "exit_route": "DIRECT"}, c)
    check(hip.name == "holding+ip" and sorted((h.holder, h.held) for h in g.holds) == [(HOLD, OP), (ULT, HOLD), (ULT, IPCO)]
          and sorted(f.id for f in g.flows) == ["exit", "iptx", "reorg", "roy", "up1", "up2"],
          "composite: holding + ip — OP held through HOLD only, the royalty to IPCO beside the chain, the IP moved to it (got %s)"
          % sorted(f.id for f in g.flows))
    try:
        composite(["holding", "repatriation"])
        ok_ = False
    except ValueError:
        ok_ = True
    check(ok_, "composite: holding and repatriation both distribute OP's profit: not combinable")

    # ---- 口径 D20: the income inclusion rule — a Hong Kong or Singapore parent pays its share of the top-up of a Mainland
    #      entity taxed below 15% (HK Sch 60 Art 2.1-2.3; SG MEMTA s11-s15); qualified status from the OECD central record
    low_cn = {"globe_income": 1000.0, "covered_taxes_other": 50.0, "sbie": 0.0, "p2_qualified_cbcr_cn": False,
              "p2_dm_avg_revenue_eur_cn": 1e9, "p2_dm_avg_income_eur_cn": 1e9, "managed_from": CN}
    quiet = lambda loc: {"globe_income": 0.0, "covered_taxes_other": 0.0, "sbie": 0.0, "managed_from": loc, "group_revenue_eur": 1e9}

    def iir_run(ents, holds):
        g = Graph({k: Entity(k, loc, attrs=dict(a)) for k, (loc, a) in ents.items()}, holds,
                  [FlowEdge("d", "OP", holds[-1].holder, DIVIDEND, 100.0, ON, attrs={"receipt_kind": "NONE"})])
        lb = run(g, FLOOR, EX_ANTE)[2]
        return {k: round(x.flow.amount * sum(it.effective for it in x.items if it.levy == "income") / 100.0, 2)
                for k, x in lb.items() if k.startswith("iir:")}

    got = iir_run({"OP": (CN, low_cn), "ULT": (SG, quiet(SG))}, [HoldEdge("ULT", "OP", 100.0, date(2020, 1, 1), 1.0)])
    check(got == {"iir:OP>ULT": 100.0},
          "IIR: a Singapore ultimate parent pays the MTT on a Mainland entity at 5%%: (15%% - 5%%) x 1000 = 100 (got %s)" % got)
    got = iir_run({"OP": (CN, low_cn), "HOLD": (HK, quiet(HK)), "ULT": (CN, quiet(CN))},
                  [HoldEdge("ULT", "HOLD", 100.0, date(2020, 1, 1), 1.0), HoldEdge("HOLD", "OP", 100.0, date(2020, 1, 1), 1.0)])
    check(got == {"iir:OP>HOLD": 100.0},
          "IIR: a Mainland ultimate parent applies none, so the Hong Kong intermediate parent does (Art 2.1.2): 100 (got %s)" % got)
    got = iir_run({"OP": (CN, low_cn), "HOLD": (HK, quiet(HK)), "ULT": (SG, quiet(SG))},
                  [HoldEdge("ULT", "HOLD", 100.0, date(2020, 1, 1), 1.0), HoldEdge("HOLD", "OP", 100.0, date(2020, 1, 1), 1.0)])
    check(got == {"iir:OP>ULT": 100.0},
          "IIR: a Singapore ultimate parent applies a qualified IIR, so the Hong Kong intermediate parent does not (Art 2.1.3(a)) (got %s)" % got)
    got = iir_run({"OP": (CN, low_cn), "HOLD": (HK, quiet(HK)), "ULT": (CN, quiet(CN))},
                  [HoldEdge("ULT", "HOLD", 60.0, date(2020, 1, 1), 1.0), HoldEdge("HOLD", "OP", 100.0, date(2020, 1, 1), 1.0)])
    check(got == {"iir:OP>HOLD": 100.0},
          "IIR: a partially-owned Hong Kong parent (40%% held outside) applies it in its own right on all it owns (Art 2.1.4) (got %s)" % got)
    got = iir_run({"OP": (SG, dict(quiet(SG), covered_taxes_other=0.0, globe_income=1000.0)), "ULT": (HK, quiet(HK))},
                  [HoldEdge("ULT", "OP", 100.0, date(2020, 1, 1), 1.0)])
    check(got == {}, "IIR: a Singapore entity has its qualified domestic top-up — no IIR top-up remains (got %s)" % got)

    # ---- 口径 D19: the client's own holding company leaves the chain — no CN / HK / SG law lets a company move its
    #      place of incorporation out, so it passes its stake on (to ULT, or to a new company) and is wound up
    from .cases import SCENARIOS
    from .facts import facts_for
    from .scenarios import IP, NEW, REPATRIATION, SERVICER, SERVICES
    _, cA, eA = SCENARIOS["A"]
    base = {"financing": "EQUITY", "payment": False, "exit_route": "DIRECT"}
    g = HOLDING.build(eA, dict(base, **{HOLD: None}), cA)
    un, wd, up = next((f for f in g.flows if f.id == "unwind"), None), next((f for f in g.flows if f.id == "wind"), None), g.holding(ULT, OP)
    check(un is not None and (un.payer, un.payee, un.target, un.amount) == (ULT, HOLD, OP, 5000.0) and wd is not None
          and (wd.payer, wd.payee, wd.income, wd.amount) == (HOLD, ULT, "LIQUIDATION", 5000.0)
          and up is not None and (up.ratio, up.since, up.cost) == (100.0, None, 5000.0) and g.entities[HOLD].attrs.get("wound_up_by_plan"),
          "unwinding: HOLD dissolved — its stake in OP to ULT at market value, then its liquidation to ULT; ULT holds OP from the step")
    lo, hi = run(g, FLOOR, EX_ANTE)[2], run(g, CEILING, EX_ANTE)[2]
    cn = lambda lb, amt: round(sum(amt * it.effective / 100.0 for it in lb.items if it.jur == CN and it.levy == "income" and not it.deferred), 2)
    check(cn(lo["unwind"], 5000.0) == 200.0 == cn(hi["unwind"], 5000.0) and cn(lo["exit"], 5000.0) == 0.0,
          "unwinding: no special reorganisation fits — 10%% x (5000 - 3000) in the Mainland on the step, the exit's basis is 5000 (got %s, %s, exit %s)"
          % (cn(lo["unwind"], 5000.0), cn(hi["unwind"], 5000.0), cn(lo["exit"], 5000.0)))
    g = HOLDING.build(eA, dict(base, **{HOLD: SG}), cA)
    new = HOLD + NEW
    flow = {f.id: f for f in g.flows}
    check(new in g.entities and g.entities[new].loc == SG and g.entities[new].attrs.get("created_by_plan") and g.holding(ULT, new).designed
          and g.holding(new, OP).cost == 5000.0 and g.holding(HOLD, OP) is None and flow["unwind"].payer == new
          and flow["up1"].payee == new and flow["up2"].payer == new and flow["exit"].payee == new,
          "unwinding: HOLD moved to Singapore — a new HOLD_NEW buys the stake at market value and holds it; HOLD is wound up")
    c2 = replace(cA, flows={k: {f: v for f, v in fs.items() if f != "amount"} for k, fs in cA.flows.items()})
    grp = run(HOLDING.build(eA, dict(base, **{HOLD: None}), c2), FLOOR, EX_ANTE)[1]
    check(("data.amount", "unwind") in grp and ("data.amount", "wind") in grp,
          "unwinding: the stake's market value and the liquidation distribution unknown: asked (unbounded without them)")
    _, cB, eB = SCENARIOS["B"]
    kept = run(HOLDING.build(eB, dict(base, **{HOLD: HK}), cB), FLOOR, EX_ANTE)[2]
    gone = run(HOLDING.build(eB, dict(base, **{HOLD: None}), cB), FLOOR, EX_ANTE)[2]
    check(any(k.startswith("cfc:HOLD") for k in kept) and not any(k.startswith("cfc:HOLD") for k in gone),
          "unwinding: a holding company wound up in the horizon has distributed its profits — no CFC inclusion (there is one while kept)")
    _, cE, eE = SCENARIOS["E"]
    lb = run(REPATRIATION.build(eE, {HOLD: HK, "repatriation": "LIQUIDATION", "payment": False}, cE), CEILING, EX_ANTE)[2]
    st = [(k, it.jur) for k, x in lb.items() for it in x.items if it.levy == "stamp" and it.effective]
    check(not st, "a liquidation cancels the shares: its disposal part passes by no transfer instrument, no stamp duty (got %s)" % st)
    # what the structure's own later flows break is a fact, not a plan item: the transferee sold out of the group within
    # 2 years (HK SDO s45(5A)); the asset disposed of within 2 years (SG 2014 Rules r 7(1)(b)); the transferor's shares
    # in the transferee sold within 12 months / 3 years (59号 §5(5), §7(1))
    g = HOLDING.build(ev, {HOLD: SG, "financing": "EQUITY", "payment": False, "exit_route": "INDIRECT"}, reorg_case(HK, CN, reorg_facts=met))
    fx = facts_for(g, next(f for f in g.flows if f.id == "reorg"))
    check(fx.get(("flow", "clawback_event_within_2y")) is True and fx.get(("flow", "reorg_commitment_3y")) is False
          and fx.get(("flow", "reorg_shares_kept_12m")) is False,
          "own flows: ULT sells the new HOLD 9 months after the step — the HK s45 relief is withdrawn, the 59号 commitments are broken")
    hk_ = lambda lb: round(sum(4000.0 * it.effective / 100.0 for it in lb.items if it.jur == HK and it.levy == "stamp"), 2)
    check(hk_(run(g, FLOOR, EX_ANTE)[2]["reorg"]) == 8.0, "own flows: so the step's HK stamp duty stands even at the floor: 0.1%% x 2 x 4000")
    g = HOLDING.build(ev, {HOLD: HK, "financing": "EQUITY", "payment": False, "exit_route": "DIRECT"}, reorg_case(SG, CN, reorg_facts=met))
    fx = facts_for(g, next(f for f in g.flows if f.id == "reorg"))
    sg_ = lambda lb: round(sum(4000.0 * it.effective / 100.0 for it in lb.items if it.jur == SG and it.levy == "stamp"), 2)
    check(fx.get(("flow", "asset_disposed_within_2y")) is True and fx.get(("flow", "clawback_event_within_2y")) is None
          and sg_(run(g, FLOOR, EX_ANTE)[2]["reorg"]) == 8.0,
          "own flows: HOLD sells the SG shares it took over within 2 years — the SG relief is withdrawn (r 7(1)(b)): 0.2%% x 4000 at the floor")
    # ---- 口径 D22: the IP transfer step — the candidate's owner buys the IP from the present one; every jurisdiction's tax
    from copy import deepcopy
    _, cC, eC = SCENARIOS["C"]
    gs = {x: IP.build(eC, {IPCO: x, "payment": False}, cC) for x in (None, HK, SG, CN)}
    tx = {x: [(f.payer, f.payee, f.amount) for f in g.flows if f.id == "iptx"] for x, g in gs.items()}
    check(tx[HK] == [] and tx[None] == [(OP, IPCO, 400.0)] and tx[SG] == [(IPCO + NEW, IPCO, 400.0)]
          and tx[CN] == [(IPCO + NEW, IPCO, 400.0)] and all(not g.unmodelled for g in gs.values()),
          "IP transfer: the candidate's owner buys the IP from the present one at the stated value; no step unmodelled (got %s)" % tx)

    def ctx_t(t):
        return lambda facts: CaseCtx(facts, t, EX_ANTE, ADJUSTABLE)

    def tax(lb, jur, levy="income", who=None):
        return round(sum(lb.flow.amount * it.effective / 100.0 for it in lb.items if it.jur == jur and it.levy == levy
                         and (who is None or (lb.flow.payer if it.borne_by == "payer" else lb.flow.payee) == who)), 2)

    def iptx(g, bound, t=None):
        return engine(g, ctx_t(t or {}), bound)[2]["iptx"]

    lo, hi = iptx(gs[None], FLOOR), iptx(gs[None], CEILING)
    check(tax(lo, CN, who=IPCO) == 0.0 and tax(hi, CN, who=IPCO) == 30.0,
          "IP transfer: a non-resident's gain — Mainland source the authority's judgement (实施条例 第七条): 0 .. 10%% x (400 - 100) = 30 "
          "(got %s, %s)" % (tax(lo, CN, who=IPCO), tax(hi, CN, who=IPCO)))
    src_cn = {Need(DISCRETION, "flow.ip_transfer_gain_sourced_in_cn"): True, Need(DISCRETION, "payee.ppt"): False}
    c2 = deepcopy(cC)
    c2.roles[IPCO].attrs["fixed_place_in_cn"] = False
    c3 = deepcopy(c2)
    c3.roles[IPCO].attrs["residence_cert"] = False
    t2 = tax(iptx(IP.build(eC, {IPCO: None, "payment": False}, c2), CEILING, src_cn), CN, who=IPCO)
    t3 = tax(iptx(IP.build(eC, {IPCO: None, "payment": False}, c3), CEILING, src_cn), CN, who=IPCO)
    check(t2 == 0.0 and t3 == 30.0, "IP transfer: judged Mainland-sourced, the Arrangement still leaves the gain to Hong Kong (Art 13(7)) — "
          "not without the residence certificate (got %s, %s)" % (t2, t3))
    off = {Need(DISCRETION, "flow.ip_gain_sourced_in_hk"): False, Need(DISCRETION, "flow.ip_transfer_gain_sourced_in_cn"): False}
    hk_f = tax(iptx(gs[None], CEILING, off), HK)
    check(abs(hk_f - 17.325) < 0.01, "IP transfer: an offshore gain received in Hong Kong is an IP disposal gain (s15I) less the R&D fraction "
          "65%% (Sch 17FC): 16.5%% x 300 x 35%% = 17.33 (got %s)" % hk_f)
    c4 = deepcopy(cC)
    c4.flows["iptx"]["ip_allowances_claimed"] = 100.0
    on_cap = {Need(DISCRETION, "flow.ip_gain_sourced_in_hk"): True, Need(DISCRETION, "flow.ip_held_as_capital_asset"): True,
              Need(DISCRETION, "flow.ip_transfer_gain_sourced_in_cn"): False}
    hk_r = tax(iptx(IP.build(eC, {IPCO: None, "payment": False}, c4), CEILING, on_cap), HK)
    check(hk_r == 16.5, "IP transfer: a capital gain arising in Hong Kong — only the deductions allowed come back (s16E(3)): "
          "16.5%% x min(400 - 100, 100) = 16.5 (got %s)" % hk_r)
    cR = Case(roles={OP: RoleFacts(CN, {"vat_general_taxpayer": True}), ULT: RoleFacts(SG, {"managed_from": SG})},
              holds={(ULT, OP): HoldEdge(ULT, OP, 100.0, date(2020, 1, 1), 3000.0)},
              flows={"roy": {"is_equipment_lease": False, "is_aircraft_or_ship_lease": False, "receipt_kind": "NONE"},
                     "iptx": {"amount": 8_000_000.0, "ip_kind": "PATENT", "cost_basis": 1_000_000.0, "cny_rate": 1.0,
                              "price_includes_vat": False, "instrument_used_in_cn": True}})
    gR = IP.build(eC, {IPCO: HK, "payment": False}, cR)
    rl, rh = tax(iptx(gR, FLOOR), CN, who=OP), tax(iptx(gR, CEILING), CN, who=OP)
    check(rl == 250000.0 and rh == 1750000.0, "IP transfer: a resident's technology transfer — 5 million yuan exempt, the rest halved "
          "(第九十条): 25%% x (7m - 5m) x 50%% = 250,000; sisters both wholly held by ULT (111号 第四条 silent): up to 25%% x 7m (got %s, %s)" % (rl, rh))
    cT = deepcopy(cR)
    cT.flows["iptx"]["ip_kind"] = "TRADEMARK"
    lT = iptx(IP.build(eC, {IPCO: HK, "payment": False}, cT), FLOOR)
    check(tax(lT, CN, who=OP) == 1750000.0 and tax(lT, CN, "vat", who=OP) == 480000.0,
          "IP transfer: a trademark is no technology — the whole gain at 25%%, and the sale bears 6%% VAT (销售方为境内单位) the foreign "
          "buyer cannot credit: 480,000 (got %s, %s)" % (tax(lT, CN, who=OP), tax(lT, CN, "vat", who=OP)))
    gx = deepcopy(gR)
    sell, buy = [f for f in gx.flows if f.id == "iptx"][0], None
    held = facts_for(Graph(gx.entities, gx.holds + [HoldEdge(IPCO, OP, 100.0, date(2020, 1, 1), 1.0)], gx.flows), sell)
    check(held[("flow", "ip_parties_100pct_held")] is True and facts_for(gR, sell)[("flow", "ip_parties_100pct_sisters")] is True,
          "IP transfer: one company wholly holding the other is derived (111号 第四条: no reduction); wholly held sisters are flagged for the judgement")
    c5 = deepcopy(cC)
    c5.flows["iptx"]["ip_kind"] = "TRADEMARK"
    c5.roles[OP].attrs["vat_general_taxpayer"] = True
    g5 = IP.build(eC, {IPCO: None, "payment": False}, c5)
    lo5, hi5 = iptx(g5, FLOOR), iptx(g5, CEILING)
    check(tax(lo5, CN, "vat") == 0.0 and tax(lo5, CN, "vat", who=IPCO) == 24.0 and tax(hi5, CN, "vat") == 24.0,
          "IP transfer: a foreign seller's IP is consumed in the Mainland (实施条例 第四条): 6%% x 400 = 24 withheld, credited by OP holding "
          "the contract, payment proof and invoice (公告2026年第13号) — not at the ceiling (got %s, %s)" % (tax(lo5, CN, "vat"), tax(hi5, CN, "vat")))
    c6 = deepcopy(cC)
    c6.flows["iptx"]["instrument_used_in_cn"] = False
    s1, s0 = tax(iptx(gs[SG], FLOOR), CN, "stamp"), tax(iptx(IP.build(eC, {IPCO: SG, "payment": False}, c6), CEILING), CN, "stamp")
    check(s1 == 0.24 and s0 == 0.0, "IP transfer: Hong Kong to Singapore — Mainland stamp duty 0.03%% from each party only if the instrument "
          "is used in the Mainland (印花税法 第一条) (got %s, %s)" % (s1, s0))
    w1 = tax(iptx(gs[SG], FLOOR), SG)
    w0 = tax(iptx(IP.build(replace(eC, on=date(2028, 1, 31)), {IPCO: SG, "payment": False}, cC), FLOOR), SG)
    check(w1 == -13.6 and w0 == 0.0, "IP transfer: the Singapore buyer writes the price down over 5 years (s19B(1AA)): 17%% x 400 / 5 = 13.6 "
          "in the year; none for rights acquired after the basis period for YA 2028 (s19B(10)(aa)) (got %s, %s)" % (w1, w0))
    c7 = deepcopy(cC)
    c7.flows["iptx"]["ip_useful_life_years"] = 5
    am = tax(iptx(IP.build(replace(eC, years=2), {IPCO: None, "payment": False}, c7), FLOOR), CN, who=OP)
    check(am == -40.0, "IP transfer: OP amortises the price over the agreed 5-year life (实施条例 第六十七条): 25%% x 400 x 2/5 = 40 in the "
          "two modelled years (got %s)" % am)
    from .engine import cfc_flows, p2_income
    from .params import Params
    cU = deepcopy(cC)
    cU.roles[ULT] = RoleFacts(CN, {"managed_from": CN})
    cU.roles[IPCO].attrs.update(after_tax_profit=0.0, globe_income=1000.0)
    gU = IP.build(eC, {IPCO: None, "payment": False}, cU)
    labU = engine(gU, ctx_t({}), FLOOR)[2]
    inc = [f.amount for f in cfc_flows(gU, Params(), {}, labU) if f.payer == IPCO]
    check(inc == [300.0] and p2_income(gU, gU.entities[IPCO], 2026, Params()) == 1300.0,
          "IP transfer: the seller keeps the proceeds — its book gain 400 - 100 joins the profit a Mainland parent's CFC rules "
          "see (after the tax on it, nil at the floor) and its GloBE income of the year (got %s)" % inc)
    from .engine import step_income
    cN = deepcopy(cU)
    del cN.flows["iptx"]["amount"]
    gN = IP.build(eC, {IPCO: None, "payment": False}, cN)
    check(step_income(gN, IPCO) == (0.0, ["flow:iptx.amount"]) and p2_income(gN, gN.entities[IPCO], 2026, Params()) is None,
          "IP transfer: no price stated — no gain is counted (never 0 less the carrying amount); the price is asked (got %s)"
          % (step_income(gN, IPCO),))
    # 口径 D27: the buyer's book amortisation (40 a year, stated) in its GloBE income; the Singapore allowance in covered
    # taxes with the deferred tax recast at 15% (Art 4.4.1): -17% x 80 + 15% x (80 - 40) = -7.6
    from .engine import designed_globe_income, p2_step_tax
    labS = engine(gs[SG], ctx_t({}), FLOOR)[2]
    gi, st = designed_globe_income(gs[SG], IPCO + NEW, 2026, Params()), round(p2_step_tax(labS, IPCO + NEW, 2026, Params()), 2)
    c8 = deepcopy(cC)
    del c8.flows["iptx"]["ip_book_amortization"]
    g8 = IP.build(eC, {IPCO: SG, "payment": False}, c8)
    gv = designed_globe_income(gs[SG], IPCO + NEW, 2026, Params(), labS)
    check(gv == 431.7, "accounts (口径 D29): the new IP company's GloBE income leaves out the VAT taken from its VAT-inclusive "
          "royalty, 460 - 500 x 6/106 = 431.70 (got %s)" % gv)
    check(gi == 460.0 and st == -7.6 and designed_globe_income(g8, IPCO + NEW, 2026, Params()) is None,
          "IP transfer (口径 D27): the new IP company's GloBE income is its royalty less its book amortisation, 500 - 40 = 460; "
          "its 5-year allowance with deferred tax recast at 15%%: -7.6 in covered taxes; no amortisation stated: asked "
          "(got %s, %s)" % (gi, st))
    fr = facts_for(gs[SG], next(f for f in gs[SG].flows if f.id == "roy"))
    check(fr[("flow", "qualifying_rd_expenditure")] == 0.0 and fr[("flow", "non_qualifying_expenditure")] == 400.0,
          "IP transfer: a new IP company bought its IP — its R&D fraction is nil (Sch 17FC s5(3)(c)), never asked")

    # ---- 口径 D28: OP and a new IP company both held wholly by a Mainland parent — the IP may move at book value (109号
    #      第三条): no gain for OP, the buyer amortises OP's tax basis; if the treatment fails, a deemed sale at fair value
    cB = Case(roles={OP: RoleFacts(CN, {"vat_general_taxpayer": True}), ULT: RoleFacts(CN, {"managed_from": CN})},
              holds={(ULT, OP): HoldEdge(ULT, OP, 100.0, date(2020, 1, 1), 3000.0)},
              flows={"roy": {"is_equipment_lease": False, "is_aircraft_or_ship_lease": False, "receipt_kind": "NONE"},
                     "iptx": {"amount": 400.0, "ip_kind": "TRADEMARK", "cost_basis": 100.0, "ip_book_value": 100.0,
                              "ip_book_amortization": 40.0, "instrument_used_in_cn": True, "ip_useful_life_years": 10,
                              "price_includes_vat": False}})
    book, book_hk = {IPCO: CN, "payment": False, "ip_transfer": "BOOK"}, {IPCO: HK, "payment": False, "ip_transfer": "BOOK"}
    check(not IP.infeasible(eC, book, cB) and IP.infeasible(eC, book_hk, cB) and IP.infeasible(eC, book, cC),
          "book value (口径 D28): offered only between Mainland companies wholly held by the same Mainland parent")
    gB, gM = IP.build(eC, book, cB), IP.build(eC, dict(book, ip_transfer="MARKET"), cB)
    cI = deepcopy(cB)
    cI.flows["iptx"]["price_includes_vat"] = True
    mi = iptx(IP.build(eC, dict(book, ip_transfer="MARKET"), cI), CEILING)
    check(tax(mi, CN, who=OP) == 69.34 and tax(mi, CN, "vat", who=OP) == 22.64,
          "IP sale (口径 D29): a VAT-inclusive 400 — OP's VAT 400 x 6/106 = 22.64, and its gain is the net 377.36 less the "
          "basis 100: 25%% x 277.36 = 69.34 (got %s, %s)" % (tax(mi, CN, who=OP), tax(mi, CN, "vat", who=OP)))
    bl, bh, ml = iptx(gB, FLOOR), iptx(gB, CEILING), iptx(gM, FLOOR)
    got = (tax(bl, CN, who=OP), tax(bl, CN, who=IPCO), tax(bh, CN, who=OP), tax(bh, CN, who=IPCO), tax(ml, CN, who=OP), tax(bl, CN, "vat"))
    check(got == (0.0, -2.5, 75.0, -10.0, 75.0, 0.0),
          "book value (口径 D28): no gain for OP and the new company amortises OP's basis, 25%% x 100 / 10 = 2.5; if the "
          "treatment fails, 25%% x 300 and 25%% x 400 / 10 (a deemed sale, 公告2015年第40号 第八条) as at market value; the "
          "deemed sale's 6%% VAT on 400 is credited by the buyer (got %s)" % (got,))

    # ---- 口径 D24: a Singapore IP company's royalty from the Mainland — judged derived from Singapore, charged whether remitted
    #      or not (s10(1)), the Agreement's 10% credited; judged foreign-sourced and not remitted, nothing
    sg_roy = lambda t, b: tax(engine(gs[SG], ctx_t(t), b)[2]["roy"], SG)
    yes_sg = {Need(DISCRETION, "payee.income_sourced_in_sg"): True}
    no_sg = {Need(DISCRETION, "payee.income_sourced_in_sg"): False}
    r1, r0 = sg_roy(yes_sg, FLOOR), sg_roy(no_sg, FLOOR)
    check(r1 == 37.83 and r0 == 0.0, "SG source (口径 D24): a royalty derived from a licensing business run in Singapore is charged "
          "on accrual: 17%% x 500 less the Mainland's 10%% of the VAT-net 500 / 1.06 = 37.83; foreign-sourced and kept abroad: 0 "
          "(got %s, %s)" % (r1, r0))
    dl = [d for d in engine(gs[SG], ctx_t({}), CEILING)[2]["iptx"].deadlines]
    check(not any(k == "filing" for k in dl), "SG s45: an IP bought outright is not withheld, so no s45 filing clock (got %s)" % dl)

    # ---- 口径 D25: interest is a loan service — 6% withheld from a foreign lender, charged to a Mainland lender, never credited;
    #      口径 D26: the non-resident's withholding base (and the treaty cap's) is the interest net of the VAT
    def int_items(on, lender_loc, **attrs):
        g = Graph({"OP": Entity("OP", CN, attrs={"vat_general_taxpayer": True}), "ULT": Entity("ULT", SG, attrs={"managed_from": SG}),
                   "L": Entity("L", lender_loc, attrs={"managed_from": lender_loc, "residence_cert": True, "bo_safe_harbour": True,
                                                        "vat_general_taxpayer": True})},
                  [HoldEdge("ULT", "OP", 100.0, date(2020, 1, 1), 1.0), HoldEdge("ULT", "L", 100.0, date(2020, 1, 1), 1.0)],
                  [FlowEdge("i", "OP", "L", INTEREST, 1060.0, on, attrs=dict({"interest_rate": 5.0, "benchmark_rate": 5.0,
                                                                              "receipt_kind": "NONE"}, **attrs))])
        lb = engine(g, ctx_t({Need(DISCRETION, "payee.no_adverse_bo_factors"): True, Need(DISCRETION, "payee.ppt"): False}), CEILING)[2]["i"]
        return tax(lb, CN, "vat"), tax(lb, CN, who="L")
    v_ex, v_in, v_cn = int_items(ON, SG, price_includes_vat=False), int_items(ON, SG, price_includes_vat=True), \
        int_items(ON, CN, price_includes_vat=False)
    v_un = int_items(ON, SG, price_includes_vat=False, unified_borrowing_relending=True)
    check(v_ex == (63.6, 106.0) and v_in == (60.0, 100.0),
          "interest VAT (口径 D25, D26): a Singapore lender's 1060 — 6%% withheld = 63.6 and never credited, 10%% withholding on 1060; "
          "a VAT-inclusive price: 60 and the withholding on the net 1000 = 100 (got %s, %s)" % (v_ex, v_in))
    check(v_cn[0] == 63.6 and v_un[0] == 0.0,
          "interest VAT: a Mainland lender pays 6%% on it, no credit for the borrower (63.6); 统借统还 on-lending is exempt "
          "(got %s, %s)" % (v_cn, v_un))
    # 口径 D29: a Mainland lender's interest at a VAT-inclusive price — 6/106 VAT, and its income is the price net of it:
    # 25% x 1000 = 250 (the borrower's VAT is not creditable: its deduction stays on the 1060 it pays)
    v_ci = int_items(ON, CN, price_includes_vat=True)
    check(v_ci == (60.0, 250.0), "resident's interest (口径 D29): VAT-inclusive 1060 — VAT 60 and 25%% on the net 1000 = 250 "
          "(got %s)" % (v_ci,))

    # 口径 D30: in 2025 the Mainland VAT is not the VAT Law's, and the library keeps current law only — the levy is outside
    # it (never nil), and so is the withholding base that turns on it (公告2013年第9号); a group company bears both here, so
    # the candidate is no plan; with a lender outside the group they are its own, a note
    def int_label(lender_in_group):
        g = Graph({"OP": Entity("OP", CN), "ULT": Entity("ULT", SG, attrs={"managed_from": SG}),
                   "L": Entity("L", SG, attrs={"managed_from": SG, "residence_cert": True, "bo_safe_harbour": True})},
                  [HoldEdge("ULT", "OP", 100.0, date(2020, 1, 1), 1.0)]
                  + ([HoldEdge("ULT", "L", 100.0, date(2020, 1, 1), 1.0)] if lender_in_group else []),
                  [FlowEdge("i", "OP", "L", INTEREST, 1060.0, date(2025, 6, 30),
                            attrs={"interest_rate": 5.0, "benchmark_rate": 5.0, "receipt_kind": "NONE"})])
        labels = engine(g, ctx_t({Need(DISCRETION, "payee.no_adverse_bo_factors"): True, Need(DISCRETION, "payee.ppt"): False}),
                        CEILING)[2]
        return g, labels

    from types import SimpleNamespace
    from .engine import outside_steps
    g_in, lab_in = int_label(True)
    g_out, lab_out = int_label(False)
    st_in, st_out = outside_steps(SimpleNamespace(L_hi=lab_in), g_in), outside_steps(SimpleNamespace(L_hi=lab_out), g_out)
    check(tax(lab_in["i"], CN, "vat") == 0.0 and sorted(lab_in["i"].outside) == [(CN, "income", "L"), (CN, "vat", "L")]
          and sorted(x[5] for x in st_in[0]) == sorted(["所得税", "增值税"]) and st_in[0][0][3:5] == ("增值税法", "2026-01-01")
          and not st_in[1] and not st_out[0] and len(st_out[1]) == 2,
          "before the VAT Law (口径 D30): no VAT computed and none assumed — the VAT and the withholding base that turns on it "
          "are outside the library; borne in the group: no plan; borne by an outside lender: a note (got %s, %s, %s)"
          % (sorted(lab_in["i"].outside), st_in, st_out))

    # 口径 D31: a Hong Kong company the effective-management variant makes a Mainland resident is still established in
    # Hong Kong (82号 第二条 is about income tax) — the interest it receives from its Hong Kong subsidiary bears the
    # Mainland's income tax but no Mainland VAT; an IP it sells to that subsidiary, no Mainland VAT or stamp duty
    from .engine import residence_graph
    gP = Graph({"ULT": Entity("ULT", CN), "H": Entity("H", HK, attrs={"managed_from": CN}), "O": Entity("O", HK)},
               [HoldEdge("ULT", "H", 100.0, date(2020, 1, 1), 1.0), HoldEdge("H", "O", 100.0, date(2020, 1, 1), 1.0)],
               [FlowEdge("i", "O", "H", INTEREST, 1000.0, ON, attrs={"interest_rate": 5.0, "benchmark_rate": 5.0,
                                                                    "receipt_kind": "NONE", "price_includes_vat": False}),
                FlowEdge("x", "O", "H", "IP_TRANSFER", 400.0, ON, attrs={"ip_kind": "TRADEMARK", "cost_basis": 100.0,
                                                                       "price_includes_vat": False, "instrument_used_in_cn": False})])
    labP = engine(residence_graph(gP, {"H"}), ctx_t({}), CEILING)[2]
    levies = [(fid, it.levy, it.cites[0]) for fid, lb in labP.items() for it in lb.items
              if it.jur == CN and it.levy != "income" and abs(it.effective) > 1e-12]
    inc = tax(labP["i"], CN, who="H")
    check(levies == [] and inc == 250.0,
          "effective management (口径 D31): a Hong Kong company resident in the Mainland by its management pays the "
          "Mainland's 25%% on its interest (250) but no Mainland VAT, and its IP sale to a Hong Kong company no VAT or stamp "
          "duty — it is established in Hong Kong (got %s, %s)" % (levies, inc))

    # the flow cache keys on the seats too: a share transfer whose target the management test moves to the Mainland is
    # stamped where the target is established — a Hong Kong target's evaluation must never answer for a Singapore one
    from . import engine as E

    def st_levies(tloc):
        g = residence_graph(Graph({"ULT": Entity("ULT", CN), "B": Entity("B", CN), "T": Entity("T", tloc, attrs={"managed_from": CN})},
                                  [HoldEdge("ULT", "T", 100.0, date(2020, 1, 1), 400.0)],
                                  [FlowEdge("s", "B", "ULT", SHARE_TRANSFER, 1000.0, ON, target="T", attrs={"cost_basis": 400.0})]),
                            {"T"})
        return sorted((it.jur, it.cites[0]) for it in engine(g, ctx_t({}), CEILING)[2]["s"].items if it.levy == "stamp")

    E._FLOW_CACHE.clear()
    hk_first, sg_after = st_levies(HK), st_levies(SG)
    E._FLOW_CACHE.clear()
    sg_fresh = st_levies(SG)
    check(sg_after == sg_fresh and any(j == HK for j, _ in hk_first) and any(j == SG for j, _ in sg_fresh)
          and not any(j == HK for j, _ in sg_fresh),
          "flow cache (口径 D31): the same share transfer of a Mainland-managed target — Hong Kong stamp duty for a Hong Kong "
          "target, Singapore's for a Singapore one, whatever the process evaluated before (got %s, %s, %s)"
          % (hk_first, sg_after, sg_fresh))
    roy_net = tax(engine(IP.build(eC, {IPCO: HK, "payment": False}, cC), ctx_t({}), FLOOR)[2]["roy"], CN, who=IPCO)
    check(roy_net == 33.02, "royalty (口径 D26): the Arrangement's 7%% applies to the royalty net of the VAT, 500 / 1.06: 33.02 "
          "(got %s)" % roy_net)

    # ---- 口径 D23: the VAT Law from 2026-01-01 — 6% of the sales amount; before it outside the library (口径 D30)
    def roy_vat(on, **attrs):
        g = Graph({"OP": Entity("OP", CN, attrs={"vat_general_taxpayer": True}), "ULT": Entity("ULT", SG, attrs={"managed_from": SG}),
                   "S": Entity("S", SG, attrs={"managed_from": SG, "residence_cert": True, "bo_safe_harbour": True})},
                  [HoldEdge("ULT", "OP", 100.0, date(2020, 1, 1), 1.0), HoldEdge("ULT", "S", 100.0, date(2020, 1, 1), 1.0)],
                  [FlowEdge("r", "OP", "S", ROYALTY, 1060.0, on, attrs=dict({"is_equipment_lease": False, "is_aircraft_or_ship_lease": False,
                                                                           "receipt_kind": "NONE"}, **attrs))])
        lb = run(g, CEILING, EX_ANTE)[2]["r"]
        return [(it.cites[0], round(1060.0 * it.effective / 100.0, 2)) for it in lb.items if it.levy == "vat" and it.borne_by == "payee"]
    v0, v1, v2 = roy_vat(date(2025, 12, 31)), roy_vat(date(2026, 1, 1), price_includes_vat=False), roy_vat(date(2026, 1, 1), price_includes_vat=True)
    check(v0 == [] and v1 == [("cn.vat.law.royalty", 63.6)] and v2 == [("cn.vat.law.royalty", 60.0)],
          "VAT Law: on 2025-12-31 no VAT is computed (口径 D30: outside the library); from 2026-01-01 6%% of the sales amount — "
          "63.6 on a price without VAT, 60 on one with it (实施条例 第十六条) (got %s, %s, %s)" % (v0, v1, v2))
    _, cD, eD = SCENARIOS["D"]
    g = SERVICES.build(eD, {SERVICER: HK, "payment": False}, cD)
    check(SERVICER + NEW in g.entities and SERVICER not in g.entities and g.entities[SERVICER + NEW].attrs.get("created_by_plan")
          and not g.unmodelled, "services elsewhere: a new servicer takes the service over, no asset moves, no step")

    # ---- 口径 D21: the case's flow facts describe the parties of its own structure; a company the plan creates gets its
    #      side from the law (headline rate), from its design (not listed, ordinary shares) or from answers of its own
    from .planner import Answers, apply_data
    from .regions import absolute_key
    _, cA, eA = SCENARIOS["A"]
    rel = {x: HOLDING.build(eA, dict(base, **{HOLD: x}), cA) for x in (HK, SG, CN)}
    up2 = {x: next(f for f in g.flows if f.id == "up2") for x, g in rel.items()}
    check(up2[HK].attrs.get("fact_key") is None and up2[HK].attrs.get("foreign_taxed") is True
          and up2[SG].attrs.get("fact_key") == "up2~HOLD_NEW-SG" and "foreign_taxed" not in up2[SG].attrs
          and up2[SG].attrs.get("receipt_kind") == "REMITTED",
          "new company: the client's HOLD keeps its stated up2 facts; HOLD_NEW's side of up2 is not carried (ULT's side is)")
    fx = facts_for(rel[SG], up2[SG])
    check(fx[("flow", "foreign_headline_rate")] == 17.0 and fx[("flow", "listed_market_trade")] is False
          and fx[("flow", "deductible_at_payer")] is False and fx[("_meta", "flow")] == "up2~HOLD_NEW-SG",
          "new company: Singapore's statutory 17% is its headline rate; not listed, its dividend not deductible (design)")
    check(absolute_key("flow.foreign_taxed", up2[SG]) == "flow:up2~HOLD_NEW-SG.foreign_taxed"
          and absolute_key("flow.foreign_taxed", up2[HK]) == "flow:up2.foreign_taxed",
          "new company: a question about its side has its own address")
    ans = Answers()
    ans.data["flow:up2~HOLD_NEW-SG.foreign_taxed"] = False
    c3 = apply_data(cA, ans)
    got = {x: next(f for f in HOLDING.build(eA, dict(base, **{HOLD: x}), c3).flows if f.id == "up2").attrs.get("foreign_taxed")
           for x in (HK, SG, CN)}
    check(got == {HK: True, SG: False, CN: None},
          "new company: an answer about HOLD_NEW in Singapore reaches only that candidate, never the client's own HOLD (got %s)" % got)

    # ---- domestic flows are charged and deducted by the statutes: a 15% high-tech payer and a 25% recipient leave 10% in the
    #      group; a dividend between residents is exempt (EIT art 26(2))
    g = Graph({"OP": Entity("OP", CN, attrs={"cit_rate": 15.0}), "FIN": Entity("FIN", CN), "ULT": Entity("ULT", SG, attrs={"managed_from": SG})},
              [HoldEdge("ULT", "OP", 100.0, date(2020, 1, 1), 1.0), HoldEdge("ULT", "FIN", 100.0, date(2020, 1, 1), 1.0)],
              [FlowEdge("i", "OP", "FIN", INTEREST, 1000.0, ON, attrs={"interest_rate": 5.0, "benchmark_rate": 5.0}),
               FlowEdge("d", "OP", "FIN", DIVIDEND, 1000.0, ON, attrs={"listed_market_trade": False})])
    lo = run(g, FLOOR, EX_ANTE)[2]
    check(abs(lo["i"].tax - 100.0) < 1e-6, "domestic interest: 25%% charged on the recipient, 15%% deducted by the high-tech payer = 100 (got %.2f)" % lo["i"].tax)
    check(lo["d"].tax == 0.0, "domestic dividend between residents: exempt (got %.2f)" % lo["d"].tax)
    # the GST reverse charge costs the unrecoverable share: 60% recoverable -> 9% x 40% x 1000 = 36
    g = Graph({"P": Entity("P", SG, attrs={"managed_from": SG, "gst_input_fully_recoverable": False, "gst_recovery_ratio": 60.0}),
               "U": Entity("U", SG, attrs={"managed_from": SG}), "V": Entity("V", HK, attrs={"managed_from": HK, "residence_cert": True, "fixed_place_in_sg": False})},
              [HoldEdge("U", "P", 100.0, date(2020, 1, 1), 1.0), HoldEdge("U", "V", 100.0, date(2020, 1, 1), 1.0)],
              [FlowEdge("f", "P", "V", SERVICE_FEE, 1000.0, ON, attrs={"service_location": HK, "service_days_12m": 0, "profit_margin": 20})])
    lb = run(g, FLOOR)[2]["f"]
    gst = [round(1000.0 * it.effective / 100.0, 2) for it in lb.items if it.levy == "vat" and it.borne_by == "payer"]
    check(gst == [36.0], "SG GST: 9%% x (1 - 60%%) x 1000 = 36 unrecoverable (got %s)" % gst)

    # ---- recurring years: a two-year event repeats the recurring flows, the exit once
    g = HOLDING.build(replace(EVENT_A, years=2), BASE_A, CASE_A)
    check(sorted(f.id for f in g.flows) == ["exit", "up1", "up1@2027", "up2", "up2@2027"], "years: recurring flows repeat with the year in their id (%s)" % sorted(f.id for f in g.flows))
    b = bounds(g, lambda facts: CaseCtx(facts, {}, EX_ANTE, ADJUSTABLE))
    check(b.lo <= b.hi, "years: two-year bounds hold (%.2f, %.2f)" % (b.lo, b.hi))

    out.write("%d checks, %d failures\n" % (n, bad))
    out.flush()
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
