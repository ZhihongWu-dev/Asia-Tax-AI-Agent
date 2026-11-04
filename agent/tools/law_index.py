#!/usr/bin/env python
"""The law-library index of the retrieval layer (agent/retrieval_spec.en.md §4).

  python agent/tools/law_index.py [--dense] [--force]

Reads database/ (doc.csv, clause.csv, param.csv, decision.csv) and rule/rule.csv; writes database/index/law.sqlite:
retrieval units with their verbatim spans and a matching-only header (act title, article label), an FTS5 index over
CJK/Thai bigrams and words, clause metadata (jurisdiction, language, validity of the document), and explicit edges only:
contains (article -> its paragraphs), same_provision (the same fragment of one work in two documents, e.g. a treaty and its
MLI-synthesised text), cites (references written in the text: same-document articles and sections, other acts named by
their title), rule_cites / param_cites / decision_cites, co_cited (clauses one rule cites together). No model-extracted edge.
--dense adds BGE-M3 vectors (database/index/vec.npy + vec_ids.txt), cached by text hash in database/index/vec_cache.sqlite.
"""
import csv
import hashlib
import json
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
DB = PROJECT / "database"
OUT = DB / "index"
sys.path.insert(0, str(HERE))
from textutil import cn2int, fts_tokens, split_units  # noqa: E402

csv.field_size_limit(2 ** 31 - 1)
INDEX_VERSION = "3"
DENSE_MODEL = "BAAI/bge-m3"
SCHEMA = """
CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE clause (cite_id TEXT PRIMARY KEY, doc_id TEXT, work TEXT, frag TEXT, jur TEXT, lang TEXT, title TEXT, label TEXT,
                     valid_from TEXT, valid_to TEXT, parent TEXT, n_units INTEGER, chars INTEGER, text TEXT);
CREATE TABLE unit (unit_id TEXT PRIMARY KEY, cite_id TEXT NOT NULL, seq INTEGER, start INTEGER, "end" INTEGER, header TEXT, gloss TEXT);
CREATE TABLE edge (src TEXT NOT NULL, dst TEXT NOT NULL, kind TEXT NOT NULL, evidence TEXT);
CREATE TABLE alias (alias TEXT PRIMARY KEY, doc_id TEXT);
CREATE VIRTUAL TABLE unit_fts USING fts5(unit_id UNINDEXED, header, body, tokenize='unicode61 remove_diacritics 2');
CREATE INDEX unit_cite ON unit(cite_id);
CREATE INDEX edge_src ON edge(src, kind);
CREATE INDEX edge_dst ON edge(dst, kind);
"""
LANG_SUFFIX = re.compile(r"\.(zh-hk|zh|en|ja|th)$")
VARIANT = re.compile(r"\.(mli|full|consolidated|sso|pdf)$")
NUM = r"[一二三四五六七八九十百零〇两\d]+"
CN_REF = re.compile(r"(?P<act>《[^》\n]{2,60}》)?(?P<self>本法|本条例|本细则|本办法|本规定|本公告|本通知|本协定|本安排|本议定书)?"
                    r"第(?P<art>" + NUM + r")条(?:の(?P<sub>" + NUM + r"))?(?:第(?P<para>" + NUM + r")[款項项])?(?:第[（(]?(?P<item>" + NUM + r")[）)]?[项號号])?")
EN_SEC = re.compile(r"\b(?:[Ss]ections?|ss?\.)\s?(?P<no>\d+[A-Z]{0,4}(?:bis|ter|quater)?)(?P<sub>(?:\(\w{1,5}\))*)"
                    r"(?:\s+of\s+(?:the\s+)?(?P<act>[A-Z][\w’'()\-. ]{2,90}?(?:Ordinance|Act|Code|Order|Regulations|Rules)(?:\s\d{4})?(?:\s\(Cap\.?\s?\d+[A-Z]*\))?))?")
NAME_END = re.compile(r"([぀-ヿ一-鿿・]{1,30}?(?:法律|法|条例|細則|细则|办法|規則|规则|规定|通知|公告|協定|协定|安排|議定書|议定书|政令|施行令|令))$")
SELF_NAMES = ("本法", "本条例", "本细则", "本办法", "本规定", "本公告", "本通知", "本协定", "本安排", "本议定书", "この法律", "この政令")
EN_ART = re.compile(r"\bparagraph\s(?P<para>\d+)\sof\sArticle\s(?P<art>\d+[A-Z]?)\b|\bArticle\s(?P<art2>\d+[A-Z]?)(?:\s?\((?P<para2>\d+)\))?")


def read_csv(name, root=DB):
    with (root / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def work_of(doc_id):
    """The work a document expresses: language and synthesis suffixes removed (treaty.cn-sg.2007.mli.en -> treaty.cn-sg.2007)."""
    x = LANG_SUFFIX.sub("", doc_id)
    while VARIANT.search(x):
        x = VARIANT.sub("", x)
    return x


def parent_of(cite, cites):
    """The enclosing provision of a fragment when the library holds it: 24.3 -> 24, s39(1) -> s39, i2 has none."""
    doc, frag = cite.split("#", 1)
    for cut in (lambda f: f.rsplit(".", 1)[0] if "." in f else None, lambda f: re.sub(r"\([^()]*\)$", "", f) if f.endswith(")") else None):
        p = cut(frag)
        if p and p != frag and "%s#%s" % (doc, p) in cites:
            return "%s#%s" % (doc, p)
    return None


class Resolver:
    """Explicit references in a clause's text -> cite ids in the library; unresolved references are not guessed."""

    def __init__(self, docs, frags):
        self.frags = frags
        self.alias = {}
        for d in docs:
            t = re.sub(r"\s+", "", d["title"])
            for a in {t, re.sub(r"^中华人民共和国", "", t), re.sub(r"\(.*?\)|（.*?）", "", t)}:
                if len(a) >= 3:
                    self.alias.setdefault(a.lower(), d["id"])
            m = re.match(r"hk\.cap(\d+[a-z]*)$", d["id"])
            if m:
                self.alias.setdefault("cap" + m.group(1), d["id"])
        self.local = defaultdict(dict)

    def act(self, name, doc):
        t = re.sub(r"\s+", "", name or "").strip("《》").lower()
        if not t:
            return None
        if t in self.local[doc]:
            return self.local[doc][t]
        if t in self.alias:
            return self.alias[t]
        m = re.search(r"\(cap\.?(\d+[a-z]*)\)", t)
        if m:
            return self.alias.get("cap" + m.group(1))
        return self.alias.get(re.sub(r"\(.*?\)|（.*?）", "", t))

    def define_shorts(self, doc, text):
        for m in re.finditer(r"《([^》]{2,90})》[^（(《》]{0,30}[（(][^）)]{0,40}?以下简称[《“\"]([^》”\"]{1,20})[》”\"]", text):
            target = self.act(m.group(1), doc)
            if target:
                self.local[doc][re.sub(r"\s+", "", m.group(2)).lower()] = target

    def first(self, doc, frags):
        for f in frags:
            if f in self.frags.get(doc, ()):
                return "%s#%s" % (doc, f)
        return None

    def named_before(self, doc, text, start):
        """The act a 第X条 reference names just before it, without 《》: (doc_id or None, named?). 本法 / この法律 is the
        document itself; in a Japanese order 法 is its parent act and in an act 令 is its order; a name that matches no
        title leaves the reference unresolved rather than guessed."""
        m = NAME_END.search(text[max(0, start - 32):start])
        if not m:
            return doc, False
        name = m.group(1)
        if name in SELF_NAMES or name.endswith(SELF_NAMES):
            return doc, True
        if name == "法" and doc.endswith(".order"):
            return doc[:-len(".order")], True
        if name in ("令", "施行令") and doc.startswith("jp.") and not doc.endswith(".order"):
            return doc + ".order", True
        if name in ("同法", "同令", "法", "令", "条例", "办法", "规定", "通知", "公告"):
            return None, True
        for i in range(len(name) - 2):
            hit = self.act(name[i:], doc)
            if hit:
                return hit, True
        return None, True

    def refs(self, cite, doc, text):
        out = []
        for m in CN_REF.finditer(text):
            art = cn2int(m.group("art"))
            if art is None:
                continue
            if m.group("act"):
                target = self.act(m.group("act"), doc)
            elif m.group("self"):
                target = doc
            else:
                target, _ = self.named_before(doc, text, m.start())
            if not target:
                continue
            base = str(art) + ("_%s" % cn2int(m.group("sub")) if m.group("sub") else "")
            para, item = cn2int(m.group("para")) if m.group("para") else None, cn2int(m.group("item")) if m.group("item") else None
            cands = ([base + ".%d" % para] if para else []) + [base] + (["i%d" % item] if item and not para else [])
            hit = self.first(target, cands)
            if hit and hit != cite:
                out.append((hit, m.group(0)))
        for m in EN_SEC.finditer(text):
            target = self.act(m.group("act"), doc) if m.group("act") else doc
            if not target:
                continue
            no = m.group("no")
            subs = re.findall(r"\(\w{1,5}\)", m.group("sub") or "")
            cands = ["s%s%s" % (no, "".join(subs[:k])) for k in range(len(subs), -1, -1)]
            hit = self.first(target, cands)
            if hit and hit != cite:
                out.append((hit, m.group(0)))
        if doc.startswith(("treaty.", "intl.")):
            for m in EN_ART.finditer(text):
                art, para = (m.group("art"), m.group("para")) if m.group("art") else (m.group("art2"), m.group("para2"))
                hit = self.first(doc, ([("%s.%s" % (art, para))] if para else []) + [art])
                if hit and hit != cite:
                    out.append((hit, m.group(0)))
        return out


def fingerprint():
    h = hashlib.sha256(INDEX_VERSION.encode())
    for p in [DB / n for n in ("doc.csv", "clause.csv", "param.csv", "decision.csv")] + [PROJECT / "rule" / "rule.csv"]:
        h.update(hashlib.sha256(p.read_bytes()).digest() if p.exists() else b"-")
    return h.hexdigest()[:16]


def build(force=False):
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "law.sqlite"
    fp = fingerprint()
    if out.exists() and not force:
        try:
            con = sqlite3.connect(str(out))
            if con.execute("SELECT v FROM meta WHERE k='fingerprint'").fetchone() == (fp,):
                con.close()
                return out
            con.close()
        except sqlite3.Error:
            pass
    docs = read_csv("doc.csv")
    dmap = {d["id"]: d for d in docs}
    clauses = read_csv("clause.csv")
    cites = {c["cite_id"] for c in clauses}
    frags = defaultdict(set)
    for c in clauses:
        frags[c["doc_id"]].add(c["cite_id"].split("#", 1)[1])
    tmp = out.with_suffix(".tmp")
    if tmp.exists():
        tmp.unlink()
    con = sqlite3.connect(str(tmp))
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO meta VALUES (?,?)", [("fingerprint", fp), ("index_version", INDEX_VERSION), ("dense_model", "")])
    R = Resolver(docs, frags)
    for c in clauses:
        R.define_shorts(c["doc_id"], c["text"][:20000])
    con.executemany("INSERT OR IGNORE INTO alias VALUES (?,?)", sorted(R.alias.items()))
    edges = set()
    by_work = defaultdict(list)
    n_units = 0
    for c in clauses:
        cite, doc = c["cite_id"], c["doc_id"]
        d = dmap.get(doc, {})
        lang = (d.get("lang") or "en")[:2]
        text = c["text"]
        units = split_units(text, lang)
        parent = parent_of(cite, cites)
        work, frag = work_of(doc), cite.split("#", 1)[1]
        con.execute("INSERT INTO clause VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (cite, doc, work, frag, d.get("jur", ""), lang, d.get("title", ""), c["label"], d.get("effective_from", ""),
                     d.get("effective_to", ""), parent, len(units), len(text), text))
        header = "%s %s" % (d.get("title", ""), c["label"])
        for seq, (a, b) in enumerate(units):
            uid = "%s@%d" % (cite, seq)
            con.execute("INSERT INTO unit VALUES (?,?,?,?,?,?,?)", (uid, cite, seq, a, b, header, None))
            con.execute("INSERT INTO unit_fts VALUES (?,?,?)", (uid, fts_tokens(header + " " + cite.replace("#", " ")), fts_tokens(text[a:b])))
            n_units += 1
        if parent:
            edges.add((parent, cite, "contains", ""))
        by_work[(work, frag)].append(cite)
        for hit, ev in R.refs(cite, doc, text[:60000]):
            edges.add((cite, hit, "cites", ev[:80]))
    for (_, _), group in by_work.items():
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                if a.split("#")[0] != b.split("#")[0]:
                    edges.add((a, b, "same_provision", ""))
    for r in read_csv("rule.csv", PROJECT / "rule"):
        cs = [x for x in r.get("cite_ids", "").split(";") if x in cites]
        for x in cs:
            edges.add(("rule:" + r["rule_id"], x, "rule_cites", ""))
        for i, a in enumerate(cs):
            for b in cs[i + 1:]:
                if a != b:
                    edges.add((a, b, "co_cited", r["rule_id"]))
    for p in read_csv("param.csv"):
        if p.get("cite_id") in cites:
            edges.add(("param:" + p["param_id"], p["cite_id"], "param_cites", ""))
    for dd in read_csv("decision.csv"):
        if dd.get("cite_id") in cites:
            edges.add(("decision:" + dd["id"], dd["cite_id"], "decision_cites", ""))
    con.executemany("INSERT INTO edge VALUES (?,?,?,?)", sorted(edges))
    con.commit()
    con.close()
    if out.exists():
        out.unlink()
    tmp.rename(out)
    kinds = defaultdict(int)
    for e in edges:
        kinds[e[2]] += 1
    print("law index: %d clauses, %d units, edges %s" % (len(clauses), n_units, dict(kinds)))
    return out


def build_vectors(batch=64):
    """BGE-M3 vectors of every unit (header + text), cached by text hash: a rebuild only embeds what changed."""
    import os
    import numpy as np
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    con = sqlite3.connect(str(OUT / "law.sqlite"))
    texts = {}
    clause_text = {c["cite_id"]: c["text"] for c in read_csv("clause.csv")}
    rows = con.execute("SELECT unit_id, cite_id, start, \"end\", header FROM unit ORDER BY rowid").fetchall()
    for uid, cite, a, b, header in rows:
        texts[uid] = (header + "\n" + clause_text[cite][a:b])[:2000]
    cache = sqlite3.connect(str(OUT / "vec_cache.sqlite"))
    cache.execute("CREATE TABLE IF NOT EXISTS vec (key TEXT PRIMARY KEY, model TEXT, vec BLOB)")
    key = lambda t: hashlib.sha256((DENSE_MODEL + "\0" + t).encode()).hexdigest()
    have = {k for (k,) in cache.execute("SELECT key FROM vec WHERE model = ?", (DENSE_MODEL,))}
    todo = [(uid, t) for uid, t in texts.items() if key(t) not in have]
    print("dense: %d units, %d to embed" % (len(texts), len(todo)))
    if todo:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(DENSE_MODEL, device="cuda")
        model.half()
        todo.sort(key=lambda x: len(x[1]))
        for i in range(0, len(todo), batch * 16):
            chunk = todo[i:i + batch * 16]
            vecs = model.encode([t for _, t in chunk], batch_size=batch, normalize_embeddings=True, show_progress_bar=False)
            cache.executemany("INSERT OR REPLACE INTO vec VALUES (?,?,?)",
                              [(key(t), DENSE_MODEL, v.astype("float16").tobytes()) for (_, t), v in zip(chunk, vecs)])
            cache.commit()
            print("  embedded %d / %d" % (min(i + batch * 16, len(todo)), len(todo)), flush=True)
    ids = [uid for uid, *_ in rows]
    mat = np.zeros((len(ids), 1024), dtype="float16")
    for i, uid in enumerate(ids):
        (blob,) = cache.execute("SELECT vec FROM vec WHERE key = ?", (key(texts[uid]),)).fetchone()
        mat[i] = np.frombuffer(blob, dtype="float16")
    np.save(OUT / "vec.npy", mat)
    (OUT / "vec_ids.txt").write_text("\n".join(ids), encoding="utf-8")
    con.execute("UPDATE meta SET v = ? WHERE k = 'dense_model'", (DENSE_MODEL,))
    con.commit()
    print("dense: wrote %d vectors" % len(ids))


if __name__ == "__main__":
    build(force="--force" in sys.argv)
    if "--dense" in sys.argv:
        build_vectors()
