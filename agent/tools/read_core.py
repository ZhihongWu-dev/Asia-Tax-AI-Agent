"""The retrieval service's logic (agent/retrieval_spec.en.md §3-§10): map, search, list, get, expand, ground, pack and
cite_check over the law library, a run's products and a case file. Program only: no model writes anything here; the dense
encoder and the reranker only order candidates, and no score is returned. Text and values come back verbatim."""
import csv
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import access  # noqa: E402
import textutil as T  # noqa: E402

csv.field_size_limit(2 ** 31 - 1)
SERVER_VERSION = "0.1"
RUN_RE = re.compile(r"^\d{8}-[0-9a-f]{8}$")
CITE_RE = re.compile(r"^[a-z][\w.\-]*#[\w.()\-]+$")
RRF_K = 60
BUDGET = 2500                    # characters per question of a search, and of a list page
CALL_CAP = 10000                 # characters one search call returns at most
GET_PAGE = 6000                  # characters a get returns per page
HIT_TEXT = 520                   # characters of one law hit's fragment
DEFAULTS = {"law": {"bm25": True, "dense": True, "balance": True, "graph": True, "rerank": True},
            "products": {"rerank": False}, "case": {"rerank": False}}
WHAT = {
    "intake/facts.json": "facts recorded by the front agent (the optimizer's input format)",
    "intake/sources.json": "where each fact comes from: document, page, verbatim quote",
    "intake/answers.json": "the client's answers to judgment points, with the quote",
    "intake/constraints.json": "constraints the client set",
    "intake/dialogue.md": "the client's words, verbatim, by entry",
    "intake/notes.md": "the front agent's notes on the case",
    "intake/handoff.md": "the front agent's handoff to the analysis",
    "intake/to_collect.md": "laws the library lacks or has out of date",
    "intake/review_intake.md": "the intake review's checklist",
    "intake/run_input.json": "the optimizer input of this round",
    "brief.json": "entry point: best structure, current structure, scenario table, judgment points, gaps, exposure",
    "ranking.json": "every candidate's rank", "paths.json": "candidate structures: path, moves, restructuring",
    "tax.json": "tax of every branch, per hop", "branches.json": "branches and their assumed answers",
    "scenarios.json": "the scenario table", "open_items.json": "judgment points and fact gaps with their effect",
    "deltas.json": "savings, one-off cost, payback and exposure per branch", "requirements/": "condition trees per structure",
    "transfers/": "share-transfer evaluations per structure", "hops/": "cell evaluations per branch", "penalty/": "penalty rules per jurisdiction",
    "past_payments.json": "earlier dividends: refundable tax and conflicts", "diff.json": "changes against the previous run",
    "edges/": "every edge of the full graph (large; use search / expand)", "graph.json": "the full graph (large; use search / expand)",
}


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def err(kind, detail, **extra):
    out = {"error": kind, "detail": detail}
    out.update(extra)
    return out


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def size(obj):
    return len(json.dumps(obj, ensure_ascii=False))


def settings():
    p = HERE.parent / "retrieval_settings.json"
    out = json.loads(json.dumps(DEFAULTS))
    try:
        for k, v in json.loads(p.read_text(encoding="utf-8")).items():
            out.setdefault(k, {}).update(v)
    except (OSError, ValueError):
        pass
    return out


class Reader:
    def __init__(self, agent="", cases_root=PROJECT / "cases", db_root=PROJECT / "database", rule_root=PROJECT / "rule", log=True):
        self.agent = agent
        self.cases = Path(cases_root).resolve()
        self.db = Path(db_root).resolve()
        self.rule = Path(rule_root).resolve()
        self.log_on = log
        self.calls = 0
        self.seen = {}
        self.cfg = settings()
        self._law = None
        self._vec = None
        self._dense = None
        self._lib = None
        self._prod = {}
        self._case = {}
        self._rules = None

    # ------------------------------------------------------------ plumbing
    def tick(self, tool, args, out):
        self.calls += 1
        if self.log_on and (self.cases / "_log").is_dir():
            row = {"time": now(), "agent": self.agent, "tool": tool, "args": args, "chars": size(out),
                   "ids": [h.get("id") for h in out.get("hits", [])][:20] if isinstance(out, dict) else []}
            try:
                with (self.cases / "_log" / "read.jsonl").open("a", encoding="utf-8") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
            except OSError:
                pass
        return out

    def denied(self, rel):
        return access.denied(self.agent, rel, self.cases)

    def mark(self, hit, full):
        """Session de-duplication: a record already returned in this session comes back as its id only."""
        hid = hit.get("id")
        if hid in self.seen and not full:
            return {"id": hid, "seen": "returned at call %d; pass full=true to have it again" % self.seen[hid]}
        self.seen.setdefault(hid, self.calls + 1)
        return hit

    def law(self):
        if self._law is None:
            p = self.db / "index" / "law.sqlite"
            if not p.exists():
                import law_index
                law_index.build()
            self._law = sqlite3.connect(str(p), check_same_thread=False)
            self._law.row_factory = sqlite3.Row
        return self._law

    def lib(self):
        """The small library tables (documents, parameters, decisions, treaties, jurisdictions, blocked, superseded)."""
        if self._lib is None:
            L = {n: read_csv(self.db / ("%s.csv" % n)) for n in ("doc", "param", "decision", "treaty", "jurisdiction", "blocked", "superseded")}
            L["docs"] = {d["id"]: d for d in L["doc"]}
            L["params"] = {p["param_id"]: p for p in L["param"]}
            self._lib = L
        return self._lib

    def rules(self):
        if self._rules is None:
            self._rules = {r["rule_id"]: r for r in read_csv(self.rule / "rule.csv")}
        return self._rules

    def case_of_run(self, run_id):
        hits = [p for p in self.cases.glob("*/intake/products/%s" % run_id) if (p / "version.json").exists()]
        return hits[0].parents[2].name if hits else None

    def products(self, case_id, run_id):
        """(sqlite connection, error) of a run's records index, built on first use."""
        key = (case_id, run_id)
        if key not in self._prod:
            pd = self.cases / case_id / "intake" / "products" / run_id
            if not (pd / "version.json").exists():
                return None, err("not_found", "no products for run %s in case %s" % (run_id, case_id))
            why = self.denied("%s/intake/products/%s/brief.json" % (case_id, run_id))
            if why:
                return None, err("forbidden", why)
            import read_index
            path = read_index.build_products(pd)
            con = sqlite3.connect(str(path), check_same_thread=False)
            con.row_factory = sqlite3.Row
            self._prod[key] = con
        return self._prod[key], None

    def casefile(self, case_id):
        if case_id not in self._case:
            cd = self.cases / case_id
            if not (cd / "intake").is_dir():
                return None, err("not_found", "no case %s" % case_id)
            import read_index
            path = read_index.build_case(cd)
            con = sqlite3.connect(str(path), check_same_thread=False)
            con.row_factory = sqlite3.Row
            self._case[case_id] = con
        return self._case[case_id], None

    def current(self, case_id):
        return access.current_round(self.cases, case_id)

    def resolve_run(self, filters):
        """(case_id, run_id) from the filters: run_id alone finds its case; case_id alone takes the current run."""
        case_id, run_id = filters.get("case_id"), filters.get("run_id")
        if run_id and not case_id:
            case_id = self.case_of_run(run_id)
        if case_id and not run_id:
            run_id = self.current(case_id)[1]
        return case_id, run_id

    # ------------------------------------------------------------ map
    def map(self, case_id):
        cd = self.cases / str(case_id)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", str(case_id)) or not cd.is_dir():
            return err("not_found", "no case %s" % case_id)
        rnd, run = self.current(case_id)
        folders = []
        for sub in ("intake", "intake/documents", "report/%s" % run if run else None, "intake/products/%s" % run if run else None,
                    "notes/%s/round-%s" % (self.agent, rnd) if self.agent else None, "bugs"):
            if not sub:
                continue
            d = cd / sub
            if not d.is_dir():
                continue
            files = []
            for f in sorted(d.iterdir()):
                rel = "%s/%s/%s" % (case_id, sub, f.name)
                if f.name.endswith(".prev") or f.name == "index" or self.denied(rel):
                    continue
                if f.is_dir():
                    n = sum(1 for _ in f.glob("*.json"))
                    files.append({"name": f.name + "/", "files": n, "what": WHAT.get(f.name + "/", "")})
                else:
                    files.append({"name": f.name, "bytes": f.stat().st_size, "what": WHAT.get("%s/%s" % (sub, f.name), WHAT.get(f.name, ""))})
            folders.append({"path": "cases/%s/%s" % (case_id, sub), "files": files})
        out = {"case_id": case_id, "round": rnd, "run_id": run, "folders": folders}
        if run:
            con, e = self.products(case_id, run)
            if con:
                out["products"] = dict(con.execute("SELECT type, count(*) FROM record GROUP BY type").fetchall())
        con, e = self.casefile(case_id)
        if con:
            out["documents"] = [json.loads(r["card"]) for r in con.execute("SELECT card FROM record WHERE type = 'document' ORDER BY id")]
        L = self.lib()
        out["library"] = {"documents": len(L["doc"]), "parameters": len(L["param"]), "law_index": (self.db / "index" / "law.sqlite").exists()}
        out["how"] = ("search(queries, scope=law|products|case|all) finds; list(kind) enumerates; get(id) returns a record or clause verbatim; "
                      "expand(id) follows edges; ground(id, quote) checks a quote; ids are the refs of the sources table")
        return self.tick("map", {"case_id": case_id}, out)

    # ------------------------------------------------------------ search
    def search(self, queries, scope="all", filters=None, k=8, max_chars=BUDGET, full=False):
        filters = dict(filters or {})
        if isinstance(queries, str):
            queries = [queries]
        queries = [q for q in (queries or []) if q and q.strip()][:8]
        if not queries:
            return err("invalid", "give one or more queries")
        if scope not in ("law", "products", "case", "all"):
            return err("invalid", "scope is law, products, case or all")
        k = max(1, min(int(k or 8), 30))
        results, total = [], 0
        for qi, q in enumerate(queries):
            res = self.search_one(q, scope, filters, k)
            if "error" in res:
                results.append(res)
                continue
            hits, kept, used = res.pop("hits"), [], 0
            for i, h in enumerate(hits):
                h = self.mark(h, full)
                if (used + size(h) > max_chars or total + size(h) > CALL_CAP) and kept:
                    res["more"] = "%d more hits: search again with k larger or narrower filters" % (len(hits) - i)
                    break
                used += size(h)
                total += size(h)
                kept.append(h)
            res["hits"] = kept
            results.append(res)
        out = {"scope": scope, "results": results}
        return self.tick("search", {"queries": queries, "scope": scope, "filters": filters, "k": k}, out)

    def search_one(self, q, scope, filters, k):
        out = {"query": q, "hits": []}
        if scope in ("law", "all"):
            r = self.law_search(q, filters, k)
            if "error" in r:
                return r
            out["hits"] += r["hits"]
            for key in ("not_covered", "tried"):
                if r.get(key):
                    out[key] = r[key]
        if scope in ("products", "all"):
            case_id, run_id = self.resolve_run(filters)
            if case_id and run_id:
                con, e = self.products(case_id, run_id)
                if e:
                    return e
                out["hits"] += self.rec_search(con, q, filters, k, "products")
            elif scope == "products":
                return err("invalid", "products search needs case_id or run_id in filters")
        if scope in ("case", "all"):
            case_id = filters.get("case_id") or (self.case_of_run(filters["run_id"]) if filters.get("run_id") else None)
            if case_id:
                con, e = self.casefile(case_id)
                if e:
                    return e
                out["hits"] += self.rec_search(con, q, filters, k, "case")
            elif scope == "case":
                return err("invalid", "case search needs case_id in filters")
        if scope == "all":
            # three rankings over different materials have no common scale, and one judge over the union proved unfair to
            # some of them (2026-11-03): each material keeps its own best few, grouped and ranked within the material
            exact = [h for h in out["hits"] if "exact" in h.get("found_by", [])]
            share = max(2, -(-k // 3))
            grouped = []
            for s_ in ("law", "products", "case"):
                grouped += [h for h in out["hits"] if h["scope"] == s_ and h not in exact][:share]
            out["hits"] = exact + grouped
            out["grouped"] = "hits are grouped by scope (law, products, case), each ranked within its scope; search one scope for more"
        for h in out["hits"]:
            h.pop("_verbal", None)
        if not out["hits"]:
            out["not_found"] = True
        return out

    # ---- records (products, case file)
    REC_FILTERS = ("type", "cand", "branch", "jur", "slot", "point", "scenario", "doc", "page")

    def rec_where(self, filters, alias="r"):
        cond, args = [], []
        for f in self.REC_FILTERS:
            v = filters.get(f)
            if v not in (None, ""):
                vals = v if isinstance(v, list) else [v]
                cond.append("%s.%s IN (%s)" % (alias, f, ",".join("?" * len(vals))))
                args += [str(x) if f != "page" else int(x) for x in vals]
        return (" AND " + " AND ".join(cond)) if cond else "", args

    def rec_hit(self, row, scope, rank, by):
        return {"id": row["id"], "scope": scope, "type": row["type"], "card": row["card"], "rank": rank, "found_by": by, "_verbal": row["verbal"]}

    def rec_search(self, con, q, filters, k, material):
        where, args = self.rec_where(filters)
        found, by = [], {}
        toks = {t for t in re.findall(r"[\w.@:\-/|]+", q) if re.search(r"[a-z]", t, re.I) and re.search(r"\d|@|:|\|", t)}
        if toks:
            ph = ",".join("?" * len(toks))
            for row in con.execute("SELECT * FROM record r WHERE (r.id IN ({0}) OR r.key IN ({0}) OR r.point IN ({0}) OR (r.type = 'structure' AND r.cand IN ({0})) "
                                   "OR (r.type = 'branch' AND r.branch IN ({0})) OR (r.type = 'scenario' AND r.scenario IN ({0})))%s ORDER BY r.rowid LIMIT 40".format(ph) % where,
                                   list(toks) * 6 + args):
                found.append(row)
                by[row["id"]] = ["exact"]
        expr = T.fts_query(q)
        relaxed = None
        if expr:
            rows = list(con.execute("SELECT r.* FROM record_fts f JOIN record r ON r.id = f.id WHERE record_fts MATCH ?%s "
                                    "ORDER BY bm25(record_fts) LIMIT 60" % where, [expr] + args))
            if not rows and where:
                rows = list(con.execute("SELECT r.* FROM record_fts f JOIN record r ON r.id = f.id WHERE record_fts MATCH ? "
                                        "ORDER BY bm25(record_fts) LIMIT 60", [expr]))
                relaxed = "filters dropped: nothing matched them"
            for row in rows:
                if row["id"] not in by:
                    found.append(row)
                    by[row["id"]] = ["bm25"]
        if self.cfg.get(material, {}).get("rerank") and len(found) > 2:
            import rerank
            exact = [r for r in found if by[r["id"]] == ["exact"]]
            rest = [r for r in found if r not in exact][:40]
            order = rerank.order(q, [r["verbal"] for r in rest], material)
            found = exact + [rest[i] for i in order]
            for r in rest:
                by[r["id"]].append("rerank")
        hits = [self.rec_hit(r, material, i + 1, by[r["id"]]) for i, r in enumerate(found[:k])]
        if relaxed and hits:
            hits[0]["relaxed"] = relaxed
        return hits

    # ---- law
    def law_meta(self, cites):
        if not cites:
            return {}
        con = self.law()
        out = {}
        cites = list(cites)
        for i in range(0, len(cites), 500):
            part = cites[i:i + 500]
            for r in con.execute("SELECT cite_id, doc_id, work, frag, jur, lang, title, label, valid_from, valid_to, parent, chars FROM clause "
                                 "WHERE cite_id IN (%s)" % ",".join("?" * len(part)), part):
                out[r["cite_id"]] = dict(r)
        return out

    def law_keep(self, m, filters):
        jur = (filters.get("jur") or "").lower()
        if jur and m["jur"].lower() != jur and not (m["doc_id"].startswith("treaty.") and jur in m["doc_id"].split(".")[1].split("-")):
            return False
        if filters.get("lang") and (m["lang"] or "")[:2] != filters["lang"][:2]:
            return False
        if filters.get("doc") and m["doc_id"] != filters["doc"] and not m["doc_id"].startswith(filters["doc"] + "."):
            return False
        as_of = filters.get("as_of")
        if as_of and ((m["valid_from"] and m["valid_from"] > as_of) or (m["valid_to"] and m["valid_to"] <= as_of)):
            return False
        return True

    def exact_law(self, q):
        """cite ids, param ids, decision ids, rule ids and article references with a named act."""
        con = self.law()
        out = []
        for cid in re.findall(r"[a-z][a-z0-9\-]*(?:\.[\w\-]+)+#[\w.()\-]+", q):
            if con.execute("SELECT 1 FROM clause WHERE cite_id = ?", (cid,)).fetchone():
                out.append(cid)
        L = self.lib()
        for pid in re.findall(r"\b[a-z]{2}(?:-[a-z]{2})?\.[a-z_]+(?:\.[a-z0-9_]+)+\b", q):
            p = L["params"].get(pid)
            if p and p.get("cite_id"):
                out.append(p["cite_id"])
            r = self.rules().get(pid)
            if r:
                out += [c for c in r.get("cite_ids", "").split(";") if c]
        for did in re.findall(r"\bD-[a-z]{2}-\d+\b", q):
            out += [d["cite_id"] for d in L["decision"] if d["id"] == did and d.get("cite_id")]
        flat = re.sub(r"\s+", "", q).lower()
        doc = None
        for a, d in sorted(((r["alias"], r["doc_id"]) for r in con.execute("SELECT alias, doc_id FROM alias")), key=lambda x: -len(x[0])):
            if len(a) >= 4 and a in flat:
                doc = d
                break
        if doc:
            m = re.search(r"第([一二三四五六七八九十百零〇\d]+)条(?:第([一二三四五六七八九十百零〇\d]+)[款項])?", q)
            frags = []
            if m:
                art = T.cn2int(m.group(1))
                frags = (["%s.%s" % (art, T.cn2int(m.group(2)))] if m.group(2) else []) + [str(art)]
            m = re.search(r"(?:section|s\.)\s?(\d+[A-Z]{0,4})", q, re.I)
            if m:
                frags.append("s" + m.group(1))
            m = re.search(r"article\s(\d+[A-Z]?)(?:\s?\((\d+)\))?", q, re.I)
            if m:
                frags = (["%s.%s" % (m.group(1), m.group(2))] if m.group(2) else []) + [m.group(1)] + frags
            for f in frags:
                if con.execute("SELECT 1 FROM clause WHERE cite_id = ?", ("%s#%s" % (doc, f),)).fetchone():
                    out.append("%s#%s" % (doc, f))
                    break
        return list(dict.fromkeys(out))

    def bm25_law(self, q, n=200):
        expr = T.fts_query(q)
        if not expr:
            return []
        con = self.law()
        return [(r["unit_id"], r["cite_id"]) for r in con.execute(
            "SELECT f.unit_id, u.cite_id FROM unit_fts f JOIN unit u ON u.unit_id = f.unit_id WHERE unit_fts MATCH ? "
            "ORDER BY bm25(unit_fts, 0.0, 0.6, 1.0) LIMIT ?", (expr, n))]

    def dense_law(self, q, n=200):
        import numpy as np
        if self._vec is None:
            vp, ip = self.db / "index" / "vec.npy", self.db / "index" / "vec_ids.txt"
            if not (vp.exists() and ip.exists()):
                self._vec = False
            else:
                ids = ip.read_text(encoding="utf-8").split("\n")
                mat = np.load(vp, mmap_mode="r")
                self._vec = (ids, mat)
        if self._vec is False:
            return []
        if self._dense is None:
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            from sentence_transformers import SentenceTransformer
            import torch
            m = SentenceTransformer("BAAI/bge-m3", device="cuda" if torch.cuda.is_available() else "cpu")
            if torch.cuda.is_available():
                m.half()
            self._dense = m
        ids, mat = self._vec
        qv = self._dense.encode([q], normalize_embeddings=True)[0].astype("float32")
        scores = np.empty(len(ids), dtype="float32")
        step = 20000
        for i in range(0, len(ids), step):
            scores[i:i + step] = np.asarray(mat[i:i + step], dtype="float32") @ qv
        top = np.argpartition(-scores, min(n, len(ids) - 1))[:n]
        top = top[np.argsort(-scores[top])]
        return [(ids[i], ids[i].rsplit("@", 1)[0]) for i in top]

    def expand_law(self, seeds, n=50):
        """Personalized PageRank over explicit edges around the seed clauses (2 hops), node specificity down-weighted."""
        import networkx as nx
        con = self.law()
        g = nx.Graph()
        frontier = set(seeds)
        for _ in range(2):
            nxt = set()
            for node in list(frontier)[:200]:
                for r in con.execute("SELECT src, dst FROM edge WHERE (src = ? OR dst = ?) AND kind IN ('contains','cites','same_provision','co_cited')",
                                     (node, node)):
                    g.add_edge(r["src"], r["dst"])
                    nxt.update((r["src"], r["dst"]))
            frontier = nxt - frontier
        if g.number_of_nodes() == 0:
            return []
        pers = {s: 1.0 / (i + 1) for i, s in enumerate(seeds) if s in g}
        if not pers:
            return []
        pr = nx.pagerank(g, alpha=0.5, personalization=pers)
        spec = {c: v / (1.0 + g.degree(c)) ** 0.5 for c, v in pr.items()}
        return [c for c, _ in sorted(spec.items(), key=lambda kv: (-kv[1], kv[0])) if c not in seeds][:n]

    def law_search(self, q, filters, k, cfg=None):
        cfg = dict(self.cfg["law"], **(cfg or {}))
        qlang = T.lang_of(q)
        ranks, best_unit = {}, {}

        def add(channel, pairs):
            seen = set()
            for uid, cite in pairs:
                if cite in seen:
                    continue
                seen.add(cite)
                ranks.setdefault(cite, {})[channel] = len(seen)
                best_unit.setdefault(cite, uid)

        tried = []
        if cfg.get("bm25", True):
            add("bm25", self.bm25_law(q))
            tried.append("bm25")
        if cfg.get("dense"):
            try:
                add("dense", self.dense_law(q))
                tried.append("dense")
            except Exception as e:                               # noqa: BLE001  (no GPU, no weights: lexical only)
                tried.append("dense unavailable: %s" % type(e).__name__)
        exact = self.exact_law(q)
        meta = self.law_meta(set(ranks) | set(exact))

        def fused():
            sc = {c: sum(1.0 / (RRF_K + rk) for name, rk in ch.items()) for c, ch in ranks.items()}
            return sorted(sc, key=lambda c: (-sc[c], c)), sc

        order, scores = fused()
        if cfg.get("graph") and order:
            seeds = [c for c in order[:10] if c in meta and self.law_keep(meta[c], filters)]
            add("graph", [(None, c) for c in self.expand_law(seeds)])
            meta.update(self.law_meta(set(ranks) - set(meta)))
            sc = {c: sum((0.5 if name == "graph" else 1.0) / (RRF_K + rk) for name, rk in ch.items()) for c, ch in ranks.items()}
            order = sorted(sc, key=lambda c: (-sc[c], c))
        if cfg.get("balance"):
            same = [c for c in order if c in meta and (meta[c]["lang"] or "")[:2] == qlang]
            other = [c for c in order if c in meta and (meta[c]["lang"] or "")[:2] != qlang and set(ranks[c]) - {"bm25"}]
            merged = []
            for a, b in zip(same, other):
                merged += [a, b]
            longer = same if len(same) > len(other) else other
            merged += longer[min(len(same), len(other)):]
            merged += [c for c in order if c not in set(merged)]
            order = merged
        order = [c for c in order if c in meta and self.law_keep(meta[c], filters)]
        if cfg.get("rerank") and len(order) > 2:
            try:
                import rerank
                pool = order[:50]
                texts = [self.unit_text(best_unit.get(c), c, 700, meta) for c in pool]
                idx = rerank.order(q, texts, "law")
                order = [pool[i] for i in idx] + order[50:]
                for c in pool:
                    ranks[c]["rerank"] = idx.index(pool.index(c)) + 1
            except Exception as e:                               # noqa: BLE001
                tried.append("rerank unavailable: %s" % type(e).__name__)
        exact = [c for c in exact if c in meta and self.law_keep(meta[c], filters)]
        final = exact + [c for c in order if c not in exact]
        hits = []
        for i, c in enumerate(final[:k]):
            m = meta[c]
            h = {"id": c, "scope": "law", "unit": best_unit.get(c), "title": m["title"], "label": m["label"], "lang": m["lang"],
                 "valid_from": m["valid_from"], "valid_to": m["valid_to"], "parent": m["parent"],
                 "text": self.unit_text(best_unit.get(c), c, HIT_TEXT, meta), "chars": m["chars"], "rank": i + 1,
                 "found_by": (["exact"] if c in exact else []) + sorted(ranks.get(c, {}))}
            if filters.get("as_of"):
                h["validity"] = "valid" if m["valid_from"] else "unknown (no effective date stated)"
            same = [r["o"] for r in self.law().execute(
                "SELECT CASE WHEN src = ? THEN dst ELSE src END AS o FROM edge WHERE kind = 'same_provision' AND (src = ? OR dst = ?)", (c, c, c))]
            if same:
                h["same_provision"] = same[:4]
            hits.append(h)
        out = {"hits": hits, "tried": tried}
        if filters.get("as_of") and not hits and ranks:
            out["not_covered"] = "no clause among the candidates is in force on %s" % filters["as_of"]
        return out

    def unit_text(self, uid, cite, cap, meta=None):
        con = self.law()
        if uid:
            r = con.execute("SELECT u.start, u.\"end\", c.text FROM unit u JOIN clause c ON c.cite_id = u.cite_id WHERE u.unit_id = ?", (uid,)).fetchone()
            if r:
                t = r["text"][r["start"]:r["end"]]
                return t if len(t) <= cap else t[:cap - 1] + "…"
        r = con.execute("SELECT text FROM clause WHERE cite_id = ?", (cite,)).fetchone()
        t = r["text"] if r else ""
        return t if len(t) <= cap else t[:cap - 1] + "…"

    # ------------------------------------------------------------ list
    LAW_KINDS = ("params", "absences", "treaties", "jurisdictions", "blocked", "decisions", "docs")
    PRODUCT_KINDS = {"structures": "structure", "branches": "branch", "hops": "hop", "cells": "cell", "rules": "rule", "points": "point",
                     "scenarios": "scenario", "open_items": "open_item", "requirements": "requirement", "transfers": "transfer",
                     "exposures": "delta", "deltas": "delta", "penalties": "penalty", "past_payments": "past_payment", "gaps": "gap",
                     "brief": "brief", "diff": "diff", "input": "input", "basis": "basis"}
    CASE_KINDS = {"facts": "fact", "sources": "source", "dialogue": "dialogue", "answers": "answer", "notes": "note", "documents": "document",
                  "pages": "page", "cells_case": "cell", "handoff": "handoff", "to_collect": "to_collect", "constraints": "constraints"}

    def list(self, kind, filters=None, k=20, cursor=0, max_chars=BUDGET):
        filters = dict(filters or {})
        k = max(1, min(int(k or 20), 200))
        cursor = max(0, int(cursor or 0))
        if kind in self.LAW_KINDS:
            rows = self.list_law(kind, filters)
        elif kind in self.PRODUCT_KINDS:
            case_id, run_id = self.resolve_run(filters)
            if not (case_id and run_id):
                return err("invalid", "%s needs case_id or run_id in filters" % kind)
            con, e = self.products(case_id, run_id)
            if e:
                return e
            where, args = self.rec_where({k2: v for k2, v in filters.items() if k2 != "type"})
            order = "r.rank IS NULL, r.rank, r.rowid" if kind == "structures" else "r.rowid"
            rows = [{"id": r["id"], "card": r["card"]} for r in con.execute(
                "SELECT r.id, r.card FROM record r WHERE r.type = ?%s ORDER BY %s" % (where, order), [self.PRODUCT_KINDS[kind]] + args)]
        elif kind in self.CASE_KINDS or kind == "cells" and filters.get("doc"):
            case_id = filters.get("case_id")
            if not case_id:
                return err("invalid", "%s needs case_id in filters" % kind)
            con, e = self.casefile(case_id)
            if e:
                return e
            where, args = self.rec_where({k2: v for k2, v in filters.items() if k2 != "type"})
            rows = [{"id": r["id"], "card": r["card"]} for r in con.execute(
                "SELECT r.id, r.card FROM record r WHERE r.type = ?%s ORDER BY r.rowid" % where, [self.CASE_KINDS.get(kind, "cell")] + args)]
        else:
            return err("invalid", "kind is one of %s" % ", ".join(list(self.LAW_KINDS) + list(self.PRODUCT_KINDS) + list(self.CASE_KINDS)))
        page, used = [], 0
        for row in rows[cursor:cursor + k]:
            if used + size(row) > max_chars and page:
                break
            used += size(row)
            page.append(row)
        nxt = cursor + len(page)
        out = {"kind": kind, "filters": filters, "total": len(rows), "items": page}
        if nxt < len(rows):
            out["cursor"] = nxt
        return self.tick("list", {"kind": kind, "filters": filters, "cursor": cursor}, out)

    def list_law(self, kind, f):
        L = self.lib()
        jur = (f.get("jur") or "").lower()
        scope_ok = lambda s: not jur or s == jur or s.startswith(jur + "-") or s.endswith("-" + jur)
        if kind == "params":
            rows = [p for p in L["param"] if scope_ok(p["scope"]) and (not f.get("slot") or p["slot"] == f["slot"])
                    and (not f.get("subject") or p["subject"] in (f["subject"], "all"))]
            return [{"id": "param:" + p["param_id"], "value": p["value"], "unit": p["unit"], "cite_id": p["cite_id"],
                     "effective": "%s..%s" % (p["effective_from"], p["effective_to"]), "superseded_by": p.get("superseded_by", "")} for p in rows]
        if kind == "absences":
            return [{"id": "decision:" + d["id"], "jur": d.get("jur"), "slot": d.get("slot"), "statement": d.get("statement", "")[:200]}
                    for d in L["decision"] if ".absent." in d["id"] and (not jur or d.get("jur") == jur) and (not f.get("slot") or d.get("slot") == f["slot"])]
        if kind == "decisions":
            return [{"id": "decision:" + d["id"], "cite_id": d.get("cite_id"), "statement": d.get("statement", "")[:200]} for d in L["decision"]
                    if ".absent." not in d["id"] and (not jur or d.get("jur") == jur)]
        if kind == "treaties":
            b = (f.get("jur_b") or "").lower()
            rows = []
            for t in L["treaty"]:
                x, _, y = t["pair"].partition("-")
                if (not jur or jur in (x, y)) and (not b or b in (x, y)):
                    d = L["docs"].get(t["doc_id"], {})
                    rows.append(dict(t, id="doc:" + t["doc_id"], title=d.get("title", ""), effective="%s..%s" % (d.get("effective_from", ""), d.get("effective_to", ""))))
            return rows
        if kind == "jurisdictions":
            return [dict(j, id="jurisdiction:" + j.get("code", "")) for j in L["jurisdiction"]]
        if kind == "blocked":
            return [dict(b, id="blocked:" + b.get("doc_id", b.get("id", ""))) for b in L["blocked"]]
        if kind == "docs":
            return [{"id": "doc:" + d["id"], "jur": d["jur"], "type": d["type"], "title": d["title"], "lang": d["lang"],
                     "effective": "%s..%s" % (d["effective_from"], d["effective_to"])} for d in L["doc"]
                    if (not jur or d["jur"] == jur) and (not f.get("type") or d["type"] == f["type"])]
        return []

    # ------------------------------------------------------------ get
    def record_owner(self, rid):
        """(scope, case_id, run_id, connection) of a product or case record id."""
        head = rid.split(":", 1)[0]
        if RUN_RE.match(head):
            case_id = self.case_of_run(head)
            if not case_id:
                return None, err("not_found", "no run %s" % head)
            con, e = self.products(case_id, head)
            return ("products", case_id, head, con), e
        if (self.cases / head / "intake").is_dir():
            con, e = self.casefile(head)
            return ("case", head, None, con), e
        return None, None

    def page(self, text, offset, max_chars):
        offset = max(0, int(offset or 0))
        max_chars = int(max_chars or GET_PAGE)
        part = text[offset:offset + max_chars]
        out = {"text": part, "offset": offset, "total_chars": len(text)}
        if offset + len(part) < len(text):
            out["next_offset"] = offset + len(part)
        return out

    def get(self, id, offset=0, max_chars=GET_PAGE):
        id = str(id or "").strip()
        if not id:
            return err("invalid", "give an id")
        self.seen.setdefault(id, self.calls + 1)
        L = self.lib()
        if id.startswith("param:"):
            p = L["params"].get(id[6:])
            if not p:
                return err("not_found", "no parameter %s" % id[6:])
            chain, seen, cur = [], set(), p
            while cur and cur["param_id"] not in seen:
                seen.add(cur["param_id"])
                chain.append(dict(cur))
                cur = L["params"].get(cur["superseded_by"]) if cur.get("superseded_by") else None
            back = [dict(q) for q in L["param"] if q.get("superseded_by") == p["param_id"]]
            return self.tick("get", {"id": id}, {"id": id, "param": dict(p), "versions": back + chain})
        if id.startswith("doc:"):
            d = L["docs"].get(id[4:])
            if not d:
                return err("not_found", "no document %s" % id[4:])
            n = self.law().execute("SELECT count(*) FROM clause WHERE doc_id = ?", (id[4:],)).fetchone()[0]
            return self.tick("get", {"id": id}, {"id": id, "doc": dict(d), "clauses": n})
        if id.startswith("decision:"):
            rows = [dict(d) for d in L["decision"] if d["id"] == id[9:]]
            return self.tick("get", {"id": id}, {"id": id, "decision": rows}) if rows else err("not_found", "no decision %s" % id[9:])
        if id.startswith("rule:"):
            r = self.rules().get(id[5:])
            return self.tick("get", {"id": id}, {"id": id, "rule": dict(r)}) if r else err("not_found", "no rule %s" % id[5:])
        if id.startswith("file:"):
            rel = id[5:].replace("\\", "/").lstrip("/")
            why = self.denied(rel)
            if why:
                return err("forbidden", why)
            p = (self.cases / rel).resolve()
            try:
                p.relative_to(self.cases)
            except ValueError:
                return err("forbidden", "file ids are relative to the cases folder: file:<case_id>/<path>")
            if not p.is_file():
                return err("not_found", "no file %s" % rel)
            if p.suffix.lower() in (".pdf", ".png", ".jpg", ".jpeg"):
                return err("invalid", "a document is read by page: get('<case_id>:page:<doc>:<n>') or the host's Read")
            return self.tick("get", {"id": id}, dict({"id": id}, **self.page(p.read_text(encoding="utf-8", errors="replace"), offset, max_chars)))
        unit = None
        if "@" in id and CITE_RE.match(id.split("@")[0]):
            id, unit = id.split("@")[0], id
        if CITE_RE.match(id):
            con = self.law()
            r = con.execute("SELECT * FROM clause WHERE cite_id = ?", (id,)).fetchone()
            if not r:
                return err("not_found", "no clause %s (it may not be in the library)" % id)
            sib = [x["cite_id"] for x in con.execute("SELECT cite_id FROM clause WHERE doc_id = ? ORDER BY rowid", (r["doc_id"],))]
            i = sib.index(id)
            out = {"id": id, "doc_id": r["doc_id"], "title": r["title"], "label": r["label"], "lang": r["lang"],
                   "valid_from": r["valid_from"], "valid_to": r["valid_to"], "parent": r["parent"],
                   "prev": sib[i - 1] if i > 0 else None, "next": sib[i + 1] if i + 1 < len(sib) else None}
            if unit:
                u = con.execute("SELECT start, \"end\" FROM unit WHERE unit_id = ?", (unit,)).fetchone()
                if u and not offset:
                    offset = u["start"]
            out.update(self.page(r["text"], offset, max_chars))
            return self.tick("get", {"id": id}, out)
        owner, e = self.record_owner(id)
        if e:
            return e
        if owner:
            scope, case_id, run_id, con = owner
            r = con.execute("SELECT * FROM record WHERE id = ?", (id,)).fetchone()
            if not r:
                near = [x["id"] for x in con.execute("SELECT id FROM record WHERE id LIKE ? LIMIT 8", (id.rsplit(":", 1)[0] + ":%",))]
                return err("not_found", "no record %s" % id, similar=near)
            out = {"id": id, "scope": scope, "type": r["type"], "file": r["file"]}
            out.update(self.page(r["full"], offset, max_chars))
            return self.tick("get", {"id": id}, out)
        return err("not_found", "unknown id %s: ids are cite_ids (doc#frag), param:/doc:/decision:/rule:/file: ids, or record ids <run_id>:<type>:<key> / <case_id>:<type>:<key>" % id)

    # ------------------------------------------------------------ expand
    def expand(self, id, kinds=None, depth=1, k=20, max_chars=BUDGET):
        id = str(id or "").strip()
        depth = max(1, min(int(depth or 1), 2))
        k = max(1, min(int(k or 20), 30))
        kinds = set(kinds or [])
        frontier, seen, groups = [id], {id}, {}
        for _ in range(depth):
            nxt = []
            for node in frontier:
                for nb, kind in self.neighbours(node):
                    if (kinds and kind not in kinds) or nb in seen:
                        continue
                    seen.add(nb)
                    groups.setdefault(kind, []).append(nb)
                    nxt.append(nb)
            frontier = nxt[:k]
        out, used = {"id": id, "neighbours": {}}, 0
        for kind, ids in groups.items():
            for nb in ids[:k]:
                c = self.card_of(nb)
                if used + size(c) > max_chars and used:
                    out["more"] = "narrow kinds or depth"
                    break
                used += size(c)
                out["neighbours"].setdefault(kind, []).append(c)
        return self.tick("expand", {"id": id, "kinds": sorted(kinds), "depth": depth}, out)

    def neighbours(self, node):
        if CITE_RE.match(node) or node.startswith(("rule:", "param:", "decision:")):
            con = self.law()
            out = []
            for r in con.execute("SELECT src, dst, kind FROM edge WHERE src = ? OR dst = ? LIMIT 200", (node, node)):
                other = r["dst"] if r["src"] == node else r["src"]
                kind = r["kind"] if r["src"] == node else ("cited_by" if r["kind"] == "cites" else "in" if r["kind"] == "contains" else r["kind"])
                out.append((other, kind))
            return out
        owner, e = self.record_owner(node)
        if not owner or e:
            return []
        con = owner[3]
        return [(r["dst"], r["kind"]) for r in con.execute("SELECT dst, kind FROM edge WHERE src = ?", (node,))] + \
               [(r["src"], "of_" + r["kind"]) for r in con.execute("SELECT src, kind FROM edge WHERE dst = ?", (node,))]

    def card_of(self, nid):
        if CITE_RE.match(nid):
            m = self.law_meta([nid]).get(nid)
            if not m:
                return {"id": nid, "note": "not in the library"}
            return {"id": nid, "scope": "law", "title": m["title"], "label": m["label"], "text": self.unit_text(None, nid, 240)}
        if nid.startswith("rule:"):
            r = self.rules().get(nid[5:], {})
            return {"id": nid, "condition": r.get("condition", "")[:200], "effect": r.get("effect"), "cite_ids": r.get("cite_ids")}
        if nid.startswith("param:"):
            p = self.lib()["params"].get(nid[6:], {})
            return {"id": nid, "value": p.get("value"), "unit": p.get("unit"), "cite_id": p.get("cite_id")}
        if nid.startswith("decision:"):
            return {"id": nid}
        owner, e = self.record_owner(nid)
        if owner and not e:
            r = owner[3].execute("SELECT type, card FROM record WHERE id = ?", (nid,)).fetchone()
            if r:
                return {"id": nid, "type": r["type"], "card": r["card"]}
        return {"id": nid}

    # ------------------------------------------------------------ ground
    def text_of(self, id):
        """(text, derived) of an id for grounding: a clause, a record (its verbatim fields) or a document page."""
        if CITE_RE.match(id.split("@")[0]):
            r = self.law().execute("SELECT text FROM clause WHERE cite_id = ?", (id.split("@")[0],)).fetchone()
            return (r["text"], "library") if r else (None, None)
        owner, e = self.record_owner(id)
        if owner and not e:
            r = owner[3].execute("SELECT full FROM record WHERE id = ?", (id,)).fetchone()
            if not r:
                return None, None
            full = json.loads(r["full"])
            if isinstance(full, dict) and "text" in full:
                return full["text"], full.get("derived", "case")
            if isinstance(full, dict) and "quote" in full:
                return full["quote"], "case"
            return json.dumps(full, ensure_ascii=False), "products"
        return None, None

    def ground(self, id, quote):
        text, derived = self.text_of(str(id or ""))
        if text is None:
            return err("not_found", "nothing to ground against: %s" % id)
        a, b, n = T.anchor(text, quote)
        if a is not None:
            out = {"id": id, "match": "exact", "start": a, "end": b, "occurrences": n, "text": text[a:b]}
        elif derived == "ocr":
            a, b, ratio = T.approx_anchor(text, quote)
            out = {"id": id, "match": "approximate" if a is not None else "none", "derived": "ocr"}
            if a is not None:
                out.update(start=a, end=b, text=text[a:b], note="OCR text: review judges whether the quote and the matched span agree")
        else:
            out = {"id": id, "match": "none"}
        return self.tick("ground", {"id": id}, out)

    # ------------------------------------------------------------ pack
    def pack(self, case_id, node):
        import pack as P
        P.CASES = self.cases
        try:
            path, ids = P.build(self, case_id, node)
        except Exception as e:                                   # noqa: BLE001
            return err("internal", "%s: %s" % (type(e).__name__, e))
        return self.tick("pack", {"case_id": case_id, "node": node}, {"path": str(path), "items": ids[:80], "total_items": len(ids)})

    # ------------------------------------------------------------ cite_check
    def ref_texts(self, case_id, row):
        """The texts and figures a sources row points at: (resolved?, set of numbers, text)."""
        ref, kind = str(row.get("ref", "")).strip(), row.get("kind")
        if kind in ("url", "tool"):                             # a web page or a tool call: not resolvable offline, its claim counts
            return "external", T.numbers(row.get("claim", "")), ""
        if kind == "name":
            return True, set(), ""
        nums, texts, ok = set(), [], False
        for token in re.split(r"[;,]\s*|\s+(?=intake/|report/)", ref):
            token = token.strip()
            if not token:
                continue
            base = token.split(" ")[0]
            if base.startswith("file:"):                         # a text file of the case, read through get
                g = self.get(base, 0, 10 ** 7)
                if "error" not in g:
                    ok = True
                    t = g.get("text", "")
                    try:
                        nums |= T.json_numbers(json.loads(t))
                    except ValueError:
                        nums |= T.numbers(t)
                    continue
            text, _ = self.text_of(base)
            if text is None and base.startswith(("param:", "rule:", "decision:", "doc:")):
                g = self.get(base)
                text = json.dumps(g, ensure_ascii=False) if "error" not in g else None
            if text is None:
                p = self.cases / case_id / base.split("#")[0]
                if p.is_file() and p.suffix == ".json":
                    try:
                        data = json.loads(p.read_text(encoding="utf-8"))
                        nums |= T.json_numbers(data)
                        ok = True
                        continue
                    except ValueError:
                        pass
                if p.is_file() and p.suffix in (".md", ".txt"):
                    text = p.read_text(encoding="utf-8", errors="replace")
                elif p.is_file():
                    ok = True                                    # a document: its page text is in the case index when parsed
                    continue
                m = re.match(r"(?:intake/)?documents/(S\d+[^/\s]*)", base) or re.match(r"(S\d+(?:_p\d+)?)\b", base)
                if text is None and m:
                    ok = True
                    continue
            if text is not None:
                ok = True
                texts.append(text)
                nums |= T.numbers(text)
        return ok, nums, "\n".join(texts)

    def cite_check(self, case_id, run_id, target="draft"):
        rd = self.cases / case_id / "report" / run_id
        md = rd / ("briefing.md" if target == "draft" else "briefing.polished.md")
        sj = rd / ("briefing.sources.json" if target == "draft" else "briefing.polished.sources.json")
        if not md.exists() or not sj.exists():
            return err("not_found", "no %s with a sources table for run %s" % (target, run_id))
        why = self.denied("%s/report/%s/%s" % (case_id, run_id, md.name))
        if why:
            return err("forbidden", why)
        try:
            data = json.loads(sj.read_text(encoding="utf-8"))
        except ValueError as e:
            return err("invalid", "sources table is not JSON: %s" % e)
        rows = data if isinstance(data, list) else data.get("sources", [])
        unresolved, covered, external = [], set(), 0
        for r in rows:
            ok, nums, _ = self.ref_texts(case_id, r)
            if ok == "external":
                external += 1
            elif not ok:
                unresolved.append({"id": r.get("id"), "ref": str(r.get("ref"))[:120]})
            covered |= nums
            covered |= T.numbers(str(r.get("claim", "")))
        text = md.read_text(encoding="utf-8")
        body = re.split(r"(?m)^#{1,3}\s+(?:附录\s*B|Appendix\s*B)\b", text)[0]
        figures = []
        for line in body.splitlines():
            if re.match(r"^\s*(?:\*\*)?(?:Date|日期)", line) or "Internal reference" in line:
                continue
            for m in re.finditer(r"(?<![\w.\-/])(\d{1,3}(?:,\d{3})+|\d{4,})(?:\.\d+)?(?![\w\-/])|(\d+(?:\.\d+)?)\s?%", line):
                raw = m.group(0)
                if m.group(1) and re.fullmatch(r"(19|20)\d\d", m.group(1)):
                    continue                                     # a year
                val = float((m.group(1) or m.group(2)).replace(",", ""))
                scaled = {val, val * 1e6} if re.match(r"\s?(million|m\b)", line[m.end():m.end() + 9], re.I) else {val}
                if not scaled & covered:
                    figures.append({"figure": raw.strip(), "line": line.strip()[:160]})
        uncovered = []
        for f in figures:
            if f["figure"] not in {u["figure"] for u in uncovered}:
                uncovered.append(f)
        out = {"case_id": case_id, "run_id": run_id, "target": target, "rows": len(rows), "external_rows": external,
               "unresolved_refs": unresolved, "uncovered_figures": uncovered[:40]}
        return self.tick("cite_check", {"case_id": case_id, "run_id": run_id}, out)
