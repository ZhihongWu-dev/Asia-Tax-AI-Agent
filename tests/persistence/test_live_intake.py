"""Live NL intake: real model extracts facts; the deterministic chain must
land on the same terminal state as the mapped golden case.

Requires FSIE_RUN_INTEGRATION=1 AND a configured model adapter
(FSIE_MODEL_BASE_URL / FSIE_MODEL_API_KEY / FSIE_MODEL_NAME in .env).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from sqlalchemy import delete

from packages.intake.cli import run_intake
from packages.knowledge_loader import parser as knowledge_parser
from packages.model_adapter.client import get_model_config
from packages.persistence.db import session_scope
from packages.persistence.models import (
    AuditEvent,
    CaseFile,
    EvaluationResult,
    EvaluationRun,
    Fact,
    FactVersion,
    Organization,
    RuleExecution,
)

FIXTURE_DIR = knowledge_parser.REPO_ROOT / "tests/fsie/natural_language_cases"

_model_configured = get_model_config().is_configured

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("FSIE_RUN_INTEGRATION") != "1",
        reason="set FSIE_RUN_INTEGRATION=1 to run live-DB integration tests",
    ),
    pytest.mark.skipif(not _model_configured, reason="model adapter not configured in .env"),
]


@pytest.fixture()
def clean_runtime():
    with session_scope() as session:
        for model in (
            EvaluationResult, RuleExecution, EvaluationRun, FactVersion,
            Fact, CaseFile, AuditEvent, Organization,
        ):
            session.execute(delete(model))
    yield


def test_all_nl_fixtures_reach_the_golden_terminal_states(clean_runtime):
    expectations = json.loads((FIXTURE_DIR / "expectations.json").read_text(encoding="utf-8"))
    for name, expected in sorted(expectations.items()):
        result = run_intake(FIXTURE_DIR / f"{name}.txt", case_id=name)
        assert result["terminal_state"] == expected["expected_state"], (
            f"{name}: got {result['terminal_state']}, "
            f"expected {expected['expected_state']} (facts={result['facts']})"
        )
        assert Path(result["report_path"]).exists()
        report_text = Path(result["report_path"]).read_text(encoding="utf-8")
        assert "L0 内部研究原型" in report_text
