"""Web API contract, offline: no database, no model calls."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from apps.api import main as api
from packages.contracts.enums import CaseTerminalState, values
from packages.intake import service
from packages.intake.extraction import ExtractionError
from packages.knowledge_loader import parser as knowledge_parser
from packages.model_adapter.client import ModelConfig, ModelError

client = TestClient(api.app)
CASE = "Fictional case for research only. A Hong Kong company received a foreign dividend."


class _Configured:
    model_name = "test-model"
    is_configured = True


@pytest.fixture()
def configured_model(monkeypatch):
    monkeypatch.setattr(api, "get_model_config", lambda: _Configured())


def test_health_never_exposes_the_database_password():
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert ":fsie@" not in body["database"]


def test_samples_are_well_formed_and_match_their_golden_fixtures():
    data = client.get("/api/samples").json()
    cases = data["cases"]
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids))
    fixtures = knowledge_parser.REPO_ROOT / "tests/fsie/natural_language_cases"
    golden = json.loads((fixtures / "expectations.json").read_text(encoding="utf-8"))
    for case in cases:
        assert len(f"WEB-{case['id']}:{'0' * 12}") <= 64  # execution_batch column width
        assert 20 <= len(case["text"]) <= api.MAX_CASE_CHARS
        assert case["text"].startswith("Fictional case")
        assert case["expected_state"] in values(CaseTerminalState) | {None}
        if case["maps_to"] in golden:
            assert case["expected_state"] == golden[case["maps_to"]]["expected_state"]


def test_analyze_requires_a_synthetic_confirmation(configured_model):
    response = client.post("/api/analyze", json={"text": CASE})
    assert response.status_code == 400
    assert "synthetic" in response.json()["detail"]


def test_analyze_rejects_too_short_or_too_long_text(configured_model):
    assert client.post("/api/analyze", json={"text": "short", "confirm_synthetic": True}).status_code == 422
    too_long = "x" * (api.MAX_CASE_CHARS + 1)
    assert client.post("/api/analyze", json={"text": too_long, "confirm_synthetic": True}).status_code == 422


def test_analyze_returns_503_without_a_model(monkeypatch):
    monkeypatch.setattr(api, "get_model_config", lambda: ModelConfig("", "", ""))
    response = client.post("/api/analyze", json={"text": CASE, "confirm_synthetic": True})
    assert response.status_code == 503


def test_analyze_strips_internal_fields(configured_model, monkeypatch):
    def fake(text, case_id=None):
        return {"case_id": case_id, "terminal_state": "research_only_output",
                "report_markdown": "# internal", "raw_facts": {"income_type": "dividend"}}

    monkeypatch.setattr(service, "analyze_case", fake)
    response = client.post(
        "/api/analyze", json={"text": CASE, "confirm_synthetic": True, "sample_id": "kept-offshore"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["case_id"] == "WEB-kept-offshore"
    assert "report_markdown" not in body and "raw_facts" not in body


@pytest.mark.parametrize(
    "error,status",
    [(ExtractionError("bad field"), 422), (ModelError("HTTP 500"), 502), (SystemExit("no rule set"), 503)],
)
def test_analyze_maps_pipeline_failures_to_http_errors(configured_model, monkeypatch, error, status):
    def boom(text, case_id=None):
        raise error

    monkeypatch.setattr(service, "analyze_case", boom)
    response = client.post("/api/analyze", json={"text": CASE, "confirm_synthetic": True})
    assert response.status_code == status
