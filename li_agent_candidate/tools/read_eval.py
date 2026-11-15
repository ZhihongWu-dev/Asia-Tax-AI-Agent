#!/usr/bin/env python
"""Evaluation of the retrieval layer (agent/retrieval_spec.en.md §12).

  python agent/tools/read_eval.py --case CASE-20261102-a032c0 [--sample 120] [--write]

Golden sets from this project's own data, never hand-picked answers:
  L-params     the note of a parameter (else its name in words)          -> the clause the parameter quotes
  L-rules      the note of a rule (else its condition)                   -> any clause the rule cites
  L-decisions  the statement of a decision                               -> the clause it rests on
  L-xlang      the first sentence of a Thai clause                       -> the same provision in English (same_provision edge)
  P-template   plain-language questions generated from the run's records -> the record
  P-hand       the five questions of the 2026-11-03 model comparison     -> the records that answer them
  C-sources    a fact key and its value in words                         -> the document page the source names
Even items are the development set, odd items the test set. A component is adopted when nDCG@10 or Recall@10 rises on the
development set and does not fall on the test set (§12.3); reranking must also stay under 1 s per query. --write records the
result in agent/retrieval_eval.md and the switches in agent/retrieval_settings.json.
"""
import argparse
import csv
import json
import math
import random
import re
import sqlite3
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import read_core as RC  # noqa: E402
from read_index import JUR, PRED  # noqa: E402

csv.field_size_limit(2 ** 31 - 1)
LAW_CONFIGS = [
    ("bm25", {"bm25": True, "dense": False, "balance": False, "graph": False, "rerank": False}),
    ("+dense", {"bm25": True, "dense": True, "balance": False, "graph": False, "rerank": False}),
    ("+balance", {"bm25": True, "dense": True, "balance": True, "graph": False, "rerank": False}),
    ("+graph", {"bm25": True, "dense": True, "balance": True, "graph": True, "rerank": False}),
    ("+rerank", {"bm25": True, "dense": True, "balance": True, "graph": True, "rerank": True}),
    ("-graph+rerank", {"bm25": True, "dense": True, "balance": True, "graph": False, "rerank": True}),
]


def words(code):
    s = re.sub(r"([a-z]{2})-([a-z]{2})\.", lambda m: "%s %s " % (JUR.get(m.group(1), m.group(1)), JUR.get(m.group(2), m.group(2))), code)
    s = re.sub(r"^([a-z]{2})\.", lambda m: JUR.get(m.group(1), m.group(1)) + " ", s)
    return re.sub(r"[._]", " ", s).replace("wht", "withholding").replace("pct", "percent").strip()


def plain_node(n):
    j, _, s = str(n).partition(":")
    return "%s %s" % (JUR.get(j, j).split(" ")[0] if j != "hk" else "Hong Kong", s)


def law_sets(sample, seed=11):
    rnd = random.Random(seed)
    db = PROJECT / "database"
    con = sqlite3.connect(str(db / "index" / "law.sqlite"))
    have = {c for (c,) in con.execute("SELECT cite_id FROM clause")}
    sets = {}
    rows = []
    for p in csv.DictReader(open(db / "param.csv", encoding="utf-8-sig")):
        if p.get("cite_id") in have:
            q = (p.get("note") or "").strip() or words(p["param_id"])
            rows.append({"q": q[:300], "gold": {p["cite_id"]}, "filters": {}})
    sets["L-params"] = rnd.sample(rows, min(sample, len(rows)))
    rows = []
    for r in csv.DictReader(open(PROJECT / "rule" / "rule.csv", encoding="utf-8-sig")):
        gold = {c for c in r.get("cite_ids", "").split(";") if c in have}
        if gold:
            rows.append({"q": ((r.get("note") or "").strip() or r["condition"])[:300], "gold": gold, "filters": {}})
    sets["L-rules"] = rnd.sample(rows, min(sample, len(rows)))
    rows = [{"q": d["statement"][:300], "gold": {d["cite_id"]}, "filters": {}} for d in csv.DictReader(open(db / "decision.csv", encoding="utf-8-sig"))
            if d.get("cite_id") in have and d.get("statement")]
    sets["L-decisions"] = rows
    rows = []
    for a, b in con.execute("SELECT src, dst FROM edge WHERE kind = 'same_provision'"):
        la = con.execute("SELECT lang, text FROM clause WHERE cite_id = ?", (a,)).fetchone()
        lb = con.execute("SELECT lang, text FROM clause WHERE cite_id = ?", (b,)).fetchone()
        if la and lb and la[0] != lb[0] and len(la[1]) > 60:
            src, gold = (a, b) if la[0] != "en" else (b, a)
            text = con.execute("SELECT text FROM clause WHERE cite_id = ?", (src,)).fetchone()[0]
            rows.append({"q": re.sub(r"\s+", " ", text)[:200], "gold": {gold}, "filters": {"lang": "en"}})
    sets["L-xlang"] = rnd.sample(rows, min(sample // 2, len(rows)))
    return sets


def product_sets(reader, case_id):
    rnd = random.Random(5)
    run = reader.current(case_id)[1]
    con, e = reader.products(case_id, run)
    if e:
        raise SystemExit(e)
    R = lambda t, k: "%s:%s:%s" % (run, t, k)
    rows = []
    for r in con.execute("SELECT key, full FROM record WHERE type = 'structure'"):
        f = json.loads(r["full"])
        c = f["path"]
        path = " to ".join(plain_node(n) for n in c["path"])
        moves = " with a wait of twelve months" if c.get("moves") else ""
        restr = " after a share transfer" if c.get("restructure") else " without restructuring"
        rows.append({"q": "tax of the route %s%s%s" % (path, restr, moves), "gold": {R("structure", r["key"])}})
        fav = ((f.get("brief") or {}).get("all_favourable") or {}).get("branch_id")
        if fav:
            rows.append({"q": "tax on %s%s if every point is answered in the group's favour" % (path, restr), "gold": {R("branch", fav), R("structure", r["key"])}})
    for r in con.execute("SELECT key, full FROM record WHERE type = 'point'"):
        jp = json.loads(r["full"])
        pred, _, jur = jp["key"].partition("@")
        rows.append({"q": "which structure comes first if %s in %s is answered against the group for the %s" % (
            PRED.get(pred, pred), JUR.get(jur, jur).split(" ")[0], plain_node(jp.get("about", ""))), "gold": {R("point", r["key"])}})
    for r in con.execute("SELECT key FROM record WHERE type = 'transfer'"):
        cid = r["key"].split("/")[0]
        c = json.loads(con.execute("SELECT full FROM record WHERE type = 'structure' AND cand = ?", (cid,)).fetchone()["full"])["path"]
        rows.append({"q": "tax on the share transfer needed for %s" % " to ".join(plain_node(n) for n in c["path"]),
                     "gold": {R("transfer", x) for (x,) in con.execute("SELECT key FROM record WHERE type = 'transfer' AND cand = ?", (cid,))}})
    rows.append({"q": "refund of the tax withheld on the earlier dividend", "gold": {R("past_payment", k) for (k,) in con.execute("SELECT key FROM record WHERE type = 'past_payment'")}})
    rows = rnd.sample(rows, len(rows))
    hand = [
        {"q": "the structure ranked first and its tax with every point favourable and with every point against the group", "gold": {R("structure", "c5"), R("brief", "summary")}},
        {"q": "the tax range of the current structure", "gold": {R("structure", "c0")}},
        {"q": "one-off cost of transferring the stake directly to the Singapore company", "gold": {R("structure", "c1"), R("structure", "c2"), R("delta", "c1.b0"), R("delta", "c2.b0")}},
        {"q": "judgment points with the largest tax at stake", "gold": {R("point", "bo@cn:hk:company"), R("point", "gaar@cn:hk:company"), R("point", "ppt@cn:hk:company")}},
        {"q": "first structure if the Mainland beneficial-ownership point is answered against the group", "gold": {R("point", "bo@cn:hk:company")}},
    ]
    for x in rows + hand:
        x["filters"] = {"case_id": case_id}
    return {"P-template": rows, "P-hand": hand}


def case_sets(reader, case_id):
    con, e = reader.casefile(case_id)
    if e:
        raise SystemExit(e)
    docs = {r["key"]: r["key"] for r in con.execute("SELECT key FROM record WHERE type = 'document'")}
    pages = {r["key"] for r in con.execute("SELECT key FROM record WHERE type = 'page'")}
    rows = []
    for r in con.execute("SELECT full FROM record WHERE type = 'source'"):
        s = json.loads(r["full"])
        doc, page = str(s.get("doc") or ""), s.get("page") or 1
        key = "%s:%s" % (doc, page)
        if key not in pages:
            continue
        k = re.sub(r"[._\[\]]", " ", str(s.get("key"))).replace("pct", "percent")
        k = re.sub(r"\b([a-z]{2}):(company|individual)\b", lambda m: plain_node(m.group(0)), k)
        fact = con.execute("SELECT full FROM record WHERE type = 'fact' AND key = ?", (s.get("key"),)).fetchone()
        val = json.loads(fact["full"]).get("value") if fact else None
        if val in (None, "", True, False) or isinstance(val, (list, dict)):
            continue                                       # the page behind a fact is looked up with the fact's value
        rows.append({"q": "%s %s" % (k, val), "gold": {"%s:page:%s" % (case_id, key)}, "filters": {"case_id": case_id, "type": "page"}})
    return {"C-sources": rows}


def metrics(ranked, gold, k=10):
    hit = [1 if r in gold else 0 for r in ranked[:k]]
    dcg = sum(h / math.log2(i + 2) for i, h in enumerate(hit))
    ideal = sum(1 / math.log2(i + 2) for i in range(min(len(gold), k)))
    first = next((i for i, h in enumerate(hit) if h), None)
    return {"R@1": float(bool(hit[:1] and hit[0])), "R@5": float(any(hit[:5])), "R@10": float(any(hit)),
            "MRR@10": 1.0 / (first + 1) if first is not None else 0.0, "nDCG@10": dcg / ideal if ideal else 0.0}


def run_set(reader, items, scope, cfg=None, material=None):
    out, secs = [], []
    for x in items:
        t = time.time()
        if scope == "law":
            res = reader.law_search(x["q"], x.get("filters", {}), 10, cfg)
            ranked = [h["id"] for h in res["hits"]]
        else:
            filters = x.get("filters", {})
            if scope == "products":
                case_id, run_id = reader.resolve_run(filters)
                con, _ = reader.products(case_id, run_id)
            else:
                con, _ = reader.casefile(filters["case_id"])
            saved = reader.cfg[material].get("rerank")
            reader.cfg[material]["rerank"] = bool(cfg and cfg.get("rerank"))
            ranked = [h["id"] for h in reader.rec_search(con, x["q"], {k: v for k, v in filters.items() if k not in ("case_id", "run_id")}, 10, material)]
            reader.cfg[material]["rerank"] = saved
        secs.append(time.time() - t)
        out.append(metrics(ranked, x["gold"]))
    avg = {m: round(sum(o[m] for o in out) / max(1, len(out)), 3) for m in ("R@1", "R@5", "R@10", "MRR@10", "nDCG@10")}
    avg["n"], avg["s/query"] = len(out), round(sum(secs) / max(1, len(secs)), 2)
    return avg


def split(items):
    return items[0::2], items[1::2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default="CASE-20261102-a032c0")
    ap.add_argument("--sample", type=int, default=120)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    reader = RC.Reader("analysis", log=False)
    reader.law_search("warm up the models", {}, 3, {"dense": True, "rerank": True})
    report, choice = {}, {}
    sets = law_sets(a.sample)
    print({n: len(v) for n, v in sets.items()}, flush=True)
    for name, items in sets.items():
        dev, test = split(items)
        for cname, cfg in LAW_CONFIGS:
            report[(name, cname, "dev")] = run_set(reader, dev, "law", cfg)
            report[(name, cname, "test")] = run_set(reader, test, "law", cfg)
            print(name, cname, report[(name, cname, "dev")], report[(name, cname, "test")], flush=True)
    for name, items in list(product_sets(reader, a.case).items()) + list(case_sets(reader, a.case).items()):
        material = "products" if name.startswith("P") else "case"
        dev, test = split(items) if len(items) > 8 else (items, items)
        for cname, cfg in (("bm25", {"rerank": False}), ("+rerank", {"rerank": True})):
            report[(name, cname, "dev")] = run_set(reader, dev, material, cfg, material)
            report[(name, cname, "test")] = run_set(reader, test, material, cfg, material)
            print(name, cname, report[(name, cname, "dev")], report[(name, cname, "test")], flush=True)

    def gain(sets_, a_, b_, split_):
        """Mean change of nDCG@10 and Recall@10 from config a_ to b_ over the sets, on a split."""
        d = [(report[(s, b_, split_)]["nDCG@10"] - report[(s, a_, split_)]["nDCG@10"],
              report[(s, b_, split_)]["R@10"] - report[(s, a_, split_)]["R@10"]) for s in sets_]
        return tuple(round(sum(x[i] for x in d) / len(d), 3) for i in (0, 1))

    lsets = list(sets)
    steps = [("dense", "bm25", "+dense"), ("balance", "+dense", "+balance"), ("graph", "+balance", "+graph"), ("rerank", "+graph", "+rerank")]
    law = {"bm25": True}
    for comp, a_, b_ in steps:
        dg, tg = gain(lsets, a_, b_, "dev"), gain(lsets, a_, b_, "test")
        ok = (dg[0] > 0 or dg[1] > 0) and tg[0] >= 0 and tg[1] >= 0
        if comp == "rerank":
            ok = ok and max(report[(s, b_, "dev")]["s/query"] for s in lsets) < 1.0 + max(report[(s, a_, "dev")]["s/query"] for s in lsets)
        law[comp] = ok
        choice[comp] = {"dev": dg, "test": tg, "adopted": ok}
    if law.get("rerank") and not law.get("graph"):
        dg, tg = gain(lsets, "+balance", "-graph+rerank", "dev"), gain(lsets, "+balance", "-graph+rerank", "test")
        choice["rerank_without_graph"] = {"dev": dg, "test": tg}
    settings = {"law": law}
    for material, names in (("products", ["P-template", "P-hand"]), ("case", ["C-sources"])):
        dg, tg = gain(names, "bm25", "+rerank", "dev"), gain(names, "bm25", "+rerank", "test")
        settings[material] = {"rerank": (dg[0] > 0 or dg[1] > 0) and tg[0] >= 0 and tg[1] >= 0}
        choice["%s rerank" % material] = {"dev": dg, "test": tg, "adopted": settings[material]["rerank"]}
    print(json.dumps(choice, indent=1))
    print(json.dumps(settings))
    if a.write:
        lines = ["# Retrieval evaluation", "", "Written by agent/tools/read_eval.py on %s (case %s, sample %d). Golden sets and the adoption rule: the module docstring and "
                 "agent/retrieval_spec.en.md §12. Even items are the development set, odd items the test set." % (RC.now(), a.case, a.sample), "",
                 "| Set | Config | Split | n | R@1 | R@5 | R@10 | MRR@10 | nDCG@10 | s/query |", "|---|---|---|---|---|---|---|---|---|---|"]
        for (s, c, sp), m in report.items():
            lines.append("| %s | %s | %s | %d | %.3f | %.3f | %.3f | %.3f | %.3f | %.2f |" % (s, c, sp, m["n"], m["R@1"], m["R@5"], m["R@10"], m["MRR@10"], m["nDCG@10"], m["s/query"]))
        lines += ["", "## Decisions (mean change of nDCG@10 and R@10)", "", "| Component | Dev | Test | Adopted |", "|---|---|---|---|"]
        for comp, v in choice.items():
            lines.append("| %s | %s | %s | %s |" % (comp, v["dev"], v["test"], v.get("adopted", "-")))
        lines += ["", "Switches written to agent/retrieval_settings.json: `%s`" % json.dumps(settings)]
        (PROJECT / "agent" / "retrieval_eval.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        (PROJECT / "agent" / "retrieval_settings.json").write_text(json.dumps(settings, indent=1) + "\n", encoding="utf-8")
        print("wrote agent/retrieval_eval.md and agent/retrieval_settings.json")


if __name__ == "__main__":
    main()
