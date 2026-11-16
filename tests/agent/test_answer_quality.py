"""Regression cases taken from the real webpage evaluation, with offline models."""
from copy import deepcopy
from uuid import uuid4

import pytest

from packages.agent.fact_context import guard_extraction
from packages.agent.grounded import claims_from_result, evidence_spans
from packages.agent.grounded import validate_case_claims
from packages.agent.knowledge import merge_bundles, validate_answer
from packages.agent.providers import MockKnowledgeProvider
from packages.chat.language import reply_language, english_text
from packages.chat.service import ChatService
from packages.chat.store import ChatStore


@pytest.mark.parametrize('text,previous,interface,expected', [
    ('What is Hong Kong FSIE?', None, 'zh', 'en'),
    ('Please explain 香港 FSIE rules.', None, 'zh', 'en'),
    ('请说明香港FSIE。', None, 'en', 'en'),
    ('请用英语说明香港FSIE。', None, 'zh', 'en'),
    ('Please explain FSIE. Reply in Chinese.', None, 'en', 'zh'),
    ('3%', 'en', 'zh', 'en'),
    ('OK', 'zh', 'en', 'en'),
    ('Why?', 'zh', 'zh', 'en'),
    ('How so?', 'zh', 'zh', 'en'),
])
def test_answer_language_honors_explicit_directive_then_english_ui(text, previous, interface, expected):
    assert reply_language({'reply_locale': previous}, text, interface) == expected


def test_months_are_not_fabricated_days_and_have_provenance():
    patch, context = guard_extraction({'receipt_date': '2025-08-01', 'acquisition_date': '2022-03-01',
        'pure_equity_holding_entity_status': 'general_entity'},
        'We acquired the shares in March 2022. The dividend was paid in August 2025. We have three employees.')
    assert 'receipt_date' not in patch and 'acquisition_date' not in patch
    assert 'pure_equity_holding_entity_status' not in patch
    assert context['partial_dates']['receipt_date'] == {
        'year': 2025, 'month': 8, 'precision': 'month', 'source_quote': 'August 2025'}
    corrected, context = guard_extraction({'receipt_date': '2025-08-17'}, 'It was received on 17 August 2025.', context)
    assert corrected['receipt_date'] == '2025-08-17'
    assert 'receipt_date' not in context['partial_dates']


def test_explicit_receipt_does_not_repeat_stage_question_but_hypothetical_does_not_set_it():
    patch, _ = guard_extraction({'income_type': 'dividend'}, '我们是一家香港公司，收到内地公司的股息100万。')
    assert patch['income_event_status'] == 'occurred'
    patch, _ = guard_extraction({'income_type': 'dividend'}, '如果我们收到内地公司的股息，应该如何处理？')
    assert 'income_event_status' not in patch


def test_two_payments_cannot_be_flattened_into_one_dividend():
    patch, context = guard_extraction({'payer_jurisdiction': 'Singapore', 'holding_percentage_pct': 22,
        'direct_or_indirect_holding': 'indirect', 'income_type': 'dividend'},
        'First distinguish the two steps: a Japanese company may pay a dividend to Singapore; '
        'Singapore may separately pay a dividend to Hong Kong. Hong Kong owns 100% of Singapore, which owns 22% of Japan.')
    assert not {'holding_percentage_pct', 'payer_jurisdiction', 'direct_or_indirect_holding'} & patch.keys()
    assert patch['income_type'] == 'dividend'
    assert context['transaction_scope']['status'] == 'multiple_unbound'


def test_entity_classification_guard_accepts_conditions_but_rejects_findings():
    validate_case_claims([{'text': 'If your company is a pure equity holding entity, different requirements apply.'}], {}, '')
    validate_case_claims([{'text': '需要核实你们公司是否是纯股权持有实体。若你的公司是纯股权持有实体，需核对相关条件。'}], {}, '')
    with pytest.raises(ValueError, match='unconfirmed_entity_classification'):
        validate_case_claims([{'text': 'Your company is a pure equity holding entity.'}], {}, '')


def test_action_plan_retrieval_covers_both_exception_routes():
    from packages.chat.knowledge import topic_locators
    refs = topic_locators('我想合法降低香港公司境外股息的税负，给可执行的方案和需要准备的材料清单。')
    assert {'s.15K(2)', 's.15M(2)', 's.15N(2)'} <= set(refs)


def test_shortened_tool_query_keeps_document_checklist_navigation(production_chat, monkeypatch):
    chat, _ = production_chat
    requests = []
    original = chat.provider.search_evidence
    def search(request, context):
        requests.append(request)
        return original(request, context)
    monkeypatch.setattr(chat.provider, 'search_evidence', search)
    choices = iter([{'tool': 'search_law', 'query': '香港境外股息 FSIE'}, {'tool': 'finish', 'query': ''}])
    chat.tool_planner = lambda *_: next(choices)
    doc = chat.store.create('test')
    chat.message('test', doc['id'], 0, str(uuid4()), '香港公司境外股息需要准备哪些材料清单？', True)
    assert requests and 's.15K(2)' in requests[0].locators and 's.15M(2)' in requests[0].locators


def test_reading_facts_alone_cannot_finish_a_source_lookup(production_chat):
    chat, seen = production_chat
    choices = iter([{'tool': 'read_case_facts', 'query': ''}, {'tool': 'finish', 'query': ''},
                    {'tool': 'finish', 'query': ''}])
    chat.tool_planner = lambda *_: next(choices)
    doc = chat.store.create('test')
    result = chat.message('test', doc['id'], 0, str(uuid4()), '香港境外股息的材料清单有哪些？', True)
    assert any(c['tool'] == 'search_law' for c in result['workflow']['tool_calls'])
    assert len(seen) == 1 and result['messages'][-1]['answer']['composition'] == 'grounded'
    assert any(e['name'] == 'tool.overridden' and e['data']['proposed_tool'] == 'finish'
               for e in chat._trace_events)


@pytest.fixture
def production_chat(tmp_path, monkeypatch):
    from packages.chat import service
    from packages.agent import grounded
    from packages.model_adapter.client import OpenAICompatibleClient, ModelConfig
    provider = MockKnowledgeProvider()
    provider.fixture = deepcopy(provider.fixture)
    provider.fixture['search_response']['is_synthetic'] = False
    provider.fixture['search_response']['provider'] = 'legacy'
    for item in provider.fixture['search_response']['evidence']:
        item['is_synthetic'] = False
    store = ChatStore(f'sqlite:///{tmp_path}/quality.sqlite')
    chat = ChatService(store, provider=provider, orchestration='hybrid', dynamic_planner=True, harness_mode='tools')
    from packages.agent import logs
    chat._trace_events = []
    monkeypatch.setattr(logs, 'append', lambda kind, record: chat._trace_events.append(record) if kind == 'events' else None)
    monkeypatch.setattr(service, 'current_model_config', lambda: ModelConfig('https://model.test', 'fixture', 'fixture', 45, 0))
    seen = []
    def route(_client, _system, _user, **_kwargs):
        return {'intent': 'research', 'facts': {}, 'reply': 'Checking the official sources.',
                'query': '香港境外股息 FSIE', 'uses_case': False, 'task_kind': 'reference_lookup'}
    monkeypatch.setattr(OpenAICompatibleClient, 'chat_json', route)
    def respond(payload):
        seen.append(payload)
        source = payload['sources'][0]
        return {'paragraphs': [{'text': 'This is the single source-supported answer.',
            'evidence': [{'evidence_id': source['evidence_id'], 'quote': source['text'][:30]}]}], 'missing_info': []}
    monkeypatch.setattr(grounded, 'respond', respond)
    yield chat, seen
    store.engine.dispose()


def test_multiple_tools_compose_once_in_english_in_chinese_interface(production_chat):
    chat, seen = production_chat
    choices = iter([{'tool': 'search_law', 'query': '香港境外股息 FSIE'},
                    {'tool': 'search_guidance', 'query': '香港境外股息 FSIE'}, {'tool': 'finish', 'query': ''}])
    chat.tool_planner = lambda *_: next(choices)
    doc = chat.store.create('test')
    result = chat.message('test', doc['id'], 0, str(uuid4()), 'Please explain Hong Kong FSIE and cite the official sources.', True, locale='zh')
    assert len(seen) == 1
    assert len(seen[0]['sources']) == 1  # Both tools retrieved the same source.
    assert seen[0]['locale'] == 'en'
    answer = result['messages'][-1]
    assert answer['reply_locale'] == 'en' and english_text(answer['text'])
    assert answer['text'].count('single source-supported answer') == 1
    assert 'References:' not in answer['text']
    assert answer['text'].endswith('Official source 1')  # This fixture has no URL.
    assert result['workflow']['answer_compositions'] == 1


def test_clear_three_percent_correction_updates_current_value_without_router_annotation(tmp_path):
    store = ChatStore(f'sqlite:///{tmp_path}/correction.sqlite')
    try:
        chat = ChatService(store, provider=MockKnowledgeProvider(), orchestration='hybrid', dynamic_planner=False,
            turner=lambda *_: {'intent': 'intake', 'reply': '已收到', 'facts': {'holding_percentage_pct': 3}, 'query': ''})
        doc = store.create('test')
        doc = chat.edit('test', doc['id'], 0, str(uuid4()), {'holding_percentage_pct': 20})
        result = chat.message('test', doc['id'], doc['revision'], str(uuid4()), '刚才说错了，我们只持有3%，不是20%，其他信息不变。', True)
        assert result['facts']['holding_percentage_pct']['value'] == 3
        assert 'holding_percentage_pct' not in result.get('fact_conflicts', {})
    finally:
        store.engine.dispose()


def test_whitespace_only_quote_is_mapped_to_exact_original_but_changed_number_fails():
    evidence = [{'evidence_id': 's', 'text': 'The entity\t must hold\n5% continuously.'}]
    output = {'paragraphs': [{'text': 'The requirement is conditional.', 'evidence': [
        {'evidence_id': 's', 'quote': 'entity must hold 5% continuously.'}]}], 'missing_info': []}
    claims, _ = claims_from_result(output, evidence)
    assert claims[0]['supports'][0]['quote'] in evidence[0]['text']
    output['paragraphs'][0]['evidence'][0]['quote'] = 'entity must hold 3% continuously.'
    with pytest.raises(ValueError, match='unsupported_citation'):
        claims_from_result(output, evidence)


def test_search_scope_repair_keeps_original_query_and_never_runs_rejected_proposal(production_chat):
    chat, seen = production_chat
    choices = iter([{'tool': 'search_law', 'query': '香港境外股息 FSIE s.15M'}, {'tool': 'finish', 'query': ''}])
    chat.tool_planner = lambda *_: next(choices)
    doc = chat.store.create('test')
    result = chat.message('test', doc['id'], 0, str(uuid4()), 'Please explain Hong Kong FSIE.', True)
    calls = result['workflow']['tool_calls']
    assert calls[0]['status'] == 'rejected' and calls[0]['repair'] == 'original_scoped_query'
    assert calls[1]['query'] == '香港境外股息 FSIE'
    assert len(seen) == 1
    events = chat._trace_events
    assert any(e['name'] == 'tool.guard' and e['status'] == 'rejected' for e in events)
    assert any(e['name'] == 'tool.repaired' and e['data']['query'] == '香港境外股息 FSIE' for e in events)


def test_model_selects_original_span_without_retyping_or_changing_the_law():
    text = 'The participation requirement is a continuous holding.\n' * 40
    evidence = [{'evidence_id': 'law', 'text': text}]
    spans = evidence_spans(text)
    assert len(spans) > 1 and all(s['text'] in text for s in spans)
    draft = {'paragraphs': [{'text': 'The rule requires continuous holding.',
        'evidence': [{'evidence_id': 'law', 'span_id': spans[1]['span_id']}]}], 'missing_info': []}
    claims, _ = claims_from_result(draft, evidence)
    assert claims[0]['supports'][0] == {'evidence_id': 'law', 'quote': spans[1]['text']}
    draft['paragraphs'][0]['evidence'][0]['span_id'] = 'P999'
    with pytest.raises(ValueError, match='unsupported_citation'):
        claims_from_result(draft, evidence)


def test_multicondition_list_is_not_discarded_for_having_five_valid_supports():
    evidence = [{'evidence_id': str(i), 'text': 'An original source passage for checking.'} for i in range(5)]
    text = '**Conditions**\n\n' + '\n'.join('- A source-bound condition requiring verification.' * 7 for _ in range(5))
    assert 1500 < len(text) < 3000
    draft = {'paragraphs': [{'text': text, 'evidence': [
        {'evidence_id': item['evidence_id'], 'span_id': 'P1'} for item in evidence]}], 'missing_info': []}
    claims, _ = claims_from_result(draft, evidence, 'en')
    assert len(claims[0]['supports']) == 5


def test_failed_optional_quality_review_preserves_already_verified_answer(production_chat):
    chat, _ = production_chat
    calls = []
    def respond(payload):
        calls.append(payload)
        if len(calls) == 2:
            raise ValueError('unsupported_citation')
        source = payload['sources'][0]
        return {'paragraphs': [{'text': 'Credit conditions must be checked separately.',
                'evidence': [{'evidence_id': source['evidence_id'], 'quote': source['text'][:30]}]}], 'missing_info': []}
    # Use the public composer directly with the same admitted production bundle.
    from packages.agent.knowledge import compose_answer
    from packages.agent.knowledge import retrieve
    from packages.agent.contracts import TrustedContext, SearchRequest
    bundle = retrieve(chat.provider, SearchRequest(query='香港境外股息 FSIE', request_id=str(uuid4()), trace_id=str(uuid4())),
                      context=TrustedContext(owner='test', case_id='test'))
    answer = compose_answer(bundle, 'en', 'Is a foreign tax credit available?', responder=respond)
    assert len(calls) == 2
    assert answer['composition'] == 'grounded'
    assert answer['quality_review_error'] == 'unsupported_citation'
    validate_answer(answer, bundle)
    def checklist(payload):
        source = payload['sources'][0]
        return {'paragraphs': [{'text': '**Documents to request**\n\n- Obtain the tax record.',
            'evidence': [{'evidence_id': source['evidence_id'], 'quote': source['text'][:30]}]}],
            'missing_info': ['Obtain the tax record.']}
    bundle['query_context'] = {'uses_case': True}
    answer = compose_answer(bundle, 'en', 'Which records should I request?', responder=checklist)
    assert answer['text'].count('Obtain the tax record.') == 1
    assert answer['missing_info'] == ['Obtain the tax record.']


def test_guard_runs_on_production_route_and_persists_partial_date_without_day(production_chat, monkeypatch):
    chat, _ = production_chat
    from packages.model_adapter.client import OpenAICompatibleClient
    monkeypatch.setattr(OpenAICompatibleClient, 'chat_json', lambda *_a, **_kw: {
        'intent': 'intake', 'reply': 'Recorded.', 'query': '', 'facts': {
            'recipient_type': 'company', 'receipt_date': '2025-08-01', 'acquisition_date': '2022-03-01'}})
    doc = chat.store.create('test')
    result = chat.message('test', doc['id'], 0, str(uuid4()),
        'We are a company. The shares were acquired in March 2022. The dividend was received in August 2025.', True)
    assert 'receipt_date' not in result['facts'] and 'acquisition_date' not in result['facts']
    assert result['fact_context']['partial_dates']['receipt_date']['precision'] == 'month'
    assert chat.store.get('test', doc['id'])['fact_context'] == result['fact_context']


def test_translating_chinese_statements_never_mutates_saved_facts(monkeypatch):
    from packages.chat.language import english_case_view
    from packages.chat import service
    from packages.model_adapter.client import ModelConfig, OpenAICompatibleClient
    doc = {'facts': {'entity_activity_profile': {'value': '在香港管理投资，有3名员工'}}}
    original = deepcopy(doc)
    monkeypatch.setattr(service, 'current_model_config', lambda: ModelConfig('https://model.test', 'fixture', 'fixture'))
    monkeypatch.setattr(OpenAICompatibleClient, 'chat_json', lambda *_a, **_kw: {
        'entity_activity_profile': 'Investment management in Hong Kong with 3 employees.'})
    shown = english_case_view(doc)
    assert english_text(shown['facts']['entity_activity_profile']['value'])
    assert '3 employees' in shown['facts']['entity_activity_profile']['value']
    assert doc == original


def test_case_gaps_do_not_stop_requested_law_and_guidance(production_chat, monkeypatch):
    chat, seen = production_chat
    from packages.agent.tool_harness import ToolHarness
    from unittest.mock import patch
    calls = []
    original = chat.provider.search_evidence
    def search(request, context):
        calls.append(request.kind)
        return original(request, context)
    chat.provider.search_evidence = search
    # Real routing contract, scripted model: current case facts stay linked.
    from packages.model_adapter.client import OpenAICompatibleClient
    monkeypatch.setattr(OpenAICompatibleClient, 'chat_json', lambda *_a, **_k: {
        'intent': 'research', 'facts': {}, 'reply': 'Checking sources.',
        'query': '香港境外股息 FSIE', 'uses_case': True, 'task_kind': 'reference_lookup'})
    # The first finish must be redirected to the still-requested source type.
    choices = iter([{'tool': 'search_law', 'query': '香港境外股息 FSIE'}, {'tool': 'finish'}, {'tool': 'finish'}])
    chat.tool_planner = lambda *_: next(choices)
    doc = chat.store.create('test')
    doc = chat.edit('test', doc['id'], 0, str(uuid4()), {
        'recipient_type': 'company', 'income_type': 'dividend', 'analysis_jurisdiction': 'HK',
        'consultation_goal': 'full_analysis'})
    observations = []
    original_observation = ToolHarness.observation
    def observe(self, state):
        view = original_observation(self, state)
        observations.append(deepcopy(view))
        return view
    with patch.object(ToolHarness, 'observation', observe):
        result = chat.message('test', doc['id'], doc['revision'], str(uuid4()),
            'Explain the Hong Kong FSIE participation requirements using legislation and IRD guidance.', True)
    assert calls == ['law', 'guidance']
    assert result['workflow']['harness_stop'] == 'finished'
    assert len(seen) == 1
    coverage = next(e['data'] for e in chat._trace_events if e['name'] == 'research.coverage')
    assert coverage['professional_validation'] == 'pending_review'
    assert observations[0]['case_state']['nonblocking_fact_gaps']
    assert 'hk_staff_description' in observations[0]['case_state']['deferred_fact_fields']
    assert observations[-1]['observations'][0]['coverage_basis'] == 'versioned_locator_navigation_only'
    assert not result['analyses'] and result['confirmed_facts'] is None
    assert not any(e['name'] == 'answer.result' and e['data']['composition'] == 'extractive' for e in chat._trace_events)


def test_mixed_case_request_researches_before_asking_unknown_business_status(production_chat, monkeypatch):
    chat, seen = production_chat
    from packages.model_adapter.client import OpenAICompatibleClient
    monkeypatch.setattr(OpenAICompatibleClient, 'chat_json', lambda *_args, **_kwargs: {'intent': 'intake', 'facts': {
        'recipient_type': 'company', 'income_type': 'dividend', 'analysis_jurisdiction': 'HK',
        'holding_percentage_pct': 8}, 'reply': 'Recorded.', 'query': '', 'uses_case': True})
    choices = iter([{'tool': 'search_law', 'query': '香港境外股息 FSIE'}, {'tool': 'finish'}])
    chat.tool_planner = lambda *_: next(choices)
    doc = chat.store.create('test')
    result = chat.message('test', doc['id'], 0, str(uuid4()),
        'Our Hong Kong company holds 8% of a Mainland company. I want to understand how the holding period affects this dividend.', True)
    assert seen and result['messages'][-1]['answer']['composition'] == 'grounded'
    assert result['facts']['holding_percentage_pct']['value'] == 8
    assert 'entity_hk_business_status' not in result['facts']
    assert 'single source-supported answer' in result['messages'][-1]['text']
    assert any(e['name'] == 'route.repaired' for e in chat._trace_events)
    assert not result['analyses'] and result['confirmed_revision'] is None


def test_partial_source_budget_preserves_verified_evidence_and_reports_stop(production_chat, monkeypatch):
    from packages.agent.budget import BudgetExceeded
    chat, seen = production_chat
    original = chat.provider.search_evidence
    def search(request, context):
        result = original(request, context)
        second = result.evidence[0].model_copy(update={'evidence_id': 'second', 'unit_id': 'second',
            'display_ref': result.evidence[0].display_ref.model_copy(update={'evidence_id': 'second', 'unit_id': 'second'})})
        return result.model_copy(update={'evidence': result.evidence + [second]})
    read = chat.provider.get_evidence
    def get(ref, purpose, context):
        if ref.evidence_id == 'second':
            raise BudgetExceeded('evidence')
        return read(ref, purpose, context)
    monkeypatch.setattr(chat.provider, 'search_evidence', search)
    monkeypatch.setattr(chat.provider, 'get_evidence', get)
    chat.tool_planner = lambda *_: {'tool': 'search_law', 'query': '香港境外股息 FSIE'}
    doc = chat.store.create('test')
    result = chat.message('test', doc['id'], 0, str(uuid4()), 'Please explain Hong Kong FSIE.', True)
    message = result['messages'][-1]
    assert seen and message['research']['passages']
    assert result['workflow']['harness_stop'] == result['workflow']['reason_code'] == 'budget_exhausted'
    assert 'could not be completed' in message['text']
    finishes = [e for e in chat._trace_events if e['name'] == 'tool.finish']
    assert finishes[-1]['data']['reason_code'] == 'budget_exhausted'
    assert not any(e['name'] == 'tool.loop_finished' and e['data']['stop_reason'] == 'finished' for e in chat._trace_events)


def test_inline_citation_uses_verified_subsection_and_keeps_each_claim_mapping():
    from packages.agent.knowledge import compose_answer
    text = 'Verified requirement in subsection one.\nVerified requirement in subsection two.'
    bundle = {'query': 'law', 'reason_code': 'evidence_available', 'gaps': [], 'is_synthetic': False,
        'passages': [{'evidence_id': 'law-1', 'locator': 's.15K(1)', 'text': text.splitlines()[0],
                      'url': 'https://www.elegislation.gov.hk/hk/cap112', 'title': 'IRO'},
                     {'evidence_id': 'law-2', 'locator': 's.15K(2)', 'text': text.splitlines()[1],
                      'url': 'https://www.elegislation.gov.hk/hk/cap112', 'title': 'IRO'}],
        'model_evidence': [{'evidence_id': 'law-1', 'locator': 's.15K(1)', 'text': text.splitlines()[0], 'title': 'IRO'},
                           {'evidence_id': 'law-2', 'locator': 's.15K(2)', 'text': text.splitlines()[1], 'title': 'IRO'}]}
    def respond(_):
        return {'paragraphs': [{'text': 'Check the first requirement.', 'evidence': [
            {'evidence_id': 'law-1', 'quote': text.splitlines()[0]}]},
            {'text': 'Check the second requirement.', 'evidence': [
            {'evidence_id': 'law-2', 'quote': text.splitlines()[1]}]}], 'missing_info': []}
    answer = compose_answer(bundle, 'en', 'Explain these requirements.', responder=respond)
    assert 'Check the first requirement. [s.15K(1)](https://' in answer['text']
    assert 'Check the second requirement. [s.15K(2)](https://' in answer['text']
    assert 'References:' not in answer['text']
    validate_answer(answer, bundle)


@pytest.mark.parametrize('text,question,error', [
    ('The expected 2027 payment month is unconfirmed.', 'The Japanese company expects to pay in 2027.', 'unconfirmed_date_precision'),
    ('No resolution has been made, so nothing has accrued.', 'We are planning a dividend.', 'unconfirmed_accrual'),
    ('The holding period is roughly eight months.', 'Shares acquired in May 2025, declared January 2026.', 'unconfirmed_holding_duration'),
])
def test_case_date_review_rejects_observed_live_precision_and_accrual_errors(text, question, error):
    with pytest.raises(ValueError, match=error):
        validate_case_claims([{'text': text}], {}, question)
    validate_case_claims([{'text': 'The expected year is 2027. The dividend is planned; the legal accrual date is unconfirmed.'}], {}, question)


def test_valid_extra_followups_are_prioritized_without_losing_the_answer(production_chat):
    from packages.agent.knowledge import retrieve, compose_answer
    from packages.agent.contracts import SearchRequest, TrustedContext
    chat, _ = production_chat
    bundle = retrieve(chat.provider, SearchRequest(query='香港境外股息', request_id=str(uuid4()), trace_id=str(uuid4())),
                      context=TrustedContext(owner='test', case_id='test'))
    bundle['query_context'] = {'uses_case': True}
    def respond(payload):
        source = payload['sources'][0]
        return {'paragraphs': [{'text': 'A supported explanation.',
                'evidence': [{'evidence_id': source['evidence_id'], 'quote': source['text'][:30]}]}],
                'missing_info': ['Question ' + str(i) for i in range(5)]}
    answer = compose_answer(bundle, 'en', 'What facts are missing?', responder=respond)
    assert answer['composition'] == 'grounded'
    assert len(answer['missing_info']) == 5
    assert 'Question 2' in answer['text'] and 'Question 3' not in answer['text']
    assert '2 further conditions remain unverified' in answer['text']
    validate_answer(answer, bundle)
