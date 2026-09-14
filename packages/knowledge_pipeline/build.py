"""Orchestration: manifest -> sources rows -> snapshots -> legal units."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from packages.knowledge_pipeline.fetch import FetchError, fetch_source, manifest
from packages.knowledge_pipeline.segment import (
    UnitDraft,
    segment_cap112,
    segment_html,
    segment_pdf,
)
from packages.persistence.models import AuditEvent, LegalUnit, Source


@dataclass
class SourceBuildReport:
    source_id: str
    parse_status: str
    units: int = 0
    reused_snapshot: bool = False
    drift: bool = False
    error: str | None = None


@dataclass
class BuildSummary:
    sources: list[SourceBuildReport] = field(default_factory=list)

    @property
    def total_units(self) -> int:
        return sum(s.units for s in self.sources)

    @property
    def parsed(self) -> int:
        return sum(1 for s in self.sources if s.parse_status == "parsed")


def _upsert_source(session: Session, entry: dict) -> Source:
    source = session.execute(
        select(Source).where(Source.source_id == entry["source_id"])
    ).scalar_one_or_none()
    if source is None:
        source = Source(source_id=entry["source_id"], title=entry["title"], url=entry["url"])
        session.add(source)
    source.title = entry["title"]
    source.publisher = entry.get("publisher")
    source.source_type = entry.get("source_type")
    source.url = entry["url"]
    source.structured_data_url = entry.get("structured_data_url")
    source.language = entry.get("language", "en")
    source.manifest_sha256 = entry.get("content_sha256")
    source.content_bytes = entry.get("content_bytes")
    source.content_type = entry.get("content_type")
    source.l0_in_scope = bool(entry.get("l0_in_scope", True))
    source.professional_validation_status = entry.get("professional_validation_status", "unverified")
    session.flush()
    return source


def _segment_for(entry: dict, content: bytes) -> list[UnitDraft]:
    content_type = (entry.get("content_type") or "").lower()
    if entry.get("structured_file", "") and entry["structured_file"].endswith(".xml"):
        return segment_cap112(content)
    if "pdf" in content_type:
        return segment_pdf(content, entry["source_id"])
    return segment_html(content, entry["source_id"])


def build_knowledge(session: Session, *, fetch: bool = True) -> BuildSummary:
    summary = BuildSummary()
    manifest_data = manifest()
    allowed = manifest_data.get("allowed_source_domains", [])

    for entry in manifest_data["sources"]:
        source = _upsert_source(session, entry)
        report = SourceBuildReport(source_id=source.source_id, parse_status="registered")

        if not source.l0_in_scope:
            source.parse_status = "out_of_scope"
            report.parse_status = "out_of_scope"
            summary.sources.append(report)
            continue
        if not fetch:
            report.parse_status = source.parse_status
            report.units = source.units_count
            summary.sources.append(report)
            continue

        try:
            result = fetch_source(entry, allowed)
        except FetchError as exc:
            source.parse_status = "failed"
            report.parse_status = "failed"
            report.error = str(exc)
            summary.sources.append(report)
            continue

        source.actual_sha256 = result.sha256
        source.snapshot_path = str(result.snapshot_path)
        source.retrieved_at = datetime.now(timezone.utc)
        source.http_status = result.http_status
        report.reused_snapshot = result.reused
        report.drift = result.drift

        try:
            drafts = _segment_for(entry, result.content)
        except Exception as exc:  # parse failure is recorded, not fatal to others
            source.parse_status = "failed"
            report.parse_status = "failed"
            report.error = f"segmentation failed: {exc}"
            summary.sources.append(report)
            continue

        session.execute(delete(LegalUnit).where(LegalUnit.source_db_id == source.id))
        for draft in drafts:
            session.add(
                LegalUnit(
                    source_db_id=source.id,
                    unit_ref=draft.unit_ref,
                    statute_locator=draft.statute_locator,
                    unit_type=draft.unit_type,
                    ordinal=draft.ordinal,
                    heading=draft.heading,
                    text=draft.text,
                    text_sha256=hashlib.sha256(draft.text.encode("utf-8")).hexdigest(),
                    language=draft.language,
                )
            )
        source.parse_status = "parsed"
        source.units_count = len(drafts)
        report.parse_status = "parsed"
        report.units = len(drafts)
        summary.sources.append(report)

    session.add(
        AuditEvent(
            organization_id=None,
            actor="knowledge_pipeline",
            action="build",
            entity_type="knowledge_package",
            entity_id=None,
            payload={
                "parsed": summary.parsed,
                "total_units": summary.total_units,
                "drift": [s.source_id for s in summary.sources if s.drift],
            },
        )
    )
    return summary
