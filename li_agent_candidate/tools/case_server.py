#!/usr/bin/env python
"""tax-case: the case-file MCP server (agent/case_mcp_spec.en.md). The only write path of the four agents into cases/<case_id>/.

  python agent/tools/case_server.py --root cases --agent front|analysis|polish|review

Reads are not served here (the host's Read / Glob / Grep do that); logging is not done here (host PostToolUse hook).
The server does three things: writes with semantics (append-only files, .prev copies, JSON and verdict checks), the
round ledger with derived status, and two read-only self-checks. Python 3.11, `mcp` 2.x and the standard library.
"""
import argparse
import base64
import csv
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
SERVER_VERSION = "0.1"
AGENTS = ("front", "analysis", "polish", "review")
BODY_FLOOR, BODY_LIMIT = 5, 10                         # pages before the appendices; the appendices do not count
BOOKS = {"front": ("reading", "construal", "ask", "rounds"),
         "analysis": ("precommit", "products", "law", "paths", "flags"),
         "polish": ("plan", "changes", "issues"),
         "review": ("expect", "recalc", "checks", "legal")}
INTAKE_NAMES = ("facts", "sources", "answers", "notes", "constraints", "handoff")
INTAKE_FILES = {"facts": "facts.json", "sources": "sources.json", "answers": "answers.json", "notes": "notes.md",
                "constraints": "constraints.json", "handoff": "handoff.md"}
DIRTY_NAMES = ("facts", "sources", "answers", "notes", "constraints")   # everything stage 1 reviews; the handoff is not reviewed
VERDICTS = {"intake": ("RUNNABLE", "REVISE"), "draft": ("DELIVERABLE", "REVISE"), "legal_draft": ("DELIVERABLE", "REVISE"),
            "final": ("DELIVERABLE", "REVISE"), "legal_final": ("DELIVERABLE", "REVISE")}   # legal_*: the legal-reasoning lane; final/legal_final: the polish stage, removed 2026-11-06 (old cases only)
LEGACY_PASS = {"draft": "POLISHABLE", "legal_draft": "POLISHABLE"}        # the pass token of draft checklists written before 2026-11-06
RETURNS = {"draft": ("analysis", "front"), "legal_draft": ("analysis",),
           "final": ("polish", "analysis", "front"), "legal_final": ("polish", "analysis")}   # who a REVISE checklist may send the case back to
REPLACEMENTS = re.compile(r"```replacements\s*\n(.*?)\n```", re.S)        # a reviewer's fix-to-order list: [{"old": ..., "new": ...}]
PROBLEM_LINE = re.compile(r"(?im)^\s*(?:[-*]\s*)?\**\s*(?:problem|问题)\s*\**\s*[:：]\s*\**\s*(.*)$")
NO_PROBLEM = re.compile(r"(?i)^(none|no\b|nothing|not found|n/a|无|没有|未发现|-\s*$)")
LINE_REF = re.compile(r"(?i)\blines?\s+(\d+)|第\s*(\d+)\s*行")
CHECKLISTS = {"draft": "review.md", "final": "review_final.md", "legal_draft": "review_legal.md", "legal_final": "review_final_legal.md"}
PARTS = (("策略思路", "strategy"), ("现状", "current state"), ("备选方案", "alternatives"),
         ("最优方案", "optimal"), ("税负比较", "tax comparison"), ("条件与要求", "requirements"), ("执行", "implementation"))
LEAKS = (r"\d{8}-[0-9a-f]{8}:[a-z_]+:", r"CASE-\d{8}-[0-9a-f]{6}:[a-z_]+:", r"#[\w.()\-]+@\d+", r"\[S\d+\]", r"\b[cx]\d+\.b\d+\b", r"\bcand_id\b", r"\bbranch_id\b", r"\brun_id\b", r"\bper_100\b", r"\bchanges_rank\b",
         r"\bopen_items\b", r"\b(floor|ceiling)\b", r"\w+\.json\b", r"\bif_(yes|no)\b", r"\btotal_N\b", r"\bslot_key\b",
         r"规则工具", r"规则层", r"优化层", r"法规库", r"模型", r"产物", r"未收录", r"补录", r"(?i)\brule (tool|layer)\b", r"(?i)\boptimi[sz](er|ation layer)\b",
         r"(?i)\bnot (yet )?(on file|in the library)\b")
JARGON = r"(?i)\bper 100\b|\bmodell?ed\b|\bvariants?\b|\bjudgment worlds?\b|\branked \d+(?:st|nd|rd|th)\b|\b(?:law|the) library\b"       # the optimizer's vocabulary, not a client's
LONG_SENTENCE = 55                                     # words; a longer sentence in the client report is sent back
DATE_LINE = re.compile(r"^\*\*(?:Date|日期)\s*[:：]?\*\*\s*[:：]?\s*(.+?)\s*$", re.M)
DATE_FORMATS = ("%Y-%m-%d", "%d %B %Y", "%B %d, %Y", "%Y年%m月%d日")
SPOKEN = (r"(?im)^\*\*(一句话|为什么|省多少|花多少|靠什么|怎么做|in a sentence|in one sentence|why|how much it saves|"
          r"how much it costs|what it depends on|how to do it)[^*]{0,12}\*\*")     # spoken lead-ins are not the register of an opinion


def numbers_in(text):
    """Every numeric token of a text, thousands separators removed; units and formats are ignored on purpose."""
    return {n.replace(",", "").rstrip(".") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}


def squeeze(text):
    """Text without whitespace or Markdown emphasis, for verbatim fragment lookup."""
    return re.sub(r"[\s*`]+", "", text or "")


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def err(kind, detail, **extra):
    out = {"error": kind, "detail": detail}
    out.update(extra)
    return out


def squash(s):
    return re.sub(r"\s+", "", s or "")


def last_line(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return lines[-1] if lines else ""


def verdict_of(text, which):
    """Canonical English verdict of the last non-empty line, or None."""
    line = re.sub(r"[\s\"'.:\-*`]+$", "", last_line(text))
    for v in VERDICTS[which]:
        if line.upper().endswith(v):
            return v
    if which in LEGACY_PASS and line.upper().endswith(LEGACY_PASS[which]):
        return VERDICTS[which][0]
    return None


def replacements_of(text):
    """The fix-to-order list of a checklist (a ```replacements block holding [{"old", "new"}]), or []; malformed -> None."""
    m = REPLACEMENTS.search(text or "")
    if not m:
        return []
    try:
        rows = json.loads(m.group(1))
    except ValueError:
        return None
    if not isinstance(rows, list) or any(not isinstance(r, dict) or not r.get("old") or "new" not in r for r in rows):
        return None
    return rows


def findings_of(text):
    """(line numbers referred to, problem statements that are not 'none') of a checklist."""
    lines, problems = set(), []
    for m in PROBLEM_LINE.finditer(text or ""):
        if not NO_PROBLEM.match(m.group(1).strip()):
            problems.append(m.group(1).strip())
    for m in LINE_REF.finditer(text or ""):
        lines.add(int(m.group(1) or m.group(2)))
    return lines, problems


def return_of(text):
    """Target of the RETURN line just before the verdict of a REVISE checklist, or None."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    m = re.fullmatch(r"[*`]*RETURN:[*`\s]*(analysis|polish|front)[.*`]*", lines[-2], re.I) if len(lines) >= 2 else None
    return m.group(1).lower() if m else None


def newest(*paths):
    """Latest modification time of the paths that exist, 0 when none does."""
    return max((p.stat().st_mtime for p in paths if p.exists()), default=0)


def draft_files(rd):
    return rd / "briefing.md", rd / "briefing.sources.json"


def report_files(rd):
    return rd / "briefing.polished.md", rd / "briefing.polished.sources.json", rd / "briefing.pdf"


def passed(path, which, since):
    """The checklist exists, is not older than what it reviewed, and its verdict lets the case go on."""
    return (path.exists() and path.stat().st_mtime >= since
            and verdict_of(path.read_text(encoding="utf-8"), which) == VERDICTS[which][0])


FACT_KEYS = ("date", "mode", "amount", "currency", "payer", "payee", "payment", "assume", "entities", "destinations", "valuation",
             "as_of", "fx", "limits", "constraints", "case", "note", "instructed_on", "past_payments", "answers")


CONSTRAINT_KEYS = ("consider", "exclude", "allow_restructure", "payback_max", "allowed_subjects")
FACT_EXTRA = ("listed", "exit_assets_cost")              # read by the optimizer beyond rule/variable.csv


def rule_jurisdictions():
    """The jurisdictions the rule layer has rules for: the system's scope."""
    with open(PROJECT / "rule" / "rule.csv", encoding="utf-8-sig") as f:
        return {r["rule_id"].split(".")[0] for r in csv.DictReader(f) if r.get("rule_id") and "-" not in r["rule_id"].split(".")[0]}   # pair prefixes are treaty rules


def variable_names():
    with open(PROJECT / "rule" / "variable.csv", encoding="utf-8-sig") as f:
        return {r["name"] for r in csv.DictReader(f)} | set(FACT_EXTRA)


VALUATION_KEYS = ("net_assets", "cost_base", "cost_currency", "appraised_value", "property_rich_ratio", "currency", "as_of", "source", "note")


def shape_problems(facts):
    """facts.json against the optimizer's input, in words an author can act on (agent/front_agent_spec.en.md section 3)."""
    out = []
    for key in ("date", "amount", "currency"):
        if not facts.get(key):
            out.append("facts.json needs a top-level %s" % key)
    for role, wanted in (("payer", '{"jur": "cn", "facts": {...}}'), ("payee", '{"jur": "hk", "subject": "company", "facts": {...}}')):
        side = facts.get(role)
        if not (isinstance(side, dict) and side.get("jur") and isinstance(side.get("facts"), dict)):
            out.append("facts.json: %s must be %s, with every variable inside facts" % (role, wanted))
    odd = sorted(k for k in facts if k not in FACT_KEYS)
    if odd:
        out.append("facts.json: top-level keys the optimizer does not read: %s. Facts of the payment go inside payment, of a company inside its facts; see optimization/examples/case001.json" % ", ".join(odd))
    if isinstance(facts.get("payment"), dict) and "past_payments" in facts["payment"]:
        out.append("facts.json: past_payments is a top-level list, not inside payment")
    if "destinations" not in facts:
        out.append("facts.json needs destinations: where the client wants the money to end up, as [jur, subject] pairs; the payee alone when the client has not said")
    obj = lambda x: x if isinstance(x, dict) else {}                  # a wrong shape is reported once below, never a crash
    entities = obj(facts.get("entities"))
    if facts.get("entities") is not None and not isinstance(facts.get("entities"), dict):
        out.append('facts.json: entities must be an object keyed by node, {"sg:company": {"holds": "hk:company", "facts": {...}}, ...}; see optimization/examples/case001.json')
    dests = facts.get("destinations") if isinstance(facts.get("destinations"), list) else []
    if facts.get("destinations") is not None and not isinstance(facts.get("destinations"), list):
        out.append('facts.json: destinations must be a list of [jur, subject] pairs, such as [["sg", "company"], ["sg", "individual"]]')
    names = variable_names()
    places = [(role, obj(facts.get(role)).get("facts")) for role in ("payer", "payee")] + [("payment", facts.get("payment"))]
    places += [("entities." + n, obj(e).get("facts")) for n, e in entities.items()]
    for where, fs in places:
        odd = sorted(k for k in (fs or {}) if k not in names and k != "past_payments") if isinstance(fs, dict) else []
        if odd:
            out.append("facts.json: %s carries keys that are no rule-layer variable: %s. Use only names from variables(); figures of earlier dividends go into past_payments" % (where, ", ".join(odd)))
    payee = obj(facts.get("payee"))
    scope = rule_jurisdictions()
    named = [(role, facts[role].get("jur")) for role in ("payer", "payee") if isinstance(facts.get(role), dict)]
    named += [("entities", str(n).split(":")[0]) for n in entities]
    named += [("destinations", d[0] if isinstance(d, (list, tuple)) and d else str(d).split(":")[0]) for d in dests]
    named += [("constraints.consider", j) for j in ((facts.get("constraints") or {}).get("consider") or [])] if isinstance(facts.get("constraints"), dict) else []
    outside = sorted({"%s %s" % (where, str(j).upper()) for where, j in named if j and str(j).lower() not in scope})
    if outside:
        out.append("facts.json names jurisdictions the system has no rules for (%s); the scope is %s. Tell the client in plain words that these are outside what the system covers; "
                   "keep only a case whose payer, payee and destinations are inside the scope" % (", ".join(outside), ", ".join(sorted(s.upper() for s in scope))))
    for node, v in obj(facts.get("valuation")).items():                # keys the optimizer does not read are silently lost
        odd = sorted(k for k in obj(v) if k not in VALUATION_KEYS)
        if odd:
            out.append("facts.json: valuation.%s carries keys the optimizer does not read: %s (allowed: %s); valuation is keyed by the company whose shares "
                       "are transferred, and cost_base is what the present holder paid for the stake it holds" % (node, ", ".join(odd), ", ".join(VALUATION_KEYS)))
    val = obj(facts.get("valuation"))
    payer_node = "%s:company" % obj(facts.get("payer")).get("jur")
    payee_node = "%s:%s" % (payee.get("jur"), payee.get("subject"))
    mine, theirs = obj(val.get(payer_node)), obj(val.get(payee_node))
    if theirs.get("cost_base") not in (None, "") and mine.get("cost_base") in (None, "") and not theirs.get("note"):
        out.append("facts.json: valuation.%s.cost_base is read as what %s's own holder paid for the shares of %s, while valuation.%s has no cost_base. If the figure is "
                   "what %s paid for its stake in %s, move it to valuation.%s.cost_base. If it really is the cost of %s's own shares, say so in valuation.%s.note"
                   % (payee_node, payee_node, payee_node, payer_node, payee_node, payer_node, payer_node, payee_node, payee_node))
    parent = obj(payee.get("facts")).get("parent_jur")
    if parent and not any(str(n).split(":")[0].lower() == str(parent).lower() for n in entities):
        out.append("facts.json: the payee's parent (parent_jur %s) is not in entities: every known company or person above the payee goes into entities with holds, holding_pct and holding_months" % parent)
    return out


def predicates():
    """key -> the answer that favours the client (rule/predicate.csv)."""
    with (PROJECT / "rule" / "predicate.csv").open(encoding="utf-8-sig", newline="") as f:
        return {r["key"]: r["favourable"] for r in csv.DictReader(f)}


def closing_answers(answers):
    """The answers that close a judgment point: only an answer against the client. The authority decides these points, so
    a favourable statement is evidence for the report and both outcomes stay open."""
    polarity, closed = predicates(), {}
    for key, a in (answers or {}).items():
        val = a.get("value") if isinstance(a, dict) else a
        if key in polarity and val in ("yes", "no") and val != polarity[key]:
            closed[key] = val
    return closed


def report_date(text):
    m = DATE_LINE.search(text)
    if not m:
        return None
    stated = m.group(1).strip().rstrip(".。")             # the header line may end its sentence with a full stop
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(stated, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    iso = re.search(r"\d{4}-\d{2}-\d{2}", stated)         # "26 March 2026 (2026-03-26)": the date with a gloss (2026-11-06)
    if iso:
        try:
            return datetime.strptime(iso.group(0), "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            pass
    return stated


def long_sentences(text):
    """Sentences over the limit in the prose of the body, tables and the flowchart aside."""
    out = []
    for line in re.sub(r"```.*?```", "", text, flags=re.S).splitlines():
        if line.lstrip().startswith(("|", "#")):
            continue
        for s in re.split(r"(?<=[.;?!])\s+", line):
            if len(s.split()) > LONG_SENTENCE:
                out.append("%d words: %s..." % (len(s.split()), " ".join(s.split()[:8])))
    return out


def outline(text):
    """The parts of a briefing with their line ranges (1-based, inclusive): head (title, date, opening declaration), 1-7, A, B.
    Agents read a part with Read offset/limit instead of the whole report."""
    lines = text.splitlines()
    marks = []
    for i, line in enumerate(lines):
        m = re.match(r"^#{1,3}\s+(.+)$", line)
        if not m:
            continue
        h = m.group(1).strip()
        ap = re.match(r"^(?:附录|Appendix)\s*([AB])\b", h)
        num = re.match(r"^(?:Part\s+)?([1-7])[.、:：\s]", h)
        key = ap.group(1) if ap else num.group(1) if num else next(
            (str(k + 1) for k, (cn, en) in enumerate(PARTS) if cn in h or h.lower().startswith(en)), None)
        if key and key not in [k for k, _, _ in marks]:
            marks.append((key, i + 1, h))
    out = []
    if marks and marks[0][1] > 1:
        out.append({"part": "head", "title": "title, date and opening declaration", "lines": [1, marks[0][1] - 1]})
    for j, (key, start, h) in enumerate(marks):
        end = marks[j + 1][1] - 1 if j + 1 < len(marks) else len(lines)
        out.append({"part": key, "title": h, "lines": [start, end]})
    return out


def part_text(text, part):
    """The text of one part (see outline), or None when the report has no such part."""
    hit = next((o for o in outline(text) if o["part"] == str(part)), None)
    if hit is None:
        return None
    a, b = hit["lines"]
    return "\n".join(text.splitlines()[a - 1:b])


def flatten(obj, prefix=""):
    """Leaf paths of a JSON object: a.b.c and a[0].b."""
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, "%s.%s" % (prefix, k) if prefix else k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, "%s[%d]" % (prefix, i)))
    else:
        out[prefix] = obj
    return out


class Case:
    def __init__(self, root, agent):
        if agent not in AGENTS:
            raise SystemExit("--agent must be one of %s" % ", ".join(AGENTS))
        self.root = Path(root).resolve()
        self.agent = agent
        self.root.mkdir(parents=True, exist_ok=True)
        self._db = None

    # ------------------------------------------------------------ paths and ledger
    def case_dir(self, case_id):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", case_id or ""):
            return None
        return self.root / case_id

    def ledger_path(self, cd):
        return cd / "rounds.json"

    def load_ledger(self, cd):
        p = self.ledger_path(cd)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def save_ledger(self, cd, ledger):
        self.ledger_path(cd).write_text(json.dumps(ledger, ensure_ascii=False, indent=1), encoding="utf-8")

    def current(self, ledger):
        n = ledger["current"]
        return next(r for r in ledger["rounds"] if r["round"] == n)

    def opened(self, case_id):
        cd = self.case_dir(case_id)
        if cd is None:
            return None, None, err("invalid", "bad case_id %r" % case_id)
        if not cd.exists():
            return None, None, err("not_found", "no case %s" % case_id, path=str(cd))
        ledger = self.load_ledger(cd)
        if ledger is None:
            return None, None, err("not_found", "no rounds.json in %s" % case_id)
        return cd, ledger, None

    def status(self, cd, ledger):
        cur = self.current(ledger)
        run_id = cur.get("run_id")
        ri = cd / "intake" / "review_intake.md"
        if run_id and (cur.get("last_intake_write") or "") > (cur.get("review_intake_written") or ""):
            return "intake"                                    # the package changed after its check: check it and run again
        if run_id and cur.get("run_registered") and (cur.get("review_intake_written") or "") > cur["run_registered"]                 and ri.exists() and verdict_of(ri.read_text(encoding="utf-8"), "intake") == "RUNNABLE":
            return "intake_ok"                                 # checked again after the run: the products are stale
        if run_id:
            rd = cd / "report" / run_id
            draft = draft_files(rd)
            pol, review = rd / "briefing.polished.md", rd / "review.md"
            if not draft[0].exists():
                return "ran"
            # file times carry the order: a rewritten draft drops the case back to drafted, whatever came after it
            lanes = (rd / ".lanes").exists()
            legal = rd / CHECKLISTS["legal_draft"]
            if not passed(review, "draft", newest(*draft)) or (lanes and not passed(legal, "legal_draft", newest(*draft))):
                return "drafted"
            # 2026-11-06: the reviewed draft is the client report; the program renders it, and the PDF newer than draft and checklists means delivered
            pdf = rd / "briefing.pdf"
            checked = max(review.stat().st_mtime, legal.stat().st_mtime if lanes else 0)
            if pdf.exists() and pdf.stat().st_mtime >= max(newest(*draft), checked):
                return "delivered"
            if pol.exists() and pol.stat().st_mtime >= checked:                 # old cases (polish stage): their final checklists decide
                since = newest(*report_files(rd))
                if passed(rd / "review_final.md", "final", since) and (not lanes or passed(rd / CHECKLISTS["legal_final"], "legal_final", since)):
                    return "delivered"
            return "reviewed"
        if ri.exists() and verdict_of(ri.read_text(encoding="utf-8"), "intake") == "RUNNABLE":
            last_write = cur.get("last_intake_write") or ""
            reviewed = cur.get("review_intake_written") or ""
            if reviewed and reviewed > last_write:
                return "intake_ok"
        return "intake"

    def pending_return(self, cd, ledger):
        """The REVISE checklist the current status is waiting on: {which, to, path}; None when there is none."""
        cur = self.current(ledger)
        st = self.status(cd, ledger)
        if st == "intake":
            p = cd / "intake" / "review_intake.md"
            reviewed = cur.get("review_intake_written") or ""
            if p.exists() and reviewed > (cur.get("last_intake_write") or "") and verdict_of(p.read_text(encoding="utf-8"), "intake") == "REVISE":
                return {"which": "intake", "to": "front", "path": str(p)}
            return None
        if st != "drafted":
            return None
        rd = cd / "report" / cur["run_id"]
        stage, since, default = ("draft", "legal_draft"), newest(*draft_files(rd)), "analysis"
        found = []                                             # every REVISE of the stage: the main review and the legal lane
        for which in stage:
            p = rd / CHECKLISTS[which]
            if p.exists() and p.stat().st_mtime >= since:
                text = p.read_text(encoding="utf-8")
                if verdict_of(text, which) == "REVISE":
                    found.append({"which": which, "to": return_of(text) or default, "path": str(p)})
        if not found:
            return None
        order = ("front", "analysis", "polish")                 # the furthest return wins; the others ride along
        found.sort(key=lambda f: order.index(f["to"]))
        first = dict(found[0], which=stage[0])
        if len(found) > 1:
            first["also"] = [f["path"] for f in found[1:]]
        elif found[0]["which"] != stage[0]:
            first["path"] = found[0]["path"]
        return first

    def round_tag(self, ledger):
        cur = self.current(ledger)
        return "round %d.%d" % (cur["round"], cur.get("revision", 0)), cur.get("run_id") or ""

    # ------------------------------------------------------------ helpers
    def write_with_prev(self, path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            shutil.copyfile(path, path.with_name(path.name + ".prev"))
        path.write_text(content, encoding="utf-8")

    def append(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            if path.stat().st_size if path.exists() else 0:
                f.write("\n")
            f.write(text.rstrip("\n") + "\n")

    def need(self, *agents):
        return None if self.agent in agents else err("forbidden", "%s may not do this; allowed: %s" % (self.agent, ", ".join(agents)))

    # ------------------------------------------------------------ ledger tools (front)
    def case_new(self, case_id):
        if (e := self.need("front")):
            return e
        cd = self.case_dir(case_id)
        if cd is None:
            return err("invalid", "bad case_id %r" % case_id)
        if cd.exists():
            return err("conflict", "case %s exists" % case_id, path=str(cd))
        for sub in ("intake/documents", "intake/products", "report", "bugs", "log"):
            (cd / sub).mkdir(parents=True)
        for ag in AGENTS:
            (cd / "notes" / ag / "round-1").mkdir(parents=True)
        ledger = {"current": 1, "rounds": [{"round": 1, "revision": 0, "run_id": None, "opened": today(), "intake_dirty": False,
                                            "last_intake_write": "", "review_intake_written": ""}]}
        self.save_ledger(cd, ledger)
        return {"case_id": case_id, "path": str(cd), "round": 1, "status": "intake", "version": SERVER_VERSION}

    def round_new(self, case_id):
        if (e := self.need("front")):
            return e
        cd, ledger, e = self.opened(case_id)
        if e:
            return e
        st = self.status(cd, ledger)
        back = self.pending_return(cd, ledger)
        if st != "delivered" and not (back and back["which"] != "intake" and back["to"] == "front"):
            return err("conflict", "current round is %s: a new round needs delivered or a report checklist with RETURN: front" % st)
        n = ledger["current"] + 1
        for ag in AGENTS:
            (cd / "notes" / ag / ("round-%d" % n)).mkdir(parents=True, exist_ok=True)
        ledger["rounds"].append({"round": n, "revision": 0, "run_id": None, "opened": today(), "intake_dirty": False,
                                 "last_intake_write": "", "review_intake_written": ""})
        ledger["current"] = n
        self.save_ledger(cd, ledger)
        return {"case_id": case_id, "round": n, "status": "intake", "version": SERVER_VERSION}

    def round_revise(self, case_id):
        if (e := self.need("front")):
            return e
        cd, ledger, e = self.opened(case_id)
        if e:
            return e
        cur = self.current(ledger)
        cur["revision"] = cur.get("revision", 0) + 1
        self.save_ledger(cd, ledger)
        return {"case_id": case_id, "round": cur["round"], "revision": cur["revision"], "version": SERVER_VERSION}

    def round_set_run(self, case_id, run_id):
        if (e := self.need("front")):
            return e
        cd, ledger, e = self.opened(case_id)
        if e:
            return e
        st = self.status(cd, ledger)
        if st != "intake_ok":
            return err("conflict", "status is %s; review_intake.md must end with RUNNABLE after the last facts / answers / constraints write" % st)
        if not (cd / "intake" / "products" / run_id / "version.json").exists():
            return err("not_found", "no products %s (version.json missing)" % run_id)
        cur = self.current(ledger)
        cur["run_id"] = run_id
        cur["intake_dirty"] = False
        cur["run_registered"] = now()
        self.save_ledger(cd, ledger)
        (cd / "report" / run_id).mkdir(parents=True, exist_ok=True)
        return {"case_id": case_id, "round": cur["round"], "run_id": run_id, "status": self.status(cd, ledger), "version": SERVER_VERSION}

    # ------------------------------------------------------------ status (any)
    def round_current(self, case_id):
        cd, ledger, e = self.opened(case_id)
        if e:
            return e
        cur = dict(self.current(ledger))
        cur["status"] = self.status(cd, ledger)
        cur["return_to"] = self.pending_return(cd, ledger)
        cur["case_id"] = case_id
        cur["version"] = SERVER_VERSION
        return cur

    def review_status(self, case_id, which):
        cd, ledger, e = self.opened(case_id)
        if e:
            return e
        if which not in VERDICTS:
            return err("invalid", "which must be intake, draft, final, legal_draft or legal_final")
        if which == "intake":
            p = cd / "intake" / "review_intake.md"
        else:
            run_id = self.current(ledger).get("run_id")
            if not run_id:
                return {"which": which, "verdict": "none", "detail": "no run in the current round", "version": SERVER_VERSION}
            p = cd / "report" / run_id / CHECKLISTS[which]
        if not p.exists():
            return {"which": which, "verdict": "none", "path": str(p), "version": SERVER_VERSION}
        text = p.read_text(encoding="utf-8")
        return {"which": which, "verdict": verdict_of(text, which) or "unrecognised", "return_to": return_of(text), "last_line": last_line(text),
                "written": datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "path": str(p), "version": SERVER_VERSION}

    # ------------------------------------------------------------ writes
    def write_intake(self, case_id, name, content):
        if (e := self.need("front")):
            return e
        cd, ledger, e = self.opened(case_id)
        if e:
            return e
        if name not in INTAKE_NAMES:
            return err("invalid", "name must be one of %s" % ", ".join(INTAKE_NAMES))
        if INTAKE_FILES[name].endswith(".json"):
            try:
                data = json.loads(content)
            except ValueError as ex:
                return err("invalid", "not valid JSON: %s" % ex)
            if name == "sources":
                rows = data if isinstance(data, list) else data.get("sources") if isinstance(data, dict) else None
                if not isinstance(rows, list):
                    return err("invalid", "sources must be a list (or {sources: [...]})")
                for i, r in enumerate(rows):
                    missing = [k for k in ("key", "doc", "page", "quote") if k not in r]
                    if missing:
                        return err("invalid", "sources[%d] lacks %s" % (i, ", ".join(missing)))
            content = json.dumps(data, ensure_ascii=False, indent=1)
        path = cd / "intake" / INTAKE_FILES[name]
        self.write_with_prev(path, content)
        cur = self.current(ledger)
        if name in DIRTY_NAMES:
            cur["intake_dirty"] = True
            cur["last_intake_write"] = now()
            self.save_ledger(cd, ledger)
        return {"case_id": case_id, "written": str(path), "prev": path.with_name(path.name + ".prev").exists(),
                "intake_dirty": cur.get("intake_dirty", False), "version": SERVER_VERSION}

    def put_document(self, case_id, name, src_path="", content_base64=""):
        if (e := self.need("front")):
            return e
        cd, ledger, e = self.opened(case_id)
        if e:
            return e
        if not re.fullmatch(r"[^/\\]+", name or ""):
            return err("invalid", "name must be a bare file name")
        dest = cd / "intake" / ("prompt.md" if name == "prompt" else "documents/" + name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src_path:
            src = Path(src_path)
            if not src.is_file():
                return err("not_found", "no file %s" % src_path)
            shutil.copyfile(src, dest)
        elif content_base64:
            dest.write_bytes(base64.b64decode(content_base64))
        else:
            return err("invalid", "give src_path or content_base64")
        return {"case_id": case_id, "written": str(dest), "bytes": dest.stat().st_size, "version": SERVER_VERSION}

    def dialogue_append(self, case_id, speaker, text):
        if (e := self.need("front")):
            return e
        cd, ledger, e = self.opened(case_id)
        if e:
            return e
        if speaker not in ("client", "front"):
            return err("invalid", "speaker must be client or front")
        if not (text or "").strip():
            return err("invalid", "empty text")
        if speaker == "client" and (cd / "log" / "hosted").exists():
            return err("forbidden", "the host records the client's messages word for word; a client entry cannot be written here. "
                                    "What the client has not said is unknown_not_asked")
        tag, _ = self.round_tag(ledger)
        path = cd / "intake" / "dialogue.md"
        n = (path.read_text(encoding="utf-8").count("\n### ") + (1 if path.exists() and path.read_text(encoding="utf-8").startswith("### ") else 0)) + 1 if path.exists() else 1
        self.append(path, "### %s | %s | %s | #%d\n%s" % (today(), tag, speaker, n, text.strip()))
        return {"case_id": case_id, "entry": n, "path": str(path), "version": SERVER_VERSION}

    def client_said(self, case_id, text):
        """The host records a client message, verbatim, before the front agent sees it."""
        cd, _, e = self.opened(case_id)
        if e:
            return e
        marked = cd / "log" / "hosted"
        marked.parent.mkdir(parents=True, exist_ok=True)
        marked.unlink(missing_ok=True)                         # the refusal is for the agent, not for the host
        out = self.dialogue_append(case_id, "client", text)
        marked.write_text("1", encoding="utf-8")
        return out

    def to_collect_append(self, case_id, law, jur, url, why):
        if (e := self.need("front", "analysis")):
            return e
        cd, ledger, e = self.opened(case_id)
        if e:
            return e
        if not (law and jur and why):
            return err("invalid", "law, jur and why are required")
        tag, _ = self.round_tag(ledger)
        path = cd / "intake" / "to_collect.md"
        self.append(path, "- %s | %s | by %s | law: %s | jur: %s | url: %s | why: %s" % (today(), tag, self.agent, law, jur, url or "-", why))
        return {"case_id": case_id, "path": str(path), "version": SERVER_VERSION}

    def merged_rows(self, path, rows):
        """The rows of a sources file with these added, or replaced by id."""
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        old = data if isinstance(data, list) else data.get("sources", [])
        fresh = {r["id"]: r for r in rows}
        return [fresh.pop(r["id"], r) for r in old] + list(fresh.values())

    def apply_edits(self, path, edits, case_id, run_id):
        """Replace sentences in place: each old text must occur exactly once; all or none."""
        if not path.exists():
            return err("not_found", "%s does not exist yet: write it first" % path.name)
        text = path.read_text(encoding="utf-8")
        if not isinstance(edits, list) or not edits:
            return err("invalid", "give a list of {old, new}")
        for i, e in enumerate(edits):
            old = e.get("old") if isinstance(e, dict) else None
            n = text.count(old) if old else 0
            if n != 1:
                return err("invalid", "edits[%d]: the old text occurs %d times, it must occur once; nothing was changed" % (i, n))
            text = text.replace(old, str(e.get("new", "")))
        self.write_with_prev(path, text)
        return {"case_id": case_id, "run_id": run_id, "written": str(path), "edits": len(edits), "version": SERVER_VERSION}

    def edit_report(self, case_id, run_id, edits):
        if (e := self.need("analysis")):
            return e
        cd, ledger, e = self.opened(case_id)
        if e:
            return e
        if self.sectioned(cd, run_id):
            return self.edit_section(case_id, run_id, edits)
        return self.apply_edits(cd / "report" / run_id / "briefing.md", edits, case_id, run_id)

    def edit_polished(self, case_id, run_id, edits):
        if (e := self.need("polish")):
            return e
        cd, ledger, e = self.opened(case_id)
        if e:
            return e
        return self.apply_edits(cd / "report" / run_id / "briefing.polished.md", edits, case_id, run_id)

    def sectioned(self, cd, run_id):
        """A draft built from parts: only when the orchestrator switched it on for this run (sections/.sectioned)."""
        return (cd / "report" / run_id / "sections" / ".sectioned").exists()

    def sections_mod(self):
        sys.path.insert(0, str(HERE))
        import sections as secm
        secm.CASES = self.root
        return secm

    def reassemble(self, cd, case_id, run_id):
        """After a part changed: the draft is put together again, once the section writers have all finished."""
        if (cd / "report" / run_id / "sections" / ".assembled").exists():
            secm = self.sections_mod()
            secm.assemble(case_id, run_id, secm.products_version(case_id, run_id))

    def write_section(self, case_id, run_id, section, content, sources=None):
        """One part of a sectioned draft: report/<run_id>/sections/<section>.md and its sources (ids are given the part as prefix)."""
        if (e := self.need("analysis")):
            return e
        cd, ledger, e = self.opened(case_id)
        if e:
            return e
        cur = self.current(ledger)
        if not cur.get("run_id") or run_id != cur["run_id"]:
            return err("conflict", "run_id %s is not the current round's run (%s)" % (run_id, cur.get("run_id")))
        if not self.sectioned(cd, run_id):
            return err("invalid", "this draft is written whole, not in parts: save each part with write_report mode=append and change sentences with edit_report")
        secm = self.sections_mod()
        if section in secm.PROGRAM:
            return err("invalid", "part %s is written by the program from the sources" % section)
        if section not in secm.ORDER:
            return err("invalid", "section must be one of %s" % ", ".join(x for x in secm.ORDER if x not in secm.PROGRAM))
        lead = secm.TITLES.get(section, "").split(" — ")[0]
        if lead and not re.match(r"^##\s+%s" % re.escape(lead), content.strip()):
            return err("invalid", "part %s must start with its heading line, such as: ## %s" % (section, secm.TITLES[section]))
        rows = []
        if sources not in (None, "", []):
            try:
                data = json.loads(sources) if isinstance(sources, str) else sources
            except ValueError as ex:
                return err("invalid", "sources is not valid JSON: %s" % ex)
            rows = data if isinstance(data, list) else data.get("sources") if isinstance(data, dict) else None
            if not isinstance(rows, list):
                return err("invalid", "sources must be a list of {id, where, claim, kind, ref}")
            for i, r in enumerate(rows):
                if not isinstance(r, dict):
                    return err("invalid", "sources[%d] is not an object" % i)
                missing = [k for k in ("id", "where", "kind", "ref") if k not in r]
                if missing:
                    return err("invalid", "sources[%d] lacks %s" % (i, ", ".join(missing)))
                if r["kind"] not in ("product", "tool", "cite", "url", "document"):
                    return err("invalid", "sources[%d].kind must be product | tool | cite | url | document (names come from the frame)" % i)
                if not str(r["id"]).startswith(section + "-"):
                    r["id"] = "%s-%s" % (section, r["id"])
        sd = cd / "report" / run_id / "sections"
        sd.mkdir(parents=True, exist_ok=True)
        self.write_with_prev(sd / ("%s.md" % section), content.strip() + "\n")
        sp = sd / ("%s.sources.json" % section)
        merged = self.merged_rows(sp, rows) if rows else (json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else [])
        sp.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
        self.reassemble(cd, case_id, run_id)
        return {"case_id": case_id, "run_id": run_id, "section": section, "sources": len(merged), "version": SERVER_VERSION}

    def edit_section(self, case_id, run_id, edits):
        """Sentences of a sectioned draft: each old text must occur exactly once across the parts; all or none."""
        if (e := self.need("analysis")):
            return e
        cd, ledger, e = self.opened(case_id)
        if e:
            return e
        sd = cd / "report" / run_id / "sections"
        files = {q: q.read_text(encoding="utf-8") for q in sorted(sd.glob("*.md"))}
        if not isinstance(edits, list) or not edits:
            return err("invalid", "give a list of {old, new}")
        for i, ed in enumerate(edits):
            old = ed.get("old") if isinstance(ed, dict) else None
            hits = [q for q, t in files.items() if old and old in t]
            n = sum(files[q].count(old) for q in hits) if old else 0
            if n != 1:
                return err("invalid", "edits[%d]: the old text occurs %d times across the parts, it must occur once; nothing was changed" % (i, n))
            files[hits[0]] = files[hits[0]].replace(old, str(ed.get("new", "")))
        for q, t in files.items():
            if q.read_text(encoding="utf-8") != t:
                self.write_with_prev(q, t)
        self.reassemble(cd, case_id, run_id)
        return {"case_id": case_id, "run_id": run_id, "edits": len(edits), "version": SERVER_VERSION}

    def write_report(self, case_id, run_id, name, content, mode="replace"):
        if (e := self.need("analysis")):
            return e
        cd, ledger, e = self.opened(case_id)
        if e:
            return e
        cur = self.current(ledger)
        if not cur.get("run_id") or run_id != cur["run_id"]:
            return err("conflict", "run_id %s is not the current round's run (%s)" % (run_id, cur.get("run_id")))
        if name not in ("briefing", "sources"):
            return err("invalid", "name must be briefing or sources")
        if self.sectioned(cd, run_id):
            if name == "briefing":
                return err("invalid", "this draft is built from parts: write one part with write_section, change sentences with edit_section")
            if mode != "append":
                return err("invalid", "the sources table is never resent whole: add or replace rows with mode=append, or give them with write_section")
            sp = cd / "report" / run_id / "sections" / "extra.sources.json"
            try:
                data = json.loads(content)
            except ValueError as ex:
                return err("invalid", "not valid JSON: %s" % ex)
            rows = data if isinstance(data, list) else data.get("sources") if isinstance(data, dict) else None
            if not isinstance(rows, list) or any(not isinstance(r, dict) or "id" not in r for r in rows):
                return err("invalid", "sources must be a list of {id, where, claim, kind, ref}")
            sp.write_text(json.dumps(self.merged_rows(sp, rows), ensure_ascii=False, indent=1), encoding="utf-8")
            self.reassemble(cd, case_id, run_id)
            return {"case_id": case_id, "run_id": run_id, "written": str(sp), "version": SERVER_VERSION}
        if mode not in ("replace", "append"):
            return err("invalid", "mode must be replace or append")
        path = cd / "report" / run_id / ("briefing.md" if name == "briefing" else "briefing.sources.json")
        if name == "sources":
            try:
                data = json.loads(content)
            except ValueError as ex:
                return err("invalid", "not valid JSON: %s" % ex)
            rows = data if isinstance(data, list) else data.get("sources") if isinstance(data, dict) else None
            if not isinstance(rows, list):
                return err("invalid", "briefing.sources.json must be a list (or {sources: [...]})")
            for i, r in enumerate(rows):
                missing = [k for k in ("id", "kind", "ref") if k not in r]
                if missing:
                    return err("invalid", "sources[%d] lacks %s" % (i, ", ".join(missing)))
                if r["kind"] not in ("product", "tool", "cite", "url", "document", "name"):
                    return err("invalid", "sources[%d].kind must be product | tool | cite | url | document | name" % i)
            content = json.dumps(self.merged_rows(path, rows) if mode == "append" else data, ensure_ascii=False, indent=1)
        elif mode == "append" and path.exists():
            content = path.read_text(encoding="utf-8").rstrip() + "\n\n" + content.strip() + "\n"
        self.write_with_prev(path, content)
        return {"case_id": case_id, "run_id": run_id, "written": str(path), "prev": path.with_name(path.name + ".prev").exists(),
                "version": SERVER_VERSION}

    def write_polished(self, case_id, run_id, name, content, mode="replace"):
        if (e := self.need("polish")):
            return e
        cd, ledger, e = self.opened(case_id)
        if e:
            return e
        cur = self.current(ledger)
        if not cur.get("run_id") or run_id != cur["run_id"]:
            return err("conflict", "run_id %s is not the current round's run (%s)" % (run_id, cur.get("run_id")))
        if name not in ("polished", "sources"):
            return err("invalid", "name must be polished or sources")
        if self.status(cd, ledger) not in ("reviewed", "polished", "delivered"):
            return err("conflict", "the draft has not passed review: review.md must end with POLISHABLE and be newer than the draft")
        rd = cd / "report" / run_id
        if not (rd / "briefing.md").exists():
            return err("conflict", "no analysis draft (briefing.md) to polish yet")
        if name == "sources":
            try:
                data = json.loads(content)
            except ValueError as ex:
                return err("invalid", "not valid JSON: %s" % ex)
            rows = data if isinstance(data, list) else data.get("sources") if isinstance(data, dict) else None
            if not isinstance(rows, list) or not rows:
                return err("invalid", "send a non-empty list of {id, where}")
            draft_data = json.loads((rd / "briefing.sources.json").read_text(encoding="utf-8"))
            draft_rows = {r["id"]: r for r in (draft_data if isinstance(draft_data, list) else draft_data.get("sources", []))}
            merged, seen = [], set()
            for i, r in enumerate(rows):
                sid, where = r.get("id"), r.get("where")
                if sid not in draft_rows:
                    return err("invalid", "sources[%d]: %s is not in the draft sources table; polish adds no sources" % (i, sid))
                if not where or sid in seen:
                    return err("invalid", "sources[%d]: %s has no where, or appears twice" % (i, sid))
                seen.add(sid)
                merged.append(dict(draft_rows[sid], where=where))         # claim, kind and ref always come from the draft
            if mode == "append":
                merged = self.merged_rows(rd / "briefing.polished.sources.json", merged)
            content = json.dumps(merged, ensure_ascii=False, indent=1)
        path = rd / ("briefing.polished.md" if name == "polished" else "briefing.polished.sources.json")
        if name == "polished" and mode == "append" and path.exists():          # written part by part: the next part goes at the end
            content = path.read_text(encoding="utf-8").rstrip() + "\n\n" + content.strip() + "\n"
        self.write_with_prev(path, content)
        return {"case_id": case_id, "run_id": run_id, "written": str(path), "prev": path.with_name(path.name + ".prev").exists(),
                "version": SERVER_VERSION}

    def client_copy(self, rd, case_id, run_id):
        """The client copy of the draft (2026-11-06, no polish stage): {{block:<name>}} markers expanded from frame/blocks, the
        internal reference line and any line carrying the case or run id removed. Written as briefing.polished.md for the renderer
        and the web host; the sources table is copied beside it."""
        text = (rd / "briefing.md").read_text(encoding="utf-8")
        fb = rd / "frame" / "blocks"
        if fb.exists():
            text = re.sub(r"\{\{block:([a-z_]+)\}\}", lambda m: (fb / ("%s.md" % m.group(1))).read_text(encoding="utf-8").strip()
                          if (fb / ("%s.md" % m.group(1))).exists() else m.group(0), text)
        kept = [l for l in text.splitlines() if case_id not in l and run_id not in l]
        text = "\n".join(kept).rstrip() + "\n"
        (rd / "briefing.polished.md").write_text(text, encoding="utf-8")
        sj = rd / "briefing.sources.json"
        if sj.exists():
            (rd / "briefing.polished.sources.json").write_text(sj.read_text(encoding="utf-8"), encoding="utf-8")
        return rd / "briefing.polished.md"

    def render_pdf(self, case_id, run_id):
        if self.agent not in ("analysis", "polish", "front"):   # front is also the program's identity (the orchestrator's render step)
            return err("forbidden", "render_pdf belongs to the analysis agent and the program")
        cd, ledger, e = self.opened(case_id)
        if e:
            return e
        rd = cd / "report" / run_id
        if self.agent == "polish":                             # old flow: the polish agent's own report
            src = rd / "briefing.polished.md"
            if not src.exists():
                return err("not_found", "no briefing.polished.md to render; write the polished report first")
            text_problems = self.report_check(case_id, run_id, "polished", text_only=True).get("problems", [])
        else:
            if not (rd / "briefing.md").exists():
                return err("not_found", "no briefing.md to render; write the draft first")
            text_problems = self.report_check(case_id, run_id, "draft", text_only=True).get("problems", [])
            src = None
        if text_problems:                                      # a render takes a minute: settle the text first
            return err("conflict", "fix the text first, nothing was rendered: " + "; ".join(text_problems[:8]))
        if src is None:
            src = self.client_copy(rd, case_id, run_id)
        out = rd / "briefing.pdf"
        script = HERE / "render_pdf.py"
        try:
            import subprocess
            r = subprocess.run([sys.executable, str(script), str(src), str(out)], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=300, cwd=str(PROJECT))
        except Exception as ex:  # noqa: BLE001
            return err("internal", "render failed to start: %s" % ex)
        if r.returncode != 0 or not out.exists():
            return err("internal", "render failed: %s" % (r.stderr or r.stdout)[-600:])
        m = re.search(r"pages=(\d+) latex_errors=(\d+) overfull=(\d+)", r.stdout)
        pages, errors, overfull = (int(x) for x in m.groups()) if m else (None, None, None)
        line = next((l for l in r.stdout.splitlines() if l.startswith("layout=")), "layout={}")
        layout = json.loads(line[len("layout="):])
        advice = ""
        body = layout.get("body_pages")
        if body and body > BODY_LIMIT:
            advice = "%d body pages, the limit is %d: cut text and rerender" % (body, BODY_LIMIT)
        elif body and body < BODY_FLOOR:
            advice = "%d body pages, the floor is %d: restore reasoning from the draft and rerender" % (body, BODY_FLOOR)
        return {"case_id": case_id, "run_id": run_id, "written": str(out), "pages": pages, "body_pages": layout.get("body_pages"), "body_floor": BODY_FLOOR, "body_limit": BODY_LIMIT,
                "advice": advice, "latex_errors": errors, "overfull": overfull,
                "layout": layout, "version": SERVER_VERSION}

    def write_review(self, case_id, which, content, run_id=""):
        if (e := self.need("review")):
            return e
        cd, ledger, e = self.opened(case_id)
        if e:
            return e
        if which not in VERDICTS:
            return err("invalid", "which must be intake, draft, final, legal_draft or legal_final")
        v = verdict_of(content, which)
        if v is None:
            return err("invalid", "last line must end with one of %s" % " / ".join(VERDICTS[which]), last_line=last_line(content))
        if which != "intake" and v == "REVISE" and return_of(content) not in RETURNS[which]:
            return err("invalid", "a REVISE checklist needs the line RETURN: <%s> just before the verdict" % " | ".join(RETURNS[which]))
        reps = replacements_of(content)
        if reps is None:
            return err("invalid", "the ```replacements block must hold a JSON list of {old, new}: the exact sentence of the draft and its replacement")
        refs, problems = findings_of(content)
        if which != "intake" and v == "REVISE" and not problems and not reps:   # 2026-11-06: a verdict must follow from the entries
            return err("invalid", "a REVISE checklist needs at least one Problem entry that states a problem; when every item is 'none', the verdict is %s" % VERDICTS[which][0])
        cur = self.current(ledger)
        if which == "intake":
            path = cd / "intake" / "review_intake.md"
        else:
            if not cur.get("run_id") or (run_id and run_id != cur["run_id"]):
                if not cur.get("run_id"):
                    return err("conflict", "this round has no run yet: the case is at the intake stage (status %s), so the only review now is which=intake; "
                                           "report folders of earlier rounds are not reviewed again. This is not a system defect" % self.status(cd, ledger))
                return err("conflict", "run_id %s is not the current round's run (%s)" % (run_id, cur.get("run_id")))
            rd = cd / "report" / cur["run_id"]
            subject = rd / ("briefing.md" if which in ("draft", "legal_draft") else "briefing.polished.md")
            if not subject.exists():
                return err("conflict", "there is no %s to review yet" % subject.name)
            path = rd / CHECKLISTS[which]
            if v == "REVISE" and refs and which in ("draft", "legal_draft") and not reps:   # a re-check reopens nothing that did not change
                stale = self.unchanged_lines(cd, cur["run_id"], refs, path)
                if stale is not None and stale == refs:
                    return err("invalid", "every line your findings refer to (%s) is unchanged since your last checklist and was not among its findings: "
                                          "a re-check checks the changed lines and whether the items you sent back are fixed; record anything else as a doubt, "
                                          "or give the fix as a replacements block" % ", ".join(str(n) for n in sorted(refs)))
        self.write_with_prev(path, content)
        if which == "intake":
            cur["review_intake_written"] = now()
            cur["intake_dirty"] = False                       # the review now postdates every intake write
            self.save_ledger(cd, ledger)
        return {"case_id": case_id, "which": which, "verdict": v, "written": str(path), "status": self.status(cd, ledger),
                "version": SERVER_VERSION}

    def unchanged_lines(self, cd, run_id, refs, checklist):
        """The subset of `refs` (line numbers of briefing.md) that neither changed since the last reviewed snapshot nor appeared in the
        previous checklist; None when there is no snapshot of this run."""
        snap = cd / "log" / "reviewed" / "review_draft"
        if not (snap / "briefing.md").exists() or not (snap / "run.txt").exists() or (snap / "run.txt").read_text(encoding="utf-8") != str(run_id):
            return None
        import difflib
        old = (snap / "briefing.md").read_text(encoding="utf-8").splitlines()
        new = (cd / "report" / run_id / "briefing.md").read_text(encoding="utf-8").splitlines()
        changed = set()
        for tag, _, _, j1, j2 in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
            if tag != "equal":
                changed.update(range(j1 + 1, max(j2, j1 + 1) + 1))
        before = checklist.read_text(encoding="utf-8") if checklist.exists() else ""
        cited, _ = findings_of(before)
        return {n for n in refs if n not in changed and n not in cited}

    def apply_replacements(self, case_id, run_id):
        """Program step (2026-11-06): the reviewers' fix-to-order replacements, applied to briefing.md without a model; the checklists are
        re-stamped so the review still postdates the draft. Returns {applied, failed}; a failed replacement names the sentence not found."""
        cd, ledger, e = self.opened(case_id)
        if e:
            return e
        rd = cd / "report" / run_id
        path = rd / "briefing.md"
        text = path.read_text(encoding="utf-8")
        applied, already, failed, stamps = 0, 0, [], []
        for which in ("draft", "legal_draft"):
            p = rd / CHECKLISTS[which]
            if not p.exists():
                continue
            stamps.append(p)
            for r in replacements_of(p.read_text(encoding="utf-8")) or []:
                if text.count(r["old"]) == 1:
                    text = text.replace(r["old"], r["new"])
                    applied += 1
                elif r["old"] not in text and r["new"] and r["new"] in text:      # applied on an earlier pass of the same checklist
                    already += 1
                else:
                    failed.append("%s: %s" % (which, r["old"][:80]))
        if applied:
            self.write_with_prev(path, text)
            t = max(path.stat().st_mtime, time.time())          # the checklists postdate the draft again, and nothing written later is older
            for p in stamps:
                os.utime(p, (t, t))
        return {"case_id": case_id, "run_id": run_id, "applied": applied, "already": already, "failed": failed}

    def autofix_draft(self, case_id, run_id):
        """Program step (2026-11-06): what the self-check would send back but the program can settle itself: sources rows whose ref
        points at a notebook or bug file (not a record) are dropped. Returns the list of fixes made."""
        cd, ledger, e = self.opened(case_id)
        if e:
            return e
        sj = cd / "report" / run_id / "briefing.sources.json"
        if not sj.exists():
            return {"fixes": []}
        try:
            data = json.loads(sj.read_text(encoding="utf-8"))
        except ValueError:
            return {"fixes": []}
        rows = data if isinstance(data, list) else data.get("sources", [])
        keep, fixes = [], []
        for r in rows:
            ref = str(r.get("ref", ""))
            if re.match(r"^file:[^ ]*/(bugs|notes)/", ref):
                fixes.append("dropped sources row %s: ref %s is not a record" % (r.get("id"), ref))
            else:
                keep.append(r)
        if fixes:
            self.write_with_prev(sj, json.dumps(keep if isinstance(data, list) else {**data, "sources": keep}, ensure_ascii=False, indent=1))
        return {"fixes": fixes}

    def notes_append(self, case_id, book, text):
        cd, ledger, e = self.opened(case_id)
        if e:
            return e
        if book not in BOOKS[self.agent]:
            return err("invalid", "%s's books are %s" % (self.agent, ", ".join(BOOKS[self.agent])))
        if not (text or "").strip():
            return err("invalid", "empty text")
        cur = self.current(ledger)
        tag, run_id = self.round_tag(ledger)
        path = cd / "notes" / self.agent / ("round-%d" % cur["round"]) / (book + ".md")
        n = len(re.findall(r"^### %s-(\d+) " % re.escape(book), path.read_text(encoding="utf-8"), re.M)) + 1 if path.exists() else 1
        self.append(path, "### %s-%d | %s | %s | %s\n%s" % (book, n, today(), tag, run_id or "-", text.strip()))
        return {"case_id": case_id, "book": book, "entry": "%s-%d" % (book, n), "path": str(path), "version": SERVER_VERSION}

    def open_defects(self, case_id):
        """Bugs of the current round that affect a figure or the ranking, not yet cleared: the run may not pass them."""
        cd, ledger, e = self.opened(case_id)
        if e or not (cd / "bugs").exists():
            return []
        cleared = cd / "bugs" / "cleared.md"
        done = set(cleared.read_text(encoding="utf-8").split()) if cleared.exists() else set()
        out = []
        for path in sorted((cd / "bugs").glob("*.md")):
            if path.stem not in ("analysis", "review"):        # the agents that see the figures
                continue
            for bid, tag, body in re.findall(r"^### (B-\d+) \| [^|]*\| round (\d+)[^\n]*\n(.*?)(?=^### B-|\Z)", path.read_text(encoding="utf-8"), re.S | re.M):
                name = "%s/%s" % (path.stem, bid)
                if int(tag) == ledger["current"] and "- affects_result: yes" in body and name not in done:
                    out.append(name)
        return out

    def clear_defect(self, case_id, name):
        """After the fix: the named bug (<agent>/B-n) no longer holds the run."""
        cd, _, e = self.opened(case_id)
        if e:
            return e
        self.append(cd / "bugs" / "cleared.md", name)
        return {"case_id": case_id, "cleared": name, "open": self.open_defects(case_id)}

    def bug_append(self, case_id, layer, symptom, expected, repro, workaround, affects_result=False, effect=""):
        cd, ledger, e = self.opened(case_id)
        if e:
            return e
        if not (layer and symptom):
            return err("invalid", "layer and symptom are required")
        if affects_result and not (effect or "").strip():         # 2026-11-06: a defect holds the run only when it changes a figure of this case
            return err("invalid", "affects_result=true needs effect: which figure or ranking of this case changes, and from what to what; "
                                  "a modelling gap that leaves this case's figures as they are is affects_result=false")
        tag, _ = self.round_tag(ledger)
        path = cd / "bugs" / (self.agent + ".md")
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        entries = re.findall(r"^### (B-\d+) \|.*?\n(.*?)(?=^### B-|\Z)", text, re.S | re.M)
        key = squash(symptom)
        for bid, body in entries:
            m = re.search(r"^- symptom: (.*?)(?=^- |\Z)", body, re.S | re.M)
            if m and squash(m.group(1)) == key:
                self.append(path, "- recurrence %s | %s | %s" % (tag, today(), bid))
                return {"case_id": case_id, "duplicate_of": bid, "path": str(path), "version": SERVER_VERSION}
        n = len(entries) + 1
        body = ("### B-%d | %s | %s\n- layer: %s\n- symptom: %s\n- expected: %s\n- repro: %s\n- workaround: %s"
                % (n, today(), tag, layer, symptom.strip(), (expected or "-").strip(), (repro or "-").strip(), (workaround or "blocked").strip()))
        if affects_result:
            body += "\n- affects_result: yes\n- effect: %s" % effect.strip()
        self.append(path, body)
        return {"case_id": case_id, "entry": "B-%d" % n, "path": str(path), "version": SERVER_VERSION}

    # ------------------------------------------------------------ self-checks (any, read-only)
    def intake_check(self, case_id):
        cd, ledger, e = self.opened(case_id)
        if e:
            return e
        it = cd / "intake"
        problems = []

        def load(name):
            p = it / name
            if not p.exists():
                problems.append("%s missing" % name)
                return None
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except ValueError as ex:
                problems.append("%s is not valid JSON: %s" % (name, ex))
                return None

        facts, sources, answers = load("facts.json"), load("sources.json"), load("answers.json")
        shape = shape_problems(facts) if isinstance(facts, dict) else []
        problems += shape
        if facts is not None and not shape:
            cwd = os.getcwd()
            try:
                sys.path.insert(0, str(PROJECT / "optimization" / "tools"))
                import optimize as op  # noqa: E402
                os.chdir(PROJECT)                          # relative paths in facts.json (e.g. fx) resolve against the project root (bug B-2)
                op.Optimizer(facts)
            except Exception as ex:  # noqa: BLE001
                problems.append("facts.json rejected by the optimizer: %s: %s" % (type(ex).__name__, str(ex)[:200]))
            finally:
                os.chdir(cwd)
        cons_path = it / "constraints.json"
        if cons_path.exists():
            try:
                cons = json.loads(cons_path.read_text(encoding="utf-8"))
                odd = sorted(k for k in cons if k not in CONSTRAINT_KEYS) if isinstance(cons, dict) else ["(not an object)"]
                if odd:
                    problems.append("constraints.json keys the optimizer does not read: %s (allowed: %s); other notes go into handoff.md" % (", ".join(odd), ", ".join(CONSTRAINT_KEYS)))
            except ValueError as ex:
                problems.append("constraints.json is not valid JSON: %s" % ex)
        if facts is not None and sources is not None:
            rows = sources if isinstance(sources, list) else sources.get("sources", [])
            keys = {r.get("key") for r in rows}
            leaves = [k for k in flatten(facts) if not k.startswith(("mode", "date", "assume", "destinations", "limits", "as_of", "fx", "case", "note"))]
            missing = [k for k in leaves if k not in keys and k.split(".")[0] not in keys]
            if missing:
                problems.append("facts keys without a sources entry: %s" % ", ".join(missing[:30]))
            for i, r in enumerate(rows):
                for k in ("doc", "page", "quote"):
                    if not r.get(k) and r.get("doc") != "prompt":
                        problems.append("sources[%d] (%s) lacks %s" % (i, r.get("key"), k))
                if r.get("confirmed_by_client") and not r.get("confirmed_note"):
                    problems.append("sources[%d] (%s) confirmed_by_client without confirmed_note" % (i, r.get("key")))
        if isinstance(facts, dict):
            if facts.get("answers"):
                problems.append("facts.json carries answers: answers.json is the only record of them")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(facts.get("instructed_on") or "")):
                problems.append("facts.json lacks instructed_on: the date the client gave the instruction, YYYY-MM-DD")
            for i, row in enumerate(facts.get("past_payments") or []):
                if not (isinstance(row, dict) and row.get("date") and row.get("payee_share")):
                    problems.append("past_payments[%d] needs date and payee_share; its other fields are gross, withheld, net_received, treaty_claimed, source" % i)
        dialogue = (it / "dialogue.md").read_text(encoding="utf-8") if (it / "dialogue.md").exists() else ""
        dq = squash(dialogue)
        known = predicates()
        if answers is not None:
            for pred, a in (answers.items() if isinstance(answers, dict) else []):
                if pred not in known:
                    problems.append("answers[%s] is not a predicate of rule/predicate.csv: a factor goes into facts.json" % pred)
                val = a.get("value") if isinstance(a, dict) else a
                quote = a.get("quote", "") if isinstance(a, dict) else ""
                if val in ("yes", "no", "unknown_asked"):
                    if not quote:
                        problems.append("answers[%s]=%s without the client's words: write {\"value\": \"%s\", \"quote\": \"<the client's words>\"}; if the client has not spoken to this point it is unknown_not_asked" % (pred, val, val))
                    elif squash(quote) not in dq:
                        problems.append("answers[%s] quote not found in dialogue.md: quote the client's own message; if the client has not spoken to this point it is unknown_not_asked" % pred)
                elif val not in ("unknown_not_asked", "unknown"):
                    problems.append("answers[%s] has value %r (allowed: yes, no, unknown_asked, unknown_not_asked): the status itself is the value, "
                                    "{\"value\": \"unknown_not_asked\"} for a point the client has not spoken to" % (pred, val))
        st = self.status(cd, ledger)
        passed_intake = st != "intake"                                   # a round past intake_ok (ran, drafted, ...) passed its intake review
        note = ("" if passed_intake else
                "status is still intake: intake_ok needs the stage-1 review to end with RUNNABLE after the last facts / answers / constraints write; an empty problems list is not that review")
        return {"case_id": case_id, "status": st, "intake_ok": passed_intake, "problems": problems, "note": note, "version": SERVER_VERSION}

    def _lib(self):
        if self._db is None:
            sys.path.insert(0, str(PROJECT / "database" / "tools"))
            import mcp_server as dbm  # noqa: E402
            self._db = dbm.Library(PROJECT / "database")
        return self._db

    def part_check(self, cd, case_id, run_id, part, which="polished"):
        """report_check of one part of the polished report while it is written part by part: numbers the draft does not
        have, system identifiers, the optimizer's vocabulary, spoken lead-ins and over-long sentences, in that part only.
        The whole-report checks (parts present, sources, where fragments, PDF) run once all parts are written.
        On the draft (which=draft, 2026-11-05: analysis also writes part by part) only the identifier and vocabulary
        checks apply; figures and sources are checked by the whole-draft report_check."""
        rd = cd / "report" / run_id
        pol, draft = rd / "briefing.polished.md", rd / "briefing.md"
        if not draft.exists() or (which == "polished" and not pol.exists()):
            return err("not_found", "the %s of run %s is missing" % ("polished report" if draft.exists() else "draft", run_id))
        text = (pol if which == "polished" else draft).read_text(encoding="utf-8")
        piece = part_text(text, part)
        if piece is None:
            return err("not_found", "no part %s in the %s yet; parts present: %s" % (part, which, ", ".join(o["part"] for o in outline(text))))
        if which == "draft":
            problems = []
            leaks = sorted({m.group(0) for pat in LEAKS for m in re.finditer(pat, piece)})
            if leaks:
                problems.append("system identifiers: %s" % ", ".join(leaks[:12]))
            if part not in ("A", "B"):
                jargon = sorted({m.group(0).lower() for m in re.finditer(JARGON, piece)})
                if jargon:
                    problems.append("the optimizer's vocabulary, say it as an adviser would: " + ", ".join(jargon))
            return {"case_id": case_id, "run_id": run_id, "target": "draft", "part": part, "problems": problems,
                    "parts_present": [o["part"] for o in outline(text)], "version": SERVER_VERSION}
        draft_text = draft.read_text(encoding="utf-8")
        fb = rd / "frame" / "blocks"
        if fb.exists():
            draft_text = re.sub(r"\{\{block:([a-z_]+)\}\}", lambda m: (fb / ("%s.md" % m.group(1))).read_text(encoding="utf-8")
                                if (fb / ("%s.md" % m.group(1))).exists() else m.group(0), draft_text)
        problems = []
        drift = sorted(numbers_in(piece) - numbers_in(draft_text))
        if drift:
            problems.append("numbers in this part that are not in the draft: " + ", ".join(drift[:12]))
        if case_id in piece or run_id in piece:
            problems.append("the client report carries the case id or run id")
        leaks = sorted({m.group(0) for pat in LEAKS for m in re.finditer(pat, piece)})
        if leaks:
            problems.append("system identifiers: %s" % ", ".join(leaks[:12]))
        spoken = sorted(set(re.findall(SPOKEN, piece)))
        if spoken:
            problems.append("spoken lead-ins, use the register of a written opinion: " + ", ".join(spoken))
        if part not in ("A", "B"):
            jargon = sorted({m.group(0).lower() for m in re.finditer(JARGON, piece)})
            if jargon:
                problems.append("the optimizer's vocabulary, say it as an adviser would: " + ", ".join(jargon))
            for s in long_sentences(piece)[:5]:
                problems.append("sentence too long, split it: " + s)
        return {"case_id": case_id, "run_id": run_id, "target": "polished", "part": part, "problems": problems, "number_drift": drift,
                "version": SERVER_VERSION}

    def report_check(self, case_id, run_id, target="auto", text_only=False, part=""):
        cd, ledger, e = self.opened(case_id)
        if e:
            return e
        if part:
            polished_exists = (cd / "report" / run_id / "briefing.polished.md").exists()
            return self.part_check(cd, case_id, run_id, str(part), "draft" if target == "draft" or (target == "auto" and not polished_exists) else "polished")
        rd = cd / "report" / run_id
        problems = []
        pol, pol_sj = rd / "briefing.polished.md", rd / "briefing.polished.sources.json"
        draft, draft_sj = rd / "briefing.md", rd / "briefing.sources.json"
        if target == "draft" or (target == "auto" and not pol.exists()):
            which, md, sj = "draft", draft, draft_sj
        else:
            which, md, sj = "polished", pol, pol_sj
        if not md.exists():
            return err("not_found", "no %s report for run %s" % (which, run_id))
        br = md
        text = br.read_text(encoding="utf-8")
        if which == "draft" and (case_id not in text or run_id not in text):
            problems.append("internal reference line lacks case_id or run_id")
        if which == "polished" and (case_id in text or run_id in text):
            problems.append("the client report carries the case id or run id: remove the internal reference line")
        heads = [(m.start(), m.group(1)) for m in re.finditer(r"^#{1,3}\s+(.+)$", text, re.M)]
        pos = {}
        for cn, en in PARTS:
            hit = [i for i, (_, h) in enumerate(heads) if (cn in h or en in h.lower()) and not re.match(r"^(附录|Appendix)", h)]
            # "strategy" also matches the strategy-plan heading; "执行" also matches "执行落地" inside part 2 only if it were a heading
            if cn == "策略思路":
                hit = [i for i in hit if "策略方案" not in heads[i][1] and "策略筹划" not in heads[i][1] and "plan" not in heads[i][1].lower()]
            if cn == "执行":
                hit = [i for i in hit if "落地" not in heads[i][1]]
            if not hit:
                problems.append("part missing: %s" % cn)
            else:
                pos[cn] = hit[0]
        for ap in ("A", "B"):
            if not re.search(r"^#{1,3}\s+(附录|Appendix)\s*%s\b" % ap, text, re.M):
                problems.append("appendix %s missing" % ap)
        body_end = min([p for p, h in heads if re.match(r"^(附录|Appendix)", h)] or [len(text)])
        body = text if which == "polished" else text[:body_end]
        leaks = sorted({m.group(0) for pat in LEAKS for m in re.finditer(pat, body)})
        if leaks:
            problems.append("system identifiers in the body: %s" % ", ".join(leaks[:12]))
        facts_path = cd / "intake" / "facts.json"
        instructed = json.loads(facts_path.read_text(encoding="utf-8")).get("instructed_on") if facts_path.exists() else None
        stated = report_date(text)
        if instructed and stated != instructed:
            problems.append("the heading date is %s, the client instructed on %s: the report speaks as of the instruction" % (stated, instructed))
        past = cd / "intake" / "products" / run_id / "past_payments.json"
        for row in (json.loads(past.read_text(encoding="utf-8"))["past_payments"] if past.exists() else []):
            must = [row["refundable_if_qualified"]] if row.get("refundable_if_qualified") else []
            if row.get("conflicts"):
                must += [row.get("withheld_stated"), row.get("payee_share")]
            for figure in must:
                if figure is not None and "{:,.0f}".format(float(figure)) not in text:
                    problems.append("past payment of %s: the report lacks the figure %s" % (row["date"], "{:,.0f}".format(float(figure))))

        def load(path, label):
            if not path.exists():
                problems.append("%s missing" % label)
                return []
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return data if isinstance(data, list) else data.get("sources", [])
            except ValueError as ex:
                problems.append("%s invalid: %s" % (label, ex))
                return []
        rows = load(sj, which + " sources.json")
        if not rows:
            problems.append("%s sources.json has no entries" % which)
        for r in rows:
            if not r.get("where"):
                problems.append("source %s lacks where" % r.get("id"))
            kind, ref = r.get("kind"), str(r.get("ref", ""))
            if kind == "product":
                if re.match(r"^(\d{8}-[0-9a-f]{8}|CASE-\d{8}-[0-9a-f]{6}):[a-z_]+:", ref):
                    continue                                    # a record id of the retrieval layer (products or case file): cite_check below resolves it
                p = (cd / ref) if not Path(ref).is_absolute() else Path(ref)
                if not p.exists() and not (self.root / ref).exists():
                    problems.append("source %s: product path not found: %s" % (r.get("id"), ref))
            elif kind == "cite":
                cite = ref.split()[0]
                if cite not in self._lib().by_cite:
                    problems.append("source %s: cite_id not in the library: %s" % (r.get("id"), cite))
        imp_path = rd / "impact.json"
        if which == "draft" and imp_path.exists():                      # a revised edition: what the last edition said and no longer holds
            try:
                imp = json.loads(imp_path.read_text(encoding="utf-8"))
            except ValueError:
                imp = {}
            if imp.get("level") == "revise":
                body = squeeze(text)
                kept = [s for s in imp.get("stale", []) if squeeze(s.get("fragment", "")) and squeeze(s["fragment"]) in body]
                if kept:
                    problems.append("stale sentences of the last edition carried unchanged: " + "; ".join('"%s"' % s["fragment"][:80] for s in kept[:8]))
                sys.path.insert(0, str(HERE))
                import impact as impm
                impm.CASES = self.root
                try:
                    old = impm.products_dir(case_id, imp["baseline_run"])
                    new = impm.products_dir(case_id, run_id)
                    gone = impm.amounts_in(old) - impm.amounts_in(new) - set(imp.get("time_only") or [])
                    still = sorted({s["figure"] for s in impm.sentences_with(text, gone)})
                    if still:
                        problems.append("figures of the last edition that this run's products no longer state: " + ", ".join(still[:12]))
                except (OSError, KeyError, ValueError) as ex:
                    problems.append("revised edition check failed: %s" % ex)
                if not re.search(r"(?i)chang\w* since (the|our) (last|previous|earlier)", text[:6000]):
                    problems.append("a revised edition opens Part 1 with a note of what changed since the last edition")
        if which == "draft":                                    # provenance (agent/retrieval_spec.en.md §10 cite_check)
            try:
                if str(HERE) not in sys.path:
                    sys.path.insert(0, str(HERE))
                import read_core
                cc = read_core.Reader(self.agent, cases_root=self.root, log=False).cite_check(case_id, run_id, "draft")
            except Exception as ex:                             # noqa: BLE001
                cc = {"error": "internal", "detail": "%s: %s" % (type(ex).__name__, ex)}
            if not cc.get("error"):
                if cc["unresolved_refs"]:
                    problems.append("sources rows whose ref does not resolve (use the ids tax-read returns): " +
                                    ", ".join("%s %s" % (u["id"], u["ref"][:60]) for u in cc["unresolved_refs"][:10]))
                if cc["uncovered_figures"]:
                    problems.append("figures that no source row states (cite the record or clause that gives them, or take the figure from it): " +
                                    "; ".join('%s in "%s"' % (u["figure"], u["line"][:70]) for u in cc["uncovered_figures"][:10]))
        # polish may cut but not change: a number new to the report is a problem, a number left out is only listed for review
        drift, omitted, changed, cut, unlocated, pdf_pages, body_pages = [], [], [], [], [], None, None
        if which == "draft":                                   # 2026-11-06: the draft is the client report, so it meets the client's standard too
            if not re.search(r"^```flow\s*$", text, re.M):
                problems.append("no ```flow block (the restructuring diagram, JSON as in agent/templates/flowchart.example.json) in Part 1")
            spoken = sorted(set(re.findall(SPOKEN, text)))
            if spoken:
                problems.append("spoken lead-ins, use the register of a written opinion: " + ", ".join(spoken))
            jargon = sorted({m.group(0).lower() for m in re.finditer(JARGON, text[:body_end])})
            if jargon:
                problems.append("the optimizer's vocabulary in the body, say it as an adviser would: " + ", ".join(jargon))
            for s in long_sentences(text[:body_end])[:5]:
                problems.append("sentence too long, split it: " + s)
            pdf = rd / "briefing.pdf"
            if text_only:
                pass
            elif not pdf.exists() or pdf.stat().st_mtime < md.stat().st_mtime:
                problems.append("briefing.pdf is missing or older than the draft: call render_pdf")
            else:
                if str(HERE) not in sys.path:
                    sys.path.insert(0, str(HERE))
                from render_pdf import layout
                shape = layout(pdf, (rd / "briefing.polished.md").read_text(encoding="utf-8") if (rd / "briefing.polished.md").exists() else text)
                pdf_pages, body_pages = shape["pages"], shape["body_pages"]
                if body_pages > BODY_LIMIT:
                    problems.append("the body has %d pages before the appendices, limit %d: cut" % (body_pages, BODY_LIMIT))
                elif body_pages < BODY_FLOOR:
                    problems.append("the body has %d pages before the appendices, floor %d" % (body_pages, BODY_FLOOR))
        if which == "polished" and draft.exists():
            draft_text = draft.read_text(encoding="utf-8")
            fb = rd / "frame" / "blocks"                     # a whole draft keeps {{block:<name>}} markers: count the figures of the tables they stand for
            if fb.exists():
                draft_text = re.sub(r"\{\{block:([a-z_]+)\}\}", lambda m: (fb / ("%s.md" % m.group(1))).read_text(encoding="utf-8")
                                    if (fb / ("%s.md" % m.group(1))).exists() else m.group(0), draft_text)
            before, after = numbers_in(draft_text), numbers_in(text)
            drift, omitted = sorted(after - before), sorted(before - after)
            if drift:
                problems.append("numbers in the polished report that are not in the draft: " + ", ".join(drift[:12]))
            pol_rows = {r.get("id"): r for r in rows}
            for r in (load(draft_sj, "draft sources.json") if draft_sj.exists() else []):
                p = pol_rows.get(r.get("id"))
                if p is None:
                    cut.append(str(r.get("id")))
                elif any(p.get(k) != r.get(k) for k in ("claim", "kind", "ref")):
                    changed.append(str(r.get("id")))
            if changed:
                problems.append("claims changed from the draft sources table: " + ", ".join(changed[:12]))
            body_text = squeeze(text)
            for r in rows:
                w = str(r.get("where") or "")
                frag = w.split("|", 1)[1] if "|" in w else w
                pieces = [squeeze(p) for p in re.split(r"…|\.\.\.", frag) if squeeze(p)]
                if not pieces or not all(p in body_text for p in pieces):
                    unlocated.append(str(r.get("id")))
            if unlocated:
                problems.append("%d of %d where fragments are not verbatim in the polished report: %s" % (len(unlocated), len(rows), ", ".join(unlocated[:12])))
            spoken = sorted(set(re.findall(SPOKEN, text)))
            if spoken:
                problems.append("spoken lead-ins, use the register of a written opinion: " + ", ".join(spoken))
            jargon = sorted({m.group(0).lower() for m in re.finditer(JARGON, text[:body_end])})
            if jargon:
                problems.append("the optimizer's vocabulary in the body, say it as an adviser would: " + ", ".join(jargon))
            for s in long_sentences(text[:body_end])[:5]:
                problems.append("sentence too long, split it: " + s)
            pdf = rd / "briefing.pdf"
            if text_only:
                pass
            elif not pdf.exists() or pdf.stat().st_mtime < md.stat().st_mtime:
                problems.append("briefing.pdf is missing or older than the polished report: call render_pdf")
            else:
                if str(HERE) not in sys.path:
                    sys.path.insert(0, str(HERE))
                from render_pdf import layout
                shape = layout(pdf, text)
                pdf_pages, body_pages = shape["pages"], shape["body_pages"]
                if body_pages > BODY_LIMIT:
                    problems.append("the body has %d pages before the appendices, limit %d" % (body_pages, BODY_LIMIT))
                elif body_pages < BODY_FLOOR:
                    problems.append("the body has %d pages before the appendices, floor %d: too much was cut" % (body_pages, BODY_FLOOR))
        return {"case_id": case_id, "run_id": run_id, "target": which, "problems": problems, "sources": len(rows), "pdf_pages": pdf_pages, "body_pages": body_pages,
                "number_drift": drift, "claims_changed": changed, "where_unlocated": unlocated,
                "numbers_omitted": omitted, "sources_cut": cut, "version": SERVER_VERSION}

def build_server(root, agent):
    from mcp.server.mcpserver import MCPServer
    case = Case(root, agent)
    s = MCPServer("tax-case-" + agent, version=SERVER_VERSION,
                  instructions="Write path into cases/<case_id>/ for the %s agent; reads go through the host's Read / Glob / Grep." % agent)

    # ---- ledger (front)
    if agent == "front":
        @s.tool()
        def case_new(case_id: str) -> dict:
            """Create cases/<case_id>/ with its sub-folders, rounds.json (round 1) and the four round-1 note folders."""
            return case.case_new(case_id)

        @s.tool()
        def round_new(case_id: str) -> dict:
            """Open the next round (the status must be delivered, or a report checklist must say RETURN: front); creates the four notes/*/round-N/ folders."""
            return case.round_new(case_id)

        @s.tool()
        def round_revise(case_id: str) -> dict:
            """Bump the revision number of the current round after a review sent something back."""
            return case.round_revise(case_id)

        @s.tool()
        def round_set_run(case_id: str, run_id: str) -> dict:
            """Register the optimizer run of the current round; requires status intake_ok and products/<run_id>/version.json."""
            return case.round_set_run(case_id, run_id)

        @s.tool()
        def write_intake(case_id: str, name: str, content: str) -> dict:
            """Write facts / sources / answers / notes / constraints / handoff (JSON checked, previous version kept as .prev)."""
            return case.write_intake(case_id, name, content)

        @s.tool()
        def put_document(case_id: str, name: str, src_path: str = "", content_base64: str = "") -> dict:
            """Store a client document under intake/documents/ (copy from src_path or decode content_base64); name=prompt writes intake/prompt.md."""
            return case.put_document(case_id, name, src_path, content_base64)

        @s.tool()
        def dialogue_append(case_id: str, speaker: str, text: str) -> dict:
            """Append one utterance (client or front) verbatim to intake/dialogue.md with date, round and entry number."""
            return case.dialogue_append(case_id, speaker, text)

    if agent in ("front", "analysis"):
        @s.tool()
        def to_collect_append(case_id: str, law: str, jur: str, url: str, why: str) -> dict:
            """Append a collection request (a law the library lacks or has out of date) to intake/to_collect.md."""
            return case.to_collect_append(case_id, law, jur, url, why)

    if agent == "analysis":
        @s.tool()
        def write_report(case_id: str, run_id: str, name: str, content: str, mode: str = "replace") -> dict:
            """Write report/<run_id>/briefing.md (name=briefing) or briefing.sources.json (name=sources); run_id must be the current round's.
            mode=append adds a part to the draft, or adds and replaces rows of the sources table by id."""
            return case.write_report(case_id, run_id, name, content, mode)

        @s.tool()
        def write_section(case_id: str, run_id: str, section: str, content: str, sources: str = "") -> dict:
            """Write one part of a sectioned draft (section = head | 1 | 2 | 3 | 4 | 5 | 6 | 7 | A) with the sources of that part (a JSON list of
            {id, where, claim, kind, ref}). A part starts with its heading line; {{block:<name>}} on a line of its own inserts a program table from
            report/<run_id>/frame/frame.md together with its sources. Writing a part again replaces that part only; its sources are added or replaced by id."""
            return case.write_section(case_id, run_id, section, content, sources)

        @s.tool()
        def edit_section(case_id: str, run_id: str, edits: list[dict]) -> dict:
            """Change sentences of a sectioned draft: edits = [{old, new}], each old text must occur exactly once across the parts, all or none."""
            return case.edit_section(case_id, run_id, edits)

        @s.tool()
        def edit_report(case_id: str, run_id: str, edits: list[dict]) -> dict:
            """Change sentences of briefing.md: edits = [{old, new}], each old text must occur exactly once, all or none."""
            return case.edit_report(case_id, run_id, edits)

        @s.tool()
        def render_pdf(case_id: str, run_id: str) -> dict:
            """Typeset the client copy of briefing.md (program tables expanded in place of the {{block:...}} markers, the internal reference line removed) into report/<run_id>/briefing.pdf; refuses while report_check(target=draft, text_only=true) reports problems. Returns the page counts, the page of each section and of the flowchart, and how full each page is."""
            return case.render_pdf(case_id, run_id)

    if agent == "polish":
        @s.tool()
        def edit_polished(case_id: str, run_id: str, edits: list[dict]) -> dict:
            """Change sentences of briefing.polished.md: edits = [{old, new}], each old text must occur exactly once, all or none."""
            return case.edit_polished(case_id, run_id, edits)

        @s.tool()
        def write_polished(case_id: str, run_id: str, name: str, content: str, mode: str = "replace") -> dict:
            """Write report/<run_id>/briefing.polished.md (name=polished; mode=append adds the next part at the end), or the sources of the entries you kept (name=sources, a JSON list of {id, where}; claim, kind and ref are copied from the draft; mode=append adds or replaces rows)."""
            return case.write_polished(case_id, run_id, name, content, mode)

        @s.tool()
        def render_pdf(case_id: str, run_id: str) -> dict:
            """Typeset briefing.polished.md into report/<run_id>/briefing.pdf with the fixed template; returns the page counts, the page of each section and of the flowchart, and how full each page is."""
            return case.render_pdf(case_id, run_id)

    if agent == "review":
        @s.tool()
        def write_review(case_id: str, which: str, content: str, run_id: str = "") -> dict:
            """Write intake/review_intake.md (which=intake, RUNNABLE / REVISE), report/<run_id>/review.md (which=draft, DELIVERABLE / REVISE) or the legal-reasoning lane's review_legal.md (which=legal_draft, DELIVERABLE / REVISE). The last line is the verdict; a REVISE other than intake has RETURN: analysis or front on the line before it, and needs at least one Problem entry that states a problem. Wording-only fixes go in a ```replacements block: a JSON list of {old, new} with the exact draft sentence and its replacement; the program applies them and they do not need a REVISE."""
            return case.write_review(case_id, which, content, run_id)

    # ---- own notebooks and bug log (every identity)
    @s.tool()
    def notes_append(case_id: str, book: str, text: str) -> dict:
        """Append an entry to one of this agent's working-paper notebooks for the current round; the header is written for you."""
        return case.notes_append(case_id, book, text)

    @s.tool()
    def bug_append(case_id: str, layer: str, symptom: str, expected: str = "", repro: str = "", workaround: str = "", affects_result: bool = False, effect: str = "") -> dict:
        """Append a bug report to this agent's bugs file (layer: database / rule / optimization / tool / web / spec); duplicates get a recurrence line.
        affects_result = true only when the defect changes a figure or the ranking of THIS case, and then effect must say which figure changes from what to what: the run then stops until the bug is fixed and cleared. A modelling gap that leaves this case's figures as they are is affects_result = false."""
        return case.bug_append(case_id, layer, symptom, expected, repro, workaround, affects_result, effect)

    # ---- status and self-checks (every identity)
    @s.tool()
    def round_current(case_id: str) -> dict:
        """The current round's ledger entry plus the status derived from the files (intake / intake_ok / ran / drafted / reviewed / polished / delivered) and return_to, the open REVISE checklist if any."""
        return case.round_current(case_id)

    @s.tool()
    def review_status(case_id: str, which: str) -> dict:
        """Verdict, RETURN target and write time of review_intake.md (which=intake), the current run's review.md (which=draft) or review_final.md (which=final)."""
        return case.review_status(case_id, which)

    @s.tool()
    def intake_check(case_id: str) -> dict:
        """Read-only self-check of the intake package: optimizer accepts facts.json, sources cover facts, answers carry the client's words found in dialogue.md, status."""
        return case.intake_check(case_id)

    @s.tool()
    def report_check(case_id: str, run_id: str, target: str = "auto", text_only: bool = False, part: str = "") -> dict:
        """Read-only self-check of a briefing (target: draft = the report you write; polished = the old polish stage): internal reference line, parts 1-7, appendices A/B, a flow block, no system identifiers or optimizer vocabulary in the body, no spoken lead-ins, no sentence over 55 words, sources entries with where and resolvable refs, every figure covered by a source row, and (unless text_only) a current briefing.pdf whose body runs to 5-10 pages. part (head, 1-7, A, B): check only that part while you write part by part."""
        return case.report_check(case_id, run_id, target, text_only, part)

    return s, case


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=str(PROJECT / "cases"))
    ap.add_argument("--agent", required=True, choices=AGENTS)
    a = ap.parse_args()
    server, _ = build_server(a.root, a.agent)
    server.run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
