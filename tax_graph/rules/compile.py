"""compile(): turn a spec into rule objects, checking every reference against official/ (规则层.md §4).

    RULES = compile_rules(SPEC, Params())          # raises CompileError listing every failed check

Checks that stop: referenced param / observed-rule / clause ids exist; a numeric value occurs in its quote
(Chinese numerals normalised); the validity interval is not empty; a grade-B rule has a grade-A rule of the same
scope and effect; two non-commuting rules on one scope are linked by overrides; every anti-abuse parameter in
the spec's scopes is referenced. Reported only: rate / condition parameters in scope that no rule reads.
"""
import csv
import io
import re
import sqlite3
import sys
from dataclasses import replace
from datetime import date

from ..params import OFFICIAL, NUMERIC
from .model import (ALL, NON_COMMUTING, PROCEDURE, Discretion, Effect, Grade, Leaf, RuleObj, leaves)


from . import procedure_cn, procedure_hk, procedure_sg

PROCEDURE_MODULES = (procedure_cn, procedure_hk, procedure_sg)
EVALUATOR_READS = {k: v for m in PROCEDURE_MODULES for k, v in m.READS.items()}


class CompileError(Exception):
    pass


CN_DIGITS = "零一二三四五六七八九"


def cn_numeral(n):
    """Chinese numeral for 0 <= n < 1000, as written in statutes (十五, 二十五, 一百); larger numbers are written in digits."""
    if n >= 1000:
        return ""
    if n < 10:
        return CN_DIGITS[n]
    if n < 20:
        return "十" + (CN_DIGITS[n % 10] if n % 10 else "")
    if n < 100:
        return CN_DIGITS[n // 10] + "十" + (CN_DIGITS[n % 10] if n % 10 else "")
    h, r = CN_DIGITS[n // 100] + "百", n % 100
    if r == 0:
        return h
    if r < 10:
        return h + "零" + CN_DIGITS[r]
    return h + ("一" if r < 20 else "") + cn_numeral(r)


FULLWIDTH = str.maketrans("０１２３４５６７８９％：", "0123456789%:")


def value_in_quote(value, quote, unit=""):
    q = re.sub(r"\s+", "", (quote or "").translate(FULLWIDTH))
    v = float(value)
    cands = {str(value), ("%g" % v)}
    if v == int(v):
        n = int(v)
        cands |= {str(n), cn_numeral(n)}
        cands.add("{:,}".format(n))                                  # $2,000,000
        if n % 1000000 == 0:
            cands.add("%d million" % (n // 1000000))                 # $400 million
        for scale, word in ((10000, "万"), (100000000, "亿")):   # 500万元 = 5,000,000; 2亿元 = 200,000,000
            if n % scale == 0 and n // scale < 100000:
                cands.add("%d%s" % (n // scale, word))
                if n // scale < 1000:
                    cands.add(cn_numeral(n // scale) + word)
    if unit == "%":                                                 # 万分之五 = 0.05%
        if v == 50:
            cands.add("减半")                                         # 减半征收: half the tax
        frac = v / 100.0
        for scale, word in ((100, "百分之"), (1000, "千分之"), (10000, "万分之")):
            if 0 < frac and abs(frac * scale - round(frac * scale)) < 1e-9 and round(frac * scale) < 1000:
                cands.add(word + cn_numeral(int(round(frac * scale))))
    return any(c and re.sub(r"\s+", "", c) in q for c in cands)      # the quote was de-spaced above


def to_date(s):
    return date.fromisoformat(s) if s else None


def load_observed():
    p = OFFICIAL / "labels" / "observed_rules.csv"
    if not p.exists():
        return {}
    with p.open(encoding="utf-8-sig", newline="") as f:
        return {r["rule_id"]: r for r in csv.DictReader(f)}


def load_clause_ids():
    db = OFFICIAL / "official.sqlite"
    if db.exists():
        con = sqlite3.connect(str(db))
        ids = {r[0] for r in con.execute("SELECT cite_id FROM clause")}
        con.close()
        return ids
    csv.field_size_limit(10 ** 9)
    with (OFFICIAL / "clauses.csv").open(encoding="utf-8-sig", newline="") as f:
        return {r["cite_id"] for r in csv.DictReader(f)}


def scope_keys(scope):
    """Scope strings as params.csv writes them. A source-side spec covers the source jurisdiction's domestic
    parameters and the pair's treaty parameters, not the residence jurisdiction's domestic law."""
    keys = {scope.source}
    if scope.residence:
        a, b = sorted([scope.source, scope.residence])
        keys.add("pair(%s,%s)" % (a, b))
    return keys


def param_refs(r):
    refs = []
    if r.value and not r.value.startswith("observed:"):
        refs.append(r.value)
    refs += [x.param for x in leaves(r.cond) if isinstance(x, Leaf) and x.param]
    for alt in r.readings:
        refs += [x.param for x in leaves(alt) if isinstance(x, Leaf) and x.param]
    refs += list(r.uses)
    return refs


def compile_rules(spec, P, report=None):
    observed, clause_ids = load_observed(), load_clause_ids()
    errors, out, covered = [], [], {}        # scope key -> incomes the spec covers there
    by_scope_effect = {}
    for r in spec:
        for k in scope_keys(r.scope):
            covered.setdefault(k, set())
            if r.scope.income != ALL:          # ALL-income rules do not by themselves claim an income type
                covered[k] |= set(r.scope.income) if isinstance(r.scope.income, tuple) else {r.scope.income}
        refs = param_refs(r)
        sources, froms, tos = [], [], []
        for pid in refs:
            if pid not in P.rows:
                errors.append("%s: parameter not in params.csv: %s" % (r.id, pid))
                continue
            row = P.rows[pid]
            sources.append(pid)
            if row["unit"] in NUMERIC and not value_in_quote(row["value"], row["quote"], row["unit"]):
                errors.append("%s: value %s of %s does not occur in its quote" % (r.id, row["value"], pid))
            if pid not in r.uses:                # ancillary (procedure) parameters do not bound the rule's validity
                froms.append(to_date(row["effective_from"]))
                tos.append(to_date(row["effective_to"]))
        if r.value and r.value.startswith("observed:"):
            oid = r.value.split(":", 1)[1]
            if oid not in observed:
                errors.append("%s: observed rule not in observed_rules.csv: %s" % (r.id, oid))
            sources.append(r.value)
        for x in leaves(r.cond):
            if isinstance(x, Leaf) and x.pred.needs_param and not x.param:
                errors.append("%s: predicate %s on %s needs a parameter" % (r.id, x.pred.name, x.field))
            if isinstance(x, Discretion):
                for c in x.cites:
                    if c not in clause_ids:
                        errors.append("%s: clause not in library: %s" % (r.id, c))
                sources += list(x.cites)
        if r.before:                                      # 口径 D30: the clause that says from when its law applies
            if r.before[1] not in clause_ids:
                errors.append("%s: clause not in library: %s" % (r.id, r.before[1]))
            sources.append(r.before[1])
        valid_from = max([d for d in froms if d], default=None)
        valid_to = min([d for d in tos if d], default=None)
        if valid_from and valid_to and valid_from > valid_to:          # effective_to is the last day in force
            errors.append("%s: empty validity interval %s..%s" % (r.id, valid_from, valid_to))
        if r.effect in (Effect.CHARGE, Effect.DENY, Effect.PENALTY, Effect.STAMP, Effect.DEDUCT_BASE) or (
                r.effect is Effect.VAT and ".input_credit" not in r.id):   # a levy, a cut deduction, VAT borne: against the taxpayer
            favourable = False                                            # DEDUCTION, NOCHARGE, the payer's input credit: for it
        elif r.effect is Effect.BASE:                 # a fraction below 100% lowers the tax; computed fractions are reliefs too
            row = P.rows.get(r.value)
            favourable = row is None or row["unit"] != "%" or float(row["value"]) < 100
        else:
            favourable = True
        if any(isinstance(x, Discretion) for x in leaves(r.cond)):
            grade = Grade.D_DISCRETION
        elif r.readings:
            grade = Grade.C_READING
        elif r.value and r.value.startswith("observed:"):
            grade = Grade.B_PRACTICE
        else:
            grade = Grade.A_TEXT
        reads = frozenset("%s.%s" % (x.on, x.field) for x in leaves(r.cond) if isinstance(x, Leaf)) | frozenset(EVALUATOR_READS.get(r.id, ()))
        out.append(replace(r, reads=reads, favourable=favourable, grade=grade, sources=tuple(sources),
                           valid=(valid_from, valid_to)))
        by_scope_effect.setdefault((r.scope, r.effect), []).append(r)

    ids = {r.id for r in out}
    for r in out:
        for o in r.overrides:
            if o not in ids:
                errors.append("%s: overrides unknown rule %s" % (r.id, o))
        if r.grade is Grade.B_PRACTICE:
            if not any(x.grade is Grade.A_TEXT for x in out if (x.scope, x.effect) == (r.scope, r.effect)):
                errors.append("%s: grade-B rule without a grade-A rule of the same scope and effect" % r.id)
    for (scope, effect), rs in by_scope_effect.items():
        if effect in NON_COMMUTING and len(rs) > 1:
            for i, a in enumerate(rs):
                for b in rs[i + 1:]:
                    if b.id not in a.overrides and a.id not in b.overrides:
                        errors.append("%s and %s: same scope and effect %s without overrides" % (a.id, b.id, effect.name))
    referenced = {s for r in out for s in r.sources}

    def in_scope(row):
        incomes = covered.get(row["scope"])
        return incomes is not None and (row["income"] == ALL or row["income"] in incomes)

    for pid, row in P.rows.items():
        if in_scope(row) and row["topic"] == "anti_abuse" and pid not in referenced:
            errors.append("anti-abuse parameter not referenced by any rule: %s" % pid)
    orphans = [pid for pid, row in P.rows.items()
               if in_scope(row) and row["topic"] in ("rate", "condition") and pid not in referenced]
    if report is not None:
        report.extend(orphans)
    check_registry(out, P, clause_ids, errors)
    if errors:
        raise CompileError("\n".join(errors))
    return out


def check_registry(rules, P, clause_ids, errors):
    """Every evaluator sits in its jurisdiction's module and names the clauses it implements: a registration must
    reach a rule of the spec (by id, by an observed value, or by the text value of its parameter) whose region holds
    the module's jurisdiction, with the effect it is registered under; each clause must be in the library; a rule whose
    effect needs an evaluator (PENALTY, DEDUCT_BASE, a BASE without a parameter) must have one; no key twice."""
    from ..regions import rule_region
    by_key = {}
    for r in rules:
        by_key.setdefault(r.id, []).append(r)
        if r.value:
            by_key.setdefault(r.value, []).append(r)
            row = P.rows.get(r.value)
            if row is not None and row["unit"] not in NUMERIC:
                by_key.setdefault(row["value"], []).append(r)
    seen = {}
    for m in PROCEDURE_MODULES:
        for key, (effect, _ev, cites) in m.REGISTRY.items():
            if key in seen:
                errors.append("evaluator for %s registered twice (%s, %s)" % (key, seen[key], m.JUR))
            seen[key] = m.JUR
            targets = by_key.get(key, [])
            if not targets:
                errors.append("%s evaluator registered for no rule: %s" % (m.JUR, key))
            for r in targets:
                if m.JUR not in rule_region(r):
                    errors.append("%s evaluator registered for %s, a rule of %s" % (m.JUR, r.id, "/".join(sorted(rule_region(r)))))
                if r.effect.name != effect:
                    errors.append("%s: evaluator registered as %s for a %s rule" % (key, effect, r.effect.name))
            if not cites:
                errors.append("%s: evaluator names no clause" % key)
            for c in cites:
                if c not in clause_ids:
                    errors.append("%s: evaluator cites a clause not in the library: %s" % (key, c))
    reached = {r.id for key in seen for r in by_key.get(key, [])}
    for r in rules:
        if (r.effect in (Effect.PENALTY, Effect.DEDUCT_BASE) or (r.effect is Effect.BASE and r.value is None)) and r.id not in reached:
            errors.append("%s: a %s rule without an evaluator" % (r.id, r.effect.name))


from ..model import JURISDICTIONS
INCOMES = ("DIVIDEND", "INTEREST", "ROYALTY", "SERVICE_FEE", "SHARE_TRANSFER", "LIQUIDATION", "CAPITAL_REDUCTION", "IP_TRANSFER")


def coverage(rules):
    """场景.md §3: for every (jurisdiction, side, income) cell, the CHARGE rules, a NOCHARGE declaration, or nothing.
    Returns {cell: ("CHARGE", [ids]) | ("NOCHARGE", [ids]) | ("MISSING", [])}."""
    cells = {}
    for jur in JURISDICTIONS:
        for side in ("source", "residence"):
            for inc in INCOMES:
                charge, no, split = [], [], []
                for r in rules:
                    if r.effect not in (Effect.CHARGE, Effect.NOCHARGE, Effect.SPLIT) or not r.scope.covers(inc):
                        continue
                    if r.effect is Effect.SPLIT:                             # a decomposition holds on every side
                        split.append(r.id)
                        continue
                    if r.scope.taxing not in (jur, ALL):
                        continue
                    rule_side = "residence" if r.scope.side == "residence" else "source"   # a named jurisdiction acts as source
                    if rule_side != side:
                        continue
                    (charge if r.effect is Effect.CHARGE else no).append(r.id)
                if split:
                    cells[(jur, side, inc)] = ("SPLIT", split)
                else:
                    cells[(jur, side, inc)] = ("CHARGE", charge) if charge else (("NOCHARGE", no) if no else ("MISSING", []))
    return cells


def dump(rules, out=None):
    out = out or io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    for r in rules:
        out.write("%-32s %-9s %-13s %-12s %s..%s  reads=%s\n" % (
            r.id, r.effect.name, r.grade.name, r.scope.source + ("->" + r.scope.residence if r.scope.residence else ""),
            r.valid[0] or "", r.valid[1] or "", ",".join(sorted(r.reads)) or "-"))
    out.flush()
