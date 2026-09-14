"""Offline extraction tests with a stubbed model client."""

from __future__ import annotations

import pytest

from packages.intake.extraction import ExtractionError, extract_facts, validate_candidates
from packages.intake.prompting import build_system_prompt, build_user_prompt, field_catalog


class StubClient:
    def __init__(self, answers: list[dict]):
        self._answers = list(answers)
        self.calls: list[str] = []

        class _Cfg:
            model_name = "stub-model"

        self.config = _Cfg()

    def chat_json(self, system, user, **kwargs):
        self.calls.append(user)
        return self._answers.pop(0)


def test_prompt_contains_the_dictionary_contract():
    system = build_system_prompt()
    user = build_user_prompt("某公司在香港经营业务。")
    assert "禁止自造字段" in system
    assert "field_name" in user or "字段词典" in user
    for f in field_catalog()[:3]:
        assert f["field_name"] in user


def test_valid_candidates_are_accepted():
    client = StubClient([{"mne_group_status": "yes", "holding_percentage_pct": "15"}])
    result = extract_facts("x", client)
    assert result.facts == {"mne_group_status": "yes", "holding_percentage_pct": 15}
    assert result.repair_rounds == 0
    assert result.model == "stub-model"


def test_unknown_field_triggers_repair_then_succeeds():
    client = StubClient([
        {"mne_group_status": "yes", "ghost": "x"},
        {"mne_group_status": "yes"},
    ])
    result = extract_facts("x", client)
    assert result.facts == {"mne_group_status": "yes"}
    assert result.repair_rounds == 1
    assert "ghost" in client.calls[1]


def test_unrepairable_candidates_raise():
    client = StubClient([{"ghost": "x"}, {"ghost2": "y"}])
    with pytest.raises(ExtractionError):
        extract_facts("x", client)


def test_enum_violation_is_rejected():
    accepted, errors = validate_candidates({"income_type": "salary"})
    assert accepted == {}
    assert errors


def test_conflict_and_unknown_sentinels_pass_enum_validation():
    accepted, errors = validate_candidates(
        {"receipt_location": "conflict", "mne_group_status": "unknown"}
    )
    assert accepted == {"receipt_location": "conflict", "mne_group_status": "unknown"}
    assert errors == []
