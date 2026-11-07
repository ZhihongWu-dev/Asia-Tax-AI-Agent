#!/usr/bin/env python
"""Merge another collector's library folder into this one by ownership (数据库规范.md §4.5).

  python database/tools/merge.py <other database folder> [--take ae,id,...] [--report <csv>] [--dry-run]

A row belongs to a jurisdiction: doc by jur, param by scope, decision by jur, treaty by pair, superseded by its doc; a
pair belongs to its alphabetically first side. The jurisdictions taken (--take, by default those that own rows in the
other folder and none here) come in: their docs with the originals in raw/ (and ocr/ texts), parameters, absence
records, treaty rows and superseded rows, plus the intl documents they cite. Rows of every other jurisdiction stay as they
are here; where the other folder has them differently, or has a row of a taken jurisdiction that exists here already
with other content, the row is listed as a conflict and not taken. Columns missing in the other folder are filled empty
(build.TABLES). text/, clause.csv and files.csv are not taken: the build makes them again.
After merging: python database/tools/build.py, then tools/recite.py for the taken jurisdictions, then the acceptance.
"""
import argparse
import csv
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build                               # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
KEYS = {"doc": ("id",), "param": ("param_id",), "decision": ("id",), "treaty": ("pair",), "superseded": ("doc_id", "clause", "by")}


def owner(row, table):
    code = {"doc": row.get("jur"), "param": row.get("scope"), "decision": row.get("jur"), "treaty": row.get("pair")}.get(table)
    if table == "superseded":
        d = row["doc_id"]
        code = d.split(".")[1] if d.startswith("treaty.") else d.split(".")[0]
    return "intl" if code == "intl" else (code or "").split("-")[0]


def cited_docs(rows):
    out = set()
    for t, rs in rows.items():
        for r in rs:
            for k in ("cite_id", "by"):
                if r.get(k):
                    out.add(r[k].split("#")[0])
            for k in ("doc_id", "mli_doc_id"):
                if t in ("treaty", "superseded") and r.get(k):
                    out.add(r[k])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("other", help="the other library folder (its database/)")
    ap.add_argument("--take", default="", help="jurisdictions to take, comma-separated (default: those only the other folder has)")
    ap.add_argument("--report", default="", help="write the taken rows and the conflicts to this csv")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--root", default="", help="library folder (default: database/)")
    args = ap.parse_args()
    global ROOT
    if args.root:
        ROOT = build.ROOT = Path(args.root).resolve()
    other = Path(args.other).resolve()
    tables = list(KEYS)
    here = {t: build.read_csv(ROOT / (t + ".csv")) for t in tables}
    there = {t: build.read_csv(other / (t + ".csv")) for t in tables}
    own_here = {owner(r, t) for t in tables for r in here[t]}
    own_there = {owner(r, t) for t in tables for r in there[t]} - {"intl"}
    take = set(args.take.split(",")) - {""} if args.take else own_there - own_here
    print("taking: %s" % (", ".join(sorted(take)) or "nothing"))
    report, added = [], {t: [] for t in tables}
    for t in tables:
        mine = {tuple(r[k] for k in KEYS[t]): r for r in here[t]}
        for r in there[t]:
            key = tuple(r[k] for k in KEYS[t])
            cols = build.TABLES.get(t) or build.SUPERSEDED
            same = key in mine and all((mine[key].get(c) or "") == (r.get(c) or "") for c in cols if c in r)
            if owner(r, t) in take and key not in mine:
                added[t].append(r)
                report.append((t, "|".join(key), "taken", owner(r, t)))
            elif key in mine and not same:
                report.append((t, "|".join(key), "conflict: kept here", owner(r, t)))
            elif key not in mine and owner(r, t) != "intl":
                report.append((t, "|".join(key), "not taken: owner %s not taken" % owner(r, t), owner(r, t)))
    ids_here = {r["id"] for r in here["doc"]}
    need = cited_docs(added) - ids_here - {r["id"] for r in added["doc"]}
    for r in there["doc"]:
        if r["jur"] == "intl" and r["id"] in need:
            added["doc"].append(r)
            report.append(("doc", r["id"], "taken: intl cited by a taken row", "intl"))
    missing = sorted(need - {r["id"] for r in added["doc"]})
    for d in missing:
        report.append(("doc", d, "conflict: cited by a taken row, in neither folder", ""))
    for t in tables:
        print("%-10s here %5d + taken %4d" % (t, len(here[t]), len(added[t])))
    print("conflicts: %d (see --report)" % sum(1 for r in report if r[2].startswith("conflict")))
    if args.report:
        with open(args.report, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["table", "key", "what", "owner"])
            w.writerows(report)
    if args.dry_run:
        print("dry run: nothing written")
        return 0
    for r in added["doc"]:
        for rel in (r["file"], "ocr/%s.txt" % r["id"]):
            src = other / rel
            if src.exists():
                (ROOT / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, ROOT / rel)
    for t in tables:
        if added[t]:
            build.write_csv(ROOT / (t + ".csv"), build.TABLES.get(t) or build.SUPERSEDED, here[t] + added[t])
    print("merged; next: build.py, recite.py --jur %s, then build.py --jur <each>" % ",".join(sorted(take)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
