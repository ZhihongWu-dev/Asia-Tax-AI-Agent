"""Exact, complete source dependencies for a pinned planning attempt.

Unlike conversational search this reader never truncates a legal passage or
silently drops a missing dependency. It does not approve rules or tax outcomes.
"""
from hashlib import sha256
import json
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
    return _read(citations, expected_version=expected_version, include_catalog=False)


def read_planning_bundle(citations, *, expected_version):
    """Materialize the cloud catalog and its source closure in one transaction.

    ``citations`` supplies rule/predicate/decision references. Every parameter
    and library-decision citation (including factor citations) is included automatically, including legacy
    rows; callers cannot silently omit a dependency by passing a shorter list.
    Catalog rows retain all columns. Sources include admitted main overlays;
    base catalog documents are not overwritten with overlay metadata.
    """
    return _read(citations, expected_version=expected_version, include_catalog=True)


def _read(citations, *, expected_version, include_catalog):
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
        tables = {}
        if include_catalog:
            # Identifiers are an internal allowlist, never request input.
            for name, key in (('jurisdiction', 'code'), ('doc', 'id'),
                              ('param', 'param_id'), ('treaty', 'pair'), ('decision', 'id')):
                table = [{k: '' if v is None else v for k, v in dict(r).items()}
                         for r in connection.execute(text(
                             f'SELECT * FROM database.{name} ORDER BY {key}'
                         )).mappings().all()]
                if len({r[key] for r in table}) != len(table):
                    raise ValueError('planning_catalog_duplicate')
                tables[name] = table
            for row in tables['param'] + tables['decision']:
                for field in ('cite_id', 'factors_cite'):
                    requested.update(c.strip() for c in row.get(field, '').split(';') if c.strip())
            if len(requested) > 1000:
                raise ValueError('planning_dependency_limit')
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
        result = {'library_version': version, 'sources': {
            r['cite_id']: {**r, 'passage_sha256': sha256(r['passage'].encode('utf-8')).hexdigest()}
            for r in sorted(rows, key=lambda r: r['cite_id'])}}
        if include_catalog:
            result['tables'] = tables
            result['table_sha256'] = {name: sha256(json.dumps(
                table, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                allow_nan=False).encode('utf-8')).hexdigest() for name, table in tables.items()}
            result['bundle_sha256'] = sha256(json.dumps(
                result, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                allow_nan=False).encode('utf-8')).hexdigest()
        return result
