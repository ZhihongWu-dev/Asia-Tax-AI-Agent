import json
from pathlib import Path

import pytest

from packages.chat.planning import save_case, enqueue_saved
from packages.chat.store import ChatStore, CaseNotFound, RevisionConflict
from packages.contracts.planning import PlanningInput
from packages.domain_bridge.planning_store import PlanningStore, metadata
from packages.domain_bridge.planning_store import PlanningConflict


def test_saved_input_is_bound_to_revision_and_survives_edits(tmp_path):
    chat = ChatStore('sqlite:///' + (tmp_path/'cases.sqlite').as_posix())
    metadata.create_all(chat.engine)
    jobs = PlanningStore(chat.engine)
    doc = chat.create('alice')
    source = json.loads((Path(__file__).resolve().parents[2]/
                        'optimization/examples/case_jp_sg_individual.json').read_text(encoding='utf-8'))
    inputs = PlanningInput.model_validate(source)
    saved = save_case(chat, 'alice', doc['id'], 0, 'save', inputs)
    assert saved['revision'] == 1
    assert save_case(chat, 'alice', doc['id'], 0, 'save', inputs)['revision'] == 1
    with pytest.raises(CaseNotFound):
        enqueue_saved(chat, jobs, 'bob', doc['id'], 1, 'stolen', {'pin':'one'})
    with pytest.raises(RevisionConflict):
        enqueue_saved(chat, jobs, 'alice', doc['id'], 0, 'stale', {'pin':'one'})
    run = enqueue_saved(chat, jobs, 'alice', doc['id'], 1, 'run', {'pin':'one'})
    assert run['input'] == run['case_snapshot']['planning_input'] == source
    source['amount'] = 7
    save_case(chat, 'alice', doc['id'], 1, 'edit', PlanningInput.model_validate(source))
    assert jobs.get('alice', run['id'])['input']['amount'] == 200000000
    assert chat.get('alice', doc['id'])['planning_history'][0]['input']['amount'] == 200000000
    chat.engine.dispose()
    restarted = ChatStore('sqlite:///' + (tmp_path/'cases.sqlite').as_posix())
    restarted_jobs = PlanningStore(restarted.engine)
    replay = enqueue_saved(restarted, restarted_jobs, 'alice', doc['id'], 1, 'run', {'pin':'one'})
    assert replay['id'] == run['id']
    assert replay['input']['amount'] == 200000000
    for revision, pin in [(2, {'pin':'one'}), (1, {'pin':'changed'})]:
        with pytest.raises(PlanningConflict):
            enqueue_saved(restarted, restarted_jobs, 'alice', doc['id'], revision, 'run', pin)
    other = restarted.create('alice')
    with pytest.raises(PlanningConflict):
        enqueue_saved(restarted, restarted_jobs, 'alice', other['id'], 1, 'run', {'pin':'one'})
    assert restarted_jobs.find_request('bob', 'run') is None
    restarted.engine.dispose()


def test_concurrent_edit_between_projection_and_enqueue_rejected(tmp_path, monkeypatch):
    chat = ChatStore('sqlite:///' + (tmp_path/'race.sqlite').as_posix())
    metadata.create_all(chat.engine)
    jobs = PlanningStore(chat.engine)
    doc = chat.create('alice')
    source = {'date':'2026-11-17','mode':'plan','amount':0,'currency':'JPY',
              'payer':{'jur':'jp'},'payee':{'jur':'sg','subject':'individual'}}
    save_case(chat, 'alice', doc['id'], 0, 'save', PlanningInput.model_validate(source))
    original = jobs.enqueue
    def race(*args):
        current = chat.get('alice', doc['id'])
        chat.save('alice', current, 1)
        return original(*args)
    monkeypatch.setattr(jobs, 'enqueue', race)
    with pytest.raises(RevisionConflict):
        enqueue_saved(chat, jobs, 'alice', doc['id'], 1, 'run', {'pin':'one'})
    assert jobs.claim() is None
    chat.engine.dispose()
