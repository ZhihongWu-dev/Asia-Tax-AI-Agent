#!/usr/bin/env python
"""Extract Singapore public holidays from the saved Ministry of Manpower page into calendars/sg_public_holidays.csv.

Each row keeps the page's own summary line as `quote`; build.py checks it verbatim against the page text.
Python 3.9, conda env "pytorch".   python official/tools/calendar_sg.py
"""
import csv
import io
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[1]
DOC = "sg.mom.public-holidays"
RE_SUMMARY = re.compile(r"^(\d{1,2} [A-Z][a-z]+ \d{4})(?: - (\d{1,2} [A-Z][a-z]+ \d{4}))?, [A-Z][a-z]+day")


def main():
    soup = BeautifulSoup((ROOT / "raw" / "sg" / (DOC + ".html")).read_bytes(), "lxml")
    for t in soup(["script", "style"]):
        t.decompose()
    lines = [" ".join(x.split()) for x in soup.get_text("\n").splitlines() if x.strip()]
    rows, seen = [], set()
    for i, ln in enumerate(lines):
        m = RE_SUMMARY.match(ln)
        if not m:
            continue
        d1 = datetime.strptime(m.group(1), "%d %B %Y").date()
        d2 = datetime.strptime(m.group(2), "%d %B %Y").date() if m.group(2) else d1
        name = lines[i - 1]
        d = d1
        while d <= d2:
            if d not in seen:
                seen.add(d)
                rows.append({"date": d.isoformat(), "weekday": d.strftime("%A"), "name": name,
                             "doc_id": DOC, "quote": ln})
            d += timedelta(days=1)
    rows.sort(key=lambda r: r["date"])
    out = ROOT / "calendars"
    out.mkdir(exist_ok=True)
    with (out / "sg_public_holidays.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "weekday", "name", "doc_id", "quote"])
        w.writeheader()
        w.writerows(rows)
    years = sorted({r["date"][:4] for r in rows})
    print("holidays: %d rows, years %s" % (len(rows), ", ".join(years)))


if __name__ == "__main__":
    main()
