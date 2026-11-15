#!/usr/bin/env python
"""Savings map (2026-11-12, optimization spec §4.7a): for every pair of jurisdictions in the search, a company paying a
dividend to a company or an individual that holds it directly, how much a better route saves on standard facts. A screening
table for choosing test cases and for seeing where a rule change moves a conclusion; not advice, and nothing in it is a case.

  python optimization/tools/savings_map.py [--out <file.csv>] [--pairs cn:sg,hk:sg] [--date 2026-04-30]

Standard facts: amount 1,000,000 in the payer's currency, 100% held for 24 months, the payer taxed at its headline rate, a
recipient company with staff, premises and substantive business that passes nothing on, a recipient individual resident with
no other income, the money received where it ends; every judgment point on the favourable side (the ranking side). As-is = the direct hop; best = the lowest
favourable-side tax over the search's frontier (labels, the edge weights before the candidate recomputation, so a figure
is a screening value). One process, one hop cache: the first pair is slow, the rest reuse its evaluations."""
import argparse
import csv
import io
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import optimize as op  # noqa: E402

SUBJECTS = ("company", "individual")


def standard_input(src, dst, subj, date, lib):
    rate = lib.params.get("%s.final.cit_rate" % src)
    payer_facts = {"incorporated_in": src, "managed_in": src, "payer_listed": False}
    payment = {"holding_pct": 100, "holding_months": 24}
    if rate:
        payment["payer_tax_rate"] = float(rate["value"])
        payment["payer_income_taxed"] = True
    if subj == "company":
        payee = {"jur": dst, "subject": "company", "facts": {"incorporated_in": dst, "managed_in": dst, "employees_in_jurisdiction": 5,
                                                             "premises_in_jurisdiction": True, "substantive_business": True,
                                                             "passes_on_within_12m": False, **op.NEW_COMPANY}}
    else:
        payee = {"jur": dst, "subject": "individual", "facts": {"domicile_in": dst, "ordinarily_resides": True, "other_taxable_income": 0}}
    ccy = next((j.get("currency") for j in lib.juris if j["code"] == src), "")
    return {"date": date, "mode": "plan", "amount": 1000000, "currency": ccy, "payer": {"jur": src, "facts": payer_facts},
            "payee": payee, "payment": payment, "destinations": [[dst, subj]], "constraints": {"allow_restructure": True, "receive_at_destination": True}}


def pct(w):
    return None if w is None else round(100 * (1 - math.exp(-w)), 4)


def one(src, dst, subj, date, shared):
    o = op.Optimizer.__new__(op.Optimizer)
    o.__init__(standard_input(src, dst, subj, date, shared["q"].lib))
    o._hop_cache = shared["cache"]
    g = o.build_graph()
    lab, allab = o.labels(g)
    cands = o.paths(lab, allab, g)
    edges = {e["edge_id"]: e for e in g["edges"]}
    c0 = next(c for c in cands if c["as_is"])
    as_is = edges[c0["edges"][0]]["w"]["floor"] if c0["edges"] else None
    best_lid = min(lab["frontier"], key=lambda lid: allab[lid]["w"]["floor"]) if lab["frontier"] else None
    best = next((c for c in cands if c.get("label") == best_lid), None) if best_lid else None
    bw = allab[best_lid]["w"]["floor"] if best_lid else None
    return {"payer": src, "recipient": "%s:%s" % (dst, subj), "as_is_pct": pct(as_is), "best_pct": pct(bw),
            "saving_pct": None if as_is is None or bw is None else round(pct(as_is) - pct(bw), 4),
            "best_route": " > ".join(best["path"]) if best else "", "best_moves": ",".join(best.get("moves") or []) if best else "",
            "best_restructure": ",".join(best.get("restructure") or []) if best else "", "frontier": len(lab["frontier"])}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", help="CSV file (default: stdout)")
    ap.add_argument("--pairs", help="payer:recipient jurisdictions, comma-separated (default: every pair)")
    ap.add_argument("--date", default="2026-04-30")
    a = ap.parse_args()
    q = op.Query(op.RULE, op.DB)
    real_query = op.Query
    op.Query = lambda root, db: q                         # one library and rule set for every pair
    shared = {"q": q, "cache": {}}
    jurs = [j["code"] for j in q.lib.juris]
    pairs = [tuple(p.split(":")) for p in a.pairs.split(",")] if a.pairs else [(s, d) for s in jurs for d in jurs if s != d]
    fields = ["payer", "recipient", "as_is_pct", "best_pct", "saving_pct", "best_route", "best_moves", "best_restructure", "frontier", "seconds", "error"]
    buf = open(a.out, "w", encoding="utf-8", newline="") if a.out else io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    w = csv.DictWriter(buf, fieldnames=fields)
    w.writeheader()
    for src, dst in pairs:
        for subj in SUBJECTS:
            t0 = time.time()
            try:
                row = one(src, dst, subj, a.date, shared)
            except Exception as ex:  # noqa: BLE001
                row = {"payer": src, "recipient": "%s:%s" % (dst, subj), "error": "%s: %s" % (type(ex).__name__, str(ex)[:160])}
            row["seconds"] = round(time.time() - t0, 1)
            w.writerow(row)
            buf.flush()
    op.Query = real_query


if __name__ == "__main__":
    main()
