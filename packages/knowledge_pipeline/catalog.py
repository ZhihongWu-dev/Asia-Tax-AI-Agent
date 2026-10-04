"""Validate and register a source-catalog package without ingesting legal text.

Usage: python -m packages.knowledge_pipeline.catalog [--search TOPIC]
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.persistence.db import session_scope
from packages.persistence.models import Source


CATALOG_PATH = Path(__file__).resolve().parents[2] / "knowledge/mainland_china/cross_border_dividends/source_manifest.json"
REQUIRED = {
    "source_id", "title", "publisher", "source_type", "url", "jurisdiction",
    "language", "publication_date", "effective_from", "effective_to", "topic_tags",
    "version_note", "coverage_note", "professional_validation_status",
}


def load_catalog(path: Path = CATALOG_PATH) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_catalog(data)
    return data


def validate_catalog(data: dict) -> None:
    if data.get("jurisdiction") != "CN" or data.get("coverage_level") != "source-catalog baseline":
        raise ValueError("Only the CN source-catalog baseline is supported")
    topics = data.get("topics")
    sources = data.get("sources")
    domains = data.get("allowed_source_domains")
    if not isinstance(topics, dict) or not topics or not isinstance(sources, list) or not sources:
        raise ValueError("Catalog needs declared topics and sources")
    if not isinstance(domains, list) or not domains or not data.get("coverage_gaps"):
        raise ValueError("Catalog needs domain allowlist and coverage gaps")
    date.fromisoformat(data["legal_coverage_cutoff"])
    date.fromisoformat(data["link_reviewed_at"])
    seen = set()
    covered = set()
    for entry in sources:
        if not isinstance(entry, dict) or REQUIRED - entry.keys():
            raise ValueError("Source metadata is incomplete")
        sid = entry["source_id"]
        if not isinstance(sid, str) or not sid.startswith("cn_") or sid in seen:
            raise ValueError(f"Duplicate or invalid CN source ID: {sid}")
        seen.add(sid)
        if entry["jurisdiction"] != "CN" or entry["language"] != "zh":
            raise ValueError(f"Wrong jurisdiction or language: {sid}")
        if entry["professional_validation_status"] != "unverified":
            raise ValueError(f"Unreviewed sources cannot be marked verified: {sid}")
        if not all(isinstance(entry[key], str) and entry[key].strip() for key in
                   ("title", "publisher", "source_type", "version_note", "coverage_note")):
            raise ValueError(f"Empty required text: {sid}")
        parsed = urlsplit(entry["url"])
        if parsed.scheme != "https" or parsed.hostname not in domains or parsed.username or parsed.password:
            raise ValueError(f"Unapproved source URL: {sid}")
        tags = entry["topic_tags"]
        if not isinstance(tags, list) or not tags or len(tags) != len(set(tags)) or not set(tags) <= topics.keys():
            raise ValueError(f"Unknown or duplicate topic tag: {sid}")
        covered.update(tags)
        dates = [date.fromisoformat(entry[key]) if entry[key] else None for key in
                 ("publication_date", "effective_from", "effective_to")]
        if dates[1] and dates[2] and dates[1] > dates[2]:
            raise ValueError(f"Invalid effective date range: {sid}")
    if covered != topics.keys():
        raise ValueError(f"Declared topics without official sources: {sorted(topics.keys() - covered)}")


def upsert_catalog(session: Session, data: dict) -> int:
    """Keep existing HK rows and the current CN row IDs stable on repeat runs."""
    validate_catalog(data)
    for entry in data["sources"]:
        source = session.execute(select(Source).where(Source.source_id == entry["source_id"])).scalar_one_or_none()
        if source is None:
            source = Source(source_id=entry["source_id"], title=entry["title"], url=entry["url"])
            session.add(source)
        elif source.jurisdiction != "CN":
            raise ValueError(f"Source ID belongs to another jurisdiction: {entry['source_id']}")
        for key in ("title", "publisher", "source_type", "url", "jurisdiction", "language",
                    "topic_tags", "version_note", "coverage_note", "professional_validation_status"):
            setattr(source, key, entry[key])
        for key in ("publication_date", "effective_from", "effective_to"):
            setattr(source, key, date.fromisoformat(entry[key]) if entry[key] else None)
        source.l0_in_scope = False  # HK FSIE retrieval must not treat this directory as parsed HK evidence.
        source.parse_status = "registered"
    session.flush()
    return len(data["sources"])


def search_catalog(session: Session, topic: str) -> list[Source]:
    """Topic IDs are declared in the manifest; no cross-region fallback."""
    if topic not in load_catalog()["topics"]:
        return []
    sources = session.execute(select(Source).where(Source.jurisdiction == "CN")).scalars().all()
    return sorted((s for s in sources if topic in (s.topic_tags or [])), key=lambda s: s.source_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Register or search mainland China official source catalog")
    parser.add_argument("--search", metavar="TOPIC", help="search one declared topic without changing data")
    args = parser.parse_args()
    data = load_catalog()
    with session_scope() as session:
        if args.search:
            for source in search_catalog(session, args.search):
                print(f"{source.source_id}\t{source.title}\t{source.url}")
        else:
            count = upsert_catalog(session, data)
            print(f"Registered {count} CN official source entries; legal text not ingested")


if __name__ == "__main__":
    main()
