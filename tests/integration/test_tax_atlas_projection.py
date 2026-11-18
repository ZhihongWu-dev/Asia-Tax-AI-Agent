from types import SimpleNamespace

import pytest

from packages.domain_bridge import tax_atlas
from packages.domain_bridge.planning_library import PlanningLibrary
from packages.domain_bridge.planning_sources import PlanningSourcesUnavailable
from tests.integration.test_planning_library import PIN, bundle


def state():
    lib = PlanningLibrary(bundle(), expected_version=PIN)
    return {'lib': lib, 'version': lib.version_metadata(), 'rs': SimpleNamespace(rules=[])}


@pytest.mark.parametrize('value', ['2026-02-30', 'not-a-date', '20260101', '2026-1-01', 123])
def test_invalid_date_does_not_fall_back_to_current_day(value):
    with pytest.raises(ValueError, match='invalid_atlas_date'):
        tax_atlas.today(value)


def test_original_passage_and_version_are_preserved_without_truncation():
    st = state()
    result = tax_atlas.clause(st, 'cn.law#1')
    assert result['text'] == 'Original text'
    assert result['title'] == 'Original'
    assert result['total'] == len(result['text'])
    assert result['version']['library'] == st['version']['bundle_sha256']
    result['version']['snapshot']['library_version']['uploaded_at'] = 'changed'
    assert tax_atlas.version(st)['snapshot']['library_version']['uploaded_at'] == 'test'


def test_missing_source_is_not_replaced_by_local_unreviewed_passage():
    with pytest.raises(PlanningSourcesUnavailable):
        tax_atlas.clause(state(), 'cn.missing#1')


def test_projections_do_not_reuse_process_global_library_state():
    first, second = state(), state()
    first['version']['bundle_sha256'] = 'first-reviewed-bundle'
    second['version']['bundle_sha256'] = 'second-reviewed-bundle'
    assert tax_atlas.version(first)['library'] != tax_atlas.version(second)['library']
    assert not hasattr(tax_atlas, '_st')


def test_map_retains_unknown_rates_and_detaches_scenario_assumptions():
    st = state()
    st['lib'] = SimpleNamespace(juris=[{'code': 'cn', 'name': 'China', 'currency': 'CNY'}], absences=[])
    st['ev'] = SimpleNamespace(eval_cell=lambda *args: {'status': 'needs_information', 'needs': [('fact', 'verified')]})
    result = tax_atlas.map_data(st, '2026-11-18')
    assert result['jurisdictions'][0]['wht_company']['ceiling'] is None
    assert result['jurisdictions'][0]['wht_company']['needs'] == ['verified']
    result['facts']['holding_pct'] = 0
    assert tax_atlas.map_data(st, '2026-11-18')['facts']['holding_pct'] == 100
