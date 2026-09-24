"""Web API contract, offline: no database, no model calls."""

from __future__ import annotations

import json
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from apps.api import main as api
from packages.contracts.enums import CaseTerminalState, values
from packages.intake import service
from packages.intake.extraction import ExtractionError
from packages.knowledge_loader import parser as knowledge_parser
from packages.model_adapter.client import ModelConfig, ModelError
from packages.persistence.config import get_settings

client = TestClient(api.app)
CASE = "Fictional case for research only. A Hong Kong company received a foreign dividend."


class _Configured:
    model_name = "test-model"
    is_configured = True


@contextmanager
def _db_down():
    raise OperationalError("SELECT 1", {}, Exception("connection refused"))
    yield  # pragma: no cover


@pytest.fixture()
def configured_model(monkeypatch):
    monkeypatch.setattr(api, "get_model_config", lambda: _Configured())
    monkeypatch.setattr(api, "_preflight", lambda: None)


def _fake_analysis(text, case_id=None):
    return {"case_id": case_id, "terminal_state": "research_only_output",
            "report_markdown": "# internal", "raw_facts": {"income_type": "dividend"}}


def test_health_never_exposes_the_database_password():
    body = client.get("/health").json()
    configured = make_url(get_settings().database_url)
    reported = make_url(body["database"])
    assert body["status"] == "ok"
    assert configured.password and reported.password != configured.password
    assert reported.password == "***"


def test_meta_reports_503_when_the_database_is_down(monkeypatch):
    monkeypatch.setattr(api, "session_scope", _db_down)
    response = client.get("/api/meta")
    assert response.status_code == 503
    assert "database unavailable" in response.json()["detail"]


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


def test_analyze_rejects_too_short_blank_or_too_long_text(configured_model):
    for text in ("short", " " * 50, "x" * (api.MAX_CASE_CHARS + 1)):
        response = client.post("/api/analyze", json={"text": text, "confirm_synthetic": True})
        assert response.status_code == 422, repr(text[:10])


def test_analyze_returns_503_without_a_model(monkeypatch):
    monkeypatch.setattr(api, "get_model_config", lambda: ModelConfig("", "", ""))
    response = client.post("/api/analyze", json={"text": CASE, "confirm_synthetic": True})
    assert response.status_code == 503


def test_preflight_stops_before_the_model_when_the_database_is_down(monkeypatch):
    monkeypatch.setattr(api, "get_model_config", lambda: _Configured())
    monkeypatch.setattr(api, "session_scope", _db_down)

    def must_not_run(*_args, **_kwargs):
        raise AssertionError("the model must not be called when the database is down")

    monkeypatch.setattr(service, "analyze_case", must_not_run)
    response = client.post("/api/analyze", json={"text": CASE, "confirm_synthetic": True})
    assert response.status_code == 503


def test_analyze_strips_internal_fields_and_uses_known_preset_ids(configured_model, monkeypatch):
    monkeypatch.setattr(service, "analyze_case", _fake_analysis)
    response = client.post(
        "/api/analyze", json={"text": CASE, "confirm_synthetic": True, "sample_id": "kept-offshore"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["case_id"] == "WEB-kept-offshore"
    assert "report_markdown" not in body and "raw_facts" not in body


def test_unknown_sample_ids_never_become_case_ids(configured_model, monkeypatch):
    monkeypatch.setattr(service, "analyze_case", _fake_analysis)
    response = client.post(
        "/api/analyze", json={"text": CASE, "confirm_synthetic": True, "sample_id": "x" * 80}
    )
    assert response.status_code == 200
    assert response.json()["case_id"] is None


@pytest.mark.parametrize(
    "error,status",
    [
        (ExtractionError("bad field"), 422),
        (ModelError("HTTP 500"), 502),
        (OperationalError("INSERT", {}, Exception("server closed the connection")), 503),
        (SystemExit("no rule set"), 503),
    ],
)
def test_analyze_maps_pipeline_failures_to_json_http_errors(configured_model, monkeypatch, error, status):
    def boom(text, case_id=None):
        raise error

    monkeypatch.setattr(service, "analyze_case", boom)
    response = client.post("/api/analyze", json={"text": CASE, "confirm_synthetic": True})
    assert response.status_code == status
    assert "detail" in response.json()
