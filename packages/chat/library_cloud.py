"""Bounded, read-only lookup of the separately uploaded public law library.

This does not turn a retrieved clause into a tax conclusion. Callers must retain
the source and library version when presenting or using a passage.
"""
from __future__ import annotations

from functools import lru_cache
from hashlib import sha256

from sqlalchemy import create_engine, text

from packages.persistence.config import get_settings


@lru_cache(maxsize=1)
def _engine():
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=0,
        connect_args={"connect_timeout": 3, "options": "-c statement_timeout=5000"},
    )


def search_library(query: str, jurisdiction: str, limit: int = 6) -> dict:
    """Search a named jurisdiction without exposing the private schema to clients."""
    query = query.strip()
    jurisdiction = jurisdiction.strip().lower()
    if not 2 <= len(query) <= 120 or not jurisdiction.isascii() or not jurisdiction.isalpha() or len(jurisdiction) != 2:
        raise ValueError("invalid_library_query")
    if not 1 <= limit <= 10:
        raise ValueError("invalid_library_limit")

    with _engine().connect() as connection, connection.begin():
        connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
        version = dict(connection.execute(text(
            "SELECT key, value FROM database.meta WHERE key IN ('uploaded_at', 'spec_version', 'tools_commit')"
        )).all())
        rows = connection.execute(text("""
            SELECT c.cite_id, c.label, left(c.text, 5000) AS passage,
                   d.id AS document_id, d.title, d.url, d.sha256 AS document_sha256,
                   d.lang, d.effective_from, d.effective_to
            FROM database.clause AS c
            JOIN database.doc AS d ON d.id = c.doc_id
            WHERE d.jur = :jurisdiction
              AND (c.cite_id = :query
                   OR position(lower(:query) in lower(c.text)) > 0
                   OR position(lower(:query) in lower(d.title)) > 0)
            ORDER BY CASE WHEN c.cite_id = :query THEN 0 ELSE 1 END, c.cite_id
            LIMIT :limit
        """), {"query": query, "jurisdiction": jurisdiction, "limit": limit}).mappings().all()

    return {
        "status": "available" if rows else "no_matching_units",
        "library_version": version,
        "jurisdiction": jurisdiction,
        "passages": [
            {**dict(row), "passage_sha256": sha256(row["passage"].encode("utf-8")).hexdigest()}
            for row in rows
        ],
    }
