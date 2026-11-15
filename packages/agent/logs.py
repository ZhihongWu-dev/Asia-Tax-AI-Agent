"""Private rotating JSONL sinks and local analysis for agent execution logs."""
from collections import Counter
from contextlib import contextmanager
import json
import logging
from math import ceil
import os
from pathlib import Path
from threading import Lock

ROOT = Path(__file__).resolve().parents[2]
MAX_BYTES = 5_000_000
BACKUPS = 3
_lock = Lock()


def log_dir():
    setting = os.environ.get('FSIE_AGENT_LOG_DIR', 'data/local-setup/agent-logs')
    if setting.lower() in ('off', 'disabled', 'none'):
        return None
    path = (ROOT / setting).resolve()
    if not path.is_relative_to((ROOT / 'data').resolve()):
        raise ValueError('Agent log directory must be inside project data/')
    return path


@contextmanager
def writer_lock(directory):
    # Threads share the process lock; Unix workers also share an advisory file lock.
    with _lock:
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(directory / '.writer.lock', os.O_CREAT | os.O_RDWR, 0o600)
        try:
            try:
                import fcntl
            except ImportError:
                fcntl = None
            if fcntl:
                fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            if fcntl:
                fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)


def append(kind, record):
    """Best effort: a logging failure must never change business state."""
    if kind not in ('events', 'runs'):
        raise ValueError('Unknown log stream')
    try:
        directory = log_dir()
        if directory is None:
            return
        data = json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n'
        path = directory / (kind + '.jsonl')
        with writer_lock(directory):
            if path.exists() and path.stat().st_size + len(data.encode('utf-8')) > MAX_BYTES:
                for index in range(BACKUPS, 0, -1):
                    target = directory / f'{kind}.{index}.jsonl'
                    source = path if index == 1 else directory / f'{kind}.{index-1}.jsonl'
                    if source.exists():
                        source.replace(target)
            fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600)
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                if hasattr(os, 'fchmod'):
                    os.fchmod(stream.fileno(), 0o600)
                stream.write(data)
    except (OSError, ValueError, TypeError) as exc:
        logging.getLogger(__name__).warning('Agent logging unavailable: %s', type(exc).__name__)


def summarize(trace):
    events = trace['events']
    terminal = next((e for e in reversed(events) if e['name'] == 'turn'), {})
    usage = Counter()
    for event in events:
        if event['name'] == 'model.usage':
            usage.update({k: v for k, v in event['data'].get('usage', {}).items()
                          if isinstance(v, int) and v >= 0})
    return {'version': '2.0', 'kind': 'run',
            **{key: trace[key] for key in ('trace_id', 'case_id', 'request_id', 'dropped_events')},
            'started_at': events[0]['at'] if events else None,
            'finished_at': terminal.get('at'), 'status': terminal.get('status', 'incomplete'),
            'result_status': terminal.get('data', {}).get('status_code'),
            'reason_code': terminal.get('data', {}).get('reason_code'),
            'error_code': terminal.get('data', {}).get('error_code'),
            'error_type': terminal.get('data', {}).get('error_type'),
            'duration_ms': terminal.get('elapsed_ms'), 'event_count': len(events),
            'model_calls': sum(e['name'] == 'model.call' and e['status'] == 'started' for e in events),
            'model_requests': sum(e['name'] == 'model.request' and e['status'] == 'started' for e in events),
            'tools': [e['data']['tool'] for e in events if e['name'] == 'tool.executing'],
            'rejected_events': sum(e['status'] == 'rejected' for e in events),
            'usage': dict(usage), 'budget': terminal.get('data', {}).get('budget')}


def records(directory, kind):
    """Read retained volumes in chronological order; ignore incomplete final lines."""
    directory = Path(directory)
    for name in [f'{kind}.{i}.jsonl' for i in range(BACKUPS, 0, -1)] + [f'{kind}.jsonl']:
        try:
            with (directory / name).open(encoding='utf-8', errors='replace') as stream:
                for line in stream:
                    try:
                        value = json.loads(line)
                        if isinstance(value, dict) and value.get('trace_id'):
                            yield value
                    except (ValueError, UnicodeError):
                        continue
        except FileNotFoundError:
            continue


def matches(record, trace_id=None, case_id=None, request_id=None):
    return all(value is None or record.get(key) == value for key, value in
               (('trace_id', trace_id), ('case_id', case_id), ('request_id', request_id)))


def statistics(runs, events):
    runs, events = list(runs), list(events)
    durations = sorted(r['duration_ms'] for r in runs if isinstance(r.get('duration_ms'), (int, float)))
    def percentile(p):
        return round(durations[max(0, ceil(len(durations)*p)-1)], 2) if durations else None
    node_totals, node_counts = Counter(), Counter()
    for event in events:
        if event.get('name', '').startswith('node.') and event.get('status') in ('completed', 'error'):
            duration = event.get('data', {}).get('duration_ms')
            if isinstance(duration, (int, float)):
                node_totals[event['name']] += duration
                node_counts[event['name']] += 1
    return {'runs': len(runs), 'status_counts': dict(Counter(r.get('status', 'unknown') for r in runs)),
            'result_status_counts': dict(Counter(r.get('result_status') or r.get('error_code') or 'unknown' for r in runs)),
            'model_calls': sum(r.get('model_calls', 0) for r in runs),
            'tool_counts': dict(Counter(tool for r in runs for tool in r.get('tools', []))),
            'rejection_counts': dict(Counter(e.get('data', {}).get('reason_code') or e.get('name')
                for e in events if e.get('status') == 'rejected')),
            'duration_ms': {'p50': percentile(.5), 'p95': percentile(.95), 'max': durations[-1] if durations else None},
            'node_mean_ms': {name: round(node_totals[name]/node_counts[name], 2) for name in node_counts},
            'reported_token_usage': dict(sum((Counter(r.get('usage', {})) for r in runs), Counter()))}
