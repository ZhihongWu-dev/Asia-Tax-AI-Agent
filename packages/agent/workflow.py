"""Bounded per-turn LangGraph. All durable writes remain in ChatService."""
from __future__ import annotations
from copy import deepcopy
from time import monotonic
from typing import TypedDict
from uuid import uuid4

from langgraph.graph import StateGraph, START, END
from packages.agent.contracts import SearchRequest, TrustedContext
from packages.agent.knowledge import retrieve, compose_answer, validate_answer
from packages.chat.facts import validate_patch, raw_facts
from packages.agent import dialogue


class TurnState(TypedDict, total=False):
    doc: dict
    text: str
    owner: str
    request_id: str
    turn: dict
    patch: dict
    conflicts: dict
    research: dict | None
    answer: dict | None
    workflow: dict
    dialogue: dict
    question: dict | None


class TurnWorkflow:
    def __init__(self, provider, turner):
        self.provider, self.turner = provider, turner
        graph = StateGraph(TurnState)
        for name, action in [('route', self.route), ('facts', self.facts), ('retrieve', self.retrieve),
                             ('compose', self.compose), ('validate', self.validate)]:
            def timed(state, action=action, name=name):
                started = monotonic()
                update = action(state)
                meta = deepcopy(update.get('workflow', state.get('workflow', {})))
                meta.setdefault('trace', []).append(name)
                meta.setdefault('timings_ms', {})[name] = round((monotonic() - started) * 1000, 2)
                return {**update, 'workflow': meta}
            graph.add_node(name, timed)
        graph.add_edge(START, 'route')
        graph.add_edge('route', 'facts')
        graph.add_conditional_edges('facts', lambda s: 'retrieve' if s['turn']['intent'] == 'research' else 'validate')
        graph.add_edge('retrieve', 'compose')
        graph.add_edge('compose', 'validate')
        graph.add_edge('validate', END)
        self.graph = graph.compile()

    def invoke(self, doc, text, owner, request_id, turn=None):
        return self.graph.invoke({'doc': deepcopy(doc), 'text': text, 'owner': owner, 'request_id': request_id,
            **({'turn': turn} if turn is not None else {}),
            'workflow': {'version': '0.2.0', 'trace_id': str(uuid4()), 'status': 'ready', 'reason_code': None}},
            {'recursion_limit': 10})

    def route(self, state):
        turn = deepcopy(dialogue.deterministic_turn(state['doc'], state['text']) or state.get('turn') or self.turner(state['doc'], state['text']))
        if turn['intent'] not in ('chat', 'research', 'intake', 'clarify', 'unsupported'):
            raise ValueError('Unknown intent')
        if turn['intent'] in ('chat', 'clarify', 'unsupported') and turn['facts']:
            raise ValueError('Non-case route cannot mutate facts')
        return {'turn': turn, 'research': None, 'answer': None}

    def facts(self, state):
        turn = deepcopy(state['turn'])
        action = turn.get('action', 'continue')
        doc = state['doc']
        previous_dialogue = doc.get('dialogue', {})
        patch = validate_patch(turn['facts'])
        old = raw_facts(doc)
        pending = previous_dialogue.get('pending')
        # New transaction belongs in a separate case, irrespective of extracted fields.
        if action == 'new_case':
            patch = {}
            turn['intent'] = 'intake'
        if action in ('unknown', 'unavailable'):
            if pending and previous_dialogue.get('status') == 'active':
                if not patch and pending.get('field') and action == 'unknown' and old.get(pending['field']) != 'conflict':
                    patch[pending['field']] = 'unknown'
            else:
                patch = {}
                turn['intent'] = 'clarify'
                turn['action'] = 'continue'
        if action == 'partial':
            # A model-labelled action alone cannot authorize a partial case result.
            if not dialogue.explicit_partial_request(state['text']):
                turn['action'] = 'continue'
                turn['intent'] = 'clarify'
        if action == 'summary':
            patch = {}
            if not dialogue.explicit_summary_request(state['text']):
                turn.update(action='continue', intent='clarify')
        authorized = dialogue.correction_fields(turn, state['text'], doc)
        conflicts = {}
        for key, value in list(patch.items()):
            if old.get(key) == value:
                del patch[key]
            elif old.get(key) == 'conflict' and value == 'unknown':
                # Inability to resolve competing values never resolves the conflict.
                del patch[key]
                if pending and pending.get('field') == key:
                    turn['action'] = 'unavailable'
            elif key in old and old[key] not in (None, 'unknown') and value not in (None, 'unknown', 'conflict') and key not in authorized and key not in ('consultation_goal', 'analysis_jurisdiction'):
                previous = doc.get('fact_conflicts', {}).get(key, {}).get('previous', old[key]) if old[key] == 'conflict' else old[key]
                conflicts[key] = {'previous': previous, 'candidate': value}
                patch[key] = 'conflict'
        projected = deepcopy(doc)
        for key, value in patch.items():
            if value is None:
                projected['facts'].pop(key, None)
            else:
                projected['facts'][key] = {'value': value}
            projected.setdefault('fact_conflicts', {}).pop(key, None)
        projected.setdefault('fact_conflicts', {}).update(conflicts)
        known = raw_facts(projected)
        meta = deepcopy(state['workflow'])
        active_conflicts = [k for k, v in known.items() if v == 'conflict']
        case_request = turn['intent'] == 'intake' or bool(patch) or turn.get('uses_case', False)
        if turn['intent'] == 'unsupported' or (case_request and action not in ('pause', 'new_case', 'summary') and not dialogue.supported(known)):
            turn['intent'] = 'unsupported'
            turn['reply'] = '目前案件分析仅支持香港境外股息 FSIE 的企业场景。本次问题超出已实现的能力范围，已记录范围缺口。'
            meta.update(status='unsupported', reason_code='out_of_scope')
        elif active_conflicts and case_request and action not in ('partial', 'pause', 'new_case', 'unknown', 'unavailable'):
            if turn['intent'] == 'research':
                projected.setdefault('dialogue', {})['deferred_query'] = turn['query']
            turn['intent'] = 'intake'
            meta.update(status='waiting_user', reason_code='fact_conflict')
        elif action in ('resume', 'retry_research') and previous_dialogue.get('deferred_query') and not active_conflicts:
            turn.update(intent='research', query=previous_dialogue['deferred_query'], uses_case=True)
        elif turn['intent'] == 'chat':
            meta.update(status='completed', reason_code='ordinary_chat')
        turn['facts'] = patch
        interview, question, reply = dialogue.update_dialogue(projected, turn, patch)
        turn['reply'] = reply
        if question:
            meta.update(status='waiting_user', reason_code='fact_conflict' if active_conflicts and question.get('field') else
                        'information_gap_choice' if question['kind'] == 'choice' else
                        'intent_unclear' if question['kind'] == 'mode' else 'fact_collection')
        elif turn['intent'] == 'intake' and turn.get('action') != 'summary':
            meta.update(status='partial_ready' if interview['status'] == 'partial' else
                        'paused' if interview['status'] in ('paused', 'suspended') else 'awaiting_confirmation',
                        reason_code='partial_requested' if interview['status'] == 'partial' else 'fact_collection')
        if turn.get('action') == 'summary':
            meta.update(status='completed', reason_code='facts_summarized')
        meta['identification'] = dialogue.identification(projected)
        return {'turn': turn, 'patch': patch, 'conflicts': conflicts, 'workflow': meta,
                'dialogue': interview, 'question': question}

    def retrieve(self, state):
        uses_case = bool(state['patch']) or state['turn'].get('uses_case', False)
        facts = {k: v for k, v in {**raw_facts(state['doc']), **state['patch']}.items() if v is not None} if uses_case else {}
        date, date_status = dialogue.query_date(facts) if uses_case else (None, 'not_needed')
        request = SearchRequest(request_id=state['request_id'], trace_id=state['workflow']['trace_id'],
            query=state['turn']['query'][:500], applicable_date=date,
            date_status=date_status,
            intent='case_analysis' if uses_case else 'reference_lookup', income_type=facts.get('income_type'),
            entity_type=facts.get('recipient_type') if facts.get('recipient_type') in ('individual', 'company', 'unknown') else 'not_needed',
            fact_filters=[{'field_name': key, 'value': facts[key]} for key in
                          ('income_type', 'source_analysis', 'entity_hk_business_status', 'receipt_location', 'recipient_type')
                          if isinstance(facts.get(key), str) and facts[key] not in ('unknown', 'conflict')])
        bundle = retrieve(self.provider, request, TrustedContext(owner=state['owner'], case_id=state['doc']['id']))
        interview = deepcopy(state['dialogue'])
        if bundle['status'] == 'unavailable':
            if not state['patch']:
                from packages.chat.service import WorkflowError
                raise WorkflowError('knowledge_unavailable')
            interview['deferred_query'] = state['turn']['query']
        elif uses_case and interview.get('deferred_query') == state['turn']['query']:
            interview.pop('deferred_query', None)
        if uses_case:
            from packages.chat.facts import catalog
            labels = {f['field_name']: f['description_zh'] for f in catalog()}
            bundle['gaps'] += [labels.get(g['field'], g['field']) + '：' + g['reason'] + '；' + g['impact'] for g in
                              dialogue.gaps({**state['doc'], 'facts': {k: {'value': v} for k, v in facts.items()}, 'dialogue': interview})[:3]]
        bundle['query_context'] = {'applicable_date': date, 'date_status': request.date_status,
                                   'jurisdiction': request.jurisdiction, 'uses_case': uses_case}

        meta = deepcopy(state['workflow'])
        meta.update(status='draft_ready' if bundle['reason_code'] == 'evidence_available' else 'paused_gap',
                    reason_code=bundle['reason_code'], retrieval_calls=bundle['retrieval_calls'])
        if bundle['status'] == 'unavailable':
            meta.update(status='partial_failure', reason_code='retrieval_failed', error_code='knowledge_unavailable', retryable=True)
        return {'research': bundle, 'workflow': meta, 'dialogue': interview}

    def compose(self, state):
        answer = compose_answer(state['research'])
        turn = deepcopy(state['turn'])
        turn['reply'] = answer['text']
        if state['patch']:
            turn['reply'] = '本次案情修订已保存，旧分析如受影响需重新确认。\n\n' + turn['reply']
        if state['research']['status'] == 'unavailable':
            turn['reply'] += '\n可回复“重试检索”继续查询；已保存事实不会重复写入。'
        update = {'turn': turn, 'answer': answer}
        if state['research']['status'] != 'unavailable' and (state['patch'] or turn.get('uses_case', False)):
            projected = deepcopy(state['doc'])
            for key, value in state['patch'].items():
                if value is None:
                    projected['facts'].pop(key, None)
                else:
                    projected['facts'][key] = {'value': value}
            projected['dialogue'] = state['dialogue']
            interview, question, followup = dialogue.update_dialogue(projected, {**turn, 'intent': 'intake', 'action': 'continue'}, {})
            update.update(dialogue=interview, question=question)
            if question:
                turn['reply'] += '\n\n' + followup
                meta = deepcopy(state['workflow'])
                meta.update(status='waiting_user', retrieval_reason_code=meta['reason_code'],
                            reason_code='information_gap_choice' if question['kind'] == 'choice' else 'fact_collection')
                update['workflow'] = meta
        return update

    def validate(self, state):
        if state['answer'] is not None:
            validate_answer(state['answer'], state['research'])
        return {}
