"""What analyze_case writes to the database, without calling a model.
Skipped unless FSIE_RUN_INTEGRATION=1 (needs the local database, loaded).
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import select

from packages.intake.extraction import ExtractionResult
from packages.intake.service import analyze_case
from packages.persistence.db import session_scope
from packages.persistence.models import AuditEvent, CaseFile, Fact, FactVersion, RuleExecution

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("FSIE_RUN_INTEGRATION") != "1",
        reason="set FSIE_RUN_INTEGRATION=1 to run live-DB integration tests",
    ),
]

FACTS = {
    "entity_hk_business_status": "yes",
    "mne_group_status": "yes",
    "income_type": "dividend",
    "receipt_location": "received_in_hk",
    "holding_percentage_pct": 15,
    "continuous_holding_period_months": 18,
    "foreign_tax_on_dividend_or_underlying_profit": "unknown",
}


def _extraction(facts):
    return ExtractionResult(facts=dict(facts), model="offline-fixture", repair_rounds=0)


def test_analysis_persists_facts_executions_and_provenance():
    case_id = f"TEST-{uuid.uuid4().hex[:8]}"
    result = analyze_case("Fictional case used by the persistence test.", case_id, extraction=_extraction(FACTS))
    assert result["terminal_state"] == "human_review_required"
    assert result["engine_commit"]

    with session_scope() as session:
        case = session.execute(select(CaseFile).where(CaseFile.external_ref == case_id)).scalar_one()
        facts = {f.field_name: f for f in session.execute(select(Fact).where(Fact.case_id == case.id)).scalars()}
        executions = session.execute(
            select(RuleExecution).where(RuleExecution.execution_batch == result["execution_batch"])
        ).scalars().all()
        provenance = session.execute(
            select(AuditEvent).where(AuditEvent.action == "extract_facts", AuditEvent.entity_id == str(case.id))
        ).scalars().all()

        assert set(facts) == set(FACTS)
        assert facts["income_type"].confirmation_status == "ai_candidate"
        assert facts["foreign_tax_on_dividend_or_underlying_profit"].confirmation_status == "unknown"
        assert facts["foreign_tax_on_dividend_or_underlying_profit"].value is None
        assert len(executions) == len([row for row in result["chain"] if row["implemented"]])
        assert case.case_status == "needs_human_judgment"
        [event] = provenance
        assert event.payload["model"] == "offline-fixture"
        assert event.payload["engine_commit"] == result["engine_commit"]
        assert event.payload["rule_set_version"] == result["rule_set_version"]
        assert len(event.payload["text_sha256"]) == 64


def test_a_changed_fact_on_rerun_appends_a_version():
    case_id = f"TEST-{uuid.uuid4().hex[:8]}"
    analyze_case("Fictional case used by the persistence test.", case_id, extraction=_extraction(FACTS))
    changed = dict(FACTS, holding_percentage_pct=4)
    result = analyze_case("Fictional case used by the persistence test.", case_id, extraction=_extraction(changed))
    assert result["terminal_state"] == "research_only_output"

    with session_scope() as session:
        case = session.execute(select(CaseFile).where(CaseFile.external_ref == case_id)).scalar_one()
        fact = session.execute(
            select(Fact).where(Fact.case_id == case.id, Fact.field_name == "holding_percentage_pct")
        ).scalar_one()
        versions = session.execute(
            select(FactVersion.version_no, FactVersion.value)
            .where(FactVersion.fact_id == fact.id).order_by(FactVersion.version_no)
        ).all()
        assert fact.value == 4
        assert [(v.version_no, v.value) for v in versions] == [(1, 15), (2, 4)]
