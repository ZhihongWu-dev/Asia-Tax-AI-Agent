"""The legal-reasoning extract for the second review lane (agent/orchestration_cli_spec.en.md §12): every sentence of a briefing
that states a legal reason, with what it rests on laid out verbatim, so the lane judges instead of searching.

For each sentence the program attaches the sources rows whose `where` fragment lies in it, the citations the sentence names in
words (cites_in), and, through them, the provision
texts, the rules of the rule layer that apply them (condition, effect, parameter values) and the rule layer's decisions on how the
provision is read. The provisions the recommended structure's all-favourable branch applies are laid out whether or not a sentence
names them. Nothing is judged here; a sentence with a legal reference and no row is listed as such.

  build(case_id, run_id, target="draft", lines=None) -> (path, count)
    target: draft (briefing.md) or polished (briefing.polished.md)
    lines: line numbers (1-based) of the file to keep; None = the whole file
  changed_lines(old_text, new_text) -> the line numbers of new_text that are new or changed
"""
import csv
import difflib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
LIMIT = 80000                                  # characters of the extract; provision texts are shortened first when it would pass
LAWREF = re.compile(r"(?i)\b(article|art\.|section|s\.?\s?\d|sections|paragraph|para\.?|item|schedule|chapter|announcement|circular|guoshuihan|caishui|"
                    r"law|ordinance|act\b|regulations?|rules?\b|arrangement|treaty|convention|protocol|e-tax guide|mli|cap\.?\s?\d)")
REASON = re.compile(r"(?i)\b(because|since|unless|provided|only if|only where|on condition|condition|requires?|required|at least|not less than|"
                    r"no less than|below|above|exceed\w*|threshold|exempt\w*|taxable|deemed|treated as|applies|apply|available|denied|fails?|"
                    r"qualif\w*|entitled|eligible|cap[sp]?\b|capped|limit\w*|within|rate)\b")
TAXWORD = re.compile(r"(?i)\b(tax\w*|withh\w*|treaty|exempt\w*|beneficial|rate|duty|deduct\w*|credit|resident\w*|dividend|gain|penalt\w*|interest|anti-avoidance|GAAR|PPT)\b")
ABBR = re.compile(r"(?i)(?:\b(?:no|art|arts|para|paras|s|ss|cap|sch|e\.g|i\.e|cf|ltd|pte|co|inc|mr|mrs|ms|dr|st|vs|etc|sec|reg|regs|p|pp|vol)|\b[A-Z])\.$")
RULE_TOKEN = re.compile(r"\b[a-z]{2}\.[a-z_]+(?:\.[a-z0-9_]+)+\b")


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def squeeze(text):
    return re.sub(r"[\s*`_'\"‘’“”]+", "", text or "").lower()


def body_lines(text):
    """(line number, text) of the parts a reader takes as advice: no fenced blocks, no Appendix B list, no internal-reference footer."""
    out, fence, skip = [], False, False
    for i, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        if re.match(r"^#{1,4}\s+(?:Appendix\s*B|附录\s*B)\b", line.strip()):
            skip = True
            continue
        if skip and re.match(r"^#{1,3}\s+", line.strip()):
            skip = False
        if skip or "Internal reference" in line:
            continue
        out.append((i, line))
    return out


def sentences(text):
    """(line, sentence) pairs; a table row is one unit, a paragraph is split at sentence ends."""
    out = []
    for no, line in body_lines(text):
        s = line.strip()
        if not s or re.match(r"^#{1,6}\s", s) or re.fullmatch(r"[|\-:\s]+", s):
            continue
        if s.startswith("|"):
            out.append((no, s))
            continue
        start = 0
        for m in re.finditer(r"(?<=[.;?!])\s+(?=[A-Z(\"'*‘“\[])", s):
            piece = s[start:m.start()]
            if ABBR.search(piece):
                continue
            out.append((no, piece.strip()))
            start = m.end()
        if s[start:].strip():
            out.append((no, s[start:].strip()))
    return out


def is_reason(sentence):
    return bool(LAWREF.search(sentence) or (REASON.search(sentence) and TAXWORD.search(sentence)))


# ------------------------------------------------------------ citations written in the sentence
NOTICE = re.compile(r"(?i)(?:\b(item|paragraph|article|para\.?)s?\s+(\d+)(?:\s*\(\w+\))?\s+of\s+(?:the\s+)?)?"
                    r"(?:STA|SAT|State\s+Taxation\s+Administration|State\s+Administration\s+of\s+Taxation|Guo\s*Shui\s*Han|Guo\s*Shui\s*Fa|Cai\s*Shui|MOF)?\s*"
                    r"(Announcement|Circular|Notice|Bulletin)?\s*\[?(\d{4})\]?\s*No\.\s*(\d+)"
                    r"(?:,?\s*(?:items?|paragraphs?|articles?)\s+(\d+)((?:\s*(?:,|and)\s*\d+)*))?")
LAWS = [(re.compile(r"(?i)implementation\s+regulations|regulations\s+(?:on|for)\s+the\s+implementation"), "cn.reg.eit"),
        (re.compile(r"(?i)enterprise\s+income\s+tax\s+law|\bEITL?\b"), "cn.law.eit"),
        (re.compile(r"(?i)individual\s+income\s+tax\s+law|\bIITL\b"), "cn.law.iit"),
        (re.compile(r"(?i)tax\s+collection|administration\s+of\s+tax\s+collection|\bTCA\b"), "cn.law.tca"),
        (re.compile(r"(?i)stamp\s+duty\s+law|stamp\s+tax\s+law"), "cn.law.stamp")]
ARTICLE = re.compile(r"(?i)\barticles?\s+(\d+)(?:\s*\((\d+)\))?(?:\s*\(\w+\))?\s+of\s+(?:the\s+|its\s+|that\s+)?([^.;()]{0,90})")
SECTION = re.compile(r"(?i)\b(?:sections?|s\.|ss\.)\s?(\d+[A-Z]{0,4})(?:\(([0-9A-Za-z]+)\))?")


def treaty_doc(words):
    w = words.lower()
    if "protocol" in w and ("fifth" in w or "no. 5" in w or "5th" in w):
        return "treaty.cn-hk.2006.p5.zh"
    if "hong kong" in w and ("arrangement" in w or "agreement" in w or "treaty" in w):
        return "treaty.cn-hk.2006.zh"
    if "singapore" in w and ("arrangement" in w or "agreement" in w or "treaty" in w):
        return "treaty.cn-sg.2007.mli.en"
    return None


BACK = re.compile(r"(?i)\b(item|paragraph|article)s?\s+(\d+)(?:\s*\(\w+\))?\s+of\s+(?:that|the\s+same|this|the\s+(\d{4}))\s+(?:Announcement|Circular|Notice)")


def cites_in(sentence, has, ctx=None):
    """The cite_ids a sentence names in words: Mainland notices by year and number with their item, Mainland laws and the
    arrangements by article, Hong Kong and Singapore acts by section. `has(cite_id)` says whether the library holds it."""
    out = []

    def add(*cands):
        for c in cands:
            if c and has(c):
                out.append(c)
                return True
        return False
    for m in NOTICE.finditer(sentence):
        if not (m.group(3) or re.search(r"(?i)STA|SAT|Guo|Cai|MOF|Taxation", m.group(0))):
            continue
        year, no = m.group(4), int(m.group(5))
        docs = [d for d in ("cn.sta.%s-%02d" % (year, no), "cn.cs.%s-%02d" % (year, no), "cn.gsf.%s-%02d" % (year, no), "cn.gsh.%s-%02d" % (year, no))]
        units = [m.group(2)] if m.group(2) else []
        if m.group(6):
            units += [m.group(6)] + re.findall(r"\d+", m.group(7) or "")
        for d in docs:
            if units:
                hit = [add("%s#i%s" % (d, u), "%s#%s" % (d, u)) for u in units]
                if any(hit):
                    break
            elif add("%s#all" % d, "%s#i1" % d, "%s#1" % d):
                break
    if ctx is not None:                                  # "item 6 of that Announcement", "paragraph 10 of the 2019 Announcement"
        for c in out:
            if c.startswith("cn."):
                d = c.split("#")[0]
                ctx["last"] = d
                ctx[d.split(".")[-1][:4]] = d
        for m in BACK.finditer(sentence):
            d = ctx.get(m.group(3)) if m.group(3) else ctx.get("last")
            if d:
                add("%s#i%s" % (d, m.group(2)), "%s#%s" % (d, m.group(2)))
    for m in ARTICLE.finditer(sentence):
        art, sub, words = m.group(1), m.group(2), m.group(3)
        doc = treaty_doc(words) or next((d for rx, d in LAWS if rx.search(words)), None)
        if doc:
            add("%s#%s.%s" % (doc, art, sub) if sub else None, "%s#%s" % (doc, art))
    acts = []
    if re.search(r"(?i)inland\s+revenue\s+ordinance|\bIRO\b|cap\.?\s?112", sentence):
        acts.append("hk.cap112")
    if re.search(r"(?i)stamp\s+duty\s+ordinance|cap\.?\s?117", sentence):
        acts.append("hk.cap117")
    if re.search(r"(?i)income\s+tax\s+act", sentence):
        acts.append("sg.ita1947")
    if not acts:
        acts = (["hk.cap112"] if re.search(r"(?i)hong\s+kong", sentence) else []) + (["sg.ita1947"] if re.search(r"(?i)singapore", sentence) else [])
    for m in SECTION.finditer(sentence):
        for a in acts:
            if add("%s#s%s(%s)" % (a, m.group(1), m.group(2)) if m.group(2) else None, "%s#s%s" % (a, m.group(1))):
                break
    return list(dict.fromkeys(out))


def fragments(where):
    """The quoted text of a sources row's `where`, as pieces split at ellipses."""
    w = str(where or "")
    w = w.split("|", 1)[1] if "|" in w else w
    m = re.search(r"['\"‘“](.+)['\"’”]\s*$", w.strip(), re.S) or re.search(r"['\"‘“](.+)", w, re.S)
    frag = m.group(1) if m else w
    return [p for p in (squeeze(x) for x in re.split(r"…|\.\.\.", frag)) if len(p) >= 10]


def changed_lines(old_text, new_text):
    """Line numbers (1-based) of new_text that are new or changed against old_text."""
    old, new = old_text.splitlines(), new_text.splitlines()
    keep = set()
    for tag, _, _, j1, j2 in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        if tag in ("replace", "insert"):
            keep.update(range(j1 + 1, j2 + 1))
    return keep


def unchanged_from(base_text, new_text):
    """Line numbers of new_text whose sentences all appear verbatim in base_text (for the final check: what polish did not touch)."""
    base = squeeze(base_text)
    same = set()
    for no, line in enumerate(new_text.splitlines(), 1):
        if line.strip() and squeeze(line) in base:
            same.add(no)
    return same


def build(case_id, run_id, target="draft", lines=None, cases_root=None, reader=None):
    import read_core
    r = reader or read_core.Reader("review", cases_root=cases_root or PROJECT / "cases", log=False)
    rd = r.cases / case_id / "report" / run_id
    md = rd / ("briefing.md" if target == "draft" else "briefing.polished.md")
    sj = rd / ("briefing.sources.json" if target == "draft" else "briefing.polished.sources.json")
    text = md.read_text(encoding="utf-8")
    data = json.loads(sj.read_text(encoding="utf-8")) if sj.exists() else []
    rows = data if isinstance(data, list) else data.get("sources", [])
    rules = r.rules()
    params = r.lib()["params"]
    decisions = {d["id"]: d for d in read_csv(r.rule / "decision.csv")}
    pcon, _ = r.products(case_id, run_id)
    used = set()                                   # the rules this run applied or tested: only those are laid out
    if pcon is not None:
        for rec in pcon.execute("SELECT full FROM record WHERE type IN ('cell', 'transfer', 'requirement')"):
            used.update(RULE_TOKEN.findall(rec["full"]))

    def rules_in(obj_text):
        return [t for t in dict.fromkeys(RULE_TOKEN.findall(obj_text)) if t in rules]

    con = r.law()
    known = {}

    def has(cid):
        if cid not in known:
            known[cid] = con.execute("SELECT 1 FROM clause WHERE cite_id = ?", (cid,)).fetchone() is not None
        return known[cid]

    def take_cite(base):
        if base not in provisions:
            provisions[base] = r.law_meta([base]).get(base)
            rule_ids.extend(rid for rid, ru in rules.items() if base in (ru.get("cite_ids") or "").split(";") and rid in used)

    items, provisions, rule_ids, record_cards = [], {}, [], {}
    ctx, ctx_line = {}, None
    for no, s in sentences(text):
        if lines is not None and no not in lines:
            continue
        if not is_reason(s):
            continue
        q = squeeze(s)
        hit = [row for row in rows if row.get("kind") in ("cite", "product", "url", "document")
               and any(p in q or q in p for p in fragments(row.get("where")))]
        refs = []
        for row in hit:
            ref = str(row.get("ref", "")).strip()
            refs.append("%s → %s (%s)" % (row.get("id"), ref, row.get("kind")))
            for token in re.split(r"[;,]\s*", ref):
                base = token.strip().split(" ")[0]
                if not base:
                    continue
                if row.get("kind") == "cite":
                    take_cite(base)
                elif row.get("kind") == "product" and pcon is not None and base not in record_cards:
                    rec = pcon.execute("SELECT type, card, full FROM record WHERE id = ?", (base,)).fetchone()
                    if rec:
                        record_cards[base] = rec["card"] if rec["type"] != "basis" else "(a structure's legal basis record: get(id) for its provisions)"
                        if rec["type"] != "basis":
                            rule_ids += rules_in(rec["full"])
        if no != ctx_line:
            ctx, ctx_line = {}, no                     # a back reference reaches only within its paragraph
        named = [c for c in cites_in(s, has, ctx) if not any(c in x for x in refs)]
        for c in named + [c for c in r.exact_law(s) if c not in named]:
            take_cite(c)
        if named:
            refs.append("named in the sentence: " + ", ".join(named))
        items.append((no, s, refs))
    plan_cites = []                                # what the recommended structure rests on: the cells of its all-favourable branch
    if pcon is not None:
        brief = pcon.execute("SELECT full FROM record WHERE type = 'brief'").fetchone()
        best = json.loads(brief["full"]).get("best", {}) if brief else {}
        fb = (best.get("all_favourable") or {}).get("branch_id")
        if fb:
            for rec in pcon.execute("SELECT card FROM record WHERE type = 'cell' AND branch = ?", (fb,)):
                c = json.loads(rec["card"])
                if c.get("status") == "absent":
                    continue
                for cid in c.get("cite_ids") or []:
                    if cid not in plan_cites:
                        plan_cites.append(cid)
                rule_ids.extend(x for x in c.get("rules") or [] if x in rules)
    for cid in plan_cites:
        take_cite(cid)
    rule_ids = list(dict.fromkeys(rule_ids))
    dec_ids = list(dict.fromkeys(d for rid in rule_ids for d in (rules[rid].get("decision_ids") or "").split(";") if d.strip() in decisions))

    def render(cap):
        out = ["# Legal-reasoning extract: case %s, run %s, %s" % (case_id, run_id, md.name), "",
               "Written by the program for the legal-reasoning check. Each sentence below states a legal reason; under it are the sources rows "
               "whose where fragment lies in it. The provisions, rules, parameters and decisions those rows lead to follow, verbatim. A sentence "
               "with no row is listed with 'no row': its authority is most often among the provisions below, which also carry every provision the "
               "recommended structure applies; look there first and use tax-read only for what is not there. Line numbers are those of %s." % md.name, "",
               "## Sentences (%d)" % len(items), ""]
        for k, (no, s, refs) in enumerate(items, 1):
            out.append("**R%d** (line %d) %s" % (k, no, s))
            out.append("  - rows: " + ("; ".join(refs) if refs else "no row"))
        if plan_cites:
            out += ["", "The recommended structure's all-favourable branch applies these provisions (all laid out below): " + ", ".join(plan_cites) + "."]
        out += ["", "## Provisions (verbatim; get(cite_id) for the whole text)", ""]
        for cite, meta in provisions.items():
            if not meta:
                out.append("- `%s`: not in the library index" % cite)
                continue
            out.append("- `%s` %s %s: %s" % (cite, meta.get("title", ""), meta.get("label", ""), r.unit_text(None, cite, cap).replace("\n", " ")))
        out += ["", "## Rules of the rule layer that apply them", ""]
        for rid in rule_ids:
            ru = rules[rid]
            ps = ["%s = %s %s (%s: \"%s\")" % (p, params[p].get("value"), params[p].get("unit", ""), params[p].get("cite_id", ""), (params[p].get("quote") or "")[:240])
                  for p in dict.fromkeys(re.findall(r"\$([\w.]+)", ru.get("condition", ""))) if p in params]
            out.append("- `%s` [%s] if %s → %s; cites %s; decisions %s%s%s" % (
                rid, ru.get("slot_key"), ru.get("condition"), ru.get("effect"), ru.get("cite_ids"), ru.get("decision_ids") or "none",
                "; parameters: " + "; ".join(ps) if ps else "", "; note: " + ru["note"][:160] if ru.get("note") else ""))
        out += ["", "## Decisions of the rule layer (how a provision is read)", ""]
        for d in dec_ids:
            out.append("- `%s` %s (%s)" % (d, decisions[d]["statement"], decisions[d].get("cite_id")))
        if record_cards:
            out += ["", "## Product records the rows cite", ""]
            out += ["- `%s` %s" % (i, c[:cap // 2]) for i, c in record_cards.items()]
        return "\n".join(out) + "\n"

    for cap in (1500, 900, 600, 300):              # whole thresholds and conditions first; shorter only when the extract would pass LIMIT
        doc = render(cap)
        if len(doc) <= LIMIT:
            break
    path = rd / "pack" / ("legal_%s.md" % target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc, encoding="utf-8")
    return path, len(items)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(HERE))
    p, n = build(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "draft")
    print(p, n, p.stat().st_size)
