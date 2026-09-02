"""Live end-to-end evaluation runs. Skipped unless FSIE_RUN_INTEGRATION=1.

Run after `make db-up && make migrate && make load`:
    FSIE_RUN_INTEGRATION=1 .venv/bin/python -m pytest -m integration
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import delete, func, select

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
    """Each test establishes its own baseline: wipe runtime tables, keep knowledge."""
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


def test_evaluation_cases_run_end_to_end_and_pass_their_golden_expectations(clean_runtime):
    with session_scope() as session:
        persist_knowledge(session, run_validation=False)
        reports = run_all(session)

    assert len(reports) == 3
    assert all(r.passed is True for r in reports), [
        (r.case_id, r.terminal_state, r.blockers) for r in reports if not r.passed
    ]
    assert {r.case_id for r in reports} == {"SYN-FSIE-001", "SYN-FSIE-002", "SYN-FSIE-003"}

    with session_scope() as session:
        runs = session.scalar(select(func.count()).select_from(EvaluationRun))
        executions = session.scalar(select(func.count()).select_from(RuleExecution))
        results = session.scalar(select(func.count()).select_from(EvaluationResult))
        facts = session.scalar(select(func.count()).select_from(Fact))
    # 3 cases x 6 nodes, fact cards of 6 + 5 + 7 facts.
    assert runs == 3
    assert executions == 18
    assert results == 18
    assert facts == 18


def test_rerun_appends_new_batches_without_duplicating_facts(clean_runtime):
    with session_scope() as session:
        first = run_all(session)
        second = run_all(session)

    assert {r.execution_batch for r in first}.isdisjoint(
        {r.execution_batch for r in second}
    )

    with session_scope() as session:
        runs = session.scalar(select(func.count()).select_from(EvaluationRun))
        facts = session.scalar(select(func.count()).select_from(Fact))
        versions = session.scalar(select(func.count()).select_from(FactVersion))
    assert runs == 6
    assert facts == 18  # upserted, never duplicated
    assert versions == 18  # unchanged values create no new versions
