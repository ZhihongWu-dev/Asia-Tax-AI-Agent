"""The template side of the client briefing (2026-11-12): what the program fixes and the analysis agent is not told about.

- Citation markers {{cite:<cite_id>|<label>}}: the client copy shows the label; the cite ids feed Appendix B and the provenance.
- Word limits per part (report_limits.json): counted on the prose only (citations, quotations, tables, fenced and program blocks
  aside), stated to the writer in the frame (2026-11-12, the one exception), reported when a part is over, and logged for
  calibration in the case's log folder, which agents cannot read.
- The client copy: the heading (title and date from the facts), the flowchart (frame/blocks/flow.json), the program tables at
  fixed places (Part 5, Appendix A), Appendix B from the citations, no internal reference line.
Program only; the agents never read this file; the frame states the limits it computes."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import sections
import words as W

HERE = Path(__file__).resolve().parent
LIMITS = HERE / "report_limits.json"
CITE = re.compile(r"\{\{cite:([^|{}]+)\|([^{}]+)\}\}")
BLOCK = re.compile(r"\{\{block:([a-z_]+)\}\}")
QUOTE = re.compile(r"“[^”]*”|\"[^\"\n]*\"|「[^」]*」")
LABEL_WORDS = 15                                                 # a citation's label longer than this is prose, not a reference
OVERRUN = re.compile(r": (\d+) words, limit (\d+)\. Cut it\.$")  # an overrun message of overruns()


def plain(text):
    """The text as the client reads it: every citation marker replaced by its label."""
    return CITE.sub(lambda m: m.group(2).strip(), text or "")


def cites(text):
    """[(cite_id, label)] in the order they appear."""
    return [(m.group(1).strip(), m.group(2).strip()) for m in CITE.finditer(text or "")]


def locate(raw, needle):
    """(start, end) of needle in raw when it occurs exactly once there; failing that, when it occurs exactly once in the text
    as the client reads it (citation markers as their labels), mapped back so that a marker it touches is covered whole.
    None otherwise. A reviewer may quote a sentence either way."""
    if not needle:
        return None
    if raw.count(needle) == 1:
        i = raw.find(needle)
        return i, i + len(needle)
    chars, starts, ends, pos = [], [], [], 0
    for m in CITE.finditer(raw):
        for j in range(pos, m.start()):
            chars.append(raw[j]); starts.append(j); ends.append(j + 1)
        for ch in m.group(2).strip():
            chars.append(ch); starts.append(m.start()); ends.append(m.end())
        pos = m.end()
    for j in range(pos, len(raw)):
        chars.append(raw[j]); starts.append(j); ends.append(j + 1)
    flat = "".join(chars)
    if flat == raw or flat.count(needle) != 1:
        return None
    i = flat.find(needle)
    return starts[i], ends[i + len(needle) - 1]


def counted_words(text):
    """Words of the prose: citation markers, quoted passages, tables, fenced blocks, program markers and headings aside.
    A CJK character counts as half a word."""
    t = re.sub(r"```.*?```", " ", text or "", flags=re.S)
    t = BLOCK.sub(" ", CITE.sub(" ", re.sub(r"\{\{fig:[^{}]+\}\}", " ", t)))
    t = QUOTE.sub(" ", t)
    prose = " ".join(l for l in t.splitlines() if not l.lstrip().startswith(("|", "#")))
    latin = len(re.findall(r"[A-Za-z0-9][\w'’.,%/\-]*", prose))
    cjk = len(re.findall(r"[一-鿿]", prose))
    return latin + cjk // 2


def limits():
    data = json.loads(LIMITS.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def render_slack(problem):
    """True for an overrun message within the share the reviewers' replacements may add at render (2026-11-25, the owner's
    decision: their corrections are typeset, a part grown beyond the slack goes back to the author)."""
    m = OVERRUN.search(problem)
    slack = json.loads(LIMITS.read_text(encoding="utf-8")).get("_render_slack", 0)
    return bool(m) and int(m.group(1)) <= int(m.group(2)) * (1 + slack)


def counts_for(frame_dir):
    """The counts the per-item allowances use: structures named in the frame, rows of the assumptions table."""
    fd = Path(frame_dir)
    names = json.loads((fd / "names.json").read_text(encoding="utf-8")) if (fd / "names.json").exists() else {}
    def rows_in(name):
        p = fd / "blocks" / ("%s.md" % name)
        table = p.read_text(encoding="utf-8") if p.exists() else ""
        return [l for l in table.splitlines() if l.startswith("|") and not re.match(r"^\|[\s\-:|]+\|$", l)]
    skeleton = json.loads((fd / "skeleton.json").read_text(encoding="utf-8")) if (fd / "skeleton.json").exists() else {}
    return {"structures": len(names), "assumptions": max(0, len(rows_in("assumptions_table")) - 1),
            "choices": max(0, len(rows_in("choices_table")) - 2), "skeleton": len(skeleton.get("steps") or [])}


def limit_of(part, frame_dir):
    rule = limits().get(str(part))
    if not rule:
        return None
    return int(rule["base"] + (rule.get("each", 0) * counts_for(frame_dir).get(rule.get("per", ""), 0) if rule.get("per") else 0))


def overruns(parts, frame_dir, log=None):
    """parts: {part: text}. The parts over their limit as "Part 2: 620 words, limit 500. Cut it."; every count is logged."""
    out, rows = [], []
    for part, text in parts.items():
        lim = limit_of(part, frame_dir)
        n = counted_words(text)
        rows.append({"part": part, "words": n, "limit": lim})
        if lim is not None and n > lim:
            name = "Part %s" % part if part.isdigit() else "Appendix %s" % part if part in ("A", "B") else "The opening before Part 1"
            out.append("%s: %d words, limit %d. Cut it." % (name, n, lim))
    if log:
        log = Path(log)
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "parts": rows}) + "\n")
    return out


def bad_cites(text, known):
    """Markers whose cite id is not in the library, or whose label reads as prose."""
    out = []
    for cid, label in cites(text):
        if cid not in known:
            out.append("citation %s is not a provision of the library" % cid)
        elif len(label.split()) > LABEL_WORDS:
            out.append("citation %s: the label is a sentence, give the provision's name only" % cid)
    return out


# ------------------------------------------------------------ the client copy
def title_of(facts):
    """'Dividend of RMB 14,000,000 from Mainland China to Hong Kong' from the facts of the case."""
    amount = facts.get("amount")
    money = "%s %s" % (facts.get("currency", ""), sections.money(amount)) if amount is not None else "a dividend"
    payer = sections.JUR.get(str((facts.get("payer") or {}).get("jur", "")), "")
    payee = sections.JUR.get(str((facts.get("payee") or {}).get("jur", "")), "")
    route = " from %s to %s" % (payer, payee) if payer and payee else ""
    return ("Dividend of %s%s" % (money, route)).strip()


def date_of(facts):
    day = str(facts.get("instructed_on") or "")
    try:
        return datetime.strptime(day, "%Y-%m-%d").strftime("%d %B %Y").lstrip("0")
    except ValueError:
        return day


def split_parts(text):
    """(head, [(key, heading line, body lines)]) on the '## ' headings: key 1-7, A, B or None."""
    head, parts, cur = [], [], None
    for line in text.splitlines():
        m = re.match(r"^##\s+(.+)$", line)
        if m:
            h = m.group(1).strip()
            ap = re.match(r"^" + W.APPENDIX + r"\s*([AB])\b", h)
            num = re.match(r"^(?:Part\s+)?([1-7])(?:" + W.LIST_MARK + "|" + W.COLON + r"|\s)", h)
            cur = [ap.group(1) if ap else num.group(1) if num else None, line, []]
            parts.append(cur)
        elif cur is None:
            head.append(line)
        else:
            cur[2].append(line)
    return head, parts


def client_text(draft, rd, case_id, run_id, facts, rows):
    """The client copy of a draft: template heading, flowchart, tables, Appendix B, plain citations, no internal ids."""
    rd = Path(rd)
    fb = rd / "frame" / "blocks"
    blocks = {p.stem: p.read_text(encoding="utf-8").strip() for p in fb.glob("*.md")} if fb.exists() else {}
    used = set(BLOCK.findall(draft))
    text = BLOCK.sub(lambda m: blocks.get(m.group(1), ""), draft)          # a draft that still places a marker keeps its place
    text = re.sub(r"```flow\s*\n.*?```\s*\n?", "", text, flags=re.S)      # the flowchart is the program's
    head, parts = split_parts(text)
    head = [l for l in head if not l.startswith("# ") and not re.match(r"^\s*\**\s*" + W.DATE + r"\s*" + W.COLON, l)]
    out = ["# %s" % title_of(facts), "", "**Date:** %s" % date_of(facts), ""] + head
    flow = fb / "flow.json"
    for key, line, body in parts:
        if key == "B":
            continue                                                        # Appendix B is built below
        out.append(line)
        if key == "5" and "tax_table" in blocks and "tax_table" not in used:
            out += ["", blocks["tax_table"], ""]
        if key == "5" and "robustness_table" in blocks and "robustness_table" not in used:
            out += ["", blocks["robustness_table"], ""]
        if key == "A" and "assumptions_table" in blocks and "assumptions_table" not in used:
            out += ["", blocks["assumptions_table"], ""]
        out += body
        if key == "1" and flow.exists():
            out += ["", "```flow", flow.read_text(encoding="utf-8").strip(), "```", ""]
        if key == "1" and "choices_table" in blocks and "choices_table" not in used:
            out += ["", blocks["choices_table"], ""]
        if key == "A" and "gaps_list" in blocks and "gaps_list" not in used:
            out += ["", blocks["gaps_list"], ""]
    cite_rows = [{"kind": "cite", "ref": cid} for cid, _ in cites(draft)]
    out += ["", sections.appendix_b(list(rows) + cite_rows)]
    kept = [l for l in plain("\n".join(out)).splitlines() if case_id not in l and run_id not in l]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip() + "\n"
