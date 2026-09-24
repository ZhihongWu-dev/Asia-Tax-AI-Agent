"""Live knowledge pipeline test (snapshots are reused once fetched).

Skipped unless FSIE_RUN_INTEGRATION=1. First run downloads official sources;
later runs reuse immutable snapshots.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import func, select

from packages.knowledge_pipeline.build import build_knowledge
from packages.knowledge_pipeline.fetch import manifest
from packages.persistence.db import session_scope
from packages.persistence.models import LegalUnit, Source

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("FSIE_RUN_INTEGRATION") != "1",
        reason="set FSIE_RUN_INTEGRATION=1 to run live-DB integration tests",
    ),
]


def test_build_snapshots_and_segments_all_l0_sources():
    with session_scope() as session:
        summary = build_knowledge(session)

    # Expected counts follow the manifest, so adding a source does not break this test.
    registered = manifest()["sources"]
    in_scope = [s for s in registered if s.get("l0_in_scope", True)]
    assert summary.parsed == len(in_scope)  # out-of-scope sources are registered, not parsed
    assert summary.total_units > 400
    assert not any(s.parse_status == "failed" for s in summary.sources)

    with session_scope() as session:
        sources = session.scalar(select(func.count()).select_from(Source))
        units = session.scalar(select(func.count()).select_from(LegalUnit))
        participation = session.execute(
            select(LegalUnit).where(LegalUnit.statute_locator == "s.15M(2)")
        ).scalars().all()
    assert sources == len(registered)
    assert units == summary.total_units
    assert len(participation) == 1
    assert "5%" in participation[0].text and "12" in participation[0].text


def test_rebuild_is_idempotent():
    with session_scope() as session:
        first = build_knowledge(session)
    with session_scope() as session:
        second = build_knowledge(session)
    assert first.total_units == second.total_units
    assert all(s.reused_snapshot for s in second.sources if s.parse_status == "parsed")
