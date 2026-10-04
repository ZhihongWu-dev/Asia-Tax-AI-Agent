from copy import deepcopy
from hashlib import sha256
import json
from uuid import uuid4

import httpx
import pytest
from pydantic import ValidationError

from packages.agent.contracts import SearchRequest, SearchResult, TrustedContext, Evidence, EvidenceResult
from packages.agent.providers import MockKnowledgeProvider, CKnowledgeProvider, ProviderSettings
from packages.agent.knowledge import retrieve, compose_answer, validate_answer
from packages.agent.review import freeze, review_report
from packages.chat.service import ChatService, WorkflowError, turn_prompt
from packages.chat.store import ChatStore, RevisionConflict

CONTEXT = TrustedContext(owner='user:test', case_id='case-test')


def request(**kwargs):
    return SearchRequest(request_id='request', trace_id='trace', query='测试查询', **kwargs)


@pytest.mark.parametrize('number,reason,calls,models,displays', [
    (1, 'evidence_available', 1, 1, 1), (2, 'no_match', 1, 0, 0),
    (3, 'evidence_restricted', 1, 0, 1), (4, 'retrieval_failed', 2, 0, 0),
    (5, 'evidence_insufficient', 1, 1, 1), (6, 'evidence_restricted', 1, 0, 0),
    (7, 'evidence_insufficient', 1, 0, 0), (8, 'retrieval_failed', 1, 0, 0),
])
def test_fixture_paths(number, reason, calls, models, displays):
    provider = MockKnowledgeProvider(f'MOCK-{number:02d}')
    req = request(applicable_date='2026-10-02', date_status='actual') if number == 7 else request()
    result = retrieve(provider, req, CONTEXT)
    assert result['reason_code'] == reason
    assert result['retrieval_calls'] == calls
    assert len(result['model_evidence']) == models
    assert len(result['passages']) == displays
    answer = compose_answer(result)
    assert '模拟' in answer['summary']
    validate_answer(answer, result)
    assert answer['review_status'] == 'pending_final_review'


def test_model_only_permission_cannot_disclose_summary():
    provider = MockKnowledgeProvider()
    provider.fixture = deepcopy(provider.fixture)
    e = provider.fixture['search_response']['evidence'][0]
    e.update(display_use='denied', display_ref=None)
    result = retrieve(provider, request(), CONTEXT)
    assert result['model_evidence'] == result['passages'] == []
    assert e['model_text'] not in compose_answer(result)['text']


def test_unknown_permission_and_exact_version():
    provider = MockKnowledgeProvider('MOCK-06')
    e = Evidence.model_validate(provider.fixture['search_response']['evidence'][0])
    assert provider.get_evidence(e.reference(), 'display', CONTEXT).status == 'restricted'
    provider = MockKnowledgeProvider()
    e = Evidence.model_validate(provider.fixture['search_response']['evidence'][0])
    ref = e.reference().model_copy(update={'source_version_id': 'latest'})
    assert provider.get_evidence(ref, 'display', CONTEXT).status == 'version_unavailable'


def test_bad_permissions_and_hashes_fail_closed():
    provider = MockKnowledgeProvider()
    e = deepcopy(provider.fixture['search_response']['evidence'][0])
    e['model_use'] = 'unknown'
    with pytest.raises(ValidationError):
        Evidence.model_validate(e)
    provider.fixture = deepcopy(provider.fixture)
    provider.fixture['display_store'][0]['text'] = 'tampered'
    result = retrieve(provider, request(), CONTEXT)
    assert not result['model_evidence'] and not result['passages']
    assert result['reason_code'] == 'evidence_insufficient'


def test_c_http_contract_and_trusted_identity():
    seen = []
    fixture = MockKnowledgeProvider().search_evidence(request(), CONTEXT).model_dump(mode='json')
    fixture['provider'] = 'c'
    def handle(req):
        seen.append(json.loads(req.content))
        return httpx.Response(200, json=fixture)
    provider = CKnowledgeProvider('https://c.test', 'test-only', httpx.MockTransport(handle))
    assert provider.search_evidence(request(), CONTEXT).provider == 'c'
    assert seen[0]['trusted_context']['owner'] == 'user:test'
    assert seen[0]['request']['query'] == '测试查询'
    assert 'test-only' not in str(seen)


@pytest.mark.parametrize('status,code,retryable', [(403, 'ACCESS_DENIED', False), (503, 'HTTP_ERROR', True), (429, 'HTTP_ERROR', True)])
def test_c_errors_are_explicit_no_mock_fallback(status, code, retryable):
    provider = CKnowledgeProvider('https://c.test', transport=httpx.MockTransport(lambda _: httpx.Response(status)))
    result = provider.search_evidence(request(), CONTEXT)
    assert result.provider == 'c' and not result.is_synthetic
    assert result.error.code == code and result.error.retryable is retryable


def test_c_identity_mismatch_rejected():
    fixture = MockKnowledgeProvider().search_evidence(request(), CONTEXT).model_dump(mode='json')
    fixture.update(provider='c', request_id='wrong')
    provider = CKnowledgeProvider('https://c.test', transport=httpx.MockTransport(lambda _: httpx.Response(200, json=fixture)))
    assert provider.search_evidence(request(), CONTEXT).error.code == 'INVALID_RESPONSE'


def test_c_missing_or_unsafe_config_never_enables_mock():
    for value in ['', 'http://internet.test', 'https://user:pass@c.test']:
        with pytest.raises(ValueError):
            CKnowledgeProvider(value)


@pytest.fixture
def chat(tmp_path):
    store = ChatStore(f'sqlite:///{tmp_path}/cases.sqlite')
    chat = ChatService(store, provider=MockKnowledgeProvider(), turner=lambda *_: {
        'intent': 'research', 'facts': {}, 'reply': 'PRE_RETRIEVAL_UNSAFE', 'query': '测试查询'})
    yield chat
    store.engine.dispose()


def send(chat, doc, text='测试问题', request_id=None):
    return chat.message('owner', doc['id'], doc['revision'], request_id or str(uuid4()), text, True)


def test_graph_routes_and_retrieval_replaces_model_preamble(chat):
    doc = send(chat, chat.store.create('owner'))
    message = doc['messages'][-1]
    assert message['workflow']['trace'] == ['route', 'facts', 'retrieve', 'compose', 'validate']
    assert 'PRE_RETRIEVAL_UNSAFE' not in message['text']
    assert 'model_evidence' not in message['research']
    assert message['answer']['claims'][0]['evidence_ids'] == ['mock-evidence-1']
    system, context = turn_prompt(doc, '继续')
    assert '模拟资料 MOCK-01：' not in context  # no original copied from history
    assert 'PRE_RETRIEVAL_UNSAFE' not in context


def test_chat_does_not_retrieve_and_same_request_is_idempotent(chat):
    chat.turner = lambda *_: {'intent': 'chat', 'facts': {}, 'reply': 'Hello', 'query': ''}
    chat.provider.search_evidence = lambda *_: pytest.fail('must not retrieve')
    original = chat.store.create('owner')
    token = str(uuid4())
    first = send(chat, original, request_id=token)
    assert send(chat, original, request_id=token) == first
    assert first['workflow']['trace'] == ['route', 'facts', 'validate']


def test_new_conflicting_value_preserved_without_silent_override(chat):
    doc = chat.store.create('owner')
    doc = chat.edit('owner', doc['id'], 0, str(uuid4()), {'dividend_amount': 100})
    chat.turner = lambda *_: {'intent': 'research', 'facts': {'dividend_amount': 200}, 'reply': 'replace', 'query': '研究股息'}
    doc = send(chat, doc)
    assert doc['facts']['dividend_amount']['value'] == 'conflict'
    assert doc['fact_conflicts']['dividend_amount'] == {'previous': 100, 'candidate': 200}
    assert doc['messages'][-1]['question_fields'] == ['dividend_amount']
    assert 'retrieve' not in doc['workflow']['trace']
    with pytest.raises(WorkflowError):
        chat.confirm('owner', doc['id'], doc['revision'], str(uuid4()))
    doc = chat.edit('owner', doc['id'], doc['revision'], str(uuid4()), {'dividend_amount': 200})
    assert doc['fact_conflicts'] == {}


def test_unknown_not_false_and_one_question(chat):
    chat.turner = lambda *_: {'intent': 'intake', 'facts': {'income_type': 'dividend', 'recipient_type': 'unknown'}, 'reply': 'ok', 'query': ''}
    doc = send(chat, chat.store.create('owner'))
    assert doc['facts']['recipient_type']['value'] == 'unknown'
    assert doc['questions'] == []
    assert doc['messages'][-1]['question']['kind'] == 'choice'
    assert doc['facts'].get('entity_hk_business_status') is None


def test_individual_case_out_of_scope(chat):
    chat.turner = lambda *_: {'intent': 'intake', 'facts': {'recipient_type': 'individual'}, 'reply': 'ok', 'query': ''}
    doc = send(chat, chat.store.create('owner'))
    assert doc['workflow']['status'] == 'unsupported'
    assert doc['questions'] == []
    doc = chat.confirm('owner', doc['id'], doc['revision'], str(uuid4()))
    with pytest.raises(WorkflowError, match='out_of_scope'):
        chat.run('owner', doc['id'], doc['revision'], str(uuid4()))


def test_noop_does_not_invalidate_and_real_change_does(chat):
    doc = chat.store.create('owner')
    doc = chat.edit('owner', doc['id'], 0, str(uuid4()), {'income_type': 'dividend'})
    doc = chat.confirm('owner', doc['id'], doc['revision'], str(uuid4()))
    confirmed = doc['confirmed_revision']
    doc = chat.edit('owner', doc['id'], doc['revision'], str(uuid4()), {'income_type': 'dividend'})
    assert doc['state'] == 'confirmed' and doc['confirmed_revision'] == confirmed
    chat.turner = lambda *_: {'intent': 'intake', 'facts': {'income_type': 'dividend'}, 'reply': 'ok', 'query': ''}
    doc = send(chat, doc)
    assert doc['confirmed_revision'] == confirmed
    doc = send(chat, doc, text='先看部分整理')
    doc = chat.run('owner', doc['id'], doc['revision'], str(uuid4()))
    assert doc['analyses'][-1]['review']['status'] == 'pending_final_review'
    doc = chat.edit('owner', doc['id'], doc['revision'], str(uuid4()), {'dividend_amount': 200})
    assert doc['analyses'][-1]['stale'] and doc['analyses'][-1]['review']['status'] == 'stale'


def test_no_match_is_a_business_reply_failure_is_atomic(chat):
    original = chat.store.create('owner')
    chat.provider = MockKnowledgeProvider('MOCK-02')
    doc = send(chat, original)
    assert doc['workflow']['reason_code'] == 'no_match'
    chat.provider = MockKnowledgeProvider('MOCK-04')
    with pytest.raises(WorkflowError, match='knowledge_unavailable'):
        send(chat, doc)
    assert chat.store.get('owner', doc['id'])['revision'] == doc['revision']


def test_forged_claim_and_citation_rejected():
    bundle = retrieve(MockKnowledgeProvider(), request(), CONTEXT)
    answer = compose_answer(bundle)
    answer['claims'][0]['evidence_ids'] = ['fake']
    with pytest.raises(ValueError): validate_answer(answer, bundle)
    answer = compose_answer(bundle)
    answer['claims'][0]['text'] = '税率0%，一定免税'
    with pytest.raises(ValueError): validate_answer(answer, bundle)


def test_final_review_authorization_snapshot_and_mock_block(chat, monkeypatch):
    doc = chat.store.create('owner')
    doc = chat.edit('owner', doc['id'], 0, str(uuid4()), {'income_type': 'dividend'})
    doc = chat.confirm('owner', doc['id'], doc['revision'], str(uuid4()))
    doc = send(chat, doc, text='先看部分整理')
    doc = chat.run('owner', doc['id'], doc['revision'], str(uuid4()))
    report = doc['analyses'][-1]
    args = ['owner', doc['id'], doc['revision'], str(uuid4()), report['id'], report['report_hash'], 'reviewer', 'approved', 'test']
    with pytest.raises(WorkflowError, match='review_forbidden'): chat.review(*args)
    monkeypatch.setenv('FSIE_AGENT_REVIEWER_IDS', '["reviewer"]')
    with pytest.raises(WorkflowError, match='review_incomplete'): chat.review(*args)
    args[-2] = 'changes_requested'
    updated = chat.review(*args)
    assert updated['analyses'][-1]['review']['history'][0]['reviewer'] == 'reviewer'
    assert chat.review(*args) == updated
    assert report['is_synthetic']
    changed = deepcopy(report)
    changed['nodes'][0]['output'] = 'changed'
    with pytest.raises(WorkflowError, match='review_snapshot_changed'):
        review_report(changed, report['report_hash'], 'reviewer', 'unable_to_conclude', 'test')


def test_final_review_approval_requires_complete_non_synthetic_snapshot():
    report = freeze({'id': 'internal-unit-test-only', 'is_synthetic': False, 'missing_nodes': [],
                     'blockers': [], 'missing_locators': [], 'evidence_gate': 'sufficient_for_task'})
    review_report(report, report['report_hash'], 'reviewer', 'approved', 'Reviewed frozen internal report')
    assert report['review']['status'] == 'approved'
    with pytest.raises(WorkflowError, match='review_already_decided'):
        review_report(report, report['report_hash'], 'reviewer', 'approved', 'again')
