#!/usr/bin/env python
"""Search, grounding and impact over official.sqlite (knowledge layer from graph.py). Python 3.9, conda env "pytorch".

  python official/tools/search.py q "受益所有人 判定" [--k 10] [--jur CN] [--lang zh] [--as-of 2026-01-01]
                                    [--channels exact,bm25,dense,graph]
  python official/tools/search.py ground "quote text" hk.cap112.en#s15
  python official/tools/search.py impact cn.law.eit#3
  python official/tools/search.py at treaty.cn-hk.2006#13.5 2007-01-01

Design (papers in literature/notes, synthesis in literature/notes/I_综合.md):
  channels   exact (cite ids, "section 15", "第三条" with a named act, param ids) > BM25 over verbatim units (I1, I6, I9)
             + optional dense vectors (I4) + expansion over explicit edges only, never over generated ones (I13, I22);
             merged by reciprocal rank fusion, k = 60, which needs no score calibration (I2). Exact hits stay first.
  results    verbatim spans with their cite_id, expression, validity and the channels that found them; never generated
             text (I13, I14). A clause is reported once per provision and language (the canonical expression first).
  time       --as-of keeps clauses valid on that date; a date before every expression's coverage, or an instrument
             only listed as removed, is answered NotCovered with the reason, never with today's text (I20).
  ground     a quote counts only if it is found verbatim (whitespace aside) in the cited clause (I21, I14).
"""
import io
import json
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import graph as G                                       # noqa: E402

DB = Path(__file__).resolve().parents[1] / "official.sqlite"
RRF_K = 60
WEIGHTS = {"exact": 1.0, "bm25": 1.0, "dense": 1.0, "graph": 0.5}     # chosen on the dev set (params) with BAAI/bge-m3, SEARCH_EVAL.md
EDGE_KINDS = ("contains", "cites", "same_provision", "substitutes")


@dataclass
class Hit:
    cite_id: str
    provision_id: str
    expr_id: str
    lang: str
    title: str
    score: float
    channels: Dict[str, int]                              # channel -> rank (1 = best)
    span: Tuple[int, int]
    snippet: str
    valid_from: Optional[str]
    valid_to: Optional[str]
    variants: List[str] = field(default_factory=list)     # same provision and language in other expressions
    validity: str = "not asked"                            # with as_of: valid | unknown (no effective date stated)
    other_lang: List[str] = field(default_factory=list)   # the same provision in the other language(s): explicit link


@dataclass
class Removed:
    """A query naming an instrument the library deleted as repealed or replaced (false-premise guard, I14, I20)."""
    id: str
    title: str
    reason: str
    ends: Optional[str]
    replaced_by: Optional[str]


@dataclass
class NotCovered:
    reason: str
    detail: List[str] = field(default_factory=list)


class Library:
    def __init__(self, db=DB):
        self.con = sqlite3.connect(str(db))
        self.con.row_factory = sqlite3.Row
        q = self.con.execute
        self.meta = {r["cite_id"]: r for r in q("SELECT m.cite_id, m.expr_id, m.provision_id, m.lang, e.canonical, e.work_id, "
                                                  "d.title, d.jur, t.valid_from, t.valid_to FROM clause_meta m "
                                                  "JOIN expression e ON e.expr_id = m.expr_id JOIN doc d ON d.id = m.expr_id "
                                                  "JOIN clause_time t ON t.cite_id = m.cite_id")}
        self.unit_rows = {r["rowid"]: r for r in q('SELECT rowid, unit_id, cite_id, start, "end" FROM unit')}
        self.alias = {r[0]: r[1] for r in q("SELECT alias, work_id FROM alias")}
        self._vec = None
        self._model = None
        self.tombs = [dict(r) for r in q("SELECT * FROM tombstone")]

    def removed(self, query):
        """Removed instruments the query names by id, number or title."""
        flat = re.sub(r"\s+", "", query)
        out = []
        for t in self.tombs:
            num = re.search(r"(\d{4})-(\d+)$", t["id"].split(".a")[0])
            names = [t["id"], re.sub(r"\s+", "", t["title"] or "")]
            if num and t["id"].startswith("cn.sta."):
                names.append("公告%s年第%d号" % (num.group(1), int(num.group(2))))
            if any(n and len(n) >= 6 and n in flat for n in names):
                out.append(Removed(t["id"], t["title"], t["reason"], t["ends"], t["replaced_by"]))
        return out

    # ------------------------------------------------------------ channels
    def bm25(self, query, n=200):
        toks = [t for t in G.fts_tokens(query).split() if len(t) > 1 or G.CJK.match(t)]
        if not toks:
            return []
        expr = " OR ".join('"%s"' % t.replace('"', "") for t in dict.fromkeys(toks))
        rows = self.con.execute("SELECT rowid, bm25(unit_fts, 0.4, 1.0) s FROM unit_fts WHERE unit_fts MATCH ? ORDER BY s LIMIT ?",
                                (expr, n)).fetchall()
        return [self.unit_rows[r[0]] for r in rows]

    def dense(self, query, n=200):
        if self._vec is None:
            rows = self.con.execute("SELECT u.rowid, v.vec, v.model FROM unit_vec v JOIN unit u ON u.unit_id = v.unit_id").fetchall() \
                if self.con.execute("SELECT name FROM sqlite_master WHERE name='unit_vec'").fetchone() else []
            if not rows:
                self._vec = False
                return []
            import numpy as np
            self._ids = [r[0] for r in rows]
            self._vec = np.vstack([np.frombuffer(r[1], dtype="float32") for r in rows])
            import os
            os.environ.setdefault("HF_HUB_OFFLINE", "1")   # the model is cached by graph.py --dense; no network check per query
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(rows[0][2])
        if self._vec is False:
            return []
        import torch                                    # numpy's BLAS clashes with torch's in this environment: use torch
        qv = torch.from_numpy(self._model.encode([query], normalize_embeddings=True)[0].astype("float32"))
        if not torch.is_tensor(self._vec):
            self._vec = torch.from_numpy(self._vec)
        top = torch.topk(self._vec @ qv, min(n, self._vec.shape[0])).indices.tolist()
        return [self.unit_rows[self._ids[i]] for i in top]

    def exact(self, query):
        """cite ids, param ids, 'section 15 IRO' / '第三条 企业所得税法' style references."""
        out = []
        for cid in re.findall(r"[a-z][a-z0-9\-]*(?:\.[\w\-]+)+#[\w.()\-]+", query):
            if cid in self.meta:
                out.append(cid)
        for pid in re.findall(r"\b[a-z]{2}(?:-[a-z]{2})?\.[a-z_]+(?:\.[a-z0-9_]+)+\b", query):
            r = self.con.execute("SELECT cite_id FROM param WHERE param_id = ?", (pid,)).fetchone()
            if r:
                out.append(r[0])
        m = re.search(r"(?:section|s\.)\s?(\d+[A-Z]{0,4})", query, re.I)
        if m:
            w = next((self.alias[a] for a in sorted(self.alias, key=len, reverse=True)
                      if len(a) >= 3 and a.lower() in re.sub(r"\s+", "", query).lower()), None)
            for cid, r in self.meta.items():
                if r["canonical"] and cid.endswith("#s" + m.group(1)) and (w is None or r["work_id"] == w):
                    out.append(cid)
        m = re.search(r"第([一二三四五六七八九十百零〇\d]+)条", query)
        if m:
            art = str(G.cn2int(m.group(1)))
            flat = re.sub(r"\s+", "", query)
            w = next((self.alias[a] for a in sorted(self.alias, key=len, reverse=True) if len(a) >= 3 and a in flat), None)
            if w:
                out += [cid for cid, r in self.meta.items() if r["work_id"] == w and cid.split("#")[1] == art and r["canonical"]]
        return list(dict.fromkeys(out))

    def expand(self, seeds, n=50):
        """Personalized PageRank over explicit edges around the seed clauses (2 hops)."""
        import networkx as nx
        if not seeds:
            return []
        g = nx.DiGraph()
        frontier = set(seeds)
        for _ in range(2):
            nxt = set()
            for node in frontier:
                for src, dst, kind in self.con.execute(
                        "SELECT src, dst, kind FROM edge WHERE (src = ? OR dst = ?) AND status IN ('resolved','ancestor') AND kind IN (%s)"
                        % ",".join("?" * len(EDGE_KINDS)), (node, node) + EDGE_KINDS):
                    if src in self.meta and dst in self.meta:
                        g.add_edge(src, dst)
                        g.add_edge(dst, src)          # references are read both ways (cited-by matters as much)
                        nxt.update((src, dst))
            frontier = nxt - frontier
        if g.number_of_nodes() == 0:
            return []
        pers = {s: 1.0 / (i + 1) for i, s in enumerate(seeds) if s in g}
        if not pers:
            return []
        pr = nx.pagerank(g, alpha=0.5, personalization=pers)
        spec = {c: v / (1.0 + g.in_degree(c)) ** 0.5 for c, v in pr.items()}      # node specificity, after I12
        return [c for c, _ in sorted(spec.items(), key=lambda kv: (-kv[1], kv[0])) if c not in seeds][:n]

    # ------------------------------------------------------------ search
    def search(self, query, k=10, jur=None, lang=None, as_of=None, channels=("exact", "bm25", "dense", "graph"), weights=None,
               balanced=True, today=None):
        """balanced: a query in one language reaches clauses in the other only through dense vectors and explicit
        edges, never through BM25; so the two language groups are ranked separately and interleaved (same language
        first) instead of letting BM25 noise bury every other-language candidate."""
        w = dict(WEIGHTS, **(weights or {}))
        qlang = G.lang_of(query)
        ranks: Dict[str, Dict[str, int]] = {}
        best_unit: Dict[str, Tuple[int, int]] = {}

        def add(channel, cites_with_span):
            seen = set()
            for cite, span in cites_with_span:
                if cite in seen or cite not in self.meta:
                    continue
                seen.add(cite)
                ranks.setdefault(cite, {})[channel] = len(seen)
                if span and cite not in best_unit:
                    best_unit[cite] = span

        if "bm25" in channels:
            add("bm25", [(u["cite_id"], (u["start"], u["end"])) for u in self.bm25(query)])
        if "dense" in channels:
            add("dense", [(u["cite_id"], (u["start"], u["end"])) for u in self.dense(query)])
        exact = self.exact(query) if "exact" in channels else []

        def keep(cite):
            r = self.meta[cite]
            if jur and r["jur"].upper() != jur.upper() and not r["work_id"].startswith("treaty.") :
                return False
            if lang and (r["lang"] or "")[:2] != lang[:2]:
                return False
            if as_of and ((r["valid_from"] and r["valid_from"] > as_of) or (r["valid_to"] and r["valid_to"] <= as_of)):
                return False                            # known not to be in force on that date
            return True

        def fused():
            scores = {c: sum(w.get(name, 1.0) / (RRF_K + rk) for name, rk in ch.items()) for c, ch in ranks.items()}
            return sorted(scores, key=lambda c: (-scores[c], c)), scores

        order, scores = fused()
        if "graph" in channels and order:
            add("graph", [(c, None) for c in self.expand([c for c in order[:10] if keep(c)])])
            order, scores = fused()
        if balanced:
            same = [c for c in order if (self.meta[c]["lang"] or "")[:2] == qlang]
            other_scores = {c: sum(w.get(n, 1.0) / (RRF_K + rk) for n, rk in ranks[c].items() if n != "bm25")
                            for c in order if (self.meta[c]["lang"] or "")[:2] != qlang}
            other = [c for c in sorted(other_scores, key=lambda c: (-other_scores[c], c)) if other_scores[c] > 0]
            merged = []
            for a, b in zip(same, other):
                merged += [a, b]
            longer = same if len(same) > len(other) else other
            merged += longer[min(len(same), len(other)):]
            merged += [c for c in order if c not in set(merged)]
            scores = {c: 1.0 / (i + 1) for i, c in enumerate(merged)}
        for i, c in enumerate(exact):                    # exact references bypass fusion
            ranks.setdefault(c, {})["exact"] = i + 1
            scores[c] = 10.0 - i * 1e-3
        order = sorted(scores, key=lambda c: (-scores[c], c))
        filtered = [c for c in order if keep(c)]
        if as_of and order and not filtered:
            return NotCovered("no clause among the candidates is valid on %s" % as_of,
                              ["%s valid %s..%s" % (c, self.meta[c]["valid_from"], self.meta[c]["valid_to"]) for c in order[:5]])
        hits, used = [], {}
        for c in filtered:                              # one hit per (provision, language): canonical expression first
            r = self.meta[c]
            key = (r["provision_id"], (r["lang"] or "")[:2])
            if key in used:
                used[key].variants.append(c)
                continue
            text = self.con.execute("SELECT text FROM clause WHERE cite_id = ?", (c,)).fetchone()[0]
            a, b = best_unit.get(c, (0, min(len(text), 400)))
            h = Hit(c, r["provision_id"], r["expr_id"], r["lang"], r["title"], round(scores[c], 6), ranks.get(c, {}),
                    (a, b), text[a:b], r["valid_from"], r["valid_to"],
                    validity=("valid" if r["valid_from"] else "unknown") if as_of else
                    ("not yet in force" if r["valid_from"] and r["valid_from"] > (today or _today()) else "not asked"))
            used[key] = h
            hits.append(h)
            if len(hits) >= k:
                break
        for h in hits:                                  # the same provision in other languages, by explicit edge
            h.other_lang = sorted({c for (c,) in self.con.execute(
                "SELECT CASE WHEN src = ? THEN dst ELSE src END FROM edge WHERE kind = 'same_provision' AND (src = ? OR dst = ?)",
                (h.cite_id, h.cite_id, h.cite_id)) if c in self.meta and (self.meta[c]["lang"] or "")[:2] != (h.lang or "")[:2]})
        for h in hits:                                  # prefer the canonical expression as the reported clause
            if not self.meta[h.cite_id]["canonical"]:
                canon = [v for v in h.variants if self.meta[v]["canonical"]]
                if canon:
                    h.variants.append(h.cite_id)
                    h.variants.remove(canon[0])
                    h.cite_id, h.expr_id = canon[0], self.meta[canon[0]]["expr_id"]
        return hits

    # ------------------------------------------------------------ grounding, impact, time
    def ground(self, quote, cite_id):
        r = self.con.execute("SELECT text FROM clause WHERE cite_id = ?", (cite_id,)).fetchone()
        if not r:
            return {"ok": False, "reason": "no such clause (it may be repealed: see event / tombstone)", "cite_id": cite_id}
        a, b, n = G.anchor(r[0], quote)
        return {"ok": a is not None, "cite_id": cite_id, "start": a, "end": b, "occurrences": n,
                "text": r[0][a:b] if a is not None else None}

    def impact(self, cite_id):
        q = lambda s, *a: [tuple(x) for x in self.con.execute(s, a)]
        desc = [cite_id] + [x[0] for x in q("SELECT dst FROM edge WHERE src = ? AND kind = 'contains'", cite_id)]
        ph = ",".join("?" * len(desc))
        params = q("SELECT src FROM edge WHERE kind = 'param_cites' AND dst IN (%s)" % ph, *desc)
        rules = q("SELECT DISTINCT src FROM edge WHERE (kind = 'rule_cites' AND dst IN (%s)) OR (kind = 'rule_uses_param' AND dst IN (%s))"
                  % (ph, ",".join("?" * len(params) or "?")), *desc, *([p[0] for p in params] or ["-"]))
        cited_by = q("SELECT src, evidence FROM edge WHERE kind = 'cites' AND dst IN (%s)" % ph, *desc)
        same = q("SELECT CASE WHEN src = ? THEN dst ELSE src END FROM edge WHERE kind = 'same_provision' AND (src = ? OR dst = ?)",
                 cite_id, cite_id, cite_id)
        gaps = q("SELECT src FROM edge WHERE kind = 'gap_cites' AND dst IN (%s)" % ph, *desc)
        decisions = q("SELECT DISTINCT src FROM edge WHERE kind = 'decision_cites' AND dst IN (%s)" % ph, *desc)
        return {"cite_id": cite_id, "params": [p[0] for p in params], "rules": [r[0] for r in rules], "gaps": [g[0] for g in gaps],
                "decisions": [d[0] for d in decisions],
                "cited_by": sorted({c[0] for c in cited_by}), "same_provision": [s[0] for s in same]}

    def at(self, provision_or_cite, date):
        """The clause(s) expressing a provision on a date, or NotCovered with the reason."""
        pid = self.meta[provision_or_cite]["provision_id"] if provision_or_cite in self.meta else provision_or_cite
        rows = self.con.execute("SELECT m.cite_id, t.valid_from, t.valid_to FROM clause_meta m JOIN clause_time t ON t.cite_id = m.cite_id "
                                "WHERE m.provision_id = ?", (pid,)).fetchall()
        work = pid.split("#")[0]
        tomb = self.con.execute("SELECT id, reason, ends FROM tombstone WHERE id = ? OR id LIKE ?", (work, work + ".%")).fetchall()
        if not rows:
            ev = self.con.execute("SELECT kind, by, since, note FROM event WHERE target LIKE ?", ("%" + pid.split("#")[1] if "#" in pid else pid,)).fetchall()
            return NotCovered("provision not in the library (only current law is kept)",
                              [str(tuple(t)) for t in tomb] + [str(tuple(e)) for e in ev[:5]])
        ok = [r[0] for r in rows if r[1] and r[1] <= date and (not r[2] or r[2] > date)]
        if ok:
            return ok
        unknown = [r[0] for r in rows if not r[1] and (not r[2] or r[2] > date)]
        if unknown:                                     # pending, not assumed: the expression states no effective date
            return NotCovered("validity unknown: no effective date stated for these expressions", unknown)
        return NotCovered("the library holds this provision only from %s; earlier versions are not kept" % min(r[1] for r in rows if r[1]),
                          ["%s valid %s..%s" % tuple(r) for r in rows])


def _today():
    import datetime
    return datetime.date.today().isoformat()


def main(argv):
    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if not argv:
        out.write(__doc__)
        return 1
    lib = Library()
    cmd = argv[0]
    if cmd == "q":
        opts = {"k": 10, "jur": None, "lang": None, "as_of": None, "channels": "exact,bm25,dense,graph"}
        query, rest = argv[1], argv[2:]
        for i in range(0, len(rest), 2):
            opts[rest[i].lstrip("-").replace("-", "_")] = rest[i + 1]
        for t in lib.removed(query):
            out.write("REMOVED from the library: %s %s\n  %s (ends %s; replaced by %s)\n" % (t.id, t.title, t.reason, t.ends, t.replaced_by))
        out.write("policy: %s; channels %s\n" % ("in force on " + opts["as_of"] if opts["as_of"] else "current library, no date filter",
                                               opts["channels"]))
        res = lib.search(query, k=int(opts["k"]), jur=opts["jur"], lang=opts["lang"], as_of=opts["as_of"],
                         channels=tuple(opts["channels"].split(",")))
        if isinstance(res, NotCovered):
            out.write("NOT COVERED: %s\n  %s\n" % (res.reason, "\n  ".join(res.detail)))
            return 0
        for i, h in enumerate(res, 1):
            out.write("%2d. %s  [%s]  %s  valid %s..%s%s\n    %s\n" % (i, h.cite_id, ",".join("%s:%d" % kv for kv in h.channels.items()),
                                                                (h.title or "")[:50], h.valid_from or "?", h.valid_to or "",
                                                                "" if h.validity == "not asked" else "  (" + h.validity + ")",
                                                                re.sub(r"\s+", " ", h.snippet)[:220]))
            if h.variants:
                out.write("    also: %s\n" % ", ".join(h.variants[:4]))
            if h.other_lang:
                out.write("    other language: %s\n" % ", ".join(h.other_lang[:3]))
    elif cmd == "ground":
        out.write(json.dumps(lib.ground(argv[1], argv[2]), ensure_ascii=False, indent=1) + "\n")
    elif cmd == "impact":
        out.write(json.dumps(lib.impact(argv[1]), ensure_ascii=False, indent=1) + "\n")
    elif cmd == "at":
        r = lib.at(argv[1], argv[2])
        out.write(json.dumps(r if isinstance(r, list) else r.__dict__, ensure_ascii=False, indent=1) + "\n")
    out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
