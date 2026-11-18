"""Real PostgreSQL row-lock races; each run owns a disposable isolated schema."""
from concurrent.futures import ThreadPoolExecutor
import os
from threading import Event
import time
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url

from packages.chat.store import ChatStore, CaseNotFound
from packages.domain_bridge.planning_store import PlanningStore, metadata
from tests.chat.test_case_deletion import (
    test_delete_removes_snapshots_and_fences_running_worker as _fence,
    test_delete_rolls_back_job_removal_when_case_delete_fails as _rollback,
    test_foreign_and_stale_deletion_preserve_case_and_jobs as _guards,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def postgres():
    url = os.environ.get('CASE_DELETION_TEST_POSTGRES_URL')
    if not url:
        pytest.skip('CASE_DELETION_TEST_POSTGRES_URL is not configured')
    parsed = make_url(url)
    schema = 'case_delete_test_' + uuid4().hex
    admin = create_engine(parsed)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA {schema}'))
    chat = None
    try:
        scoped = parsed.update_query_dict({'options': f'-csearch_path={schema}'})
        chat = ChatStore(scoped.render_as_string(hide_password=False))
        metadata.create_all(chat.engine)
        yield chat, PlanningStore(chat.engine), admin
    finally:
        if chat is not None:
            chat.engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA {schema} CASCADE'))
        admin.dispose()


@pytest.mark.parametrize('first', ['enqueue', 'delete'])
def test_enqueue_delete_serialization_has_no_orphan_jobs(postgres, first):
    chat, jobs, admin = postgres
    case = chat.create('alice')
    locked, release = Event(), Event()
    blocker = []

    def hold(connection, cursor, statement, parameters, context, many):
        is_insert = statement.startswith('INSERT INTO planning_runs')
        is_case_lock = statement.startswith('SELECT chat_cases.revision') and 'FOR UPDATE' in statement
        if (first == 'enqueue' and is_insert) or (first == 'delete' and is_case_lock):
            blocker.append(connection.connection.driver_connection.info.backend_pid)
            locked.set()
            assert release.wait(10), 'test did not release the winning transaction'

    def enqueue():
        return jobs.enqueue('alice', case['id'], 0, 'request', {}, {'version': 'test'})

    def delete():
        return chat.delete('alice', case['id'], 0)

    event.listen(chat.engine, 'after_cursor_execute', hold)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            winner = pool.submit(enqueue if first == 'enqueue' else delete)
            try:
                assert locked.wait(10), 'winning transaction never acquired its lock'
                loser = pool.submit(delete if first == 'enqueue' else enqueue)
                deadline = time.monotonic() + 5
                blocked = False
                while time.monotonic() < deadline:
                    with admin.connect() as connection:
                        blocked = connection.execute(text(
                            'SELECT EXISTS (SELECT 1 FROM pg_stat_activity '
                            'WHERE :pid = ANY(pg_blocking_pids(pid)))'), {'pid': blocker[0]}).scalar_one()
                    if blocked:
                        break
                    time.sleep(.02)
                assert blocked, 'PostgreSQL did not report the expected row-lock wait'
            finally:
                release.set()
            winner.result(timeout=10)
            if first == 'delete':
                with pytest.raises(CaseNotFound):
                    loser.result(timeout=10)
            else:
                loser.result(timeout=10)
    finally:
        event.remove(chat.engine, 'after_cursor_execute', hold)
    assert chat.list('alice') == []
    assert jobs.list_case('alice', case['id'])['items'] == []
    assert jobs.find_request('alice', 'request') is None


@pytest.mark.parametrize('probe', [_fence, _rollback, _guards], ids=['worker-fence', 'rollback', 'owner-revision'])
def test_postgres_deletion_invariants(postgres, probe):
    chat, jobs, _ = postgres
    probe((chat, jobs))


def test_postgres_concurrent_creation_and_deleted_receipt(postgres):
    chat, _, _ = postgres
    request = str(uuid4())
    with ThreadPoolExecutor(max_workers=4) as pool:
        docs = list(pool.map(lambda _: chat.create('alice', request), range(8)))
    assert len({doc['id'] for doc in docs}) == 1
    doc = docs[0]
    doc['title'] = 'Retain updates'
    saved = chat.save('alice', doc, 0)
    assert chat.create('alice', request) == saved
    assert chat.create('bob', request)['id'] != saved['id']
    chat.delete('alice', saved['id'], saved['revision'])
    with pytest.raises(CaseNotFound):
        chat.create('alice', request)


def test_creation_receipt_migration_preserves_records_and_rls(postgres):
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from packages.chat.store import creations
    chat, _, _ = postgres
    path = Path(__file__).resolve().parents[2] / 'alembic/versions/0007_chat_case_creations.py'
    spec = importlib.util.spec_from_file_location('creation_migration', path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with chat.engine.begin() as connection:
        creations.drop(connection)
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
    request = str(uuid4())
    original = chat.create('alice', request)
    with chat.engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
            migration.upgrade()
        assert connection.execute(text("SELECT relrowsecurity FROM pg_class WHERE oid = 'chat_case_creations'::regclass")).scalar_one()
    assert chat.create('alice', request) == original
