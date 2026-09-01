#!/usr/bin/env python3
"""Validate the Hong Kong FSIE candidate package against the shared contract.

Zero third-party dependencies. Two layers of validation:

1. In-package safety (unchanged): official HTTPS sources only, candidate assets
   stay professionally unverified, synthetic cases use safe terminal states.
2. Cross-file contract consistency (new): every fact field, evidence type, node
   key and blocker must resolve to the contract in packages/contracts — the fact
   dictionary, the shared enums and the JSON Schema definitions. The Python enum
   module and the JSON Schema enum blocks are cross-checked for drift.
"""

from __future__ import annotations

import importlib.util
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

CONTRACTS = ROOT / "packages" / "contracts"
SCHEMA_DIR = CONTRACTS / "json_schemas"
DEFINITIONS = SCHEMA_DIR / "definitions.schema.json"
FACT_DICT = CONTRACTS / "fact_dictionary" / "hk_fsie_fact_fields.v0.json"
ENUMS_PY = CONTRACTS / "enums.py"

SENTINELS = {"unknown", "conflict", "assumed", "not_applicable"}


def load(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_enums_module():
    spec = importlib.util.spec_from_file_location("fsie_contract_enums", ENUMS_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fail(errors, message):
    errors.append(message)


def enum_block(definitions, name):
    return set(definitions["$defs"][name]["enum"])


def main() -> int:
    errors = []

    # ---- load package + contract -----------------------------------------
    sources = load(SOURCES)
    rules = load(RULES)
    evidence = load(EVIDENCE)
    cases = load(CASES)
    definitions = load(DEFINITIONS)
    fact_dict = load(FACT_DICT)
    enums = load_enums_module()

    field_by_name = {f["field_name"]: f for f in fact_dict["fields"]}
    field_names = set(field_by_name)
    evidence_types = {e["type"] for e in fact_dict["controlled_evidence_types"]}

    node_keys = enum_block(definitions, "JudgementNodeKey")
    node_outputs = enum_block(definitions, "NodeOutputStatus")
    terminal_states = enum_block(definitions, "CaseTerminalState")

    # ---- contract self-check: Python enums must not drift from schema -----
    drift_pairs = [
        ("LifecycleStatus", enums.LifecycleStatus),
        ("ProfessionalValidationStatus", enums.ProfessionalValidationStatus),
        ("NodeOutputStatus", enums.NodeOutputStatus),
        ("CaseTerminalState", enums.CaseTerminalState),
        ("JudgementNodeKey", None),
        ("FactDomain", enums.FactDomain),
        ("BlockingLevel", enums.BlockingLevel),
        ("FactDataType", enums.FactDataType),
    ]
    for name, py_enum in drift_pairs:
        schema_values = enum_block(definitions, name)
        if name == "JudgementNodeKey":
            py_values = set(enums.JUDGEMENT_CHAIN.keys())
        else:
            py_values = enums.values(py_enum)
        if py_values != schema_values:
            fail(errors, f"enum drift in {name}: schema={sorted(schema_values)} python={sorted(py_values)}")
    if set(enums.JUDGEMENT_CHAIN.values()) - set(range(0, 11)):
        fail(errors, "judgement chain ordinals must be within 0..10")

    # ---- sources -----------------------------------------------------------
    source_items = sources.get("sources", [])
    source_ids = {item.get("source_id") for item in source_items}
    if sources.get("professional_status") != "unverified":
        fail(errors, "source manifest must remain professionally unverified")
    allowed_bases = {"ird.gov.hk", "elegislation.gov.hk", "data.one.gov.hk"}
    allowed_bases |= set(sources.get("allowed_source_domains", []))

    def is_official_https(value):
        parsed = urlparse(value or "")
        host = parsed.netloc
        host_ok = host in allowed_bases or any(host.endswith("." + b) for b in allowed_bases)
        return parsed.scheme == "https" and host_ok

    for item in source_items:
        sid = item.get("source_id")
        if not sid or not item.get("title") or not item.get("url"):
            fail(errors, f"source {sid!r} is missing identity fields")
        if not is_official_https(item.get("url", "")):
            fail(errors, f"source {sid!r} url is not an HTTPS official-source URL")
        structured_url = item.get("structured_data_url")
        if structured_url and not is_official_https(structured_url):
            fail(errors, f"source {sid!r} structured_data_url is not an HTTPS official-source URL")
        if item.get("professional_validation_status") != "unverified":
            fail(errors, f"source {sid!r} must remain unverified")

    # ---- rules -------------------------------------------------------------
    rule_ids = set()
    for rule in rules.get("rules", []):
        rid = rule.get("rule_id")
        if not rid or rid in rule_ids:
            fail(errors, f"duplicate or missing rule id: {rid!r}")
        rule_ids.add(rid)
        if rule.get("status") != "unverified":
            fail(errors, f"rule {rid} must remain unverified")
        if not rule.get("human_review_required"):
            fail(errors, f"rule {rid} must require human review in the candidate package")

        node = rule.get("node")
        if node not in node_keys:
            fail(errors, f"rule {rid} node {node!r} is not a canonical judgement node")
        elif "ordinal" not in rule:
            fail(errors, f"rule {rid} is missing ordinal")
        elif rule["ordinal"] != enums.JUDGEMENT_CHAIN[node]:
            fail(errors, f"rule {rid} ordinal {rule['ordinal']} != canonical {enums.JUDGEMENT_CHAIN[node]} for node {node}")

        for fact in rule.get("required_facts", []):
            if fact not in field_names:
                fail(errors, f"rule {rid} required_fact {fact!r} is not in the fact dictionary")
        for etype in rule.get("required_evidence", []):
            if etype not in evidence_types:
                fail(errors, f"rule {rid} required_evidence {etype!r} is not a controlled evidence type")
        for out in rule.get("outputs", []):
            if out not in node_outputs:
                fail(errors, f"rule {rid} output {out!r} is not a valid node output status")
        for sid in rule.get("source_ids", []):
            if sid not in source_ids:
                fail(errors, f"rule {rid} references unknown source {sid}")
        for dep in rule.get("depends_on_nodes", []):
            if dep not in node_keys:
                fail(errors, f"rule {rid} depends on unknown node {dep!r}")

    # ---- evidence requirements --------------------------------------------
    evidence_ids = set()
    for item in evidence.get("requirements", []):
        eid = item.get("evidence_id")
        if not eid or eid in evidence_ids:
            fail(errors, f"duplicate or missing evidence id: {eid!r}")
        evidence_ids.add(eid)
        facts = item.get("facts")
        if not isinstance(facts, list) or not facts:
            fail(errors, f"evidence {eid} must declare a non-empty 'facts' list")
        else:
            for fact in facts:
                if fact not in field_names:
                    fail(errors, f"evidence {eid} fact {fact!r} is not in the fact dictionary")
        etypes = item.get("evidence_types", [])
        if not etypes:
            fail(errors, f"evidence {eid} must declare 'evidence_types'")
        for etype in etypes:
            if etype not in evidence_types:
                fail(errors, f"evidence {eid} type {etype!r} is not a controlled evidence type")
        for rid in item.get("mandatory_for", []):
            if rid not in rule_ids:
                fail(errors, f"evidence {eid} references unknown rule {rid}")

    # ---- candidate cases ---------------------------------------------------
    for case in cases.get("cases", []):
        cid = case.get("case_id")
        if case.get("synthetic") is not True:
            fail(errors, f"case {cid} is not marked synthetic")
        if case.get("expected_state") not in terminal_states:
            fail(errors, f"case {cid} has an unsafe expected state")
        for key, value in case.get("facts", {}).items():
            if key not in field_names:
                fail(errors, f"case {cid} fact key {key!r} is not in the fact dictionary")
                continue
            spec = field_by_name[key]
            if spec["data_type"] == "enum" and isinstance(value, str):
                allowed = set(spec.get("enum_values", [])) | SENTINELS
                if value not in allowed:
                    fail(errors, f"case {cid} field {key}={value!r} is outside its enum {sorted(spec.get('enum_values', []))}")
            if spec["data_type"] in {"decimal", "integer"} and not isinstance(value, (int, float)) and value not in SENTINELS:
                fail(errors, f"case {cid} numeric field {key}={value!r} must be a number or a sentinel")
        for blocker in case.get("expected_blockers", []):
            if blocker not in field_names:
                fail(errors, f"case {cid} blocker {blocker!r} must name a dictionary field, not free text")

    # ---- result ------------------------------------------------------------
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        "FSIE package valid: "
        f"{len(source_items)} sources, {len(rule_ids)} rules, {len(evidence_ids)} evidence requirements, "
        f"{len(cases.get('cases', []))} synthetic cases; contract: {len(field_names)} fact fields, "
        f"{len(evidence_types)} evidence types"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
