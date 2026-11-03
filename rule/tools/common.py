"""Shared pieces of the rule-layer tools (rule/规则层规范（最小集）.md): table layouts, the vocabulary of effects,
csv access, the condition parser and the loader of the library tables that the rule layer reads.

Python 3.11, standard library only. Imported by build.py and eval.py; not run directly.
"""
import csv
import re
from pathlib import Path

csv.field_size_limit(10 ** 9)
ENC = "utf-8-sig"

# ---------------------------------------------------------------- tables (spec §2): authored columns only
TABLES = {
    "rule": ["rule_id", "slot_key", "condition", "effect", "overrides", "procedure", "cite_ids", "decision_ids",
             "effective_from", "effective_to", "note"],
    "variable": ["name", "kind", "type", "allowed_values", "inputs", "question", "meaning"],
    "predicate": ["key", "question", "factors_cite", "factor_vars", "favourable"],
    "decision": ["id", "statement", "cite_id", "quote"],
    "rule_test": ["test_id", "slot_key", "date", "facts", "answers", "expect", "source"],
}
GENERATED = {"rule": ["requires", "predicates"]}          # sqlite only

SUBJECTS = ("company", "individual", "all")              # same values as param.subject in the library
SLOTS = ("outbound_wht", "inbound", "final", "residence", "cfc", "anti_abuse", "penalty", "restructure")
VAR_KINDS = ("client_fact", "structure", "derived")
VAR_TYPES = ("bool", "number", "date", "text", "enum")
AUTHORITATIVE_DOC_TYPES = ("law", "regulation", "treaty")
NUMBER_UNITS = ("%", "days", "months", "years", "count")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}$")

# effect -> (slots it may appear in, whether it takes a parameter, direction)
# direction "unfav": applying the effect is unfavourable to the taxpayer; "fav": favourable (spec §2.2)
EFFECTS = {
    "resident": (("residence",), False, "unfav"),
    "rate": (("outbound_wht", "final", "restructure"), True, "unfav"),
    "surtax": (("outbound_wht", "final"), True, "unfav"),
    "cap": (("outbound_wht",), True, "fav"),
    "exempt": (("outbound_wht", "inbound", "final", "restructure"), False, "fav"),
    "taxable": (("inbound",), False, "unfav"),
    "share": (("inbound", "final"), True, "fav"),
    "exclude": (("inbound", "final"), True, "fav"),
    "credit": (("inbound", "restructure"), False, "fav"),
    "include": (("cfc",), False, "unfav"),
    "deny": (("anti_abuse",), False, "unfav"),
    "schedule": (("final", "restructure"), True, "unfav"),
    "stamp": (("restructure",), True, "unfav"),           # stamp duty on a share transfer, % of the consideration; stamp rules add up           # progressive schedule; the parameter is <base>_bracket_1_rate (spec §2.2)
    "interest": (("penalty",), True, "unfav"),         # late-payment interest / surcharge; period from the parameter name (spec §2.2)
    "interest_cap": (("penalty",), True, "unfav"),
    "fine": (("penalty",), True, "unfav"),             # fixed penalty, % of the tax
    "fine_min": (("penalty",), True, "unfav"),
    "fine_max": (("penalty",), True, "unfav"),
}
RATE_LIKE = {"rate": "rate", "schedule": "rate", "share": "share", "exclude": "exclude"}   # alternatives of one value (spec §4)
PENALTY_EFFECTS = ("interest", "interest_cap", "fine", "fine_min", "fine_max")
OWN_VALUE_EFFECTS = PENALTY_EFFECTS + ("stamp",)     # golden tests compare the rule's own parameter for these
INTEREST_PERIODS = (("_per_day", "day"), ("_per_month", "month"), ("_per_year", "year"), ("_initial", "once"), ("_once", "once"))
SCHEDULE_INPUTS = ("other_taxable_income", "amount_payee_ccy")


def interest_period(param_id):
    """day / month / year / once from the parameter name (spec §2.2); None when the name carries no period."""
    name = param_id.split(".")[2] if param_id.count(".") >= 2 else param_id
    for suffix, period in INTEREST_PERIODS:
        if name.endswith(suffix):
            return period
    return None


def schedule_prefix(param_id):
    """'jp.final.progressive_bracket_1_rate' -> 'jp.final.progressive'."""
    i = param_id.rfind("_bracket_")
    return param_id[:i] if i > 0 else None

WILDCARDS = ("cap", "exempt", "share", "exclude", "credit")   # `<effect>:*` in overrides


# ---------------------------------------------------------------- csv
def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding=ENC, newline="") as f:
        return list(csv.DictReader(f))


def read_header(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding=ENC, newline="") as f:
        return next(csv.reader(f), [])


def write_csv(path, fields, rows):
    with Path(path).open("w", encoding=ENC, newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def split_list(s):
    return [x.strip() for x in (s or "").split(";") if x.strip()]


def parse_slot_key(s):
    """'jur|subject|slot|flow' -> (jur, subject, slot, flow) or None when not four parts."""
    parts = (s or "").split("|")
    return tuple(parts) if len(parts) == 4 else None


def parse_effect(s):
    """'cap:cn-hk.outbound_wht.dividend_rate_reduced' -> ('cap', param_id); 'exempt' -> ('exempt', None)."""
    s = (s or "").strip()
    if ":" in s:
        name, param = s.split(":", 1)
        return name.strip(), param.strip()
    return s, None


def param_type(unit):
    """Type of a parameter value by its unit: bool, number (%, days, months, years, count, a currency) or text."""
    if unit == "bool":
        return "bool"
    if unit == "text":
        return "text"
    return "number"


def typed_param_value(row):
    t = param_type(row.get("unit", ""))
    v = (row.get("value") or "").strip()
    if t == "bool":
        return v.lower() in ("yes", "true", "1")
    if t == "number":
        try:
            return float(v)
        except ValueError:
            return None
    return v


# ---------------------------------------------------------------- condition (spec §3)
TOKEN = re.compile(r"""\s*(?:(?P<op>>=|<=|!=|=|<|>)|(?P<punct>[()\[\],])|(?P<param>\$[A-Za-z0-9_.\-]+)|'(?P<str>[^']*)'|"""
                   r"""(?P<num>\d+(?:\.\d+)?)|(?P<word>[A-Za-z_][A-Za-z0-9_.\-]*))""")
KEYWORDS = ("and", "or", "not", "in", "true", "pred", "listed")


class CondError(ValueError):
    pass


def tokenize(s):
    pos, out = 0, []
    s = s.rstrip()
    while pos < len(s):
        m = TOKEN.match(s, pos)
        if not m or m.end() == pos:
            raise CondError("cannot read at character %d: %r" % (pos + 1, s[pos:pos + 12]))
        pos = m.end()
        kind = m.lastgroup
        val = m.group(kind)
        if kind == "word" and val in KEYWORDS:
            kind = val
        out.append((kind, val))
    return out


def parse_condition(text):
    """Infix condition -> tree.
    Nodes: True | {"and": [..]} | {"or": [..]} | {"not": x} | {op: [a, b]} | {"in": [a, [c, ..]]} | {"pred": key}
           | {"listed": [prefix, {"var": name}]}
    Operands: {"var": name} | {"param": id} | int | float | str (quoted constant) | True (the constant true)."""
    toks = tokenize(text or "")
    if not toks:
        raise CondError("empty condition (write true for a rule without condition)")
    i = [0]

    def peek():
        return toks[i[0]][0] if i[0] < len(toks) else None

    def peek_val():
        return toks[i[0]][1] if i[0] < len(toks) else "end of text"

    def take(kind, val=None):
        if peek() != kind or (val is not None and toks[i[0]][1] != val):
            raise CondError("expected %s, found %r" % (val or kind, peek_val()))
        i[0] += 1
        return toks[i[0] - 1][1]

    def operand():
        k = peek()
        if k == "word":
            return {"var": take("word")}
        if k == "param":
            return {"param": take("param")[1:]}
        if k == "num":
            v = take("num")
            return float(v) if "." in v else int(v)
        if k == "str":
            return take("str")
        if k == "true":
            take("true")
            return True
        raise CondError("expected a variable, $param or constant, found %r" % peek_val())

    def constant():
        k = peek()
        if k == "num":
            v = take("num")
            return float(v) if "." in v else int(v)
        if k == "str":
            return take("str")
        raise CondError("expected a constant inside [ ], found %r" % peek_val())

    def primary():
        k = peek()
        if k == "punct" and toks[i[0]][1] == "(":
            take("punct", "(")
            e = disj()
            take("punct", ")")
            return e
        if k == "true":
            take("true")
            if peek() == "op":                       # `true = x` is not a condition
                raise CondError("the constant true may only stand on the right of a comparison or alone")
            return True
        if k == "pred":
            take("pred")
            take("punct", "(")
            key = take("word")
            take("punct", ")")
            return {"pred": key}
        if k == "listed":
            take("listed")
            take("punct", "(")
            prefix = take("word")
            take("punct", ",")
            var = take("word")
            take("punct", ")")
            return {"listed": [prefix, {"var": var}]}
        left = operand()
        if peek() == "op":
            op = take("op")
            return {op: [left, operand()]}
        if peek() == "in":
            take("in")
            take("punct", "[")
            vals = [constant()]
            while peek() == "punct" and toks[i[0]][1] == ",":
                take("punct", ",")
                vals.append(constant())
            take("punct", "]")
            return {"in": [left, vals]}
        raise CondError("a variable, parameter or constant must be compared (=, !=, <, <=, >, >=) or tested with in [...]")

    def neg():
        if peek() == "not":
            take("not")
            return {"not": neg()}
        return primary()

    def conj():
        parts = [neg()]
        while peek() == "and":
            take("and")
            parts.append(neg())
        return parts[0] if len(parts) == 1 else {"and": parts}

    def disj():
        parts = [conj()]
        while peek() == "or":
            take("or")
            parts.append(conj())
        return parts[0] if len(parts) == 1 else {"or": parts}

    tree = disj()
    if i[0] != len(toks):
        raise CondError("unexpected %r after the end of the condition" % toks[i[0]][1])
    return tree


def leaves(tree, key, out=None):
    """Names under {"var": ..} / {"param": ..} / {"pred": ..} in order of first appearance."""
    if out is None:
        out = []
    if isinstance(tree, dict):
        for k, v in tree.items():
            if k == key and isinstance(v, str):
                if v not in out:
                    out.append(v)
            elif k == "listed":
                leaves(v[1], key, out)
            elif isinstance(v, list):
                for x in v:
                    leaves(x, key, out)
            else:
                leaves(v, key, out)
    elif isinstance(tree, list):
        for x in tree:
            leaves(x, key, out)
    return out


def listed_prefixes(tree, out=None):
    if out is None:
        out = []
    if isinstance(tree, dict):
        for k, v in tree.items():
            if k == "listed":
                if v[0] not in out:
                    out.append(v[0])
            elif isinstance(v, list):
                for x in v:
                    listed_prefixes(x, out)
            else:
                listed_prefixes(v, out)
    elif isinstance(tree, list):
        for x in tree:
            listed_prefixes(x, out)
    return out


# ---------------------------------------------------------------- library (database/)
class Library:
    """The library tables the rule layer reads. `with_clauses=True` loads clause.csv (ids and texts)."""

    def __init__(self, db, with_clauses=False):
        self.db = Path(db)
        self.juris = read_csv(self.db / "jurisdiction.csv")
        self.codes = {j["code"] for j in self.juris}
        self.docs = {r["id"]: r for r in read_csv(self.db / "doc.csv")}
        self.params = {r["param_id"]: r for r in read_csv(self.db / "param.csv")}
        self.treaties = {}
        for r in read_csv(self.db / "treaty.csv"):
            a, _, b = r["pair"].partition("-")
            self.treaties[frozenset((a, b))] = r
        self.absences = read_csv(self.db / "decision.csv")
        self.clause_text = {}
        self._con = None
        if with_clauses:
            self.clause_text = {c["cite_id"]: c["text"] for c in read_csv(self.db / "clause.csv")}

    def clause(self, cite_id):
        """Text of one clause, or None. Uses database.sqlite when it exists (built by database/tools/build.py),
        otherwise the clause.csv loaded with with_clauses=True."""
        if cite_id in self.clause_text:
            return self.clause_text[cite_id]
        if self.clause_text:
            return None
        if self._con is None:
            import sqlite3
            path = self.db / "database.sqlite"
            if not path.exists():
                self.clause_text = {c["cite_id"]: c["text"] for c in read_csv(self.db / "clause.csv")}
                return self.clause_text.get(cite_id)
            self._con = sqlite3.connect(str(path))
        row = self._con.execute("SELECT text FROM clause WHERE cite_id = ?", (cite_id,)).fetchone()
        return row[0] if row else None

    def clause_label(self, cite_id):
        if self._con is not None:
            row = self._con.execute("SELECT label FROM clause WHERE cite_id = ?", (cite_id,)).fetchone()
            return row[0] if row else ""
        return ""

    def treaty(self, a, b):
        """Treaty row of a pair with a registered text, else None (a 'no treaty' row has no doc_id)."""
        r = self.treaties.get(frozenset((a, b)))
        return r if r and (r.get("doc_id") or "").strip() else None

    def param_effective(self, pid, date):
        p = self.params.get(pid)
        if not p:
            return False
        return in_window(date, p.get("effective_from"), p.get("effective_to"))


def in_window(date, start, end):
    if start and date < start:
        return False
    if end and date > end:
        return False
    return True
