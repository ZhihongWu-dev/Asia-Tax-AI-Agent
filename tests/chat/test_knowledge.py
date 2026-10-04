from copy import deepcopy
from uuid import uuid4
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from packages.chat import knowledge, analysis
from packages.chat.service import ChatService, WorkflowError
from packages.chat.store import ChatStore


def test_multiple_references_use_cloud_query_and_ranking(monkeypatch):
    """Exercise actual SQL selection too, rather than mocking read_documents."""
    from sqlalchemy import create_engine, text
    engine = create_engine('sqlite://')
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE sources (id INTEGER PRIMARY KEY, source_id TEXT, l0_in_scope BOOLEAN, parse_status TEXT, actual_sha256 TEXT, manifest_sha256 TEXT, retrieved_at DATETIME)'))
        conn.execute(text('CREATE TABLE legal_units (source_db_id INTEGER, unit_ref TEXT, statute_locator TEXT, heading TEXT, text TEXT, text_sha256 TEXT, unit_type TEXT, ordinal INTEGER)'))
        for number, sid in [(1, 'law'), (2, 'hk_ird_advance_68')]:
            conn.execute(text("INSERT INTO sources VALUES (:id,:sid,1,'parsed',NULL,NULL,NULL)"), {'id': number, 'sid': sid})
        for index, ref in enumerate(['s.15K(1)', 's.15K(2)', 's.15K(3)', 's.15M(1)', 's.15M(2)', 's.15H(5)', 's.15H(6)', 's.15H(7)', 's.15H(1)', 's.15I(1)', 's.15I(3)', 's.15N(2)', 's.15N(5)', 's.15N(4)'], 1):
            conn.execute(text("INSERT INTO legal_units VALUES (1,:ref,:ref,'Heading','Synthetic text','hash','subsection',:n)"), {'ref': ref, 'n': index})
        for n in range(1, 8):
            conn.execute(text("INSERT INTO legal_units VALUES (2,:ref,NULL,'Heading','Synthetic ruling','hash','ruling_block',:n)"), {'ref': f'hk_ird_advance_68:section{n}', 'n': n})
    monkeypatch.setattr(knowledge, 'knowledge_engine', lambda: engine)
    monkeypatch.setattr(knowledge, 'catalog', lambda: {'allowed_source_domains': ['www.ird.gov.hk'], 'legal_coverage_cutoff': '2026-08-15', 'sources': [
        {'source_id': sid, 'url': 'https://www.ird.gov.hk/', 'title': 'Fixture'} for sid in ['law', 'hk_ird_advance_68']]})
    dataset = json.loads(Path(__file__).with_name('retrieval_cases.json').read_text(encoding='utf-8'))
    try:
        for case in dataset['cases']:
            result = knowledge.search(case['query'])
            assert result['status'] != 'unavailable', case['id']
            docs = result['passages']
            for key, field in [('expected_locators', 'locator'), ('expected_units', 'unit_id'), ('expected_sources', 'source_id')]:
                assert set(case.get(key, [])) <= {d[field] for d in docs}, case['id']
            if case.get('expect_empty'):
                assert result['status'] == 'no_matching_units' and not docs
            assert len(docs) == len({d['unit_id'] for d in docs})
        assert {d['locator'] for d in knowledge.search('s.15K and s.15M', limit=2)['passages']} == {'s.15K(1)', 's.15M(1)'}
        assert all(d['locator'] for d in knowledge.search('Case 68 s.15K', kind='law')['passages'])
        assert all(d['source_id'] == 'hk_ird_advance_68' for d in knowledge.search('Case 68 s.15K', kind='ruling')['passages'])
    finally:
        engine.dispose()


def test_reference_boundaries_and_parent_subsections():
    assert knowledge.references('s.15OA(1) 第15K（2）（a） 15K(2)') == (['s.15OA(1)', 's.15K(2)'], [])
    assert knowledge.references('x15K 115K 15K999') == ([], [])
    assert knowledge.references('Case 68 Case 69 Case 68')[1] == ['hk_ird_advance_68', 'hk_ird_advance_69']
    assert not knowledge.locator_matches('s.15KA(1)', 's.15K')
    assert not knowledge.locator_matches('s.15K(20)', 's.15K(2)')
    docs = [document('law', n, 'Fixture', f's.15K({n})') for n in range(1, 4)]
    assert knowledge.rank_documents(docs, 's.15K s.15K(2)', limit=0) == []
    result = knowledge.rank_documents(docs, 's.15K s.15K(2)', limit=7)
    assert len(result) == 3 and len({d['unit_id'] for d in result}) == 3


def test_short_context_is_batched_and_cannot_cross_source_or_snapshot(monkeypatch):
    short = {**document('faq', 4, 'outsourcing guidance'), 'unit_type': 'paragraph'}
    neighbors = [document('faq', 3, 'previous'), document('faq', 5, 'next'),
                 document('other', 5, 'wrong source'),
                 {**document('faq', 6, 'old snapshot'), 'snapshot_sha256': 'old'}]
    calls = []
    def read(**kwargs):
        calls.append(kwargs)
        return neighbors if 'context_ranges' in kwargs else [deepcopy(short)]
    monkeypatch.setattr(knowledge, 'read_documents', read)
    result = knowledge.search('outsourcing')
    assert len(calls) == 2 and calls[1]['context_ranges'] == [('faq', 3, 6)]
    assert [p['unit_id'] for p in result['passages'][0]['context']] == ['faq:section3', 'faq:section5']
    assert result['passages'][0]['text_sha256'] == short['text_sha256']


def test_weak_keyword_overlap_does_not_produce_unrelated_answer():
    docs = [document('other', 1, 'Dividend is the only overlapping word in this unrelated document.')]
    assert knowledge.rank_documents(docs, 'dividend weather temperature forecast') == []


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
    doc = service.message('owner', doc['id'], doc['revision'], str(uuid4()), '先看部分整理', True)
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
