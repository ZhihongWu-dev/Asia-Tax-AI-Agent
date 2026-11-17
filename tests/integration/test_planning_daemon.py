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
                            cwd=ROOT, env={**os.environ, 'FSIE_WEB_DATABASE_URL':url},
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == (0 if ready else 1), result.stderr
    if not ready:
        assert result.stderr.strip() == 'planning_worker_failed'
        check = create_engine(url)
        assert not inspect(check).get_table_names()
        check.dispose()


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
