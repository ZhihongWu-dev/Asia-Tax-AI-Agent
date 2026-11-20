#!/usr/bin/env python
"""Re-fetch the documents most likely to change and say which did (database_spec.en.md §4.6): each jurisdiction's treaty
list and the treaties signed but not yet in force (coverage/watch.csv, written by coverage.py). The library is not
changed; the report goes to coverage/watch.md.

  python database/tools/watch.py [--all] [--jur cn]

--all re-checks every document of sources.csv. Plain requests through fetch.get (1 attempt + 2 retries), no other
measure: a page that refuses is reported, never worked around. A web page counts as changed only when its visible text
changed, since pages carry dates and tokens that differ on every load. For a changed document: open it, register the
new version with fetch.py --force (or under a new id when it is a new instrument), then update treaty_list.csv or
treaty.csv and record it in session_log.md.
"""
import argparse
import hashlib
import io
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402
import fetch  # noqa: E402

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def visible(content):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(content, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ")).strip()


def is_html(content, ctype):
    return "html" in (ctype or "") or content[:200].lstrip().lower().startswith((b"<!doctype html", b"<html"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="every document, not only the watch list")
    ap.add_argument("--jur", default="", help="only documents of this jurisdiction and its pairs")
    ap.add_argument("--pace", type=float, default=2.0, help="seconds between requests")
    args = ap.parse_args()
    root = build.ROOT
    docs = {d["id"]: d for d in build.read_csv(root / "doc.csv")}
    rows = build.read_csv(root / "coverage" / ("sources.csv" if args.all else "watch.csv"))
    if not rows:
        print("no %s; run python database/tools/coverage.py first" % ("coverage/sources.csv" if args.all else "coverage/watch.csv"))
        return 1
    if args.jur:
        rows = [r for r in rows if args.jur in docs.get(r["id"], {}).get("jur", "").split("-")]
    report = ["# Watch report", "", "Written by `tools/watch.py` on %s; the library was not changed." % datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ"),
              "", "| id | why | result |", "|---|---|---|"]
    counts = {}
    for k, r in enumerate(rows):
        d = docs.get(r["id"])
        if not d or "<OC>" in d["url"]:
            continue
        if k:
            time.sleep(args.pace)
        try:
            content, ctype, _ = fetch.get(d["url"], min_bytes=200)
        except RuntimeError as e:
            result = "unreachable: %s" % str(e)[:120]
        else:
            if hashlib.sha256(content).hexdigest() == d["sha256"]:
                result = "same"
            elif is_html(content, ctype) and (root / d["file"]).is_file() and visible(content) == visible((root / d["file"]).read_bytes()):
                result = "same text (page bytes differ)"
            else:
                result = "CHANGED: open it and register the new version (fetch.py --force)"
        counts[result.split(":")[0].split(" (")[0]] = counts.get(result.split(":")[0].split(" (")[0], 0) + 1
        report.append("| %s | %s | %s |" % (d["id"], r.get("why", ""), result.replace("|", "/")))
        print("%s: %s" % (d["id"], result))
    (root / "coverage").mkdir(exist_ok=True)
    (root / "coverage" / "watch.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(", ".join("%s %d" % kv for kv in sorted(counts.items())) or "nothing checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
