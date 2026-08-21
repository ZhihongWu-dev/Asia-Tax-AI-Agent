#!/usr/bin/env python3
"""Validate the initial Hong Kong FSIE package without third-party dependencies."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "knowledge" / "hong_kong" / "fsie"
SOURCES = PACKAGE / "source_manifest.json"
RULES = PACKAGE / "rules.json"
EVIDENCE = PACKAGE / "evidence_requirements.json"
CASES = ROOT / "tests" / "fsie" / "candidate_cases.json"


def load(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def fail(errors, message):
    errors.append(message)


def main() -> int:
    errors = []
    sources = load(SOURCES)
    rules = load(RULES)
    evidence = load(EVIDENCE)
    cases = load(CASES)

    source_items = sources.get("sources", [])
    source_ids = {item.get("source_id") for item in source_items}
    if sources.get("professional_status") != "unverified":
        fail(errors, "source manifest must remain professionally unverified")
    for item in source_items:
        source_id = item.get("source_id")
        if not source_id or not item.get("title") or not item.get("url"):
            fail(errors, f"source {source_id!r} is missing identity fields")
        parsed = urlparse(item.get("url", ""))
        if parsed.scheme != "https" or not parsed.netloc.endswith("ird.gov.hk"):
            fail(errors, f"source {source_id!r} is not an HTTPS IRD source")
        if item.get("professional_validation_status") != "unverified":
            fail(errors, f"source {source_id!r} must remain unverified")

    rule_ids = set()
    for rule in rules.get("rules", []):
        rule_id = rule.get("rule_id")
        if not rule_id or rule_id in rule_ids:
            fail(errors, f"duplicate or missing rule id: {rule_id!r}")
        rule_ids.add(rule_id)
        if rule.get("status") != "unverified":
            fail(errors, f"rule {rule_id} must remain unverified")
        for source_id in rule.get("source_ids", []):
            if source_id not in source_ids:
                fail(errors, f"rule {rule_id} references unknown source {source_id}")
        if not rule.get("human_review_required"):
            fail(errors, f"rule {rule_id} must require human review in the candidate package")

    evidence_ids = set()
    for item in evidence.get("requirements", []):
        evidence_id = item.get("evidence_id")
        if not evidence_id or evidence_id in evidence_ids:
            fail(errors, f"duplicate or missing evidence id: {evidence_id!r}")
        evidence_ids.add(evidence_id)
        for rule_id in item.get("mandatory_for", []):
            if rule_id not in rule_ids:
                fail(errors, f"evidence {evidence_id} references unknown rule {rule_id}")

    for case in cases.get("cases", []):
        if case.get("synthetic") is not True:
            fail(errors, f"case {case.get('case_id')} is not marked synthetic")
        if case.get("expected_state") not in {"research_only_output", "stop_and_escalate", "human_review_required"}:
            fail(errors, f"case {case.get('case_id')} has an unsafe expected state")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"FSIE package valid: {len(source_items)} sources, {len(rule_ids)} rules, {len(evidence_ids)} evidence requirements, {len(cases.get('cases', []))} synthetic cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
