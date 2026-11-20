#!/usr/bin/env python
"""Write the no-treaty rows the treaty lists prove, and list the pairs still due (database_spec.en.md §4.2, §5).

  python database/tools/pairs.py            # show what would be written and what is due
  python database/tools/pairs.py --write    # append the no-treaty rows to treaty.csv

For each pair of jurisdictions of jurisdiction.csv without a treaty row: when the treaty lists of both are in
treaty_list.csv (or one has no treaty at all, an absence record of category page_treaties) and neither names the other
in force or signed, the pair gets a row with status none whose note names both lists. A pair that a list names is only
printed: its treaty is registered by hand (§4.2).
"""
import argparse
import io
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def source(jur, named, decisions):
    docs = sorted({r["doc_id"] for r in named.get(jur, {}).values()})
    if docs:
        return "the treaty list of %s (%s)" % (jur, ", ".join(docs))
    absent = [d["id"] for d in decisions if d.get("jur") == jur and (d.get("category") or "").strip() == "page_treaties"]
    return "%s, which has no treaty (%s)" % (jur, ", ".join(absent))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="append the no-treaty rows to treaty.csv")
    ap.add_argument("--root", default="", help="library folder (default: database/)")
    args = ap.parse_args()
    if args.root:
        build.ROOT = Path(args.root).resolve()
    root = build.ROOT
    juris = build.read_csv(root / "jurisdiction.csv")
    treaties = build.read_csv(root / "treaty.csv")
    decisions = build.read_csv(root / "decision.csv")
    named = build.treaty_lists(build.read_csv(root / "treaty_list.csv"), decisions)
    have = {t["pair"] for t in treaties}
    new, due, waiting = [], [], []
    for pair in build.pairs_of([j["code"] for j in juris]):
        if pair in have:
            continue
        a, b = pair.split("-")
        if a not in named or b not in named:
            waiting.append("%s (treaty list of %s missing)" % (pair, "/".join(x for x in (a, b) if x not in named)))
            continue
        says = [x for x, y in ((a, b), (b, a)) if y in named[x] and named[x][y]["status"] in ("in_force", "signed")]
        if says:
            due.append("%s (named by the list of %s)" % (pair, "/".join(says)))
            continue
        new.append({"pair": pair, "doc_id": "", "status": "none", "signed_on": "", "in_force_from": "", "mli_doc_id": "",
                    "pending_doc_id": "", "pending_signed_on": "",
                    "note": "No treaty: neither %s nor %s names the other; written by pairs.py on %s."
                            % (source(a, named, decisions), source(b, named, decisions), date.today().isoformat())})
    for r in new:
        print("no treaty: %s" % r["pair"])
    for x in due:
        print("due, register the treaty: %s" % x)
    for x in waiting:
        print("waiting: %s" % x)
    print("%d no-treaty rows%s, %d treaties due, %d pairs waiting for a treaty list" % (
        len(new), " written" if args.write and new else "" if args.write else " (not written; add --write)", len(due), len(waiting)))
    if args.write and new:
        build.write_csv(root / "treaty.csv", build.TABLES["treaty"], treaties + new)
    return 0


if __name__ == "__main__":
    sys.exit(main())
