"""Shared guarded subgraphs and bounded dynamic scheduling; pure proposals only."""
from copy import deepcopy
from uuid import uuid4
from langgraph.graph import StateGraph, START, END

from packages.agent import dialogue, task_state
from packages.agent.workflow import TurnState, TurnWorkflow
from packages.agent.task_contracts import NextAction, TaskProposal
from packages.agent.budget import RunBudget, BudgetedProvider, BudgetExceeded, current_budget, model_call
from packages.agent.contracts import SearchRequest, TrustedContext
from packages.agent.knowledge import retrieve, compose_answer, validate_answer
from packages.chat.facts import raw_facts


class HybridState(TurnState, total=False):
    orchestration: dict
    entry_hint: str
    job: dict
    task_results: list
    analysis_result: dict | None
    next_action: str
    rewrite_count: int
    answers: list
    research_results: list


SHORTCUTS = {
    '分析境外股息的 FSIE 处理，需要先确认哪些事实？': ('consultation', '香港境外股息FSIE分析所需事实与官方资料'),
    '帮我整理境外股息分析所需的案例事实和证据清单。': ('fact_intake', '香港境外股息FSIE案例事实及证据要求'),
    '研究境外股息的 FSIE 处理，应当查阅哪些官方资料？': ('reference_lookup', '香港境外股息FSIE官方资料'),
    'What facts should we confirm first when researching FSIE treatment of foreign dividends?': ('consultation', '香港境外股息FSIE官方资料'),
    'What facts should be confirmed first when analyzing foreign dividends under FSIE?': ('consultation', '香港境外股息FSIE官方资料'),
    'Which facts should we confirm before analyzing foreign dividends under FSIE?': ('consultation', '香港境外股息FSIE官方资料'),
    'Help me organize the facts and evidence needed to analyze foreign dividends.': ('fact_intake', '香港境外股息FSIE事实及证据要求'),
    'Which official sources should we consult when researching foreign dividends under FSIE?': ('reference_lookup', '香港境外股息FSIE官方资料'),
}


def requested_analysis(text):
    return not any(x in text.casefold() for x in ('不要', '不用', '不需要', '什么是', '如何', 'don\'t', 'do not', 'what is')) and \
        any(x in text.casefold() for x in ('开始分析', '生成研究稿', '生成分析', 'start analysis', 'generate analysis'))


class HybridWorkflow(TurnWorkflow):
    def __init__(self, provider, turner, analyzer, dynamic=False, planner=None,
                 harness_mode='rewrite', tool_planner=None):
        self.original_provider, self.original_turner = provider, turner
        self.analyzer, self.dynamic = analyzer, dynamic
        self.harness_mode, self.tool_planner = harness_mode, tool_planner
        from packages.agent.harness import plan_next
        self.planner = planner or plan_next
        self.graph = self.build_graph()

    def timed(self, name, callback):
        def run(state):
            from time import monotonic
            started = monotonic()
            result = callback(state)
            meta = deepcopy(result.get('workflow', state.get('workflow', {})))
            meta.setdefault('trace', []).append(name)
            meta.setdefault('timings_ms', {})[name] = round((monotonic() - started) * 1000, 2)
            return {**result, 'workflow': meta}
        return run

    def build_graph(self):
        # Each business path is a compiled graph; facts/policy are shared before dispatch.
        parent = StateGraph(HybridState)
        parent.add_node('route', self.timed('route', self.route))
        parent.add_node('facts', self.timed('facts', self.facts))
        for kind in ('consultation', 'fact_intake', 'reference_lookup'):
            child = StateGraph(HybridState)
            child.add_node('execute', self.timed(kind, self.execute))
            child.add_edge(START, 'execute')
            child.add_edge('execute', END)
            parent.add_node(kind, child.compile())
        parent.add_node('observe', self.timed('observe', self.observe))
        parent.add_node('tool_harness', self.timed('tool_harness', self.run_tools))
        parent.add_node('validate', self.timed('validate', self.validate))
        parent.add_edge(START, 'route')
        parent.add_edge('route', 'facts')
        parent.add_conditional_edges('facts', self.path)
        for kind in ('consultation', 'fact_intake', 'reference_lookup'):
            parent.add_edge(kind, 'observe')
        parent.add_edge('tool_harness', 'observe')
        parent.add_conditional_edges('observe', lambda s: s['next_action'])
        parent.add_edge('validate', END)
        return parent.compile()

    def path(self, state):
        if state['turn'].get('action') == 'summary':
            return 'validate'
        if state['turn']['intent'] in ('chat', 'clarify', 'unsupported') or state['turn'].get('action') in ('pause', 'new_case'):
            return 'validate'
        if state.get('question') and state['turn']['intent'] != 'research':
            return 'validate'
        if (self.dynamic and self.harness_mode == 'tools' and state['entry_hint'] == 'auto'
                and state['turn'].get('action', 'continue') in ('continue', 'resume', 'retry_research')):
            return 'tool_harness'
        return state['job']['kind']

    def run_tools(self, state):
        from packages.agent.tool_harness import ToolHarness
        from packages.agent.analysis_policy import analysis_eligibility
        # The router may already have decomposed an explicit multi-task request.
        # Execute that queue once; do not let another planner duplicate its jobs.
        if state['orchestration'].get('queued_tasks'):
            return self.execute(state)
        # Missing scope and analysis preconditions use the same established
        # clarification/status messages, rather than asking a planner to override.
        if requested_analysis(state['text']) and (state['patch'] or analysis_eligibility(self.projected(state))):
            return self.execute(state)
        if state['job'].get('query') and self.scope(state, state['job']) != 'HK':
            return self.execute(state)
        return ToolHarness(self, self.tool_planner).invoke(state)

    def invoke(self, doc, text, owner, request_id, turn=None, entry_hint='auto'):
        self.budget = RunBudget()
        self.provider = BudgetedProvider(self.original_provider, self.budget, dialogue.fingerprint(doc))
        token = current_budget.set(self.budget)
        try:
            return self.graph.invoke({'doc': deepcopy(doc), 'text': text, 'owner': owner, 'request_id': request_id,
                'entry_hint': entry_hint, 'task_results': [], 'answers': [], 'research_results': [], 'rewrite_count': 0,
                'analysis_result': None, **({'turn': turn} if turn is not None else {}),
                'workflow': {'version': '0.3.0', 'policy_version': task_state.VERSION, 'trace_id': str(uuid4()),
                             'status': 'ready', 'reason_code': None}}, {'recursion_limit': 40})
        except BudgetExceeded:
            from packages.chat.service import WorkflowError
            raise WorkflowError('execution_budget_exhausted') from None
        finally:
            current_budget.reset(token)

    def route(self, state):
        from packages.chat.service import plan_turn, validate_turn, WorkflowError
        doc = deepcopy(state['doc'])
        doc['_entry_hint'] = state['entry_hint']
        parsed = dialogue.deterministic_turn(doc, state['text'])
        pending = doc.get('dialogue', {}).get('pending')
        if pending and doc.get('dialogue', {}).get('status') == 'active' and pending['id'].startswith('hybrid:scope:') and \
                dialogue.normalize(state['text']) in ('香港', 'hong kong', 'hk'):
            active = doc.get('orchestration', {}).get('active_task') or {}
            parsed = {'intent': 'research', 'facts': {}, 'query': '香港 ' + active.get('query', '股息规定'),
                      'reply': '将按香港范围查阅。', 'uses_case': False, 'task_kind': 'reference_lookup'}
        if not parsed and state['entry_hint'] != 'auto' and state['text'] in SHORTCUTS:
            kind, query = SHORTCUTS[state['text']]
            parsed = {'intent': 'research', 'facts': {}, 'query': query, 'reply': '将查阅所需资料。',
                      'uses_case': False, 'task_kind': kind}
        if not parsed:
            parsed = state.get('turn')
        if not parsed:
            parsed = self.original_turner(doc, state['text']) if self.original_turner is plan_turn else \
                model_call(self.original_turner, doc, state['text'])
        parsed = deepcopy(parsed)
        parsed['reply'] = parsed.get('reply') or '已收到本次请求。'
        try:
            parsed = validate_turn(parsed)
        except (ValueError, TypeError, KeyError):
            raise WorkflowError('model_failed') from None
        from packages.agent.policy import concrete_tax_claim
        if parsed['intent'] == 'chat' and concrete_tax_claim(parsed['reply']):
            parsed.update(intent='research', query=state['text'][:500], reply='具体税务条件须查阅依据。', uses_case=False)
        if parsed['intent'] == 'chat' and any(x in parsed['reply'] for x in ('报告已批准', '已完成最终复核', '批准通过')):
            parsed['reply'] = '报告批准须由有权限的顾问在最终复核环节完成；聊天不能批准报告。'
        if parsed.get('action') == 'retry_research' and doc.get('dialogue', {}).get('deferred_query'):
            parsed.update(intent='research', query=doc['dialogue']['deferred_query'],
                          uses_case=doc['dialogue'].get('deferred_query_uses_case', True), task_kind='reference_lookup')
        if parsed.get('action') == 'resume' and doc.get('orchestration', {}).get('queued_tasks') and \
                not (pending and pending.get('field') and doc.get('dialogue', {}).get('status') == 'active'):
            tasks = deepcopy(doc['orchestration']['queued_tasks'])
            first = tasks[0]
            parsed.update(intent='research' if first.get('query') else 'intake', query=first.get('query', ''),
                          uses_case=first.get('uses_case', False), task_kind=first['kind'], tasks=tasks)
        elif parsed.get('action') == 'resume':
            active = doc.get('orchestration', {}).get('active_task') or {}
            if active.get('kind') == 'reference_lookup' and active.get('status') != 'completed' and active.get('query'):
                parsed.update(intent='research', query=active['query'], uses_case=active.get('uses_case', False),
                              task_kind='reference_lookup')
        if requested_analysis(state['text']) and not parsed.get('tasks'):
            parsed['task_kind'] = 'consultation'
        proposals = parsed.get('tasks', [])
        if not proposals and parsed.get('task_kind'):
            proposals = [TaskProposal(kind=parsed['task_kind'], query=parsed['query'],
                                      uses_case=parsed.get('uses_case', False)).model_dump()]
        orchestration = task_state.resolve(doc, parsed, state['entry_hint'], proposals)
        active = orchestration['active_task']
        job = proposals[0] if proposals else {'kind': active['kind'] if active else 'consultation',
            'query': parsed['query'], 'uses_case': parsed.get('uses_case', bool(parsed['facts']))}
        if requested_analysis(state['text']) and not parsed.get('tasks'):
            job['kind'] = 'consultation'
        if parsed['intent'] == 'research':
            job['query'] = job.get('query') or parsed['query']
        if active:
            active['query'] = job.get('query', '')
        meta = deepcopy(state['workflow'])
        meta.update(entry_hint=state['entry_hint'], effective_task=job['kind'], dynamic_planner=self.dynamic)
        return {'turn': parsed, 'research': None, 'answer': None, 'orchestration': orchestration,
                'job': job, 'workflow': meta}

    def facts(self, state):
        result = super().facts(state)
        original = state['turn']
        # An independent reference task is not dependent on a conflicting case patch.
        independent = original['intent'] == 'research' and not original.get('uses_case', bool(original['facts']))
        if independent and result['turn']['intent'] in ('intake', 'unsupported'):
            parsed = deepcopy(original)
            parsed['facts'] = result['patch']
            result['turn'] = parsed
            result['dialogue'].pop('deferred_query', None)
        if independent:
            result['turn']['uses_case'] = False
        if result['question']:
            task = state['orchestration']['active_task']
            if task:
                result['question']['task_id'] = task['id']
        if requested_analysis(state['text']) and original.get('action', 'continue') == 'continue':
            result['question'] = None
        return result

    def projected(self, state):
        doc = deepcopy(state['doc'])
        for key, value in state['patch'].items():
            if value is None:
                doc['facts'].pop(key, None)
            else:
                doc['facts'][key] = {'value': value}
        doc['fact_conflicts'] = {**doc.get('fact_conflicts', {}), **state['conflicts']}
        doc['dialogue'] = deepcopy(state['dialogue'])
        return doc

    def scope(self, state, job):
        from packages.agent.policy import scope
        query = job.get('query') or state['turn']['query']
        return scope(query, job, raw_facts(self.projected(state)), state['entry_hint'])

    def execute(self, state):
        from packages.chat.service import WorkflowError
        meta = deepcopy(state['workflow'])
        turn = deepcopy(state['turn'])
        job = state['job']
        try:
            self.budget.consume('action')
            if job['kind'] == 'consultation' and requested_analysis(state['text']):
                from packages.agent.analysis_policy import analysis_eligibility, report_proposal
                projected = self.projected(state)
                reason = 'confirmation_required' if state['patch'] else analysis_eligibility(projected)
                if reason:
                    turn['reply'] = '请先核对并确认当前事实，再开始分析。' if reason == 'confirmation_required' else \
                        '信息仍有缺口，请明确选择“先看部分整理”，再核对事实并分析。' if reason == 'partial_confirmation_required' else \
                        '本次案件超出已实现的分析范围。'
                    meta.update(status='awaiting_confirmation' if reason != 'out_of_scope' else 'unsupported', reason_code=reason)
                    return self.result(state, turn, meta, job, reason, question=None)
                report = report_proposal(projected, self.analyzer, self.provider, state['owner'])
                turn['reply'] = '已生成有状态标识的内部研究稿，等待最终顾问复核。'
                meta.update(status='draft_ready', reason_code='analysis_ready')
                return {**self.result(state, turn, meta, job, 'pending_final_review', question=None), 'analysis_result': report}
            if turn['intent'] != 'research' and not job.get('query'):
                return self.result(state, turn, meta, job, meta.get('reason_code') or 'fact_collection')
            scope = self.scope(state, job)
            if scope != 'HK':
                if scope == 'need_scope':
                    q = {'id': f'hybrid:scope:{state["doc"]["revision"] + 1}', 'kind': 'mode', 'field': None,
                         'text': '您要查哪个地区的股息规定？', 'why': '先确认检索范围，避免套用错误地区的资料。',
                         'example': '香港；或明确其他地区。', 'attempt': 1,
                         'based_on_revision': state['doc']['revision'] + 1}
                    turn['reply'] = dialogue.render_question(q)
                    meta.update(status='waiting_user', reason_code='intent_unclear')
                    interview = deepcopy(state['dialogue'])
                    interview.update(status='active', pending=q)
                    return {**self.result(state, turn, meta, job, 'need_scope', question=q), 'dialogue': interview}
                turn['reply'] = '当前检索接入覆盖香港境外股息 FSIE；本次请求地区或主题未覆盖，不能套用香港资料回答。'
                meta.update(status='unsupported', reason_code='out_of_scope')
                return self.result(state, turn, meta, job, 'out_of_scope', question=None)
            uses_case = bool(job.get('uses_case', turn.get('uses_case', bool(state['patch']))))
            facts = raw_facts(self.projected(state)) if uses_case else {}
            when, date_status = dialogue.query_date(facts) if uses_case else (None, 'not_needed')
            query = job.get('query') or turn['query']
            req = SearchRequest(request_id=state['request_id'], trace_id=meta['trace_id'], query=query,
                jurisdiction='HK', topic='dividend', applicable_date=when, date_status=date_status,
                intent='case_analysis' if uses_case else 'reference_lookup', income_type=facts.get('income_type'),
                entity_type=facts.get('recipient_type') if facts.get('recipient_type') in ('company', 'individual', 'unknown') else 'not_needed',
                kind=job.get('tool_kind', 'all'),
                fact_filters=[{'field_name': k, 'value': facts[k]} for k in
                    ('income_type', 'source_analysis', 'entity_hk_business_status', 'receipt_location', 'recipient_type')
                    if isinstance(facts.get(k), str) and facts[k] not in ('unknown', 'conflict')])
            bundle = retrieve(self.provider, req, TrustedContext(owner=state['owner'], case_id=state['doc']['id'] if uses_case else None))
            bundle['query_context'] = {'uses_case': uses_case, 'applicable_date': when, 'date_status': date_status, 'jurisdiction': 'HK'}
            if bundle['status'] == 'unavailable' and not state['patch'] and not state['task_results']:
                raise WorkflowError('knowledge_unavailable')
            answer = compose_answer(bundle)
            validate_answer(answer, bundle)
            turn.update(intent='research', query=query, reply=answer['text'])
            if state['patch']:
                turn['reply'] = '本次事实修订将在本轮提交时保存，旧分析需重新确认。\n\n' + turn['reply']
            meta.update(status='draft_ready' if bundle['reason_code'] == 'evidence_available' else 'paused_gap',
                        reason_code=bundle['reason_code'], retrieval_calls=self.budget.counts.get('search', 0))
            interview = deepcopy(state['dialogue'])
            q = state.get('question')
            if bundle['status'] == 'unavailable':
                interview.update(deferred_query=query, deferred_query_uses_case=uses_case)
                meta.update(status='partial_failure', reason_code='retrieval_failed', error_code='knowledge_unavailable', retryable=True)
                turn['reply'] += '\n可回复“重试检索”继续。'
            else:
                if interview.get('deferred_query') == query:
                    interview.pop('deferred_query', None)
                if not uses_case and not state['patch']:
                    interview['status'] = 'suspended'
                if uses_case or state['patch']:
                    projected = self.projected(state)
                    projected['dialogue'] = interview
                    interview, q, followup = dialogue.update_dialogue(projected, {**turn, 'intent': 'intake', 'action': 'continue'}, {})
                    if q:
                        turn['reply'] += '\n\n' + followup
                        meta.update(status='waiting_user', retrieval_reason_code=meta['reason_code'], reason_code='fact_collection')
            return {**self.result(state, turn, meta, job, bundle['reason_code'], question=q),
                    'research': bundle, 'research_results': state['research_results'] + [bundle],
                    'answer': answer, 'dialogue': interview}
        except BudgetExceeded:
            turn['reply'] = '本轮执行预算已用尽，已取得的结果和未完成事项会分别保留；请继续或调整当前任务。'
            meta.update(status='paused_gap', reason_code='budget_exhausted')
            return self.result(state, turn, meta, job, 'budget_exhausted', question=None)

    def result(self, state, turn, meta, job, reason, **extras):
        status = 'completed' if reason == 'evidence_available' else meta['status']
        active = state['orchestration']['active_task']
        item = {'kind': job['kind'], 'task_id': active['id'] if active else 'standalone', 'status': status, 'reason_code': reason,
                'query': job.get('query', '')}
        return {'turn': turn, 'workflow': meta, 'task_results': state['task_results'] + [item],
                'answers': state['answers'] + [turn['reply']], **extras}

    def observe(self, state):
        from packages.chat.service import WorkflowError
        q, meta = state.get('question'), deepcopy(state['workflow'])
        control = deepcopy(state['orchestration'])
        queued = control.get('queued_tasks', [])
        active = control['active_task']
        if active:
            active['status'] = 'waiting_user' if q else 'waiting_confirmation' if meta['status'] == 'awaiting_confirmation' else \
                'failed' if meta['status'] == 'partial_failure' else 'blocked_gap' if meta['status'] in ('paused_gap', 'unsupported') else 'completed'
        if q or state.get('analysis_result') or meta.get('error_code'):
            return {'next_action': 'validate', 'orchestration': control}
        if meta.get('harness_stop') not in (None, 'finished', 'waiting_user', 'analysis_ready'):
            return {'next_action': 'validate', 'orchestration': control}
        if queued and self.budget.remaining() > 0 and self.budget.counts.get('action', 0) < self.budget.action_limit:
            job = queued.pop(0)
            control['active_task'] = task_state.new_task(job['kind'], job['uses_case'])
            if job['uses_case'] and any(v['value'] == 'conflict' for v in self.projected(state)['facts'].values()):
                return {'next_action': 'validate', 'orchestration': {**control, 'queued_tasks': [job] + queued}}
            return {'job': job, 'orchestration': control, 'next_action': job['kind']}
        reason = state.get('research', {}).get('reason_code') if state.get('research') else None
        if meta.get('harness_version') or not self.dynamic or reason != 'no_match' or state['rewrite_count'] or meta['status'] == 'unsupported':
            return {'next_action': 'validate', 'orchestration': control}
        observation = {'latest_user_message': state['text'], 'query': state['turn']['query'],
            'allowed_actions': ['finish', 'lookup_reference'], 'result': {'reason_code': reason, 'evidence_count': 0},
            'task': task_state.project({'orchestration': control}), 'budget': self.budget.snapshot()}
        try:
            from packages.agent.harness import plan_next
            safe_doc = {'facts': deepcopy(self.projected(state)['facts']),
                        'orchestration': task_state.project({'orchestration': control})}
            proposal = self.planner(safe_doc, observation) if self.planner is plan_next else model_call(self.planner, safe_doc, observation)
            proposal = NextAction.model_validate(proposal)
            if proposal.action != 'lookup_reference' or not proposal.query or proposal.query == state['turn']['query']:
                return {'next_action': 'validate', 'orchestration': control}
            job = {**state['job'], 'query': proposal.query}
            if self.scope(state, job) != 'HK':
                meta.update(reason_code='planner_scope_rejected')
                return {'workflow': meta, 'next_action': 'validate', 'orchestration': control}
            # Rewrites must keep user-specified references and years verbatim.
            from packages.agent.policy import rewrite_preserves_scope
            if not rewrite_preserves_scope(state['turn']['query'], proposal.query):
                return {'next_action': 'validate', 'orchestration': control}
            return {'job': job, 'rewrite_count': 1, 'next_action': job['kind'], 'orchestration': control}
        except (WorkflowError, BudgetExceeded, ValueError, TypeError):
            meta.update(status='partial_failure', error_code='model_failed', reason_code='planner_failed', retryable=True)
            return {'workflow': meta, 'next_action': 'validate', 'orchestration': control}

    def validate(self, state):
        result = super().validate(state)
        meta = deepcopy(state['workflow'])
        meta.update(task_results=state['task_results'], budget=self.budget.snapshot())
        from packages.agent.policy import decisions
        meta['rule_decisions'] = decisions(meta, state['turn'])
        if state['orchestration'].get('queued_tasks'):
            meta['pending_tasks'] = len(state['orchestration']['queued_tasks'])
        turn = deepcopy(state['turn'])
        if len(state['answers']) > 1:
            # A rewrite supersedes its earlier no-match result; unrelated tasks retain theirs.
            latest = {}
            for item, answer in zip(state['task_results'], state['answers']):
                latest[item.get('tool_call_id', item['task_id'])] = answer
            turn['reply'] = '\n\n'.join(latest.values())
        if meta.get('reason_code') == 'planner_failed':
            turn['reply'] += '\n后续调度失败，以上为已校验的结果；可重试未完成查询。'
        elif meta.get('harness_stop') not in (None, 'finished', 'waiting_user', 'analysis_ready'):
            turn['reply'] += '\n本轮工具调度已停止，以上为已校验的结果；未完成事项需继续处理。'
        if meta.get('pending_tasks'):
            turn['reply'] += '\n还有未完成的后续任务，已保留进度；补充当前信息或明确继续后再推进。'
        control = deepcopy(state['orchestration'])
        task = control['active_task']
        if not state['task_results'] and state['turn']['intent'] == 'unsupported' and task:
            task['status'] = 'blocked_gap'
        if task:
            if state['turn'].get('action') == 'summary':
                pass  # Read-only summary keeps the prior task and question binding.
            elif state.get('question'):
                task.update(status='waiting_user', pending_question_id=state['question']['id'])
                state['question']['task_id'] = task['id']
            elif state['turn'].get('action') in ('pause', 'new_case') or state['turn']['intent'] == 'chat':
                task['status'] = 'paused'
            elif meta['status'] == 'awaiting_confirmation':
                task['status'] = 'waiting_confirmation'
            elif meta['status'] in ('draft_ready', 'completed', 'partial_ready'):
                task['status'] = 'completed'
                task.pop('pending_question_id', None)
            task['facts_hash'] = dialogue.fingerprint(self.projected(state))
        control['last_run'] = {'request_id': state['request_id'], 'status': meta['status'],
            'reason_code': meta.get('reason_code'), 'policy_version': task_state.VERSION,
            'actions': [t['kind'] for t in state['task_results']]}
        return {**result, 'workflow': meta, 'turn': turn, 'orchestration': control}
