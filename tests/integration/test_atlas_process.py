import asyncio
import json
from pathlib import Path

import pytest

from packages.domain_bridge import atlas_process, atlas_runner
from tests.integration.test_planning_library import PIN, bundle


REQUEST = {'operation': 'clause', 'cite_id': 'cn.law#1'}


def test_real_subprocess_returns_pinned_complete_passage():
    result = asyncio.run(atlas_process.execute(REQUEST, bundle(), expected_version=PIN))
    assert result['library_snapshot'] == PIN
    assert result['result']['text'] == 'Original text'
    assert result['runtime'] == atlas_runner.capture_atlas_runtime()


def test_runner_rejects_runtime_change_before_loading_library():
    with pytest.raises(ValueError, match='atlas_runtime_changed'):
        atlas_runner.run(REQUEST, {}, expected_version=PIN, expected_runtime={})


@pytest.mark.parametrize('payload', [
    {'operation': 'country', 'code': 'xx'},
    {'operation': 'clause'},
    {'operation': 'map', 'cite_id': 'cn.law#1'},
    {'operation': 'map', 'date': '2026-02-30'},
    {'operation': 'map', 'date': 2026},
    {'operation': 'shell'},
])
def test_invalid_selectors_are_rejected(payload):
    with pytest.raises(ValueError):
        atlas_runner.run(payload, {}, expected_version=PIN, expected_runtime={})


def test_timeout_awaits_child_cleanup(monkeypatch):
    cleaned = []

    async def child(command):
        try:
            await asyncio.sleep(60)
        finally:
            cleaned.append(True)

    monkeypatch.setattr(atlas_process, '_child', child)
    with pytest.raises(ValueError, match='atlas_execution_failed'):
        asyncio.run(atlas_process.execute(REQUEST, bundle(), expected_version=PIN,
                                         timeout_seconds=0.01))
    assert cleaned == [True]


def test_response_from_different_snapshot_is_rejected(monkeypatch):
    async def child(command):
        payload = json.loads(Path(command[-2]).read_text(encoding='utf-8'))
        payload['library_snapshot'] = {'uploaded_at': 'other'}
        Path(command[-1]).write_text(json.dumps(payload), encoding='utf-8')
        return 0

    monkeypatch.setattr(atlas_process, '_child', child)
    with pytest.raises(ValueError, match='atlas_snapshot_changed'):
        asyncio.run(atlas_process.execute(REQUEST, bundle(), expected_version=PIN))
