"""extract (信息收集.md P1–P4): documents -> facts for the fields a case needs, each with the quote it rests on.

Two passes, both driven by the field list the rules produce (fields.required_fields), never by a problem type:

    pass 1  locate   for every field, the passages of the documents that bear on it (or none)
    pass 2  read     one typed value per field from its passages, with the verbatim quote behind it

The model is a parameter: any callable prompt -> text (JSON). Everything around it is program: the field
specifications come from the compiled rules (predicate -> type, enum params -> allowed values) and from the
evidence column of 信息收集.md; replies are validated against them; a quote that is not found verbatim in the
document is not evidence, so the field stays missing (P4); units follow the rules (ratios in percent, periods in
months, amounts in the flow's currency). Nothing here decides tax; what comes out is Case facts plus evidence.
"""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from ..engine import RULES
from ..params import Params
from ..rules.model import ALL, And, Discretion, Leaf, Not, Or, eq, ge, gt, is_false, is_in, is_true, le, lt

DOC = Path(__file__).resolve().parents[2] / "信息收集.md"
BOOL, NUMBER, ENUM, DATE, TEXT = "bool", "number", "enum", "date", "text"


@dataclass(frozen=True)
class FieldSpec:
    key: str                              # "payee.residence_cert"
    kind: str                             # bool | number | enum | date | text
    rules: Tuple[str, ...]                # rule ids that read it
    hint: str = ""                        # evidence column of 信息收集.md for the field's group
    allowed: Tuple[str, ...] = ()         # enum values, from the param the predicate compares with


@dataclass
class Extraction:
    facts: Dict[Tuple[str, str], object] = field(default_factory=dict)       # (elem, field) -> value
    evidence: Dict[Tuple[str, str], Tuple[str, str]] = field(default_factory=dict)   # -> (doc id, quote)
    missing: List[str] = field(default_factory=list)                          # keys no passage supports
    rejected: List[Tuple[str, str]] = field(default_factory=list)             # (key, why)


# ---------------------------------------------------------------- field specifications, from the rules
def _leaves(c, out):
    if isinstance(c, Leaf):
        out.append(c)
    elif isinstance(c, (And, Or)):
        for x in c.xs:
            _leaves(x, out)
    elif isinstance(c, Not):
        _leaves(c.x, out)


def _hints():
    """Field -> the evidence column of its group in 信息收集.md §3–§4 (same parse as check_fields.doc_fields)."""
    text = DOC.read_text(encoding="utf-8")
    sec = text[text.index("## 3. CONDITIONAL"):text.index("## 5. 激活与收集")]
    hints = {}
    for row in sec.splitlines():
        cells = [c.strip() for c in row.split("|")]
        if len(cells) < 6 or not cells[1].startswith("`") or cells[1] == "`mount`":
            continue
        names = [re.sub(r"=.*$", "", n.strip()) for span in re.findall(r"`([^`]*)`", cells[4]) for n in span.split(",")]
        for n in names:
            if re.fullmatch(r"[a-z_][a-z0-9_]*", n):
                hints.setdefault(n, cells[5])
    return hints


def field_specs(rules=None, P=None) -> Dict[str, FieldSpec]:
    """One spec per field the rules read. The predicate fixes the type: is_true/is_false -> bool, is_in -> enum of
    the param's values, comparisons -> number; *_on fields are dates; anything no predicate touches is text."""
    rules, P = rules or RULES, P or Params()
    hints = _hints()
    kinds, allowed, readers = {}, {}, {}
    for r in rules:
        for key in r.reads:
            readers.setdefault(key, set()).add(r.id)
        leaves = []
        _leaves(r.cond, leaves)
        for lf in leaves:
            key = "%s.%s" % (lf.on, lf.field)
            if lf.pred in (is_true, is_false):
                kinds[key] = BOOL
            elif lf.pred is is_in:
                kinds[key] = ENUM
                if lf.param and lf.param in P.rows:
                    allowed[key] = tuple(str(P.rows[lf.param]["value"]).split(";"))
            elif lf.pred in (ge, gt, le, lt, eq):
                kinds[key] = NUMBER
    specs = {}
    for key, rids in readers.items():
        name = key.split(".", 1)[1]
        kind = kinds.get(key) or (DATE if name.endswith("_on") else TEXT)
        specs[key] = FieldSpec(key, kind, tuple(sorted(rids)), hints.get(name, ""), allowed.get(key, ()))
    return specs


# ---------------------------------------------------------------- the two passes
def _prompt_locate(specs: List[FieldSpec], docs: Dict[str, str]) -> str:
    lines = ["For each field below, list the passages of the documents that bear on it. Answer with JSON only:",
             '{"<field key>": [{"doc": "<doc id>", "quote": "<verbatim passage>"}], ...}. Quote verbatim; an empty list',
             "when the documents say nothing about the field.", "", "FIELDS"]
    for s in specs:
        lines.append("- %s (%s%s)%s" % (s.key, s.kind, " of " + "/".join(s.allowed) if s.allowed else "", "; evidence: " + s.hint if s.hint else ""))
    lines.append("")
    lines.append("DOCUMENTS")
    for did, text in docs.items():
        lines.append("### %s\n%s" % (did, text))
    return "\n".join(lines)


def _prompt_read(spec: FieldSpec, passages: List[dict]) -> str:
    unit = {BOOL: "true or false", NUMBER: "a number; ratios in percent, periods in whole months, amounts as stated",
            ENUM: "one of " + "/".join(spec.allowed), DATE: "an ISO date YYYY-MM-DD", TEXT: "a short string"}[spec.kind]
    lines = ["Read the value of one field from the passages. Answer with JSON only:",
             '{"value": <%s>, "doc": "<doc id>", "quote": "<the verbatim passage the value rests on>"}' % unit,
             'or {"value": null} if the passages do not settle it.', "", "FIELD: %s" % spec.key, "PASSAGES"]
    for p in passages:
        lines.append("- [%s] %s" % (p.get("doc", ""), p.get("quote", "")))
    return "\n".join(lines)


def _json(text: str):
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else None


def _coerce(spec: FieldSpec, v):
    """Typed value or (None, reason)."""
    if spec.kind == BOOL:
        if isinstance(v, bool):
            return v, None
        if isinstance(v, str) and v.strip().lower() in ("true", "false", "yes", "no"):
            return v.strip().lower() in ("true", "yes"), None
        return None, "not a boolean"
    if spec.kind == NUMBER:
        if isinstance(v, bool):
            return None, "boolean where a number was expected"
        if isinstance(v, (int, float)):
            return float(v), None
        if isinstance(v, str):
            m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*%?\s*", v)
            if m:
                return float(m.group(1)), None
        return None, "not a number"
    if spec.kind == ENUM:
        if isinstance(v, str) and (not spec.allowed or v in spec.allowed):
            return v, None
        return None, "not one of %s" % "/".join(spec.allowed)
    if spec.kind == DATE:
        if isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            from datetime import date
            y, m, d = map(int, v.split("-"))
            return date(y, m, d), None
        return None, "not an ISO date"
    return (v, None) if isinstance(v, str) else (None, "not text")


def _supported(quote, doc_id, docs):
    """P4: a quote is evidence only if it is found verbatim (whitespace-insensitive) in the named document."""
    if not quote or doc_id not in docs:
        return False
    norm = lambda s: re.sub(r"\s+", "", s)
    return norm(quote) in norm(docs[doc_id])


def extract(docs: Dict[str, str], keys: List[str], model: Callable[[str], str], specs=None) -> Extraction:
    """docs: document id -> text. keys: the (flow or entity) fields wanted, as "elem.field". Returns facts with evidence;
    whatever the documents do not settle stays missing, and the rules treat it as U(MISSING)."""
    specs = specs or field_specs()
    wanted = [specs[k] if k in specs else FieldSpec(k, TEXT, ()) for k in keys]
    out = Extraction()
    located = _json(model(_prompt_locate(wanted, docs))) or {}
    for s in wanted:
        passages = [p for p in (located.get(s.key) or []) if isinstance(p, dict) and _supported(p.get("quote"), p.get("doc"), docs)]
        if not passages:
            out.missing.append(s.key)
            continue
        reply = _json(model(_prompt_read(s, passages))) or {}
        if reply.get("value") is None:
            out.missing.append(s.key)
            continue
        if not _supported(reply.get("quote"), reply.get("doc"), docs):
            out.rejected.append((s.key, "quote not found in the document"))
            out.missing.append(s.key)
            continue
        value, why = _coerce(s, reply["value"])
        if why:
            out.rejected.append((s.key, why))
            out.missing.append(s.key)
            continue
        elem, name = s.key.split(".", 1)
        out.facts[(elem, name)] = value
        out.evidence[(elem, name)] = (reply["doc"], reply["quote"])
    return out


def apply(extraction: Extraction, attrs_of: Dict[str, dict]):
    """Merge extracted facts into attrs dicts keyed by elem ("payer" | "payee" | "flow"); stated values are kept."""
    for (elem, name), v in extraction.facts.items():
        attrs_of.setdefault(elem, {}).setdefault(name, v)
    return attrs_of
