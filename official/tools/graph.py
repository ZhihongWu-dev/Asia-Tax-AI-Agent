#!/usr/bin/env python
"""Knowledge layer of official.sqlite. Runs after build.py (build.py calls it last); reads only what build.py wrote.

Design notes and the papers behind each part: literature/notes/I_综合.md.

  work / expression     FRBR split (Akoma Ntoso, I17): a Work is the instrument; an Expression is one language or one
                        variant of it (consolidated, assembled, single-provision view). Only current Expressions exist
                        (the library keeps no repealed text); time sits on the Expression and on the clause.
  provision             the language-independent provision a clause expresses: "<work>#<fragment>"; clauses of two
                        Expressions with the same fragment express the same provision (explicit cross-language link,
                        instead of relying on lexical matching across languages, I4).
  unit                  retrieval units: verbatim character spans [start, end) of a clause, split at the law's own
                        structure (subsection, paragraph, item) and then at sentence ends, about 100 words each
                        (I5, I21); a context header (title > label) is indexed for search, never cited.
  edge                  typed relations, each with the matched text and the extraction rule: contains, cites
                        (explicit cross-reference, resolved by structure; I15), cites_act, same_provision, variant_of,
                        attachment_of, amends, interprets, param_cites, gap_cites, rule_cites, rule_uses_param,
                        substitutes. An unresolvable reference stays "unresolved", never guessed (I15, I22).
  term                  defined terms with the other-language equivalent the law itself prints.
  event / tombstone     legislative events (substitution, repeal) and removed instruments: metadata only (I17, I19);
                        a date before an instrument's coverage is answered "not covered", never with today's text (I20).
  clause_time           validity of each clause (expression dates; substitution dates from superseded.csv).
  anchor                every param / gap / decision quote resolved to an exact character span of its clause (I14, I21).
  decision              decisions.csv: the readings (口径) the engine relies on, each with the verbatim words it rests on;
                        the engine names them in code ("口径 D04"), and the build checks both directions (I21, J11).
  constraint_result     declarative quality constraints, Error or Warning, run at every build; the counts are compared
                        with the previous build in INDEX.md (J10).
  unit_fts              FTS5 BM25 index over units; CJK as character bigrams, Latin words stemmed (I1, I6, I9).
  unit_vec              optional dense vectors (--dense), cached by text hash in _index/vec_cache.sqlite (I4).

Python 3.9, conda env "pytorch".   python official/tools/graph.py [--dense]
"""
import csv
import hashlib
import io
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
csv.field_size_limit(10 ** 9)
ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
DB = ROOT / "official.sqlite"
ENC = "utf-8-sig"
EXTRACTOR = "graph.py/2026-10-08"            # recorded on every derived row; bump when a rule changes

CN_DIGIT = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
CN_UNIT = {"十": 10, "百": 100, "千": 1000}


def cn2int(s):
    if s.isdigit():
        return int(s)
    total, num = 0, 0
    for ch in s:
        if ch in CN_DIGIT:
            num = CN_DIGIT[ch]
        elif ch in CN_UNIT:
            total += (num or 1) * CN_UNIT[ch]
            num = 0
    return total + num


def read_csv(path):
    with open(path, encoding=ENC, newline="") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------- schema
SCHEMA = """
CREATE TABLE work (work_id TEXT PRIMARY KEY, jur TEXT NOT NULL, type TEXT, title TEXT);
CREATE TABLE expression (expr_id TEXT PRIMARY KEY, work_id TEXT NOT NULL REFERENCES work(work_id), lang TEXT,
  variant TEXT, canonical INTEGER NOT NULL, part_of TEXT, alias_of TEXT, valid_from TEXT, valid_to TEXT,
  sha256 TEXT, status TEXT NOT NULL DEFAULT 'current');
CREATE TABLE provision (provision_id TEXT PRIMARY KEY, work_id TEXT NOT NULL, fragment TEXT NOT NULL, n_expr INTEGER);
CREATE TABLE clause_meta (cite_id TEXT PRIMARY KEY REFERENCES clause(cite_id), expr_id TEXT NOT NULL,
  provision_id TEXT NOT NULL REFERENCES provision(provision_id), depth INTEGER, path TEXT, lang TEXT, sha1 TEXT);
CREATE TABLE clause_time (cite_id TEXT PRIMARY KEY REFERENCES clause(cite_id), valid_from TEXT, valid_to TEXT, basis TEXT,
  efficacy_from TEXT, efficacy_note TEXT);      -- in force vs. applies to which tax periods (Akoma Ntoso, I17); empty = not stated
CREATE TABLE unit (unit_id TEXT PRIMARY KEY, cite_id TEXT NOT NULL REFERENCES clause(cite_id), seq INTEGER NOT NULL,
  start INTEGER NOT NULL, "end" INTEGER NOT NULL, kind TEXT, lang TEXT, header TEXT, sha1 TEXT, extractor TEXT);
CREATE TABLE edge (src TEXT NOT NULL, dst TEXT NOT NULL, kind TEXT NOT NULL, status TEXT NOT NULL,
  evidence TEXT, src_start INTEGER, src_end INTEGER, rule TEXT, extractor TEXT);
CREATE TABLE term (term TEXT NOT NULL, lang TEXT, equiv TEXT, cite_id TEXT NOT NULL REFERENCES clause(cite_id),
  start INTEGER, "end" INTEGER, rule TEXT);
CREATE TABLE event (kind TEXT NOT NULL, target TEXT NOT NULL, by TEXT, since TEXT, note TEXT, source TEXT);
CREATE TABLE tombstone (id TEXT PRIMARY KEY, title TEXT, reason TEXT, removed_at TEXT, ends TEXT, replaced_by TEXT);
CREATE TABLE anchor (owner TEXT NOT NULL, cite_id TEXT NOT NULL, start INTEGER, "end" INTEGER, occurrences INTEGER,
  status TEXT NOT NULL);
CREATE TABLE alias (alias TEXT NOT NULL, work_id TEXT NOT NULL, lang TEXT, source TEXT);
CREATE TABLE decision (id TEXT NOT NULL, seq INTEGER NOT NULL, statement TEXT, cite_id TEXT NOT NULL, quote TEXT NOT NULL,
  used_in TEXT, PRIMARY KEY (id, seq));
CREATE TABLE decision_ref (id TEXT NOT NULL, location TEXT NOT NULL);     -- "口径 Dnn" in the engine's code
CREATE TABLE verify_result (id TEXT PRIMARY KEY, match TEXT, checked_at TEXT);
CREATE TABLE constraint_result (id TEXT PRIMARY KEY, severity TEXT NOT NULL, description TEXT, violations INTEGER,
  sample TEXT);
CREATE VIRTUAL TABLE unit_fts USING fts5(header, body, tokenize='porter unicode61 remove_diacritics 2');
CREATE INDEX edge_src ON edge(src, kind);
CREATE INDEX edge_dst ON edge(dst, kind);
CREATE INDEX unit_cite ON unit(cite_id);
CREATE INDEX clause_meta_prov ON clause_meta(provision_id);
"""
BASE_INDEXES = """
CREATE UNIQUE INDEX IF NOT EXISTS doc_pk ON doc(id);
CREATE UNIQUE INDEX IF NOT EXISTS clause_pk ON clause(cite_id);
CREATE INDEX IF NOT EXISTS clause_doc ON clause(doc_id);
CREATE UNIQUE INDEX IF NOT EXISTS param_pk ON param(param_id);
"""
DROP = ["work", "expression", "provision", "clause_meta", "clause_time", "unit", "edge", "term", "event", "tombstone",
        "anchor", "alias", "unit_fts", "unit_vec", "decision", "decision_ref", "verify_result", "constraint_result"]


# ---------------------------------------------------------------- constraints (J10): id, severity, what, violating rows
CONSTRAINTS = [
    ("E01", "Error", "引文（参数、缺口、口径）在所引条款里找不到原文",
     "SELECT owner || ' @ ' || cite_id FROM anchor WHERE status = 'missing'"),
    ("E02", "Error", "已解析的关系指向不存在的条款",
     "SELECT src || ' -> ' || dst FROM edge WHERE kind IN ('contains','cites','same_provision','param_cites','gap_cites',"
     "'decision_cites') AND status IN ('resolved','ancestor') AND dst NOT LIKE 'work:%' AND dst NOT IN (SELECT cite_id FROM clause)"),
    ("E03", "Error", "规则层引用了库里没有的条款或参数",
     "SELECT src || ' -> ' || dst FROM edge WHERE kind IN ('rule_cites','rule_uses_param') AND status = 'unresolved'"),
    ("E04", "Error", "已废止（removed.csv）的文件仍有条文留在库里",
     "SELECT c.cite_id FROM clause c WHERE c.doc_id IN (SELECT id FROM tombstone)"),
    ("E05", "Error", "口径没有被引擎代码引用（代码里写“口径 Dnn”）",
     "SELECT DISTINCT d.id FROM decision d WHERE d.id NOT IN (SELECT id FROM decision_ref)"),
    ("E06", "Error", "引擎代码引用了 decisions.csv 里没有的口径",
     "SELECT id || ' @ ' || location FROM decision_ref WHERE id NOT IN (SELECT id FROM decision)"),
    ("E07", "Error", "口径所依条文已失效（valid_to 已过）",
     "SELECT d.id || ' @ ' || d.cite_id FROM decision d JOIN clause_time t ON t.cite_id = d.cite_id "
     "WHERE t.valid_to IS NOT NULL AND t.valid_to != '' AND t.valid_to <= date('now')"),
    ("W01", "Warning", "引文在条款里出现不止一次（锚点取第一处）",
     "SELECT owner || ' @ ' || cite_id FROM anchor WHERE status = 'ambiguous'"),
    ("W02", "Warning", "参数没有原文引语",
     "SELECT owner FROM anchor WHERE status = 'no_quote'"),
    ("W03", "Warning", "参数或口径所依条文有替换事件（superseded.csv），值需复核",
     "SELECT DISTINCT a.owner || ' @ ' || a.cite_id FROM anchor a JOIN event e ON e.target = a.cite_id WHERE e.kind = 'substitution'"),
    ("W04", "Warning", "显式交叉引用未能解析（保留原文，不猜）",
     "SELECT src || ' -> ' || substr(dst, 1, 60) FROM edge WHERE kind = 'cites' AND status = 'unresolved'"),
    ("W05", "Warning", "条款的生效日期未知",
     "SELECT cite_id FROM clause_time WHERE valid_from IS NULL OR valid_from = ''"),
    ("W06", "Warning", "复核下载与登记的哈希不一致（verify.csv）：来源页面可能已改",
     "SELECT id FROM verify_result WHERE match != 'yes'"),
    ("W07", "Warning", "条款里有未转写的公式图片（formulas.csv 未登记）：该处公式在文本层缺失",
     "SELECT cite_id FROM clause WHERE text LIKE '%[formula image %'"),
]


# ---------------------------------------------------------------- identities (FRBR)
LANG = re.compile(r"\.(zh-hk|zh|en)$")
FRAG = re.compile(r"\.frag\d+$")
VARIANT = re.compile(r"\.(full|consolidated|sso|pdf|flk|sh)$")
VIEW = re.compile(r"\.(s\d+[A-Z]*|sch\d+[A-Z]*)$")
VARIANT_RANK = {"": 0, "full": 0, "sso": 1, "pdf": 2, "consolidated": 3, "flk": 4, "sh": 4, "mli": 5, "view": 6}


def identity(doc_id):
    """doc id -> (work id, variant, part_of). Language is a column of doc already."""
    x, part_of, variants = doc_id, None, []
    if FRAG.search(x):
        part_of = FRAG.sub("", x)
        x = part_of
    had_lang = bool(LANG.search(x))
    x = LANG.sub("", x)
    if had_lang and x.endswith(".mli"):
        x, variants = x[:-4], variants + ["mli"]
    while VARIANT.search(x):
        variants.append(VARIANT.search(x).group(1))
        x = VARIANT.sub("", x)
    if VIEW.search(x) and not x.startswith(("treaty.", "intl.")):
        variants.append("view")
        x = VIEW.sub("", x)
    return x, "+".join(variants), part_of


# ---------------------------------------------------------------- retrieval units
CJK = re.compile(r"[㐀-鿿豈-﫿]")
MAX_CJK, MAX_LAT = 260, 700          # about 100 words of English; similar reading load in Chinese
BLOCK = re.compile(r"(?m)^(?=(?:—)?\(\d+[A-Z]*\)|\([a-z]{1,4}\)\s|\([ivx]{1,6}\)\s|（[一二三四五六七八九十]+）|"
                   r"[一二三四五六七八九十]+、|第[一二三四五六七八九十百零〇\d]+[条款项]|\d+(?:\.\d+)*\s|[a-z]\)\s|Article \d+)")
SENT = re.compile(r"(?<=[。；;！？!?])|(?<=\.)\s+(?=[A-Z(“\"])|(?<=:)\n")


def lang_of(text):
    n = len(text) or 1
    return "zh" if len(CJK.findall(text[:2000])) / min(n, 2000) > 0.2 else "en"


def split_units(text, lang):
    """Verbatim spans [start, end) covering the text without gaps."""
    cap = MAX_CJK if lang == "zh" else MAX_LAT
    n = len(text)
    if n <= cap * 1.4:
        return [(0, n, "clause")]
    cuts = sorted({0, n} | {m.start() for m in BLOCK.finditer(text)})
    blocks = [(a, b) for a, b in zip(cuts, cuts[1:]) if b > a]
    pieces = []
    for a, b in blocks:
        if b - a <= cap:
            pieces.append((a, b))
            continue
        sc = sorted({a, b} | {a + m.end() for m in SENT.finditer(text[a:b])})
        pieces += [(x, y) for x, y in zip(sc, sc[1:]) if y > x]
    out, cur_a, cur_b = [], None, None
    for a, b in pieces:                          # merge small neighbours up to the cap, hard-cut what is still too long
        if cur_a is None:
            cur_a, cur_b = a, b
        elif b - cur_a <= cap:
            cur_b = b
        else:
            out.append((cur_a, cur_b))
            cur_a, cur_b = a, b
    if cur_a is not None:
        out.append((cur_a, cur_b))
    final = []
    for a, b in out:
        while b - a > cap * 1.5:
            final.append((a, a + cap))
            a += cap
        final.append((a, b))
    return [(a, b, "part") for a, b in final if text[a:b].strip()]


def fts_tokens(text):
    """CJK runs as overlapping character bigrams (single characters stay), everything else as words."""
    out = []
    for run in re.findall(r"[㐀-鿿豈-﫿]+|[A-Za-z0-9À-ɏḀ-ỿ]+", text):
        if CJK.match(run):
            out += [run] if len(run) == 1 else [run[i:i + 2] for i in range(len(run) - 1)]
        else:
            out.append(run.lower())
    return " ".join(out)


# ---------------------------------------------------------------- cross-references (I15: explicit references only)
CN_NUM = r"[一二三四五六七八九十百零〇两\d]+"
DEF_SHORT_EN = re.compile(r"([A-Z][\w ()\.,’'\-]{3,90}?(?:Ordinance|Act)(?:\s\d{4})?(?:\s\(Cap\.?\s?\d+[A-Z]*\))?)\s*\((?:the\s)?[“\"]([A-Z][A-Za-z]{1,7})[”\"]\)")
ABBREV_OF = re.compile(r"\s+of\s+(?:the\s+)?([A-Z]{2,8})\b")
DEF_SHORT = re.compile(r"《([^》]{2,90})》(?:及[^（(]{0,12})?[（(](?:([^，,（）()]{2,30}?号)[，,]\s*)?以下简称[《“\"]([^》”\"]{1,20})[》”\"]")
ACT_WORD = re.compile(r"(?:法|条例|细则|办法|规定|规则|通知|公告|决定|协定|安排|议定书|公约|指南|解释)$")
CN_ORDINAL = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6}
CN_REF = re.compile(r"(?P<act>《[^》\n]{2,60}》)?(?P<self>本法|本条例|本细则|本办法|本规定|本公告|本通知|本协定|本安排|本议定书)?"
                    r"第(?P<art>" + CN_NUM + r")条(?:第(?P<para>" + CN_NUM + r")款)?(?:第[（(]?(?P<item>" + CN_NUM + r")[）)]?项)?")
EN_SEC = re.compile(r"\b(?P<kw>sections?|ss?\.)\s?(?P<no>\d+[A-Z]{0,4})(?!\.\d|\d)(?P<sub>(?:\(\w{1,5}\))*)"
                    r"(?P<more>(?:\s?(?:,|and|or|to)\s?\d+[A-Z]{0,4}(?:\(\w{1,5}\))*)*)"
                    r"(?P<of>\s+of\s+(?:the\s+)?(?P<act>[A-Z][\w’'()\-. ]{2,90}?(?:Ordinance|Act|Order|Regulations|Rules)(?:\s\d{4})?(?:\s\(Cap\.?\s?\d+[A-Z]*\))?))?")
AMEND_NOTE = re.compile(r"(?:\b\d+|L\.N\.\s?\d+) of \d{4}\s*$")
SEC_QUALIFIER = re.compile(r"\s*,?\s*(?:of|in|to|under)\s+(?:(?:this|that|the said|the)\s+(?:Schedule|Part|Division|Order|Annex|Appendix|"
                           r"Protocol|Rules|Regulations|Notice|Form|Guide)\b|Schedule\s+(?P<sch>\d+[A-Z]{0,3})\b|Part\s+\d+|(?:L\.N\.\s?)?\d+\s+of\s+\d{4}\b)")
EN_SCH = re.compile(r"\b(?:Schedule|Sch\.)\s?(?P<no>\d+[A-Z]{0,3})\b|\b(?P<ord>First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth)\s+Schedule\b")
EN_ART = re.compile(r"\bparagraph\s(?P<para>\d+)\sof\sArticle\s(?P<art>\d+)\b|\bArticle\s(?P<art2>\d+[A-Z]?)(?:\s?\((?P<para2>\d+)\))?")
ORD = {"First": 1, "Second": 2, "Third": 3, "Fourth": 4, "Fifth": 5, "Sixth": 6, "Seventh": 7, "Eighth": 8, "Ninth": 9, "Tenth": 10}
CAP = re.compile(r"\(Cap\.?\s?(\d+[A-Z]*)\)|第\s?(\d+[A-Z]*)\s?章")

# default law of a guidance text (Sannier et al.'s "same law" context): only when the text names that law
DEFAULT_LAW = {"hk": ("hk.cap112", ("Inland Revenue Ordinance", "稅務條例")),
               "sg": ("sg.ita1947", ("Income Tax Act",))}


class Resolver:
    def __init__(self, con):
        self.frags = defaultdict(set)               # expr -> fragments present
        self.expr_work, self.expr_lang, self.work_exprs = {}, {}, defaultdict(list)
        for cite, doc in con.execute("SELECT cite_id, doc_id FROM clause"):
            self.frags[doc].add(cite.split("#", 1)[1])
        for e, w, lang, canon in con.execute("SELECT expr_id, work_id, lang, canonical FROM expression"):
            self.expr_work[e], self.expr_lang[e] = w, lang
            self.work_exprs[w].append((0 if canon else 1, e))
        self.alias = {}
        for a, w in con.execute("SELECT alias, work_id FROM alias"):
            self.alias[a] = w
        self.doc_type = dict(con.execute("SELECT id, type FROM doc"))
        self.local = {}
        self.by_docno = {}
        for did, docno in con.execute("SELECT id, doc_no FROM doc WHERE doc_no != ''"):
            self.by_docno.setdefault(re.sub(r"\s+", "", docno), self.expr_work.get(did))
        self.title_protocol = {}
        work_ids = {w for (w,) in con.execute("SELECT work_id FROM work")}
        self.title_treaty = {}                      # expression -> the treaty its title names in 《》
        for did, title in con.execute("SELECT id, title FROM doc"):
            for name in re.findall(r"[《〈]([^》〈〉]+)[》〉]", title or ""):
                w = self.alias.get(re.sub(r"\s+", "", name))
                if w and w.startswith("treaty."):
                    self.title_treaty[did] = w
                    pm = re.search(r"》\s*(?:及)?第([一二三四五六])议定书", title or "")
                    if pm and "%s.p%d" % (w, CN_ORDINAL[pm.group(1)]) in work_ids:
                        self.title_protocol[did] = "%s.p%d" % (w, CN_ORDINAL[pm.group(1)])
                    break

    def expr_for(self, work, lang, frag=None):
        """Expression of a work to point at: same language and holding the fragment first, then any holding it."""
        cands = sorted(self.work_exprs.get(work, []))
        same = [e for _, e in cands if self.expr_lang[e][:2] == (lang or "")[:2]]
        for pool in (same, [e for _, e in cands]):
            for e in pool:
                if frag is None or frag in self.frags[e]:
                    return e
        return (same or [e for _, e in cands] or [None])[0]

    def define_shorts(self, expr, text):
        """Short names a document defines for the instruments it cites (Sannier et al.: per-document name lists)."""
        out = self.local.setdefault(expr, {})
        for m in DEF_SHORT_EN.finditer(text):
            out[m.group(2)] = self.act(m.group(1))
        for m in DEF_SHORT.finditer(text):
            name, docno, short = (re.sub(r"\s+", "", x or "") for x in m.groups())
            w = self.by_docno.get(docno) if docno else None
            w = w or self.alias.get(name) or self.alias.get(re.sub(r"^中华人民共和国", "", name))
            out[short] = w                          # None: defined, but the instrument is not in the library

    def act(self, text, expr=None):
        t = re.sub(r"\s+", "", text).strip("《》")
        local = self.local.get(expr, {})
        if t in local:
            return local[t]
        if t in self.alias:
            return self.alias[t]
        m = CAP.search(text)
        if m:
            cap = (m.group(1) or m.group(2)).lower()
            return self.alias.get("cap" + cap)
        t2 = re.sub(r"\(.*?\)|（.*?）", "", t)
        return self.alias.get(t2)

    def target(self, expr, frags):
        """First fragment (most specific first) present in expr -> (cite, 'resolved'|'ancestor')."""
        for i, f in enumerate(frags):
            if f in self.frags.get(expr, ()):
                return "%s#%s" % (expr, f), ("resolved" if i == 0 else "ancestor")
        return None, None


def extract_refs(cite, expr, text, lang, R, doc_text_has):
    """Yield edge rows for explicit references in one clause."""
    work = R.expr_work[expr]
    rows = []
    if lang == "zh":
        for m in CN_REF.finditer(text):
            if m.start() <= 2 and not m.group("act") and not m.group("self"):
                continue                            # the clause's own heading ("第十三条 财产收益"), not a reference
            art = str(cn2int(m.group("art")))
            frags = []
            if m.group("para"):
                frags.append("%s.%s" % (art, cn2int(m.group("para"))))
            frags.append(art)
            tgt_work, rule = work, "cn.internal"
            if m.group("act"):
                tgt_work, rule = R.act(m.group("act"), expr), "cn.named_act"
            elif m.group("self") in ("本协定", "本安排") and not work.startswith("treaty."):
                # a notice explaining a treaty says "本协定" for that treaty: the treaty its own title names
                tgt_work, rule = R.title_treaty.get(expr), "cn.title_treaty"
            elif m.group("self") == "本议定书" and not work.startswith("treaty."):
                tgt_work, rule = R.title_protocol.get(expr), "cn.title_protocol"
            elif not m.group("self"):
                run = re.search(r"[\u4e00-\u9fff]+$", text[max(0, m.start() - 30):m.start()])
                if run:                       # longest act name from the alias list ending right before "第X条"
                    s0 = run.group(0)
                    local = R.local.get(expr, {})
                    for i in range(len(s0) - 1):
                        cand = s0[i:]
                        if cand in local and local[cand]:
                            tgt_work, rule = local[cand], "cn.defined_short"
                            break
                        if cand in R.alias:
                            tgt_work, rule = R.alias[cand], "cn.bare_act"
                            break
                        if cand in ("实施条例", "实施细则"):
                            near = text[max(0, m.start() - 80):m.start()]
                            if cand == "实施条例" and ("所得税法" in near or doc_text_has("企业所得税法实施条例")):
                                tgt_work, rule = "cn.reg.eit", "cn.context_act"
                                break
                            if cand == "实施细则" and ("征管法" in near or "税收征收管理法" in near):
                                tgt_work, rule = "cn.reg.tca", "cn.context_act"
                                break
                        if cand in ("协定", "安排") and not work.startswith("treaty."):
                            tgt_work, rule = R.title_treaty.get(expr), "cn.title_treaty"
                            break
                        if cand == "议定书" and not work.startswith("treaty."):
                            tgt_work, rule = R.title_protocol.get(expr), "cn.title_protocol"
                            break
                    else:
                        if ACT_WORD.search(s0):     # an instrument is named but not known here: never read it as internal
                            tgt_work, rule = None, "cn.unknown_act"
                if rule == "cn.internal" and not work.startswith("treaty.") and (R.title_protocol.get(expr) or R.title_treaty.get(expr)):
                    # a notice explaining a treaty or protocol numbers its parts after that instrument's articles
                    tgt_work, rule = R.title_protocol.get(expr) or R.title_treaty.get(expr), "cn.title_implicit"
            if tgt_work is None:
                rows.append(("unresolved:" + text[max(0, m.start() - 12):m.end()].split("\n")[-1], "cites", "unresolved", m, rule))
                continue
            e = expr if (tgt_work == work and any(f in R.frags.get(expr, ()) for f in frags)) else R.expr_for(tgt_work, "zh", frags[-1])
            dst, status = R.target(e, frags) if e else (None, None)
            if dst is None:
                if m.group("act"):
                    rows.append(("work:" + tgt_work, "cites_act", "act_only", m, rule))
                elif rule == "cn.internal":
                    continue                     # a bare "第X条" with no such article here: not a reference we can place
                else:
                    rows.append(("unresolved:" + m.group(0), "cites", "unresolved", m, rule))
                continue
            if dst == cite:
                continue
            rows.append((dst, "cites", status, m, rule))
        return rows
    # English: sections, schedules, treaty articles
    law_ctx = None
    jur = work.split(".")[0]
    if jur in DEFAULT_LAW and not work.startswith(DEFAULT_LAW[jur][0]) and R.doc_type.get(expr) != "form":
        w, names = DEFAULT_LAW[jur]
        if any(doc_text_has(nm) for nm in names):
            law_ctx = w
    for m in EN_SEC.finditer(text):
        nos = [m.group("no")] + re.findall(r"\d+[A-Z]{0,4}", re.sub(r"\(\w{1,5}\)", "", m.group("more") or ""))
        subs = re.findall(r"\((\w{1,5})\)", m.group("sub") or "")
        tail = text[m.end():m.end() + 60]
        if AMEND_NOTE.search(text[max(0, m.start() - 30):m.start()]):
            continue                                # "(Added 4 of 1998 s. 6)": a section of the amending Ordinance
        if not m.group("act"):
            q = SEC_QUALIFIER.match(tail)
            if q:                                   # "section 6 of this Schedule": a section of something else
                if q.group("sch"):
                    e = R.expr_for(work, lang, "sch" + q.group("sch"))
                    dst, status = R.target(e, ["sch" + q.group("sch")]) if e else (None, None)
                    if dst and dst != cite:
                        rows.append((dst, "cites", "ancestor", m, "en.section_of_schedule"))
                continue
        in_schedule = cite.split("#", 1)[1].startswith("sch")
        if in_schedule and not m.group("act") and not re.match(r"\s*,?\s*of (?:this|the) Ordinance|\s*,?\s*of (?:this|the) Act", tail):
            continue
        sch_of_act = re.match(r"Schedule\s+(\d+[A-Z]{0,3})\s+to\s+(?:the\s+)?(.+)$", m.group("act") or "")
        if sch_of_act:
            w = R.act(sch_of_act.group(2))
            e = R.expr_for(w, lang, "sch" + sch_of_act.group(1)) if w else None
            dst, status = R.target(e, ["sch" + sch_of_act.group(1)]) if e else (None, None)
            rows.append((dst or "unresolved:" + m.group("act"), "cites", "ancestor" if dst else "unresolved", m, "en.section_of_schedule_of_act"))
            continue
        ab = ABBREV_OF.match(tail)
        if not m.group("act") and ab:               # "section 23 of the SFO": an abbreviation names the Act
            short = ab.group(1)
            w = R.local.get(expr, {}).get(short, R.alias.get(short, "?"))
            if w in (None, "?"):
                rows.append(("unresolved:%s s%s" % (short, nos[0]), "cites", "unresolved", m, "en.abbreviation"))
                continue
            tgt_work, rule = w, "en.abbreviation"
        elif m.group("act"):
            tgt_work, rule = R.act(m.group("act")), "en.named_act"
        elif any(re.match(r"s\d", f) for f in R.frags.get(expr, ())):
            tgt_work, rule = work, "en.internal"          # a statute sliced by sections cites its own sections
        else:
            tgt_work, rule = law_ctx, "en.context_law"
        if tgt_work is None:
            if m.group("act"):
                rows.append(("unresolved:" + m.group("act"), "cites_act", "unresolved", m, rule))
            continue
        for k, no in enumerate(nos):
            frags = ["s%s(%s)" % (no, ")(".join(subs))] if (subs and k == 0) else []
            frags.append("s" + no)
            e = expr if (tgt_work == work and frags[-1] in R.frags.get(expr, ())) else R.expr_for(tgt_work, lang, frags[-1])
            dst, status = R.target(e, frags) if e else (None, None)
            if dst is None:
                rows.append(("unresolved:%s s%s" % (tgt_work, no), "cites", "unresolved", m, rule))
            elif dst != cite:
                rows.append((dst, "cites", status, m, rule))
    for m in EN_SCH.finditer(text):
        no = m.group("no") or str(ORD[m.group("ord")])
        tgt_work = work if any(f.startswith("sch") for f in R.frags.get(expr, ())) else law_ctx
        if tgt_work is None:
            continue
        e = R.expr_for(tgt_work, lang, "sch" + no)
        dst, status = R.target(e, ["sch" + no]) if e else (None, None)
        if dst is None:
            rows.append(("unresolved:%s sch%s" % (tgt_work, no), "cites", "unresolved", m, "en.schedule"))
        elif dst != cite:
            rows.append((dst, "cites", status, m, "en.schedule"))
    if work.startswith("treaty."):
        for m in EN_ART.finditer(text):
            if m.start() == 0 or text[m.start() - 1] == "\n" or re.match(r"\s*[-–]?\s*[A-Z]{3,}", text[m.end():m.end() + 12]):
                continue                            # an article heading, not a reference
            tail = text[m.end():m.end() + 80]
            if re.match(r"\s*of\s+\[?(?:the |this )?(?:[A-Z]\w+ )?(?:Protocol|Convention|Multilateral|MLI)", tail) or \
                    re.match(r"\s*of\s+\[?the\s+(?:[A-Z][\w\-]+\s+)+(?:Arrangement|Agreement)", tail):
                continue                            # an article of another instrument
            art, para = (m.group("art"), m.group("para")) if m.group("art") else (m.group("art2"), m.group("para2"))
            frags = (["%s.%s" % (art, para)] if para else []) + [art]
            target_expr = expr
            if re.search(r"\.p\d+", expr) and not re.match(r"\s*of\s+this\s+Protocol", tail):
                base = re.match(r"^(treaty\.[a-z\-]+\.\d{4})", work).group(1)   # a protocol citing the treaty it amends
                target_expr = R.expr_for(base, lang, frags[-1])
            dst, status = R.target(target_expr, frags) if target_expr else (None, None)
            if dst and dst != cite:
                rows.append((dst, "cites", status, m, "treaty.internal" if target_expr == expr else "treaty.protocol_to_base"))
    return rows


# ---------------------------------------------------------------- definitions
DEF_EN_HK = re.compile(r"(?m)^(?P<term>[a-z][a-z0-9 \-’'/]{1,70}?) \((?P<equiv>[一-鿿][^)\n]{0,40})\)(?=[ ,]|$)")
DEF_EN_Q = re.compile(r"(?m)^\s*[“\"](?P<term>[^”\"\n]{2,80})[”\"]\s*(?:\((?P<equiv>[^)\n]{1,60})\))?\s*,?\s*(?:in relation to [^\n]{1,120}?,\s*)?(?:means|includes|has the (?:same )?meaning)")
DEF_ZH_HK = re.compile(r"(?m)^(?P<term>[一-鿿]{2,30}) \((?P<equiv>[a-z][a-z0-9 \-’'/]{1,70})\)")
DEF_CN = re.compile(r"(?:本(?:法|条例|细则|办法|公告|通知|规定)|前款)?所称(?P<term>[一-鿿“”]{2,40}?)，(?:是指|包括)")


def extract_terms(cite, text, lang):
    out = []
    pats = [("cn.so_called", DEF_CN)] if lang == "zh" else [("en.quoted", DEF_EN_Q), ("hk.en_with_zh", DEF_EN_HK)]
    if lang == "zh":
        pats.append(("hk.zh_with_en", DEF_ZH_HK))
    for rule, p in pats:
        for m in p.finditer(text):
            term = m.group("term").strip().strip("“”")
            equiv = (m.groupdict().get("equiv") or "").strip()
            if rule == "hk.en_with_zh" and len(term.split()) > 8:
                continue
            out.append((term, lang, equiv, cite, m.start("term"), m.end("term"), rule))
    return out


# ---------------------------------------------------------------- anchors
def anchor(text, quote):
    """Exact span of quote in text, comparing with whitespace removed (the build-time rule); -> (start, end, n)."""
    keep = [i for i, ch in enumerate(text) if not ch.isspace()]
    flat = "".join(text[i] for i in keep)
    q = re.sub(r"\s+", "", quote or "")
    if not q:
        return None, None, 0
    pos = [m.start() for m in re.finditer(re.escape(q), flat)]
    if not pos:
        return None, None, 0
    return keep[pos[0]], keep[pos[0] + len(q) - 1] + 1, len(pos)


# ---------------------------------------------------------------- rules (compiled layer -> edges)
def rule_edges():
    """rule -> clause (condition cites) and rule -> param (value, uses, thresholds) from the compiled rule layer."""
    try:
        sys.path.insert(0, str(PROJECT))
        from tax_graph.rules.spec import SPEC
        from tax_graph.rules.model import leaves
    except Exception as e:                                   # noqa: BLE001
        print("  ! rule edges skipped: %r" % e)
        return []
    rows = []
    for r in SPEC:
        src = "rule:" + r.id
        for leaf in (leaves(r.cond) if r.cond is not None else []):
            for c in getattr(leaf, "cites", ()) or ():
                rows.append((src, c, "rule_cites"))
            if getattr(leaf, "param", None):
                rows.append((src, "param:" + leaf.param, "rule_uses_param"))
        for pid in ([r.value] if isinstance(r.value, str) and not r.value.startswith("observed:") else []) + list(r.uses or ()):
            rows.append((src, "param:" + pid, "rule_uses_param"))
        if getattr(r, "before", ()):                             # 口径 D30: the law's commencement clause
            rows.append((src, r.before[1], "rule_cites"))
    return rows


# ---------------------------------------------------------------- main
def build(dense=False):
    con = sqlite3.connect(str(DB))
    con.execute("PRAGMA foreign_keys = OFF")
    for t in DROP:
        con.execute("DROP TABLE IF EXISTS %s" % t)
    con.executescript(BASE_INDEXES)
    con.executescript(SCHEMA)
    problems = []

    docs = {r[0]: r for r in con.execute("SELECT id, jur, type, title, lang, alias_of, parent, effective_from, "
                                          "effective_to, issued, sha256 FROM doc")}
    clauses = con.execute("SELECT cite_id, doc_id, kind, label, parent, text FROM clause").fetchall()
    n_by_doc = Counter(c[1] for c in clauses)

    # work / expression
    works, exprs = {}, []
    for d, (did, jur, typ, title, lang, alias_of, parent, eff_from, eff_to, issued, sha) in docs.items():
        w, variant, part_of = identity(did)
        works.setdefault(w, (w, jur, typ, title))
        exprs.append([did, w, lang, variant, 0, part_of, alias_of or None, eff_from or None, eff_to or None, sha])   # no date stated: unknown, not the signing date
    best = {}
    for e in exprs:                       # canonical: per (work, language), the fullest non-derivative variant
        key = (e[1], (e[2] or "")[:2])
        rank = (max(VARIANT_RANK.get(v, 3) for v in (e[3] or "").split("+")), -n_by_doc[e[0]], e[0])
        if e[5] is None and (key not in best or rank < best[key][0]):
            best[key] = (rank, e[0])
    canon = {v[1] for v in best.values()}
    for e in exprs:
        e[4] = int(e[0] in canon)
    con.executemany("INSERT INTO work VALUES (?,?,?,?)", list(works.values()))
    con.executemany("INSERT INTO expression VALUES (?,?,?,?,?,?,?,?,?,?,'current')", exprs)
    expr_work = {e[0]: e[1] for e in exprs}

    # aliases: curated list + titles of statutes
    alias_rows = []
    for r in read_csv(ROOT / "aliases.csv"):
        alias_rows.append((re.sub(r"\s+", "", r["alias"]).strip("《》"), r["work_id"], r["lang"], "aliases.csv"))
    for did, (_, jur, typ, title, lang, *_rest) in docs.items():
        if typ in ("law", "regulation", "treaty") and title:
            t = re.sub(r"\s+", "", re.split(r"\s[-–(（]\s?|（", title)[0]).strip("《》")
            if len(t) >= (5 if CJK.search(t) else 8):
                alias_rows.append((t, expr_work[did], lang, "title"))
            if t.startswith("中华人民共和国") and len(t) > 9:
                alias_rows.append((t[7:], expr_work[did], lang, "title.short"))
            m = re.search(r"\bCap\.?\s?(\d+[A-Z]*)", title)
            if m:
                alias_rows.append(("cap" + m.group(1).lower(), expr_work[did], lang, "title.cap"))
    con.executemany("INSERT INTO alias VALUES (?,?,?,?)", alias_rows)

    # provisions, clause metadata, units, fts
    prov_exprs = defaultdict(set)
    meta, units, fts = [], [], []
    by_cite = {c[0]: c for c in clauses}
    for cite, did, kind, label, parent, text in clauses:
        frag = cite.split("#", 1)[1]
        pid = "%s#%s" % (expr_work[did], frag)
        prov_exprs[pid].add(did)
        path, p, depth = [label], parent, 0
        while p and p in by_cite and depth < 8:
            path.insert(0, by_cite[p][3])
            p, depth = by_cite[p][4], depth + 1
        lang = (docs[did][4] or lang_of(text))[:2]
        meta.append((cite, did, pid, depth, " > ".join(path), lang, hashlib.sha1(text.encode("utf-8")).hexdigest()))
        header = "%s > %s" % (docs[did][3] or did, " > ".join(path))
        for seq, (a, b, ukind) in enumerate(split_units(text, lang)):
            uid = "%s~%d" % (cite, seq)
            units.append((uid, cite, seq, a, b, ukind, lang, header, hashlib.sha1(text[a:b].encode("utf-8")).hexdigest(), EXTRACTOR))
            fts.append((len(units), fts_tokens(header), fts_tokens(text[a:b])))
    con.executemany("INSERT INTO provision VALUES (?,?,?,?)",
                    [(p, p.split("#", 1)[0], p.split("#", 1)[1], len(es)) for p, es in prov_exprs.items()])
    con.executemany("INSERT INTO clause_meta VALUES (?,?,?,?,?,?,?)", meta)
    con.executemany('INSERT INTO unit VALUES (?,?,?,?,?,?,?,?,?,?)', units)
    con.executemany("INSERT INTO unit_fts(rowid, header, body) VALUES (?,?,?)", fts)

    # edges
    edges = []
    for cite, did, kind, label, parent, text in clauses:
        if parent:
            edges.append((parent, cite, "contains", "resolved", None, None, None, "slice.parent", EXTRACTOR))
    for pid, es in prov_exprs.items():
        members = sorted(c for c in (f"{e}#{pid.split('#', 1)[1]}" for e in es))
        for a in members:
            for b in members:
                if a < b:
                    edges.append((a, b, "same_provision", "resolved", pid, None, None, "provision", EXTRACTOR))
    for did, (_, jur, typ, title, lang, alias_of, parent, *_r) in docs.items():
        if parent:
            edges.append(("doc:" + did, "doc:" + parent, "attachment_of", "resolved", None, None, None, "doc.parent", EXTRACTOR))
        if alias_of:
            edges.append(("doc:" + did, "doc:" + alias_of, "same_manifestation", "resolved", None, None, None, "doc.alias_of", EXTRACTOR))
        w, variant, part_of = identity(did)
        if part_of:
            edges.append(("doc:" + did, "doc:" + part_of, "part_of", "resolved", None, None, None, "frag", EXTRACTOR))
        m = re.match(r"^(treaty\.[a-z\-]+\.\d{4})\.p\d+", did)
        if m:
            edges.append(("work:" + w, "work:" + m.group(1), "amends", "resolved", None, None, None, "treaty.protocol", EXTRACTOR))
        if did.endswith(".interp"):
            edges.append(("doc:" + did, "doc:" + did[:-7], "interprets", "resolved", None, None, None, "doc.interp", EXTRACTOR))
    R = Resolver(con)
    doc_text = defaultdict(str)
    for cite, did, kind, label, parent, text in clauses:
        if len(doc_text[did]) < 400000:
            doc_text[did] += text[:20000]
    for cite, did, kind, label, parent, text in clauses:
        R.define_shorts(did, text)
    xref_stats = Counter()
    for cite, did, kind, label, parent, text in clauses:
        lang = R.expr_lang.get(did, "en")[:2]
        has = (lambda s, d=did: s in doc_text[d])
        for dst, k, status, m, rule in extract_refs(cite, did, text, lang, R, has):
            xref_stats[(k, status)] += 1
            edges.append((cite, dst, k, status, m.group(0)[:120], m.start(), m.end(), rule, EXTRACTOR))
    for p in con.execute("SELECT param_id, cite_id FROM param"):
        edges.append(("param:" + p[0], p[1], "param_cites", "resolved", None, None, None, "params.csv", EXTRACTOR))
    for g in con.execute("SELECT new_id, cite_id FROM gap"):
        if g[1]:
            edges.append(("gap:" + g[0], g[1], "gap_cites", "resolved", None, None, None, "gaps.csv", EXTRACTOR))
    known = {c[0] for c in clauses}
    known_params = {r[0] for r in con.execute("SELECT param_id FROM param")}
    for src, dst, k in rule_edges():
        ok = (dst in known) if k == "rule_cites" else (dst[6:] in known_params)
        edges.append((src, dst, k, "resolved" if ok else "unresolved", None, None, None, "tax_graph.rules", EXTRACTOR))
        if not ok:
            pass                                                # reported by constraint E03
    con.executemany("INSERT INTO edge VALUES (?,?,?,?,?,?,?,?,?)", edges)

    # terms
    terms = []
    for cite, did, kind, label, parent, text in clauses:
        terms += extract_terms(cite, text, R.expr_lang.get(did, "en")[:2])
    con.executemany("INSERT INTO term VALUES (?,?,?,?,?,?,?)", terms)

    # events, tombstones, clause time
    events, since_of = [], {}
    for r in read_csv(ROOT / "superseded.csv"):
        target = "%s#%s" % (r["doc_id"], r["clause"]) if r["clause"] not in ("", "*") else r["doc_id"]
        kind = "substitution" if re.search(r"替换|替代|取代|replaced|substitut", r["note"] or "") else "repeal"
        events.append((kind, target, r["by"], r["since"], r["note"] + ((" | phrase: " + r["phrase"]) if r.get("phrase") else ""), "superseded.csv"))
        if r["by"] and r["since"]:
            since_of[r["by"]] = max(since_of.get(r["by"], ""), r["since"])
            if r["by"] in known:
                edges_sub = (r["by"], target, "substitutes", "resolved", None, None, None, "superseded.csv", EXTRACTOR)
                con.execute("INSERT INTO edge VALUES (?,?,?,?,?,?,?,?,?)", edges_sub)
    stub_path = ROOT / "repealed_stubs.csv"
    if stub_path.exists():
        for r in read_csv(stub_path):
            events.append(("repeal", r["cite_id"], "", "", r["text"], "repealed_stubs.csv"))
    tombs = []
    for r in read_csv(ROOT / "removed.csv"):
        m = re.search(r"自\s?(\d{4}-\d{2}-\d{2})\s?起", r["reason"])
        by = re.search(r"被(.+?)取代", r["reason"])
        tombs.append((r["id"], r["title"], r["reason"], r["removed_at"], m.group(1) if m else None, by.group(1) if by else None))
        events.append(("repeal", r["id"], by.group(1) if by else "", m.group(1) if m else "", r["reason"], "removed.csv"))
    con.executemany("INSERT INTO event VALUES (?,?,?,?,?,?)", events)
    con.executemany("INSERT INTO tombstone VALUES (?,?,?,?,?,?)", tombs)
    expr_time = {e[0]: (e[7], e[8]) for e in exprs}
    times = []
    for cite, did, *_ in clauses:
        vf, vt = expr_time[did]
        basis = "expression" if vf else "unknown"
        if cite in since_of and (not vf or since_of[cite] > vf):
            vf, basis = since_of[cite], "superseded.csv"
        times.append((cite, vf, vt, basis))
    con.executemany("INSERT INTO clause_time VALUES (?,?,?,?,NULL,NULL)", times)

    # anchors
    text_of = {c[0]: c[5] for c in clauses}
    anchors = []
    for owner, cid, quote in list(con.execute("SELECT 'param:'||param_id, cite_id, quote FROM param")) + \
            list(con.execute("SELECT 'gap:'||new_id, cite_id, quote FROM gap")):
        if not quote:
            anchors.append((owner, cid, None, None, 0, "no_quote"))
            continue
        a, b, n = anchor(text_of.get(cid, ""), quote)
        status = "missing" if a is None else ("unique" if n == 1 else "ambiguous")
        anchors.append((owner, cid, a, b, n, status))

    # decisions (口径): anchored like params; the engine's code names them
    dec_path = ROOT / "decisions.csv"
    decisions = read_csv(dec_path) if dec_path.exists() else []
    con.executemany("INSERT INTO decision VALUES (?,?,?,?,?,?)",
                    [(r["id"], int(r["seq"]), r["statement"], r["cite_id"], r["quote"], r["used_in"]) for r in decisions])
    for r in decisions:
        a, b, n = anchor(text_of.get(r["cite_id"], ""), r["quote"])
        anchors.append(("decision:%s.%s" % (r["id"], r["seq"]), r["cite_id"], a, b, n,
                        "missing" if a is None else ("unique" if n == 1 else "ambiguous")))
    con.executemany("INSERT INTO edge VALUES (?,?,?,?,?,?,?,?,?)",
                    [("decision:" + r["id"], r["cite_id"], "decision_cites", "resolved", None, None, None, "decisions.csv",
                      EXTRACTOR) for r in decisions])
    con.executemany("INSERT INTO anchor VALUES (?,?,?,?,?,?)", anchors)
    refs = []
    for py in sorted((PROJECT / "tax_graph").rglob("*.py")):
        for i, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            for m in re.finditer(r"口径\s?(D\d{2})", line):
                refs.append((m.group(1), "%s:%d" % (py.relative_to(PROJECT).as_posix(), i)))
    con.executemany("INSERT INTO decision_ref VALUES (?,?)", refs)
    if (ROOT / "verify.csv").exists():
        con.executemany("INSERT OR REPLACE INTO verify_result VALUES (?,?,?)",
                        [(r["id"], r["match"], r["checked_at"]) for r in read_csv(ROOT / "verify.csv")])

    # integrity and quality: declarative constraints (Errors stop the build's exit status; Warnings are reported)
    fk = con.execute("PRAGMA foreign_key_check").fetchall()
    if fk:
        problems.append("%d foreign-key violations" % len(fk))
    results = []
    for cid_, sev, what, sql in CONSTRAINTS:
        rows_ = [r[0] for r in con.execute(sql).fetchall()]
        results.append((cid_, sev, what, len(rows_), "; ".join(map(str, rows_[:5]))))
        if sev == "Error" and rows_:
            problems.append("%s %s: %d (%s)" % (cid_, what, len(rows_), "; ".join(map(str, rows_[:3]))))
    con.executemany("INSERT INTO constraint_result VALUES (?,?,?,?,?)", results)
    con.commit()

    if dense:
        build_vectors(con, dense)
    stats = report(con, xref_stats, problems)
    con.close()
    return stats, problems


DEFAULT_DENSE = "BAAI/bge-m3"


def build_vectors(con, model_name=DEFAULT_DENSE):
    """Dense vectors per unit (header + text), cached by text hash so a rebuild only embeds what changed."""
    import numpy as np
    cache_path = ROOT / "_index" / "vec_cache.sqlite"
    cache_path.parent.mkdir(exist_ok=True)
    cache = sqlite3.connect(str(cache_path))
    cache.execute("CREATE TABLE IF NOT EXISTS vec (key TEXT PRIMARY KEY, dim INTEGER, vec BLOB)")
    rows = con.execute("SELECT u.unit_id, u.header, substr(c.text, u.start + 1, u.\"end\" - u.start) "
                       "FROM unit u JOIN clause c ON c.cite_id = u.cite_id").fetchall()
    keys = [hashlib.sha1((model_name + "\n" + h + "\n" + t).encode("utf-8")).hexdigest() for _, h, t in rows]
    have = {k for (k,) in cache.execute("SELECT key FROM vec")}
    todo = [(k, h + "\n" + t) for k, (_, h, t) in zip(keys, rows) if k not in have]
    if todo:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(model_name)
        model.max_seq_length = min(model.max_seq_length or 512, 512)    # units are about 100 words
        for i in range(0, len(todo), 512):
            chunk = todo[i:i + 512]
            vecs = model.encode([t for _, t in chunk], batch_size=64, normalize_embeddings=True, show_progress_bar=False)
            cache.executemany("INSERT OR REPLACE INTO vec VALUES (?,?,?)",
                              [(k, v.shape[0], v.astype("float32").tobytes()) for (k, _), v in zip(chunk, vecs)])
            cache.commit()
    con.execute("CREATE TABLE unit_vec (unit_id TEXT PRIMARY KEY, model TEXT, vec BLOB)")
    got = dict(cache.execute("SELECT key, vec FROM vec"))
    con.executemany("INSERT INTO unit_vec VALUES (?,?,?)", [(u, model_name, got[k]) for (u, _, _), k in zip(rows, keys)])
    con.commit()
    cache.close()
    print("  dense: %d units, %d newly embedded" % (len(rows), len(todo)))


def report(con, xref_stats, problems):
    q = lambda s: con.execute(s).fetchall()
    lines = ["# INDEX", "", "由 `tools/graph.py` 生成，不要手改。知识层的设计、原理与依据见 [README.md](README.md) 第 3.3、6.2、7–9 节，参考文献在第 16 节。", "",
             "| 表 | 行数 |", "|---|---|"]
    for t in ("work", "expression", "provision", "clause_meta", "unit", "edge", "term", "event", "tombstone", "anchor", "alias"):
        lines.append("| %s | %d |" % (t, q("SELECT COUNT(*) FROM %s" % t)[0][0]))
    lines += ["", "## 关系（edge）", "", "| kind | status | 条数 |", "|---|---|---|"]
    for k, s, n in q("SELECT kind, status, COUNT(*) FROM edge GROUP BY kind, status ORDER BY kind, status"):
        lines.append("| %s | %s | %d |" % (k, s, n))
    lines += ["", "## 交叉引用的解析", ""]
    tot = sum(v for (k, s), v in xref_stats.items() if k == "cites")
    res = sum(v for (k, s), v in xref_stats.items() if k == "cites" and s in ("resolved", "ancestor"))
    lines.append("显式引用 %d 条，解析到条款 %d 条（其中只到上级条款的 %d 条），未解析 %d 条；未解析的保留原文，不猜。" % (
        tot, res, xref_stats[("cites", "ancestor")], xref_stats[("cites", "unresolved")]))
    top = q("SELECT substr(dst, 12, 60), COUNT(*) n FROM edge WHERE status='unresolved' GROUP BY 1 ORDER BY n DESC LIMIT 12")
    if top:
        lines += ["", "未解析最多的目标：", ""] + ["- `%s` ×%d" % (t, n) for t, n in top]
    lines += ["", "## 检索单元", ""]
    for k, n, avg, mx in q("SELECT kind, COUNT(*), AVG(\"end\"-start), MAX(\"end\"-start) FROM unit GROUP BY kind"):
        lines.append("- %s：%d 个，平均 %d 字符，最长 %d" % (k, n, avg, mx))
    lines += ["", "## 引文锚定", ""]
    for s, n in q("SELECT status, COUNT(*) FROM anchor GROUP BY status"):
        lines.append("- %s：%d" % (s, n))
    lines += ["", "## 定义词", ""]
    for r, n in q("SELECT rule, COUNT(*) FROM term GROUP BY rule"):
        lines.append("- %s：%d" % (r, n))
    lines += ["", "## 口径（decisions.csv）", "", "| 口径 | 锚点 | 代码引用 | 内容 |", "|---|---|---|---|"]
    for did, stmt in q("SELECT id, statement FROM decision WHERE seq = 1 ORDER BY id"):
        st = q("SELECT status, COUNT(*) FROM anchor WHERE owner LIKE 'decision:%s.%%' GROUP BY status" % did)
        nref = q("SELECT COUNT(*) FROM decision_ref WHERE id = '%s'" % did)[0][0]
        lines.append("| %s | %s | %d | %s |" % (did, ", ".join("%s %d" % x for x in st), nref, stmt))
    lines += ["", "## 约束（每次构建检查；Error 使构建失败）", "", "| 约束 | 级别 | 内容 | 违反 | 示例 |", "|---|---|---|---|---|"]
    cons = q("SELECT id, severity, description, violations, sample FROM constraint_result ORDER BY id")
    for cid_, sev, what, n, sample in cons:
        lines.append("| %s | %s | %s | %d | %s |" % (cid_, sev, what, n, (sample or "")[:120].replace("|", "/")))
    metrics = {"table." + t: q("SELECT COUNT(*) FROM %s" % t)[0][0]
               for t in ("work", "expression", "clause_meta", "unit", "edge", "term", "anchor", "decision")}
    metrics.update({"constraint." + c[0]: c[3] for c in cons})
    metrics.update({"xref.total": tot, "xref.resolved": res})
    mpath = ROOT / "_index" / "metrics.json"
    import json as _json
    prev = _json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else {}
    changed = [(k, prev.get(k), v) for k, v in sorted(metrics.items()) if prev.get(k) != v]
    lines += ["", "## 与上次构建对照", ""]
    if not prev:
        lines.append("（首次记录）")
    elif not changed:
        lines.append("无变化。")
    else:
        lines += ["| 指标 | 上次 | 本次 |", "|---|---|---|"] + ["| %s | %s | %s |" % (k, "—" if a is None else a, b) for k, a, b in changed]
    mpath.parent.mkdir(exist_ok=True)
    mpath.write_text(_json.dumps(metrics, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    lines += ["", "## 检查", ""] + (["- " + p for p in problems] or ["- 无 Error。"])
    (ROOT / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dict(units=q("SELECT COUNT(*) FROM unit")[0][0], edges=q("SELECT COUNT(*) FROM edge")[0][0],
                xref_total=tot, xref_resolved=res)


def main(argv):
    dense = None
    for a in argv:                                   # --dense, --dense=MODEL; without it the last model's cache is reused
        if a == "--dense":
            dense = DEFAULT_DENSE
        elif a.startswith("--dense="):
            dense = a.split("=", 1)[1]
    marker = ROOT / "_index" / "dense_model.txt"
    if "--no-dense" in argv:
        dense = None
    elif dense:
        marker.parent.mkdir(exist_ok=True)
        marker.write_text(dense, encoding="utf-8")
    elif marker.exists():
        dense = marker.read_text(encoding="utf-8").strip()
    stats, problems = build(dense=dense)
    print("graph: units=%(units)d edges=%(edges)d cross-references=%(xref_total)d resolved=%(xref_resolved)d" % stats,
          "problems=%d" % len(problems))
    for p in problems[:20]:
        print("  !", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
