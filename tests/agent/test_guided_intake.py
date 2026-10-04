"""Conversation acceptance cases; fake parser isolates policy from model quality."""
from copy import deepcopy
from uuid import uuid4

import pytest

from packages.agent.dialogue import identification, required_fields, fingerprint, JUDGMENT_FIELDS
from packages.agent.providers import MockKnowledgeProvider
from packages.chat.service import ChatService, WorkflowError, validate_turn, turn_prompt
from packages.chat.store import ChatStore, RevisionConflict
from packages.chat.facts import catalog


@pytest.fixture
def chat(tmp_path):
    store = ChatStore(f'sqlite:///{tmp_path}/cases.sqlite')
    result = ChatService(store, provider=MockKnowledgeProvider())
    yield result
    store.engine.dispose()


def turn(facts=None, intent='intake', **extras):
    return {'intent': intent, 'facts': facts or {}, 'reply': 'parser reply', 'query': '股息收取规定' if intent == 'research' else '', **extras}


def send(chat, doc, parsed=None, text='测试描述', request_id=None):
    if parsed is not None:
        chat.turner = lambda *_: deepcopy(parsed)
    return chat.message('owner', doc['id'], doc['revision'], request_id or str(uuid4()), text, True)


def edit(chat, doc, facts):
    return chat.edit('owner', doc['id'], doc['revision'], str(uuid4()), facts)


def case_facts(goal='scope'):
    return {'recipient_type': 'company', 'income_type': 'dividend', 'analysis_jurisdiction': 'HK',
            'consultation_goal': goal, 'payer_jurisdiction': '新加坡'}


def test_candidate_identification_needs_four_background_facts_not_amount(chat):
    doc = send(chat, chat.store.create('owner'), turn(case_facts()))
    assert doc['identification']['status'] == 'candidate_identified'
    assert 'dividend_amount' not in doc['facts']
    assert doc['messages'][-1]['question']['field'] == 'entity_hk_business_status'
    assert doc['questions'] == ['entity_hk_business_status']
    doc = edit(chat, doc, {'recipient_type': 'unknown'})
    assert doc['identification']['status'] == 'collecting'


def test_missing_company_cannot_be_inferred_from_hk_business(chat):
    doc = send(chat, chat.store.create('owner'), turn({'income_type': 'dividend', 'entity_hk_business_status': 'yes'}))
    assert doc['questions'] == ['recipient_type']


@pytest.mark.parametrize('goal,required,absent', [
    ('scope', 'entity_hk_business_status', 'holding_percentage_pct'),
    ('receipt', 'dividend_form', 'hk_staff_description'),
    ('participation', 'holding_percentage_pct', 'hk_premises_description'),
    ('substance', 'hk_staff_description', 'holding_percentage_pct'),
])
def test_task_specific_fields_do_not_interview_everything(goal, required, absent):
    doc = {'facts': {k: {'value': v} for k, v in case_facts(goal).items()}}
    fields = required_fields(doc)
    assert required in fields and absent not in fields
    assert not JUDGMENT_FIELDS.intersection(fields)


def test_unknown_is_kept_then_user_can_skip_to_other_information(chat):
    doc = send(chat, chat.store.create('owner'), turn({'income_type': 'dividend'}))
    doc = send(chat, doc, text='不知道')
    assert doc['facts']['recipient_type']['value'] == 'unknown'
    assert doc['questions'] == []
    assert doc['messages'][-1]['question']['kind'] == 'choice'
    doc = send(chat, doc, text='继续补充')
    assert doc['questions'] == ['analysis_jurisdiction']
    assert doc['facts']['recipient_type']['value'] == 'unknown'


def test_unavailable_is_not_unknown_or_negative_and_can_be_supplied_later(chat):
    doc = send(chat, chat.store.create('owner'), turn({'income_type': 'dividend'}))
    doc = send(chat, doc, text='暂时没有资料')
    assert 'recipient_type' not in doc['facts']
    assert doc['dialogue']['deferred']['recipient_type'] == 'unavailable'
    doc = send(chat, doc, turn({'recipient_type': 'company'}), '由公司收取')
    assert 'recipient_type' not in doc['dialogue']['deferred']
    assert doc['questions'] != ['recipient_type']


def test_two_attempt_budget_and_idempotency(chat):
    doc = send(chat, chat.store.create('owner'), turn({'income_type': 'dividend'}))
    first = doc
    rid = str(uuid4())
    doc = send(chat, doc, turn(), '我没理解这个问题', rid)
    assert doc['messages'][-1]['question']['attempt'] == 2
    assert send(chat, first, turn(), '我没理解这个问题', rid) == doc
    doc = send(chat, doc, turn(), '还是无法描述')
    assert doc['messages'][-1]['question']['kind'] == 'choice'
    assert doc['dialogue']['deferred']['recipient_type'] == 'unanswered'


def test_chat_and_reference_lookup_are_not_hijacked_by_old_conflict(chat):
    doc = edit(chat, chat.store.create('owner'), {'dividend_amount': 'conflict'})
    doc = send(chat, doc, turn(intent='chat'), '你好')
    assert doc['messages'][-1]['kind'] == 'chat'
    assert doc['workflow']['reason_code'] == 'ordinary_chat'
    doc = send(chat, doc, turn(intent='research'), '查案例68')
    assert doc['messages'][-1]['kind'] == 'research'
    assert doc['facts']['dividend_amount']['value'] == 'conflict'


def test_pause_refresh_resume_and_unbound_unknown(chat):
    doc = send(chat, chat.store.create('owner'), turn({'income_type': 'dividend'}))
    pending = doc['dialogue']['pending']
    doc = send(chat, doc, text='暂停')
    reloaded = chat.store.get('owner', doc['id'])
    assert reloaded['dialogue']['pending'] == pending
    assert doc['questions'] == []
    doc = send(chat, reloaded, turn(action='unknown'), '不知道')
    assert 'recipient_type' not in doc['facts']
    assert doc['messages'][-1]['question']['kind'] == 'mode'
    doc = send(chat, doc, text='继续案件')
    assert doc['questions'] == ['recipient_type']


def test_partial_requires_explicit_choice_and_tracks_exact_facts(chat):
    doc = send(chat, chat.store.create('owner'), turn({'income_type': 'dividend'}))
    doc = chat.confirm('owner', doc['id'], doc['revision'], str(uuid4()))
    with pytest.raises(WorkflowError, match='partial_confirmation_required'):
        chat.run('owner', doc['id'], doc['revision'], str(uuid4()))
    doc = send(chat, doc, turn(action='partial'), '谢谢')
    assert 'partial_consent' not in doc['dialogue']
    doc = send(chat, doc, text='先看部分整理')
    assert doc['dialogue']['partial_consent']['facts_hash'] == fingerprint(doc)
    assert '不是完整分析' in doc['messages'][-1]['text']
    doc = chat.run('owner', doc['id'], doc['revision'], str(uuid4()))
    assert doc['analyses'][-1]['intake_gaps']
    assert doc['analyses'][-1]['evidence_gate'] == 'insufficient'
    doc = edit(chat, doc, {'dividend_amount': 10})
    assert 'partial_consent' not in doc['dialogue']
    assert doc['analyses'][-1]['stale']


def test_field_specific_correction_and_other_difference_stays_conflict(chat):
    doc = edit(chat, chat.store.create('owner'), {'dividend_amount': 100, 'holding_percentage_pct': 10})
    text = '刚才金额说错了，应为200；持股20%'
    doc = send(chat, doc, turn({'dividend_amount': 200, 'holding_percentage_pct': 20},
                 corrections={'dividend_amount': '金额说错了，应为200'}), text)
    assert doc['facts']['dividend_amount']['value'] == 200
    assert doc['facts']['holding_percentage_pct']['value'] == 'conflict'
    assert doc['fact_conflicts']['holding_percentage_pct'] == {'previous': 10, 'candidate': 20}
    assert any(h.get('field') == 'dividend_amount' and (h.get('before') or {}).get('value') == 100 for h in doc['fact_history'])


def test_fabricated_correction_span_does_not_override(chat):
    doc = edit(chat, chat.store.create('owner'), {'dividend_amount': 100})
    doc = send(chat, doc, turn({'dividend_amount': 200}, corrections={'dividend_amount': '金额改为200'}), '金额200')
    assert doc['facts']['dividend_amount']['value'] == 'conflict'


def test_conflict_preserved_when_unknown_then_resolved_by_user(chat):
    doc = edit(chat, chat.store.create('owner'), {'dividend_amount': 100})
    doc = send(chat, doc, turn({'dividend_amount': 200}), '金额200')
    doc = send(chat, doc, text='不知道')
    assert doc['facts']['dividend_amount']['value'] == 'conflict'
    assert doc['fact_conflicts']['dividend_amount'] == {'previous': 100, 'candidate': 200}
    doc = edit(chat, doc, {'dividend_amount': 200})
    assert doc['fact_conflicts'] == {}


def test_mixed_conflict_defers_lookup_and_resume_retrieves(chat):
    doc = edit(chat, chat.store.create('owner'), {'dividend_amount': 100})
    doc = send(chat, doc, turn({'dividend_amount': 200}, intent='research'), '金额200，查相关规定')
    assert doc['dialogue']['deferred_query'] == '股息收取规定'
    assert 'retrieve' not in doc['workflow']['trace']
    doc = send(chat, doc, turn({'dividend_amount': 200}), '采用200')
    assert doc['facts']['dividend_amount']['value'] == 200
    doc = send(chat, doc, text='继续案件')
    assert 'retrieve' in doc['workflow']['trace']
    assert 'deferred_query' not in doc['dialogue']


def test_mixed_correction_persists_when_retrieval_fails_then_retries(chat):
    doc = edit(chat, chat.store.create('owner'), {'dividend_amount': 100})
    chat.provider = MockKnowledgeProvider('MOCK-04')
    doc = send(chat, doc, turn({'dividend_amount': 200}, intent='research', corrections={'dividend_amount': '金额改为200'}), '金额改为200，查相关规定')
    assert doc['facts']['dividend_amount']['value'] == 200
    assert doc['workflow']['status'] == 'partial_failure'
    assert doc['workflow']['error_code'] == 'knowledge_unavailable'
    assert doc['workflow']['retrieval_calls'] == 2
    history_len = len(doc['fact_history'])
    chat.provider = MockKnowledgeProvider()
    doc = send(chat, doc, text='重试检索')
    assert len(doc['fact_history']) == history_len
    assert doc['messages'][-1]['research']['status'] == 'available'


def test_standalone_research_does_not_inherit_case_period(chat):
    seen = []
    original = chat.provider.search_evidence
    def search(request, context):
        seen.append(request)
        return original(request, context)
    chat.provider.search_evidence = search
    doc = edit(chat, chat.store.create('owner'), {'accrual_date': '2025-04-10', 'income_event_status': 'occurred', 'income_type': 'dividend'})
    doc = send(chat, doc, turn(intent='research'), '查案例68')
    assert seen[-1].applicable_date is None and seen[-1].fact_filters == []
    doc = send(chat, doc, turn(intent='research', uses_case=True), '查这笔股息的相关规定')
    assert str(seen[-1].applicable_date) == '2025-04-10'
    assert seen[-1].intent == 'case_analysis'


def test_planned_date_is_not_actual_and_no_receipt_date_demand(chat):
    seen = []
    original = chat.provider.search_evidence
    chat.provider.search_evidence = lambda req, ctx: (seen.append(req), original(req, ctx))[1]
    facts = {**case_facts('receipt'), 'income_event_status': 'planned', 'accrual_date': '2027-05-01'}
    doc = send(chat, chat.store.create('owner'), turn(facts, intent='research'))
    assert seen[-1].date_status == 'planned'
    assert 'receipt_date' not in required_fields(doc)


def test_new_case_does_not_mutate_existing_case(chat):
    doc = edit(chat, chat.store.create('owner'), {'dividend_amount': 100})
    doc = send(chat, doc, turn({'dividend_amount': 999}, action='new_case'), '另一个案件金额999')
    assert doc['facts']['dividend_amount']['value'] == 100
    assert '新对话' in doc['messages'][-1]['text']


@pytest.mark.parametrize('patch', [{'recipient_type': 'individual'}, {'income_type': 'interest'}, {'analysis_jurisdiction': 'JP'}])
def test_explicit_unsupported_background_has_no_tax_conclusion(chat, patch):
    doc = send(chat, chat.store.create('owner'), turn(patch))
    assert doc['identification']['status'] == 'unsupported'
    assert doc['questions'] == []
    assert doc['workflow']['reason_code'] == 'out_of_scope'


def test_no_match_explains_specific_query_and_date(chat):
    chat.provider = MockKnowledgeProvider('MOCK-02')
    doc = send(chat, chat.store.create('owner'), turn({'accrual_date': '2025-04-10', 'income_event_status': 'occurred'}, intent='research'))
    answer = doc['messages'][-1]['answer']
    assert '股息收取规定' in answer['text'] and '2025-04-10' in answer['text']
    assert '不存在' in answer['summary'] and '不能' in answer['summary']


def test_model_contract_rejects_undeclared_actions_and_correction_fields():
    for extra in ({'action': 'approve'}, {'corrections': {'expert_decision_status': 'approved'}}, {'uses_case': 'yes'}):
        with pytest.raises(ValueError):
            validate_turn(turn(**extra))
    assert validate_turn(turn())['intent'] == 'intake'
    assert 'expert_decision_status' not in {f['field_name'] for f in catalog()}


def test_candidate_cases_have_explicit_missing_identification_fields():
    import json
    from pathlib import Path
    cases = json.loads(Path('tests/fsie/candidate_cases.json').read_text())['cases']
    for case in cases:
        doc = {'facts': {k: {'value': v} for k, v in case['facts'].items()}}
        status = identification(doc)
        if case['facts'].get('income_type') != 'dividend':
            assert status['status'] == 'unsupported'
        else:
            assert status['status'] == 'collecting'
            assert 'recipient_type' in status['missing_fields']
    # These fixtures don't justify claiming complete user-side routing coverage.


def test_in_kind_never_asks_for_a_bank_transfer_or_amount(chat):
    doc = send(chat, chat.store.create('owner'), turn({**case_facts('receipt'), 'dividend_form': 'in_kind'}))
    required = required_fields(doc)
    assert 'transaction_flow_description' in required
    assert 'bank_or_account_path' not in required
    assert 'dividend_amount' not in required


def test_unknown_form_does_not_assume_cash(chat):
    doc = edit(chat, chat.store.create('owner'), {**case_facts('receipt'), 'dividend_form': 'unknown'})
    assert 'bank_or_account_path' not in required_fields(doc)
    assert 'transaction_flow_description' in required_fields(doc)


def test_goal_switch_rebuilds_queue_and_invalidates_partial_consent(chat):
    doc = send(chat, chat.store.create('owner'), turn(case_facts('scope')))
    doc = send(chat, doc, text='先看部分整理')
    doc = send(chat, doc, turn({'consultation_goal': 'substance'}), '现在我想先看经济实质')
    assert doc['facts']['consultation_goal']['value'] == 'substance'
    assert 'partial_consent' not in doc['dialogue']
    assert 'hk_staff_description' in required_fields(doc)


def test_short_enum_answer_only_binds_to_active_field(chat):
    doc = send(chat, chat.store.create('owner'), turn({'income_type': 'dividend'}))
    chat.turner = lambda *_: pytest.fail('Exact answer should not need a model call')
    doc = send(chat, doc, text='公司')
    assert doc['facts']['recipient_type']['value'] == 'company'
    pending = deepcopy(doc['dialogue']['pending'])
    doc = send(chat, doc, text='暂停')
    doc = send(chat, doc, text='是')
    assert doc['facts'].get(pending['field']) is None
    assert doc['messages'][-1]['question']['kind'] == 'mode'


def test_partial_negation_is_not_consent(chat):
    doc = send(chat, chat.store.create('owner'), turn({'income_type': 'dividend'}))
    doc = send(chat, doc, turn(action='partial'), '不要给我部分整理')
    assert 'partial_consent' not in doc['dialogue']


def test_unqualified_date_is_not_assumed_actual(chat):
    seen = []
    original = chat.provider.search_evidence
    chat.provider.search_evidence = lambda req, ctx: (seen.append(req), original(req, ctx))[1]
    doc = send(chat, chat.store.create('owner'), turn({'accrual_date': '2027-05-01'}, intent='research'))
    assert seen[-1].date_status == 'unknown' and seen[-1].applicable_date is None
    assert doc['facts']['accrual_date']['value'] == '2027-05-01'


def test_no_response_does_not_advance_question_or_approve_case(chat):
    doc = send(chat, chat.store.create('owner'), turn({'income_type': 'dividend'}))
    before = deepcopy(doc['dialogue'])
    reloaded = chat.store.get('owner', doc['id'])
    assert reloaded['dialogue'] == before
    assert reloaded['confirmed_facts'] is None


def test_stale_reply_cannot_mutate_a_newer_question(chat):
    original = send(chat, chat.store.create('owner'), turn({'income_type': 'dividend'}))
    current = send(chat, original, text='公司')
    with pytest.raises(RevisionConflict):
        send(chat, original, text='不知道')
    assert chat.store.get('owner', current['id'])['facts']['recipient_type']['value'] == 'company'


def test_unknown_about_another_field_does_not_answer_current_question(chat):
    doc = send(chat, chat.store.create('owner'), turn({'income_type': 'dividend'}))
    assert doc['questions'] == ['recipient_type']
    doc = send(chat, doc, turn({'receipt_date': 'unknown', 'dividend_amount': 100}, action='unknown'), '收款日期不知道，金额100')
    assert 'recipient_type' not in doc['facts']
    assert 'recipient_type' not in doc['dialogue']['deferred']
    assert doc['facts']['receipt_date']['value'] == 'unknown'


def test_entry_recognition_does_not_wait_for_payer_country_or_legal_source(chat):
    facts = case_facts()
    facts.pop('payer_jurisdiction')
    doc = send(chat, chat.store.create('owner'), turn(facts))
    assert doc['identification']['status'] == 'candidate_identified'
    assert doc['questions'] == ['payer_jurisdiction']
    assert doc['facts'].get('source_analysis') is None


def test_numeric_substring_is_not_a_valid_correction(chat):
    doc = edit(chat, chat.store.create('owner'), {'dividend_amount': 100})
    doc = send(chat, doc, turn({'dividend_amount': 200}, corrections={'dividend_amount': '金额改为1200'}), '金额改为1200')
    assert doc['facts']['dividend_amount']['value'] == 'conflict'


def test_independent_lookup_keeps_a_deferred_case_query(chat):
    doc = edit(chat, chat.store.create('owner'), {'dividend_amount': 100})
    doc = send(chat, doc, turn({'dividend_amount': 200}, intent='research'))
    query = doc['dialogue']['deferred_query']
    doc = send(chat, doc, {**turn(intent='research'), 'query': '案例68'}, '先查案例68')
    assert doc['dialogue']['deferred_query'] == query
    assert doc['facts']['dividend_amount']['value'] == 'conflict'


def test_question_about_partial_output_is_not_permission(chat):
    doc = send(chat, chat.store.create('owner'), turn({'income_type': 'dividend'}))
    doc = send(chat, doc, turn(action='partial'), '什么是部分整理？')
    assert 'partial_consent' not in doc['dialogue']


def test_natural_unknown_does_not_resolve_existing_conflict(chat):
    doc = edit(chat, chat.store.create('owner'), {'dividend_amount': 100})
    doc = send(chat, doc, turn({'dividend_amount': 200}), '金额200')
    doc = send(chat, doc, turn({'dividend_amount': 'unknown'}), '我不知道哪个金额正确')
    assert doc['facts']['dividend_amount']['value'] == 'conflict'
    assert doc['fact_conflicts']['dividend_amount'] == {'previous': 100, 'candidate': 200}
    assert doc['messages'][-1]['question']['kind'] == 'choice'
    with pytest.raises(WorkflowError, match='resolve_conflicts'):
        chat.confirm('owner', doc['id'], doc['revision'], str(uuid4()))


def test_additional_conflicting_candidate_preserves_original_value_and_history(chat):
    doc = edit(chat, chat.store.create('owner'), {'dividend_amount': 100})
    doc = send(chat, doc, turn({'dividend_amount': 200}), '金额200')
    doc = send(chat, doc, text='暂停')
    doc = send(chat, doc, turn({'dividend_amount': 300}), '另有材料说金额300')
    assert doc['fact_conflicts']['dividend_amount'] == {'previous': 100, 'candidate': 300}
    entries = [h['conflicts']['dividend_amount'] for h in doc['fact_history'] if h.get('action') == 'conflict_detected']
    assert entries == [{'previous': 100, 'candidate': 200}, {'previous': 100, 'candidate': 300}]


def test_answer_with_followup_reports_waiting_user_to_frontend(chat):
    doc = send(chat, chat.store.create('owner'), turn({'income_type': 'dividend'}, intent='research'))
    assert doc['messages'][-1]['question']['field'] == 'recipient_type'
    assert doc['workflow']['status'] == 'waiting_user'
    assert doc['workflow']['reason_code'] == 'fact_collection'
    assert doc['workflow']['retrieval_reason_code'] == 'evidence_available'
    assert doc['messages'][-1]['research']['reason_code'] == 'evidence_available'
