"""Task ownership and request-scoped safe projections of durable dialogue."""
from copy import deepcopy
from hashlib import sha256
import json
from uuid import uuid4

VERSION = 'hybrid-0.1'
HINT_TASK = {'dividend_consultation': 'consultation', 'fact_intake': 'fact_intake',
             'reference_lookup': 'reference_lookup'}


def payload_hash(text, approved, entry_hint='auto', reply_to_question_id=None):
    return sha256(json.dumps({'operation': 'messages', 'text': text, 'data_approved': approved,
        'entry_hint': entry_hint, 'reply_to_question_id': reply_to_question_id}, sort_keys=True).encode()).hexdigest()


def project(doc):
    """No source passages, answer text, model-only content or customer payload log."""
    data = deepcopy(doc.get('orchestration', {}))
    return {k: data.get(k) for k in ('schema_version', 'active_task', 'suspended_task', 'queued_tasks')}


def new_task(kind, uses_case, origin='auto'):
    return {'id': str(uuid4()), 'kind': kind, 'uses_case': uses_case, 'origin': origin, 'status': 'active'}


def legacy_projection(doc):
    """Freeze hybrid-only pending semantics when the server returns to legacy."""
    copy = deepcopy(doc)
    control = copy.get('orchestration')
    if not control:
        return copy, False
    active = control.get('active_task')
    pending = copy.get('dialogue', {}).get('pending')
    hybrid_pending = pending and pending['id'].startswith('hybrid:')
    freeze = bool(control.get('queued_tasks') or hybrid_pending or active and active.get('status') == 'paused')
    if freeze:
        copy.setdefault('dialogue', {})['status'] = 'suspended'
        if active:
            active['status'] = 'paused'
    return copy, freeze


def resolve(doc, turn, hint, proposals):
    state = deepcopy(doc.get('orchestration', {}))
    state.setdefault('schema_version', '0.1.0')
    state.setdefault('active_task', None)
    state.setdefault('suspended_task', None)
    state.setdefault('queued_tasks', [])
    active = state['active_task']
    intent, action = turn['intent'], turn.get('action', 'continue')
    if action == 'summary':
        return state
    if action == 'resume' and state['suspended_task']:
        active, state['suspended_task'] = state['suspended_task'], None
    if intent in ('chat', 'clarify', 'unsupported') or action in ('pause', 'new_case'):
        if active:
            active['status'] = 'paused' if intent == 'chat' or action in ('pause', 'new_case') else 'blocked_gap'
        state['active_task'] = active
        return state
    pending = doc.get('dialogue', {}).get('pending')
    # A clear answer continues its task; an explicit new task can supersede a hint.
    kind = proposals[0]['kind'] if proposals else ('reference_lookup' if intent == 'research' else
        active['kind'] if active and active['kind'] in ('fact_intake', 'consultation') else
        HINT_TASK.get(hint, 'fact_intake'))
    if pending and doc.get('dialogue', {}).get('status') == 'active' and turn.get('facts') and not proposals and intent == 'intake':
        kind = active['kind'] if active and active['kind'] != 'reference_lookup' else HINT_TASK.get(hint, 'fact_intake')
    if active and active['kind'] != kind and active.get('status') not in ('completed', 'failed'):
        if state['suspended_task'] and state['suspended_task']['id'] != active['id']:
            from packages.chat.service import WorkflowError
            raise WorkflowError('task_focus_required')
        active['status'] = 'paused'
        state['suspended_task'] = active
        active = None
    if not active or active['kind'] != kind or active.get('status') in ('completed', 'failed'):
        active = new_task(kind, bool(turn.get('facts')) or turn.get('uses_case', False) or intent == 'intake',
                          'shortcut' if hint != 'auto' else 'auto')
    active['status'] = 'active'
    state['active_task'] = active
    if proposals:
        state['queued_tasks'] = deepcopy(proposals[1:])
    return state
