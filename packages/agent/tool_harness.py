"""Plan/guard/execute/observe loop on the existing LangGraph runtime."""
from copy import deepcopy
from time import monotonic
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from packages.agent.tools import ToolDecision, SEARCH_KINDS, allowed_tools, tool_catalog, validate_call
from packages.agent.budget import BudgetExceeded, model_call


class LoopState(TypedDict, total=False):
    payload: dict
    seen: list
    observations: list
    calls: list
    decision: dict
    stop: str | None


class ToolHarness:
    def __init__(self, workflow, planner=None):
        self.workflow = workflow
        from packages.agent.harness import plan_tool
        self.planner = planner or plan_tool
        graph = StateGraph(LoopState)
        graph.add_node('plan', self.plan)
        graph.add_node('execute', self.execute)
        graph.add_edge(START, 'plan')
        graph.add_conditional_edges('plan', lambda s: END if s.get('stop') else 'execute')
        graph.add_conditional_edges('execute', lambda s: END if s.get('stop') else 'plan')
        self.graph = graph.compile()

    def invoke(self, state):
        result = self.graph.invoke({'payload': deepcopy(state), 'seen': [], 'observations': [],
                                    'calls': [], 'stop': None}, {'recursion_limit': 12})
        payload = result['payload']
        meta = deepcopy(payload['workflow'])
        meta.update(harness_version='1.0', harness_stop=result['stop'], tool_calls=result['calls'])
        if result['stop'] not in ('finished', 'waiting_user', 'analysis_ready'):
            meta.update(status='partial_failure' if payload['task_results'] else 'paused_gap',
                        reason_code=meta.get('reason_code') if meta.get('error_code') else result['stop'])
            if result['stop'] in ('planner_failed', 'tool_failed'):
                meta.setdefault('error_code', 'model_failed' if result['stop'] == 'planner_failed' else 'tool_failed')
                meta['retryable'] = True
                if not payload['task_results'] and not payload['patch']:
                    from packages.chat.service import WorkflowError
                    raise WorkflowError(meta['error_code'])
        if not payload['task_results']:
            payload['turn']['reply'] = '本轮未取得可用工具结果；当前问题尚未完成，不能生成税务结论。'
        payload['workflow'] = meta
        return payload

    def observation(self, state):
        payload = state['payload']
        return {'latest_user_message': payload['text'],
                'task': {k: payload['job'].get(k) for k in ('kind', 'query', 'uses_case')},
                'tools': tool_catalog(allowed_tools(self.workflow, payload)),
                'case_state': {'fact_fields': list(self.workflow.projected(payload)['facts']),
                               'has_conflicts': bool(payload['conflicts']),
                               'has_pending_question': bool(payload.get('question'))},
                'observations': state['observations'], 'budget': self.workflow.budget.snapshot()}

    def plan(self, state):
        from packages.agent.harness import plan_tool
        from packages.chat.service import WorkflowError
        budget = self.workflow.budget
        if budget.remaining() <= 0 or budget.counts.get('action', 0) >= budget.action_limit:
            return {'stop': 'budget_exhausted'}
        observation = self.observation(state)
        try:
            proposal = self.planner({}, observation) if self.planner is plan_tool else model_call(self.planner, {}, observation)
            decision = ToolDecision.model_validate(proposal)
        except BudgetExceeded:
            return {'stop': 'budget_exhausted'}
        except WorkflowError as exc:
            payload = deepcopy(state['payload'])
            payload['workflow'].update(error_code=exc.code, retryable=True)
            return {'payload': payload, 'stop': 'planner_failed'}
        except Exception:
            return {'stop': 'planner_failed'}
        if decision.tool == 'finish':
            return {'stop': 'finished' if state['calls'] else 'no_tool_result'}
        reason = validate_call(self.workflow, state['payload'], decision, state['seen'])
        if reason:
            return {'stop': reason, 'calls': state['calls'] + [
                {'tool': decision.tool, 'status': 'rejected', 'reason_code': reason}]}
        return {'decision': decision.model_dump()}

    def execute(self, state):
        from packages.agent import dialogue
        from packages.chat.service import WorkflowError
        payload = deepcopy(state['payload'])
        decision = ToolDecision.model_validate(state['decision'])
        # Recheck immediately before execution, even after schema validation.
        rejection = validate_call(self.workflow, payload, decision, state['seen'])
        if rejection:
            return {'stop': rejection}
        started = monotonic()
        try:
            if decision.tool in SEARCH_KINDS:
                job = {**payload['job'], 'kind': 'reference_lookup', 'query': decision.query,
                       'tool_kind': SEARCH_KINDS[decision.tool]}
                # Preserve all scope and case linkage from the original task.
                turn = {**payload['turn'], 'intent': 'research', 'query': decision.query}
                update = self.workflow.execute({**payload, 'job': job, 'turn': turn})
            elif decision.tool == 'prepare_analysis':
                update = self.workflow.execute({**payload, 'job': {**payload['job'], 'kind': 'consultation'}})
            else:
                self.workflow.budget.consume('action')
                doc = self.workflow.projected(payload)
                if decision.tool == 'read_case_facts':
                    reply = dialogue.summary_text(doc)
                else:
                    gaps = dialogue.gaps(doc)
                    reply = '当前目标的事实缺口：\n' + '\n'.join(
                        f'- {g["field"]}：{g["reason"]}；{g["impact"]}' for g in gaps)
                    if not gaps:
                        reply += '当前访谈必需项已记录；仍需核对事实和法源，不代表已满足免税条件。'
                meta = {**payload['workflow'], 'status': 'completed', 'reason_code': 'read_only_result'}
                update = self.workflow.result(payload, {**payload['turn'], 'reply': reply}, meta,
                                              payload['job'], 'read_only_result')
            payload.update(update)
        except BudgetExceeded:
            return {'stop': 'budget_exhausted'}
        except Exception as exc:
            # Do not send exception text, source originals or credentials to planner.
            meta = deepcopy(payload['workflow'])
            meta.update(status='partial_failure', reason_code='retrieval_failed' if
                        isinstance(exc, WorkflowError) and exc.code == 'knowledge_unavailable' else 'tool_failed',
                        error_code=exc.code if isinstance(exc, WorkflowError) else 'tool_failed', retryable=True)
            payload['workflow'] = meta
            return {'payload': payload, 'stop': 'tool_failed', 'calls': state['calls'] + [
                {'tool': decision.tool, 'status': 'failed', 'reason_code': 'tool_failed'}]}
        call_id = f'tool-{len(state["calls"]) + 1}'
        payload['task_results'][-1]['tool_call_id'] = call_id
        reason = payload['workflow'].get('reason_code')
        result = {'tool': decision.tool, 'status': payload['workflow']['status'], 'reason_code': reason,
                  'query': decision.query,
                  'duration_ms': round((monotonic() - started) * 1000, 2)}
        # Planner sees metadata only. Never copy payload['turn']['reply'] or bundle text.
        observation = {'tool': decision.tool, 'query': decision.query, 'reason_code': reason}
        if decision.tool in SEARCH_KINDS:
            bundle = payload.get('research') or {}
            observation.update(evidence_count=len(bundle.get('passages', [])), gaps=bundle.get('reason_code'))
        elif decision.tool == 'check_fact_gaps':
            observation['missing_fields'] = [g['field'] for g in dialogue.gaps(self.workflow.projected(payload))]
        stop = 'waiting_user' if payload.get('question') else 'analysis_ready' if payload.get('analysis_result') else \
            'tool_failed' if payload['workflow'].get('error_code') else None
        return {'payload': payload, 'seen': state['seen'] + [(decision.tool, decision.query)],
                'calls': state['calls'] + [result], 'observations': state['observations'] + [observation], 'stop': stop}
