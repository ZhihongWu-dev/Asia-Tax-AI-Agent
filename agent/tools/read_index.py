#!/usr/bin/env python
"""Indexes of the retrieval layer for a run's products and for a case file (agent/retrieval_spec.en.md §5, §6).

  python agent/tools/read_index.py products cases/<case>/intake/products/<run_id>
  python agent/tools/read_index.py case cases/<case> [--ocr]

Products: typed records with stable ids <run_id>:<type>:<key>, filter fields, a template verbalisation (matching only), a
compact card and the full record, plus the edges of the products graph; in <products>/index/records.sqlite. Values are
copied from the products, never recomputed. Case file: facts, sources, dialogue, answers, notes, handoff and the parsed
documents (pages, table cells) in <case>/intake/index/case.sqlite. Deterministic: the same files give the same index.
"""
import csv
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from textutil import fts_tokens  # noqa: E402

INDEX_VERSION = "4"
CARD_MAX = 600
VERBAL_MAX = 300
SCHEMA = """
CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE record (id TEXT PRIMARY KEY, type TEXT NOT NULL, key TEXT NOT NULL, cand TEXT, branch TEXT, jur TEXT, slot TEXT,
                     point TEXT, scenario TEXT, doc TEXT, page INTEGER, rank INTEGER, verbal TEXT, card TEXT, full TEXT, file TEXT);
CREATE TABLE edge (src TEXT NOT NULL, dst TEXT NOT NULL, kind TEXT NOT NULL);
CREATE VIRTUAL TABLE record_fts USING fts5(id UNINDEXED, body, tokenize='unicode61 remove_diacritics 2');
CREATE INDEX record_type ON record(type);
CREATE INDEX edge_src ON edge(src);
CREATE INDEX edge_dst ON edge(dst);
"""


def jload(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def money(x):
    try:
        return "{:,.0f}".format(float(x))
    except (TypeError, ValueError):
        return "open"


def span(r):
    """{'floor','ceiling'} -> '700,000' or '700,000-1,400,000'."""
    if not isinstance(r, dict):
        return money(r)
    a, b = r.get("floor"), r.get("ceiling")
    if a is None or b is None:
        return "open"
    return money(a) if abs(float(a) - float(b)) < 0.5 else "%s-%s" % (money(a), money(b))


def card(obj):
    """Fields and values as they are, cut at CARD_MAX; the full record is in get()."""
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return s if len(s) <= CARD_MAX else s[:CARD_MAX - 1] + "…"


JUR = {"cn": "Mainland China Chinese PRC", "hk": "Hong Kong", "sg": "Singapore", "jp": "Japan Japanese", "th": "Thailand Thai",
       "kr": "Korea", "id": "Indonesia", "in": "India", "my": "Malaysia", "vn": "Vietnam"}
PRED = {"bo": "beneficial owner ownership", "parent_bo": "beneficial ownership of the parent", "ppt": "principal purpose test treaty abuse",
        "gaar": "general anti-avoidance rule", "fsie_mpr": "foreign-sourced income exemption main purpose rule", "substance": "economic substance",
        "lob": "limitation on benefits"}


def plain(text):
    """Plain words for the codes in a text (sg:company -> Singapore company, bo@cn -> beneficial owner Mainland China)."""
    out = []
    for jur, subj in re.findall(r"([a-z]{2}):(company|individual)", text or ""):
        out.append("%s %s" % (JUR.get(jur, jur), subj))
    for pred, jur in re.findall(r"([a-z_]+)@([a-z]{2})", text or ""):
        out.append("%s %s" % (PRED.get(pred, pred.replace("_", " ")), JUR.get(jur, jur)))
    for w in ("wait_months", "transfer", "indirect", "acquire"):
        if w in (text or ""):
            out.append({"wait_months": "wait holding period months", "transfer": "direct share transfer restructuring",
                        "indirect": "indirect transfer", "acquire": "acquisition"}[w])
    return " ".join(dict.fromkeys(out))


def short(text, n=VERBAL_MAX):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= n else text[:n - 1] + "…"


class Writer:
    def __init__(self, path, meta):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        if tmp.exists():
            tmp.unlink()
        self.tmp = tmp
        self.con = sqlite3.connect(str(tmp))
        self.con.executescript(SCHEMA)
        self.con.executemany("INSERT INTO meta VALUES (?, ?)", sorted(meta.items()))
        self.ids = set()
        self.edges = set()

    def add(self, rid, type_, key, verbal, card_obj, full_obj, file="", **f):
        if rid in self.ids:
            return
        self.ids.add(rid)
        verbal = short(verbal)
        self.con.execute("INSERT INTO record VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                         (rid, type_, key, f.get("cand"), f.get("branch"), f.get("jur"), f.get("slot"), f.get("point"), f.get("scenario"),
                          f.get("doc"), f.get("page"), f.get("rank"), verbal, card(card_obj),
                          json.dumps(full_obj, ensure_ascii=False, separators=(",", ":")), file))
        words = rid.split(":", 1)[-1] + " " + verbal + " " + f.get("extra", "")
        self.con.execute("INSERT INTO record_fts VALUES (?, ?)", (rid, fts_tokens(words + " " + plain(words))))

    def edge(self, src, dst, kind):
        if src and dst and (src, dst, kind) not in self.edges:
            self.edges.add((src, dst, kind))
            self.con.execute("INSERT INTO edge VALUES (?,?,?)", (src, dst, kind))

    def close(self):
        self.con.commit()
        self.con.close()
        if self.path.exists():
            self.path.unlink()
        self.tmp.rename(self.path)


def fingerprint(paths):
    h = hashlib.sha256(INDEX_VERSION.encode())
    for p in sorted(paths, key=str):
        p = Path(p)
        if p.is_file():
            st = p.stat()
            h.update(("%s|%d|%d" % (p.name, st.st_size, int(st.st_mtime))).encode())
    return h.hexdigest()[:16]


def stale(index_path, fp):
    try:
        con = sqlite3.connect(str(index_path))
        row = con.execute("SELECT v FROM meta WHERE k = 'fingerprint'").fetchone()
        con.close()
        return not row or row[0] != fp
    except sqlite3.Error:
        return True


# ------------------------------------------------------------ products
def rules_table():
    p = PROJECT / "rule" / "rule.csv"
    with p.open(encoding="utf-8-sig", newline="") as f:
        return {r["rule_id"]: r for r in csv.DictReader(f)}


def product_files(pd):
    names = ["paths.json", "ranking.json", "brief.json", "tax.json", "branches.json", "scenarios.json", "open_items.json", "deltas.json",
             "past_payments.json", "diff.json", "gap.json", "input.json", "version.json"]
    files = [pd / n for n in names]
    for sub in ("hops", "requirements", "transfers", "penalty"):
        files += sorted((pd / sub).glob("*.json")) if (pd / sub).is_dir() else []
    return files


def build_products(pd, force=False):
    """The records index of one run's products; skipped when the files are unchanged. Returns the index path."""
    pd = Path(pd)
    out = pd / "index" / "records.sqlite"
    fp = fingerprint(product_files(pd))
    if out.exists() and not force and not stale(out, fp):
        return out
    run = pd.name
    w = Writer(out, {"fingerprint": fp, "kind": "products", "run_id": run, "index_version": INDEX_VERSION})
    R = lambda t, k: "%s:%s:%s" % (run, t, k)
    get = lambda n: jload(pd / n) if (pd / n).exists() else {}
    paths = {c["cand_id"]: c for c in get("paths.json").get("candidates", [])}
    ranking = {}
    for r in get("ranking.json").get("ranking", []):
        ranking.setdefault(r["cand_id"], r)
    brief = get("brief.json")
    bstruct = {s["cand_id"]: s for s in brief.get("structures", [])}
    tax = get("tax.json")
    ccy = tax.get("currency", "")
    taxes = tax.get("taxes", [])
    rules = rules_table()

    # structures
    for cid, c in paths.items():
        rk, bs = ranking.get(cid, {}), bstruct.get(cid, {})
        if cid == (brief.get("as_is") or {}).get("cand_id"):
            bs = dict(bs, as_is=brief["as_is"])
        fav = (bs.get("all_favourable") or {}).get("amount")
        unf = (bs.get("all_unfavourable") or {}).get("amount")
        sig = "%s | %s | %s" % (">".join(c["path"]), ",".join(sorted(c.get("moves") or [])) or "-", ",".join(sorted(c.get("restructure") or [])) or "-")
        verbal = "structure %s%s: %s; moves %s; restructure %s; rank %s; all favourable %s %s, all against %s; one-off %s%s" % (
            cid, " (current structure)" if c.get("as_is") else "", " > ".join(c["path"]), ", ".join(c.get("moves") or []) or "none",
            ", ".join(c.get("restructure") or []) or "none", rk.get("structure_rank", "-"), span(fav) if fav else "-", ccy,
            span(unf) if unf else "-", span(bs.get("one_off_total")) if bs.get("one_off_total") else "-",
            "; flags " + ", ".join(bs.get("one_off_flags") or []) if bs.get("one_off_flags") else "")
        cardo = {"cand": cid, "path": c["path"], "moves": c.get("moves"), "restructure": c.get("restructure"), "as_is": c.get("as_is"),
                 "signature": sig, "structure_rank": rk.get("structure_rank"), "rank": rk.get("rank"),
                 "all_favourable": fav, "all_unfavourable": unf, "one_off_total": bs.get("one_off_total"), "one_off_flags": bs.get("one_off_flags"),
                 "saving_per_payment": bs.get("saving_per_payment"), "payback_payments": bs.get("payback_payments"), "vs_as_is": bs.get("vs_as_is"), "first_in": bs.get("first_in"),
                 "dominated_by": rk.get("dominated_by")}
        full = {"path": c, "ranking": rk, "brief": bs}
        w.add(R("structure", cid), "structure", cid, verbal, cardo, full, "paths.json", cand=cid, rank=rk.get("structure_rank"),
              extra=" ".join(c["path"]).replace(":", " "))

    # branches and hops
    hops_of = {}
    role = {}
    for cid2, bs2 in bstruct.items():
        for side, word in (("all_favourable", "every point favourable all favourable"), ("all_unfavourable", "every point against all unfavourable worst case")):
            b = (bs2.get(side) or {}).get("branch_id")
            if b:
                role[b] = (role.get(b, "") + " " + word).strip()
    for t in taxes:
        bid, cid = t["branch_id"], t["cand_id"]
        ans = ", ".join("%s=%s" % kv for kv in sorted((t.get("answers_assumed") or {}).items()))
        hop_words = []
        for i, h in enumerate(t.get("hops", [])):
            f, c = h.get("floor") or {}, h.get("ceiling") or {}
            hop_words.append("%s>%s wht %s%% incl %s credit %s rate %s" % (h.get("tail"), h.get("head"), f.get("wht"), f.get("incl"), f.get("credit"), f.get("rate")))
        verbal = "branch %s of %s %s: tax %s %s (%s per 100); answers %s; %s; complete %s" % (
            bid, cid, " > ".join(paths.get(cid, {}).get("path", [])), span(t.get("amount")), ccy, span(t.get("per_100")), ans or "none",
            "; ".join(hop_words), t.get("complete"))
        cardo = {"branch": bid, "cand": cid, "amount": t.get("amount"), "per_100": t.get("per_100"), "answers_assumed": t.get("answers_assumed"),
                 "complete": t.get("complete"), "needs": t.get("needs"), "hops": [{"tail": h.get("tail"), "head": h.get("head"),
                 "floor": {k: (h.get("floor") or {}).get(k) for k in ("wht", "incl", "credit", "rate", "t")}} for h in t.get("hops", [])]}
        if role.get(bid):
            verbal = verbal.replace("branch %s of %s" % (bid, cid), "branch %s of %s (%s)" % (bid, cid, role[bid]), 1)
            cardo["scenario"] = role[bid].split(" all ")[0]
        w.add(R("branch", bid), "branch", bid, verbal, cardo, t, "tax.json", cand=cid, branch=bid)
        w.edge(R("structure", cid), R("branch", bid), "branch")
        hops_of[bid] = t.get("hops", [])
        for i, h in enumerate(t.get("hops", [])):
            hk = "%s/%d" % (bid, i)
            jur = str(h.get("tail", "")).split(":")[0]
            verbal = "hop %d of branch %s: %s > %s; floor %s; ceiling %s" % (i, bid, h.get("tail"), h.get("head"),
                                                                           json.dumps(h.get("floor")), json.dumps(h.get("ceiling")))
            w.add(R("hop", hk), "hop", hk, verbal, h, h, "tax.json", cand=cid, branch=bid, jur=jur)
            w.edge(R("branch", bid), R("hop", hk), "hop")

    # cells of every branch's hops (hops/<branch>.json: per hop, the items of its cells)
    for f in sorted((pd / "hops").glob("*.b*.json")) if (pd / "hops").is_dir() else []:
        bid = f.stem
        cid = bid.split(".")[0]
        items = jload(f).get("items", [])
        for i, cells in enumerate(items):
            for it in cells if isinstance(cells, list) else []:
                sk = it.get("slot_key", "")
                ck = "%s/%d/%s" % (bid, i, sk)
                applied = sorted(set((it.get("rules_applied") or {}).get("floor", []) + (it.get("rules_applied") or {}).get("ceiling", [])))
                verbal = "cell %s of branch %s hop %d: status %s; floor %s; ceiling %s; rules %s; cites %s; assumptions %s; needs %s" % (
                    sk, bid, i, it.get("status"), json.dumps((it.get("floor") or {}).get("value")), json.dumps((it.get("ceiling") or {}).get("value")),
                    ", ".join(applied), ", ".join(it.get("cite_ids") or []), ", ".join(it.get("assumptions") or []),
                    ", ".join("%s %s" % tuple(n[:2]) for n in it.get("needs") or [] if isinstance(n, list) and len(n) >= 2))
                cardo = {k: it.get(k) for k in ("slot_key", "status", "value_kind", "assumptions", "needs", "cite_ids")}
                cardo.update(floor=(it.get("floor") or {}).get("value"), ceiling=(it.get("ceiling") or {}).get("value"), rules=applied)
                w.add(R("cell", ck), "cell", ck, verbal, cardo, it, "hops/%s" % f.name, cand=cid, branch=bid, jur=it.get("jur"), slot=it.get("slot"))
                w.edge(R("hop", "%s/%d" % (bid, i)), R("cell", ck), "cell")
                for rid in applied:
                    w.edge(R("cell", ck), R("rule", rid), "rule")
                for cite in it.get("cite_ids") or []:
                    w.edge(R("cell", ck), cite, "cites")
                for rid in applied:
                    r = rules.get(rid)
                    if not r:
                        continue
                    verbal = "rule %s (%s): if %s then %s; cites %s; %s" % (rid, r["slot_key"], r["condition"], r["effect"], r["cite_ids"], r.get("note", ""))
                    w.add(R("rule", rid), "rule", rid, verbal, {k: r.get(k) for k in ("rule_id", "slot_key", "condition", "effect", "cite_ids", "decision_ids", "note")},
                          dict(r), "rule/rule.csv", jur=rid.split(".")[0].split("-")[0], slot=r["slot_key"].split("|")[2] if r["slot_key"].count("|") >= 2 else None)
                    for cite in [x for x in r["cite_ids"].split(";") if x]:
                        w.edge(R("rule", rid), cite, "cites")

    # legal basis of each structure: every provision its cells and transfers rest on, verbatim (agent/retrieval_spec.en.md §5.1)
    law_db = PROJECT / "database" / "index" / "law.sqlite"
    lcon = sqlite3.connect(str(law_db)) if law_db.exists() else None
    for cid in paths:
        uses = {}
        for f in sorted((pd / "hops").glob("%s.b*.json" % cid)) if (pd / "hops").is_dir() else []:
            for cells in jload(f).get("items", []):
                for it in cells if isinstance(cells, list) else []:
                    rules_used = sorted(set((it.get("rules_applied") or {}).get("floor", []) + (it.get("rules_applied") or {}).get("ceiling", [])))
                    for cite in it.get("cite_ids") or []:
                        u = uses.setdefault(cite, {"n": 0, "rules": set(), "slots": set()})
                        u["n"] += 1
                        u["rules"].update(rules_used)
                        u["slots"].add(it.get("slot_key", ""))
        tf = pd / "transfers" / ("%s.json" % cid)
        for group in (jload(tf).get("items", []) if tf.exists() else []):
            for it in group if isinstance(group, list) else [group]:
                for cite in it.get("cite_ids") or []:
                    u = uses.setdefault(cite, {"n": 0, "rules": set(), "slots": set()})
                    u["n"] += 1
                    u["slots"].add(it.get("slot_key", ""))
        if not uses:
            continue
        rows = []
        def weight(c):                                  # what sets the tax first (rates, caps, exemptions, anti-abuse), residence last
            slots = {x.split("|")[2] if x.count("|") >= 2 else "" for x in uses[c]["slots"]}
            return (all(x in ("residence", "") for x in slots), -uses[c]["n"], c)
        for cite in sorted(uses, key=weight):
            row = {"cite_id": cite, "rules": sorted(uses[cite]["rules"]), "slots": sorted(x for x in uses[cite]["slots"] if x)}
            if lcon:
                m = lcon.execute("SELECT title, label, text FROM clause WHERE cite_id = ?", (cite,)).fetchone()
                if m:
                    row.update(title=m[0], label=m[1], text=m[2][:800], total_chars=len(m[2]))
            rows.append(row)
        verbal = "legal basis of structure %s (%s): %s" % (cid, " > ".join(paths[cid]["path"]),
                                                          "; ".join("%s %s" % (r.get("title", ""), r.get("label", r["cite_id"])) for r in rows))
        w.add(R("basis", cid), "basis", cid, verbal, [r["cite_id"] for r in rows], rows, "hops/ + transfers/", cand=cid)
        w.edge(R("structure", cid), R("basis", cid), "basis")
        for r in rows:
            w.edge(R("basis", cid), r["cite_id"], "cites")
    if lcon:
        lcon.close()

    # judgment points (brief) and open items
    for jp in brief.get("judgment_points", []):
        key = "%s:%s" % (jp["key"], jp.get("about", ""))
        f, u = jp.get("first_if_favourable") or {}, jp.get("first_if_unfavourable") or {}
        verbal = "judgment point %s about %s: %s; changes rank %s; first if favourable %s (%s), first if unfavourable %s (%s); at stake %s" % (
            jp["key"], jp.get("about"), jp.get("question", ""), jp.get("changes_rank"), f.get("cand_id"), span(f.get("amount")),
            u.get("cand_id"), span(u.get("amount")), span(jp.get("value_at_stake")))
        w.add(R("point", key), "point", key, verbal, {k: jp.get(k) for k in ("key", "about", "changes_rank", "value_at_stake")} |
              {"first_if_favourable": {k: f.get(k) for k in ("cand_id", "amount", "one_off_total")},
               "first_if_unfavourable": {k: u.get(k) for k in ("cand_id", "amount", "one_off_total")}, "question": short(jp.get("question"), 200)},
              jp, "brief.json", point=jp["key"], jur=jp["key"].split("@")[-1])
        if f.get("cand_id"):
            w.edge(R("point", key), R("structure", f["cand_id"]), "first_if_favourable")
        if u.get("cand_id"):
            w.edge(R("point", key), R("structure", u["cand_id"]), "first_if_unfavourable")
    oi = get("open_items.json")
    for n, it in enumerate(oi.get("open_items", []) if isinstance(oi, dict) else oi):
        key = "%s:%s:%s" % (it.get("kind", "item"), it.get("key", n), it.get("about", ""))
        verbal = "open item %s %s about %s: %s; changes rank %s; client supplies %s; blocks %d branches" % (
            it.get("kind"), it.get("key"), it.get("about"), it.get("question", ""), it.get("changes_rank"), it.get("client_supplies"), len(it.get("blocks") or []))
        cardo = {k: it.get(k) for k in ("kind", "key", "about", "changes_rank", "client_supplies", "narrows_best", "factor_vars")}
        cardo.update(question=short(it.get("question"), 200), blocks=len(it.get("blocks") or []))
        w.add(R("open_item", key), "open_item", key, verbal, cardo, it, "open_items.json", point=it.get("key"))
        for b in (it.get("blocks") or [])[:80]:
            w.edge(R("open_item", key), R("branch", b), "blocks")

    # scenarios
    sc = get("scenarios.json")
    for s in sc.get("scenarios", []):
        sid = s["scenario_id"]
        amounts = "; ".join("%s %s" % (c, span(v.get("amount"))) for c, v in sorted((s.get("structures") or {}).items()))
        verbal = "scenario %s: against %s; first %s, second %s; order %s; amounts %s" % (
            sid, ", ".join(":".join(a) if isinstance(a, list) else str(a) for a in s.get("against") or []) or "nothing", s.get("first"), s.get("second"), ", ".join(s.get("order") or []), amounts)
        cardo = {"scenario": sid, "against": s.get("against"), "first": s.get("first"), "second": s.get("second"), "order": s.get("order"),
                 "amounts": {c: v.get("amount") for c, v in (s.get("structures") or {}).items()}, "as_is": (s.get("as_is") or {}).get("amount")}
        w.add(R("scenario", sid), "scenario", sid, verbal, cardo, s, "scenarios.json", scenario=sid)
        if s.get("first"):
            w.edge(R("scenario", sid), R("structure", s["first"]), "first")

    # deltas: savings, one-off cost and exposure per branch
    for d in get("deltas.json").get("deltas", []):
        bid, cid = d["branch_id"], d["cand_id"]
        oo, ex = d.get("one_off_cost") or {}, d.get("exposure_if_denied") or {}
        verbal = "delta of branch %s (%s): vs current %s, vs best %s, vs best without restructuring %s; saving per payment %s against baseline %s; payback in payments %s; one-off total %s; exposure if denied total %s (tax %s, interest %s, fine %s)" % (
            bid, cid, span((d.get("vs_as_is") or {}).get("amount")), span((d.get("vs_best") or {}).get("amount")),
            span((d.get("vs_best_no_restructure") or {}).get("saving_per_payment")), span(d.get("saving_per_payment")), d.get("baseline_branch"), json.dumps(d.get("payback_payments")), span(oo.get("total")),
            span(ex.get("total")), span(ex.get("tax")), span(ex.get("interest")), span(ex.get("fine")))
        cardo = {"branch": bid, "cand": cid, "vs_as_is": d.get("vs_as_is"), "vs_best": d.get("vs_best"), "saving_per_payment": d.get("saving_per_payment"), "payback_payments": d.get("payback_payments"),
                 "one_off_total": oo.get("total"), "one_off_flags": oo.get("flags"),
                 "exposure_total": ex.get("total"), "exposure_tax": ex.get("tax"), "exposure_interest": ex.get("interest"), "exposure_fine": ex.get("fine")}
        w.add(R("delta", bid), "delta", bid, verbal, cardo, d, "deltas.json", cand=cid, branch=bid)
        w.edge(R("branch", bid), R("delta", bid), "delta")

    # requirements, transfers, penalties
    for f in sorted((pd / "requirements").glob("*.json")) if (pd / "requirements").is_dir() else []:
        cid = f.stem
        for i, req in enumerate(jload(f).get("requirements", [])):
            key = "%s/%d" % (cid, i)
            fav = req.get("favourable_rules") or []
            verbal = "requirements of %s hop %s (%s): %s" % (cid, i, req.get("edge_id"), "; ".join(
                "%s needs %s" % (r.get("rule_id"), ", ".join(sorted(set(str(v) for v in (r.get("variables") or []) + (r.get("predicates") or []))))) for r in fav)[:220])
            w.add(R("requirement", key), "requirement", key, verbal, {"cand": cid, "edge_id": req.get("edge_id"),
                  "rules": [r.get("rule_id") for r in fav]}, req, "requirements/%s" % f.name, cand=cid)
            w.edge(R("structure", cid), R("requirement", key), "requirement")
    for f in sorted((pd / "transfers").glob("*.json")) if (pd / "transfers").is_dir() else []:
        cid = f.stem
        for i, group in enumerate(jload(f).get("items", [])):
            cells = group if isinstance(group, list) else [group]
            restr = [c for c in cells if c.get("slot") == "restructure"]
            verbal = "transfer %d of %s: %s" % (i, cid, "; ".join("%s %s floor %s ceiling %s cites %s" % (
                c.get("slot_key"), c.get("status"), json.dumps((c.get("floor") or {}).get("value")), json.dumps((c.get("ceiling") or {}).get("value")),
                ",".join(c.get("cite_ids") or [])) for c in restr or cells))
            w.add(R("transfer", "%s/%d" % (cid, i)), "transfer", "%s/%d" % (cid, i), verbal,
                  [{k: c.get(k) for k in ("slot_key", "status", "assumptions")} | {"floor": (c.get("floor") or {}).get("value"),
                   "ceiling": (c.get("ceiling") or {}).get("value")} for c in restr or cells], cells, "transfers/%s" % f.name, cand=cid)
            w.edge(R("structure", cid), R("transfer", "%s/%d" % (cid, i)), "transfer")
    for f in sorted((pd / "penalty").glob("*.json")) if (pd / "penalty").is_dir() else []:
        items = jload(f).get("items", [])
        verbal = "penalty rules of %s: %s" % (f.stem, "; ".join("%s %s cites %s" % (it.get("slot_key"), json.dumps((it.get("ceiling") or {}).get("value")),
                                                                                    ",".join(it.get("cite_ids") or [])) for it in items))
        w.add(R("penalty", f.stem), "penalty", f.stem, verbal, [{k: it.get(k) for k in ("slot_key", "status", "cite_ids")} | {"value": (it.get("ceiling") or {}).get("value")}
                                                               for it in items], items, "penalty/%s" % f.name, jur=f.stem)

    # past payments, diff, input, brief notes
    for p in get("past_payments.json").get("past_payments", []):
        verbal = "past payment %s: payee share %s, withheld %s, refundable if qualified %s, refund limit %s; conflicts %s" % (
            p.get("date"), money(p.get("payee_share")), money(p.get("withheld_stated")), money(p.get("refundable_if_qualified")),
            p.get("refund_limit_date"), "; ".join(p.get("conflicts") or []))
        w.add(R("past_payment", p.get("date")), "past_payment", p.get("date"), verbal, p, p, "past_payments.json")
    df = get("diff.json")
    if df:
        verbal = "difference from the previous run: inputs changed %s; engine changed %s; %d rank moves; incomparable %s" % (
            ", ".join(df.get("inputs_changed") or []), ", ".join(k for k, v in (df.get("engine_changed") or {}).items() if v),
            len(df.get("rank_moves") or []), "; ".join(df.get("incomparable") or []))
        w.add(R("diff", "previous"), "diff", "previous", verbal, {k: df.get(k) for k in ("inputs_changed", "engine_changed", "incomparable")} |
              {"rank_moves": len(df.get("rank_moves") or []), "interval_changes": len(df.get("interval_changes") or [])}, df, "diff.json")
    inp = get("input.json")
    if inp:
        verbal = "optimizer input: %s %s paid %s by %s to %s; destinations %s; entities %s" % (
            money(inp.get("amount")), inp.get("currency"), inp.get("date"), (inp.get("payer") or {}).get("jur"),
            "%s:%s" % ((inp.get("payee") or {}).get("jur"), (inp.get("payee") or {}).get("subject")),
            ", ".join(":".join(d) for d in inp.get("destinations") or []), ", ".join(sorted(inp.get("entities") or {})))
        w.add(R("input", "run"), "input", "run", verbal, {k: inp.get(k) for k in ("amount", "currency", "date", "destinations", "valuation", "constraints")}, inp, "input.json")
    if brief:
        best = brief.get("best") or {}
        verbal = "brief: best %s %s all favourable %s; current %s %s; %d judgment points; %d decision gaps; notes %s" % (
            best.get("cand_id"), best.get("label"), span((best.get("all_favourable") or {}).get("amount")), (brief.get("as_is") or {}).get("cand_id"),
            span((brief.get("as_is") or {}).get("range_all_branches", {}).get("amount")), len(brief.get("judgment_points") or []),
            len(brief.get("decision_gaps") or []), " | ".join(brief.get("notes") or []))
        w.add(R("brief", "summary"), "brief", "summary", verbal, {"best": best.get("cand_id"), "as_is": (brief.get("as_is") or {}).get("cand_id"),
              "terms": brief.get("terms"), "decision_gaps": [g.get("key") for g in brief.get("decision_gaps") or []]}, brief, "brief.json")
        for g in brief.get("decision_gaps") or []:
            gk = "%s:%s" % (g.get("kind"), g.get("key"))
            w.add(R("gap", gk), "gap", gk, "decision gap %s %s about %s: %s; need %s" % (g.get("kind"), g.get("key"), g.get("about"), g.get("question", ""), g.get("need", "")),
                  {k: g.get(k) for k in ("kind", "key", "about", "need", "first_in_scenarios")} | {"question": short(g.get("question"), 200)}, g, "brief.json")
    w.close()
    return out


# ------------------------------------------------------------ case file
def case_files(cd):
    intake = cd / "intake"
    files = [intake / n for n in ("facts.json", "sources.json", "answers.json", "constraints.json", "dialogue.md", "notes.md", "handoff.md", "to_collect.md")]
    docs = intake / "documents"
    files += sorted(docs.iterdir()) if docs.is_dir() else []
    files += sorted((intake / "index" / "parsed").glob("*.json")) if (intake / "index" / "parsed").is_dir() else []
    return files


def flatten(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from flatten(v, "%s.%s" % (prefix, k) if prefix else str(k))
    elif isinstance(obj, list) and obj and all(isinstance(x, (dict, list)) for x in obj):
        for i, v in enumerate(obj):
            yield from flatten(v, "%s[%d]" % (prefix, i))
    else:
        yield prefix, obj


def build_case(cd, force=False, ocr=False):
    """The case-file index; documents are parsed (text layer, and OCR when ocr=True) and cached by sha256."""
    cd = Path(cd)
    case_id = cd.name
    intake = cd / "intake"
    if (intake / "documents").is_dir():
        import doc_parse
        for f in sorted((intake / "documents").iterdir()):
            if f.is_file():
                doc_parse.parse(f, intake / "index" / "parsed", ocr=ocr)
    out = intake / "index" / "case.sqlite"
    fp = fingerprint(case_files(cd))
    if out.exists() and not force and not stale(out, fp):
        return out
    w = Writer(out, {"fingerprint": fp, "kind": "case", "case_id": case_id, "index_version": INDEX_VERSION})
    R = lambda t, k: "%s:%s:%s" % (case_id, t, k)
    get = lambda n: jload(intake / n) if (intake / n).exists() else {}
    sources = get("sources.json")
    srows = sources.get("sources", []) if isinstance(sources, dict) else sources
    by_key = {}
    for n, s in enumerate(srows):
        by_key.setdefault(s.get("key"), []).append(n)
        verbal = "source of %s: %s page %s: %s" % (s.get("key"), s.get("doc"), s.get("page"), s.get("quote", ""))
        w.add(R("source", n), "source", str(n), verbal, s, s, "intake/sources.json", doc=s.get("doc"), page=s.get("page"))
    for path, val in flatten(get("facts.json")):
        verbal = "fact %s = %s" % (path, json.dumps(val, ensure_ascii=False))
        rows = [srows[i] for i in by_key.get(path, [])] or [srows[i] for k, ix in by_key.items() if k and path.startswith(str(k)) for i in ix]
        w.add(R("fact", path), "fact", path, verbal, {"key": path, "value": val, "sources": [{"doc": r.get("doc"), "page": r.get("page")} for r in rows][:4]},
              {"key": path, "value": val, "sources": rows}, "intake/facts.json", extra=" ".join(r.get("quote", "") for r in rows)[:300])
        for i in by_key.get(path, []):
            w.edge(R("fact", path), R("source", i), "source")
    for k, a in (get("answers.json") or {}).items():
        a = a if isinstance(a, dict) else {"value": a}
        w.add(R("answer", k), "answer", k, "answer %s = %s: %s" % (k, a.get("value"), a.get("quote", "")), a, a, "intake/answers.json", point=k)
    con = get("constraints.json")
    if con:
        w.add(R("constraints", "all"), "constraints", "all", "constraints " + json.dumps(con, ensure_ascii=False), con, con, "intake/constraints.json")
    dl = intake / "dialogue.md"
    if dl.exists():
        entries = re.split(r"(?m)^(?=### )", dl.read_text(encoding="utf-8"))
        for e in entries:
            m = re.match(r"### (.*?)#(\d+)\s*$", e.splitlines()[0]) if e.strip() else None
            if not m:
                continue
            no, head = m.group(2), m.group(1)
            paras = [p.strip() for p in re.split(r"\n\s*\n", "\n".join(e.splitlines()[1:])) if p.strip()]
            for j, p in enumerate(paras):
                key = "%s.%d" % (no, j)
                w.add(R("dialogue", key), "dialogue", key, "dialogue #%s %s: %s" % (no, head, p), {"entry": no, "head": head.strip(" |"), "text": short(p, 500)},
                      {"entry": no, "head": head, "text": p}, "intake/dialogue.md", extra=p)
    for name, typ in (("notes.md", "note"), ("to_collect.md", "to_collect"), ("handoff.md", "handoff")):
        p = intake / name
        if not p.exists():
            continue
        blocks = [b.strip() for b in re.split(r"\n\s*\n|\n(?=- )", p.read_text(encoding="utf-8")) if b.strip()]
        for j, b in enumerate(blocks):
            w.add(R(typ, j), typ, str(j), "%s %d: %s" % (typ, j, b), {"text": short(b, 500)}, {"text": b}, "intake/" + name, extra=b)
    import doc_parse
    for f in sorted((intake / "documents").iterdir()) if (intake / "documents").is_dir() else []:
        if not f.is_file():
            continue
        doc = f.name.split("_")[0] + ("_" + re.search(r"_(p\d+)$", f.stem).group(1) if re.search(r"_(p\d+)$", f.stem) else "")
        parsed = doc_parse.cached(f, intake / "index" / "parsed")
        pages = parsed.get("pages", []) if parsed else []
        w.add(R("document", doc), "document", doc, "document %s %s: %d pages, %s" % (doc, f.name, len(pages), (parsed or {}).get("status", "not parsed")),
              {"doc": doc, "file": f.name, "pages": len(pages), "status": (parsed or {}).get("status", "not parsed"),
               "derived": (parsed or {}).get("derived")}, {"doc": doc, "file": "intake/documents/" + f.name, "parsed": {k: v for k, v in (parsed or {}).items() if k != "pages"}},
              "intake/documents/" + f.name, doc=doc)
        for pg in pages:
            pk = "%s:%d" % (doc, pg["page"])
            w.add(R("page", pk), "page", pk, "page %d of %s (%s): %s" % (pg["page"], doc, pg.get("derived"), pg.get("text", "")),
                  {"doc": doc, "page": pg["page"], "derived": pg.get("derived"), "confidence": pg.get("confidence"), "text": short(pg.get("text"), 500)},
                  pg, "intake/documents/" + f.name, doc=doc, page=pg["page"], extra=pg.get("text", "")[:4000])
            w.edge(R("document", doc), R("page", pk), "page")
            for t, table in enumerate(pg.get("tables") or []):
                header = table[0] if table else []
                for r_i, row in enumerate(table[1:], 1):
                    for c_i, val in enumerate(row):
                        if val in (None, ""):
                            continue
                        ck = "%s:%d:%d:%d:%d" % (doc, pg["page"], t, r_i, c_i)
                        col = header[c_i] if c_i < len(header) else ""
                        rowh = row[0] if row else ""
                        w.add(R("cell", ck), "cell", ck, "table cell of %s page %d: row %s, column %s = %s" % (doc, pg["page"], rowh, col, val),
                              {"doc": doc, "page": pg["page"], "row": rowh, "column": col, "value": val, "derived": pg.get("derived")},
                              {"doc": doc, "page": pg["page"], "table": t, "row": r_i, "col": c_i, "row_header": rowh, "column": col, "value": val},
                              "intake/documents/" + f.name, doc=doc, page=pg["page"])
                        w.edge(R("page", pk), R("cell", ck), "cell")
    w.close()
    return out


def main(argv):
    if len(argv) < 3 or argv[1] not in ("products", "case"):
        print(__doc__)
        return 2
    target = Path(argv[2])
    if argv[1] == "products":
        out = build_products(target, force="--force" in argv)
    else:
        out = build_case(target, force="--force" in argv, ocr="--ocr" in argv)
    con = sqlite3.connect(str(out))
    counts = dict(con.execute("SELECT type, count(*) FROM record GROUP BY type").fetchall())
    edges = con.execute("SELECT count(*) FROM edge").fetchone()[0]
    print(out, json.dumps(counts), "edges", edges)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
