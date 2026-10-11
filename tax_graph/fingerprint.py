"""Regression fingerprint: every battery case's ex-ante table (candidate, floor, ceiling, pending groups and their
costs) as one JSON file, so a refactor that must not change results can be diffed exactly.

    python -m tax_graph.fingerprint out/fp_before.json
    python -m tax_graph.fingerprint out/fp_after.json
    python -m tax_graph.fingerprint --diff out/fp_before.json out/fp_after.json
"""
import io
import json
import sys
import time
import traceback
from pathlib import Path

from .run import load_case
from .ex_ante import ex_ante

DIR = Path("cases/battery")


def fingerprint_case(path):
    template, case, event, subject, ticks, notes = load_case(path)
    try:
        out = ex_ante(template, event, case, ticks=ticks or None, subject=subject)
    except Exception as e:                                  # noqa: BLE001
        return {"error": "%s: %s" % (type(e).__name__, e)}
    rows = []
    for r in out.table:
        rows.append({"cand": {k: str(v) for k, v in sorted(r.cand.items())}, "lo": r.b.lo, "hi": r.b.hi,
                     "dominated": r.dominated,
                     "groups": sorted("%s|%s|%s" % (g[0], g[1], ",".join(sorted("%s:%s" % (n.source, n.key) for n in ns)))
                                      for g, ns in r.b.groups.items()),
                     "cost": sorted("%s|%s=%.2f" % (g[0], g[1], c) for g, c in r.b.cost.items())})
    return {"rows": rows}


def _fp_one(path):
    try:
        return path.stem, fingerprint_case(path)
    except Exception:                                       # noqa: BLE001
        return path.stem, {"error": traceback.format_exc().splitlines()[-1]}


def main(argv):
    """python -m tax_graph.fingerprint OUT.json [--jobs N] | --diff A.json B.json"""
    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if argv and argv[0] == "--diff":
        a = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        b = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
        diffs = [k for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]
        out.write("%d cases, %d differ\n" % (len(set(a) | set(b)), len(diffs)))
        for k in diffs[:20]:
            out.write("  %s\n" % k)
        out.flush()
        return 1 if diffs else 0
    dest = Path(argv[0])
    jobs = int(argv[argv.index("--jobs") + 1]) if "--jobs" in argv else 1
    t0 = time.time()
    paths = sorted(DIR.glob("*.json"))
    if jobs > 1:
        from multiprocessing import Pool
        with Pool(jobs) as pool:
            res = dict(pool.map(_fp_one, paths, chunksize=1))
    else:
        res = dict(_fp_one(p) for p in paths)
    dest.write_text(json.dumps(res, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
    out.write("%d cases in %.1f s -> %s\n" % (len(res), time.time() - t0, dest))
    out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
