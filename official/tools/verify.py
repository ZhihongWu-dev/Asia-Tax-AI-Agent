#!/usr/bin/env python
"""Re-download files that were registered from a curl copy and compare sha256 with the manifest.

Uses the curl command line, paced, because the chinatax CDN challenges python-requests.
Writes official/verify.csv (id, match, sha256_manifest, sha256_now, bytes_now, checked_at).
Python 3.9, conda env "pytorch".   python official/tools/verify.py [--sleep 3]
"""
import csv
import hashlib
import io
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[1]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def curl(url, out):
    r = subprocess.run(["curl", "-s", "-L", "-m", "120", "-A", UA, "-o", str(out), quote(url, safe=":/?&=%#")],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return r.returncode == 0 and out.exists()


def main():
    pause = float(sys.argv[sys.argv.index("--sleep") + 1]) if "--sleep" in sys.argv else 3.0
    rows = []
    for p in sorted(ROOT.glob("manifest_*.csv")):
        with p.open(encoding="utf-8-sig", newline="") as f:
            rows += [r for r in csv.DictReader(f) if r["via"] == "webfetch_copy" and "RAW bytes via curl" in r["note"]]
    out = []
    prev = {}
    if "--retry" in sys.argv and (ROOT / "verify.csv").exists():      # keep earlier matches, redo the rest
        with (ROOT / "verify.csv").open(encoding="utf-8-sig", newline="") as f:
            prev = {x["id"]: x for x in csv.DictReader(f)}
    tmp = Path(tempfile.mkdtemp())
    for i, r in enumerate(rows):
        if prev.get(r["id"], {}).get("match") == "yes":
            out.append(prev[r["id"]])
            continue
        f = tmp / ("f%03d" % i)
        ok = curl(r["url"], f)
        data = f.read_bytes() if ok else b""
        sha = hashlib.sha256(data).hexdigest() if data else ""
        match = "yes" if sha == r["sha256"] else "no"
        out.append({"id": r["id"], "match": match, "sha256_manifest": r["sha256"], "sha256_now": sha,
                    "bytes_now": len(data), "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
        print("%-28s %-3s %8d bytes" % (r["id"], match, len(data)))
        time.sleep(pause)
    with (ROOT / "verify.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()) if out else ["id"])
        w.writeheader()
        w.writerows(out)
    print("verified %d of %d" % (sum(1 for x in out if x["match"] == "yes"), len(out)))


if __name__ == "__main__":
    main()
