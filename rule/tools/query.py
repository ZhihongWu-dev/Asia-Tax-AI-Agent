#!/usr/bin/env python
"""Reverse and differential queries of the rule layer (rule/规则层规范（最小集）.md §5): judgment points, requirements,
options, what-if, gaps, the field dictionary and the version stamp. Read-only; same input, same output.

Python 3.11, standard library only.

  python rule/tools/query.py judgment_points --flow cn hk company --date 2026-04-30 --facts '...' [--answers '...']
  python rule/tools/query.py requirements --slot 'cn|company|outbound_wht|hk' [--effect cap] [--date YYYY-MM-DD]
  python rule/tools/query.py requirements --rule cn-hk.outbound_wht.cap_5
  python rule/tools/query.py options --flow cn hk company --date 2026-04-30
  python rule/tools/query.py what_if --flow cn hk company --date ... --facts '...' --answers '...' --set 'holding_pct=20' --answer-set 'bo=yes'
  python rule/tools/query.py gap --flow cn hk company
  python rule/tools/query.py variables | predicates | version
  options: --json  --root rule/  --db database/  --mode record|plan
"""
import argparse
import datetime
import hashlib
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import EFFECTS, Library, leaves, parse_slot_key, read_csv, split_list  # noqa: E402
import eval as ev  # noqa: E402
from rule_tool import RuleTool  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT.parent / "database"


class Query:
    def __init__(self, root=ROOT, db=DB):
        self.root, self.db = Path(root), Path(db)
        self.tool = RuleTool(root, db)
        self.rs, self.lib = self.tool.rs, self.tool.lib

    # ------------------------------------------------------------ field dictionary, version
    def variables(self):
        return [dict(v) for v in read_csv(self.root / "variable.csv")]

    def predicates(self):
        out = []
        for p in read_csv(self.root / "predicate.csv"):
            row = dict(p)
            row["factors"] = [{"cite_id": c, "text": self.lib.clause(c) or ""} for c in split_list(p.get("factors_cite"))]
            row["factor_vars"] = split_list(p.get("factor_vars"))
            out.append(row)
        return out

    def version(self):
        def sha(path):
            return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16] if Path(path).exists() else ""
        return {
            "rule": {"rules": len(self.rs.rules), "variables": len(self.rs.variables), "predicates": len(self.rs.predicates),
                     "decisions": len(read_csv(self.root / "decision.csv")), "tests": len(read_csv(self.root / "rule_test.csv")),
                     "rule_csv_sha256": sha(self.root / "rule.csv")},
            "database": {"jurisdictions": len(self.lib.juris), "docs": len(self.lib.docs), "params": len(self.lib.params),
                         "param_csv_sha256": sha(self.db / "param.csv"), "doc_csv_sha256": sha(self.db / "doc.csv")},
            "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    # ------------------------------------------------------------ requirements / options
    def expand(self, tree):
        """Condition tree -> the same tree with leaves resolved: parameter values, variable questions, predicate rows."""
        if tree is True:
            return {"kind": "always"}
        (k, v), = tree.items()
        if k in ("and", "or"):
            return {"kind": k, "parts": [self.expand(x) for x in v]}
        if k == "not":
            return {"kind": "not", "part": self.expand(v)}
        if k == "pred":
            p = self.rs.predicates.get(v, {})
            return {"kind": "predicate", "key": v, "question": p.get("question", ""), "factors_cite": split_list(p.get("factors_cite")),
                    "factor_vars": split_list(p.get("factor_vars"))}
        if k == "listed":
            prefix, var = v
            return {"kind": "listed", "prefix": prefix, "variable": var["var"],
                    "listed": sorted(pid[len(prefix) + 1:] for pid in self.lib.params if pid.startswith(prefix + "_"))}
        if k == "in":
            return {"kind": "in", "left": self.operand(v[0]), "values": v[1]}
        return {"kind": "compare", "op": k, "left": self.operand(v[0]), "right": self.operand(v[1])}

    def operand(self, x):
        if isinstance(x, dict) and "var" in x:
            row = self.rs.variables.get(x["var"], {})
            return {"variable": x["var"], "kind": row.get("kind", ""), "type": row.get("type", ""), "question": row.get("question", "")}
        if isinstance(x, dict) and "param" in x:
            p = self.lib.params.get(x["param"], {})
            return {"param_id": x["param"], "value": p.get("value"), "unit": p.get("unit"), "cite_id": p.get("cite_id"), "quote": p.get("quote"),
                    "effective_from": p.get("effective_from"), "effective_to": p.get("effective_to")}
        return {"constant": x}

    def requirements(self, slot_key=None, effect=None, rule_id=None, date=None):
        rules = self.tool.rule_rows(rule_id=rule_id) if rule_id else self.tool.rule_rows(slot_key=slot_key, date=date)
        if effect:
            rules = [r for r in rules if r["eff"] == effect or r["effect"] == effect]
        out = []
        for r in rules:
            x = self.tool.expand(r)
            out.append({"rule_id": r["id"], "slot_key": r["slot_key"], "effect": r["effect"], "direction": direction_of(r),
                        "condition": r["condition"], "requires": self.expand(r["tree"]),
                        "variables": leaves(r["tree"], "var"), "predicates": leaves(r["tree"], "pred"),
                        "procedure": x["procedure"], "cite_ids": r["cites"], "decision_ids": r["decisions"]})
        ref = self.tool.reference_params(slot_key or (rules[0]["slot_key"] if rules else "")) if (slot_key or rules) else []
        return {"rules": out, "reference_params": ref}

    def options(self, S, R, subject, date):
        out = []
        for sk in cells_for_flow(S, R, subject):
            fav = [r for r in self.tool.rule_rows(slot_key=sk, date=date) if direction_of(r) == "fav"]
            if fav:
                out.append({"slot_key": sk, "options": self.requirements(slot_key=sk, date=date)["rules"] and
                            [o for o in self.requirements(slot_key=sk, date=date)["rules"] if o["direction"] == "fav"]})
        return out

    # ------------------------------------------------------------ judgment points, what-if, gap
    def judgment_points(self, flow=None, slot=None, date=None, facts=None, answers=None, mode="record"):
        facts, answers = dict(facts or {}), dict(answers or {})
        items = self._run(flow, slot, date, facts, answers, mode)
        out = []
        seen = set()
        for it in items:
            for g in it["pending"]:
                for kind, key in [tuple(n) for n in g["needs"]]:
                    if kind != "DISCRETION" or (it["slot_key"], key) in seen:
                        continue
                    seen.add((it["slot_key"], key))
                    p = self.rs.predicates.get(key, {})
                    res = {}
                    for ans in ("yes", "no"):
                        a2 = dict(answers, **{key: ans})
                        alt = self._run(flow, slot, date, facts, a2, mode)
                        alt_it = next((x for x in alt if x["slot_key"] == it["slot_key"]), None)
                        res[ans] = {"floor": alt_it["floor"]["value"], "ceiling": alt_it["ceiling"]["value"], "status": alt_it["status"],
                                    "remaining_needs": alt_it["needs"]} if alt_it else None
                    out.append({"slot_key": it["slot_key"], "predicate": key, "question": p.get("question", ""),
                                "factors": [{"cite_id": c, "text": self.lib.clause(c) or ""} for c in split_list(p.get("factors_cite"))],
                                "factor_vars": [{"variable": v, "value": self._fact(facts, v, it)} for v in split_list(p.get("factor_vars"))],
                                "blocked_rules": [g2["rule_id"] for g2 in it["pending"] if ["DISCRETION", key] in [list(n) for n in g2["needs"]]],
                                "now": {"floor": it["floor"]["value"], "ceiling": it["ceiling"]["value"]}, "if": res})
        return out

    def _fact(self, facts, v, item):
        for prefix in ("", "payee.", "payer."):
            if prefix + v in facts:
                return facts[prefix + v]
        return None

    def _run(self, flow, slot, date, facts, answers, mode):
        if slot:
            return [ev.eval_cell(self.rs, slot, date, facts, answers, mode)]
        return ev.eval_flow(self.rs, flow[0], flow[1], flow[2], date, facts, answers, mode)

    def what_if(self, flow=None, slot=None, date=None, facts=None, answers=None, mode="record", set_facts=None, set_answers=None):
        before = self._run(flow, slot, date, dict(facts or {}), dict(answers or {}), mode)
        f2, a2 = dict(facts or {}), dict(answers or {})
        f2.update(set_facts or {})
        a2.update(set_answers or {})
        after = self._run(flow, slot, date, f2, a2, mode)
        out = []
        for b, a in zip(before, after):
            changed = (b["floor"]["value"], b["ceiling"]["value"], b["status"], b["needs"]) != (a["floor"]["value"], a["ceiling"]["value"], a["status"], a["needs"])
            out.append({"slot_key": b["slot_key"], "changed": changed,
                        "before": {"floor": b["floor"]["value"], "ceiling": b["ceiling"]["value"], "status": b["status"], "needs": b["needs"]},
                        "after": {"floor": a["floor"]["value"], "ceiling": a["ceiling"]["value"], "status": a["status"], "needs": a["needs"],
                                  "rules_applied": a["rules_applied"]}})
        return {"changes": {"facts": set_facts or {}, "answers": set_answers or {}}, "cells": out}

    def gap(self, S, R, subject):
        absent = {(a["jur"], s, a["slot"]) for a in self.lib.absences if a.get("subject") and a.get("slot")
                  for s in (("company", "individual") if a["subject"] == "all" else (a["subject"],))}
        out, seen = [], set()
        for sk in cells_for_flow(S, R, subject):
            if sk in seen:
                continue
            seen.add(sk)
            jur, subj, slot, flow = parse_slot_key(sk)
            rules = self.tool.rule_rows(slot_key=sk)
            effects = sorted({r["eff"] for r in rules})
            allowed = [e for e, (slots, _, _) in EFFECTS.items() if slot in slots]
            entry = {"slot_key": sk, "rules": len(rules), "effects_present": effects,
                     "effects_absent": [e for e in allowed if e not in effects],
                     "variables": sorted({v for r in rules for v in leaves(r["tree"], "var")}),
                     "predicates": sorted({p for r in rules for p in leaves(r["tree"], "pred")})}
            if not rules:
                entry["gap"] = "absence record in the library" if (jur, subj, slot) in absent else "no rules and no absence record: jurisdiction or cell not collected"
            if flow != "*" and not self.lib.treaty(jur, flow):
                entry["treaty"] = "no treaty text for %s-%s in the library" % (jur, flow)
            out.append(entry)
        return {"note": "effects_absent lists effects the slot allows but no rule of the cell produces; the library records absence "
                        "only per slot, so an absent effect may not exist in law or may simply not be modelled", "cells": out}


def direction_of(r):
    d = EFFECTS[r["eff"]][2]
    return d


def cells_for_flow(S, R, subject):
    return ["%s|company|residence|*" % S, "%s|%s|residence|*" % (R, subject), "%s|company|residence|*" % R,
            "%s|%s|outbound_wht|%s" % (S, subject, R), "%s|%s|anti_abuse|%s" % (S, subject, R),
            "%s|%s|inbound|%s" % (R, subject, S), "%s|%s|anti_abuse|%s" % (R, subject, S),
            "%s|%s|final|*" % (R, subject), "%s|%s|cfc|*" % (R, subject)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=("judgment_points", "requirements", "options", "what_if", "gap", "variables", "predicates", "version", "cells_for_flow"))
    ap.add_argument("--slot")
    ap.add_argument("--rule")
    ap.add_argument("--effect")
    ap.add_argument("--flow", nargs=3, metavar=("PAYER_JUR", "PAYEE_JUR", "SUBJECT"))
    ap.add_argument("--date")
    ap.add_argument("--facts", default="")
    ap.add_argument("--answers", default="")
    ap.add_argument("--set", default="", help="facts to change for what_if")
    ap.add_argument("--answer-set", default="", help="answers to change for what_if")
    ap.add_argument("--mode", default="record", choices=("record", "plan"))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--root", default="")
    ap.add_argument("--db", default="")
    a = ap.parse_args()
    q = Query(Path(a.root) if a.root else ROOT, Path(a.db) if a.db else DB)
    facts, answers = ev.parse_kv(a.facts), ev.parse_kv(a.answers)
    c = a.command
    if c == "variables":
        res = q.variables()
    elif c == "predicates":
        res = q.predicates()
    elif c == "version":
        res = q.version()
    elif c == "cells_for_flow":
        res = cells_for_flow(*a.flow)
    elif c == "requirements":
        res = q.requirements(a.slot, a.effect, a.rule, a.date)
    elif c == "options":
        res = q.options(a.flow[0], a.flow[1], a.flow[2], a.date)
    elif c == "judgment_points":
        res = q.judgment_points(a.flow, a.slot, a.date, facts, answers, a.mode)
    elif c == "what_if":
        res = q.what_if(a.flow, a.slot, a.date, facts, answers, a.mode, ev.parse_kv(a.set), ev.parse_kv(a.answer_set))
    else:
        res = q.gap(a.flow[0], a.flow[1], a.flow[2])
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main())
