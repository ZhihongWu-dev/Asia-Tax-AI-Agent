import asyncio
from pathlib import Path
import sys

import pytest

from packages.chat.store import ChatStore
from packages.chat.worker_limits import terminate_worker
from packages.domain_bridge.planning_store import PlanningStore, LeaseLost, metadata
from packages.domain_bridge.planning_worker import run_once

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def setup(tmp_path):
    chat = ChatStore('sqlite:///' + (tmp_path/'worker.sqlite').as_posix())
    metadata.create_all(chat.engine)
    jobs = PlanningStore(chat.engine)
    case = chat.create('alice')
    job = jobs.enqueue('alice', case['id'], 0, 'request', {'amount':100}, {'version':'one'})
    yield jobs, job
    chat.engine.dispose()


async def verified(job):
    assert job['library_snapshot'] == {'version':'one'}
    return {'version':'one'}


def test_changed_release_is_persisted_as_failure_before_source_read(setup, monkeypatch):
    from packages.domain_bridge import planning_executor as executor
    jobs, job = setup
    monkeypatch.setattr(executor, 'capture_runtime', lambda: {'files': {'rule': 'changed'}})
    monkeypatch.setattr(executor, 'read_planning_bundle',
                        lambda *a, **k: pytest.fail('stale task accessed sources'))
    assert asyncio.run(run_once(jobs, executor.execute_job, verified)) == job['id']
    saved = jobs.get('alice', job['id'])
    assert saved['status'] == 'failed'
    assert saved['error'] == 'planning_runtime_changed'
    assert saved['result'] is None
    assert saved['runtime_snapshot'] == job['runtime_snapshot']


def test_success_renews_and_verifies_before_and_after(setup, monkeypatch):
    jobs, job = setup
    renewals, checks = [], []
    original = jobs.heartbeat

    def heartbeat(*args):
        renewals.append(args[0])
        return original(*args)

    monkeypatch.setattr(jobs, 'heartbeat', heartbeat)

    async def verify(row):
        checks.append(row['id'])
        return await verified(row)

    async def execute(row):
        assert len(checks) == 1
        await asyncio.sleep(2)
        return {'amount':row['input']['amount']}

    assert asyncio.run(run_once(jobs, execute, verify, lease_seconds=5)) == job['id']
    assert renewals == [job['id']]
    assert checks == [job['id'],job['id']]
    assert jobs.get('alice', job['id'])['result'] == {'amount':100}


@pytest.mark.parametrize('fail_check', [1, 2])
def test_changed_source_never_publishes_success(setup, fail_check):
    jobs, job = setup
    checks, executions = [], []

    async def verify(row):
        checks.append(row['id'])
        if len(checks) == fail_check:
            return {'version':'two'}
        return {'version':'one'}

    async def execute(row):
        executions.append(row['id'])
        return {'report':'must not be published'}

    asyncio.run(run_once(jobs, execute, verify))
    saved = jobs.get('alice', job['id'])
    assert saved['status'] == 'failed'
    assert saved['error'] == 'library_version_changed'
    assert saved['result'] is None
    assert len(executions) == fail_check - 1


@pytest.mark.parametrize('failure', [LeaseLost, RuntimeError])
def test_failed_renewal_cancels_execution_without_publishing(setup, monkeypatch, failure):
    jobs, job = setup
    cleaned = []

    def heartbeat(*args):
        raise failure('private database detail')

    monkeypatch.setattr(jobs, 'heartbeat', heartbeat)

    async def execute(row):
        try:
            await asyncio.sleep(30)
            return {'report':'stale'}
        finally:
            cleaned.append(True)

    with pytest.raises(failure):
        asyncio.run(run_once(jobs, execute, verified, lease_seconds=5))
    saved = jobs.get('alice', job['id'])
    assert saved['status'] == 'running'  # recoverable after its lease expires
    assert saved['result'] is None and saved['error'] is None
    assert cleaned == [True]


def test_shutdown_keeps_job_recoverable(setup):
    jobs, job = setup

    async def scenario():
        started = asyncio.Event()
        cleaned = asyncio.Event()

        async def execute(row):
            started.set()
            try:
                await asyncio.sleep(30)
            finally:
                cleaned.set()

        task = asyncio.create_task(run_once(jobs, execute, verified))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert cleaned.is_set()

    asyncio.run(scenario())
    assert jobs.get('alice', job['id'])['status'] == 'running'


def test_timeout_reaps_real_subprocess_before_persisting_failure(setup):
    jobs, job = setup
    children = []

    async def execute(row):
        proc = await asyncio.create_subprocess_exec(
            sys.executable, '-c', 'import time;time.sleep(30)', cwd=ROOT,
            start_new_session=True, stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL)
        children.append(proc)
        try:
            await proc.wait()
            return {}
        finally:
            await terminate_worker(proc, process_group=True)

    asyncio.run(run_once(jobs, execute, verified, wall_seconds=1))
    assert children and children[0].returncode is not None
    assert jobs.get('alice', job['id'])['error'] == 'planning_timeout'


def test_unexpected_error_does_not_persist_sensitive_details(setup):
    jobs, job = setup

    async def execute(row):
        raise RuntimeError('private credentials or case details')

    asyncio.run(run_once(jobs, execute, verified))
    saved = jobs.get('alice', job['id'])
    assert saved['error'] == 'planning_execution_failed'
    assert 'private' not in str(saved['events'])


def test_default_verifier_uses_pinned_cloud_snapshot(setup, monkeypatch):
    from packages.chat import library_cloud
    jobs, job = setup
    reads = []

    def read(*, expected_version):
        reads.append(expected_version)
        if len(reads) == 2:
            raise library_cloud.LibraryVersionChanged('library_review_base_changed')
        return dict(expected_version)

    monkeypatch.setattr(library_cloud, 'current_library_snapshot', read)

    async def execute(row):
        return {'report':'discard after source change'}

    asyncio.run(run_once(jobs, execute))
    assert reads == [{'version':'one'}, {'version':'one'}]
    saved = jobs.get('alice', job['id'])
    assert saved['error'] == 'library_version_changed'
    assert saved['result'] is None
