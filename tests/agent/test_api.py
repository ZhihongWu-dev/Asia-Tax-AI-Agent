import json
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from apps.api.main import app
from apps.api.auth import optional_user
from apps.api.chat import get_service, get_provider
from packages.agent.providers import MockKnowledgeProvider
from packages.chat.service import ChatService
from packages.chat.store import ChatStore

USER = {'id': 'd06000ef-f8ef-4699-a3ee-eb12bd6249a9', 'email': 'fixture@example.invalid'}
HEADERS = {'x-asiatax-request': '1'}


@pytest.fixture
def api(tmp_path):
    provider = MockKnowledgeProvider()
    store = ChatStore(f'sqlite:///{tmp_path}/api.sqlite')
    service = ChatService(store, provider=provider, turner=lambda *_: {
        'intent': 'research', 'facts': {}, 'reply': 'NEVER_RELEASE_UNCHECKED', 'query': '测试查询'})
    app.dependency_overrides[optional_user] = lambda: USER
    app.dependency_overrides[get_service] = lambda: service
    app.dependency_overrides[get_provider] = lambda: provider
    with TestClient(app) as client:
        yield client, service
    app.dependency_overrides.clear()
    store.engine.dispose()


def new_case(client):
    return client.post('/api/cases', headers=HEADERS).json()


def mutation(doc, **kwargs):
    return dict(revision=doc['revision'], request_id=str(uuid4()), **kwargs)


def test_sse_and_json_shared_graph_and_retry(api):
    client, service = api
    a, b = new_case(client), new_case(client)
    body = mutation(a, text='测试', data_approved=True)
    path = f"/api/cases/{a['id']}/messages"
    response = client.post(path, headers={**HEADERS, 'accept': 'text/event-stream'}, json=body)
    assert 'NEVER_RELEASE_UNCHECKED' not in response.text
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
    assert [e['type'] for e in events] == ['done']
    doc = events[0]['case']
    plain = client.post(f"/api/cases/{b['id']}/messages", headers=HEADERS,
                        json=mutation(b, text='测试', data_approved=True)).json()
    assert doc['messages'][-1]['text'] == plain['messages'][-1]['text']
    assert doc['workflow']['trace'] == plain['workflow']['trace']
    assert client.post(path, headers=HEADERS, json=body).json() == doc
    assert len(doc['messages']) == 2


def test_reference_panel_uses_same_provider(api):
    client, _ = api
    result = client.get('/api/knowledge/search?q=测试查询').json()
    assert result['provider'] == 'mock' and result['is_synthetic']
    assert 'model_evidence' not in result
    assert result['passages'][0]['is_synthetic']


def test_error_not_no_match_and_no_partial_commit(api):
    client, service = api
    service.provider = MockKnowledgeProvider('MOCK-04')
    original = new_case(client)
    path = f"/api/cases/{original['id']}/messages"
    response = client.post(path, headers=HEADERS, json=mutation(original, text='测试', data_approved=True))
    assert response.status_code == 503 and response.json()['detail'] == 'knowledge_unavailable'
    response = client.post(path, headers={**HEADERS, 'accept': 'text/event-stream'}, json=mutation(original, text='测试', data_approved=True))
    assert 'knowledge_unavailable' in response.text and '"type": "done"' not in response.text
    assert client.get(f"/api/cases/{original['id']}").json() == original
    service.provider = MockKnowledgeProvider('MOCK-02')
    result = client.post(path, headers=HEADERS, json=mutation(original, text='测试', data_approved=True))
    assert result.status_code == 200 and result.json()['workflow']['reason_code'] == 'no_match'


def test_review_api_does_not_trust_body_roles(api, monkeypatch):
    client, _ = api
    doc = new_case(client)
    doc = client.patch(f"/api/cases/{doc['id']}/facts", headers=HEADERS,
                       json=mutation(doc, facts={'income_type': 'dividend'})).json()
    doc = client.post(f"/api/cases/{doc['id']}/messages", headers=HEADERS,
                      json=mutation(doc, text='先看部分整理', data_approved=True)).json()
    doc = client.post(f"/api/cases/{doc['id']}/confirm", headers=HEADERS, json=mutation(doc)).json()
    doc = client.post(f"/api/cases/{doc['id']}/analyze", headers=HEADERS, json=mutation(doc)).json()
    report = doc['analyses'][-1]
    path = f"/api/cases/{doc['id']}/analyses/{report['id']}/review"
    body = mutation(doc, report_hash=report['report_hash'], decision='changes_requested', note='测试退回')
    assert client.post(path, headers=HEADERS, json={**body, 'role': 'advisor'}).status_code == 403
    monkeypatch.setenv('FSIE_AGENT_REVIEWER_IDS', json.dumps([USER['id']]))
    response = client.post(path, headers=HEADERS, json=body)
    assert response.status_code == 200
    assert response.json()['analyses'][-1]['review']['status'] == 'changes_requested'
