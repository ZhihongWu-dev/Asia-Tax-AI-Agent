from copy import deepcopy
from hashlib import sha256

import pytest

from packages.domain_bridge.planning_library import PlanningLibrary, digest
from packages.domain_bridge.planning_sources import PlanningSourcesUnavailable


PIN = {'uploaded_at': 'test', 'review_sha256': 'test-review'}


def seal(bundle):
    bundle.pop('bundle_sha256', None)
    bundle['bundle_sha256'] = digest(bundle)
    return bundle


def bundle():
    tables = {'jurisdiction': [{'code': 'cn'}, {'code': 'sg'}],
              'doc': [{'id': 'cn.law', 'title': 'Original'}],
              'param': [{'param_id': 'rate', 'value': '20', 'cite_id': 'cn.law#1',
                         'effective_from': '2026-01-01', 'effective_to': '2026-12-31'}],
              'treaty': [{'pair': 'cn-sg', 'doc_id': 'treaty.cn-sg'}], 'decision': []}
    return seal({'library_version': deepcopy(PIN), 'tables': tables,
                 'table_sha256': {name: digest(rows) for name, rows in tables.items()},
                 'sources': {'cn.law#1': {'cite_id': 'cn.law#1', 'passage': 'Original text',
                              'label': 'Article 1',
                              'passage_sha256': sha256(b'Original text').hexdigest()}}})


def test_library_detaches_input_and_every_returned_mutable_value():
    original = bundle()
    lib = PlanningLibrary(original, expected_version=PIN)
    original['tables']['param'][0]['value'] = '0'
    lib.params['rate']['value'] = '1'
    lib.juris.clear()
    lib.docs['cn.law']['title'] = 'Changed'
    lib.source('cn.law#1')['passage'] = 'Changed'
    lib.version_metadata()['library_version']['uploaded_at'] = 'Changed'
    lib.treaty('cn', 'sg')['doc_id'] = ''
    assert lib.params['rate']['value'] == '20'
    assert lib.codes == {'cn', 'sg'}
    assert lib.docs['cn.law']['title'] == 'Original'
    assert lib.clause('cn.law#1') == 'Original text'
    assert lib.clause_label('cn.law#1') == 'Article 1'
    assert lib.version_metadata()['library_version'] == PIN
    assert lib.treaty('sg', 'cn')['doc_id'] == 'treaty.cn-sg'
    assert lib.treaty('cn', 'jp') is None


@pytest.mark.parametrize('date,expected', [('2025-12-31', False), ('2026-01-01', True),
                                         ('2026-12-31', True), ('2027-01-01', False)])
def test_effective_window_is_inclusive(date, expected):
    lib = PlanningLibrary(bundle(), expected_version=PIN)
    assert lib.param_effective('rate', date) is expected
    assert not lib.param_effective('absent', date)


@pytest.mark.parametrize('method', ['clause', 'clause_label', 'source'])
def test_unknown_citation_raises_without_fallback(method):
    lib = PlanningLibrary(bundle(), expected_version=PIN)
    with pytest.raises(PlanningSourcesUnavailable) as exc:
        getattr(lib, method)('cn.missing#1')
    assert exc.value.missing == ('cn.missing#1',)


def test_version_and_all_digest_layers_are_checked():
    with pytest.raises(ValueError, match='version_mismatch'):
        PlanningLibrary(bundle(), expected_version={'uploaded_at': 'other'})
    changed = bundle()
    changed['sources']['cn.law#1']['passage'] = 'Changed'
    with pytest.raises(ValueError, match='bundle_digest'):
        PlanningLibrary(changed, expected_version=PIN)
    seal(changed)
    with pytest.raises(ValueError, match='passage_digest'):
        PlanningLibrary(changed, expected_version=PIN)
    changed = bundle()
    changed['tables']['param'][0]['value'] = '0'
    seal(changed)
    with pytest.raises(ValueError, match='table_digest'):
        PlanningLibrary(changed, expected_version=PIN)


def test_valid_hash_cannot_hide_missing_factor_dependency():
    changed = bundle()
    changed['tables']['param'][0]['factors_cite'] = 'cn.missing#1'
    changed['table_sha256']['param'] = digest(changed['tables']['param'])
    seal(changed)
    with pytest.raises(PlanningSourcesUnavailable) as exc:
        PlanningLibrary(changed, expected_version=PIN)
    assert exc.value.missing == ('cn.missing#1',)


def test_reversed_duplicate_treaty_is_rejected():
    changed = bundle()
    changed['tables']['treaty'].append({'pair': 'sg-cn', 'doc_id': 'other'})
    changed['table_sha256']['treaty'] = digest(changed['tables']['treaty'])
    seal(changed)
    with pytest.raises(ValueError, match='treaty_pair_duplicate'):
        PlanningLibrary(changed, expected_version=PIN)
