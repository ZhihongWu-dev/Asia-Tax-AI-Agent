"""Finite business tool surface. No model-supplied identity or write authority."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

ToolName = Literal['finish', 'read_case_facts', 'check_fact_gaps', 'search_law',
                   'search_guidance', 'search_cases', 'prepare_analysis']
SEARCH_KINDS = {'search_law': 'law', 'search_guidance': 'guidance', 'search_cases': 'ruling'}
DESCRIPTIONS = {
    'read_case_facts': '只读整理当前案件用户陈述，不确认事实。',
    'check_fact_gaps': '只读检查当前目标所需事实、未知及冲突，不批准部分分析。',
    'search_law': '查询当前范围的法律条文；保留用户地区、日期、编号。',
    'search_guidance': '查询当前范围的官方解释与指引。',
    'search_cases': '查询用户指定或同主题的参考裁定；不等于案例相似性判断。',
    'prepare_analysis': '仅在用户明确要求且最新事实已经确认时生成待最终复核的内部稿。',
}


class ToolDecision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    tool: ToolName
    query: str = Field(default='', max_length=500)

    @model_validator(mode='after')
    def arguments(self):
        self.query = self.query.strip()
        if self.tool in SEARCH_KINDS and len(self.query) < 2:
            raise ValueError('Search requires a query')
        if self.tool not in SEARCH_KINDS and self.query:
            raise ValueError('Read/control tools do not accept search arguments')
        return self


def tool_catalog(names):
    """Expose only capabilities allowed for this turn, with argument schemas."""
    return [{'name': name, 'description': DESCRIPTIONS[name],
             'arguments': {'query': 'string 2..500'} if name in SEARCH_KINDS else {}}
            for name in names if name in DESCRIPTIONS]


def allowed_tools(workflow, state):
    from packages.agent.hybrid import requested_analysis
    from packages.agent.analysis_policy import analysis_eligibility
    tools = ['read_case_facts', 'check_fact_gaps']
    if workflow.scope(state, state['job']) == 'HK' and state['job'].get('query'):
        tools += list(SEARCH_KINDS)
    if (requested_analysis(state['text']) and not state['patch']
            and not analysis_eligibility(workflow.projected(state))):
        tools.append('prepare_analysis')
    return tools


def validate_call(workflow, state, decision, seen):
    from packages.agent.policy import rewrite_preserves_scope
    if decision.tool not in allowed_tools(workflow, state):
        return 'tool_not_allowed'
    if decision.tool in SEARCH_KINDS:
        original = state['job'].get('query') or state['turn']['query']
        job = {**state['job'], 'query': decision.query}
        if workflow.scope(state, job) != 'HK' or not rewrite_preserves_scope(original, decision.query):
            return 'tool_scope_rejected'
        if (('股息' in original or 'dividend' in original.casefold())
                and not ('股息' in decision.query or 'dividend' in decision.query.casefold())):
            return 'tool_scope_rejected'
        if 'fsie' in original.casefold() and 'fsie' not in decision.query.casefold():
            return 'tool_scope_rejected'
        rewrites = {query for tool, query in seen if tool in SEARCH_KINDS and query != original}
        if decision.query != original and rewrites and decision.query not in rewrites:
            return 'rewrite_limit'
    if (decision.tool, decision.query) in seen:
        return 'duplicate_tool_call'
    return None
