from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.catalog_migration import digest, simulate, validate_plan, read_affected_catalogs, verify_target


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


def test_exact_target_verification_includes_deletion_and_preserves_rows(example):
    plan, rows = example
    target = simulate(plan, rows, uploaded_at='upload')
    original = deepcopy(target)
    assert verify_target(plan, target)['verified_operations'] == 3
    assert target == original
    target['clause']['law#notice'] = None
    with pytest.raises(ValueError, match='migration_target_changed:clause:law#notice'):
        verify_target(plan, target)


@pytest.mark.parametrize('change', ['missing', 'edited', 'missing_table'])
def test_target_verification_rejects_drift_or_incomplete_read(example, change):
    plan, rows = example
    target = simulate(plan, rows, uploaded_at='upload')
    if change == 'missing': del target['doc']['law']
    elif change == 'edited': target['doc']['law']['sha256'] = 'stale'
    else: del target['clause']
    with pytest.raises(ValueError, match='migration_target_'):
        verify_target(plan, target)


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


class Result:
    def __init__(self, rows): self.rows = rows
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def mappings(self): return iter(self.rows)


def test_reads_only_bound_batches_and_preserves_absence(example):
    plan, rows = example
    calls = []
    class Connection:
        def execute(self, statement, params):
            sql = str(statement)
            calls.append((sql, params))
            table = sql.split('database.')[1].split()[0]
            return Result([rows[table][key] for key in params['ids'] if key in rows[table]])
    malicious_value = "law'); DROP TABLE database.doc; --"
    result = read_affected_catalogs(Connection(), plan, batch_size=1,
                                    extra_keys={'doc': [malicious_value, 'law']})
    assert result['doc'] == rows['doc']
    assert result['clause'] == rows['clause']
    assert 'law#1' not in result['clause']
    assert len(calls) == 4
    assert all('WHERE' in sql and '= ANY(:ids)' in sql and malicious_value not in sql
               and len(params['ids']) == 1 for sql, params in calls)


@pytest.mark.parametrize('options', [
    {'batch_size': 0}, {'batch_size': 101}, {'batch_size': True},
    {'extra_keys': {'meta': ['uploaded_at']}}, {'extra_keys': {'doc': 'law'}},
    {'extra_keys': {'doc': [None]}},
])
def test_invalid_read_options_rejected_before_sql(example, options):
    class NoSQL:
        def execute(self, *args): pytest.fail('invalid request must not issue SQL')
    with pytest.raises(ValueError): read_affected_catalogs(NoSQL(), example[0], **options)


@pytest.mark.parametrize('rows', [[{'id': 'other'}], [{'id': 'law'}, {'id': 'law'}]])
def test_unexpected_database_rows_fail_closed(example, rows):
    class Connection:
        def execute(self, *args): return Result(rows)
    with pytest.raises(ValueError, match='unexpected_or_duplicate_row'):
        read_affected_catalogs(Connection(), example[0])
