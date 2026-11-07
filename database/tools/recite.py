#!/usr/bin/env python
"""Repoint citations by their quotes after the slicing changed or a merge (数据库规范.md §4.3, §4.5). Needs a built
clause.csv. Values, units, dates and the wording of the law are never touched.

  python database/tools/recite.py --jur ae,id [--ids] [--report <csv>] [--dry-run]

For the parameters and absence records of the given jurisdictions (and the pairs they own):
  1. a cite_id that no longer exists, or whose clause does not hold the quote, points to the smallest clause of the same
     document that holds the quote verbatim (build.norm);
  2. if none does, lines of the quote that are only a page number (build.RE_PAGENO), then page headers too (a line such
     as 'Laws of Malaysia ACT 53'), are left out when that makes the quote match a clause of the document;
  3. with --ids, a param_id not of the form <scope>.<slot>.<name>[.<suffix>] becomes <scope>.<slot>.<name>, with the
     suffix .company / .individual when that id is taken (§4.4); superseded_by follows.
Rows still unmatched are listed as unresolved.
"""
import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build                               # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
HEADER = re.compile(r"^\s*(Page \d+( of \d+)?|\d{1,4}\s+Laws of Malaysia\b.*|Laws of Malaysia\s*ACT \d+|Income Tax)\s*$", re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jur", required=True, help="jurisdictions, comma-separated")
    ap.add_argument("--ids", action="store_true", help="also bring param_ids to <scope>.<slot>.<name>[.<suffix>]")
    ap.add_argument("--report", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--root", default="", help="library folder (default: database/)")
    args = ap.parse_args()
    global ROOT
    if args.root:
        ROOT = build.ROOT = Path(args.root).resolve()
    jurs = set(args.jur.split(","))
    by_doc = {}
    for c in build.read_csv(ROOT / "clause.csv"):
        by_doc.setdefault(c["doc_id"], []).append((c["cite_id"], build.norm(c["text"])))
    text = {cid: t for rows in by_doc.values() for cid, t in rows}
    changes = []

    def hits(doc, quote):
        q = build.norm(quote)
        return sorted((len(t), c) for c, t in by_doc.get(doc, []) if q and q in t)

    def fix(kind, key, r):
        cid = r.get("cite_id") or ""
        if not cid or (cid in text and build.norm(r.get("quote")) in text[cid]):
            return
        doc = cid.split("#")[0]
        h = hits(doc, r.get("quote"))
        if h:
            changes.append((kind, key, "cite_id", cid, h[0][1]))
            r["cite_id"] = h[0][1]
            return
        lines = (r.get("quote") or "").splitlines()
        for drop in (build.RE_PAGENO, HEADER):
            kept = [x for x in lines if not drop.match(x.strip()) and not build.RE_PAGENO.match(x.strip())]
            h = hits(doc, "\n".join(kept)) if len(kept) < len(lines) else []
            if h:
                changes.append((kind, key, "quote", " | ".join(x.strip() for x in lines if x not in kept), "page lines left out; cite " + h[0][1]))
                r["quote"], r["cite_id"] = "\n".join(kept), h[0][1]
                return
        changes.append((kind, key, "unresolved", cid, ""))

    def mine(code):
        return code.split("-")[0] in jurs

    params = build.read_csv(ROOT / "param.csv")
    if args.ids:
        ids, renamed = {p["param_id"] for p in params}, {}
        for p in params:
            stem = "%s.%s.%s" % (p["scope"], p["slot"], p["name"])
            if mine(p["scope"]) and p["param_id"] != stem and not p["param_id"].startswith(stem + "."):
                new = stem if stem not in ids else "%s.%s" % (stem, p["subject"])
                n = 2
                while new in ids:
                    new, n = "%s.%s.%d" % (stem, p["subject"], n), n + 1
                ids.discard(p["param_id"])
                ids.add(new)
                renamed[p["param_id"]] = new
                changes.append(("param", p["param_id"], "param_id", p["param_id"], new))
                p["param_id"] = new
        for p in params:
            if p.get("superseded_by") in renamed:
                p["superseded_by"] = renamed[p["superseded_by"]]
    for p in params:
        if mine(p["scope"]):
            fix("param", p["param_id"], p)
    decisions = build.read_csv(ROOT / "decision.csv")
    for d in decisions:
        if mine(d["jur"]):
            fix("decision", d["id"], d)
    for what in ("param_id", "cite_id", "quote", "unresolved"):
        print("%-10s %d" % (what, sum(1 for c in changes if c[2] == what)))
    if args.report:
        with open(args.report, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["table", "row", "what", "old", "new"])
            w.writerows(changes)
    if not args.dry_run:
        build.write_csv(ROOT / "param.csv", build.TABLES["param"], params)
        build.write_csv(ROOT / "decision.csv", build.TABLES["decision"], decisions)
    return 0


if __name__ == "__main__":
    sys.exit(main())
