#!/usr/bin/env python
"""Remove documents that are repealed or superseded: raw file, text file, manifest row, verify row.

A one-line audit record (id, title, reason, date) is appended to official/removed.csv; the content is not kept.
Python 3.9, conda env "pytorch".
  python official/tools/prune.py --reason "全文废止，2025-04-01" cn.sta.2016-40 cn.sta.2016-40.a01
  python official/tools/prune.py --reason "..." --with-children cn.sta.2019-17
"""
import csv
import io
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[1]
ENC = "utf-8-sig"


def read(path):
    if not path.exists():
        return [], []
    with path.open(encoding=ENC, newline="") as f:
        r = csv.DictReader(f)
        return list(r), r.fieldnames


def write(path, fields, rows):
    with path.open("w", encoding=ENC, newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main(argv):
    reason, children, ids = "", False, []
    it = iter(argv)
    for a in it:
        if a == "--reason":
            reason = next(it)
        elif a == "--with-children":
            children = True
        else:
            ids.append(a)
    if not ids or not reason:
        print(__doc__)
        return 1
    removed = []
    for man in sorted(ROOT.glob("manifest_*.csv")):
        rows, fields = read(man)
        keep = []
        for r in rows:
            hit = r["id"] in ids or (children and any(r["id"].startswith(i + ".a") for i in ids))
            if not hit:
                keep.append(r)
                continue
            for f in (ROOT / r["file"], ROOT / "text" / (r["id"] + ".txt")):
                if f.exists():
                    f.unlink()
            removed.append({"id": r["id"], "title": r["title"], "reason": reason,
                            "removed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
        if len(keep) != len(rows):
            write(man, fields, keep)
    gone = {r["id"] for r in removed}
    rows, fields = read(ROOT / "verify.csv")
    if rows:
        write(ROOT / "verify.csv", fields, [r for r in rows if r["id"] not in gone])
    log, _ = read(ROOT / "removed.csv")
    write(ROOT / "removed.csv", ["id", "title", "reason", "removed_at"], log + removed)
    for r in removed:
        print("removed", r["id"])
    print("%d removed; not found: %s" % (len(removed), sorted(set(ids) - gone)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
