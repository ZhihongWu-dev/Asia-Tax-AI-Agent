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
         "review": ("expect", "recalc", "checks")}
INTAKE_NAMES = ("facts", "sources", "answers", "notes", "constraints", "handoff")
INTAKE_FILES = {"facts": "facts.json", "sources": "sources.json", "answers": "answers.json", "notes": "notes.md",
                "constraints": "constraints.json", "handoff": "handoff.md"}
DIRTY_NAMES = ("facts", "sources", "answers", "notes", "constraints")   # everything stage 1 reviews; the handoff is not reviewed
VERDICTS = {"intake": ("RUNNABLE", "REVISE"), "draft": ("POLISHABLE", "REVISE"), "final": ("DELIVERABLE", "REVISE")}
RETURNS = {"draft": ("analysis", "front"), "final": ("polish", "analysis", "front")}   # who a REVISE checklist may send the case back to
PARTS = (("策略思路", "strategy"), ("现状", "current state"), ("备选方案", "alternatives"),
         ("最优方案", "optimal"), ("税负比较", "tax comparison"), ("条件与要求", "requirements"), ("执行", "implementation"))
LEAKS = (r"\[S\d+\]", r"\b[cx]\d+\.b\d+\b", r"\bcand_id\b", r"\bbranch_id\b", r"\brun_id\b", r"\bper_100\b", r"\bchanges_rank\b",
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
    return None


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


FACT_KEYS = ("date", "mode", "amount", "currency", "payer", "payee", "payment", "assume", "entities", "destinations", "valuation", "horizon_years",
             "as_of", "fx", "limits", "constraints", "case", "note", "instructed_on", "past_payments", "answers")


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
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(m.group(1), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return m.group(1)


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
            if not passed(review, "draft", newest(*draft)):
                return "drafted"
            if not pol.exists() or pol.stat().st_mtime < review.stat().st_mtime:
                return "reviewed"
            return "delivered" if passed(rd / "review_final.md", "final", newest(*report_files(rd))) else "polished"
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
        if st not in ("drafted", "polished"):
            return None
        rd = cd / "report" / cur["run_id"]
        if st == "drafted":
            which, p, since, default = "draft", rd / "review.md", newest(*draft_files(rd)), "analysis"
        else:
            which, p, since, default = "final", rd / "review_final.md", newest(*report_files(rd)), "polish"
        if p.exists() and p.stat().st_mtime >= since:
            text = p.read_text(encoding="utf-8")
            if verdict_of(text, which) == "REVISE":
                return {"which": which, "to": return_of(text) or default, "path": str(p)}
        return None

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
            return err("invalid", "which must be intake, draft or final")
        if which == "intake":
            p = cd / "intake" / "review_intake.md"
        else:
            run_id = self.current(ledger).get("run_id")
            if not run_id:
                return {"which": which, "verdict": "none", "detail": "no run in the current round", "version": SERVER_VERSION}
            p = cd / "report" / run_id / ("review.md" if which == "draft" else "review_final.md")
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
        return self.apply_edits(cd / "report" / run_id / "briefing.md", edits, case_id, run_id)

    def edit_polished(self, case_id, run_id, edits):
        if (e := self.need("polish")):
            return e
        cd, ledger, e = self.opened(case_id)
        if e:
            return e
        return self.apply_edits(cd / "report" / run_id / "briefing.polished.md", edits, case_id, run_id)

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
                if r["kind"] not in ("product", "tool", "cite", "url", "document"):
                    return err("invalid", "sources[%d].kind must be product | tool | cite | url | document" % i)
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
        self.write_with_prev(path, content)
        return {"case_id": case_id, "run_id": run_id, "written": str(path), "prev": path.with_name(path.name + ".prev").exists(),
                "version": SERVER_VERSION}

    def render_pdf(self, case_id, run_id):
        if (e := self.need("polish")):
            return e
        cd, ledger, e = self.opened(case_id)
        if e:
            return e
        rd = cd / "report" / run_id
        src = rd / "briefing.polished.md"
        if not src.exists():
            return err("not_found", "no briefing.polished.md to render; write the polished report first")
        text_problems = self.report_check(case_id, run_id, "polished", text_only=True).get("problems", [])
        if text_problems:                                      # a render takes a minute: settle the text first
            return err("conflict", "fix the text first, nothing was rendered: " + "; ".join(text_problems[:8]))
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
            return err("invalid", "which must be intake, draft or final")
        v = verdict_of(content, which)
        if v is None:
            return err("invalid", "last line must end with one of %s" % " / ".join(VERDICTS[which]), last_line=last_line(content))
        if which != "intake" and v == "REVISE" and return_of(content) not in RETURNS[which]:
            return err("invalid", "a REVISE checklist needs the line RETURN: <%s> just before the verdict" % " | ".join(RETURNS[which]))
        cur = self.current(ledger)
        if which == "intake":
            path = cd / "intake" / "review_intake.md"
        else:
            if not cur.get("run_id") or (run_id and run_id != cur["run_id"]):
                return err("conflict", "run_id %s is not the current round's run (%s)" % (run_id, cur.get("run_id")))
            rd = cd / "report" / cur["run_id"]
            subject = rd / ("briefing.md" if which == "draft" else "briefing.polished.md")
            if not subject.exists():
                return err("conflict", "there is no %s to review yet" % subject.name)
            path = rd / ("review.md" if which == "draft" else "review_final.md")
        self.write_with_prev(path, content)
        if which == "intake":
            cur["review_intake_written"] = now()
            cur["intake_dirty"] = False                       # the review now postdates every intake write
            self.save_ledger(cd, ledger)
        return {"case_id": case_id, "which": which, "verdict": v, "written": str(path), "status": self.status(cd, ledger),
                "version": SERVER_VERSION}

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

    def bug_append(self, case_id, layer, symptom, expected, repro, workaround, affects_result=False):
        cd, ledger, e = self.opened(case_id)
        if e:
            return e
        if not (layer and symptom):
            return err("invalid", "layer and symptom are required")
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
            body += "\n- affects_result: yes"
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
                    problems.append("answers[%s] has value %r (allowed: yes, no, unknown_asked, unknown_not_asked)" % (pred, val))
        st = self.status(cd, ledger)
        note = ("" if st == "intake_ok" else
                "status is still intake: intake_ok needs the stage-1 review to end with RUNNABLE after the last facts / answers / constraints write; an empty problems list is not that review")
        return {"case_id": case_id, "status": st, "intake_ok": st == "intake_ok", "problems": problems, "note": note, "version": SERVER_VERSION}

    def _lib(self):
        if self._db is None:
            sys.path.insert(0, str(PROJECT / "database" / "tools"))
            import mcp_server as dbm  # noqa: E402
            self._db = dbm.Library(PROJECT / "database")
        return self._db

    def report_check(self, case_id, run_id, target="auto", text_only=False):
        cd, ledger, e = self.opened(case_id)
        if e:
            return e
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
                p = (cd / ref) if not Path(ref).is_absolute() else Path(ref)
                if not p.exists() and not (self.root / ref).exists():
                    problems.append("source %s: product path not found: %s" % (r.get("id"), ref))
            elif kind == "cite":
                cite = ref.split()[0]
                if cite not in self._lib().by_cite:
                    problems.append("source %s: cite_id not in the library: %s" % (r.get("id"), cite))
        # polish may cut but not change: a number new to the report is a problem, a number left out is only listed for review
        drift, omitted, changed, cut, unlocated, pdf_pages, body_pages = [], [], [], [], [], None, None
        if which == "polished" and draft.exists():
            before, after = numbers_in(draft.read_text(encoding="utf-8")), numbers_in(text)
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
        def edit_report(case_id: str, run_id: str, edits: list[dict]) -> dict:
            """Change sentences of briefing.md: edits = [{old, new}], each old text must occur exactly once, all or none."""
            return case.edit_report(case_id, run_id, edits)

    if agent == "polish":
        @s.tool()
        def edit_polished(case_id: str, run_id: str, edits: list[dict]) -> dict:
            """Change sentences of briefing.polished.md: edits = [{old, new}], each old text must occur exactly once, all or none."""
            return case.edit_polished(case_id, run_id, edits)

        @s.tool()
        def write_polished(case_id: str, run_id: str, name: str, content: str, mode: str = "replace") -> dict:
            """Write report/<run_id>/briefing.polished.md (name=polished), or the sources of the entries you kept (name=sources, a JSON list of {id, where}; claim, kind and ref are copied from the draft)."""
            return case.write_polished(case_id, run_id, name, content, mode)

        @s.tool()
        def render_pdf(case_id: str, run_id: str) -> dict:
            """Typeset briefing.polished.md into report/<run_id>/briefing.pdf with the fixed template; returns the page counts, the page of each section and of the flowchart, and how full each page is."""
            return case.render_pdf(case_id, run_id)

    if agent == "review":
        @s.tool()
        def write_review(case_id: str, which: str, content: str, run_id: str = "") -> dict:
            """Write intake/review_intake.md (which=intake, RUNNABLE / REVISE), report/<run_id>/review.md (which=draft, POLISHABLE / REVISE) or report/<run_id>/review_final.md (which=final, DELIVERABLE / REVISE). The last line is the verdict; a REVISE in draft or final has RETURN: analysis, polish or front on the line before it."""
            return case.write_review(case_id, which, content, run_id)

    # ---- own notebooks and bug log (every identity)
    @s.tool()
    def notes_append(case_id: str, book: str, text: str) -> dict:
        """Append an entry to one of this agent's working-paper notebooks for the current round; the header is written for you."""
        return case.notes_append(case_id, book, text)

    @s.tool()
    def bug_append(case_id: str, layer: str, symptom: str, expected: str = "", repro: str = "", workaround: str = "", affects_result: bool = False) -> dict:
        """Append a bug report to this agent's bugs file (layer: database / rule / optimization / tool / web / spec); duplicates get a recurrence line.
        affects_result = true when the defect can change a figure or the ranking in the report: the run then stops until the bug is fixed and cleared."""
        return case.bug_append(case_id, layer, symptom, expected, repro, workaround, affects_result)

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
    def report_check(case_id: str, run_id: str, target: str = "auto", text_only: bool = False) -> dict:
        """Read-only self-check of a briefing (target: auto / draft / polished; auto = polished when it exists): internal reference line, parts 1-7, appendices A/B, no system identifiers, sources entries with where and resolvable refs; for the polished report also new numbers, changed claims, unlocated where fragments, spoken lead-ins and the PDF page limit, and it lists what was cut for review."""
        return case.report_check(case_id, run_id, target, text_only)

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
