#!/usr/bin/env python
"""The assistant's `rule` tool (rule/规则层规范（最小集）.md §5): returns rule rows with the clauses they cite, the
parameters in their effect and condition, their decisions and procedure documents. It does not evaluate anything;
what it does not find, the assistant must not assert.

Python 3.11, standard library only.

  python rule/tools/rule_tool.py --slot 'cn|company|outbound_wht|hk' [--date 2026-01-01]   rules of a cell (subject all and flow * included)
  python rule/tools/rule_tool.py --rule cn-hk.outbound_wht.cap_5                          one rule
  python rule/tools/rule_tool.py --variable holding_pct                                   which rules read a variable
  python rule/tools/rule_tool.py --predicate bo                                           which rules depend on a predicate, and its factors
  options: --brief (clause text cut to 300 characters)  --json  --root rule/  --db database/
"""
import argparse
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Library, parse_slot_key, read_csv  # noqa: E402
import eval as ev  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT.parent / "database"


class RuleTool:
    def __init__(self, root=ROOT, db=DB):
        self.root = Path(root)
        self.lib = Library(db)
        self.rs = ev.RuleSet(root, db, lib=self.lib)
        self.decisions = {}
        for d in read_csv(self.root / "decision.csv"):
            self.decisions.setdefault(d["id"], []).append(d)

    def rule_rows(self, slot_key=None, date=None, rule_id=None, variable=None, predicate=None):
        if rule_id:
            return [r for r in self.rs.rules if r["id"] == rule_id]
        if variable:
            return [r for r in self.rs.rules if variable in ev.leaves(r["tree"], "var")]
        if predicate:
            return [r for r in self.rs.rules if predicate in ev.leaves(r["tree"], "pred")]
        parts = parse_slot_key(slot_key)
        if not parts:
            raise ValueError("slot_key must be jur|subject|slot|flow")
        jur, subject, slot, flow = parts
        out = []
        for r in self.rs.by_cell.get((jur, slot), []):
            if r["subject"] not in (subject, "all") and subject != "all":
                continue
            if r["flow"] not in (flow, "*"):
                continue
            if date and not self.rs.valid(r, date):
                continue
            out.append(r)
        return out

    def expand(self, r, brief=False):
        def clause(cite):
            text = self.lib.clause(cite) or ""
            doc = self.lib.docs.get(cite.split("#", 1)[0], {})
            return {"cite_id": cite, "doc_type": doc.get("type", ""), "title": doc.get("title", ""), "url": doc.get("url", ""),
                    "effective_from": doc.get("effective_from", ""), "effective_to": doc.get("effective_to", ""),
                    "found": bool(text), "text": (text[:300] + ("…" if len(text) > 300 else "")) if brief else text}

        params = []
        for pid in r["params"]:
            p = self.lib.params.get(pid)
            params.append({"param_id": pid, "found": bool(p), **({k: p[k] for k in ("value", "unit", "cite_id", "quote", "effective_from", "effective_to", "note")} if p else {})})
        decisions = [dict(d) for did in r["decisions"] for d in self.decisions.get(did, [{"id": did, "statement": "(not found)", "cite_id": "", "quote": ""}])]
        proc = []
        for e in [x.strip() for x in (r["procedure"] or "").split(";") if x.strip()]:
            d = self.lib.docs.get(e)
            if d:
                proc.append({"id": e, "kind": "doc", "title": d["title"], "url": d["url"], "category": d["category"]})
                continue
            a = next((x for x in self.lib.absences if x["id"] == e), None)
            if a:
                proc.append({"id": e, "kind": "absence", "statement": a["statement"]})
                continue
            text = self.lib.clause(e)
            if text is not None:
                doc = self.lib.docs.get(e.split("#", 1)[0], {})
                proc.append({"id": e, "kind": "clause", "title": doc.get("title", ""), "text": (text[:300] + "…" if brief and len(text) > 300 else text)})
            else:
                proc.append({"id": e, "kind": "unknown"})
        row = {k: r[k] for k in ("rule_id", "slot_key", "condition", "effect", "overrides", "procedure", "cite_ids", "decision_ids",
                                 "effective_from", "effective_to", "note")}
        row.update(requires=ev.leaves(r["tree"], "var"), predicates=ev.leaves(r["tree"], "pred"))
        return {"rule": row, "clauses": [clause(c) for c in r["cites"]], "params": params, "decisions": decisions, "procedure": proc}

    def reference_params(self, slot_key):
        """Parameters of the cell's jurisdiction (and treaty pair) in the cell's slot that no rule of the cell uses:
        deadlines, certificate rules, factor thresholds. Quoted, not computed."""
        parts = parse_slot_key(slot_key)
        if not parts:
            return []
        jur, subject, slot, flow = parts
        scopes = {jur} | ({"%s-%s" % (jur, flow), "%s-%s" % (flow, jur)} if flow != "*" else set())
        used = {p for r in self.rule_rows(slot_key) for p in r["params"]}
        out = []
        for pid, p in self.lib.params.items():
            if p["scope"] in scopes and p["slot"] == slot and p["subject"] in (subject, "all") and pid not in used:
                out.append({k: p[k] for k in ("param_id", "subject", "value", "unit", "cite_id", "quote", "effective_from", "effective_to", "note")})
        return out

    def predicate_row(self, key):
        p = self.rs.predicates.get(key)
        if not p:
            return None
        return {"key": key, "question": p["question"],
                "factors": [{"cite_id": c, "text": self.lib.clause(c) or ""} for c in (p["factors_cite"] or "").split(";") if c]}

    def variable_row(self, name):
        v = self.rs.variables.get(name)
        return dict(v) if v else None


def print_text(items, extra):
    if extra:
        print(json.dumps(extra, ensure_ascii=False, indent=1))
    for it in items:
        r = it["rule"]
        print("=" * 100)
        print("%s   [%s]   %s..%s" % (r["rule_id"], r["slot_key"], r["effective_from"] or "-", r["effective_to"] or "-"))
        print("  condition : %s" % r["condition"])
        print("  effect    : %s%s" % (r["effect"], ("   overrides " + r["overrides"]) if r["overrides"] else ""))
        print("  reads     : %s   predicates: %s" % (", ".join(r["requires"]) or "-", ", ".join(r["predicates"]) or "-"))
        if r["note"]:
            print("  note      : %s" % r["note"])
        for p in it["params"]:
            if p["found"]:
                print("  param     : %s = %s %s  <- %s  (%s..%s)" % (p["param_id"], p["value"], p["unit"], p["cite_id"], p["effective_from"] or "-", p["effective_to"] or "-"))
                print("              quote: %s" % p["quote"])
            else:
                print("  param     : %s  NOT FOUND" % p["param_id"])
        for c in it["clauses"]:
            print("  clause    : %s  (%s; %s; %s)%s" % (c["cite_id"], c["doc_type"], c["title"][:60], c["url"], "" if c["found"] else "  NOT FOUND"))
            for line in c["text"].splitlines():
                print("              " + line)
        for d in it["decisions"]:
            print("  decision  : %s <- %s" % (d["id"], d["cite_id"]))
            print("              %s" % d["statement"])
            print("              quote: %s" % d["quote"])
        for pr in it["procedure"]:
            print("  procedure : %s" % json.dumps(pr, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slot")
    ap.add_argument("--date")
    ap.add_argument("--rule")
    ap.add_argument("--variable")
    ap.add_argument("--predicate")
    ap.add_argument("--brief", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--root", default="")
    ap.add_argument("--db", default="")
    a = ap.parse_args()
    if not (a.slot or a.rule or a.variable or a.predicate):
        ap.error("give --slot, --rule, --variable or --predicate")
    tool = RuleTool(Path(a.root) if a.root else ROOT, Path(a.db) if a.db else DB)
    rows = tool.rule_rows(a.slot, a.date, a.rule, a.variable, a.predicate)
    items = [tool.expand(r, a.brief) for r in rows]
    extra = {}
    if a.slot:
        extra["reference_params"] = tool.reference_params(a.slot)
    if a.variable:
        extra["variable"] = tool.variable_row(a.variable)
    if a.predicate:
        extra["predicate"] = tool.predicate_row(a.predicate)
    if a.json:
        print(json.dumps({"query": {k: v for k, v in vars(a).items() if v and k in ("slot", "date", "rule", "variable", "predicate")},
                          "found": len(items), **extra, "rules": items}, ensure_ascii=False, indent=1))
    else:
        print_text(items, extra)
        print("found=%d" % len(items))
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main())
