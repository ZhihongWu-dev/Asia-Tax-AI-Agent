from tests.agent.private_file_assertions import assert_private
from concurrent.futures import ThreadPoolExecutor
import json

from packages.agent import logs
from packages.agent.tracing import ExecutionTrace, current_trace, emit, export
from scripts.agent_logs import main


def test_events_are_written_before_turn_finishes_and_tokens_are_preserved(tmp_path, monkeypatch):
    monkeypatch.setattr(logs, 'log_dir', lambda: tmp_path)
    trace = ExecutionTrace('case', 'request')
    token = current_trace.set(trace)
    try:
        emit('turn', 'started')
        assert len(list(logs.records(tmp_path, 'events'))) == 1
        assert not (tmp_path / 'runs.jsonl').exists()
        emit('model.usage', usage={'prompt_tokens': 25, 'completion_tokens': 10, 'total_tokens': 35}, api_key='PRIVATE')
        emit('turn', 'completed', status_code='draft_ready')
        export(trace)
    finally:
        current_trace.reset(token)
    run = list(logs.records(tmp_path, 'runs'))[0]
    assert run['usage']['total_tokens'] == 35 and 'events' not in run
    assert 'PRIVATE' not in (tmp_path / 'events.jsonl').read_text()


def test_rotation_and_concurrent_writes_leave_valid_private_jsonl(tmp_path, monkeypatch):
    monkeypatch.setattr(logs, 'log_dir', lambda: tmp_path)
    monkeypatch.setattr(logs, 'MAX_BYTES', 500)
    def write(number):
        logs.append('events', {'trace_id': str(number), 'seq': number, 'data': 'x' * 40})
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(write, range(60)))
    files = list(tmp_path.glob('events*.jsonl'))
    assert len(files) == logs.BACKUPS + 1
    for path in files:
        assert_private(path)
        assert all(json.loads(line)['trace_id'] for line in path.read_text().splitlines())
    retained = list(logs.records(tmp_path, 'events'))
    assert 0 < len(retained) < 60


def test_log_write_failure_does_not_interrupt_agent_execution(tmp_path, monkeypatch):
    blocker = tmp_path / 'not-a-directory'
    blocker.write_text('fixture')
    monkeypatch.setattr(logs, 'log_dir', lambda: blocker)
    trace = ExecutionTrace('case', 'request')
    trace.emit('turn', 'started')
    trace.emit('turn', 'completed')
    export(trace)
    assert trace.events[-1]['status'] == 'completed'


def test_reader_and_cli_filter_timeline_errors_and_compute_statistics(tmp_path, capsys):
    events = [
        {'trace_id': 'one', 'case_id': 'case-a', 'request_id': 'r1', 'seq': 1, 'elapsed_ms': 2,
         'name': 'tool.proposed', 'status': 'info', 'data': {'tool': 'search_law'}},
        {'trace_id': 'one', 'case_id': 'case-a', 'request_id': 'r1', 'seq': 2, 'elapsed_ms': 3,
         'name': 'tool.guard', 'status': 'rejected', 'data': {'reason_code': 'tool_scope_rejected'}},
        {'trace_id': 'two', 'case_id': 'case-b', 'request_id': 'r2', 'seq': 1, 'elapsed_ms': 4,
         'name': 'node.route', 'status': 'completed', 'data': {'duration_ms': 4}},
    ]
    runs = [
        {'trace_id': 'one', 'case_id': 'case-a', 'request_id': 'r1', 'status': 'error', 'duration_ms': 10,
         'model_calls': 2, 'tools': ['search_law'], 'usage': {'total_tokens': 30}, 'rejected_events': 1},
        {'trace_id': 'two', 'case_id': 'case-b', 'request_id': 'r2', 'status': 'completed', 'duration_ms': 4,
         'model_calls': 1, 'tools': [], 'usage': {'total_tokens': 10}},
    ]
    (tmp_path / 'events.jsonl').write_bytes(('\n'.join(json.dumps(e) for e in events)+'\n').encode()+b'{"broken": "\xe4')
    (tmp_path / 'runs.jsonl').write_text('\n'.join(json.dumps(r) for r in runs))
    main(['show', '--directory', str(tmp_path), '--trace-id', 'one', '--errors', '--json'])
    result = json.loads(capsys.readouterr().out)
    assert len(result) == 1 and result[0]['name'] == 'tool.guard'
    main(['stats', '--directory', str(tmp_path), '--json'])
    result = json.loads(capsys.readouterr().out)
    assert result['runs'] == 2 and result['model_calls'] == 3
    assert result['reported_token_usage']['total_tokens'] == 40
    assert result['rejection_counts'] == {'tool_scope_rejected': 1}
    assert result['node_mean_ms'] == {'node.route': 4}


def test_logging_does_not_write_record_when_permissions_cannot_be_set(tmp_path, monkeypatch):
    monkeypatch.setattr(logs, 'log_dir', lambda: tmp_path)
    real = logs.make_private
    def fail_for_file(path, *, directory=False):
        if not directory:
            raise OSError('permission unavailable')
        return real(path, directory=True)
    monkeypatch.setattr(logs, 'make_private', fail_for_file)
    logs.append('events', {'trace_id': 'must-not-be-written'})
    path=tmp_path/'events.jsonl'
    assert not path.exists() or path.read_text(encoding='utf-8')==''


def test_existing_log_and_directory_are_secured_before_append(tmp_path, monkeypatch):
    monkeypatch.setattr(logs, 'log_dir', lambda: tmp_path)
    path=tmp_path/'events.jsonl'
    path.write_text('{"trace_id":"old"}\n',encoding='utf-8')
    logs.append('events', {'trace_id': 'new'})
    assert_private(path)
    assert_private(tmp_path)
    assert [r['trace_id'] for r in logs.records(tmp_path,'events')]==['old','new']
