#!/usr/bin/env python
"""CNY central parity (人民币汇率中间价) for a date, from the CFETS history query, cached in fx/cny_central_parity.csv.

The law fixes the rate (cn.sta.2017-37#i4: the central parity on the day the withholding obligation arises;
cn.sta.2025-18#i6: on the payment day for a reinvestment), so the rate is reference data, not a case input.
Publisher: 中国外汇交易中心, authorised by the People's Bank of China (doc cn.cfets.central-parity).
Python 3.9, conda env "pytorch".

    python official/tools/fx_cny.py 2025-09-30 HKD SGD        # prints the rates, fetching and caching if needed
    from fx_cny import rate; rate(date(2025, 9, 30), "HKD")   # -> 0.91298 (CNY per 1 HKD); None on a non-publishing day
"""
import csv
import io
import json
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "fx" / "cny_central_parity.csv"
API = "https://www.chinamoney.com.cn/ags/ms/cm-u-bk-ccpr/CcprHisNew"
FIELDS = ["date", "pair", "rate", "source_url", "retrieved_at"]
PAIRS = {"USD": "USD/CNY", "HKD": "HKD/CNY", "SGD": "SGD/CNY", "EUR": "EUR/CNY", "GBP": "GBP/CNY", "JPY": "100JPY/CNY"}


def _load():
    if not CSV.exists():
        return {}
    with CSV.open(encoding="utf-8-sig", newline="") as f:
        return {(r["date"], r["pair"]): r for r in csv.DictReader(f)}


def _save(rows):
    CSV.parent.mkdir(exist_ok=True)
    with CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(sorted(rows.values(), key=lambda r: (r["date"], r["pair"])))


def fetch(start, end, currencies):
    """All published parities between two dates for the given currencies; the site answers JSON to curl."""
    pairs = ",".join(PAIRS[c] for c in currencies)
    url = "%s?startDate=%s&endDate=%s&currency=%s&pageNum=1&pageSize=10" % (API, start, end, pairs)      # the site refuses larger pages
    out = subprocess.run(["curl", "-s", "--max-time", "40", "-A", "Mozilla/5.0", url], capture_output=True, check=True).stdout
    d = json.loads(out.decode("utf-8"))
    head = d["data"].get("searchlist") or d["data"]["head"]     # values follow the requested pairs, not the full head
    rows = {}
    for rec in d.get("records", []):
        for pair, v in zip(head, rec["values"]):
            if pair in pairs.split(",") and v:
                rows[(rec["date"], pair)] = dict(date=rec["date"], pair=pair, rate=v, source_url=url,
                                                retrieved_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    return rows


def rate(day, currency):
    """CNY per one unit of currency (per 100 for JPY) on that day; None when no parity was published (weekend, holiday)."""
    pair = PAIRS[currency]
    cache = _load()
    key = (day.isoformat(), pair)
    if key not in cache:
        got = fetch(day.isoformat(), day.isoformat(), [currency])
        if not got:                                     # remember the empty day so it is not asked again
            got = {key: dict(date=day.isoformat(), pair=pair, rate="", source_url=API, retrieved_at="")}
        cache.update(got)
        _save(cache)
    v = cache[key]["rate"]
    return float(v) if v else None


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    d = date.fromisoformat(sys.argv[1])
    for c in sys.argv[2:] or ["USD", "HKD", "SGD"]:
        print(d, PAIRS[c], rate(d, c))
