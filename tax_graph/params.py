"""Read-only access to official/params.csv. The calculators hold no numbers of their own."""
import csv
from pathlib import Path

OFFICIAL = Path(__file__).resolve().parents[1] / "official"
NUMERIC = {"%", "days", "months", "years", "tiers", "ratio", "CNY", "HKD", "SGD", "EUR", "persons"}


class Params:
    def __init__(self, path=None):
        import hashlib
        raw = Path(str(path or OFFICIAL / "params.csv")).read_bytes()
        self.token = hashlib.sha1(raw).hexdigest()   # identifies the parameter set (cache keys)
        with open(str(path or OFFICIAL / "params.csv"), encoding="utf-8-sig", newline="") as f:
            self.rows = {r["param_id"]: r for r in csv.DictReader(f)}
        self.used = []                               # ids read during one calculation, in order

    def __getitem__(self, pid):
        if pid not in self.rows:
            raise KeyError("parameter not in official/params.csv: %s" % pid)
        r = self.rows[pid]
        if pid not in self.used:
            self.used.append(pid)
        if r["unit"] in NUMERIC:
            return float(r["value"])
        if r["unit"] == "bool":
            return r["value"] in ("1", "1.0", "True", "true")
        return r["value"]

    def cite(self, pid):
        return self.rows[pid]["cite_id"]
