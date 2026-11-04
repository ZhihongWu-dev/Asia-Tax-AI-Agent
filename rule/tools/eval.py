#!/usr/bin/env python
"""Reference evaluator of the rule layer (rule/规则层规范（最小集）.md §4): three-valued conditions, composition of
the effects of one cell, the interval [floor, ceiling] with its pending groups, and the fixed cross-cell order of a
dividend flow. Any other evaluator must pass the same rule_test.csv.

Python 3.11, standard library only.

  python rule/tools/eval.py --slot 'cn|company|outbound_wht|hk' --date 2026-01-01 --facts 'holding_pct=30' --answers 'bo=yes'
  python rule/tools/eval.py --flow cn hk company --date 2026-01-01 --facts 'payer.incorporated_in=cn;payee.incorporated_in=hk;holding_pct=30'
  options: --mode record|plan (default record)  --root rule/  --db database/  --json
"""
import argparse
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (EFFECTS, OWN_VALUE_EFFECTS, RATE_LIKE, SCHEDULE_INPUTS, Library, in_window, interest_period, leaves,  # noqa: E402
                    listed_prefixes, parse_condition, parse_effect, schedule_prefix,
                    parse_slot_key, read_csv, split_list, typed_param_value)

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT.parent / "database"
SIDES = ("floor", "ceiling")


class Unknown:
    """A derived value that another cell could not settle; carries the needs of that cell."""

    def __init__(self, needs):
        self.needs = frozenset(needs)


class Defect(Exception):
    pass


# ---------------------------------------------------------------- rules
class RuleSet:
    def __init__(self, root=ROOT, db=DB, lib=None):
        self.root = Path(root)
        self.lib = lib or Library(db)
        self.variables = {v["name"]: v for v in read_csv(self.root / "variable.csv")}
        self.predicates = {p["key"]: p for p in read_csv(self.root / "predicate.csv")}
        self.rules = []
        self.by_cell = {}
        for r in read_csv(self.root / "rule.csv"):
            parts = parse_slot_key(r["slot_key"])
            if not parts:
                continue
            try:
                tree = parse_condition(r["condition"])
            except ValueError:
                continue                                  # build.py reports it; the evaluator skips it
            eff, param = parse_effect(r["effect"])
            rule = dict(r)
            rule.update(id=r["rule_id"], jur=parts[0], subject=parts[1], slot=parts[2], flow=parts[3], tree=tree,
                        eff=eff, param=param, conditioned=tree is not True,
                        params=[p for p in ([param] if param else []) + leaves(tree, "param")],
                        overrides_list=split_list(r.get("overrides")), cites=split_list(r.get("cite_ids")),
                        decisions=split_list(r.get("decision_ids")))
            self.rules.append(rule)
            self.by_cell.setdefault((parts[0], parts[2]), []).append(rule)

    def valid(self, rule, date):
        if not in_window(date, rule.get("effective_from"), rule.get("effective_to")):
            return False
        return all(self.lib.param_effective(p, date) for p in rule["params"])

    def candidates(self, jur, subject, slot, flow, date):
        out = []
        for r in self.by_cell.get((jur, slot), []):
            if r["subject"] not in (subject, "all") and subject != "all":
                continue
            if r["flow"] not in (flow, "*"):
                continue
            if self.valid(r, date):
                out.append(r)
        return out

    def pvalue(self, pid):
        return typed_param_value(self.lib.params[pid])

    def schedule(self, pid):
        """Brackets of a progressive schedule named by its first rate parameter: [(upper or None, rate %), ...] in order
        (database convention <base>_bracket_<n>_rate / _upper, spec §2.2)."""
        prefix = schedule_prefix(pid)
        out = []
        n = 1
        while ("%s_bracket_%d_rate" % (prefix, n)) in self.lib.params:
            upper = self.lib.params.get("%s_bracket_%d_upper" % (prefix, n))
            out.append((typed_param_value(upper) if upper else None, self.pvalue("%s_bracket_%d_rate" % (prefix, n))))
            n += 1
        return out

    def typed(self, name, value):
        """A fact as given (string or typed) -> value of the variable's type."""
        if isinstance(value, Unknown) or value is None:
            return value
        v = self.variables.get(name)
        t = v["type"] if v else "text"
        if isinstance(value, bool):
            return value
        if t == "bool":
            return str(value).strip().lower() in ("true", "yes", "1")
        if t == "number":
            return float(value)
        return str(value).strip()

    def typed_facts(self, facts):
        return {k: self.typed(k, v) for k, v in (facts or {}).items() if v is not None and v != ""}


# ---------------------------------------------------------------- three-valued condition
def tv_and(parts):
    needs = set()
    for s, n in parts:
        if s == "F":
            return "F", frozenset()
        needs |= n
    return ("U", frozenset(needs)) if any(s == "U" for s, _ in parts) else ("T", frozenset())


def tv_or(parts):
    needs = set()
    for s, n in parts:
        if s == "T":
            return "T", frozenset()
        needs |= n
    return ("U", frozenset(needs)) if any(s == "U" for s, _ in parts) else ("F", frozenset())


def tv_not(part):
    s, n = part
    return ({"T": "F", "F": "T"}.get(s, "U"), n)


class Context:
    def __init__(self, rs, date, facts, answers, mode, jur=None):
        self.rs, self.date, self.mode, self.jur = rs, date, mode, jur
        self.facts = rs.typed_facts(facts)
        self.answers = {k: (v or "").strip().lower() for k, v in (answers or {}).items()}

    def var(self, name):
        """-> ("V", value) or ("U", needs)."""
        v = self.facts.get(name)
        if isinstance(v, Unknown):
            return "U", v.needs
        if v is not None:
            return "V", v
        row = self.rs.variables.get(name)
        kind = row["kind"] if row else "client_fact"
        if kind == "structure":
            if self.mode == "plan":
                return "U", frozenset({("PLAN", name)})
            if row and row["type"] == "bool":
                return "V", False                          # not in the described structure: not the case
            return "U", frozenset({("MISSING", name)})
        if kind == "derived":
            missing = [i for i in split_list(row.get("inputs")) if self.facts.get(i) in (None, "")] if row else []
            return "U", frozenset(("MISSING", i) for i in missing) if missing else frozenset({("MISSING", name)})
        return "U", frozenset({("MISSING", name)})

    def operand(self, x):
        if isinstance(x, dict):
            if "var" in x:
                return self.var(x["var"])
            if "param" in x:
                return "V", self.rs.pvalue(x["param"])
        return "V", x

    def compare(self, op, a, b):
        sa, va = self.operand(a)
        sb, vb = self.operand(b)
        if sa == "U" or sb == "U":
            return "U", (va if sa == "U" else frozenset()) | (vb if sb == "U" else frozenset())
        if isinstance(va, bool) or isinstance(vb, bool):
            va, vb = bool(va), bool(vb)
        elif isinstance(va, (int, float)) or isinstance(vb, (int, float)):
            try:
                va, vb = float(va), float(vb)
            except (TypeError, ValueError):
                raise Defect("comparison of %r with %r" % (va, vb))
        ok = {"=": va == vb, "!=": va != vb, "<": va < vb, "<=": va <= vb, ">": va > vb, ">=": va >= vb}[op]
        return ("T" if ok else "F"), frozenset()

    def eval(self, tree):
        if tree is True:
            return "T", frozenset()
        (k, v), = tree.items()
        if k == "and":
            return tv_and([self.eval(x) for x in v])
        if k == "or":
            return tv_or([self.eval(x) for x in v])
        if k == "not":
            return tv_not(self.eval(v))
        if k == "pred":
            a = self.answers.get("%s@%s" % (v, self.jur)) if self.jur else None      # an answer for this authority first
            a = a or self.answers.get(v)
            if a == "yes":
                return "T", frozenset()
            if a == "no":
                return "F", frozenset()
            return "U", frozenset({("DISCRETION", v)})
        if k == "listed":
            prefix, var = v
            s, val = self.var(var["var"])
            if s == "U":
                return "U", val
            pid = "%s_%s" % (prefix, str(val).strip().lower())
            p = self.rs.lib.params.get(pid)
            hit = bool(p) and self.rs.lib.param_effective(pid, self.date) and typed_param_value(p) is True
            return ("T" if hit else "F"), frozenset()
        if k == "in":
            left, consts = v
            s, val = self.operand(left)
            if s == "U":
                return "U", val
            hit = any((val == c) or (isinstance(c, (int, float)) and _num(val) == float(c)) for c in consts)
            return ("T" if hit else "F"), frozenset()
        return self.compare(k, v[0], v[1])


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- composition of one cell (spec §4)
LOWER_TAX_IS_LOWER_VALUE = {"rate": True, "share": True, "exclude": False}


def pick_single(rs, rules, what, side, certain, val=None):
    """Several rules with the same value in one cell (rate-like: rate / schedule, share, exclude). A conditioned rule
    whose condition is T beats `true`; two conditioned rules both T = Defect (the rules are wrong). Conditioned rules
    taken while their condition is still U are alternatives, not a clash, and the unconditioned rule is one of the
    alternatives too (they may all turn out F): the floor keeps the alternative with the lowest tax, the ceiling the
    highest. `val(rule)` gives a rule's value on this side (a schedule's value depends on the side and the facts)."""
    val = val or (lambda r: rs.pvalue(r["param"]))
    if not rules:
        return None
    cond = [r for r in rules if r["conditioned"]]
    uncond = [r for r in rules if not r["conditioned"]]
    if len(uncond) > 1:
        raise Defect("two unconditioned %s rules in one cell: %s" % (what, ", ".join(r["id"] for r in uncond)))
    sure = [r for r in cond if r["id"] in certain]
    if len(sure) > 1:
        raise Defect("two conditioned %s rules apply at once: %s" % (what, ", ".join(r["id"] for r in sure)))
    if len(sure) == 1:
        return sure[0]
    if not cond:
        return uncond[0]
    # conditioned rules still U: alternatives. Without an unconditioned rule, "no rule applies" is an alternative too:
    # for rate its value is unknown (floor None), for share / exclude it is full inclusion (the highest tax: ceiling).
    lowest_tax = LOWER_TAX_IS_LOWER_VALUE[what] == (side == "floor")      # True: pick the lowest value
    if not uncond and ((what == "rate" and side == "floor") or (what != "rate" and side == "ceiling")):
        return None
    return (min if lowest_tax else max)(rules, key=val)


def compose(rs, slot, rules, side="ceiling", certain=None, val=None):
    """The value of one cell from the rules taken on one side (spec §4). `certain` = ids whose condition is T;
    `val(rule)` = a rule's value on this side (default: its parameter)."""
    certain = certain if certain is not None else {r["id"] for r in rules}
    pv = val or (lambda r: rs.pvalue(r["param"]))
    eff = {}
    for r in rules:
        eff.setdefault(RATE_LIKE.get(r["eff"], r["eff"]), []).append(r)
    res = {"value": None, "rules": sorted(r["id"] for r in rules)}
    picked = []                                               # rules that determined the value on this side
    if slot == "penalty":
        interest = [{"param": r["param"], "pct": pv(r), "period": interest_period(r["param"])} for r in eff.get("interest", [])]
        caps = [pv(r) for r in eff.get("interest_cap", [])]
        fines = {k: list(eff.get(k, [])) for k in ("fine", "fine_min", "fine_max")}
        if any(r["conditioned"] and r["id"] in certain for k in fines for r in fines[k]):
            fines = {k: [r for r in v if r["conditioned"]] for k, v in fines.items()}   # a conditioned fine that holds replaces the ordinary one
        fine = [pv(r) for r in fines["fine"]]
        fmin = [pv(r) for r in fines["fine_min"]] + fine
        fmax = [pv(r) for r in fines["fine_max"]] + fine
        res["value"] = {"interest": sorted(interest, key=lambda x: x["param"]), "interest_cap": min(caps) if caps else None,
                        "fine_min": _r(min(fmin)) if fmin else (0.0 if fmax else None), "fine_max": _r(max(fmax)) if fmax else None}
        return res
    if slot == "cfc":
        res["value"] = bool(eff.get("include"))
        res["rate"], res["credit"], res["credit_underlying"] = None, False, False
        if res["value"]:                                      # inclusion: the rate and credit of the shareholder's tax on it
            chosen = pick_single(rs, eff.get("rate", []), "rate", side, certain, pv)
            rate = pv(chosen) if chosen else None
            picked = list(eff["include"]) + ([chosen] if chosen else [])
            for s in eff.get("surtax", []):
                if rate is not None:
                    rate = rate * (1 + pv(s) / 100)
                    picked.append(s)
            res["rate"], res["credit"] = _r(rate), bool(eff.get("credit") or eff.get("credit_underlying"))
            res["credit_underlying"] = bool(eff.get("credit_underlying"))   # the credit reaches the taxes of lower tiers too
            picked += eff.get("credit", []) + eff.get("credit_underlying", [])
        res["rules"] = sorted({r["id"] for r in picked})
        return res
    if slot in ("outbound_wht", "final", "restructure", "exit"):
        chosen = pick_single(rs, eff.get("rate", []), "rate", side, certain, pv)
        rate = pv(chosen) if chosen else None
        picked += [chosen] if chosen else []
        for s in eff.get("surtax", []):
            if rate is not None:
                rate = rate * (1 + pv(s) / 100)
                picked.append(s)
        if slot in ("outbound_wht", "restructure", "exit"):
            caps = [pv(c) for c in eff.get("cap", [])]
            if caps and rate is not None:
                rate = min([rate] + caps)
                picked += eff.get("cap", [])
            if eff.get("exempt"):
                rate = 0.0
                picked += eff.get("exempt", [])
            res["value"] = _r(rate)
            if slot == "restructure":
                res["stamp"] = _r(sum(pv(r) for r in eff.get("stamp", []))) if eff.get("stamp") else None
                picked += eff.get("stamp", [])
                res["credit"] = bool(eff.get("credit"))     # the home jurisdiction credits the source transfer tax
                picked += eff.get("credit", [])
        else:
            incl, more = included(rs, eff, side, certain, pv)
            picked += more
            res["included"] = _r(incl)
            res["value"] = None if rate is None else _r(rate * incl / 100)
        res["rules"] = sorted({r["id"] for r in picked})
    elif slot == "inbound":
        incl, more = included(rs, eff, side, certain, pv) if eff.get("taxable") else (0.0, [])
        res["value"] = _r(incl)
        res["credit"] = bool(eff.get("credit"))
        res["credit_underlying"] = bool(eff.get("credit_underlying"))
        res["rules"] = sorted({r["id"] for r in eff.get("taxable", []) + more + eff.get("credit", []) + eff.get("credit_underlying", [])})
    elif slot == "residence":
        res["value"] = bool(eff.get("resident"))
    elif slot == "anti_abuse":
        res["value"] = bool(eff.get("deny"))
        res["overrides"] = sorted({o for r in eff.get("deny", []) for o in r["overrides_list"]})
    return res


def included(rs, eff, side, certain, pv):
    """-> (included %, rules that determined it)."""
    incl, picked = 100.0, []
    s = pick_single(rs, eff.get("share", []), "share", side, certain, pv)
    if s:
        incl *= pv(s) / 100
        picked.append(s)
    x = pick_single(rs, eff.get("exclude", []), "exclude", side, certain, pv)
    if x:
        incl *= (100 - pv(x)) / 100
        picked.append(x)
    if eff.get("exempt"):
        incl = 0.0
        picked += eff.get("exempt", [])
    return incl, picked


def _r(x):
    return None if x is None else round(x + 0.0, 6)


def schedule_tax(brackets, x):
    """Tax on x under a marginal schedule [(upper or None, rate %), ...]."""
    tax, lower = 0.0, 0.0
    for upper, rate in brackets:
        top = x if upper is None else min(x, upper)
        if top > lower:
            tax += (top - lower) * rate / 100
        if upper is None or x <= upper:
            break
        lower = upper
    return tax


def schedule_value(rs, rule, facts, side):
    """-> (rate %, missing inputs). The effective rate of the dividend on top of the recipient's other taxable income,
    both in the recipient jurisdiction's currency (variables other_taxable_income, amount_payee_ccy); without them the
    floor is the lowest bracket rate and the ceiling the highest (spec §4)."""
    brackets = rs.schedule(rule["param"])
    base, amt = facts.get("other_taxable_income"), facts.get("amount_payee_ccy")
    missing = [k for k, v in (("other_taxable_income", base), ("amount_payee_ccy", amt)) if not isinstance(v, (int, float)) or isinstance(v, bool)]
    if missing or not brackets:
        rates = [r for _, r in brackets] or [None]
        return (min(rates) if side == "floor" else max(rates)), missing or ["schedule"]
    if amt <= 0:
        rate = next((r for u, r in brackets if u is None or base < u), brackets[-1][1])
        return rate, []
    return 100 * (schedule_tax(brackets, base + amt) - schedule_tax(brackets, base)) / amt, []


def outcome(res):
    """What counts as 'the result' when deciding whether a pending rule can still change it."""
    return tuple(sorted((k, json.dumps(v)) for k, v in res.items() if k != "rules"))


# ---------------------------------------------------------------- one cell
def direction(rs, rule, cands):
    """fav / unfav / both of a rule's effect (spec §2.2, §4). A conditioned rate-like rule (rate, schedule, share,
    exclude) whose condition is U is an alternative on both sides: pick_single keeps the lowest-tax alternative on the
    floor and the highest on the ceiling, the unconditioned rule of the same value among them."""
    if rule["eff"] in RATE_LIKE and rule["conditioned"]:
        return "both"
    if rule["eff"] in ("fine", "fine_min", "fine_max") and rule["conditioned"]:
        base = [r for r in cands if r["eff"] in ("fine", rule["eff"]) and not r["conditioned"]]
        if base and rs.pvalue(rule["param"]) < min(rs.pvalue(b["param"]) for b in base):
            return "fav"                                   # e.g. JP 5% for voluntary payment against the 10% rule
    return EFFECTS[rule["eff"]][2]


def eval_cell(rs, slot_key, date, facts, answers, mode="record", suppress=None, assume=None):
    """-> item dict. `suppress(side, rule) -> bool` marks rules denied by an anti_abuse cell on that side.
    `assume`: keys of facts / answers declared as assumptions; the item lists the ones it used and the result without them."""
    parts = parse_slot_key(slot_key)
    if not parts:
        raise ValueError("slot_key must be jur|subject|slot|flow: %r" % slot_key)
    jur, subject, slot, flow = parts
    facts = dict(facts or {})
    mode = facts.pop("mode", mode) or mode                 # rule_test may set the mode through the facts column
    ctx = Context(rs, date, facts, answers, mode, jur)
    cands = rs.candidates(jur, subject, slot, flow, date)
    tv = {r["id"]: ctx.eval(r["tree"]) for r in cands}
    dirs = {r["id"]: direction(rs, r, cands) for r in cands}
    tfacts = rs.typed_facts(facts)
    sched = {(r["id"], side): schedule_value(rs, r, tfacts, side) for r in cands if r["eff"] == "schedule" for side in SIDES}
    vals = {side: (lambda r, side=side: sched[(r["id"], side)][0] if r["eff"] == "schedule" else rs.pvalue(r["param"]))
            for side in SIDES}

    def applied(side, forced=None):
        out = []
        for r in cands:
            s, _ = tv[r["id"]]
            if forced and r["id"] in forced:
                take = forced[r["id"]]
            elif s == "T":
                take = True
            elif s == "F":
                take = False
            else:
                take = dirs[r["id"]] == "both" or (side == "floor") == (dirs[r["id"]] == "fav")
            if take and not (suppress and suppress(side, r)):
                out.append(r)
        return out

    certain = {r["id"] for r in cands if tv[r["id"]][0] == "T"}

    def result(forced=None):
        sure = certain | {k for k, v in (forced or {}).items() if v}
        return {side: compose(rs, slot, applied(side, forced), side, sure, vals[side]) for side in SIDES}

    res = result()
    pending, needs = [], set()
    for r in cands:
        s, n = tv[r["id"]]
        if s != "U":
            continue
        a, b = result({r["id"]: True}), result({r["id"]: False})
        if any(outcome(a[x]) != outcome(b[x]) for x in SIDES):
            pending.append({"rule_id": r["id"], "needs": sorted(n)})
            needs |= n
    for r in cands:                                           # a schedule applied without its inputs: pending on them
        if r["eff"] == "schedule" and any(r["id"] in res[s]["rules"] for s in SIDES):
            miss = [m for m in sched[(r["id"], "ceiling")][1] if m in SCHEDULE_INPUTS]
            if miss:
                pending.append({"rule_id": r["id"], "needs": sorted(("MISSING", m) for m in miss)})
                needs |= {("MISSING", m) for m in miss}
    by_id = {r["id"]: r for r in cands}
    used = {rid for side in SIDES for rid in res[side]["rules"]}
    used_keys = {v for r in cands for v in leaves(r["tree"], "var")} | {k for r in cands for k in leaves(r["tree"], "pred")}
    used_keys |= {"%s@%s" % (k, jur) for r in cands for k in leaves(r["tree"], "pred")}
    assumptions = sorted(k for k in (assume or ()) if k in used_keys and (k in facts or k in (answers or {})))
    item = {
        "slot_key": slot_key, "jur": jur, "subject": subject, "slot": slot, "counterparty": flow, "date": date,
        "status": "absent" if not cands else ("U" if pending else "T"),
        "value_kind": value_kind([by_id[i] for i in res["ceiling"]["rules"]]),
        "assumptions": assumptions,
        "floor": res["floor"], "ceiling": res["ceiling"],
        "rules_applied": {side: res[side]["rules"] for side in SIDES},
        "conditions": {r["id"]: [tv[r["id"]][0], sorted(tv[r["id"]][1])] for r in cands},
        "pending": pending, "needs": sorted(needs),
        "cite_ids": sorted({c for r in cands if r["id"] in used for c in r["cites"]}),
        "decision_ids": sorted({d for r in cands if r["id"] in used for d in r["decisions"]}),
    }
    if sched:                                                 # what a schedule rule read, so that trace.py can recompose
        item["schedule_inputs"] = {k: tfacts[k] for k in SCHEDULE_INPUTS
                                   if isinstance(tfacts.get(k), (int, float)) and not isinstance(tfacts.get(k), bool)}
    if assumptions:
        f2 = {k: v for k, v in facts.items() if k not in assumptions}
        a2 = {k: v for k, v in (answers or {}).items() if k not in assumptions}
        base = eval_cell(rs, slot_key, date, dict(f2, mode=mode), a2, mode, suppress)
        item["without_assumptions"] = {"status": base["status"], "floor": base["floor"]["value"], "ceiling": base["ceiling"]["value"], "needs": base["needs"]}
    check_invariants(item)
    return item


def value_kind(applied_rules):
    """statutory: only rules without variables or predicates took effect (base rates and `$param = true` rules);
    conditional: a rule that reads facts or judgments took effect; none: no rule applied."""
    if not applied_rules:
        return "none"
    if all(not (leaves(r["tree"], "var") or leaves(r["tree"], "pred")) for r in applied_rules):
        return "statutory"
    return "conditional"


def check_invariants(item):
    f, c = item["floor"]["value"], item["ceiling"]["value"]
    if isinstance(f, (int, float)) and isinstance(c, (int, float)) and float(f) > float(c) + 1e-9:
        raise Defect("%s: floor %r above ceiling %r" % (item["slot_key"], f, c))
    if item["status"] == "T" and item["needs"]:
        raise Defect("%s: status T with needs %r" % (item["slot_key"], item["needs"]))
    if (item["rules_applied"]["floor"] or item["rules_applied"]["ceiling"]) and not item["cite_ids"]:
        raise Defect("%s: rules applied but no cite" % item["slot_key"])


# ---------------------------------------------------------------- a dividend flow (spec §4 cross-cell order, §5 cells)
def tri(item, name):
    """Residence item -> True, False or Unknown(needs) for the derived variable `name`. A cell without rules (the
    jurisdiction is not in the library) leaves the variable missing rather than silently false."""
    if item["status"] == "absent":
        return Unknown({("MISSING", name)})
    if item["status"] == "U":
        return Unknown(item["needs"])
    return bool(item["ceiling"]["value"])


def entity_view(facts, who):
    """Plain facts overlaid with the `who.` facts (who = payer | payee), prefixes stripped."""
    out = {k: v for k, v in facts.items() if "." not in k}
    out.update({k.split(".", 1)[1]: v for k, v in facts.items() if k.startswith(who + ".")})
    return out


def suppressor(deny_rules_by_side):
    def fn(side, rule):
        for d in deny_rules_by_side.get(side, []):
            for o in d["overrides_list"]:
                if o == rule["id"]:
                    return True
                if o.endswith(":*") and o[:-2] == rule["eff"] and d["flow"] in ("*", rule["flow"]):
                    return True
        return False
    return fn


def apply_anti_abuse(rs, aa, targets):
    """Re-evaluate the target cells under the deny rules of anti_abuse item `aa`; keep only the pending deny groups
    that change some target. targets: list of (slot_key, facts, exclude_flows). Returns (items, aa)."""
    by_id = {r["id"]: r for r in rs.rules}
    applied = {side: [by_id[i] for i in aa["rules_applied"][side] if by_id[i]["eff"] == "deny"] for side in SIDES}

    def run(deny_sets):
        return [eval_cell(rs, sk, aa["date"], f, aa["_answers"], aa["_mode"], suppressor(deny_sets), aa.get("_assume"))
                for sk, f in targets]

    items = run(applied)
    kept = []
    for g in aa["pending"]:
        d = by_id[g["rule_id"]]
        with_d = {side: [x for x in applied[side] if x is not d] + [d] for side in SIDES}
        without = {side: [x for x in applied[side] if x is not d] for side in SIDES}
        a, b = run(with_d), run(without)
        changed = [i for i, (x, y) in enumerate(zip(a, b)) if any(outcome(x[s]) != outcome(y[s]) for s in SIDES)]
        if changed:
            kept.append(g)
            for i in changed:                          # the denial is part of what keeps the target open
                it = items[i]
                it["pending"].append({"rule_id": g["rule_id"], "needs": g["needs"]})
                it["needs"] = sorted({tuple(n) for n in it["needs"]} | {tuple(n) for n in g["needs"]})
                if it["status"] != "absent":
                    it["status"] = "U"
    aa["pending"] = kept
    aa["needs"] = sorted({tuple(n) for g in kept for n in g["needs"]})
    aa["status"] = "absent" if aa["status"] == "absent" else ("U" if kept else "T")
    for it in items:
        it["denied_by"] = aa["rules_applied"]
    return items, aa


def treaty_rate(rs, pair, pct, date):
    """The dividend cap of treaty `pair` (e.g. cn-sg) for a holder of `pct` %, from the library parameters; None when the
    pair has no dividend parameter, Unknown when the holding decides and is not given."""
    def p(name):
        pid = "%s.outbound_wht.%s" % (pair, name)
        return rs.pvalue(pid) if pid in rs.lib.params and rs.lib.param_effective(pid, date) else None
    reduced, least, other = p("dividend_rate_reduced"), p("holding_pct_min"), p("dividend_rate_other")
    other = p("dividend_rate") if other is None else other
    if reduced is not None and least is not None:
        if pct is None:
            return Unknown({("MISSING", "holding_pct")})
        if float(pct) >= least:
            return reduced
    elif reduced is not None:
        return reduced
    return other


def parent_treaty_not_worse(rs, S, R, facts, date):
    """Derived variable parent_treaty_not_worse (rule/variable.csv): would the payee's parent, receiving the dividend
    directly, have a dividend cap at least as good as the payee's? No treaty for the parent's pair: not a qualifying
    person. None when there is no parent."""
    parent = facts.get("parent_jur")
    if not parent:
        return None
    pct = facts.get("holding_pct")
    up = facts.get("parent_holding_pct")
    mine = treaty_rate(rs, "%s-%s" % (S, R), pct, date)
    if str(parent).lower() == S.lower():
        return False                                   # a parent resident in the source state has no treaty with it
    theirs = treaty_rate(rs, "%s-%s" % (S, str(parent).lower()), None if pct is None or up is None else float(pct) * float(up) / 100, date)
    for v in (mine, theirs):
        if isinstance(v, Unknown):
            return v
    if theirs is None:
        return False
    if mine is None:
        return True
    return theirs <= mine


def eval_flow(rs, payer_jur, payee_jur, subject, date, facts, answers, mode="record", assume=None):
    """A dividend from a company in payer_jur to a `subject` in payee_jur. facts: plain names for the payment,
    `payer.<name>` / `payee.<name>` for the two entities. Returns the items of the nine cells (spec §5)."""
    S, R = payer_jur, payee_jur
    payer_f, payee_f = entity_view(facts, "payer"), entity_view(facts, "payee")
    derived = parent_treaty_not_worse(rs, S, R, payee_f, date)      # computed from the parameters, not asked (variable.csv)
    if derived is not None:
        for view in (payer_f, payee_f):
            if view.get("parent_treaty_not_worse") in (None, ""):
                view["parent_treaty_not_worse"] = derived
    items = []
    res_payer_S = eval_cell(rs, "%s|company|residence|*" % S, date, payer_f, answers, mode, assume=assume)
    res_payee_R = eval_cell(rs, "%s|%s|residence|*" % (R, subject), date, payee_f, answers, mode, assume=assume)
    res_payer_R = eval_cell(rs, "%s|company|residence|*" % R, date, payer_f, answers, mode, assume=assume)
    items += [res_payer_S, res_payee_R]
    payee_in_R = tri(res_payee_R, "payee_resident")       # treaty rules test payee_resident = true themselves

    s_facts = dict(payer_f)
    s_facts["payee_resident"] = payee_in_R
    s_facts["payer_resident"] = tri(res_payer_S, "payer_resident")
    aa_S = eval_cell(rs, "%s|%s|anti_abuse|%s" % (S, subject, R), date, s_facts, answers, mode, assume=assume)
    aa_S.update(_answers=answers, _mode=mode, _assume=assume)
    (out,), aa_S = apply_anti_abuse(rs, aa_S, [("%s|%s|outbound_wht|%s" % (S, subject, R), s_facts)])
    items += [out, aa_S]

    r_facts = dict(payee_f)
    r_facts["payer_resident"] = tri(res_payer_R, "payer_resident")
    r_facts["payee_resident"] = payee_in_R
    aa_R = eval_cell(rs, "%s|%s|anti_abuse|%s" % (R, subject, S), date, r_facts, answers, mode, assume=assume)
    aa_R.update(_answers=answers, _mode=mode, _assume=assume)
    (inb, fin), aa_R = apply_anti_abuse(rs, aa_R, [("%s|%s|inbound|%s" % (R, subject, S), r_facts),
                                                   ("%s|%s|final|*" % (R, subject), r_facts)])
    cfc = eval_cell(rs, "%s|%s|cfc|*" % (R, subject), date, r_facts, answers, mode, assume=assume)
    items += [inb, aa_R, fin, cfc]
    for it in items:
        it.pop("_answers", None)
        it.pop("_mode", None)
        it.pop("_assume", None)
    seen = set()
    for it in items:
        key = (it["jur"], it["slot"], it["counterparty"], it is res_payer_S or it is res_payer_R)
        if key in seen and S != R:                      # a domestic hop (S == R) evaluates the same anti_abuse cell twice
            raise Defect("two items for %s" % it["slot_key"])
        seen.add(key)
    return items


def eval_transfer(rs, target_jur, home_jur, subject, date, facts, answers, mode="record", assume=None):
    """A transfer of shares in a company of target_jur by a `subject` resident (or not) in home_jur: the source cell
    `target|subject|restructure|home` and the home cell `home|subject|restructure|target` (spec §5). facts: plain names for the
    transfer (transfer_gain, transferred_pct, consideration ...), `target.<name>` for the company transferred (listed,
    property_rich_ratio ...), `transferor.<name>` for the transferor (incorporated_in, managed_in ...). Returns the
    residence items of the transferor (in home and in target) and the two restructure items."""
    T, H = target_jur, home_jur
    target_f, tr_f = entity_view(facts, "target"), entity_view(facts, "transferor")
    res_H = eval_cell(rs, "%s|%s|residence|*" % (H, subject), date, tr_f, answers, mode, assume=assume)
    res_T = eval_cell(rs, "%s|%s|residence|*" % (T, subject), date, tr_f, answers, mode, assume=assume)
    in_H, in_T = tri(res_H, "transferor_resident"), tri(res_T, "transferor_resident")
    src = dict(target_f)
    src.update(tr_f)                                        # the transferor's own facts win (substance, receipts); target attributes come as target_* plain facts
    src["transferor_resident"] = in_T                      # the transferor is resident where the company is
    src["payee_resident"] = in_H                           # treaty rules: the transferor is resident in the partner
    src["target_in_jurisdiction"] = True
    source = eval_cell(rs, "%s|%s|restructure|%s" % (T, subject, H), date, src, answers, mode, assume=assume)
    items = [res_H, res_T, source]
    if H != T:
        hm = dict(target_f)
        hm.update(tr_f)
        hm["transferor_resident"] = in_H
        hm["payee_resident"] = in_T
        hm["target_in_jurisdiction"] = False
        items.append(eval_cell(rs, "%s|%s|restructure|%s" % (H, subject, T), date, hm, answers, mode, assume=assume))
    return items


# ---------------------------------------------------------------- rule_test (spec §2.6)
def parse_kv(s):
    out = {}
    for part in (s or "").split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def fmt_value(v):
    if v is None:
        return "-"
    if isinstance(v, dict):                                   # a penalty cell
        parts = ["%s%%/%s" % (fmt_value(i["pct"]), i["period"] or "?") for i in v.get("interest", [])]
        if v.get("interest_cap") is not None:
            parts.append("cap %s%%" % fmt_value(v["interest_cap"]))
        if v.get("fine_max") is not None:
            parts.append("fine %s-%s%%" % (fmt_value(v.get("fine_min")), fmt_value(v["fine_max"])))
        return "; ".join(parts) or "-"
    if isinstance(v, bool):
        return "yes" if v else "no"
    return ("%.6f" % v).rstrip("0").rstrip(".")


def run_test(rs, t):
    """-> None when the test passes, else the failure text."""
    rule_id = t["test_id"].rsplit(".", 1)[0]
    rule = next((r for r in rs.rules if r["id"] == rule_id), None)
    if not rule:
        return "rule %s not found" % rule_id
    try:
        item = eval_cell(rs, t["slot_key"], t["date"], parse_kv(t["facts"]), parse_kv(t["answers"]))
    except Defect as e:
        return "Defect: %s" % e
    want = (t["expect"] or "").split()
    if len(want) != 3:
        return "expect must be '<effect> <value> <status>'"
    w_eff, w_val, w_status = want
    if w_eff != rule["eff"]:
        return "expect names effect %s but the rule's effect is %s" % (w_eff, rule["eff"])
    cond = item["conditions"].get(rule_id)
    got_status = "-" if cond is None else cond[0]
    if cond and cond[0] == "U":
        got_status = "U:" + ",".join(sorted(k for _, k in cond[1]))
    if rule["eff"] in OWN_VALUE_EFFECTS:                     # penalty dict / stamp: the test checks this rule's own figure
        got_val = fmt_value(rs.pvalue(rule["param"])) if rule_id in item["rules_applied"]["ceiling"] else "-"
    elif item["slot"] == "cfc" and rule["eff"] in ("rate", "surtax", "schedule"):
        got_val = fmt_value(item["ceiling"].get("rate"))
    else:
        got_val = fmt_value(item["ceiling"]["value"])
    if got_status != w_status or not same_value(got_val, w_val):
        return "expected '%s', got '%s %s %s'" % (t["expect"], rule["eff"], got_val, got_status)
    return None


def same_value(a, b):
    if a == b:
        return True
    try:
        return abs(float(a) - float(b)) < 1e-6
    except ValueError:
        return False


# ---------------------------------------------------------------- command line
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slot", help="slot_key of one cell")
    ap.add_argument("--flow", nargs=3, metavar=("PAYER_JUR", "PAYEE_JUR", "SUBJECT"))
    ap.add_argument("--transfer", nargs=3, metavar=("TARGET_JUR", "HOME_JUR", "SUBJECT"), help="a share transfer: the company transferred is in TARGET_JUR, the transferor in HOME_JUR")
    ap.add_argument("--date", required=True)
    ap.add_argument("--facts", default="")
    ap.add_argument("--answers", default="")
    ap.add_argument("--mode", default="record", choices=("record", "plan"))
    ap.add_argument("--assume", default="", help="keys of facts/answers declared as assumptions, ';'-separated")
    ap.add_argument("--root", default="")
    ap.add_argument("--db", default="")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    rs = RuleSet(Path(a.root) if a.root else ROOT, Path(a.db) if a.db else DB)
    facts, answers = parse_kv(a.facts), parse_kv(a.answers)
    assume = [x.strip() for x in a.assume.split(";") if x.strip()]
    if a.slot:
        items = [eval_cell(rs, a.slot, a.date, facts, answers, a.mode, assume=assume)]
    elif a.transfer:
        items = eval_transfer(rs, a.transfer[0], a.transfer[1], a.transfer[2], a.date, facts, answers, a.mode, assume=assume)
    elif a.flow:
        items = eval_flow(rs, a.flow[0], a.flow[1], a.flow[2], a.date, facts, answers, a.mode, assume=assume)
    else:
        ap.error("give --slot or --flow")
    if a.json:
        print(json.dumps(items, ensure_ascii=False, indent=1))
        return 0
    for it in items:
        extra = ""
        if it.get("assumptions"):
            w = it["without_assumptions"]
            extra = "  assumed=%s  without=%s..%s %s" % (",".join(it["assumptions"]), fmt_value(w["floor"]), fmt_value(w["ceiling"]), w["status"])
        if it["ceiling"].get("stamp") is not None or it["floor"].get("stamp") is not None:
            extra += "  stamp=%s..%s" % (fmt_value(it["floor"].get("stamp")), fmt_value(it["ceiling"].get("stamp")))
        print("%s  status=%s  floor=%s  ceiling=%s  kind=%s%s" % (it["slot_key"], it["status"], fmt_value(it["floor"]["value"]),
                                                               fmt_value(it["ceiling"]["value"]), it.get("value_kind", ""), extra))
        for side in SIDES:
            print("   %-8s %s" % (side, ", ".join(it["rules_applied"][side]) or "-"))
        for rid, (s, needs) in it["conditions"].items():
            print("   cond     %-40s %s %s" % (rid, s, " ".join("%s:%s" % n for n in needs)))
        if it["pending"]:
            print("   pending  " + "; ".join("%s -> %s" % (g["rule_id"], ",".join("%s:%s" % tuple(n) for n in g["needs"]))
                                            for g in it["pending"]))
        print("   cite     " + (", ".join(it["cite_ids"]) or "-"))
        if it["decision_ids"]:
            print("   decision " + ", ".join(it["decision_ids"]))
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main())
