"""Reports rebuilt from the DB must be complete and reproducible.

Skipped unless FSIE_RUN_INTEGRATION=1. Run after db-up + migrate + load.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import delete

from packages.knowledge_loader.loader import persist_knowledge
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
from packages.reporting.cli import collect_report_inputs, write_reports
from packages.reporting.renderer import RESEARCH_WATERMARK
from packages.rule_engine.cli import run_all

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("FSIE_RUN_INTEGRATION") != "1",
        reason="set FSIE_RUN_INTEGRATION=1 to run live-DB integration tests",
    ),
]


@pytest.fixture()
def clean_runtime():
    with session_scope() as session:
        for model in (
            EvaluationResult,
            RuleExecution,
            EvaluationRun,
            FactVersion,
            Fact,
            CaseFile,
            AuditEvent,
            Organization,
        ):
            session.execute(delete(model))
    yield


def test_reports_rebuild_from_the_db_for_every_case(clean_runtime, tmp_path):
    with session_scope() as session:
        persist_knowledge(session, run_validation=False)
        run_all(session)

    with session_scope() as session:
        inputs = collect_report_inputs(session)

    assert len({i.case_id for i in inputs}) == 10
    for report in inputs:
        assert report.rule_set_version == "0.2.0"
        assert report.terminal_state in {
            "research_only_output", "human_review_required", "stop_and_escalate"
        }
        assert len(report.node_rows) == 6

    paths = write_reports(inputs, base_dir=tmp_path)
    assert len(paths) == 10
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert RESEARCH_WATERMARK in text
        assert "判断链节点轨迹" in text


def test_rerender_from_the_same_db_state_is_byte_identical(clean_runtime, tmp_path):
    with session_scope() as session:
        persist_knowledge(session, run_validation=False)
        run_all(session)

    with session_scope() as session:
        first = {p.name: p.read_text() for p in write_reports(collect_report_inputs(session), base_dir=tmp_path / "a")}
    with session_scope() as session:
        second = {p.name: p.read_text() for p in write_reports(collect_report_inputs(session), base_dir=tmp_path / "b")}
    assert first == second
