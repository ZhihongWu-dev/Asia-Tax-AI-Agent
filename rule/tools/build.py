#!/usr/bin/env python
"""Build of the rule layer (rule/规则层规范（最小集）.md §7, §10): parses every condition, checks the five authored
tables against each other and against the library in database/, runs rule_test.csv with the reference evaluator,
reports the slot coverage, writes rule.sqlite and STATUS.md.

Python 3.11, standard library only.   python rule/tools/build.py [--root DIR] [--db DIR]
Run database/tools/build.py first: this build reads database/jurisdiction.csv, doc.csv, param.csv, treaty.csv,
decision.csv and clause.csv.

Authored (in rule/): rule.csv variable.csv predicate.csv decision.csv rule_test.csv   (authored columns only)
Generated: rule.sqlite (the five tables + requires / predicates on rule), STATUS.md
Exit code 0 when no check fails, 1 otherwise. Coverage gaps are reported, not counted as errors.
"""
import argparse
import io
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (AUTHORITATIVE_DOC_TYPES, DATE, EFFECTS, GENERATED, SCHEDULE_INPUTS, Library, SLOTS, SUBJECTS, TABLES,  # noqa: E402
                    VAR_KINDS, VAR_TYPES, WILDCARDS, CondError, leaves, listed_prefixes, param_type,
                    parse_condition, parse_effect, parse_slot_key, read_csv, read_header, split_list, write_csv)
import eval as ev  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT.parent / "database"


def init_csvs(root):
    for name, cols in TABLES.items():
        p = root / (name + ".csv")
        if not p.exists():
            write_csv(p, cols, [])


def norm(s):
    return re.sub(r"\s+", "", s or "")


# ---------------------------------------------------------------- types in conditions (spec §3 rule 3)
def operand_type(x, variables, lib):
    """-> (type, detail). Types: bool, number, text, date, enum; detail = allowed values for enum."""
    if isinstance(x, dict):
        if "var" in x:
            v = variables.get(x["var"])
            if not v:
                return None, None
            return v["type"], split_list(v.get("allowed_values"))
        p = lib.params.get(x["param"])
        return (param_type(p["unit"]) if p else None), None
    if x is True:
        return "bool", None
    if isinstance(x, (int, float)):
        return "number", None
    return ("date" if DATE.match(x) else "text"), x


def compatible(ta, tb):
    a = "text" if ta in ("enum", "date") else ta
    b = "text" if tb in ("enum", "date") else tb
    return a == b


def check_types(tree, rid, variables, lib, errors):
    if not isinstance(tree, dict):
        return
    (k, v), = tree.items()
    if k in ("and", "or"):
        for x in v:
            check_types(x, rid, variables, lib, errors)
    elif k == "not":
        check_types(v, rid, variables, lib, errors)
    elif k == "in":
        ta, allowed = operand_type(v[0], variables, lib)
        for c in v[1]:
            tc, _ = operand_type(c, variables, lib)
            if ta and not compatible(ta, tc):
                errors.append("rule %s: `in` compares %s with a %s constant %r" % (rid, ta, tc, c))
            if ta == "enum" and c not in allowed:
                errors.append("rule %s: %r is not an allowed value of the enum (%s)" % (rid, c, "; ".join(allowed)))
    elif k == "listed":
        ta, _ = operand_type(v[1], variables, lib)
        if ta and ta not in ("text", "enum"):
            errors.append("rule %s: listed() needs a text or enum variable, %s is %s" % (rid, v[1]["var"], ta))
    elif k in ("=", "!=", "<", "<=", ">", ">="):
        ta, da = operand_type(v[0], variables, lib)
        tb, db = operand_type(v[1], variables, lib)
        if ta and tb and not compatible(ta, tb):
            errors.append("rule %s: comparison of %s with %s" % (rid, ta, tb))
        if k in ("<", "<=", ">", ">=") and ta and ta not in ("number", "date"):
            errors.append("rule %s: ordering operator %s on %s" % (rid, k, ta))
        for t, d, other in ((ta, da, v[1]), (tb, db, v[0])):
            if t == "enum" and isinstance(other, str) and other not in d:
                errors.append("rule %s: %r is not an allowed value of the enum (%s)" % (rid, other, "; ".join(d)))


# ---------------------------------------------------------------- checks (spec §7)
def check_variables(variables, errors):
    seen = set()
    for v in variables:
        n = v.get("name") or ""
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", n):
            errors.append("variable %r: name must be lowercase letters, digits and _" % n)
        if n in seen:
            errors.append("variable %s: duplicate name" % n)
        seen.add(n)
        if v.get("kind") not in VAR_KINDS:
            errors.append("variable %s: kind %r not in %s" % (n, v.get("kind"), "/".join(VAR_KINDS)))
        if v.get("type") not in VAR_TYPES:
            errors.append("variable %s: type %r not in %s" % (n, v.get("type"), "/".join(VAR_TYPES)))
        if v.get("type") == "enum" and not split_list(v.get("allowed_values")):
            errors.append("variable %s: enum without allowed_values" % n)
        if not (v.get("question") or "").strip():
            errors.append("variable %s: question empty" % n)
        if not (v.get("meaning") or "").strip():
            errors.append("variable %s: meaning empty" % n)
        if v.get("kind") == "derived" and not split_list(v.get("inputs")):
            errors.append("variable %s: derived variable without inputs" % n)
        if v.get("kind") != "derived" and split_list(v.get("inputs")):
            errors.append("variable %s: only derived variables have inputs" % n)
    names = {v["name"] for v in variables}
    for v in variables:
        for i in split_list(v.get("inputs")):
            if i not in names:
                errors.append("variable %s: input %s is not a variable" % (v["name"], i))


def check_predicates(predicates, clause_ids, variables, errors):
    seen = set()
    for p in predicates:
        k = p.get("key") or ""
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", k):
            errors.append("predicate %r: key must be lowercase letters, digits and _" % k)
        if k in seen:
            errors.append("predicate %s: duplicate key" % k)
        seen.add(k)
        if not (p.get("question") or "").strip():
            errors.append("predicate %s: question empty" % k)
        if p.get("favourable") not in ("yes", "no"):
            errors.append("predicate %s: favourable must be yes or no" % k)
        cites = split_list(p.get("factors_cite"))
        if not cites:
            errors.append("predicate %s: factors_cite empty" % k)
        for c in cites:
            if c not in clause_ids:
                errors.append("predicate %s: factors_cite %s not in clause" % (k, c))
        for v in split_list(p.get("factor_vars")):
            if v not in variables:
                errors.append("predicate %s: factor_vars %s is not a variable" % (k, v))


def check_decisions(decisions, lib, errors):
    for d in decisions:
        did = d.get("id") or ""
        if not re.fullmatch(r"D-[a-z]{2}(-[a-z]{2})?-\d+", did):
            errors.append("decision %r: id must be D-<jur or pair>-<n>" % did)
        if not (d.get("statement") or "").strip():
            errors.append("decision %s: statement empty" % did)
        cid = d.get("cite_id") or ""
        if cid not in lib.clause_text:
            errors.append("decision %s: cite_id %s not in clause" % (did, cid))
        elif not (d.get("quote") or "").strip():
            errors.append("decision %s: quote empty" % did)
        elif norm(d["quote"]) not in norm(lib.clause_text[cid]):
            errors.append("decision %s: quote not found verbatim in %s" % (did, cid))


def dates_intersect(a_from, a_to, b_from, b_to):
    start = max([x for x in (a_from, b_from) if x] or [""])
    ends = [x for x in (a_to, b_to) if x]
    return not ends or start <= min(ends)


def check_rules(rules, lib, variables, predicates, decision_ids, errors):
    """Parses conditions, fills requires / predicates (in memory), checks every reference and constraint."""
    var_names = set(variables)
    pred_keys = set(predicates)
    by_id = {}
    for r in rules:
        rid = r.get("rule_id") or ""
        if not re.fullmatch(r"[a-z]{2}(-[a-z]{2})?\.[a-z_]+\.[a-z0-9_.]+", rid):
            errors.append("rule %r: rule_id must be <jur or pair>.<slot>.<name>" % rid)
        if rid in by_id:
            errors.append("rule %s: duplicate rule_id" % rid)
        by_id[rid] = r
        r["requires"], r["predicates"], r["_tree"], r["_parts"] = "", "", None, None
        parts = parse_slot_key(r.get("slot_key"))
        if not parts:
            errors.append("rule %s: slot_key must be jurisdiction|subject|slot|flow" % rid)
            continue
        jur, subj, slot, flow = parts
        r["_parts"] = parts
        if jur not in lib.codes:
            errors.append("rule %s: slot_key jurisdiction %r unknown" % (rid, jur))
        if subj not in SUBJECTS:
            errors.append("rule %s: slot_key subject %r not in %s" % (rid, subj, "/".join(SUBJECTS)))
        if slot not in SLOTS:
            errors.append("rule %s: slot_key slot %r not in %s" % (rid, slot, "/".join(SLOTS)))
        if flow != "*":
            if flow not in lib.codes:
                errors.append("rule %s: slot_key flow %r is not a jurisdiction code or *" % (rid, flow))
            elif not lib.treaty(jur, flow):
                errors.append("rule %s: no treaty row with a text for the pair %s-%s in treaty.csv" % (rid, jur, flow))
            if not rid.startswith("%s-%s." % (jur, flow)) and not rid.startswith("%s-%s." % (flow, jur)):
                errors.append("rule %s: a treaty rule's id must start with the pair" % rid)
        try:
            tree = parse_condition(r.get("condition"))
        except CondError as e:
            errors.append("rule %s: condition: %s" % (rid, e))
            continue
        r["_tree"] = tree
        need, preds, used = leaves(tree, "var"), leaves(tree, "pred"), leaves(tree, "param")
        if parse_effect(r.get("effect"))[0] == "schedule":          # a schedule reads its inputs besides the condition
            need = need + [v for v in SCHEDULE_INPUTS if v not in need]
        r["requires"], r["predicates"] = ";".join(need), ";".join(preds)
        for v in need:
            if v not in var_names:
                errors.append("rule %s: variable %s not in variable" % (rid, v))
        for k in preds:
            if k not in pred_keys:
                errors.append("rule %s: predicate %s not in predicate" % (rid, k))
        for p in used:
            if p not in lib.params:
                errors.append("rule %s: parameter $%s not in param" % (rid, p))
        for prefix in listed_prefixes(tree):
            if not any(pid.startswith(prefix + "_") for pid in lib.params):
                errors.append("rule %s: listed(%s, ..) names no parameter prefix in param" % (rid, prefix))
        check_types(tree, rid, variables, lib, errors)

        eff, param = parse_effect(r.get("effect"))
        if eff not in EFFECTS:
            errors.append("rule %s: effect %r not in the vocabulary (%s)" % (rid, eff, ", ".join(EFFECTS)))
        else:
            slots, takes_param, _ = EFFECTS[eff]
            if slot not in slots:
                errors.append("rule %s: effect %s is not allowed in slot %s" % (rid, eff, slot))
            if takes_param and not param:
                errors.append("rule %s: effect %s needs a parameter (%s:<param_id>)" % (rid, eff, eff))
            if not takes_param and param:
                errors.append("rule %s: effect %s takes no parameter" % (rid, eff))
            if param:
                p = lib.params.get(param)
                if not p:
                    errors.append("rule %s: effect parameter %s not in param" % (rid, param))
                else:
                    if p["slot"] != slot and not (eff == "schedule" and p["slot"] == "final"):   # one progressive table per jurisdiction and subject
                        errors.append("rule %s: effect parameter %s has slot %s, the rule is in %s" % (rid, param, p["slot"], slot))
                    if param_type(p["unit"]) != "number":
                        errors.append("rule %s: effect parameter %s is not a number (unit %s)" % (rid, param, p["unit"]))
        overrides = split_list(r.get("overrides"))
        if eff == "deny" and not overrides:
            errors.append("rule %s: deny without overrides" % rid)
        if eff != "deny" and overrides:
            errors.append("rule %s: only deny has overrides" % rid)
        cites = split_list(r.get("cite_ids"))
        if not cites:
            errors.append("rule %s: cite_ids empty" % rid)
        kinds = set()
        for c in cites:
            if c not in lib.clause_text:
                errors.append("rule %s: cite_id %s not in clause" % (rid, c))
            else:
                doc = lib.docs.get(c.split("#", 1)[0], {})
                kinds.add(doc.get("type"))
        if cites and not kinds & set(AUTHORITATIVE_DOC_TYPES):
            errors.append("rule %s: no cite from a law, regulation or treaty" % rid)
        for d in split_list(r.get("decision_ids")):
            if d not in decision_ids:
                errors.append("rule %s: decision %s not in decision" % (rid, d))
        proc = (r.get("procedure") or "").strip()
        for e in split_list(proc):
            if e not in lib.docs and e not in lib.absence_ids_cat7 and e not in lib.clause_text:
                errors.append("rule %s: procedure %s is neither a doc, a clause nor a category-7 absence record" % (rid, e))
        if eff == "cap" and preds and not proc:
            errors.append("rule %s: a treaty cap that depends on a predicate needs a procedure" % rid)
        for col in ("effective_from", "effective_to"):
            if r.get(col) and not DATE.match(r[col]):
                errors.append("rule %s: %s is not YYYY-MM-DD" % (rid, col))
        for pid in ([param] if param else []) + used:
            p = lib.params.get(pid)
            if p and not dates_intersect(r.get("effective_from"), r.get("effective_to"),
                                         p.get("effective_from"), p.get("effective_to")):
                errors.append("rule %s: its dates never overlap the effective period of %s" % (rid, pid))
    for rid, r in by_id.items():
        if not r.get("_parts") or parse_effect(r.get("effect"))[0] != "deny":
            continue
        jur, subj, slot, flow = r["_parts"]
        for o in split_list(r.get("overrides")):
            if o.endswith(":*"):
                if o[:-2] not in WILDCARDS:
                    errors.append("rule %s: overrides %s is not one of %s" % (rid, o, ", ".join(w + ":*" for w in WILDCARDS)))
                continue
            t = by_id.get(o)
            if not t:
                errors.append("rule %s: overrides %s is not a rule" % (rid, o))
                continue
            tp = t.get("_parts")
            if tp and (tp[0] != jur or (flow != "*" and tp[3] not in (flow, "*"))):
                errors.append("rule %s: overrides %s belongs to another jurisdiction or flow" % (rid, o))
    return by_id


def check_tests(tests, by_id, variables, predicates, errors):
    for t in tests:
        tid = t.get("test_id") or ""
        rid = tid.rsplit(".", 1)[0]
        if rid not in by_id:
            errors.append("rule_test %s: rule %s not found" % (tid, rid))
        if not parse_slot_key(t.get("slot_key")):
            errors.append("rule_test %s: slot_key must have four parts" % tid)
        if not DATE.match(t.get("date") or ""):
            errors.append("rule_test %s: date is not YYYY-MM-DD" % tid)
        for k in ev.parse_kv(t.get("facts")):
            if k != "mode" and k not in variables:
                errors.append("rule_test %s: fact %s is not a variable" % (tid, k))
        for k, v in ev.parse_kv(t.get("answers")).items():
            if k not in predicates:
                errors.append("rule_test %s: answer %s is not a predicate" % (tid, k))
            if v not in ("yes", "no", "unknown"):
                errors.append("rule_test %s: answer %s=%s is not yes/no/unknown" % (tid, k, v))
        if len((t.get("expect") or "").split()) != 3:
            errors.append("rule_test %s: expect must be '<effect> <value> <status>'" % tid)
        if not (t.get("source") or "").strip():
            errors.append("rule_test %s: source empty (a cite_id or authored)" % tid)


def rules_needing_tests(by_id, tests):
    """Conditioned rules (reading a variable or predicate) without a T, F and U test (spec §2.6)."""
    have = {}
    for t in tests:
        rid = t["test_id"].rsplit(".", 1)[0]
        parts = (t.get("expect") or "").split()
        if len(parts) == 3:
            have.setdefault(rid, set()).add(parts[2][:1])
    out = []
    for rid, r in by_id.items():
        if r.get("_tree") in (None, True) or (not r["requires"] and not r["predicates"]):   # `true` rules cannot be F or U
            continue
        missing = [s for s in "TFU" if s not in have.get(rid, set())]
        if missing:
            out.append("%s (missing %s)" % (rid, "/".join(missing)))
    return out


def coverage(by_id, lib):
    covered = set()
    for r in by_id.values():
        if r.get("_parts"):
            jur, subj, slot, _ = r["_parts"]
            for s in (("company", "individual") if subj == "all" else (subj,)):
                covered.add((jur, s, slot))
    for a in lib.absences:
        if a.get("subject") and a.get("slot"):
            for s in (("company", "individual") if a["subject"] == "all" else (a["subject"],)):
                covered.add((a["jur"], s, a["slot"]))
    gaps = []
    for j in lib.juris:
        for s, col in (("company", "company_in_scope"), ("individual", "individual_in_scope")):
            if (j.get(col) or "yes").lower() not in ("yes", "y", "1", "true"):
                continue
            for slot in SLOTS:
                if (j["code"], s, slot) not in covered:
                    gaps.append("%s|%s|%s" % (j["code"], s, slot))
    return gaps


# ---------------------------------------------------------------- outputs
def write_sqlite(root, tables):
    db = root / "rule.sqlite"
    if db.exists():
        db.unlink()
    con = sqlite3.connect(str(db))
    for name, cols in TABLES.items():
        allcols = cols + GENERATED.get(name, [])
        con.execute("CREATE TABLE %s (%s)" % (name, ", ".join('"%s" TEXT' % c for c in allcols)))
        data = []
        for r in tables[name]:
            vals = []
            for c in allcols:
                v = r.get(c, "")
                if name == "rule" and c in ("requires", "predicates", "cite_ids", "decision_ids", "overrides"):
                    v = json.dumps(split_list(v), ensure_ascii=False)       # JSON arrays: json_each() finds rules by variable
                vals.append(str(v if v is not None else ""))
            data.append(vals)
        con.executemany("INSERT INTO %s VALUES (%s)" % (name, ",".join("?" * len(allcols))), data)
    con.execute("CREATE INDEX ix_rule_slot_key ON rule(slot_key)")
    con.execute("CREATE INDEX ix_test_rule ON rule_test(test_id)")
    con.commit()
    con.close()


def write_status(root, tables, errors, gaps, untested, test_failures, lib):
    rules = tables["rule"]
    per_jur = Counter(r["slot_key"].split("|")[0] for r in rules if r.get("slot_key"))
    L = ["# STATUS", "", "Written by `rule/tools/build.py` at every build; do not edit.", "",
         "| What | Count |", "|---|---|",
         "| Rules | %d |" % len(rules),
         "| Variables / predicates | %d / %d |" % (len(tables["variable"]), len(tables["predicate"])),
         "| Interpretation decisions (rows) | %d |" % len(tables["decision"]),
         "| Golden tests (passed / total) | %d / %d |" % (len(tables["rule_test"]) - len(test_failures), len(tables["rule_test"])),
         "| Errors | %d |" % len(errors),
         "| Coverage gaps (jurisdiction, subject, slot) | %d |" % len(gaps),
         "| Conditioned rules without a T, F and U test | %d |" % len(untested),
         "", "## Rules by jurisdiction", "", "| Jurisdiction | Rules |", "|---|---|"]
    L += ["| %s | %d |" % (j["code"], per_jur.get(j["code"], 0)) for j in lib.juris]
    L += ["", "## Errors", ""] + (["- " + x for x in errors] or ["None."])
    L += ["", "## Golden tests", ""] + (["- " + x for x in test_failures] or ["All passed."])
    L += ["", "## Coverage", "", "Cells jurisdiction | subject | slot with neither a rule nor an absence record in database/decision.csv:", ""]
    L += ["- " + g for g in gaps] or ["None."]
    L += ["", "## Conditioned rules without a T, F and U test", ""] + (["- " + x for x in untested] or ["None."])
    L += ["", "## sqlite", "", "`rule.sqlite`: tables rule, variable, predicate, decision, rule_test; on rule the generated "
          "columns requires and predicates, and the list columns cite_ids, decision_ids, overrides, as JSON arrays "
          "(`SELECT rule_id FROM rule, json_each(rule.requires) WHERE json_each.value = 'holding_pct'`)."]
    (root / "STATUS.md").write_text("\n".join(L) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="", help="rule folder (default: rule/)")
    ap.add_argument("--db", default="", help="library folder that is read (default: database/)")
    args = ap.parse_args()
    root = Path(args.root).resolve() if args.root else ROOT
    db = Path(args.db).resolve() if args.db else DB
    if not (db / "clause.csv").exists():
        print("! %s has no clause.csv: run database/tools/build.py first" % db)
        return 1
    init_csvs(root)
    errors = []
    tables = {name: read_csv(root / (name + ".csv")) for name in TABLES}
    for name, cols in TABLES.items():
        header = read_header(root / (name + ".csv"))
        missing = [c for c in cols if c not in header]
        extra = [c for c in header if c not in cols]
        if missing:
            errors.append("%s.csv: columns missing: %s" % (name, ", ".join(missing)))
        if extra:
            errors.append("%s.csv: columns not in the spec (generated columns go to sqlite only): %s" % (name, ", ".join(extra)))
    lib = Library(db, with_clauses=True)
    lib.absence_ids_cat7 = {a["id"] for a in lib.absences if (a.get("category") or "").strip() == "7"}

    variables = {v["name"]: v for v in tables["variable"]}
    predicates = {p["key"]: p for p in tables["predicate"]}
    check_variables(tables["variable"], errors)
    check_predicates(tables["predicate"], set(lib.clause_text), variables, errors)
    check_decisions(tables["decision"], lib, errors)
    by_id = check_rules(tables["rule"], lib, variables, predicates, {d["id"] for d in tables["decision"]}, errors)
    read_vars = {v for r in by_id.values() for v in split_list(r.get("requires"))}
    read_vars |= {i for v in tables["variable"] if v["kind"] == "derived" for i in split_list(v.get("inputs"))}
    read_vars |= {f for p in tables["predicate"] for f in split_list(p.get("factor_vars"))}   # judgment factors count as read
    for v in tables["variable"]:
        if v["name"] not in read_vars and v["kind"] != "derived":
            errors.append("variable %s: no rule reads it" % v["name"])
    derived_used = {v for r in by_id.values() for v in split_list(r.get("requires"))}
    for v in tables["variable"]:
        if v["kind"] == "derived" and v["name"] not in derived_used:
            errors.append("variable %s: no rule reads it" % v["name"])
    check_tests(tables["rule_test"], by_id, variables, predicates, errors)

    test_failures = []
    if not errors:
        rs = ev.RuleSet(root, db, lib=lib)
        for t in tables["rule_test"]:
            try:
                fail = ev.run_test(rs, t)
            except Exception as e:                        # a crash in the evaluator is a failed test, not a crashed build
                fail = "%s: %s" % (type(e).__name__, e)
            if fail:
                test_failures.append("%s: %s" % (t["test_id"], fail))
        errors += ["rule_test " + x for x in test_failures]
    untested = rules_needing_tests(by_id, tables["rule_test"])
    errors += ["rule %s has no complete golden test set" % x for x in untested]
    gaps = coverage(by_id, lib)

    write_sqlite(root, tables)
    write_status(root, tables, errors, gaps, untested, test_failures, lib)
    print("rules=%d variables=%d predicates=%d decisions=%d tests=%d failed=%d errors=%d coverage_gaps=%d" % (
        len(tables["rule"]), len(tables["variable"]), len(tables["predicate"]), len(tables["decision"]),
        len(tables["rule_test"]), len(test_failures), len(errors), len(gaps)))
    for x in errors:
        print("  ! " + x)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main())
