#!/usr/bin/env python
"""Check what a change to the tools did to the clauses (数据库规范.md §4.9).

  python database/tools/clause_diff.py --save     # before the change: keep the current clause ids and texts
  python database/tools/build.py                  # after the change: rebuild
  python database/tools/clause_diff.py            # compare with the saved state

Lists, per document, the clause ids that disappeared, appeared or changed text. A disappeared id that is still cited
by param.csv, decision.csv or superseded.csv (column by) is an error: fix those citations in the same change.
Exit code 0 when no cited id disappeared, 1 otherwise. The saved state is database/.clause_before.csv.
"""
import argparse
import csv
import hashlib
import io
import sys
from collections import defaultdict
from pathlib import Path

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
csv.field_size_limit(10 ** 9)
ROOT = Path(__file__).resolve().parent.parent
SAVED = ROOT / ".clause_before.csv"


def read(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def state(rows):
    return {r["cite_id"]: (r["doc_id"], hashlib.md5((r.get("text") or "").encode("utf-8")).hexdigest()) for r in rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", action="store_true", help="save the current clause ids and texts")
    args = ap.parse_args()
    now = read(ROOT / "clause.csv")
    if args.save:
        with SAVED.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["cite_id", "doc_id", "text_md5"])
            for cid, (doc, md5) in state(now).items():
                w.writerow([cid, doc, md5])
        print("saved %d clause ids to %s" % (len(now), SAVED.name))
        return 0
    if not SAVED.exists():
        print("! nothing saved: run with --save before changing the tools")
        return 1
    old = {r["cite_id"]: (r["doc_id"], r["text_md5"]) for r in read(SAVED)}
    new = state(now)
    lost, gained, changed = defaultdict(list), defaultdict(list), defaultdict(list)
    for cid, (doc, md5) in old.items():
        if cid not in new:
            lost[doc].append(cid)
        elif new[cid][1] != md5:
            changed[doc].append(cid)
    for cid, (doc, _) in new.items():
        if cid not in old:
            gained[doc].append(cid)
    docs = sorted(set(lost) | set(gained) | set(changed))
    for d in docs:
        print("%s: lost %d, gained %d, text changed %d" % (d, len(lost[d]), len(gained[d]), len(changed[d])))
        for cid in lost[d][:8]:
            print("    lost   " + cid)
    cited = defaultdict(list)
    for r in read(ROOT / "param.csv"):
        cited[r.get("cite_id", "")].append("param " + r.get("param_id", ""))
    for r in read(ROOT / "decision.csv"):
        cited[r.get("cite_id", "")].append("decision " + r.get("id", ""))
    for r in read(ROOT / "superseded.csv"):
        cited[r.get("by", "")].append("superseded.csv by (%s#%s)" % (r.get("doc_id", ""), r.get("clause", "")))
    errors = [(cid, who) for d in lost for cid in lost[d] for who in cited.get(cid, [])]
    for cid, who in errors:
        print("! %s cites %s, which no longer exists" % (who, cid))
    warn = [(cid, who) for d in changed for cid in changed[d] for who in cited.get(cid, [])]
    for cid, who in warn:
        print("  note: %s cites %s, whose text changed (the build checks the quote)" % (who, cid))
    print("documents changed: %d; cited ids lost: %d" % (len(docs), len(errors)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
