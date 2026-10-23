"""Synthetic fixtures; model and calculations are explicit doubles for workflow checks."""
from copy import deepcopy
from packages.consultation.workflow import fingerprint

TEXT = ('合成研究：分红公司在中国内地。金额1000000 CNY，计划2026-12-01分红。'
        '香港公司直接持有100%股份，自2020-01-01取得。最终给张先生，税务居民地中国内地。'
        '没有中间控股公司，目标长期留在公司投资。')
FACTS = dict(payer_jurisdiction='CN', amount=1000000, currency='CNY', payment_date='2026-12-01',
             direct_holder='香港公司', holding_pct=100, beneficiary='张先生', beneficiary_residence='CN',
             intermediates='none', goal='reinvest_company', holder_type='company', holder_jurisdiction='HK', acquisition_date='2020-01-01')


def ready():
    brief = {'version': 1, 'stage': 'ready', 'facts': {k: {'value': v, 'quote': TEXT, 'status': 'user_stated'} for k, v in FACTS.items()},
             'answers': {'data': {}, 'actions': {}, 'rulings': {}, 'library': {}}, 'conflicts': {}, 'followup_rounds': 0,
             'tools': [], 'analysis': {'diagnosis': '核对现有结构与留存投资目标。', 'alternatives': ['核对现有路径。', '研究具有商业实质的控股路径。'],
                'recommendation': '在法律条件核验后选择可行方案。', 'requirements': ['核验受益所有人和经济实质。'], 'implementation': ['整理股权资料。', '复核适用待遇。']}}
    h = fingerprint(brief)
    def output(value):
        return {'status': 'ready', 'upper': {'value': value, 'status': 'finite'}, 'lower': {'value': value, 'status': 'finite'},
                'currency': 'CNY', 'today': '2026-10-23', 'questions': [], 'unmodelled': [], 'candidate_count': 3,
                'release': 'synthetic-engine-fixture', 'citations': []}
    brief['tools'] = [{'tool': 'calculate_tax', 'status': 'completed', 'input_hash': h, 'currency': 'CNY', 'scope': 'corporate_dividend_only',
                       'assess_current': output(100000), 'plan_structure': output(80000)}]
    brief['analyzed_hash'] = h
    return brief


def fake_model(system, context, tokens=2400):
    if 'Extract only explicitly stated facts' in system:
        source = context['latest_message']
        if '1000000' in source:
            return {'facts': {k: {'value': v, 'quote': source} for k, v in FACTS.items()}, 'answers': {}, 'reply': '已提取合成案例。'}
        return {'facts': {}, 'answers': {}, 'reply': '已收到。'}
    observations = context.get('observations', [])
    if not any(t['tool'] == 'calculate_tax' for t in observations): return {'tool': 'calculate_tax'}
    if not any(t['tool'] == 'search_law' for t in observations): return {'tool': 'search_law', 'query': '股息 分红 受益所有人'}
    return {'tool': 'finish', **ready()['analysis']}


def fake_calculate(brief):
    return {**deepcopy(ready()['tools'][0]), 'input_hash': fingerprint(brief)}


def fake_research(*args):
    return {'tool': 'search_law', 'status': 'no_matching_units', 'model_evidence': [], 'passages': [], 'gaps': ['合成测试不调用真实检索']}
