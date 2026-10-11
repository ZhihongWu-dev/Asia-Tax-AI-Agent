"""Entity-stage checks: Singapore pooled credit (s50C) and the Mainland reinvestment credit (2025–2028).

  python -m tax_graph.check_entity          (conda env "pytorch")

oracle_kind = text_derived (hand-read from the cited provisions). Two graphs, each with two flows into one entity:
the pooled credit must equal min(sum foreign, sum Singapore tax) and exceed the item-by-item credits; the
reinvestment credit must offset the later withholding from the same payer and nothing else.
"""
import io
import sys
from datetime import date

from .data.domain import ADJUSTABLE
from .engine import EX_ANTE, EX_POST, CaseCtx, engine
from .model import CN, DIVIDEND, HK, INTEREST, SG, Entity, FlowEdge, Graph, HoldEdge
from .rules.tri import CEILING, FLOOR

ON = date(2026, 3, 10)


def pooling_graph(elect):
    """U (SG) receives a CN dividend bearing 10% (SG tax 17% minus credit 10 = 7) and a HK dividend bearing nothing
    (SG tax 17%). Pooled: foreign 100 vs SG 340 -> credit 100 either way... so use interest: CN interest 1000 at 10%
    WHT (SG 17%: credit 100) and HK interest 1000 at 0% but SG exempt?  Pooling pays when one flow has excess
    foreign tax: a SG-source-exempt flow cannot carry it. Hence: flow 1 CN dividend 1000, taxed 10%, Singapore exempts
    it under s13(8) only if the Comptroller agrees -> under hi SG 17 - 10; flow 2 CN interest 1000, WHT 10%, SG 17%.
    Item by item each credit is 100; pooled is also 200 -> no gain. The gain appears with a flow whose foreign tax
    exceeds its Singapore tax: a CN royalty on a 60% base?  Keep it simple and verifiable: flow A foreign 15% (SG
    interest from... ) — we instead construct facts directly: flow 1 foreign_tax_rate 25 (stated, ex post), SG 17;
    flow 2 foreign 0, SG 17. Item by item credit = 17 + 0; pooled = min(25, 34) = 25."""
    ents = {"U": Entity("U", SG, attrs={"ftc_pooling_election": elect, "fixed_place_in_sg": False}),
            "A": Entity("A", HK), "B": Entity("B", HK)}
    flows = [FlowEdge("f1", "A", "U", INTEREST, 1000.0, ON, attrs={"receipt_kind": "REMITTED", "foreign_taxed": True,
                                                                   "foreign_headline_rate": 16.5, "foreign_tax_rate": 25.0}),
             FlowEdge("f2", "B", "U", INTEREST, 1000.0, ON, attrs={"receipt_kind": "REMITTED", "foreign_taxed": True,
                                                                   "foreign_headline_rate": 16.5, "foreign_tax_rate": 0.0})]
    return Graph(ents, [], flows)


def reinvest_graph():
    """U (SG, listed) owns OP (CN). A 2026 dividend of 1000 is reinvested (capital increase, encouraged industry,
    planned 72 months): its 10% withholding is deferred and a credit of 5% (treaty dividend rate below 10%) arises;
    a later 2027 interest payment of 1000 from OP bears 10% withholding, offset by the 50 credit."""
    ents = {"OP": Entity("OP", CN, attrs={"related_party_debt_equity_ratio": 1.0}),
            "U": Entity("U", SG, attrs={"residence_cert": True, "bo_safe_harbour": True,
                                        "fixed_place_in_sg": False, "ftc_pooling_election": False})}
    holds = [HoldEdge("U", "OP", 100.0, date(2020, 1, 1), 3000.0)]
    common = {"receipt_kind": "NONE", "foreign_taxed": True, "foreign_headline_rate": 25}
    flows = [FlowEdge("div", "OP", "U", DIVIDEND, 1000.0, date(2026, 6, 30),
                      attrs={**common, "reinvested_in_cn": True, "reinvestment_form": "capital_increase", "direct_payment": True,
                             "reinvestment_from_distributed_profit": True, "investee_encouraged_industry": True,
                             "planned_holding_months": 72}),
             FlowEdge("int", "OP", "U", INTEREST, 1000.0, date(2027, 6, 30), attrs={**common})]
    return Graph(ents, holds, flows)


def main():
    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    out.write("oracle_kind = text_derived\n")
    bad = 0
    checks = []
    ctx = lambda facts: CaseCtx(facts, {}, EX_POST)
    def jur_tax(labels, fid, jur, amount):
        return round(sum(amount * it.effective / 100.0 for it in labels[fid].items
                         if it.jur == jur and it.levy == "income" and not it.deduction and not it.deferred), 2)   # income tax only

    for elect, want in ((False, 170.0), (True, 340.0 - 250.0)):          # item by item: 17 - 17 = 0 on f1, 17 on f2
        total, groups, labels = engine(pooling_graph(elect), ctx, FLOOR)
        sg = jur_tax(labels, "f1", SG, 1000.0) + jur_tax(labels, "f2", SG, 1000.0)
        checks.append(("pooling election %s: Singapore tax after credit" % elect, want, sg))
    g = reinvest_graph()
    for bound, want_div, want_int in ((FLOOR, 0.0, 50.0), (CEILING, 100.0, 100.0)):
        total, groups, labels = engine(g, ctx, bound)
        checks.append(("reinvestment %s: Mainland tax on the dividend (deferred under lo; GAAR denies under hi)" % bound,
                       want_div, jur_tax(labels, "div", CN, 1000.0)))
        checks.append(("reinvestment %s: later interest 10%% withholding less the 5%% credit (GAAR denies under hi)" % bound,
                       want_int, jur_tax(labels, "int", CN, 1000.0)))
    for name, want, got in checks:
        ok = abs((got or 0) - want) < 1e-6
        bad += not ok
        out.write("%-4s %s%s\n" % ("ok" if ok else "DIFF", name, "" if ok else "  expected %s, got %s" % (want, got)))
    out.write("%d checks, %d with differences\n" % (len(checks), bad))
    out.flush()
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
