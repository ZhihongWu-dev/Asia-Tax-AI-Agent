"""Exact, complete source dependencies for a pinned planning attempt.

Unlike conversational search this reader never truncates a legal passage or
silently drops a missing dependency. It does not approve rules or tax outcomes.
"""
from hashlib import sha256
import re

from sqlalchemy import text

from packages.chat import library_cloud


class PlanningSourcesUnavailable(ValueError):
    def __init__(self, *, blocked=(), missing=()):
        self.blocked = tuple(sorted(blocked))
        self.missing = tuple(sorted(missing))
        super().__init__('planning_sources_unavailable')


def read_sources(citations, *, expected_version):
    """Read at most 1,000 exact citations under a mandatory queued snapshot.

    Return complete text and provenance only if every dependency is admitted.
    No fuzzy matching, local fallback, network cache, or truncated text is used.
    """
    if not isinstance(expected_version, dict) or not expected_version:
        raise ValueError('planning_snapshot_required')
    if not isinstance(citations, (list, tuple)) or not 1 <= len(citations) <= 1000:
        raise ValueError('invalid_planning_citations')
    if any(not isinstance(c, str) or len(c) > 240 or not re.fullmatch(
            r'[a-z0-9_.-]+#[a-z0-9_.()/-]+', c, re.I) for c in citations):
        raise ValueError('invalid_planning_citations')
    requested = set(citations)
    with library_cloud._engine().connect() as connection, connection.begin():
        connection.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
        version, reviews, overlay = library_cloud._read_library_state(connection, expected_version)
        blocked = {r['cite_id'] for r in reviews
                   if r['difference'] == 'different_text'
                   and not (r['review_status'] == 'rejected' and r['reviewed_at'] is not None)}
        blocked.update(r['cite_id'] for r in reviews
                       if r['difference'] == 'main_only' and r['review_status'] == 'candidate')
        if requested & blocked:
            raise PlanningSourcesUnavailable(blocked=requested & blocked)
        rows = [dict(r) for r in connection.execute(text('''
            SELECT c.cite_id, c.label, c.text AS passage,
                   d.id AS document_id, d.title, d.url, d.sha256 AS document_sha256,
                   d.lang, d.jur AS jurisdiction, d.effective_from, d.effective_to
            FROM database.clause AS c
            JOIN database.doc AS d ON d.id = c.doc_id
            WHERE c.cite_id = ANY(:ids)
            ORDER BY c.cite_id
        '''), {'ids': sorted(requested)}).mappings().all()]
        rows.extend({**{k: v for k, v in r.items() if k != '_search_text'},
                     'passage': r['_search_text']} for r in overlay if r['cite_id'] in requested)
        if len({r['cite_id'] for r in rows}) != len(rows):
            raise library_cloud.LibraryVersionChanged('overlay_base_collision')
        missing = requested - {r['cite_id'] for r in rows}
        if missing:
            raise PlanningSourcesUnavailable(missing=missing)
        return {'library_version': version, 'sources': {
            r['cite_id']: {**r, 'passage_sha256': sha256(r['passage'].encode('utf-8')).hexdigest()}
            for r in sorted(rows, key=lambda r: r['cite_id'])}}
