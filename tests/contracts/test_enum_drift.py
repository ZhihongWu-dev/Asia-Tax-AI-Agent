"""Python enums must not drift from the authoritative JSON Schema enum blocks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.contracts import enums
from packages.contracts.enums import values

ROOT = Path(__file__).resolve().parents[2]
DEFS = json.load(
    (ROOT / "packages/contracts/json_schemas/definitions.schema.json").open(encoding="utf-8")
)["$defs"]

PAIRS = [
    ("LifecycleStatus", enums.LifecycleStatus),
    ("ProfessionalValidationStatus", enums.ProfessionalValidationStatus),
    ("FactConfirmationStatus", enums.FactConfirmationStatus),
    ("NodeOutputStatus", enums.NodeOutputStatus),
    ("CaseTerminalState", enums.CaseTerminalState),
    ("EvidenceStatus", enums.EvidenceStatus),
    ("BlockingLevel", enums.BlockingLevel),
    ("CaseStatus", enums.CaseStatus),
    ("FactDomain", enums.FactDomain),
    ("FactDataType", enums.FactDataType),
]


@pytest.mark.parametrize("schema_name,py_enum", PAIRS)
def test_enum_matches_schema(schema_name, py_enum):
    assert set(DEFS[schema_name]["enum"]) == values(py_enum)


def test_judgement_chain_matches_schema():
    assert set(enums.JUDGEMENT_CHAIN) == set(DEFS["JudgementNodeKey"]["enum"])
    assert set(enums.JUDGEMENT_CHAIN.values()) <= set(range(0, 11))
