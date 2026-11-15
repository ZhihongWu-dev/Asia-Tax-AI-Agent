"""Audited interviewing policy, independent of the immutable tax calculation.

Logical AND siblings are not automatically factual prerequisites. Only reviewed
existence/scope dependencies below gate questions; other active engine questions
remain available and carry a neutral explanation of why they are being asked.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re

CATALOG = json.loads(Path(__file__).with_name('interview_catalog.json').read_text(encoding='utf-8'))
POLICY_VERSION = 'interview-2026-10-22-v4'
REINVESTMENT_DETAILS = frozenset({'reinvestment_from_distributed_profit', 'reinvestment_form',
                                'direct_payment', 'investee_encouraged_industry', 'planned_holding_months'})
PILLAR_FIELDS = {f for f, v in CATALOG.items() if v['family'] == 'pillar_two'} - {'group_revenue_eur'}
# Observational gates have no tax-engine semantics. Their answers never become
# a tax exemption, a professional ruling, or an invented zero/date.
EVENT_GATES = {
    'assessment_notice_on': ('assessment_received', '是否已收到这笔事项的评税或核定通知？', 'Have you received an assessment notice for this matter?'),
    'determination_on': ('determination_received', '这笔事项是否已有税务机关作出的决定？', 'Has the tax authority issued a decision on this matter?'),
    'first_notification_on': ('notification_received', '是否已收到或知悉这笔事项涉及的税务通知？', 'Have you received or become aware of the relevant tax notification?'),
    'tax_paid_on': ('tax_paid', '这笔事项是否已实际缴纳税款？', 'Has tax actually been paid on this matter?'),
    'remitted_on': ('tax_remitted', '这笔事项的代扣税款是否已解缴？', 'Has the withheld tax for this matter been remitted?'),
    'tp_adjustment_amount': ('tp_adjusted', '这笔事项是否已发生转让定价调整？', 'Has a transfer-pricing adjustment been made for this matter?'),
    'tp_adjustment_tax': ('tp_adjusted', '这笔事项是否已发生转让定价调整？', 'Has a transfer-pricing adjustment been made for this matter?'),
    'tp_adjustment_paid_on': ('tp_adjustment_paid', '转让定价调整的税款是否已经实际缴纳？', 'Has the tax arising from the transfer-pricing adjustment actually been paid?'),
    'pboc_benchmark_rate': ('tp_adjusted', '这笔事项是否已发生转让定价调整？', 'Has a transfer-pricing adjustment been made for this matter?'),
}
# These existence checks are interview-only and do not invent tax facts.
EVENT_GATES.update({
    'clawback_event_within_2y': ('transfer_relief', '这笔交易是否涉及已申请或计划申请的集团内部转让减免安排？', 'Does this transaction involve claimed or planned intra-group transfer relief?'),
    'prior_map_outcome': ('prior_map', '这笔事项以前是否经过税务机关相互协商？', 'Has this matter previously been through a mutual agreement procedure?'),
    'corresponding_adjustment_granted': ('tp_adjusted', '这笔事项是否已发生转让定价调整？', 'Has a transfer-pricing adjustment been made for this matter?'),
    's10l_open_market_applied': ('assessment_received', '是否已收到这笔事项的评税或核定通知？', 'Have you received an assessment notice for this matter?'),
    'date_of_payment': ('payment_made', '这笔款项是否已经实际支付？', 'Has this payment actually been made?'),
})
LOSS_DETAILS = {'loss_brought_forward', 'cn_loss_type', 'cn_foreign_loss_offset', 'cn_branch_actual_loss',
                'hk_loss_change_dominant_purpose', 'sg_loss_shareholders_same', 'sg_loss_continuity_waived',
                'sg_loss_same_trade', 'sg_group_relief_elected'}
for field in LOSS_DETAILS:
    EVENT_GATES[field] = ('losses_exist', '这家公司是否有本次需要核对或抵扣的亏损？', 'Does this company have losses to review or offset in this case?')
# A notification of paid adjustment tax must not presuppose an adjustment itself.
EVENT_PARENTS = {'tp_adjustment_paid': 'tp_adjusted'}
# Same-object dependencies. No answers from another flow/entity can unlock them.
GATES = {f: ('reinvested_in_cn', True) for f in REINVESTMENT_DETAILS}
GATES.update({
    'reinvested_into': ('reinvested_in_cn', True),
    'reinvestment_withdrawn': ('reinvested_in_cn', True),
    'reinvestment_withdrawn_on': ('reinvestment_withdrawn', True),
    'capitalised_from': ('capitalised', True),
    'sg_loss_same_trade': ('sg_loss_continuity_waived', True),
    'sg_loss_continuity_waived': ('sg_loss_shareholders_same', False),
    'foreign_tax_rate': ('foreign_taxed', True),
    'underlying_tax_share': ('underlying_profits_taxed', True),
    'gst_recovery_ratio': ('gst_input_fully_recoverable', False),
    'asset_disposed_within_2y': ('stamp_relief_claimed', True),
    'government_exempt_condition_met': ('payee_is_government', True),
    'registration_filing_compliant': ('pure_equity_holding', True),
    'cn_asset_ratio': ('indirect_cn_target', True),
    'cn_income_ratio': ('indirect_cn_target', True),
    'cn_value_ratio': ('indirect_cn_target', True),
    'limited_functions_and_risks': ('indirect_cn_target', True),
    'foreign_tax_lower_than_cn': ('indirect_cn_target', True),
    'no_reasonable_commercial_purpose': ('indirect_cn_target', True),
})
FAMILY_NAMES = {
    'goods': ('货物买卖及运输', 'goods transactions and shipping'),
    'property': ('不动产交易或租赁', 'property transactions or leases'),
    'branch': ('分支机构经营情况', 'branch operations'),
    'losses': ('亏损及抵扣条件', 'losses and relief conditions'),
    'reinvestment': ('再投资安排', 'reinvestment arrangements'),
    'foreign_tax': ('境外所得及已缴税款', 'foreign income and taxes paid'),
    'substance': ('收款及经营活动', 'receipt and business activities'),
    'procedure': ('实际发生的税务手续', 'tax procedures that have actually occurred'),
    'pillar_two': ('集团补足税的适用范围', 'the scope of group top-up tax'),
    'cfc': ('境外被控企业相关规则', 'rules for controlled foreign companies'),
    'treaty': ('协定待遇的适用条件', 'eligibility for treaty treatment'),
    'restructuring': ('股权转让或重组方案', 'share transfer or restructuring arrangements'),
    'vat': ('增值税或消费税', 'VAT or GST'), 'interest': ('借款及利息', 'loans and interest'),
    'service': ('服务的履行情况', 'the performance of services'), 'royalty': ('许可及特许权收入', 'licensing and royalty income'),
    'residence': ('公司的居民身份', 'company residence'), 'indirect_transfer': ('间接股权转让', 'indirect share transfers'),
    'share_transfer': ('股权或资产处置', 'share or asset disposals'), 'ownership': ('持股和关联关系', 'ownership and related-party relationships'),
    'pricing': ('交易定价及相关资料', 'transaction pricing and supporting records'),
    'ip': ('知识产权安排', 'intellectual property arrangements'), 'core': ('这笔交易的计算条件', 'the calculation inputs for this transaction'),
}


def parts(key):
    scope, _, raw = key.rpartition('.')
    raw = raw.split(':', 1)[0]  # action predicates are not different fields
    field = raw if raw in CATALOG else re.sub(r'_(?:cn|hk|sg|\d{4})$', '', raw)
    if raw.startswith('branch_') and raw.endswith(('_hk', '_sg')) and field + '_cn' in CATALOG:
        field += '_cn'
    return scope, raw, field


def interview_context(doc):
    core = {k: {'value': r.get('value'),
                'unresolved': r.get('status') in ('unknown', 'conflict', 'deferred')}
            for k, r in doc.get('canonical_fact_records', {}).items()
            if k.startswith(('event.', 'hold:', 'case.')) or k.endswith('.loc')}
    return sha256(json.dumps([doc.get('domain_definition'), core], sort_keys=True, default=str).encode()).hexdigest()


def _value(doc, key):
    if key.startswith('interview:'):
        record = doc.get('domain_interview', {}).get(key, {})
        if record.get('context') is not None and record['context'] != interview_context(doc):
            return None
        return record.get('value')
    record = doc.get('canonical_fact_records', {}).get(key)
    if record is not None:
        if record.get('status') == 'unknown':
            return 'unknown'
        return record.get('value') if record.get('status') not in ('conflict', 'deferred') else None
    # Planned feasibility cannot override an explicit conflicting observation.
    if (doc.get('domain_workflow') or {}).get('mode') == 'plan_structure':
        actions = (doc.get('domain_answers') or {}).get('actions', {})
        values = [truth if actions[key + ':' + predicate] == 'yes' else not truth
                  for predicate, truth in (('is_true', True), ('is_false', False))
                  if actions.get(key + ':' + predicate) in ('yes', 'no')]
        if values:
            return values[0] if all(v is values[0] for v in values) else None
    if key.startswith('group.'):
        field = key.partition('.')[2]
        # Mirror group propagation, but conservatively withhold conflicting values.
        members = (doc.get('domain_case') or {}).get('members') or list((doc.get('domain_case') or {}).get('roles', {}))
        records = [r for k, r in doc.get('canonical_fact_records', {}).items()
                   if k.partition('.')[0] in members and k.endswith('.' + field)]
        if any(r.get('status') in ('unknown', 'conflict', 'deferred') for r in records):
            return None
        vals = [r.get('value') for r in records]
        return vals[0] if vals and all(type(v) is type(vals[0]) and v == vals[0] for v in vals) else None
    return None


def requirements(question, doc, parameters=None):
    scope, raw, field = parts(question['key'])
    if question['key'].startswith('interview:'):
        parent = EVENT_PARENTS.get(raw)
        return ([{'key': scope + '.' + parent, 'op': 'eq', 'value': True}] if parent else [])
    reqs = []
    if field in GATES:
        parent, expected = GATES[field]
        reqs.append({'key': scope + '.' + parent, 'op': 'eq', 'value': expected})
    if field in PILLAR_FIELDS:
        threshold = (parameters or (doc.get('domain_outcome') or {}).get('interview_parameters') or {}).get('pillar_revenue_min')
        reqs.append({'key': 'group.group_revenue_eur', 'op': 'ge', 'value': threshold})
        if field in ('p2_cbcr_revenue', 'p2_cbcr_pbt', 'p2_cbcr_simplified_taxes'):
            suffix = ('_' + raw.rsplit('_', 1)[-1]) if field.startswith('branch_') else raw[len(field):]
            reqs.append({'key': scope + '.p2_qualified_cbcr' + suffix, 'op': 'eq', 'value': True})
    if field == 'clawback_event_within_2y':
        # This field is shared by stamp relief AND HK income relief. Never gate
        # the income-rule question on an unrelated stamp-duty election.
        why = question.get('why', [])
        if why and all('.stamp.' in rule for rule in why):
            reqs.append({'key': scope + '.stamp_relief_claimed', 'op': 'eq', 'value': True})
    if field.startswith('branch_'):
        jurisdiction = raw.rsplit('_', 1)[-1]
        reqs.append({'key': 'interview:' + scope + '.branch_exists_' + jurisdiction, 'op': 'eq', 'value': True})
    stamp_only = field == 'clawback_event_within_2y' and question.get('why') and all('.stamp.' in r for r in question['why'])
    if field in EVENT_GATES and not stamp_only:
        event, _, _ = EVENT_GATES[field]
        reqs.append({'key': 'interview:' + scope + '.' + event, 'op': 'eq', 'value': True})
    return reqs


def requirement_state(req, doc):
    value = _value(doc, req['key'])
    if value is None or value in ('unknown', 'conflict'):
        return 'waiting'
    if req['op'] == 'ge':
        if isinstance(value, bool) or not isinstance(value, (float, int)) or req['value'] is None:
            return 'waiting'
        passed = value >= req['value']
    else:
        if type(value) is not type(req['value']):
            return 'waiting'
        passed = value == req['value']
    return 'ready' if passed else 'not_applicable'


def interview_status(question, doc, parameters=None, _seen=None):
    key = question['key']
    seen = set(_seen or ())
    if key in seen:
        return 'needs_policy_review'
    seen.add(key)
    field = parts(key)[2]
    meta = CATALOG.get(field)
    if not key.startswith(('interview:', 'calendar:')) and not meta:
        return 'needs_policy_review'
    states = []
    for req in requirements(question, doc, parameters):
        states.append(requirement_state(req, doc))
        states.append(interview_status({'key': req['key'], 'kind': 'data'}, doc, parameters, seen))
    if 'not_applicable' in states:
        return 'not_applicable'
    if 'needs_policy_review' in states:
        return 'needs_policy_review'
    if 'waiting' in states:
        return 'waiting'
    if meta and meta.get('handling') in ('derived', 'structured_review'):
        return 'needs_policy_review'
    return 'ready'


def eligible(question, doc):
    return interview_status(question, doc) == 'ready'


def _parent(key, child):
    _, raw, field = parts(key)
    if key.startswith('interview:'):
        if raw.startswith('branch_exists_'):
            region = {'cn': ('内地', 'Mainland China'), 'hk': ('香港', 'Hong Kong'), 'sg': ('新加坡', 'Singapore')}[raw.rsplit('_', 1)[-1]]
            zh, en = '这家公司是否在' + region[0] + '设有分支机构？', 'Does this company have a branch in ' + region[1] + '?'
        else:
            event = next(v for v in EVENT_GATES.values() if v[0] == raw)
            zh, en = event[1], event[2]
        hint, source = '是/否', ''
    else:
        meta = CATALOG.get(field)
        if not meta:
            return None
        zh, en, hint, source = meta['zh'], meta['en'], meta['hint'], meta['source_zh']
        suffix = ('_' + raw.rsplit('_', 1)[-1]) if field.startswith('branch_') else raw[len(field):]
        region = {'_cn': ('中国内地', 'Mainland China'), '_hk': ('香港', 'Hong Kong'), '_sg': ('新加坡', 'Singapore')}.get(suffix)
        if region:
            if field.startswith('branch_'):
                zh, en = zh.replace('内地', region[0]), en.replace('the Mainland', region[1])
            else:
                zh, en = region[0] + '：' + zh, region[1] + ': ' + en
    kind = 'boolean' if hint == '是/否' else 'number' if hint in ('金额', '%', '数值', '比率', '月数', '天数', '比值') else 'date' if hint == '日期' else 'text'
    return {'key': key, 'kind': 'data', 'prompt': zh, 'prompt_en': en, 'region': child.get('region', []),
            'source_hint': source, 'answer_schema': {'type': kind, 'hint': hint}, 'why': child.get('why', []),
            'interview_prerequisite': True}


def prepare_questions(result, doc):
    """Preserve raw engine needs and bounds; add only interview prerequisites."""
    parameters = result.get('interview_parameters', {})
    questions = deepcopy(result.get('questions', []))
    # Traverse prerequisite ancestry even when an intermediate answer already
    # exists; it must not bypass an unanswered root. Avoid duplicating action keys.
    def base_key(key):
        scope, raw, _ = parts(key)
        return scope + '.' + raw
    by_key = {base_key(q['key']): q for q in questions}
    queue = list(questions)
    visited = set()
    while queue:
        q = queue.pop(0)
        if q['key'] in visited or interview_status(q, doc, parameters) == 'not_applicable':
            continue
        visited.add(q['key'])
        for req in requirements(q, doc, parameters):
            parent = _parent(req['key'], q)
            if not parent:
                continue
            queue.append(parent)
            if base_key(parent['key']) not in by_key and _value(doc, req['key']) is None:
                by_key[base_key(parent['key'])] = parent
                questions.append(parent)
    for q in questions:
        q['requirements'] = requirements(q, doc, parameters)
        q['interview_status'] = interview_status(q, doc, parameters)
        meta = CATALOG.get(parts(q['key'])[2], {})
        if meta.get('handling') == 'derived':
            q['review_reason_en'] = 'This value must be derived from the transaction and source facts, not confirmed directly.'
            q['review_reason'] = '此项由交易结构和原始事实计算，不能让用户直接确认计算值。'
        elif meta.get('handling') == 'structured_review':
            q['review_reason_en'] = 'Year-by-year structured records require review; a single sentence or number is insufficient.'
            q['review_reason'] = '此项需要按年度核对结构化明细，不能用一句话或单个数字代替。'
        meta = CATALOG.get(parts(q['key'])[2])
        if meta:
            # Keep upstream English and our reviewed Chinese labels separate.
            label = _parent(q['key'], q)
            q['prompt_en'] = q.get('prompt_en') or (label['prompt_en'] if label else meta['en'])
            if label:
                prefix = {'action': '请确认是否能够完成：', 'ruling': '请由专业人员核实：'}.get(q['kind'], '请确认：')
                q['prompt'] = prefix + label['prompt']
                q['source_hint'] = meta['source_zh']
                q['source_hint_en'] = meta['source_en']
            zh, en = FAMILY_NAMES[meta['family']]
            plan = (doc.get('domain_workflow') or {}).get('mode') == 'plan_structure'
            q['context_zh'] = ('为比较候选方案，需核对' if plan else '为核对') + zh + '；这项提问不代表已认定相关安排或优惠适用。'
            q['context_en'] = ('To compare candidate arrangements, we need to check ' if plan else 'To check ') + en + '; asking does not establish that the arrangement or relief applies.'
    result['engine_question_count'] = result.get('question_count', len(result.get('questions', [])))
    result['questions'] = questions
    result['question_count'] = len(questions)
    result['interview_policy_version'] = POLICY_VERSION
    result['interview_counts'] = {status: sum(q['interview_status'] == status for q in questions)
                                  for status in ('ready', 'waiting', 'not_applicable', 'needs_policy_review')}


def is_deferred(question, doc, facts_hash):
    saved = doc.get('domain_deferred', {}).get(question['key'])
    if isinstance(saved, dict):
        return saved.get('context') == interview_context(doc)
    return saved is not None and saved == facts_hash  # older saved sessions


def next_question(questions, doc, facts_hash):
    parents = {r['key'] for q in questions for r in requirements(q, doc)}
    def order(q):
        _, _, field = parts(q['key'])
        priority = 0 if field == 'reinvested_in_cn' else 1 if q['key'] in parents else 2 if q['kind'] == 'blocking' else 3
        return priority, q['key'], q['kind']
    return next((q for q in sorted(questions, key=order)
                 if q['kind'] in ('data', 'blocking', 'joint', 'action')
                 and not is_deferred(q, doc, facts_hash) and eligible(q, doc)), None)
