"""Tool-loop acceptance: real service/graph, scripted model, synthetic evidence."""
from copy import deepcopy
from uuid import uuid4
import json
import pytest
from fastapi.testclient import TestClient
from packages.chat.service import ChatService, WorkflowError
from packages.chat.store import ChatStore
from packages.agent.providers import MockKnowledgeProvider

QUERY = '香港境外股息 FSIE'


class Provider(MockKnowledgeProvider):
    def __init__(self, scenario='MOCK-01'):
        super().__init__(scenario)
        self.calls = []

    def search_evidence(self, request, context):
        self.calls.append((request, context))
        return super().search_evidence(request, context)


class Planner:
    def __init__(self, *steps):
        self.steps, self.observations = list(steps), []

    def __call__(self, doc, observation):
        self.observations.append(deepcopy(observation))
        step = self.steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


def tool(name, query=''):
    return {'tool': name, 'query': query}


@pytest.fixture
def chat(tmp_path):
    store = ChatStore(f'sqlite:///{tmp_path / "tools.sqlite"}')
    service = ChatService(store, provider=Provider(), orchestration='hybrid', dynamic_planner=True,
                          harness_mode='tools', turner=lambda *_: {
                              'intent': 'research', 'reply': '将查阅。', 'facts': {}, 'query': QUERY,
                              'uses_case': False, 'task_kind': 'reference_lookup'})
    yield service
    store.engine.dispose()


def send(chat, doc=None, text='整理当前案件信息，并查香港股息规定', **kwargs):
    doc = doc or chat.store.create('owner')
    return chat.message('owner', doc['id'], doc['revision'], str(uuid4()), text, True, **kwargs)


def test_read_facts_then_law_and_finish_preserves_both_results(chat):
    doc = chat.store.create('owner')
    doc = chat.edit('owner', doc['id'], 0, str(uuid4()), {'dividend_amount': 123456})
    chat.tool_planner = Planner(tool('read_case_facts'), tool('search_law', QUERY), tool('finish'))
    result = send(chat, doc)
    assert '123456' in result['messages'][-1]['text']
    assert '模拟联调资料' in result['messages'][-1]['text']
    assert chat.provider.calls[0][0].kind == 'law'
    assert chat.provider.calls[0][1].case_id is None
    assert result['facts'] == doc['facts'] and result['confirmed_revision'] is None
    assert [c['tool'] for c in result['workflow']['tool_calls']] == ['read_case_facts', 'search_law']
    assert result['workflow']['harness_stop'] == 'finished'


def test_law_and_cases_use_distinct_provider_arguments(chat):
    chat.tool_planner = Planner(tool('search_law', QUERY), tool('search_cases', QUERY), tool('finish'))
    result = send(chat)
    assert [req.kind for req, _ in chat.provider.calls] == ['law', 'ruling']
    assert len(result['messages'][-1]['research_results']) == 2
    assert result['messages'][-1]['text'].count('模拟联调资料') == 2


def test_check_gaps_is_read_only_and_does_not_authorize_partial(chat):
    doc = chat.store.create('owner')
    doc = chat.edit('owner', doc['id'], 0, str(uuid4()), {'recipient_type': 'unknown'})
    chat.tool_planner = Planner(tool('check_fact_gaps'), tool('finish'))
    result = send(chat, doc)
    assert 'unknown' in result['messages'][-1]['text']
    assert result['facts'] == doc['facts']
    assert not result['dialogue'].get('partial_consent') and not result['analyses']
    assert not chat.provider.calls


@pytest.mark.parametrize('hint', ['auto', 'dividend_consultation', 'fact_intake', 'reference_lookup'])
def test_ordinary_chat_never_enters_tool_loop(chat, hint):
    chat.turner = lambda *_: {'intent': 'chat', 'facts': {}, 'reply': '你好', 'query': ''}
    chat.tool_planner = lambda *_: pytest.fail('No tools for chat')
    result = send(chat, text='你好', entry_hint=hint)
    assert not chat.provider.calls and 'tool_calls' not in result['workflow']


def test_fixed_entry_remains_on_fixed_path(chat):
    chat.tool_planner = lambda *_: pytest.fail('Shortcut must keep fixed path')
    result = send(chat, text='研究境外股息的 FSIE 处理，应当查阅哪些官方资料？', entry_hint='reference_lookup')
    assert len(chat.provider.calls) == 1 and 'harness_version' not in result['workflow']


def test_duplicate_stops_without_second_query(chat):
    chat.tool_planner = Planner(tool('search_guidance', QUERY), tool('search_guidance', QUERY))
    result = send(chat)
    assert len(chat.provider.calls) == 1
    assert result['workflow']['harness_stop'] == 'duplicate_tool_call'
    assert result['workflow']['tool_calls'][-1]['status'] == 'rejected'
    assert '模拟联调资料' in result['messages'][-1]['text']


@pytest.mark.parametrize('query', ['新加坡税', '香港境外股息2027', '香港Case 999', '香港工资待遇'])
def test_scope_and_invented_reference_rejected_before_query(chat, query):
    chat.tool_planner = Planner(tool('search_law', query))
    result = send(chat)
    assert not chat.provider.calls and not result['analyses']
    assert result['workflow']['harness_stop'] == 'tool_scope_rejected'


@pytest.mark.parametrize('proposal', [
    {'tool': 'approve_report'},
    {'tool': 'search_law', 'query': QUERY, 'owner': 'other'},
    {'tool': 'read_case_facts', 'query': 'SELECT * FROM cases'},
])
def test_invalid_control_and_identity_arguments_fail_without_commit(chat, proposal):
    doc = chat.store.create('owner')
    chat.tool_planner = Planner(proposal)
    with pytest.raises(WorkflowError, match='model_failed'):
        send(chat, doc)
    assert chat.store.get('owner', doc['id']) == doc and not chat.provider.calls


def test_restricted_original_never_enters_followup_planner(chat):
    chat.provider = Provider('MOCK-03')
    chat.tool_planner = Planner(tool('search_guidance', QUERY), tool('finish'))
    result = send(chat)
    raw = chat.provider.fixture['display_store'][0]['text']
    assert raw in json.dumps(result['messages'][-1]['research'], ensure_ascii=False)
    assert raw not in json.dumps(chat.tool_planner.observations, ensure_ascii=False)
    assert 'model_evidence' not in json.dumps(chat.tool_planner.observations)
    assert chat.tool_planner.observations[-1]['observations'][0]['evidence_count'] == 1


def test_followup_model_failure_keeps_successful_result(chat):
    chat.tool_planner = Planner(tool('search_law', QUERY), WorkflowError('model_failed'))
    result = send(chat)
    assert result['workflow']['error_code'] == 'model_failed'
    assert '模拟联调资料' in result['messages'][-1]['text']
    assert result['workflow']['status'] == 'partial_failure'


def test_first_model_failure_keeps_original_case(chat):
    doc = chat.store.create('owner')
    chat.tool_planner = Planner(WorkflowError('model_failed'))
    with pytest.raises(WorkflowError, match='model_failed'):
        send(chat, doc)
    assert chat.store.get('owner', doc['id']) == doc


def test_retrieval_failure_is_not_no_match_or_mock_fallback(chat):
    doc = chat.store.create('owner')
    chat.provider = Provider('MOCK-04')
    chat.tool_planner = Planner(tool('search_law', QUERY))
    with pytest.raises(WorkflowError, match='knowledge_unavailable'):
        send(chat, doc)
    assert chat.store.get('owner', doc['id']) == doc


def test_no_match_rewrite_is_bounded_to_one_query(chat):
    chat.provider = Provider('MOCK-02')
    chat.tool_planner = Planner(tool('search_law', QUERY), tool('search_law', QUERY + '官方指引'),
                                tool('search_cases', QUERY + '参考裁定'))
    result = send(chat)
    assert len(chat.provider.calls) == 2
    assert result['workflow']['harness_stop'] == 'rewrite_limit'
    assert '未找到' in result['messages'][-1]['text']


def test_shared_budget_stops_after_two_tools_and_keeps_results(chat, monkeypatch):
    from packages.agent import hybrid
    from packages.agent.budget import RunBudget
    monkeypatch.setattr(hybrid, 'RunBudget', lambda: RunBudget(action_limit=2))
    chat.tool_planner = Planner(tool('search_law', QUERY), tool('search_cases', QUERY))
    result = send(chat)
    assert len(chat.provider.calls) == 2
    assert result['workflow']['harness_stop'] == 'budget_exhausted'
    assert len(result['messages'][-1]['research_results']) == 2


def test_analysis_not_available_without_explicit_request(chat):
    chat.tool_planner = Planner(tool('prepare_analysis'))
    result = send(chat)
    assert not result['analyses']
    assert result['workflow']['harness_stop'] == 'tool_not_allowed'
    assert 'prepare_analysis' not in [t['name'] for t in chat.tool_planner.observations[0]['tools']]


def test_explicit_analysis_without_confirmation_uses_existing_gate(chat):
    chat.tool_planner = lambda *_: pytest.fail('Gate must run before planner')
    result = send(chat, text='开始分析')
    assert result['workflow']['reason_code'] == 'confirmation_required'
    assert not result['analyses']


def test_authorized_analysis_creates_only_pending_review_report(chat):
    doc = chat.store.create('owner')
    doc = chat.edit('owner', doc['id'], 0, str(uuid4()), {
        'recipient_type': 'company', 'income_type': 'dividend', 'analysis_jurisdiction': 'HK',
        'consultation_goal': 'scope', 'payer_jurisdiction': '新加坡'})
    chat.tool_planner = lambda *_: pytest.fail('Partial consent must not enter tool loop')
    doc = send(chat, doc, text='先看部分整理')
    doc = chat.confirm('owner', doc['id'], doc['revision'], str(uuid4()))
    chat.tool_planner = Planner(tool('prepare_analysis'))
    result = send(chat, doc, text='开始分析')
    assert len(result['analyses']) == 1
    assert result['analyses'][0]['review']['status'] == 'pending_final_review'
    assert result['workflow']['harness_stop'] == 'analysis_ready'


def test_unexpected_planner_exception_is_sanitized_and_preserves_result(chat):
    secret = 'INTERNAL_CREDENTIAL_SHOULD_NOT_ESCAPE'
    chat.tool_planner = Planner(tool('search_law', QUERY), RuntimeError(secret))
    result = send(chat)
    assert result['workflow']['error_code'] == 'model_failed'
    assert secret not in json.dumps(result)


def test_tool_loop_rejected_when_existing_fact_question_needs_answer(chat):
    chat.turner = lambda *_: {'intent': 'intake', 'facts': {'income_type': 'dividend'}, 'reply': '已记录', 'query': ''}
    chat.tool_planner = lambda *_: pytest.fail('One fact question must take priority')
    result = send(chat, text='我想分析这笔股息')
    assert result['messages'][-1]['question']['field'] == 'recipient_type'
    assert not chat.provider.calls


def test_explicit_router_queue_is_not_executed_again_by_tool_planner(chat):
    chat.turner = lambda *_: {'intent': 'research', 'reply': '将查阅', 'facts': {}, 'query': QUERY,
        'tasks': [{'kind': 'reference_lookup', 'query': QUERY + '官方指引', 'uses_case': False},
                  {'kind': 'reference_lookup', 'query': QUERY + '参考裁定', 'uses_case': False}]}
    chat.tool_planner = lambda *_: pytest.fail('Router already supplied a queue')
    result = send(chat)
    assert len(chat.provider.calls) == 2
    assert len(result['messages'][-1]['research_results']) == 2


def test_format_repair_uses_remaining_deadline_not_a_fresh_budget(monkeypatch):
    from packages.agent.harness import plan_tool
    from packages.agent.budget import RunBudget, current_budget
    from packages.model_adapter.client import ModelConfig, OpenAICompatibleClient
    from packages.chat import service
    budget = RunBudget(seconds=45)
    monkeypatch.setattr(service, 'current_model_config', lambda: ModelConfig('https://model.test', 'fixture', 'fixture', 45, 0))
    timeouts = []
    def respond(client, *_args, **_kwargs):
        timeouts.append(client.config.timeout_seconds)
        if len(timeouts) == 1:
            budget.started -= 43
            return {'tool': 'invalid'}
        return {'tool': 'finish', 'query': ''}
    monkeypatch.setattr(OpenAICompatibleClient, 'chat_json', respond)
    token = current_budget.set(budget)
    try:
        assert plan_tool({}, {})['tool'] == 'finish'
        assert 0 < timeouts[1] <= 2 and timeouts[0] > 40
        assert budget.counts['model'] == 2
    finally:
        current_budget.reset(token)


@pytest.mark.parametrize('sse', [False, True])
def test_tool_loop_via_actual_message_api(chat, sse):
    from apps.api.main import app
    from apps.api.auth import optional_user
    from apps.api.chat import get_service
    chat.tool_planner = Planner(tool('search_law', QUERY), tool('search_cases', QUERY), tool('finish'))
    app.dependency_overrides[optional_user] = lambda: {'id': 'fixture', 'email': 'fixture@example.invalid'}
    app.dependency_overrides[get_service] = lambda: chat
    try:
        with TestClient(app) as client:
            headers = {'x-asiatax-request': '1'}
            doc = client.post('/api/cases', headers=headers).json()
            payload = {'text': '查询香港股息法条和参考裁定', 'revision': 0,
                       'request_id': str(uuid4()), 'data_approved': True, 'entry_hint': 'auto'}
            response = client.post(f'/api/cases/{doc["id"]}/messages',
                headers={**headers, **({'accept': 'text/event-stream'} if sse else {})}, json=payload)
            assert response.status_code == 200
            if sse:
                events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
                assert [event['type'] for event in events] == ['done']
                result = events[-1]['case']
            else:
                result = response.json()
            assert result['workflow']['harness_stop'] == 'finished'
            before = len(chat.provider.calls)
            duplicate = client.post(f'/api/cases/{doc["id"]}/messages', headers=headers, json=payload)
            assert duplicate.status_code == 200 and len(chat.provider.calls) == before
    finally:
        app.dependency_overrides.clear()
