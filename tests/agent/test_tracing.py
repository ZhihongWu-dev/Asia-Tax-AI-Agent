from tests.agent.private_file_assertions import assert_private
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from uuid import uuid4

import pytest

from packages.agent.tracing import ExecutionTrace, current_trace, current_span, emit, span, node
from packages.agent import logs
from packages.agent.budget import model_call
from packages.agent.providers import MockKnowledgeProvider
from packages.chat.service import ChatService, WorkflowError
from packages.chat.store import ChatStore


def test_nested_nodes_and_model_decisions_have_correlated_order_without_payloads():
    trace = ExecutionTrace('case', 'request')
    token = current_trace.set(trace)
    try:
        def route(state):
            result = model_call(lambda: {'intent': 'research', 'query': '香港FSIE', 'reply': 'PRIVATE_REPLY',
                                         'facts': {'payer_entity': 'PRIVATE_ENTITY'}})
            return {'turn': result}
        node('route', route, {})
    finally:
        current_trace.reset(token)
    events = trace.snapshot()['events']
    assert [e['seq'] for e in events] == list(range(1, len(events)+1))
    start = next(e for e in events if e['name'] == 'node.route' and e['status'] == 'started')
    model = next(e for e in events if e['name'] == 'model.call' and e['status'] == 'started')
    assert model['parent_span_id'] == start['data']['span_id']
    assert any(e['name'] == 'model.decision' and e['data']['intent'] == 'research' for e in events)
    serialized = json.dumps(events)
    assert 'PRIVATE_REPLY' not in serialized and 'PRIVATE_ENTITY' not in serialized
    assert current_span.get() is None


def test_failures_log_only_type_and_safe_code_and_restore_context():
    trace = ExecutionTrace('case', 'request')
    token = current_trace.set(trace)
    try:
        with pytest.raises(ValueError):
            with span('broken'):
                raise ValueError('password=private secret data')
    finally:
        current_trace.reset(token)
    event = trace.events[-1]
    assert event['status'] == 'error' and event['data']['error_type'] == 'ValueError'
    assert 'private' not in json.dumps(trace.snapshot())
    assert current_trace.get() is None and current_span.get() is None


def test_secret_redaction_event_bound_and_separate_concurrent_turns():
    def run(number):
        trace = ExecutionTrace(str(number), str(number))
        token = current_trace.set(trace)
        try:
            emit('query', query='key sk-example123 person@example.com password=example 13612345678', api_key='secret')
            for _ in range(300):
                emit('tick', value=number)
            emit('failure', 'error', error_type='TimeoutError')
            return trace.snapshot()
        finally:
            current_trace.reset(token)
    with ThreadPoolExecutor(max_workers=2) as pool:
        records = list(pool.map(run, [1, 2]))
    assert records[0]['trace_id'] != records[1]['trace_id']
    for number, record in enumerate(records, 1):
        assert record['case_id'] == str(number) and record['dropped_events'] > 0
        assert record['events'][-1]['status'] == 'error'
        assert all(e['data'].get('value', number) == number for e in record['events'])
        serialized = json.dumps(record)
        assert 'sk-example123' not in serialized and 'person@example.com' not in serialized
        assert 'password=example' not in serialized and '13612345678' not in serialized


def test_traces_are_log_only_and_retry_is_idempotent(tmp_path, monkeypatch):
    directory = tmp_path / 'logs'
    monkeypatch.setattr(logs, 'log_dir', lambda: directory)
    store = ChatStore(f'sqlite:///{tmp_path}/traces.sqlite')
    service = ChatService(store, provider=MockKnowledgeProvider(), orchestration='hybrid', dynamic_planner=False,
        turner=lambda *_: {'intent': 'research', 'reply': 'Checking.', 'facts': {}, 'query': '香港 FSIE 股息'})
    try:
        case = store.create('owner')
        request_id = str(uuid4())
        result = service.message('owner', case['id'], 0, request_id, '香港 FSIE 股息', True)
        trace_id = result['workflow']['trace_id']
        events = list(logs.records(directory, 'events'))
        runs = list(logs.records(directory, 'runs'))
        assert len(runs) == 1 and runs[0]['trace_id'] == trace_id
        assert runs[0]['case_id'] == case['id'] and runs[0]['request_id'] == request_id
        assert any(e['name'] == 'node.route' for e in events)
        assert any(e['name'] == 'knowledge.retrieve' for e in events)
        assert any(e['name'] == 'answer.validate' for e in events)
        assert 'execution_trace' not in json.dumps(result)
        assert 'execution_trace' not in json.dumps(store.get('owner', case['id']))
        again = service.message('owner', case['id'], 0, request_id, '香港 FSIE 股息', True)
        assert len(list(logs.records(directory, 'runs'))) == 1
        assert len(list(logs.records(directory, 'events'))) == len(events)
        assert len(again['messages']) == 2
        seen = []
        def next_turn(document, _text):
            seen.append(document)
            return {'intent': 'chat', 'reply': '收到。', 'facts': {}, 'query': ''}
        service.turner = next_turn
        result = service.message('owner', case['id'], again['revision'], str(uuid4()), '谢谢', True)
        assert seen and all('execution_trace' not in m.get('workflow', {}) for m in seen[0]['messages'])
        assert 'execution_trace' not in json.dumps(result)
        assert result['messages'][-1]['workflow']['trace_id'] != trace_id
        assert len(list(logs.records(directory, 'runs'))) == 2
    finally:
        store.engine.dispose()


def test_failed_turn_is_exported_without_partial_fact_commit(tmp_path, monkeypatch):
    directory = tmp_path / 'logs'
    monkeypatch.setattr(logs, 'log_dir', lambda: directory)
    store = ChatStore(f'sqlite:///{tmp_path}/failed.sqlite')
    def broken(*_):
        raise WorkflowError('model_failed')
    service = ChatService(store, orchestration='hybrid', turner=broken, provider=MockKnowledgeProvider())
    try:
        case = store.create('owner')
        with pytest.raises(WorkflowError):
            service.message('owner', case['id'], 0, str(uuid4()), '香港股息', True)
        records = list(logs.records(directory, 'runs'))
        assert records and records[0]['status'] == 'error'
        assert records[0]['error_code'] == 'model_failed'
        events = list(logs.records(directory, 'events'))
        assert events[-1]['status'] == 'error'
        assert store.get('owner', case['id'])['messages'] == []
        for name in ('events.jsonl', 'runs.jsonl'):
            assert_private(directory / name)
    finally:
        store.engine.dispose()
