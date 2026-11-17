import pytest

from packages.domain_bridge.planning_runner import run


@pytest.mark.parametrize('fx', ['database/private.json', '', [], 1, False])
def test_file_or_non_object_fx_rejected_before_engine_load(tmp_path, fx):
    with pytest.raises(ValueError, match='planning_inline_fx_required'):
        run({'fx': fx}, {}, expected_version={}, output=tmp_path / 'unused')
    assert not (tmp_path / 'unused').exists()


def test_existing_output_is_preserved(tmp_path):
    sentinel = tmp_path / 'keep.txt'
    sentinel.write_text('existing user content', encoding='utf-8')
    with pytest.raises(ValueError, match='planning_output_already_exists'):
        run({}, {}, expected_version={}, output=tmp_path)
    assert sentinel.read_text(encoding='utf-8') == 'existing user content'
