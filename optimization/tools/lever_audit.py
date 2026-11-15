#!/usr/bin/env python
"""Lever audit (2026-11-12, optimization spec §4.7a): the facts that switch a favourable effect on in the rule layer and that no
move of move.csv sets, so the search never tries changing them. The list is for whoever extends the move vocabulary; a
variable on it may well be a fact no client can change (a residence, a listing): that is for a person to judge, not this tool.

  python optimization/tools/lever_audit.py [--out <file.md>]

Reads rule/rule.csv, rule/variable.csv and optimization/move.csv only; no library, no network."""
import argparse
import io
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "rule" / "tools"))
from common import read_csv, split_list  # noqa: E402

FAVOURABLE = ("cap", "exempt", "share", "exclude", "credit", "credit_underlying")
# facts the optimizer derives itself from the path or the holding chain (optimization spec §4.1, §4.7): not levers
DERIVED_BY_OPTIMIZER = {"payer_income_taxed", "payer_tax_rate", "tiers", "owner_safe_harbour", "passes_on_within_12m",
                        "future_cn_tax_not_reduced", "amount_payee_ccy", "payee_resident", "payer_resident", "overdue_months",
                        "parent_treaty_not_worse", "group_relation_pct"}
WORD = re.compile(r"(?<![$\w.])([a-z_][a-z0-9_]*)(?![\w(])")
KEYWORDS = {"and", "or", "not", "true", "false", "in", "pred", "listed"}


def condition_vars(cond):
    """The fact variables a condition reads: bare names, not $parameters, predicates or literals."""
    text = re.sub(r"'[^']*'", " ", cond or "")
    text = re.sub(r"\$[\w.\-]+", " ", text)
    text = re.sub(r"pred\(\w+\)", " ", text)
    return {m.group(1) for m in WORD.finditer(text) if m.group(1) not in KEYWORDS}


def audit():
    variables = {v["name"]: v for v in read_csv(ROOT / "rule" / "variable.csv")}
    moves = read_csv(HERE.parent / "move.csv")
    set_by_move = {}
    for m in moves:
        for kv in split_list(m.get("sets")):
            set_by_move.setdefault(kv.partition("=")[0].strip(), []).append(m["move_id"])
    uses = defaultdict(list)
    for r in read_csv(ROOT / "rule" / "rule.csv"):
        eff = (r.get("effect") or "").split(":")[0]
        if eff not in FAVOURABLE:
            continue
        for v in condition_vars(r.get("condition")):
            uses[v].append((r["rule_id"], eff, r["slot_key"].split("|")[0]))
    rows = []
    for v, rs in sorted(uses.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        meta = variables.get(v)
        if not meta or meta.get("kind") == "derived" or v in DERIVED_BY_OPTIMIZER:
            continue
        rows.append({"variable": v, "kind": meta.get("kind"), "question": meta.get("question"), "rules": rs,
                     "set_by": set_by_move.get(v, [])})
    return rows


def render(rows):
    out = ["# Lever audit", "",
           "Facts that switch a favourable effect on (cap, exempt, share, exclude, credit) in rule/rule.csv. `set by` names the "
           "moves of optimization/move.csv that change the fact; an empty cell means the search never tries another value. "
           "Whether a client could change the fact is for a person to judge.", "",
           "| Variable | Kind | Rules | Jurisdictions | Effects | Set by | Question |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        jurs = sorted({j for _, _, j in r["rules"]})
        effs = sorted({e for _, e, _ in r["rules"]})
        out.append("| %s | %s | %d | %s | %s | %s | %s |" % (r["variable"], r["kind"], len(r["rules"]), ", ".join(jurs), ", ".join(effs),
                                                           ", ".join(r["set_by"]) or "—", (r["question"] or "").replace("|", "/")))
    gaps = [r for r in rows if not r["set_by"]]
    out += ["", "%d variables, %d set by no move." % (len(rows), len(gaps))]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", help="write the table to this file instead of stdout")
    a = ap.parse_args()
    text = render(audit())
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print("written %s" % a.out)
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        print(text)


if __name__ == "__main__":
    main()
