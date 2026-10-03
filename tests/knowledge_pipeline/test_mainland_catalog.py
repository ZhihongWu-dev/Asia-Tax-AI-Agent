"""The CN catalog is metadata only and must not alter HK FSIE evidence."""

from copy import deepcopy

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from packages.knowledge_pipeline.catalog import load_catalog, search_catalog, upsert_catalog, validate_catalog
from packages.persistence.models import Source


def test_catalog_declared_topics_and_domain_guard():
    data = load_catalog()
    assert len(data["sources"]) >= 5
    assert {tag for source in data["sources"] for tag in source["topic_tags"]} == set(data["topics"])
    bad = deepcopy(data)
    bad["sources"][0]["url"] = "https://example.com/unofficial"
    with pytest.raises(ValueError, match="Unapproved source URL"):
        validate_catalog(bad)


def test_upsert_is_idempotent_and_hk_source_stays_out_of_cn_results():
    engine = create_engine("sqlite://")
    Source.__table__.create(engine)
    data = load_catalog()
    try:
        with Session(engine) as session:
            session.add(Source(source_id="hk_fixture", title="HK", url="https://www.ird.gov.hk/", jurisdiction="HK"))
            session.commit()
            assert upsert_catalog(session, data) == len(data["sources"])
            session.commit()
            ids = {s.source_id: s.id for s in session.scalars(select(Source)).all()}
            assert upsert_catalog(session, data) == len(data["sources"])
            session.commit()
            assert ids == {s.source_id: s.id for s in session.scalars(select(Source)).all()}
            hits = search_catalog(session, "dividend_withholding")
            assert hits and all(s.jurisdiction == "CN" and not s.l0_in_scope for s in hits)
            assert session.scalar(select(Source).where(Source.source_id == "hk_fixture")).title == "HK"
    finally:
        engine.dispose()
