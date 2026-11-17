import asyncio

import pytest

from packages.domain_bridge import planning_executor as executor
from packages.domain_bridge.planning_worker import PlanningExecutionError


@pytest.mark.parametrize('failure', [None, 'sources', 'version', 'runtime'])
def test_admission_precedes_execution_and_failures_never_execute(monkeypatch, failure):
    runtime = {'files': {'rule': 'hash'}, 'citations': ['cn.rule#1']}
    calls = []
    def capture():
        if failure == 'runtime' and calls:
            return {'files': {'rule': 'changed'}, 'citations': ['cn.rule#1']}
        return runtime
    def read(citations, *, expected_version):
        calls.append('read')
        assert citations == runtime['citations'] and expected_version == {'pin': 'one'}
        if failure == 'sources':
            raise executor.PlanningSourcesUnavailable(missing=['cn.rule#1'])
        if failure == 'version':
            raise executor.LibraryVersionChanged()
        return {'fixture': 'admitted'}
    async def execute(inputs, bundle, *, expected_version, expected_runtime):
        calls.append('execute')
        assert inputs == {'amount': 100} and bundle == {'fixture': 'admitted'}
        assert expected_runtime == runtime and expected_version == {'pin': 'one'}
        return {'fixture': 'result'}
    monkeypatch.setattr(executor, 'capture_runtime', capture)
    monkeypatch.setattr(executor, 'read_planning_bundle', read)
    monkeypatch.setattr(executor, 'execute_bundle', execute)
    job = {'input': {'amount': 100}, 'library_snapshot': {'pin': 'one'},
           'runtime_snapshot': runtime}
    if failure:
        with pytest.raises(PlanningExecutionError) as exc:
            asyncio.run(executor.execute_job(job))
        assert exc.value.code == {'sources': 'planning_sources_unavailable',
                                  'version': 'library_version_changed',
                                  'runtime': 'planning_runtime_changed'}[failure]
        assert calls == ['read']
    else:
        assert asyncio.run(executor.execute_job(job)) == {'fixture': 'result'}
        assert calls == ['read', 'execute']


@pytest.mark.parametrize('runtime', [None, {}, {'files': {'rule': 'old'}}])
def test_stale_or_missing_queued_runtime_never_reads_cloud(monkeypatch, runtime):
    monkeypatch.setattr(executor, 'capture_runtime', lambda: {'files': {'rule': 'new'}})
    monkeypatch.setattr(executor, 'read_planning_bundle', lambda *a, **k: pytest.fail('cloud read'))
    with pytest.raises(PlanningExecutionError, match='planning_runtime_changed'):
        asyncio.run(executor.execute_job({'input': {}, 'library_snapshot': {'pin': 'one'},
                                         'runtime_snapshot': runtime}))
