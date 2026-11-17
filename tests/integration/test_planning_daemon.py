import asyncio
import os
from pathlib import Path
import subprocess
import sys

import pytest
from sqlalchemy import create_engine, inspect

from packages.domain_bridge import planning_daemon as daemon
from packages.domain_bridge.planning_store import metadata, LeaseLost


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('ready', [True, False])
def test_real_once_cli_checks_schema_without_creating_it(tmp_path, ready):
    url = 'sqlite:///' + (tmp_path/'worker.sqlite').as_posix()
    engine = create_engine(url)
    if ready:
        metadata.create_all(engine)
    engine.dispose()
    result = subprocess.run([sys.executable, '-X', 'utf8', 'scripts/run_planning_worker.py', '--once'],
                            cwd=ROOT, env={**os.environ, 'FSIE_WEB_DATABASE_URL':url, 'FSIE_LIBRARY_DATABASE_URL':''},
                            capture_output=True, text=True, timeout=30)
    # A ready queue still must not start without its dedicated library reader.
    assert result.returncode == 1, result.stderr
    assert result.stderr.strip() == 'planning_worker_failed'
    if not ready:
        assert result.stderr.strip() == 'planning_worker_failed'
        check = create_engine(url)
        assert not inspect(check).get_table_names()
        check.dispose()


@pytest.mark.parametrize('reader_ready', [False, True])
def test_preflight_never_claims_jobs_and_disposes_engine(monkeypatch, reader_ready):
    from types import SimpleNamespace
    calls = []
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, query):
            assert 'planning_runs' in str(query)
            calls.append('schema')
    engine = SimpleNamespace(connect=Connection, dispose=lambda: calls.append('dispose'))
    monkeypatch.setattr(daemon, 'create_engine', lambda *a, **k: engine)
    monkeypatch.setattr(daemon, 'WorkerSettings', lambda: SimpleNamespace(
        web_database_url='sqlite://', database_url=''))
    def snapshot():
        calls.append('reader')
        if not reader_ready: raise ValueError('library_reader_unavailable')
        return {'uploaded_at':'test'}
    monkeypatch.setattr(daemon, 'current_library_snapshot', snapshot)
    monkeypatch.setattr(daemon, 'PlanningStore', lambda *a: pytest.fail('Preflight claimed queue access'))
    if reader_ready:
        daemon.start(check_only=True)
    else:
        with pytest.raises(ValueError, match='library_reader_unavailable'):
            daemon.start(check_only=True)
    assert calls == ['schema','reader','dispose']


def test_missing_reader_prevents_normal_worker_polling(monkeypatch):
    from types import SimpleNamespace
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, query): pass
    monkeypatch.setattr(daemon,'WorkerSettings',lambda: SimpleNamespace(web_database_url='sqlite://',database_url=''))
    monkeypatch.setattr(daemon,'create_engine',lambda *a,**k: SimpleNamespace(connect=Connection,dispose=lambda:None))
    def fail(): raise ValueError('missing_reader')
    monkeypatch.setattr(daemon,'current_library_snapshot',fail)
    monkeypatch.setattr(daemon,'PlanningStore',lambda *a:pytest.fail('Must not poll or claim'))
    with pytest.raises(ValueError,match='missing_reader'):
        daemon.start()


@pytest.mark.parametrize('lost', [False, True])
def test_once_forwards_policy_and_never_reclaims_twice(monkeypatch, lost):
    calls = []
    async def run(store, execute, **kwargs):
        calls.append(kwargs)
        assert execute is daemon.execute_job
        if lost:
            raise LeaseLost()
        return 'run'
    monkeypatch.setattr(daemon, 'run_once', run)
    config = daemon.WorkerSettings(_env_file=None, lease_seconds=9, wall_seconds=15, max_attempts=2)
    asyncio.run(daemon.serve(object(), config, once=True))
    assert calls == [{'lease_seconds':9,'wall_seconds':15,'max_attempts':2}]
