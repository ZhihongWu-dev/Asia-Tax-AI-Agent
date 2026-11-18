from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy import event

from packages.chat.store import ChatStore, CaseNotFound, RevisionConflict
from packages.domain_bridge.planning_store import PlanningStore, LeaseLost, metadata
from tests.chat.test_workflow import setup, create, HEADERS


@pytest.fixture
def stores(tmp_path):
    chat = ChatStore('sqlite:///' + (tmp_path / 'delete.sqlite').as_posix())
    metadata.create_all(chat.engine)
    yield chat, PlanningStore(chat.engine)
    chat.engine.dispose()


def test_delete_removes_snapshots_and_fences_running_worker(stores):
    chat, jobs = stores
    case = chat.create('alice')
    original = deepcopy(case)
    run = jobs.enqueue('alice', case['id'], 0, 'one', {}, {'version': 'test'})
    lease = jobs.claim()
    other = chat.create('bob')
    chat.delete('alice', case['id'], 0)
    assert chat.list('alice') == []
    assert chat.get('bob', other['id']) == other
    for read in (lambda: chat.get('alice', case['id']), lambda: jobs.get('alice', run['id'])):
        with pytest.raises(CaseNotFound):
            read()
    assert jobs.find_request('alice', 'one') is None
    assert jobs.list_case('alice', case['id'])['items'] == []
    with pytest.raises(LeaseLost):
        jobs.finish(run['id'], lease['lease_token'], result={'late': True})
    with pytest.raises(CaseNotFound):
        jobs.enqueue('alice', case['id'], 0, 'later', {}, {'version': 'test'})
    with pytest.raises(RevisionConflict):
        chat.save('alice', original, 0)


def test_foreign_and_stale_deletion_preserve_case_and_jobs(stores):
    chat, jobs = stores
    case = chat.create('alice')
    run = jobs.enqueue('alice', case['id'], 0, 'one', {}, {'version': 'test'})
    for owner, revision, error in [('bob', 0, CaseNotFound), ('alice', 1, RevisionConflict)]:
        with pytest.raises(error):
            chat.delete(owner, case['id'], revision)
        assert chat.get('alice', case['id']) == case
        assert jobs.get('alice', run['id'])['status'] == 'queued'


def test_delete_rolls_back_job_removal_when_case_delete_fails(stores):
    chat, jobs = stores
    case = chat.create('alice')
    run = jobs.enqueue('alice', case['id'], 0, 'one', {}, {'version': 'test'})
    def fail(connection, cursor, statement, parameters, context, many):
        if statement.startswith('DELETE FROM chat_cases'):
            raise RuntimeError('injected failure')
    event.listen(chat.engine, 'before_cursor_execute', fail)
    try:
        with pytest.raises(RuntimeError, match='injected failure'):
            chat.delete('alice', case['id'], 0)
    finally:
        event.remove(chat.engine, 'before_cursor_execute', fail)
    assert chat.get('alice', case['id']) == case
    assert jobs.get('alice', run['id'])['status'] == 'queued'


def test_delete_api_revision_guard_and_no_resurrection(setup):
    client, service = setup
    metadata.create_all(service.store.engine)
    case = create(client)
    path = f"/api/cases/{case['id']}"
    payload = {'revision': 1, 'request_id': str(uuid4())}
    assert client.request('DELETE', path, headers=HEADERS, json=payload).status_code == 409
    assert client.get(path).status_code == 200
    payload['revision'] = 0
    assert client.request('DELETE', path, headers=HEADERS, json=payload).status_code == 200
    assert client.get(path).status_code == 404
    assert client.request('DELETE', path, headers=HEADERS, json=payload).status_code == 404
