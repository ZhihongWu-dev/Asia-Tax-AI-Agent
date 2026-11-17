from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.chat import router, get_service, owner
from packages.chat.store import ChatStore
from packages.chat import library_cloud
from packages.domain_bridge.planning_store import metadata


def test_save_queue_read_and_retry_are_owner_and_revision_scoped(tmp_path, monkeypatch):
    store = ChatStore('sqlite:///' + (tmp_path/'api.sqlite').as_posix())
    metadata.create_all(store.engine)
    case = store.create('alice')
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_service] = lambda: SimpleNamespace(store=store)
    app.dependency_overrides[owner] = lambda: 'alice'
    monkeypatch.setattr(library_cloud, 'current_library_snapshot', lambda: {'pin':'test'})
    inputs = {'date':'2026-11-17','mode':'plan','amount':0,'currency':'JPY',
              'payer':{'jur':'jp'},'payee':{'jur':'sg','subject':'individual'}}
    prefix = '/api/cases/' + case['id']
    with TestClient(app) as client:
        saved = client.put(prefix+'/planning-input', json={'revision':0,'request_id':str(uuid4()),'inputs':inputs})
        assert saved.status_code == 200, saved.text
        assert saved.json()['revision'] == 1
        request = {'revision':1,'request_id':str(uuid4())}
        submitted = client.post(prefix+'/planning-runs', json=request)
        assert submitted.status_code == 202, submitted.text
        run = submitted.json()
        assert run['status'] == 'queued' and run['input']['amount'] == 0
        assert 'lease_token' not in run and 'owner' not in run
        url = prefix+'/planning-runs/'+run['id']
        assert client.get(url).json()['id'] == run['id']
        listing = client.get(prefix+'/planning-runs?limit=1')
        assert listing.status_code == 200
        assert listing.json()['items'][0]['id'] == run['id']
        assert 'result' not in listing.json()['items'][0]
        assert client.get(prefix+'/planning-runs?limit=101').status_code == 422
        current = store.get('alice', case['id'])
        store.save('alice', current, 1)
        monkeypatch.setattr(library_cloud, 'current_library_snapshot', lambda: (_ for _ in ()).throw(AssertionError('retry read cloud')))
        assert client.post(prefix+'/planning-runs', json=request).json()['id'] == run['id']
        assert client.post(prefix+'/planning-runs', json={**request,'revision':2}).status_code == 409
        assert client.post(prefix+'/planning-runs', json={'revision':1,'request_id':str(uuid4())}).status_code == 409
        other = store.create('alice')
        assert client.get('/api/cases/'+other['id']+'/planning-runs/'+run['id']).status_code == 404
        app.dependency_overrides[owner] = lambda: 'bob'
        assert client.get(prefix+'/planning-runs').status_code == 404
        assert client.get(url).status_code == 404
        assert client.post(prefix+'/planning-runs', json=request).status_code == 404
        del app.dependency_overrides[owner]
        assert client.get(url).status_code == 401
    store.engine.dispose()
