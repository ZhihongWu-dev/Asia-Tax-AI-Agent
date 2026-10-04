import asyncio
import json
import httpx
import pytest
from packages.chat import answers
from packages.chat.service import validate_turn, research_query


def test_empty_intake_can_start_clarification_but_invalid_facts_are_not_dropped():
    result = validate_turn({'intent': 'intake', 'reply': 'Summary', 'facts': {}, 'query': ''})
    # B supports an intake request before the user has supplied any facts.
    assert result['intent'] == 'intake' and result['facts'] == {}
    with pytest.raises(ValueError):
        validate_turn({'intent': 'intake', 'reply': 'Approved', 'facts': {'expert_decision_status': 'approved'}, 'query': ''})


def test_receipt_date_is_not_inferred_as_accrual_date():
    def turn():
        return {'intent': 'intake', 'reply': 'Recorded', 'facts': {'receipt_date': '2025-06-30', 'accrual_date': '2025-06-30'}, 'query': ''}
    result = validate_turn(turn(), '股息在2025年6月30日汇入香港账户。')
    assert result['facts'] == {'receipt_date': '2025-06-30'}
    assert 'accrual_date' in validate_turn(turn(), '股息累算和汇入日期都是2025年6月30日。')['facts']


def test_citation_and_quote_validation():
    units = {'test:1': {'unit_id': 'test:1', 'text': 'This is synthetic supporting evidence.', 'locator': 's.15K(2)', 'url': 'https://www.ird.gov.hk/'}}
    result = {'paragraphs': [{'text': 'A supported summary.', 'evidence': [{'unit_id': 'test:1', 'quote': 'synthetic supporting evidence'}]}], 'missing_info': []}
    text, citations, _ = answers.validate_answer(result, units)
    assert '[s.15K(2)](https://www.ird.gov.hk/)' in text
    assert citations[0]['unit_id'] == 'test:1'
    result['paragraphs'][0]['evidence'][0]['unit_id'] = 'invented'
    with pytest.raises(ValueError):
        answers.validate_answer(result, units)
    result['paragraphs'][0]['evidence'][0] = {'unit_id': 'test:1', 'quote': 'not present in document'}
    with pytest.raises(ValueError):
        answers.validate_answer(result, units)
    result['paragraphs'][0]['evidence'] = []
    with pytest.raises(ValueError):
        answers.validate_answer(result, units)


def test_heading_is_valid_evidence_but_fabricated_quote_is_not():
    unit = {'unit_id': 'one', 'text': '1 March 2023', 'heading': '7. Date of ruling issued', 'locator': None, 'url': 'https://www.ird.gov.hk/'}
    result = {'paragraphs': [{'text': 'The date appears in section 7.', 'evidence': [{'unit_id': 'one', 'quote': unit['heading']}]}], 'missing_info': []}
    assert answers.validate_answer(result, {'one': unit})[1][0]['quote'] == unit['heading']
    result['paragraphs'][0]['evidence'][0]['quote'] = '1 March 2024'
    with pytest.raises(ValueError):
        answers.validate_answer(result, {'one': unit})


def test_model_cannot_invent_exact_references_but_followups_keep_user_case():
    doc = {'messages': [{'role': 'user', 'text': 'Case 68'}]}
    query = research_query(doc, 'When was it issued?', 'Case 68 s.15I')
    assert 'Case 68' in query and '15I' not in query
    query = research_query({'messages': []}, 'Explain receipt in HK', 'received s.15I Case 999')
    assert '15I' not in query and '999' not in query
    query = research_query(doc, 'Compare s.15K and s.15M', 's.15K')
    assert 's.15K' in query and 's.15M' in query
    question = '内地个人股息税率多少？'
    assert research_query(doc, question, '香港 FSIE 股息') == question


def test_only_exact_manifest_sources_can_leave_process(monkeypatch):
    monkeypatch.setattr(answers, 'catalog', lambda: {'sources': [{'source_id': 'official', 'url': 'https://www.ird.gov.hk/official'}], 'allowed_source_domains': ['www.ird.gov.hk']})
    doc = {'source_id': 'official', 'url': 'https://www.ird.gov.hk/official', 'unit_id': 'one', 'text': 'public evidence'}
    assert answers.evidence_units({'passages': [doc]})['one']['text'] == 'public evidence'
    assert not answers.evidence_units({'passages': [{**doc, 'url': 'https://evil.test/'}]})
    assert not answers.evidence_units({'passages': [{**doc, 'source_id': 'private'}]})


def test_no_evidence_does_not_call_model(monkeypatch):
    monkeypatch.setattr(answers, 'evidence_units', lambda _: {})
    monkeypatch.setattr(answers.httpx, 'AsyncClient', lambda **_: pytest.fail('No evidence must not call model'))
    result = asyncio.run(answers.compose_async('Case 999', {'status': 'no_matching_units'}))
    assert result['answer_status'] == 'insufficient_evidence'


def test_invalid_citations_retry_then_safe_fallback(monkeypatch):
    from packages.chat import service
    from packages.model_adapter.client import ModelConfig
    monkeypatch.setattr(answers, 'evidence_units', lambda _: {'one': {'unit_id': 'one', 'text': 'Synthetic evidence'}})
    monkeypatch.setattr(service, 'current_model_config', lambda: ModelConfig('https://model.test', 'fixture', 'fixture'))
    attempts = []
    def respond(request):
        attempts.append(request)
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps({'paragraphs': [], 'missing_info': []})}}]})
    original = httpx.AsyncClient
    monkeypatch.setattr(answers.httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(respond), **kw))
    result = asyncio.run(answers.compose_async('Explain FSIE', {'status': 'available'}))
    assert len(attempts) == 2
    assert result['answer_status'] == 'summary_unavailable'
    assert not result['citations']
