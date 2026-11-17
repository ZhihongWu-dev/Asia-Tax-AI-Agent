from concurrent.futures import ThreadPoolExecutor

import pytest

from packages.chat.store import ChatStore, CaseNotFound, RevisionConflict
from packages.domain_bridge import planning_store as module
from packages.domain_bridge.planning_store import PlanningStore, PlanningConflict, LeaseLost


@pytest.fixture
def setup(tmp_path, monkeypatch):
    url = 'sqlite:///' + (tmp_path/'jobs.sqlite').as_posix()
    chat = ChatStore(url)
    module.metadata.create_all(chat.engine)
    clock = [1000.0]
    monkeypatch.setattr(module, '_clock', lambda connection: clock[0])
    return chat, PlanningStore(chat.engine), clock, url


def enqueue(chat, jobs, request='request', owner='alice'):
    case = chat.create(owner)
    run = jobs.enqueue(owner, case['id'], 0, request, {'amount':100}, {'uploaded_at':'pinned', 'overlay':'rev1'})
    return case, run


def test_case_pages_handle_ties_new_rows_and_foreign_cursors(setup):
    chat, jobs, clock, _ = setup
    case = chat.create('alice')
    rows = [jobs.enqueue('alice', case['id'], 0, str(n), {}, {'pin':'one'}) for n in range(5)]
    expected = sorted((row['id'] for row in rows), reverse=True)
    first = jobs.list_case('alice', case['id'], 2)
    assert [row['id'] for row in first['items']] == expected[:2]
    assert not {'input','case_snapshot','result','lease_token','owner'} & first['items'][0].keys()
    clock[0] += 1
    jobs.enqueue('alice', case['id'], 0, 'new', {}, {'pin':'one'})
    second = jobs.list_case('alice', case['id'], 2, first['next_before'])
    third = jobs.list_case('alice', case['id'], 2, second['next_before'])
    assert [row['id'] for row in second['items'] + third['items']] == expected[2:]
    assert third['next_before'] is None
    other, foreign = enqueue(chat, jobs, 'other', 'bob')
    with pytest.raises(CaseNotFound):
        jobs.list_case('alice', case['id'], 2, foreign['id'])
    with pytest.raises(CaseNotFound):
        jobs.list_case('alice', other['id'], 2, first['items'][0]['id'])
    for invalid in (0,101,True):
        with pytest.raises(ValueError):
            jobs.list_case('alice', case['id'], invalid)


def test_owner_revision_and_immutable_snapshot(setup):
    chat, jobs, _, _ = setup
    case, run = enqueue(chat, jobs)
    with pytest.raises(CaseNotFound):
        jobs.get('bob', run['id'])
    with pytest.raises(CaseNotFound):
        jobs.enqueue('bob', case['id'], 0, 'stolen', {}, {'version':'x'})
    with pytest.raises(RevisionConflict):
        jobs.enqueue('alice', case['id'], 1, 'stale', {}, {'version':'x'})
    case['title'] = 'later edit'
    chat.save('alice', case, 0)
    stored = jobs.get('alice', run['id'])
    assert stored['case_snapshot']['revision'] == 0
    assert stored['case_snapshot']['title'] == ''
    assert 'lease_token' not in stored
    assert stored['input'] == {'amount':100}
    assert stored['library_snapshot'] == {'uploaded_at':'pinned', 'overlay':'rev1'}
    assert jobs.enqueue('alice', case['id'], 0, 'request', {'amount':100},
                        {'uploaded_at':'pinned', 'overlay':'rev1'})['id'] == run['id']
    with pytest.raises(PlanningConflict):
        jobs.enqueue('alice', case['id'], 0, 'request', {'amount':101},
                     {'uploaded_at':'pinned', 'overlay':'rev1'})


def test_restart_reclaims_expired_lease_and_fences_old_worker(setup):
    chat, jobs, clock, url = setup
    _, run = enqueue(chat, jobs)
    first = jobs.claim(lease_seconds=5)
    assert first['id'] == run['id']
    assert jobs.claim() is None
    chat.engine.dispose()
    restarted = ChatStore(url)
    jobs = PlanningStore(restarted.engine)
    clock[0] += 5
    with pytest.raises(LeaseLost):
        jobs.heartbeat(run['id'], first['lease_token'])
    second = jobs.claim()
    assert second['lease_token'] != first['lease_token']
    assert second['attempts'] == 2
    with pytest.raises(LeaseLost):
        jobs.finish(run['id'], first['lease_token'], result={'report':'obsolete'})
    jobs.finish(run['id'], second['lease_token'], result={'report':'current'})
    stored = jobs.get('alice', run['id'])
    assert stored['result'] == {'report':'current'}
    assert stored['status'] == 'succeeded'
    assert [e['status'] for e in stored['events']] == ['queued','running','running','succeeded']
    assert jobs.claim() is None


def test_heartbeat_and_retry_budget(setup):
    chat, jobs, clock, _ = setup
    _, run = enqueue(chat, jobs)
    first = jobs.claim(lease_seconds=5, max_attempts=1)
    clock[0] += 4
    jobs.heartbeat(run['id'], first['lease_token'], lease_seconds=10)
    clock[0] += 2
    assert jobs.claim(max_attempts=1) is None
    clock[0] += 8
    assert jobs.claim(max_attempts=1) is None
    stored = jobs.get('alice', run['id'])
    assert stored['status'] == 'failed'
    assert stored['error'] == 'worker_attempts_exhausted'
    with pytest.raises(LeaseLost):
        jobs.finish(run['id'], first['lease_token'], result={})


def test_competing_workers_claim_once(setup):
    chat, jobs, _, _ = setup
    _, run = enqueue(chat, jobs)
    with ThreadPoolExecutor(max_workers=4) as pool:
        claims = list(pool.map(lambda _: jobs.claim(), range(4)))
    assert [c['id'] for c in claims if c is not None] == [run['id']]


def test_competing_submissions_are_idempotent(setup):
    chat, jobs, _, _ = setup
    case = chat.create('alice')
    with ThreadPoolExecutor(max_workers=4) as pool:
        submissions = list(pool.map(lambda _: jobs.enqueue('alice', case['id'], 0, 'same', {}, {'version':'x'}), range(4)))
    assert len({r['id'] for r in submissions}) == 1


def test_failure_is_terminal_and_does_not_accept_raw_exception(setup):
    chat, jobs, _, _ = setup
    _, run = enqueue(chat, jobs)
    claim = jobs.claim()
    with pytest.raises(ValueError):
        jobs.finish(run['id'], claim['lease_token'], error='secret connection string')
    jobs.finish(run['id'], claim['lease_token'], error='library_version_changed')
    assert jobs.get('alice', run['id'])['result'] is None
    assert jobs.claim() is None
    with pytest.raises(LeaseLost):
        jobs.finish(run['id'], claim['lease_token'], result={})


def test_real_database_clock_and_completed_result_survive_reopen(tmp_path):
    url = 'sqlite:///' + (tmp_path/'real-clock.sqlite').as_posix()
    chat = ChatStore(url)
    module.metadata.create_all(chat.engine)
    jobs = PlanningStore(chat.engine)
    _, run = enqueue(chat, jobs)
    claim = jobs.claim()
    assert claim['lease_until'] > claim['created_at'] > 0
    jobs.finish(run['id'], claim['lease_token'], result={'artifact_hash':'verified'})
    chat.engine.dispose()
    restarted = ChatStore(url)
    assert PlanningStore(restarted.engine).get('alice', run['id'])['result'] == {'artifact_hash':'verified'}
    restarted.engine.dispose()


def test_queued_runtime_survives_restart_and_cannot_be_silently_replaced(setup, monkeypatch):
    chat, jobs, clock, url = setup
    original = {'schema': 1, 'files': {'rule': 'original'}, 'citations': ['cn.rule#1']}
    monkeypatch.setattr(module, 'capture_runtime', lambda: original)
    case, run = enqueue(chat, jobs)
    assert run['runtime_snapshot'] == original
    first = jobs.claim(lease_seconds=5)
    monkeypatch.setattr(module, 'capture_runtime', lambda: {'schema': 1, 'files': {'rule': 'new'}})
    chat.engine.dispose()
    restarted = ChatStore(url)
    jobs = PlanningStore(restarted.engine)
    clock[0] += 5
    recovered = jobs.claim()
    assert recovered['runtime_snapshot'] == original
    assert recovered['lease_token'] != first['lease_token']
    with pytest.raises(PlanningConflict):
        jobs.enqueue('alice', case['id'], 0, 'request', {'amount':100},
                     {'uploaded_at':'pinned', 'overlay':'rev1'})
    restarted.engine.dispose()
