"""Migrate structural identifiers only; never infer tax values or legal equivalence."""
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path


def normalize(text):
    return re.sub(r"\s+", "", text)


def reconcile(params, decisions, clauses):
    params = [dict(row) for row in params]
    decisions = [dict(row) for row in decisions]
    occupied = {row["param_id"] for row in params}
    renames = {}
    for row in params:
        old = row["param_id"]
        stem = ".".join(row[key] for key in ("scope", "slot", "name"))
        if old == stem or old.startswith(stem + "."):
            continue
        # A stable suffix keeps distinct historical observations distinct.
        new = stem + ".legacy_" + hashlib.sha256(old.encode()).hexdigest()[:12]
        if new in occupied:
            raise ValueError("parameter_id_collision: " + new)
        occupied.add(new)
        renames[old] = new
        row["param_id"] = new
    for row in params:
        if row.get("superseded_by") in renames:
            row["superseded_by"] = renames[row["superseded_by"]]
    ids = {row["cite_id"] for row in clauses}
    by_doc = {}
    for clause in clauses:
        by_doc.setdefault(clause["doc_id"], []).append(clause)
    rebindings, unresolved = [], []
    for table, rows, key in (("param", params, "param_id"), ("decision", decisions, "id")):
        for row in rows:
            old = row.get("cite_id", "")
            if not old or old in ids:
                continue
            quote = normalize(row.get("quote", ""))
            matches = [c["cite_id"] for c in by_doc.get(old.split("#")[0], [])
                       if quote and quote in normalize(c["text"])]
            record = {"table": table, "id": row[key], "old_cite_id": old, "matches": matches}
            if len(matches) == 1:
                row["cite_id"] = matches[0]
                rebindings.append(record)
            else:
                unresolved.append(record)
    return params, decisions, {"parameter_renames": renames, "exact_quote_rebindings": rebindings,
                               "unresolved_citations": unresolved}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("database"))
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    csv.field_size_limit(10**9)
    data, headers = {}, {}
    for name in ("param", "decision", "clause"):
        with (args.root / (name + ".csv")).open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            headers[name] = reader.fieldnames
            data[name] = list(reader)
    params, decisions, report = reconcile(data["param"], data["decision"], data["clause"])
    report["applied"] = args.apply
    report["legal_review"] = "not_established_by_structural_migration"
    args.report.parent.mkdir(parents=True, exist_ok=True)
    # Never overwrite a previous migration record with an empty subsequent run.
    if args.report.exists():
        raise FileExistsError(args.report)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.apply:
        for name, records in (("param", params), ("decision", decisions)):
            with (args.root / (name + ".csv")).open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=headers[name])
                writer.writeheader()
                writer.writerows(records)
    print(json.dumps({key: len(report[key]) for key in
                      ("parameter_renames", "exact_quote_rebindings", "unresolved_citations")}))


if __name__ == "__main__":
    main()
