"""Offline parsing of the Git knowledge package (no database required)."""

from __future__ import annotations

import json

from packages.contracts.enums import JUDGEMENT_CHAIN, NodeOutputStatus, values
from packages.knowledge_loader import parser


def test_rules_payload_is_contract_shaped():
    rules = parser.load_rules_payload()
    assert rules["rule_package_version"] == "0.2.0"
    assert len(rules["rules"]) == 6
    for rule in rules["rules"]:
        assert rule["node"] in JUDGEMENT_CHAIN
        assert rule["ordinal"] == JUDGEMENT_CHAIN[rule["node"]]
        assert set(rule["outputs"]) <= values(NodeOutputStatus)
        assert rule["human_review_required"] is True
        assert rule["status"] == "unverified"


def test_cases_payload_is_synthetic_and_uses_dictionary_fields():
    repo_root = parser.REPO_ROOT
    dictionary = json.load(
        (repo_root / "packages/contracts/fact_dictionary/hk_fsie_fact_fields.v0.json").open(
            encoding="utf-8"
        )
    )
    field_names = {f["field_name"] for f in dictionary["fields"]}

    cases = parser.load_cases_payload()
    assert len(cases["cases"]) == 3
    for case in cases["cases"]:
        assert case["synthetic"] is True
        assert case["case_id"].startswith("SYN-FSIE-")
        assert set(case["facts"]) <= field_names
        assert set(case["expected_blockers"]) <= field_names
