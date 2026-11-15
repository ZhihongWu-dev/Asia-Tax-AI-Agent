"""Check merged library provenance without treating structural validity as legal approval."""
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path


def rows(root, name):
    csv.field_size_limit(10 ** 9)
    with (root / (name + ".csv")).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def audit(root):
    errors = []
    tables = {name: rows(root, name) for name in ("doc", "clause", "param", "decision")}
    keys = {"doc": "id", "clause": "cite_id", "param": "param_id", "decision": "id"}
    for name, records in tables.items():
        seen = set()
        for row in records:
            key = row[keys[name]]
            if key in seen:
                errors.append({"kind": "duplicate_id", "table": name, "id": key})
            seen.add(key)
    clauses = {row["cite_id"]: row for row in tables["clause"]}
    for row in tables["doc"]:
        path = (root / row["file"]).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            errors.append({"kind": "missing_source_file", "id": row["id"]})
        elif hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            errors.append({"kind": "source_hash_mismatch", "id": row["id"]})
    normalize = lambda value: re.sub(r"\s+", "", value)
    for table in ("param", "decision"):
        for row in tables[table]:
            cite = row.get("cite_id", "")
            if not cite:
                continue
            clause = clauses.get(cite)
            if clause is None:
                errors.append({"kind": "missing_citation", "table": table, "id": row[keys[table]], "cite_id": cite})
            elif row.get("quote") and normalize(row["quote"]) not in normalize(clause["text"]):
                errors.append({"kind": "quote_mismatch", "table": table, "id": row[keys[table]], "cite_id": cite})
    return {"counts": {k: len(v) for k, v in tables.items()}, "errors": errors, "legal_review": "not_established_by_this_check"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("database"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"counts": report["counts"], "errors": len(report["errors"])}))
    raise SystemExit(bool(report["errors"]))
