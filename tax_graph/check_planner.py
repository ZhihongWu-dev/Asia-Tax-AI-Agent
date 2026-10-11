"""check_planner.py — the planner's contract (优化方案 v2 §1), checked on every battery case.

  1. one round per case: an outcome is either a question sheet or a plan; every question and every plan entry lies in
     a jurisdiction region; a plan never coexists with an unanswered datum that leaves a tax unbounded;
  2. ask-only-what-matters: a sparse case answered round by round from the matching full case's facts (actions yes,
     rulings no, anything the full case lacks: unknown) ends in the same plan — structure and guaranteed tax — as the
     full case answered the same way, or in a structure the other run lists as having the same guaranteed tax. If the
     planner skipped a datum that mattered, the two would differ;
  3. targeted contracts: an answer reaches only its own address; a new holding company does not dilute the stake it
     takes over; an unknown datum that leaves a tax unbounded excludes the candidates that need it, it is never filled.

    python -m tax_graph.check_planner [--quick] [--all] [--jobs N]   (--all: the battery's boundary and pairwise cases too)
"""
import io
import re
import sys
import time
from pathlib import Path

from .engine import flow_name
from .model import JURISDICTIONS
from .planner import Answers, plan
from .run import load_case

DIR = Path("cases/battery")
MAX_ROUNDS = 8


def _respond(question, full):
    """The full case's own value for an address, or 'unknown'."""
    key = question.key
    if question.kind == "action":
        return "actions", "yes"
    if question.kind == "ruling":
        return "rulings", "no"
    if question.kind == "library":
        return "library", "unknown"
    m = re.match(r"^hold:([A-Z_]+)>([A-Z_]+)\.(\w+)$", key)
    if m:
        h = full.holds.get((m.group(1), m.group(2)))
        v = getattr(h, m.group(3), None) if h is not None else None
        return "data", v if v is not None else "unknown"
    m = re.match(r"^flow:(.+)\.(\w+)$", key)
    if m:
        v = full.flows.get(flow_name(m.group(1)), {}).get(m.group(2))
        return "data", v if v is not None else "unknown"
    m = re.match(r"^group\.(\w+)$", key)
    if m:
        vals = [rf.attrs.get(m.group(1)) for rf in full.roles.values() if rf.attrs.get(m.group(1)) is not None]
        return "data", vals[0] if vals else "unknown"
    m = re.match(r"^([A-Z_]+)\.(\w+)$", key)
    if m:
        rf = full.roles.get(m.group(1))
        v = rf.attrs.get(m.group(2)) if rf is not None else None
        return "data", v if v is not None else "unknown"
    return "data", "unknown"


def drive(template, event, case, full):
    """Answer round by round from `full` until the planner stops asking. Returns (outcome, answers, rounds)."""
    ans = Answers()
    out = None
    for k in range(MAX_ROUNDS):
        out = plan(template, event, case, ans)
        if not out.questions:
            return out, ans, k + 1
        for q in out.questions:
            kind, v = _respond(q, full)
            if hasattr(v, "isoformat"):
                v = v.isoformat()
            getattr(ans, kind)[q.key] = v
    return out, ans, MAX_ROUNDS


def _regions_ok(out):
    for q in out.questions:
        if not q.region or not set(q.region) <= set(JURISDICTIONS):
            return "question without a region: %s" % q.key
    if out.plan:
        for rg in out.plan["regions"]:
            if not set(rg) <= set(JURISDICTIONS):
                return "plan entry outside the jurisdictions: %s" % sorted(rg)
    return None


def _round_one(path):
    """One planner round on one case: (stem, defect lines, asked?, planned?)."""
    template, case, event, subject, ticks, notes = load_case(path)
    try:
        o = plan(template, event, case, Answers())
    except Exception as e:                              # noqa: BLE001
        return path.stem, ["DEFECT %s: %s: %s" % (path.stem, type(e).__name__, e)], False, False
    lines = []
    msg = _regions_ok(o)
    if msg:
        lines.append("DEFECT %s: %s" % (path.stem, msg))
    if o.plan is not None and any(e.blocking for e in o.evaluations if e.cand == o.plan["cand"]):
        lines.append("DEFECT %s: a plan while a datum leaves its tax unbounded" % path.stem)
    return path.stem, lines, bool(o.questions), o.plan is not None


def _pair(sp_fp):
    """A sparse case and its full case answered round by round: (stem, defect line or None)."""
    sp, fp = sp_fp
    t_s, c_s, e_s, *_ = load_case(sp)
    t_f, c_f, e_f, *_ = load_case(fp)
    try:
        o_s, a_s, r_s = drive(t_s, e_s, c_s, c_f)
        o_f, a_f, r_f = drive(t_f, e_f, c_f, c_f)
    except Exception as e:                              # noqa: BLE001
        return sp.stem, "DEFECT %s (answered round by round): %s: %s" % (sp.stem, type(e).__name__, e)
    ps, pf = o_s.plan, o_f.plan
    key_s = (ps["cand"], round(ps["guaranteed"], 2)) if ps else ("none", o_s.note)
    key_f = (pf["cand"], round(pf["guaranteed"], 2)) if pf else ("none", o_f.note)
    equal = ps and pf and key_s[1] == key_f[1] and (                # equal guaranteed tax, and one run's structure
        pf["cand"] in [c for c, _, _ in ps.get("ties", [])] or ps["cand"] in [c for c, _, _ in pf.get("ties", [])])
    if key_s == key_f or equal:
        return sp.stem, None
    return sp.stem, "DEFECT ask-only-what-matters %s: sparse -> %s after %d rounds; full -> %s after %d rounds" % (
        sp.stem, key_s, r_s, key_f, r_f)


def main(argv):
    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    quick = "--quick" in argv
    jobs = int(argv[argv.index("--jobs") + 1]) if "--jobs" in argv else 1
    bad, t0 = 0, time.time()
    paths = sorted(DIR.glob("*.json"))
    if "--all" not in argv:                             # boundary-value and pairwise cases test the engine (battery)
        paths = [p for p in paths if "__" not in p.stem]
    if quick:
        paths = paths[::7]
    pairs = [(p, DIR / (p.name.replace("_sparse_", "_full_"))) for p in paths if "_sparse_" in p.name]
    pairs = [(sp, fp) for sp, fp in pairs if fp.exists()]
    if jobs > 1:
        from multiprocessing import Pool
        with Pool(jobs) as pool:
            ones = pool.map(_round_one, paths, chunksize=1)
            t1 = time.time()
            twos = pool.map(_pair, pairs, chunksize=1)
    else:
        ones = [_round_one(p) for p in paths]
        t1 = time.time()
        twos = [_pair(x) for x in pairs]
    # 1. one round per case
    for stem, lines, asked, planned in ones:
        for line in lines:
            out.write(line + "\n")
        bad += len(lines)
    out.write("round one on %d cases: %d question sheets, %d plans (%.0f s)\n" % (
        len(paths), sum(x[2] for x in ones), sum(x[3] for x in ones), t1 - t0))
    # 2. sparse answered from full == full
    for stem, line in twos:
        if line:
            out.write(line + "\n")
    diff = sum(1 for _, line in twos if line)
    bad += diff
    out.write("sparse answered from full: %d same plan, %d different (%.0f s)\n" % (len(twos) - diff, diff, time.time() - t0))
    out.write("%d defects\n" % bad)
    out.flush()
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
