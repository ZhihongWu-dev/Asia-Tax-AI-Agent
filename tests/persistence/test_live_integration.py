"""Live-DB integration test. Skipped unless FSIE_RUN_INTEGRATION=1.

Run after `make db-up && make migrate`:
    FSIE_RUN_INTEGRATION=1 .venv/bin/python -m pytest -m integration
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import func, select

from packages.knowledge_loader.loader import persist_knowledge
from packages.persistence.db import session_scope
from packages.persistence.models import EvaluationCase, RuleNode

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("FSIE_RUN_INTEGRATION") != "1",
        reason="set FSIE_RUN_INTEGRATION=1 to run live-DB integration tests",
    ),
]


def _counts(session, rule_set_id):
    # Per rule-set version: a new package version is a new rule set, by design.
    rules = session.scalar(
        select(func.count()).select_from(RuleNode).where(RuleNode.rule_set_id == rule_set_id)
    )
    cases = session.scalar(select(func.count()).select_from(EvaluationCase))
    return rules, cases


def test_load_is_idempotent():
    with session_scope() as session:
        first = persist_knowledge(session, run_validation=False)
        assert (first.rules_loaded, first.cases_loaded) == (6, 10)
    # Second run must converge, not duplicate.
    with session_scope() as session:
        second = persist_knowledge(session, run_validation=False)
        assert (second.rules_loaded, second.cases_loaded) == (6, 10)
        assert _counts(session, second.rule_set_id) == (6, 10)
