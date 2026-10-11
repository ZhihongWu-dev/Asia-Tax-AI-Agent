"""GOLD and SNAPSHOT (v1 §8, 规则层.md §4). Two oracle kinds, never mixed:

    official   values taken from an official tool or worked example — official/labels/ (checked by check_sg_s45)
    snapshot   the engine's own output on a whole structure, stored here to detect change, not to prove correctness

    python -m tax_graph.data.gold            compare scenario A with the stored snapshot
    python -m tax_graph.data.gold --update   re-snapshot after a deliberate rule change
"""
import io
import json
import sys
from pathlib import Path

from ..cases import SCENARIOS
from ..ex_ante import ex_ante
from ..scenarios import TEMPLATES

STORE = Path(__file__).resolve().parent / "gold" / "scenarios.json"


def snapshot():
    rows = {}
    for name, (tname, case, event) in SCENARIOS.items():
        t = TEMPLATES[tname]
        res = ex_ante(t, event, case)
        for r in res.table:
            key = name + ": " + "/".join(str(r.cand.get(k)) for k in t.vars(event))
            rows[key] = {"lo": r.b.lo, "hi": r.b.hi, "dominated": r.dominated,
                         "pending": sorted(n.key for ns in r.b.groups.values() for n in ns)}
            if r.unmodelled:
                rows[key]["unmodelled"] = [list(x) for x in r.unmodelled]
    return {"oracle_kind": "snapshot", "case": "scenarios " + ", ".join(SCENARIOS), "rows": rows}


def main(argv):
    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    now = snapshot()
    if "--update" in argv or not STORE.exists():
        STORE.parent.mkdir(exist_ok=True)
        STORE.write_text(json.dumps(now, ensure_ascii=False, indent=1), encoding="utf-8")
        out.write("snapshot written: %d rows -> %s\n" % (len(now["rows"]), STORE.name))
        out.flush()
        return 0
    old = json.loads(STORE.read_text(encoding="utf-8"))
    changed = 0
    for key, row in now["rows"].items():
        was = old["rows"].get(key)
        if was != row:
            changed += 1
            out.write("CHANGED %-26s was %s\n%-34s now %s\n" % (key, was, "", row))
    for key in set(old["rows"]) - set(now["rows"]):
        changed += 1
        out.write("GONE    %s\n" % key)
    out.write("%d rows, %d changed since the snapshot (oracle_kind = snapshot: change detection only)\n" % (len(now["rows"]), changed))
    out.flush()
    return 1 if changed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
