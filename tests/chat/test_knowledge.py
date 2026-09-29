from copy import deepcopy
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from packages.chat import knowledge, analysis
from packages.chat.service import ChatService, WorkflowError
from packages.chat.store import ChatStore


def document(sid, number, text, locator=None):
    return {'source_id': sid, 'unit_id': f'{sid}:section{number}', 'heading': f'{number}. Test section',
            'ordinal': number, 'text': text, 'locator': locator,
            'unit_type': 'subsection' if locator else 'ruling_block', 'drift': True,
            'snapshot_sha256': 'a' * 64, 'text_sha256': 'b' * 64,
            'title': 'Synthetic retrieval fixture', 'url': 'https://www.ird.gov.hk/',
            'retrieved_at': '2026-09-27T00:00:00+00:00', 'coverage_cutoff': '2026-08-15'}


@pytest.fixture
def documents(monkeypatch):
    docs = [document('hk_ird_advance_68', n, text) for n, text in enumerate([
        'Test provisions', 'Dividend and economic substance background', 'Test arrangement',
        'Dividend economic substance ruling', '2023/24', 'No assumptions', '12 September 2023',
    ], 1)]
    docs += [document('hk_hkel_iro_cap112', 1, 'Participation exemption holding', 's.15M(2)')]
    monkeypatch.setattr(knowledge, 'read_documents', lambda **_: deepcopy(docs))
    monkeypatch.setattr(analysis, 'read_documents', lambda **_: deepcopy(docs))
    return docs


def test_bilingual_retrieval_exact_reference_and_unknown(documents):
    for query in ['Case 68', '裁定 68', '案例第68号']:
        result = knowledge.search(query, limit=7)
        assert len(result['passages']) == 7
        assert result['passages'][-1]['text'] == '12 September 2023'
    assert knowledge.search('第15M(2)条')['passages'][0]['locator'] == 's.15M(2)'
    assert knowledge.search('section 15M')['passages'][0]['locator'] == 's.15M(2)'
    assert knowledge.search('经济实质')['passages']
    assert knowledge.search('economic substance')['passages']
    assert knowledge.search('有哪些案例')['passages'][0]['ordinal'] == 4
    assert knowledge.search('What cases are there?')['passages'][0]['ordinal'] == 4
    assert knowledge.search('What is FSIE?')['passages']
    for query in ['case 999', 's.15Z(9)', 'weather forecast', "'; DROP TABLE sources; --"]:
        assert knowledge.search(query)['status'] == 'no_matching_units'
    assert knowledge.search('Case 68', kind='law')['passages'] == []


def test_case_query_failure_is_safe_and_atomic(tmp_path, monkeypatch):
    def fail(**_):
        raise RuntimeError('postgresql://private-secret@server/database')
    monkeypatch.setattr(knowledge, 'read_documents', fail)
    assert 'private-secret' not in str(knowledge.search('Case 68'))
    store = ChatStore(f'sqlite:///{tmp_path.as_posix()}/cases.sqlite')
    service = ChatService(store, extractor=lambda *_: {})
    doc = store.create('owner')
    with pytest.raises(WorkflowError, match='knowledge_unavailable'):
        service.message('owner', doc['id'], 0, str(uuid4()), 'Case 68', True)
    assert store.get('owner', doc['id']) == doc
    store.engine.dispose()


def test_research_preserves_confirmation_and_freezes_citations(tmp_path, documents):
    store = ChatStore(f'sqlite:///{tmp_path.as_posix()}/cases.sqlite')
    service = ChatService(store, extractor=lambda *_: {})
    doc = store.create('owner')
    doc = service.edit('owner', doc['id'], 0, str(uuid4()), {'income_type': 'dividend'})
    doc = service.confirm('owner', doc['id'], doc['revision'], str(uuid4()))
    confirmed = doc['confirmed_revision']
    request_id = str(uuid4())
    before = doc['revision']
    doc = service.message('owner', doc['id'], before, request_id, 'Case 68', True)
    assert doc['confirmed_revision'] == confirmed and doc['state'] == 'confirmed'
    assert doc['messages'][-1]['kind'] == 'research'
    assert service.message('owner', doc['id'], before, request_id, 'Case 68', True) == doc
    saved_text = doc['messages'][-1]['research']['passages'][0]['text']
    documents[0]['text'] = 'Changed later'
    assert store.get('owner', doc['id'])['messages'][-1]['research']['passages'][0]['text'] == saved_text
    doc = service.run('owner', doc['id'], doc['revision'], str(uuid4()))
    result = doc['analyses'][-1]
    assert len(result['review_tasks']) == 5
    assert len(result['related_rulings']['passages']) == 7
    assert result['citation_status'] == 'review_required'
    assert result['professional_validation_status'] == 'unverified'
    store.engine.dispose()


def test_search_api_validates_and_requires_workspace(documents, monkeypatch):
    from apps.api.auth import optional_user
    from tests.chat.auth_support import fixture_user
    monkeypatch.setitem(app.dependency_overrides, optional_user, fixture_user)
    with TestClient(app) as client:
        assert client.get('/api/knowledge/search?q=Case%2068').status_code == 401
        client.get('/api/session')
        assert len(client.get('/api/knowledge/search?q=Case%2068').json()['passages']) == 7
        assert client.get('/api/knowledge/search?q=x').status_code == 422
        assert client.get('/api/knowledge/search?q=Case&kind=invalid').status_code == 422
