"""Real pinned tax engine release through the chat DB and read-only C boundary."""
import json
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from apps.api.auth import optional_user
from apps.api.chat import get_service
from apps.api.main import app as chat_app
from apps.knowledge_api.main import app as library_app, _release
from packages.chat.service import ChatService
from packages.chat.store import ChatStore
from packages.domain_bridge.bridge import DomainError, PINNED_COMMIT, release_path

try:
    RELEASE = release_path()
except DomainError:
    RELEASE = Path(__file__).resolve().parents[2] / 'data/tax_engine/releases' / PINNED_COMMIT
HEADERS = {'X-AsiaTax-Request': '1'}
USER = {'id': '11111111-1111-1111-1111-111111111111', 'email': 'test@example.invalid'}


@pytest.fixture
def real_release(monkeypatch):
    if not (RELEASE / 'official/official.sqlite').is_file() or (RELEASE / 'official/official.sqlite').stat().st_size < 1_000_000:
        pytest.skip('Pinned tax engine LFS release not installed')
    monkeypatch.setenv('FSIE_TAX_ENGINE_RELEASE_DIR', str(RELEASE))
    _release.cache_clear()
    yield
    _release.cache_clear()


def _mutation(doc, **payload):
    return {'revision': doc['revision'], 'request_id': str(uuid4()), **payload}


def test_saved_case_planner_question_answer_and_conflict(real_release, tmp_path):
    store = ChatStore(f'sqlite:///{tmp_path}/cases.sqlite')
    service = ChatService(store)
    chat_app.dependency_overrides[optional_user] = lambda: USER
    chat_app.dependency_overrides[get_service] = lambda: service
    source = json.loads((RELEASE / 'tax_graph/examples/meridian.json').read_text(encoding='utf-8'))
    source['currency'] = 'CNY'
    source['notes'] = ['Synthetic CNY variant for engineering tests; not the original SGD case.']
    try:
        with TestClient(chat_app) as client:
            doc = client.post('/api/cases', headers=HEADERS).json()
            path = f"/api/cases/{doc['id']}"
            refused = client.put(path + '/domain-case', headers=HEADERS,
                                 json=_mutation(doc, case_input=source)).json()
            assert refused['detail'] == 'data_confirmation_required'
            setup_body = _mutation(doc, case_input=source, data_approved=True)
            first = client.put(path + '/domain-case', headers=HEADERS, json=setup_body)
            assert first.status_code == 200
            doc = first.json()
            assert client.put(path + '/domain-case', headers=HEADERS, json=setup_body).json() == doc
            with patch('packages.domain_bridge.coordinator.run_plan', side_effect=DomainError('domain_execution_failed')):
                failed = client.post(path + '/domain-plan', headers=HEADERS, json=_mutation(doc))
            assert failed.status_code == 503
            assert client.get(path).json()['revision'] == doc['revision']
            planned = client.post(path + '/domain-plan', headers=HEADERS, json=_mutation(doc))
            assert planned.status_code == 200
            doc = planned.json()
            assert doc['domain_outcome']['status'] == 'needs_input'
            assert doc['domain_outcome']['release'].startswith('771e452')
            assert doc['domain_outcome']['input_hash']
            question = doc['domain_outcome']['questions'][0]
            assert question['kind'] in ('data', 'blocking', 'joint')
            original_revision = doc['revision']
            answer = client.post(path + '/domain-answer', headers=HEADERS,
                                 json=_mutation(doc, key=question['key'], kind=question['kind'], value='900000000'))
            assert answer.status_code == 200
            updated = answer.json()
            assert updated['revision'] == original_revision + 1
            assert updated['domain_answers']['data'][question['key']]['value'] == 900000000.0
            assert client.get(path).json()['domain_answers'] == updated['domain_answers']
            stale = client.post(path + '/domain-plan', headers=HEADERS, json=_mutation(doc))
            assert stale.status_code == 409
            denied = client.post(path + '/domain-answer', headers=HEADERS,
                                 json=_mutation(updated, key='fake.ruling', kind='ruling', value='yes'))
            assert denied.status_code == 422
            assert client.get(path).json()['revision'] == updated['revision']
            edited = client.patch(path + '/facts', headers=HEADERS,
                                  json=_mutation(updated, facts={'income_type': 'dividend'})).json()
            assert edited['domain_outcome']['stale'] is True
            assert edited['canonical_fact_records']['legacy.income_type']['value'] == 'dividend'
            assert client.post(path + '/domain-answer', headers=HEADERS,
                               json=_mutation(edited, key=question['key'], kind=question['kind'],
                                              value='900000000')).status_code == 409
            malformed = json.loads(json.dumps(source))
            malformed['event']['years'] = 500
            assert client.put(path + '/domain-case', headers=HEADERS,
                              json=_mutation(edited, case_input=malformed, data_approved=True)).status_code == 422
            assert client.get(path).json()['revision'] == edited['revision']
    finally:
        chat_app.dependency_overrides.clear()
        store.engine.dispose()


def test_official_search_and_exact_replay(real_release):
    with TestClient(library_app) as client:
        assert client.get('/health').json()['knowledge_ready']
        response = client.post('/search', json={'request': {
            'request_id': 'r1', 'trace_id': 't1', 'query': 'hk.cap112.en#s15H'},
            'trusted_context': {'owner': 'user:test'}})
        assert response.status_code == 200
        result = response.json()
        assert result['provider'] == 'c' and result['status'] == 'ok'
        hit = result['evidence'][0]
        assert hit['model_use'] == 'allowed' and hit['display_use'] == 'allowed'
        assert hit['policy_version'] == 'public-hk-official-v1'
        ref = {key: hit[key] for key in ('evidence_id', 'source_version_id', 'unit_id')}
        replay = client.post('/evidence', json={'reference': ref, 'purpose': 'display',
                                                'trusted_context': {'owner': 'user:test'}}).json()
        from hashlib import sha256
        assert replay['status'] == 'ok'
        assert sha256(replay['text'].encode()).hexdigest() == hit['content_hash']
        restricted = client.post('/evidence', json={'reference': ref, 'purpose': 'model',
                                                    'trusted_context': {'owner': 'user:test'}}).json()
        assert restricted['status'] == 'ok'
        assert restricted['content_hash'] == hit['content_hash']


@pytest.mark.parametrize(('query', 'expected'), [
    ('请查第15K条和第15M条', {'s.15K(1)', 's.15M(1)'}),
    ('纯股权持有实体经济实质要求和外包条件', {'s.15K(2)', 's.15K(3)'}),
])
def test_official_search_navigates_sections_and_chinese_topics(real_release, query, expected):
    with TestClient(library_app) as client:
        response = client.post('/search', json={'request': {
            'request_id': 'navigation', 'trace_id': 'navigation', 'query': query},
            'trusted_context': {'owner': 'user:test'}})
        assert response.status_code == 200
        result = response.json()
        assert result['status'] == 'ok'
        locators = {span['locator'] for hit in result['evidence'] for span in hit['locator_spans']}
        assert expected <= locators


def test_existing_b_retriever_gets_bounded_partial_coverage(real_release):
    from packages.agent.budget import BudgetedProvider, RunBudget
    from packages.agent.contracts import SearchRequest, TrustedContext
    from packages.agent.knowledge import retrieve
    from packages.agent.providers import CKnowledgeProvider
    from packages.chat.analysis import NODE_LOCATORS

    locators = sorted({locator for group in NODE_LOCATORS.values() for locator in group})
    with TestClient(library_app) as library:
        def dispatch(request):
            response = library.request(request.method, request.url.path, content=request.content,
                                       headers=dict(request.headers))
            return httpx.Response(response.status_code, content=response.content,
                                  headers=dict(response.headers))

        provider = CKnowledgeProvider('http://127.0.0.1:8010', transport=httpx.MockTransport(dispatch))
        budget = RunBudget()
        result = retrieve(BudgetedProvider(provider, budget), SearchRequest(
            request_id='bounded', trace_id='bounded', query='香港境外股息 FSIE 适用规则',
            intent='case_analysis', locators=locators), TrustedContext(owner='user:test'))
        assert result['status'] == 'available'
        assert result['reason_code'] == 'evidence_available'
        assert result['model_evidence']
        assert not result['coverage']['truncated']
        assert {p['locator'] for p in result['passages']} == set(locators)
        assert budget.counts['evidence'] == 7
        assert not any(gap.startswith('未定位条款：') for gap in result['gaps'])


def test_b_analysis_reads_law_knowledge_without_approving_gaps(real_release):
    from packages.agent.budget import BudgetedProvider, RunBudget
    from packages.agent.contracts import TrustedContext
    from packages.agent.providers import CKnowledgeProvider
    from packages.chat.analysis import analyze

    with TestClient(library_app) as library:
        def dispatch(request):
            response = library.request(request.method, request.url.path, content=request.content,
                                       headers=dict(request.headers))
            return httpx.Response(response.status_code, content=response.content,
                                  headers=dict(response.headers))

        provider = CKnowledgeProvider('http://127.0.0.1:8010', transport=httpx.MockTransport(dispatch))
        budget = RunBudget()
        report = analyze('test-case', {'income_type': 'dividend'}, 1,
                         provider=BudgetedProvider(provider, budget),
                         context=TrustedContext(owner='user:test'))
        assert report['retrieval_status'] == 'available'
        assert report['evidence_gate'] == 'insufficient'
        assert report['passages'] and not report['missing_locators']
        assert report['related_rulings']['status'] == 'no_matching_units'
        assert budget.counts['search'] == 2 and budget.counts['evidence'] <= 14


def test_combined_current_report_resolves_rule_ids_to_legal_text(real_release, tmp_path):
    from packages.agent.providers import CKnowledgeProvider, RoutedKnowledgeProvider, LegacyKnowledgeProvider
    from packages.agent.review import report_hash
    source = json.loads((Path(__file__).parent / 'fixtures/holding.synthetic.json').read_text(encoding='utf-8'))
    store = ChatStore(f'sqlite:///{tmp_path}/combined-report.sqlite')
    with TestClient(library_app) as library:
        def dispatch(request):
            response = library.request(request.method, request.url.path, content=request.content,
                                       headers=dict(request.headers))
            return httpx.Response(response.status_code, content=response.content)
        provider = RoutedKnowledgeProvider(CKnowledgeProvider('http://127.0.0.1:8010', transport=httpx.MockTransport(dispatch)),
                     LegacyKnowledgeProvider(lambda _: {'status': 'no_matching_units', 'passages': []}))
        service = ChatService(store, provider=provider); owner = 'user:report'
        try:
            doc = store.create(owner)
            doc = service.edit(owner, doc['id'], 0, str(uuid4()), {'dividend_amount': 1000000, 'income_type': 'dividend'})
            doc = service.domain_setup(owner, doc['id'], doc['revision'], str(uuid4()), source, True,
                                       'assess_current', {'dividend_amount': 'event.dividend'})
            doc = service.domain_plan(owner, doc['id'], doc['revision'], str(uuid4()))
            assert all('#' in ref for ref in doc['domain_outcome']['citations'])
            assert doc['domain_outcome']['citation_map']['hk.fsie.charge']
            doc = service.domain_confirm(owner, doc['id'], doc['revision'], str(uuid4()))
            doc = service.domain_report(owner, doc['id'], doc['revision'], str(uuid4()), True)
            report = doc['analyses'][-1]
            assert report_hash(report) == report['report_hash']
            assert len({p['locator'] for p in report['fsie_assessment']['passages']}) == 21
            assert not report['missing_locators']
            assert set(report['domain_citation_coverage']['read']) == set(report['outcome']['citations'])
            assert {'cn.sta.2018-09#i2', 'treaty.cn-hk.2006.zh#10.2'} <= set(report['domain_citation_coverage']['read'])
            # Non-HK references are display evidence; resolving them must not
            # silently expand the provider's permission to send text to a model.
            cross_border = [p for p in report['passages'] if p['locator'] in
                            ('cn.sta.2018-09#i2', 'treaty.cn-hk.2006.zh#10.2')]
            assert len(cross_border) == 2
            assert all(p['model_use'] == 'denied' and p['text_sha256'] for p in cross_border)
            assert report['budget']['evidence'] <= 35 and report['budget']['search'] <= 10
            assert report['evidence_gate'] == 'insufficient' and report['is_synthetic']
        finally:
            store.engine.dispose()


@pytest.mark.parametrize('include_known', [False, True])
def test_exact_missing_reference_does_not_substitute_keyword_hits(real_release, include_known):
    missing = 'hk.cap112.en#nonexistent-review-clause'
    requested = [missing] + (['hk.cap112.en#s15H'] if include_known else [])
    with TestClient(library_app) as client:
        response = client.post('/search', json={'request': {
            'request_id': 'exact-missing', 'trace_id': 'exact-missing',
            'query': 'hk.cap112.en#s15H', 'kind': 'all', 'locators': requested},
            'trusted_context': {'owner': 'user:test'}})
    assert response.status_code == 200
    result = response.json()
    assert result['status'] == ('partial' if include_known else 'no_match')
    assert result['coverage']['missing_requirements'] == ['未定位条款：' + missing]
    locators = {span['locator'] for hit in result['evidence'] for span in hit['locator_spans']}
    assert locators == ({'hk.cap112.en#s15H'} if include_known else set())
    if not include_known:
        assert not result['evidence']
