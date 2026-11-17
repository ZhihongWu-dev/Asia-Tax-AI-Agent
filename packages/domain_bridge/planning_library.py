"""Offline Li Library interface over a verified planning bundle.

Digests detect accidental corruption, not authenticity. Only bundles produced by
the trusted planning source reader may be supplied; the worker verifies the live
library version before and after execution.
"""
from copy import deepcopy
from hashlib import sha256
import json

from packages.domain_bridge.planning_sources import PlanningSourcesUnavailable


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                            ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()


class PlanningLibrary:
    """No database connection, file lookup, or missing-citation fallback."""

    def __init__(self, bundle, *, expected_version):
        data = deepcopy(bundle)
        if not expected_version or data.get('library_version') != expected_version:
            raise ValueError('planning_library_version_mismatch')
        fingerprint = data.pop('bundle_sha256', None)
        if fingerprint != digest(data):
            raise ValueError('planning_bundle_digest_mismatch')
        tables = data['tables']
        keys = {'jurisdiction': 'code', 'doc': 'id', 'param': 'param_id',
                'treaty': 'pair', 'decision': 'id'}
        if set(tables) != set(keys) or set(data['table_sha256']) != set(keys):
            raise ValueError('planning_catalog_incomplete')
        for name, key in keys.items():
            rows = tables[name]
            if digest(rows) != data['table_sha256'][name]:
                raise ValueError('planning_table_digest_mismatch')
            if any(not row.get(key) for row in rows) or len({row[key] for row in rows}) != len(rows):
                raise ValueError('planning_catalog_duplicate_or_empty_key')
        sources = data['sources']
        for cite, source in sources.items():
            if source['cite_id'] != cite or sha256(source['passage'].encode('utf-8')).hexdigest() != source['passage_sha256']:
                raise ValueError('planning_passage_digest_mismatch')
        required = {cite.strip() for row in tables['param'] + tables['decision']
                    for field in ('cite_id', 'factors_cite')
                    for cite in row.get(field, '').split(';') if cite.strip()}
        if required - sources.keys():
            raise PlanningSourcesUnavailable(missing=required - sources.keys())
        self._tables = tables
        self._sources = sources
        self._params = {row['param_id']: row for row in tables['param']}
        self._treaties = {}
        for row in tables['treaty']:
            pair = row['pair'].split('-')
            if len(pair) != 2 or not all(pair) or pair[0] == pair[1]:
                raise ValueError('planning_treaty_pair_invalid')
            key = frozenset(pair)
            if key in self._treaties:
                raise ValueError('planning_treaty_pair_duplicate')
            self._treaties[key] = row
        self._version = {'library_version': data['library_version'],
                         'bundle_sha256': fingerprint, 'table_sha256': data['table_sha256']}

    @property
    def juris(self):
        return deepcopy(self._tables['jurisdiction'])

    @property
    def codes(self):
        return {row['code'] for row in self._tables['jurisdiction']}

    @property
    def docs(self):
        return {row['id']: deepcopy(row) for row in self._tables['doc']}

    @property
    def params(self):
        return deepcopy(self._params)

    @property
    def treaties(self):
        return deepcopy(self._treaties)

    @property
    def absences(self):
        return deepcopy(self._tables['decision'])

    def version_metadata(self):
        return deepcopy(self._version)

    def source(self, cite_id):
        if cite_id not in self._sources:
            raise PlanningSourcesUnavailable(missing=[cite_id])
        return deepcopy(self._sources[cite_id])

    def clause(self, cite_id):
        return self.source(cite_id)['passage']

    def clause_label(self, cite_id):
        return self.source(cite_id).get('label') or ''

    def treaty(self, a, b):
        row = self._treaties.get(frozenset((a, b)))
        return deepcopy(row) if row and (row.get('doc_id') or '').strip() else None

    def param_effective(self, pid, date):
        row = self._params.get(pid)
        return bool(row is not None and
                    (not row.get('effective_from') or date >= row['effective_from']) and
                    (not row.get('effective_to') or date <= row['effective_to']))
