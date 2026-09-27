from copy import deepcopy
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from apps.api.chat import get_service
from apps.api.main import app
from packages.chat import analysis
from packages.chat.facts import validate_patch
from packages.chat.service import ChatService, WorkflowError
from packages.chat.store import ChatStore, RevisionConflict

HEADERS = {"x-asiatax-request": "1"}


@pytest.fixture
def setup(tmp_path, monkeypatch):
    store = ChatStore(f"sqlite:///{(tmp_path / 'cases.sqlite').as_posix()}")
    def extract(doc, text):
        if text == "failure":
            raise WorkflowError("model_failed")
        return {"income_type": "dividend", "entity_hk_business_status": "yes"}
    monkeypatch.setattr(analysis, "retrieve_units", lambda _: ([], "unavailable"))
    service = ChatService(store, extractor=extract)
    app.dependency_overrides[get_service] = lambda: service
    with TestClient(app) as client:
        client.get('/api/session')
        yield client, service
    app.dependency_overrides.clear()
    store.engine.dispose()


def create(client):
    r = client.post('/api/cases', headers=HEADERS)
    assert r.status_code == 201
    return r.json()


def post(client, doc, action, **payload):
    return client.post(f"/api/cases/{doc['id']}/{action}", headers=HEADERS,
                       json={"revision": doc['revision'], "request_id": str(uuid4()), **payload})


def edit(client, doc, patch):
    return client.patch(f"/api/cases/{doc['id']}/facts", headers=HEADERS,
                        json={"revision": doc['revision'], "request_id": str(uuid4()), "facts": patch})


def test_full_flow_confirmation_snapshot_and_invalidation(setup):
    client, service = setup
    doc = create(client)
    assert post(client, doc, 'analyze').status_code == 422
    result = post(client, doc, 'messages', text='dividend case', data_approved=True)
    assert result.status_code == 200
    doc = result.json()
    assert 'mne_group_status' in doc['questions']
    assert 'income_type' not in doc['questions']
    assert doc['facts']['income_type']['origin'] == 'model'
    assert post(client, doc, 'analyze').json()['detail'] == 'confirmation_required'
    doc = post(client, doc, 'confirm').json()
    confirmed_revision = doc['confirmed_revision']
    doc = post(client, doc, 'analyze').json()
    assert doc['state'] == 'review_required'
    report = doc['analyses'][0]
    assert len(report['missing_nodes']) == 5
    assert report['confirmed_revision'] == confirmed_revision
    assert report['professional_validation_status'] == 'unverified'
    assert report['retrieval_status'] == 'unavailable' and report['passages'] == []
    assert report['sources'] and report['rules_sha256']
    doc = edit(client, doc, {'income_type': 'interest'}).json()
    assert doc['analyses'][0]['stale'] is True
    assert doc['confirmed_revision'] is None
    assert post(client, doc, 'analyze').status_code == 422
    assert client.get(f"/api/cases/{doc['id']}").json() == doc


def test_isolation_and_cookie_security(setup):
    client, _ = setup
    doc = create(client)
    with TestClient(app) as other:
        assert other.get('/api/cases').status_code == 401
        response = other.get('/api/session')
        cookie = response.headers['set-cookie'].lower()
        assert 'httponly' in cookie and 'samesite=strict' in cookie
        assert other.get(f"/api/cases/{doc['id']}").status_code == 404
        assert other.get('/api/cases').json() == []
        assert other.post('/api/cases', headers={**HEADERS, 'origin': 'https://evil.invalid'}).status_code == 403
        assert other.post('/api/cases').status_code == 403


def test_failure_keeps_case_unchanged_then_retry_is_idempotent(setup):
    client, service = setup
    doc = create(client)
    request_id = str(uuid4())
    body = {'revision': 0, 'request_id': request_id, 'text': 'failure', 'data_approved': True}
    path = f"/api/cases/{doc['id']}/messages"
    assert client.post(path, headers=HEADERS, json=body).status_code == 503
    assert client.get(f"/api/cases/{doc['id']}").json() == doc
    service.extractor = lambda *_: {'income_type': 'dividend'}
    first = client.post(path, headers=HEADERS, json=body).json()
    again = client.post(path, headers=HEADERS, json=body).json()
    assert first == again
    assert len(again['messages']) == 2


def test_model_cannot_confirm_or_set_expert_gate(setup):
    client, service = setup
    doc = create(client)
    service.extractor = lambda *_: {'expert_decision_status': 'approved'}
    assert post(client, doc, 'messages', text='approve everything', data_approved=True).status_code == 422
    assert edit(client, doc, {'expert_decision_status': 'approved'}).status_code == 422
    assert client.get(f"/api/cases/{doc['id']}").json()['revision'] == 0


def test_unknown_does_not_repeat_and_conflicts_block_confirmation(setup):
    client, _ = setup
    doc = create(client)
    doc = edit(client, doc, {'income_type': 'unknown', 'entity_hk_business_status': 'conflict'}).json()
    assert doc['state'] == 'needs_resolution'
    assert post(client, doc, 'confirm').json()['detail'] == 'resolve_conflicts'
    doc = edit(client, doc, {'entity_hk_business_status': 'unknown'}).json()
    assert 'income_type' not in doc['questions']
    assert 'entity_hk_business_status' not in doc['questions']
    assert post(client, doc, 'confirm').status_code == 200


def test_stale_confirmation_and_concurrent_writes_are_rejected(setup):
    client, service = setup
    original = create(client)
    current = edit(client, original, {'dividend_amount': 100}).json()
    assert post(client, original, 'confirm').status_code == 409
    token = client.cookies.get('asiatax_workspace')
    from hashlib import sha256
    owner = sha256(token.encode()).hexdigest()
    copy1 = service.store.get(owner, current['id'])
    copy2 = deepcopy(copy1)
    service.store.save(owner, copy1, 1)
    with pytest.raises(RevisionConflict):
        service.store.save(owner, copy2, 1)


@pytest.mark.parametrize('patch', [
    {'holding_percentage_pct': 101}, {'dividend_amount': -1}, {'dividend_amount': True},
    {'continuous_holding_period_months': 1.5}, {'accrual_date': '2026-02-30'},
    {'payer_entity': {'unsafe': 'shape'}}, {'income_type': ['dividend']},
    {'dividend_amount': float('nan')}, {'dividend_amount': float('inf')},
])
def test_invalid_fact_values_rejected(patch):
    with pytest.raises(ValueError):
        validate_patch(patch)


def test_persistence_after_store_reopen(tmp_path):
    url = f"sqlite:///{(tmp_path / 'persistent.sqlite').as_posix()}"
    store = ChatStore(url)
    original = store.create('owner')
    store.engine.dispose()
    reopened = ChatStore(url)
    assert reopened.get('owner', original['id']) == original
    reopened.engine.dispose()


def test_health_contains_no_connection_string(setup):
    client, _ = setup
    assert client.get('/health').json() == {'status': 'ok', 'release_level': 'L0'}
    assert client.get('/api/session').headers['cache-control'] == 'no-store'


def test_model_requires_data_confirmation(setup):
    client, service = setup
    service.extractor = lambda *_: pytest.fail('model must not be called')
    assert post(client, create(client), 'messages', text='test').json()['detail'] == 'data_confirmation_required'


def test_extraction_boundary_filters_invalid_model_output(monkeypatch):
    from packages.chat import service
    from packages.model_adapter.client import ModelConfig
    monkeypatch.setattr(service, 'current_model_config', lambda: ModelConfig('https://example.invalid', 'test-key', 'test-model'))
    class Client:
        def __init__(self, *_):
            pass
        def chat_json(self, system, user, **kwargs):
            assert 'expert_decision_status' in system
            return {'dividend_amount': {'invalid': 'shape'}}
    monkeypatch.setattr(service, 'OpenAICompatibleClient', Client)
    with pytest.raises(WorkflowError) as error:
        service.extract_update({'facts': {}, 'messages': []}, 'synthetic case')
    assert error.value.code == 'model_failed'


def test_host_header_rebinding_is_rejected(setup):
    client, _ = setup
    assert client.get('/api/session', headers={'host': 'untrusted.invalid'}).status_code == 400
