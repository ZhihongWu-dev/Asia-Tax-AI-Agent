"""Real configured model/cloud retrieval, synthetic cases, isolated conversation store.

Makes paid model requests. Does not test HTTP authentication or certify tax answers.
"""
import argparse
import asyncio
import json
from pathlib import Path
import sys
import tempfile
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from packages.chat.service import ChatService, WorkflowError, current_model_config
from packages.chat.store import ChatStore
from packages.chat.streaming import events


def case_flow(service, owner, doc):
    """Verify confirmation, real rules/citations, replay, and stale-result handling."""
    try:
        service.run(owner, doc['id'], doc['revision'], str(uuid4()))
    except WorkflowError as exc:
        assert exc.code == 'confirmation_required'
    else:
        raise AssertionError('Unconfirmed analysis was allowed')
    confirmed = service.confirm(owner, doc['id'], doc['revision'], str(uuid4()))
    request = str(uuid4())
    result = service.run(owner, doc['id'], confirmed['revision'], request)
    replay = service.run(owner, doc['id'], confirmed['revision'], request)
    # Dataclass tuples become JSON arrays at the API/store boundary.
    assert replay == json.loads(json.dumps(result)) and len(result['analyses']) == 1
    analysis = result['analyses'][-1]
    assert result['state'] == 'review_required'
    assert analysis['professional_validation_status'] == 'unverified'
    assert analysis['facts_snapshot'] == confirmed['confirmed_facts']
    assert analysis['retrieval_status'] == 'available' and analysis['passages']
    assert not analysis['missing_locators'], analysis['missing_locators']
    ids = {p['unit_id'] for p in analysis['passages']}
    assert all(set(n['passage_ids']) <= ids for n in analysis['nodes'])
    assert analysis['review_tasks'] and analysis['missing_nodes']
    changed = service.edit(owner, doc['id'], result['revision'], str(uuid4()), {'holding_percentage_pct': 20})
    assert changed['confirmed_revision'] is None and changed['confirmed_facts'] is None
    assert changed['analyses'][-1]['stale'] is True
    return {'status': 'passed', 'analysis': analysis,
            'checks': ['confirmation_required', 'idempotent_run', 'review_required', 'frozen_facts',
                       'cloud_citations', 'missing_nodes_visible', 'edit_invalidates_confirmation_and_result']}


async def evaluate(output, only=None):
    cases = json.loads((ROOT / 'tests/chat/conversation_cases.json').read_text(encoding='utf-8'))
    if only:
        selected = set(only.split(','))
        if selected - {c['id'] for c in cases}:
            raise ValueError('Unknown test ID')
        cases = [c for c in cases if c['id'] in selected]
    rows, docs = [], {}
    owner = 'evaluation:' + str(uuid4())
    report = {'method': 'Real streaming.events / configured model and cloud knowledge; synthetic facts; temporary SQLite conversation store. No HTTP/auth/browser or expert tax validation.',
              'model': current_model_config().model_name, 'rows': rows}
    output.parent.mkdir(parents=True, exist_ok=True)
    def save():
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    with tempfile.TemporaryDirectory(prefix='taxora-eval-') as td:
        service = ChatService(ChatStore('sqlite:///' + Path(td).as_posix() + '/sessions.sqlite'))
        try:
            for case in cases:
                doc = docs.get(case['session']) or service.store.create(owner)
                before = {m['id'] for m in doc['messages']}
                row = dict(case)
                start, first, partial, result = time.perf_counter(), None, '', None
                async def connected(): return False
                try:
                    async with asyncio.timeout(90):
                        async for event in events(service, doc, owner, doc['revision'], str(uuid4()), case['prompt'], connected):
                            if event['type'] == 'reset':
                                partial = ''
                            elif event['type'] == 'delta':
                                if first is None:
                                    first = time.perf_counter() - start
                                partial += event['text']
                            elif event['type'] == 'done':
                                result = event['case']
                    if result is None:
                        raise RuntimeError('no_final_result')
                    docs[case['session']] = service.store.get(owner, doc['id'])
                    row.update(status='completed', messages=[m for m in result['messages'] if m['id'] not in before and m['role'] == 'assistant'], facts=result['facts'], state=result['state'])
                except Exception as exc:
                    row.update(status='failed', error=getattr(exc, 'code', type(exc).__name__), messages=[], facts={})
                row.update(seconds=round(time.perf_counter() - start, 3), first_seconds=round(first, 3) if first is not None else None, partial=partial)
                rows.append(row)
                save()
                print(row['id'], row['status'], row['seconds'], flush=True)
            if 'S10' in docs:
                try:
                    report['case_flow'] = await asyncio.to_thread(case_flow, service, owner, docs['S10'])
                except Exception as exc:
                    report['case_flow'] = {'status': 'failed', 'error': getattr(exc, 'code', type(exc).__name__)}
            elif only:
                report['case_flow'] = {'status': 'not_run', 'reason': 'no_intake_session_selected'}
            else:
                report['case_flow'] = {'status': 'failed', 'error': 'missing_intake_session'}
            save()
        finally:
            service.store.engine.dispose()
    return (all(r['status'] == 'completed' and all(m.get('research', {}).get('answer_status') != 'summary_unavailable'
                for m in r['messages']) for r in rows) and report['case_flow']['status'] in ('passed', 'not_run'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--only', help='Comma-separated test IDs; include prior turns for follow-up questions')
    args = parser.parse_args()
    sys.exit(0 if asyncio.run(evaluate(args.output, args.only)) else 1)
