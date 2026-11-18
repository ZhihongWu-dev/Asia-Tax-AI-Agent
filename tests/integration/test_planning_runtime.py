from pathlib import Path

import pytest

from packages.domain_bridge.planning_runtime import FILES, capture_runtime


@pytest.fixture
def release(tmp_path):
    for name in FILES:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('# fixture\n', encoding='utf-8')
    (tmp_path / 'rule/rule.csv').write_text('cite_ids\ncn.law#1;cn.law#2\n', encoding='utf-8')
    (tmp_path / 'rule/predicate.csv').write_text('factors_cite\ncn.law#2;sg.law#1\n', encoding='utf-8')
    (tmp_path / 'rule/decision.csv').write_text('cite_id\ncn.decision#1\n', encoding='utf-8')
    return tmp_path


def test_all_rule_dependency_classes_are_collected(release):
    result = capture_runtime(release)
    assert result['citations'] == ['cn.decision#1', 'cn.law#1', 'cn.law#2', 'sg.law#1']
    assert len(result['files']) == len(FILES)
    assert all(len(value) == 64 for value in result['files'].values())


@pytest.mark.parametrize('name', FILES)
def test_every_runtime_file_changes_snapshot_even_without_row_count_change(release, name):
    before = capture_runtime(release)
    path = release / name
    path.write_text(path.read_text(encoding='utf-8').replace('fixture', 'changed')
                    if name.endswith('.py') or name.endswith('move.csv') or
                    name.endswith('variable.csv') or name.endswith('rule_test.csv')
                    else path.read_text(encoding='utf-8').replace('cn.', 'hk.'), encoding='utf-8')
    assert capture_runtime(release)['files'][name] != before['files'][name]


def test_missing_file_is_not_an_empty_digest(release):
    (release / 'rule/variable.csv').unlink()
    with pytest.raises(FileNotFoundError):
        capture_runtime(release)


def test_procedure_clauses_are_loaded_without_treating_documents_as_clauses(release):
    (release / 'rule/rule.csv').write_text(
        'cite_ids,procedure\ncn.law#1,cn.form; absence.procedure; cn.form#6 ; cn.form#7\n',
        encoding='utf-8')
    result = capture_runtime(release)
    assert 'cn.form#6' in result['citations']
    assert 'cn.form#7' in result['citations']
    assert 'cn.form' not in result['citations']
    assert 'absence.procedure' not in result['citations']
