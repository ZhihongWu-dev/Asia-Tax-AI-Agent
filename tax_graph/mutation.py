"""mutation (优化方案 v2 item 10; J12): how many plausible mistakes in the rule layer the battery would notice — the
adequacy measure that replaces "rules fired".

    python -m tax_graph.mutation [--ops NEG,DROP,PRED,SHIFT] [--limit N] [--jobs N]

Operators, one mutant each:
  NEG    a rule's condition negated
  DROP   a rule removed from the spec
  PRED   a threshold comparison's boundary moved (>= to >, > to >=, <= to <, < to <=) on one rule
  SHIFT  a threshold parameter moved by one unit (0.1 below 10) for every rule reading it
A mutant is killed when, on some case of the sample, a candidate's floor, ceiling, pending groups, costs, tax items or
deadlines differ from the original's, the run fails, or the compiler rejects the mutated spec. The sample: the
boundary-value cases of the battery plus a greedy cover of the grid cases by the rules that fire in them; each mutant
runs first on the cases where its rule fires and stops at the first difference. Writes out/mutation.json (read by the
battery report) and out/mutation_report.md. Survivors point at rules or thresholds no case pins down.
"""
import io
import json
import sys
import time
from dataclasses import replace
from multiprocessing import Pool
from pathlib import Path

OUT = Path("out")


def table(path, P):
    """The case's candidate table as the fingerprint keeps it (plus every tax item and deadline), and the rule ids
    that fire in it."""
    from .battery import items_of
    from .engine import RULES_BY_ID
    from .ex_ante import ex_ante
    from .rules.model import Effect
    from .run import load_case
    template, case, event, subject, ticks, notes = load_case(path)
    out = ex_ante(template, event, case, ticks=ticks or None, P=P, subject=subject)
    rows, fired = [], set()
    for r in out.table:
        pending = {g for g in r.b.groups}                         # (rule, flow) left open in this row
        rows.append((str(sorted(r.cand.items())), r.b.lo, r.b.hi, items_of(r.b.L_lo), items_of(r.b.L_hi),
                     sorted("%s|%s|%s" % (g[0], g[1], ",".join(sorted(n.key for n in ns))) for g, ns in r.b.groups.items()),
                     sorted("%s|%s=%.2f" % (g[0], g[1], c) for g, c in r.b.cost.items())))
        for labels in (r.b.L_lo, r.b.L_hi):
            for lb in labels.values():                          # a charge or a base counts where it moves a tax item —
                moving = {c for it in lb.items if abs(it.effective) > 1e-12 for c in it.cites}   # applied at a nil rate it
                for rid in set(lb.applied) | {c for it in lb.items for c in it.cites}:            # pins nothing down; any
                    r_ = RULES_BY_ID.get(rid)                                                      # other rule where it applies
                    if r_ is not None and r_.effect in (Effect.CHARGE, Effect.BASE) and rid not in moving:
                        continue
                    fired.add(rid)
                    if lb.flow is not None and (rid, lb.flow.id) not in pending:
                        fired.add(rid + "!")                    # applied with its condition decided: a negation shows
        fired |= {g[0] for g in r.b.groups}
    return rows, fired


def _table_job(name):
    from .battery import DIR
    from .params import Params
    try:
        return name, table(DIR / (name + ".json"), Params())
    except Exception as e:                                      # noqa: BLE001
        return name, ("error: %s" % e, set())


def swap_pred(c, target, new):
    """The condition with the leaf `target` (by identity) replaced by `new`."""
    from .rules.model import And, Not, Or
    if c is target:
        return new
    if isinstance(c, And):
        return And(*(swap_pred(x, target, new) for x in c.xs))
    if isinstance(c, Or):
        return Or(*(swap_pred(x, target, new) for x in c.xs))
    if isinstance(c, Not):
        return Not(swap_pred(c.x, target, new))
    return c


def threshold_leaves(c):
    from .rules.model import And, Leaf, Not, Or
    if isinstance(c, Leaf):
        return [c] if c.param and c.pred.name in ("ge", "gt", "le", "lt") else []
    if isinstance(c, (And, Or)):
        return [x for y in c.xs for x in threshold_leaves(y)]
    if isinstance(c, Not):
        return threshold_leaves(c.x)
    return []


def mutants(ops):
    """(id, operator, rule ids it touches, spec or None, shifted parameter or None), in a fixed order."""
    from .battery import numeric_thresholds
    from .rules.model import Leaf, Not, ge, gt, le, lt
    from .rules.spec import SPEC
    flip = {"ge": gt, "gt": ge, "le": lt, "lt": le}
    out = []
    if "NEG" in ops:
        for i, r in enumerate(SPEC):
            if r.cond is None or getattr(r.cond, "xs", None) == ():
                continue                                        # unconditional: negation would only remove it (DROP)
            out.append(("NEG %s" % r.id, "NEG", {r.id}, SPEC[:i] + [replace(r, cond=Not(r.cond))] + SPEC[i + 1:], None))
    if "DROP" in ops:
        for i, r in enumerate(SPEC):
            out.append(("DROP %s" % r.id, "DROP", {r.id}, SPEC[:i] + SPEC[i + 1:], None))
    if "PRED" in ops:
        for i, r in enumerate(SPEC):
            for x in threshold_leaves(r.cond):
                new = Leaf(x.field, flip[x.pred.name], x.param, x.on)
                out.append(("PRED %s %s %s->%s" % (r.id, x.field, x.pred.name, new.pred.name), "PRED", {r.id},
                            SPEC[:i] + [replace(r, cond=swap_pred(r.cond, x, new))] + SPEC[i + 1:], None))
    if "SHIFT" in ops:
        for pid, (field_, kind, rids) in sorted(numeric_thresholds().items()):
            out.append(("SHIFT %s" % pid, "SHIFT", set(rids), None, pid))
    return out


def shifted(pid):
    from .params import Params
    P = Params()
    row = dict(P.rows[pid])
    v = float(row["value"])
    row["value"] = repr(v + (1.0 if abs(v) >= 10 else 0.1))
    P.rows[pid] = row
    P.token = P.token + ":" + pid + "+"
    return P


_STATE = {}


def _init(state):
    _STATE.update(state)


def _mutant_job(k):
    """Run mutant k (rebuilt here: rule conditions hold functions and do not cross processes)."""
    from . import engine as E
    from .battery import DIR
    from .params import Params
    from .rules.compile import CompileError, compile_rules
    if "_mutants" not in _STATE:                                # built once per worker
        _STATE["_mutants"] = mutants(_STATE["ops"])
    mid, op, rids, spec, ppid = _STATE["_mutants"][k]
    base, fired_in, sample, bounds_cases = _STATE["base"], _STATE["fired_in"], _STATE["sample"], _STATE["bounds_cases"]
    verdict, where, P = "survived", "", Params()
    orig = E.RULES
    try:
        if spec is not None:
            E.RULES = compile_rules(spec, Params())
            E._PLAN_FAV.clear()                             # plan sides are read off the rules in force
        if ppid is not None:
            P = shifted(ppid)
        first = [n for n in sample if fired_in[n] & rids]
        if ppid is not None:
            first = [n for n in bounds_cases if ("__thr_%s_" % ppid.replace(".", "-")) in n] + first
        for n in first + [n for n in sample if n not in first]:
            try:
                rows, _ = table(DIR / (n + ".json"), P)
            except Exception as e:                              # noqa: BLE001
                verdict, where = "killed", "%s (run failed: %s)" % (n, type(e).__name__)
                break
            if rows != base[n]:
                verdict, where = "killed", n
                break
    except CompileError as e:
        verdict, where = "killed", "compiler: %s" % str(e).splitlines()[0][:100]
    finally:
        E.RULES = orig
        E._PLAN_FAV.clear()
    return {"mutant": mid, "operator": op, "verdict": verdict, "where": where}


def main(argv):
    from .battery import DIR
    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    ops = set((argv[argv.index("--ops") + 1] if "--ops" in argv else "NEG,DROP,PRED,SHIFT").split(","))
    limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else None
    jobs = int(argv[argv.index("--jobs") + 1]) if "--jobs" in argv else 1
    t0 = time.time()
    grid = sorted(p.stem for p in DIR.glob("*.json") if "__" not in p.stem)
    bounds_cases = sorted(p.stem for p in DIR.glob("*__thr_*.json"))
    with Pool(jobs) as pool:                                    # the original's tables and what fires where
        got = dict(pool.map(_table_job, grid + bounds_cases, chunksize=1))
    base = {n: v[0] for n, v in got.items()}
    fired_in = {n: v[1] for n, v in got.items()}
    need = set().union(*(fired_in[n] for n in grid))
    cover = []
    while need:                                                 # greedy set cover of the grid by fired rules
        best = max(grid, key=lambda n: len(fired_in[n] & need))
        if not fired_in[best] & need:
            break
        cover.append(best)
        need -= fired_in[best]
    sample = cover + bounds_cases
    ids = list(range(len(mutants(ops))))[:limit]
    out.write("baseline: %d grid cases, cover %d, boundary %d, %d mutants (%.0f s)\n" % (
        len(grid), len(cover), len(bounds_cases), len(ids), time.time() - t0))
    out.flush()
    state = {"ops": ops, "base": base, "fired_in": fired_in, "sample": sample, "bounds_cases": bounds_cases}
    with Pool(jobs, initializer=_init, initargs=(state,)) as pool:
        results = pool.map(_mutant_job, ids, chunksize=1)
    by_op = {}
    for r in results:
        a = by_op.setdefault(r["operator"], [0, 0])
        a[0] += r["verdict"] == "killed"
        a[1] += 1
    survivors = [r["mutant"] for r in results if r["verdict"] != "killed"]
    summary = {"killed": sum(v[0] for v in by_op.values()), "total": len(results), "cases": len(sample),
               "by_operator": by_op, "survivors": survivors, "seconds": round(time.time() - t0)}
    OUT.mkdir(exist_ok=True)
    (OUT / "mutation.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = ["# Mutation report", "", "killed %d of %d mutants on %d cases (%d s)" % (summary["killed"], summary["total"],
                                                                                    len(sample), summary["seconds"]), ""]
    lines += ["| operator | killed | total |", "|---|---|---|"] + ["| %s | %d | %d |" % (k, v[0], v[1]) for k, v in sorted(by_op.items())]
    lines += ["", "## survivors (no case of the sample notices them)", ""] + ["- " + s for s in survivors]
    lines += ["", "## killed: where", ""] + ["- %s — %s" % (r["mutant"], r["where"]) for r in results if r["verdict"] == "killed"]
    (OUT / "mutation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    out.write("killed %d of %d (%s) -> out/mutation_report.md\n" % (summary["killed"], summary["total"],
                                                                     ", ".join("%s %d/%d" % (k, v[0], v[1]) for k, v in sorted(by_op.items()))))
    out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
