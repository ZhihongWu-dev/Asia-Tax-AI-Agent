#!/usr/bin/env python
"""Trace-back check of evaluation output (rule/规则层规范（最小集）.md §7 回溯). For every item it walks
item -> rule_id -> effect and condition parameters -> param.quote verbatim in clause.text and parameter effective at
the item's date -> every cite_id a clause whose document is in force at the date -> decision quotes verbatim in their
clauses -> the value recomposed from the applied rules equals the item's value. Any broken link = FAIL.

Python 3.11, standard library only.

  python rule/tools/trace.py --items out.json              (JSON written by eval.py --json)
  python rule/tools/trace.py --flow cn hk company --date 2026-01-01 --facts '...' [--answers '...'] [--mode plan]
  python rule/tools/trace.py --slot 'cn|company|outbound_wht|hk' --date 2026-01-01 --facts '...'
  options: --root rule/  --db database/  --json
Exit code 0 when every item passes, 1 otherwise.
"""
import argparse
import io
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Library, in_window, read_csv  # noqa: E402
import eval as ev  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT.parent / "database"


def norm(s):
    return re.sub(r"\s+", "", s or "")


class Tracer:
    def __init__(self, root=ROOT, db=DB):
        self.lib = Library(db)
        self.rs = ev.RuleSet(root, db, lib=self.lib)
        self.rules = {r["id"]: r for r in self.rs.rules}
        self.decisions = {}
        for d in read_csv(Path(root) / "decision.csv"):
            self.decisions.setdefault(d["id"], []).append(d)

    # ------------------------------------------------------------ links
    def check_param(self, pid, date, chain, fails):
        p = self.lib.params.get(pid)
        if not p:
            fails.append("parameter %s not in param" % pid)
            return
        text = self.lib.clause(p["cite_id"])
        if text is None:
            fails.append("parameter %s cites %s, not in clause" % (pid, p["cite_id"]))
        elif norm(p["quote"]) not in norm(text):
            fails.append("parameter %s: quote not verbatim in %s" % (pid, p["cite_id"]))
        if not in_window(date, p.get("effective_from"), p.get("effective_to")):
            fails.append("parameter %s not effective at %s (%s..%s)" % (pid, date, p.get("effective_from") or "", p.get("effective_to") or ""))
        chain.append("param %s = %s %s <- %s" % (pid, p["value"], p["unit"], p["cite_id"]))

    def check_cite(self, cite, date, chain, fails):
        text = self.lib.clause(cite)
        if text is None:
            fails.append("cite %s not in clause" % cite)
            return
        doc = self.lib.docs.get(cite.split("#", 1)[0])
        if not doc:
            fails.append("cite %s: document not in doc" % cite)
            return
        if not in_window(date, doc.get("effective_from"), doc.get("effective_to")):
            fails.append("cite %s: document not in force at %s (%s..%s)" % (cite, date, doc.get("effective_from") or "", doc.get("effective_to") or ""))
        chain.append("clause %s (%s, %s)" % (cite, doc["type"], doc["title"][:50]))

    def check_decision(self, did, chain, fails):
        rows = self.decisions.get(did)
        if not rows:
            fails.append("decision %s not in decision" % did)
            return
        for d in rows:
            text = self.lib.clause(d["cite_id"])
            if text is None:
                fails.append("decision %s cites %s, not in clause" % (did, d["cite_id"]))
            elif norm(d["quote"]) not in norm(text):
                fails.append("decision %s: quote not verbatim in %s" % (did, d["cite_id"]))
            chain.append("decision %s <- %s" % (did, d["cite_id"]))

    def recompose(self, item, fails):
        """The value from the applied rules and the parameters must equal the item's value (spec §7 不变量)."""
        certain = {rid for rid, (s, _) in item.get("conditions", {}).items() if s == "T"}
        sched_facts = item.get("schedule_inputs") or {}
        for side in ev.SIDES:
            rules = [self.rules[rid] for rid in item["rules_applied"][side] if rid in self.rules]
            # rules_applied lists the rules that determined the value on this side (alternatives not chosen are left
            # out), so they are the certain ones here; a schedule's value is recomputed from the inputs the item kept
            val = (lambda r, side=side: ev.schedule_value(self.rs, r, sched_facts, side)[0] if r["eff"] == "schedule"
                   else self.rs.pvalue(r["param"]))
            try:
                chosen = {r["id"] for r in rules if r["eff"] in ev.RATE_LIKE}   # listed rate-like rules are the chosen alternatives
                res = ev.compose(self.rs, item["slot"], rules, side, certain | chosen, val)
            except ev.Defect as e:
                fails.append("%s: recompose: %s" % (side, e))
                continue
            if json.dumps(res.get("value")) != json.dumps(item[side]["value"]):
                fails.append("%s: recomposed value %r differs from item value %r" % (side, res.get("value"), item[side]["value"]))

    # ------------------------------------------------------------ one item
    def trace_item(self, item):
        date = item["date"]
        chain, fails = [], []
        used = sorted(set(item["rules_applied"]["floor"]) | set(item["rules_applied"]["ceiling"]))
        if item["status"] == "T" and item.get("needs"):
            fails.append("status T with needs")
        f, c = item["floor"]["value"], item["ceiling"]["value"]
        if isinstance(f, (int, float)) and isinstance(c, (int, float)) and float(f) > float(c) + 1e-9:   # penalty values are dicts
            fails.append("floor above ceiling")
        if used and not item.get("cite_ids"):
            fails.append("rules applied but no cite")
        for rid in used:
            r = self.rules.get(rid)
            if not r:
                fails.append("rule %s not in rule" % rid)
                continue
            chain.append("rule %s: %s -> %s" % (rid, r["condition"], r["effect"]))
            for pid in r["params"]:
                self.check_param(pid, date, chain, fails)
            if not r["cites"]:
                fails.append("rule %s: no cite" % rid)
            for c in r["cites"]:
                self.check_cite(c, date, chain, fails)
            for d in r["decisions"]:
                self.check_decision(d, chain, fails)
            for e in [x.strip() for x in (r["procedure"] or "").split(";") if x.strip()]:
                if e not in self.lib.docs and e not in {a["id"] for a in self.lib.absences} and self.lib.clause(e) is None:
                    fails.append("rule %s: procedure %s unknown" % (rid, e))
        if used:
            self.recompose(item, fails)
        return {"slot_key": item["slot_key"], "status": item["status"], "value": [item["floor"]["value"], item["ceiling"]["value"]],
                "result": "FAIL" if fails else "PASS", "fails": fails, "chain": chain}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", help="JSON file written by eval.py --json, or an optimization-layer hops/transfers file ({\"items\": [...]}, nested lists are flattened)")
    ap.add_argument("--slot")
    ap.add_argument("--flow", nargs=3, metavar=("PAYER_JUR", "PAYEE_JUR", "SUBJECT"))
    ap.add_argument("--date")
    ap.add_argument("--facts", default="")
    ap.add_argument("--answers", default="")
    ap.add_argument("--mode", default="record", choices=("record", "plan"))
    ap.add_argument("--root", default="")
    ap.add_argument("--db", default="")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    root = Path(a.root) if a.root else ROOT
    db = Path(a.db) if a.db else DB
    tr = Tracer(root, db)
    if a.items:
        items = json.loads(Path(a.items).read_text(encoding="utf-8"))
        if isinstance(items, dict) and "items" in items:
            items = items["items"]
        flat = []
        stack = list(items)
        while stack:
            x = stack.pop(0)
            (stack.extend(x) if isinstance(x, list) else flat.append(x))
        items = flat
    else:
        if not a.date:
            ap.error("--date is required with --slot or --flow")
        facts, answers = ev.parse_kv(a.facts), ev.parse_kv(a.answers)
        if a.slot:
            items = [ev.eval_cell(tr.rs, a.slot, a.date, facts, answers, a.mode)]
        elif a.flow:
            items = ev.eval_flow(tr.rs, a.flow[0], a.flow[1], a.flow[2], a.date, facts, answers, a.mode)
        else:
            ap.error("give --items, --slot or --flow")
    results = [tr.trace_item(it) for it in items]
    if a.json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
    else:
        for r in results:
            print("%s  %s  status=%s  value=%s" % (r["result"], r["slot_key"], r["status"],
                                                 "/".join(ev.fmt_value(v) for v in r["value"])))
            for line in r["chain"]:
                print("   " + line)
            for f in r["fails"]:
                print("   ! " + f)
    bad = sum(1 for r in results if r["fails"])
    print("items=%d failed=%d" % (len(results), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main())
