#!/usr/bin/env python
"""Retrieval evaluation on gold sets built from the project's own traced citations (I1: per-dataset reporting, I3:
disjoint and stratified sets, I20: deterministic scoring, no LLM judge). Writes official/SEARCH_EVAL.md.

Gold sets (query -> relevant clauses; a hit counts if it is a relevant clause, another expression of the same
provision, or a clause the relevant one contains):
  params      param name words (+ income, topic)        -> the clause the param quotes      (~300)
  rules       discretion key words of a compiled rule   -> the clauses the rule cites        (~48)
  gaps        dictionary-gap id words                    -> the clause the gap quotes        (~65)
  xlang       first 60 characters of a zh treaty clause  -> the en clause of the same provision, and back
Limits: queries are terse identifiers written while building the library, one or two relevant clauses each, so
unlabeled relevant clauses count as misses (false negatives, I1 Hole@10, I3).

Python 3.9, conda env "pytorch".   python official/tools/eval_search.py [--configs bm25,dense,...]
"""
import io
import random
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import search as S                                      # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = {"bm25": (("bm25",), {}), "dense": (("dense",), {}),
           "balanced bm25+dense": (("bm25", "dense"), {"_balanced": True}),
           "balanced bm25+dense+graph w.5": (("bm25", "dense", "graph"), {"graph": 0.5, "_balanced": True}),
           "balanced all+exact": (("exact", "bm25", "dense", "graph"), {"graph": 0.5, "_balanced": True}),
           "bm25+dense": (("bm25", "dense"), {}), "bm25+dense w.5": (("bm25", "dense"), {"dense": 0.5}),
           "bm25+graph": (("bm25", "graph"), {}), "bm25+graph w.5": (("bm25", "graph"), {"graph": 0.5}),
           "bm25+dense+graph": (("bm25", "dense", "graph"), {}),
           "bm25+dense+graph w.5": (("bm25", "dense", "graph"), {"dense": 0.5, "graph": 0.5}),
           "bm25+dense+graph w.3": (("bm25", "dense", "graph"), {"dense": 0.3, "graph": 0.3})}
DEV = {"params"}                                         # weights are chosen on params only; the other sets are test
KS = (1, 5, 10, 50)


def words(ident):
    return re.sub(r"[_.:\-]+", " ", ident).replace("NEW ", "").strip()


def gold_sets(con):
    sets = defaultdict(list)
    for pid, name, income, topic, cite in con.execute("SELECT param_id, name, income, topic, cite_id FROM param"):
        sets["params"].append((("%s %s %s" % (words(name), "" if income == "ALL" else words(income).lower(), topic)).strip(), {cite}))
    by_rule = defaultdict(set)
    for src, dst in con.execute("SELECT src, dst FROM edge WHERE kind = 'rule_cites' AND status = 'resolved'"):
        by_rule[src].add(dst)
    import importlib
    sys.path.insert(0, str(ROOT.parent))
    spec = importlib.import_module("tax_graph.rules.spec").SPEC
    from tax_graph.rules.model import Discretion, leaves
    for r in spec:
        for leaf in (leaves(r.cond) if r.cond is not None else []):
            if isinstance(leaf, Discretion) and leaf.cites:
                sets["rules"].append((words(leaf.key), set(leaf.cites)))
    for gid, cite in con.execute("SELECT new_id, cite_id FROM gap WHERE cite_id != ''"):
        sets["gaps"].append((words(gid), {cite}))
    rnd = random.Random(7)
    pairs = con.execute("SELECT e.src, e.dst FROM edge e JOIN clause_meta a ON a.cite_id = e.src JOIN clause_meta b ON b.cite_id = e.dst "
                        "WHERE e.kind = 'same_provision' AND a.lang != b.lang AND a.provision_id LIKE 'treaty.%'").fetchall()
    rnd.shuffle(pairs)
    lang_of = {c: l for c, l in con.execute("SELECT cite_id, lang FROM clause_meta")}
    prov_of = {c: p for c, p in con.execute("SELECT cite_id, provision_id FROM clause_meta")}
    by_prov = defaultdict(set)
    for c, p in prov_of.items():
        by_prov[p].add(c)
    for a, b in pairs[:120]:
        for q, g in ((a, b), (b, a)):
            text = con.execute("SELECT text FROM clause WHERE cite_id = ?", (q,)).fetchone()[0]
            body = re.sub(r"^\s*(?:第[一二三四五六七八九十百]+条|Article \d+[A-Z]?|[一二三四五六七八九十]+、|\d+\.)\s*", "", text)
            other = {c for c in by_prov[prov_of[q]] if (lang_of[c] or "")[:2] != (lang_of[q] or "")[:2]}
            sets["xlang"].append((re.sub(r"\s+", " ", body)[:60], other, "strict"))   # only the other language counts
    return sets


def relevant_set(con, gold, strict=False):
    """Gold clauses, their other expressions (same provision) and the clauses they contain."""
    out = set(gold)
    if strict:
        return out
    for g in gold:
        out.update(x[0] for x in con.execute("SELECT CASE WHEN src = ? THEN dst ELSE src END FROM edge "
                                             "WHERE kind = 'same_provision' AND (src = ? OR dst = ?)", (g, g, g)))
        out.update(x[0] for x in con.execute("SELECT dst FROM edge WHERE kind = 'contains' AND src = ?", (g,)))
    return out


def evaluate(lib, sets, configs):
    con = lib.con
    lang_of = {c: (l or "")[:2] for c, l in con.execute("SELECT cite_id, lang FROM clause_meta")}
    rows = []
    for name, items in sets.items():
        rel = [relevant_set(con, it[1], strict=len(it) > 2) for it in items]
        glang = [lang_of.get(sorted(it[1])[0], "?") if it[1] else "?" for it in items]
        for cfg in configs:
            ch, wts = CONFIGS[cfg]
            per = defaultdict(lambda: {"n": 0, "mrr": 0.0, **{k: 0 for k in KS}})
            for it, r, gl in zip(items, rel, glang):
                bal = bool(wts.get("_balanced"))
                res = lib.search(it[0], k=max(KS), channels=ch, weights={a: b for a, b in wts.items() if a != "_balanced"}, balanced=bal)
                ranked = [{h.cite_id, *h.variants} | (set(h.other_lang) if name != "xlang" else set())
                          for h in (res if isinstance(res, list) else [])]
                first = next((i for i, cs in enumerate(ranked, 1) if cs & r), None)
                for key in ("all", "gold " + gl):
                    d = per[key]
                    d["n"] += 1
                    for k in KS:
                        d[k] += int(first is not None and first <= k)
                    d["mrr"] += (1.0 / first) if first and first <= 10 else 0.0
            for key, d in sorted(per.items()):
                rows.append((name, cfg, key, d["n"], *[d[k] / d["n"] for k in KS], d["mrr"] / d["n"]))
    return rows


def model_name(lib):
    r = lib.con.execute("SELECT model FROM unit_vec LIMIT 1").fetchone() if lib.con.execute(
        "SELECT name FROM sqlite_master WHERE name = 'unit_vec'").fetchone() else None
    return r[0] if r else "none"


def main(argv):
    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    configs = argv[argv.index("--configs") + 1].split(",") if "--configs" in argv else list(CONFIGS)
    lib = S.Library()
    sets = gold_sets(lib.con)
    rows = evaluate(lib, sets, configs)
    lines = ["# SEARCH_EVAL", "", "由 `tools/eval_search.py` 生成，不要手改。金标准取自本项目自己追溯过的引用（参数、规则裁量项、字典缺口各自引用的条款；"
             "条约同一条款的中英文对照），命中按条款计：本条、同一条款的其他文本、本条所含的款都算。", "",
             "向量模型：%s。权重只在 params 上选（开发集），rules、gaps、xlang 是测试集。" % model_name(lib), "",
             "| 集合 | 配置 | 切分 | 条数 | R@1 | R@5 | R@10 | R@50 | MRR@10 |", "|---|---|---|---|---|---|---|---|---|"]
    for name, cfg, key, n, *vals in rows:
        lines.append("| %s%s | %s | %s | %d | %s |" % (name, " (dev)" if name in DEV else "", cfg, key, n, " | ".join("%.3f" % v for v in vals)))
    out_name = argv[argv.index("--out") + 1] if "--out" in argv else "SEARCH_EVAL.md"
    lines += ["", "局限：查询是建库时写下的简短标识，每条只有一两个标注的相关条款，未标注的相关条款计为未命中（BEIR 的 Hole@10 问题）；"
              "xlang 只覆盖条约，因为只有条约在库内同时有中英文文本。"]
    (ROOT / out_name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    out.write("\n".join(lines) + "\n")
    out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
