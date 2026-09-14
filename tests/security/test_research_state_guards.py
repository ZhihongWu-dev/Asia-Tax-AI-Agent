"""Explicit proof that the L0 research state cannot be bypassed (PRD 11.1).

Guards under test:
1. The contract validator refuses to load rules/sources marked verified.
2. The knowledge loader runs that validator before touching the database.
3. The report watermark is unconditional — no render path can drop it.
"""

from __future__ import annotations

import importlib.util
import inspect
import json

import pytest

from packages.knowledge_loader import loader as loader_mod
from packages.knowledge_loader import parser as knowledge_parser
from packages.reporting.renderer import (
    RESEARCH_WATERMARK,
    NodeRow,
    ReportInput,
    render_markdown,
)

REPO_ROOT = knowledge_parser.REPO_ROOT


def _load_validator_module():
    spec = importlib.util.spec_from_file_location(
        "validate_fsie_package", REPO_ROOT / "scripts/validate_fsie_package.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _mutated_rules_payload() -> dict:
    payload = knowledge_parser.load_rules_payload()
    payload["rules"][0]["status"] = "verified"  # simulate a forged flip
    return payload


def test_validator_refuses_verified_rules(tmp_path):
    validator = _load_validator_module()
    forged = tmp_path / "rules.json"
    forged.write_text(json.dumps(_mutated_rules_payload()), encoding="utf-8")
    validator.RULES = forged
    rc = validator.main()
    assert rc == 1, "validator must reject verified rules"


def test_validator_refuses_verified_sources(tmp_path):
    validator = _load_validator_module()
    manifest = json.loads(
        (REPO_ROOT / "knowledge/hong_kong/fsie/source_manifest.json").read_text(encoding="utf-8")
    )
    manifest["sources"][0]["professional_validation_status"] = "verified"
    forged = tmp_path / "source_manifest.json"
    forged.write_text(json.dumps(manifest), encoding="utf-8")
    validator.SOURCES = forged
    rc = validator.main()
    assert rc == 1, "validator must reject verified sources"


def test_loader_gates_on_the_validator(monkeypatch):
    """persist_knowledge must validate first; a failed validator must stop the
    load before any database interaction."""

    class TripwireSession:
        def __getattribute__(self, name):
            raise AssertionError(f"session.{name} touched before validation")

    def boom() -> None:
        raise RuntimeError("validation failed")

    monkeypatch.setattr(loader_mod, "validate_package_or_raise", boom)
    with pytest.raises(RuntimeError, match="validation failed"):
        loader_mod.persist_knowledge(TripwireSession(), run_validation=True)


def _minimal_report(terminal: str) -> ReportInput:
    return ReportInput(
        case_id="GUARD-001",
        case_description=None,
        synthetic=True,
        execution_batch="GUARD-001:test",
        generated_at="2026-09-05T00:00:00+00:00",
        organization_name="L0 Research Organisation",
        rule_set_version="0.2.0",
        git_commit=None,
        terminal_state=terminal,
        node_rows=(NodeRow(node="scope", ordinal=1, rule_id="FSIE-SCOPE-001", output="unknown"),),
    )


@pytest.mark.parametrize("terminal", [
    "research_only_output", "human_review_required", "stop_and_escalate",
])
def test_watermark_is_unconditional_for_every_terminal_state(terminal):
    assert RESEARCH_WATERMARK in render_markdown(_minimal_report(terminal))


def test_renderer_exposes_no_watermark_switch():
    params = inspect.signature(render_markdown).parameters
    assert set(params) == {"report"}, (
        "render_markdown must take only the report; no flag may disable the watermark"
    )
