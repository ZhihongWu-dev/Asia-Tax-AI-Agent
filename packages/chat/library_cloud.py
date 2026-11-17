"""Bounded, read-only lookup of the separately uploaded public law library.

This does not turn a retrieved clause into a tax conclusion. Callers must retain
the source and library version when presenting or using a passage.
"""
from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
import json
import re

from sqlalchemy import create_engine, text

from packages.persistence.config import get_settings
from packages.chat.library_overlay import (load_candidates, admitted_rows, matching_rows,
                                         validate_base_rows, blocked_citations)


class LibraryVersionChanged(ValueError):
    """A caller's pinned base/review snapshot no longer matches the library."""


def _snapshot(version, reviews, expected_version):
    if not version.get('uploaded_at'):
        raise LibraryVersionChanged('library_version_missing')
    # Include review contents, not just status/count: a source replacement or
    # changed review decision must invalidate an already pinned read.
    digest = sha256(json.dumps(reviews, sort_keys=True, separators=(',', ':'),
                               default=str).encode('utf-8')).hexdigest()
    snapshot = {**version, 'review_sha256': digest}
    if any(row['base_uploaded_at'] != version['uploaded_at'] for row in reviews):
        raise LibraryVersionChanged('library_review_base_changed')
    if expected_version is not None and snapshot != expected_version:
        raise LibraryVersionChanged('library_version_changed')
    return snapshot


@lru_cache(maxsize=1)
def _engine():
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=0,
        connect_args={"connect_timeout": 3, "options": "-c statement_timeout=5000"},
    )


def _read_library_state(connection, expected_version=None):
    """Read version and admission metadata inside the caller's read-only snapshot."""
    source_commit, candidates, overlay_hash = load_candidates()
    version = dict(connection.execute(text(
        "SELECT key, value FROM database.meta WHERE key IN ('uploaded_at', 'spec_version', 'tools_commit')"
    )).all())
    reviews = [dict(row) for row in connection.execute(text(
        'SELECT * FROM database_integration.source_review ORDER BY cite_id'
    )).mappings().all()]
    version['overlay_bundle_sha256'] = overlay_hash
    version = _snapshot(version, reviews, expected_version)
    overlay = admitted_rows(source_commit, candidates, reviews)
    if overlay:
        bases = [dict(r) for r in connection.execute(text('''
            SELECT c.cite_id, c.doc_id, c.text, d.sha256 AS document_sha256
            FROM database.clause c JOIN database.doc d ON d.id = c.doc_id
            WHERE c.cite_id = ANY(:ids)
        '''), {'ids': [row['cite_id'] for row in overlay]}).mappings().all()]
        try:
            validate_base_rows(overlay, candidates, bases)
        except ValueError as exc:
            raise LibraryVersionChanged(str(exc)) from exc
    return version, reviews, overlay


def current_library_snapshot(*, expected_version: dict | None = None) -> dict:
    """Fresh version/admission check without running a legal-text search.

    A matching version does not establish that every rule citation is admitted;
    planner reads must still use the same reviewed source boundary.
    """
    with _engine().connect() as connection, connection.begin():
        connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
        version, _, _ = _read_library_state(connection, expected_version)
        return version


def search_library(query: str, jurisdiction: str, limit: int = 6, *, expected_version: dict | None = None) -> dict:
    """Search a jurisdiction or canonical treaty pair through the reviewed boundary."""
    query = query.strip()
    jurisdiction = jurisdiction.strip().lower()
    if not 2 <= len(query) <= 120 or not re.fullmatch(r'[a-z]{2}(?:-[a-z]{2})?', jurisdiction):
        raise ValueError("invalid_library_query")
    if '-' in jurisdiction:
        parties = jurisdiction.split('-')
        if parties[0] == parties[1]:
            raise ValueError("invalid_library_query")
        jurisdiction = '-'.join(sorted(parties))
    if not 1 <= limit <= 10:
        raise ValueError("invalid_library_limit")

    # A full conversational question rarely occurs verbatim in a statute. Keep
    # the exact locator path, otherwise reduce it to a small set of tax terms.
    exact_locator = bool(re.fullmatch(r"[a-z0-9_.-]+#[a-z0-9_.()/-]+", query, re.I))
    terms = [] if exact_locator else [term for term in (
        "企业所得税", "个人所得税", "增值税", "股息", "红利", "扣除", "税率",
        "税收居民", "非居民", "预提所得税", "所得税", "发票",
    ) if term in query]
    if not terms and not exact_locator:
        terms = [query]
    terms = terms[:4]
    with _engine().connect() as connection, connection.begin():
        connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
        version, reviews, overlay = _read_library_state(connection, expected_version)
        # An accepted replacement is not usable until the overlay text and
        # applicability metadata are published. Rejected candidates retain the
        # base only after an explicit completed review.
        blocked = blocked_citations(reviews, overlay)
        rows = connection.execute(text("""
            SELECT c.cite_id, c.label, left(c.text, 5000) AS passage,
                   d.id AS document_id, d.title, d.url, d.sha256 AS document_sha256,
                   d.lang, d.effective_from, d.effective_to
            FROM database.clause AS c
            JOIN database.doc AS d ON d.id = c.doc_id
            WHERE d.jur = :jurisdiction
              AND NOT (c.cite_id = ANY(:blocked))
              AND NOT EXISTS (
                  SELECT 1 FROM database_integration.source_review AS r
                  WHERE r.cite_id = c.cite_id AND (
                    r.difference = 'main_only' OR (r.difference = 'different_text'
                    AND NOT (r.review_status = 'rejected' AND r.reviewed_at IS NOT NULL)))
              )
              AND (c.cite_id = :query
                   OR (:exact_locator = false AND (
                       position(lower(:term0) in lower(c.text)) > 0
                       OR position(lower(:term0) in lower(d.title)) > 0)))
            ORDER BY CASE WHEN c.cite_id = :query THEN 0 ELSE 1 END,
                     CASE WHEN position(lower(:term0) in lower(d.title)) > 0 THEN 0 ELSE 1 END,
                     CASE WHEN position(lower(:term1) in lower(c.text)) > 0 THEN 0 ELSE 1 END,
                     CASE WHEN position(lower(:term2) in lower(c.text)) > 0 THEN 0 ELSE 1 END,
                     c.cite_id
            LIMIT :limit
        """), {"query": query, "jurisdiction": jurisdiction, "limit": limit, "blocked": sorted(blocked),
               "exact_locator": exact_locator, "term0": terms[0] if terms else query,
               "term1": terms[1] if len(terms) > 1 else terms[0] if terms else query,
               "term2": terms[2] if len(terms) > 2 else terms[0] if terms else query}).mappings().all()

    overlay_matches = matching_rows(overlay, query, jurisdiction, terms, exact_locator)
    combined = [dict(row) for row in rows] + overlay_matches
    # An admitted main-only ID must not collide with a newly appeared base row.
    if len({row['cite_id'] for row in combined}) != len(combined):
        raise LibraryVersionChanged('overlay_base_collision')
    def rank(row):
        primary = terms[0] if terms else query
        return (row['cite_id'] != query, primary.lower() not in row['title'].lower(),
                (terms[1] if len(terms)>1 else primary).lower() not in row['passage'].lower(),
                (terms[2] if len(terms)>2 else primary).lower() not in row['passage'].lower(), row['cite_id'])
    combined = (sorted(combined,key=rank) if overlay_matches else combined)[:limit]
    return {
        "status": "review_required" if exact_locator and query in blocked else "available" if combined else "no_matching_units",
        "library_version": version,
        "jurisdiction": jurisdiction,
        "query": query,
        "blocked_citations": [query] if exact_locator and query in blocked else [],
        "passages": [
            {**{key: value for key,value in row.items() if key != '_search_text'}, "passage_sha256": sha256(row["passage"].encode("utf-8")).hexdigest()}
            for row in combined
        ],
    }
