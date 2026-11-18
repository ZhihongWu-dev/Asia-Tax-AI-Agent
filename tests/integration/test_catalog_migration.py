from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.catalog_migration import digest, simulate, validate_plan


def plan_for(operations):
    return dict(operations=operations, operation_count=len(operations),
                proposed_catalog_revision=digest(operations), base_uploaded_at='upload')


@pytest.fixture
def example():
    operations = [
        dict(table='doc', key_column='id', key='law', operation='update',
             expected_before={'id': 'law', 'sha256': 'old'}, after={'id': 'law', 'sha256': 'new'}),
        dict(table='clause', key_column='cite_id', key='law#notice', operation='delete',
             expected_before={'cite_id': 'law#notice', 'text': 'redirect'}, after=None),
        dict(table='clause', key_column='cite_id', key='law#1', operation='insert',
             expected_before=None, after={'cite_id': 'law#1', 'text': 'operative text'}),
    ]
    return plan_for(operations), deepcopy({'doc': {'law': operations[0]['expected_before']},
                                  'clause': {'law#notice': operations[1]['expected_before']}})


def test_atomic_replacement_simulation_preserves_inputs(example):
    plan, rows = example
    original = deepcopy(rows)
    result = simulate(plan, rows, uploaded_at='upload')
    assert rows == original
    assert result['doc']['law']['sha256'] == 'new'
    assert set(result['clause']) == {'law#1'}
    result['clause']['law#1']['text'] = 'changed'
    assert plan['operations'][2]['after']['text'] == 'operative text'


@pytest.mark.parametrize('change', ['edited', 'missing', 'collision', 'null_collision'])
def test_stale_or_conflicting_rows_fail_without_partial_changes(example, change):
    plan, rows = example
    if change == 'edited': rows['clause']['law#notice']['text'] = 'another notice'
    if change == 'missing': del rows['clause']['law#notice']
    if change == 'collision': rows['clause']['law#1'] = plan['operations'][2]['after']
    if change == 'null_collision': rows['clause']['law#1'] = None
    before = deepcopy(rows)
    with pytest.raises(ValueError, match='before_state_changed'):
        simulate(plan, rows, uploaded_at='upload')
    assert rows == before


def test_old_upload_rejected(example):
    with pytest.raises(ValueError, match='base_upload_changed'):
        simulate(*example, uploaded_at='another upload')


def test_tampered_plan_rejected(example):
    plan, _ = example
    plan['operations'][0]['after']['sha256'] = 'tampered'
    with pytest.raises(ValueError, match='plan_digest_mismatch'): validate_plan(plan)


@pytest.mark.parametrize('change,error', [
    ('duplicate', 'duplicate_or_invalid_key'), ('table', 'table_or_key_invalid'),
    ('key', 'row_key_mismatch'), ('action', 'action_invalid'),
    ('shape', 'row_shape_invalid'), ('digest', 'row_digest_mismatch'),
])
def test_invalid_operations_rejected_even_with_matching_plan_hash(example, change, error):
    plan, _ = example
    ops = plan['operations']
    if change == 'duplicate': ops.append(deepcopy(ops[0]))
    if change == 'table': ops[0]['table'] = 'meta'
    if change == 'key': ops[0]['after']['id'] = 'other'
    if change == 'action': ops[0]['operation'] = 'upsert'
    if change == 'shape': ops[0]['after'] = None
    if change == 'digest': ops[0]['after_sha256'] = 'wrong'
    with pytest.raises(ValueError, match=error): validate_plan(plan_for(ops))


def test_reviewed_real_plan_is_valid():
    root = Path(__file__).resolve().parents[2]
    plan = json.loads((root / 'docs/project/data-reconciliation/catalog-migration-plan-20261118.json').read_text('utf-8'))
    ops = validate_plan(plan)
    assert len(ops) == 399
    assert len([op for op in ops if op['table'] == 'clause']) == 152
