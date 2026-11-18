from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from packages.chat.store import ChatStore, CaseNotFound
from packages.domain_bridge.planning_store import metadata
from tests.chat.test_workflow import setup, HEADERS


def test_concurrent_creation_reuses_latest_document_and_keeps_owners_separate(tmp_path):
    store = ChatStore('sqlite:///' + (tmp_path / 'creation.sqlite').as_posix())
    request = str(uuid4())
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            cases = list(pool.map(lambda _: store.create('alice', request), range(8)))
        assert len({case['id'] for case in cases}) == 1
        doc = cases[0]
        doc['title'] = 'Keep my edits'
        saved = store.save('alice', doc, 0)
        assert store.create('alice', request) == saved
        assert store.create('bob', request)['id'] != saved['id']
        assert len(store.list('alice')) == 1
        metadata.create_all(store.engine)
        store.delete('alice', saved['id'], saved['revision'])
        with pytest.raises(CaseNotFound):
            store.create('alice', request)
        assert store.list('alice') == []
    finally:
        store.engine.dispose()


def test_creation_api_retries_and_legacy_clients(setup):
    client, _ = setup
    payload = {'request_id': str(uuid4())}
    first = client.post('/api/cases', headers=HEADERS, json=payload)
    retry = client.post('/api/cases', headers=HEADERS, json=payload)
    assert first.status_code == retry.status_code == 201
    assert first.json() == retry.json()
    assert client.post('/api/cases', headers=HEADERS).json()['id'] != first.json()['id']
    assert client.post('/api/cases', headers=HEADERS, json={'request_id':'invalid'}).status_code == 422
