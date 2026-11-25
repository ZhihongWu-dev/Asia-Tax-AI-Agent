"""Patterns over the words of report_words.json (2026-11-25): the programs read reports and checklists in any language the
table lists, English first. A language is added in the table, not in the code."""
import json
import re
from pathlib import Path

W = json.loads((Path(__file__).resolve().parent / "report_words.json").read_text(encoding="utf-8"))


def alt(words, escape=True):
    return "|".join(re.escape(w) if escape else w for w in words)


APPENDIX = "(?:%s)" % alt(W["appendix"])                      # "Appendix" in any listed language
DATE = "(?:%s)" % alt(W["date"])
COLON = "[%s]" % "".join(re.escape(c) for c in W["colons"])
LIST_MARK = "[%s]" % "".join(re.escape(c) for c in W["list_marks"])
NONE = "(?:%s)" % alt(W["none"], escape=False)
LABELS = "(?:%s)" % alt([w for ws in W["checklist"].values() for w in ws])
PROBLEM = "(?:%s)" % alt(W["checklist"]["problem"])
LINE_REF = re.compile("(?i)" + "|".join(W["line_ref"]))
LEAKS = [re.escape(w) for w in W["leaks"]]
SPOKEN = "(?im)^\\*\\*(%s)[^*]{0,12}\\*\\*" % alt(W["spoken"])
PARTS = W["parts"]


def line_numbers(text):
    """Line numbers a checklist refers to, in any listed language."""
    return {int(next(g for g in m.groups() if g)) for m in LINE_REF.finditer(text or "")}


def part_hits(heads, part):
    """Indexes of the headings that name one part of the report (any language), not an appendix."""
    out = []
    for i, h in enumerate(heads):
        low = h.lower()
        if re.match("^" + APPENDIX, h):
            continue
        if any(w in h or w in low for w in part["words"]) and not any(x in h or x in low for x in part.get("not", [])):
            out.append(i)
    return out
