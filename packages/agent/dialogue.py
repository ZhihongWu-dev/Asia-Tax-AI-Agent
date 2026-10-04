"""Deterministic, versioned interview policy. No tax qualifications inferred here."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import re

VERSION = 'guided-intake-0.2'

# B-owned input fields. C's source dictionary and search-filter contract stay separate.
EXTRA_FIELDS = [
    ('recipient_type', '收款主体', 'Recipient type', ['company', 'individual', 'unknown', 'conflict']),
    ('analysis_jurisdiction', '本次分析的地区', 'Jurisdiction to analyze', None),
    ('consultation_goal', '本次咨询目标', 'Consultation goal', ['scope', 'receipt', 'participation', 'substance', 'full_analysis', 'unknown', 'conflict']),
    ('payer_jurisdiction', '派息方所在地区', 'Payer jurisdiction', None),
    ('income_event_status', '收入已发生还是计划发生', 'Actual or planned income', ['occurred', 'planned', 'unknown', 'conflict']),
    ('group_structure_description', '集团成员与经营地区描述', 'Group members and operating jurisdictions', None),
    ('hk_staff_description', '在港员工人数与职责描述', 'Hong Kong staff and duties', None),
    ('hk_premises_description', '在港场所及用途描述', 'Hong Kong premises and usage', None),
    ('foreign_tax_description', '境外缴税实际情况', 'Observed foreign tax payments', None),
    ('dividend_form', '股息支付形式', 'Form of dividend', ['cash', 'in_kind', 'mixed', 'unknown', 'conflict']),
    ('transaction_flow_description', '非现金资产及流转描述', 'Non-cash assets and transaction flow', None),
]

IDENTIFICATION = ('recipient_type', 'income_type', 'analysis_jurisdiction', 'consultation_goal')
BASE = ('payer_jurisdiction', 'entity_hk_business_status', 'group_structure_description', 'income_event_status', 'accrual_date', 'payer_entity')
RECEIPT = ('bank_or_account_path', 'receipt_date', 'set_off_or_clearing_arrangement', 'cash_pool_arrangement', 'payment_on_behalf_arrangement')
PARTICIPATION = ('direct_or_indirect_holding', 'holding_percentage_pct', 'continuous_holding_period_months', 'investee_entity', 'foreign_tax_description', 'commercial_rationale')
SUBSTANCE = ('entity_activity_profile', 'hk_staff_description', 'hk_premises_description', 'hk_operating_expenditure_amount', 'hk_operating_expenditure_currency', 'strategic_decision_making_location', 'outsourcing_and_supervision')
# These are customer assertions, never machine-certified qualifications.
JUDGMENT_FIELDS = frozenset(('mne_group_status', 'income_legal_character', 'source_analysis', 'receipt_location',
    'regulated_financial_entity_status', 'pure_equity_holding_entity_status', 'beneficial_owner_status',
    'foreign_tax_on_dividend_or_underlying_profit', 'foreign_tax_credit_available', 'hk_adequate_employees',
    'hk_adequate_premises', 'hybrid_mismatch_arrangement', 'main_purpose_tax_benefit_flag'))

# One principal question per turn, with a reason and a description example.
PROMPTS = {
    'recipient_type': ('这笔收入由个人还是公司收取？', '先确定适用的主体场景。', '公司收取；也可以回答不清楚。'),
    'income_type': ('这笔款项是什么类型的收入？', '当前案件流程支持股息。', '股息、利息、出售资产收入，或暂不清楚。'),
    'analysis_jurisdiction': ('这次希望分析哪个地区的税务处理？', '付款地扣税与香港收款方处理属于不同范围。', '香港收款方的处理；或内地付款方的扣税。'),
    'consultation_goal': ('这次最想解决股息的哪个问题？', '按目标选择后续必要信息。', '是否属于适用范围、收款路径、参股条件、经济实质，或整体梳理。'),
    'payer_jurisdiction': ('派发股息的公司位于哪个地区？', '识别交易背景；所在地本身不等于法律上的收入来源地。', '可写地区，不需要公司真实名称。'),
    'entity_hk_business_status': ('收款公司是否在香港实际经营业务？', '注册地不能代替实际经营事实。', '有贸易业务、只注册暂未经营，或不清楚。'),
    'group_structure_description': ('请简要描述收款公司所属集团的结构。', '收集判断集团范围的事实，不要求您先判断 MNE 法律资格。', '独立公司，或母子公司分别在哪些地区经营。'),
    'income_event_status': ('这笔股息已经发生，还是计划发生？', '区分已发生事实与计划条件。', '已经发生 / 计划发生 / 不清楚。'),
    'accrual_date': ('材料中记载的股息累算日期是哪一天？', '用于核对规则适用期间；不使用今天代替交易日期。', '决议或派息通知中的 YYYY-MM-DD；尚未确定可说不知道。'),
    'payer_entity': ('派息公司与收款公司是什么关系？', '明确本次收入对应哪一主体。', '可用“被投资公司 A”等别名说明。'),
    'bank_or_account_path': ('请描述这笔股息的资金流转路径。', '先了解实际路径，再判断收取规则；不需要银行账号。', '先到境外账户，再汇到香港；或仍在境外。'),
    'dividend_form': ('这笔股息是现金、股票等非现金资产，还是两者都有？', '非现金股息不能套用银行汇款问题。', '现金 / 分配股份 / 两者都有 / 不清楚。'),
    'transaction_flow_description': ('请描述分配的非现金资产及其流转过程。', '记录资产种类、涉及主体与地区，不自动转换成现金收款。', '公司 A 把某公司的股份分给 B，B 是否又向其他主体转让；可以使用别名。'),
    'receipt_date': ('实际收款日期是哪一天？', '收款日与累算日分别记录。', 'YYYY-MM-DD；未收款或未知可说明。'),
    'set_off_or_clearing_arrangement': ('这笔股息有没有通过抵销或结算处理？', '资金未转账也可能存在其他安排，不能仅凭账户所在地判断。', '有 / 没有 / 不清楚。'),
    'cash_pool_arrangement': ('这笔股息是否经过集团现金池？', '补充资金路径。', '有 / 没有 / 不清楚。'),
    'payment_on_behalf_arrangement': ('这笔股息是否用于替其他主体付款？', '补充资金用途。', '有 / 没有 / 不清楚。'),
    'direct_or_indirect_holding': ('收款公司直接还是间接持有派息公司的股份？', '确定持股链路。', '直接持有；或通过某公司间接持有。'),
    'holding_percentage_pct': ('收款公司持有派息公司多少比例的股份？', '收集参股路径的数量事实。', '例如 15%，不清楚则保留未知。'),
    'continuous_holding_period_months': ('在股息累算前已经连续持股多少个月？', '期间以本次交易为基准，不按今天计算。', '例如 18 个月；也可以提供取得日期待核算。'),
    'investee_entity': ('这次持股对应的被投资公司是哪一家？', '与派息主体相互核对，不自动当成同一主体。', '可使用公司 A 等别名。'),
    'foreign_tax_description': ('已知这笔股息或对应利润在境外缴过什么税？', '先记录实际税种和材料，是否合资格留待复核。', '可描述完税凭证中的税种、地区；没有资料可说明。'),
    'commercial_rationale': ('请简要说明这项投资或安排的商业目的。', '记录实际背景，不让用户代替专业判断主要目的。', '例如拓展经营、长期持有投资；未知可以说明。'),
    'entity_activity_profile': ('收款公司在香港具体开展哪些活动？', '先描述活动，再评估经济实质。', '例如管理投资、作出决策或日常经营。'),
    'hk_staff_description': ('香港员工的配置和实际职责是怎样的？', '收集事实，不要求您判断员工是否“足够”。', '人数、职责、工作地点；无需员工姓名。'),
    'hk_premises_description': ('公司在香港使用什么场所开展活动？', '收集场所用途，不预设充分性。', '办公室及其实际用途，或没有场所。'),
    'hk_operating_expenditure_amount': ('相关期间在香港的经营支出金额是多少？', '收集经济实质相关数量，未知不按零处理。', '提供金额，币种可以一并说明。'),
    'hk_operating_expenditure_currency': ('这项经营支出的币种是什么？', '金额必须与币种配对。', '例如 HKD。'),
    'strategic_decision_making_location': ('主要战略决策在哪里作出？', '记录决策实际地点。', '香港、境外、两地都有或不清楚。'),
    'outsourcing_and_supervision': ('相关活动是否外包，监督安排如何？', '了解活动与监督的实际安排。', '没有外包；或外包并在港监督；不清楚可说明。'),
}


def extra_catalog():
    return [{'field_name': k, 'description_zh': zh, 'label_en': en,
             'data_type': 'enum' if options else 'string', **({'enum_values': options} if options else {}),
             'owner': 'B', 'purpose': 'intake_context'} for k, zh, en, options in EXTRA_FIELDS]


def values(doc):
    return {k: v['value'] for k, v in doc.get('facts', {}).items()}


def resolved(value):
    return value is not None and value not in ('unknown', 'conflict', '')


def fingerprint(doc):
    return sha256(json.dumps(values(doc), ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def supported(facts):
    if facts.get('recipient_type') == 'individual':
        return False
    if resolved(facts.get('income_type')) and facts['income_type'] != 'dividend':
        return False
    region = facts.get('analysis_jurisdiction')
    return not resolved(region) or region.strip().casefold() in ('hk', '香港', '中国香港', '中國香港', 'hong kong', 'hong kong sar')


def required_fields(doc):
    facts = values(doc)
    required = list(IDENTIFICATION)
    if not supported(facts):
        return []
    required += list(BASE)
    # Explicit group qualification is retained as a candidate assertion; don't ask its description twice.
    if resolved(facts.get('mne_group_status')):
        required.remove('group_structure_description')
    goal = facts.get('consultation_goal')
    if goal in ('receipt', 'full_analysis'):
        required += ['dividend_form']
        form = facts.get('dividend_form')
        if form in ('cash', 'mixed'):
            required += [f for f in RECEIPT if not (f == 'receipt_date' and facts.get('income_event_status') == 'planned')]
        if form in ('in_kind', 'mixed', 'unknown'):
            required += ['transaction_flow_description']
    if goal in ('participation', 'full_analysis'):
        required += list(PARTICIPATION)
    if goal in ('substance', 'full_analysis'):
        required += list(SUBSTANCE)
    # Do not collect exemption-path details when the supplied scope assertions already disagree.
    if facts.get('entity_hk_business_status') == 'no' or facts.get('mne_group_status') == 'no':
        return list(IDENTIFICATION)
    return required


def gaps(doc):
    facts = values(doc)
    deferred = doc.get('dialogue', {}).get('deferred', {})
    return [{'field': k, 'reason': 'conflict' if facts.get(k) == 'conflict' else
             'unknown' if facts.get(k) == 'unknown' else deferred.get(k, 'missing'),
             'impact': PROMPTS.get(k, ('', '该信息尚未确定，相关判断暂停。', ''))[1]}
            for k in dict.fromkeys(required_fields(doc) + [f for f, v in facts.items() if v == 'conflict'])
            if not resolved(facts.get(k))]


def identification(doc):
    facts = values(doc)
    missing = [k for k in IDENTIFICATION if not resolved(facts.get(k))]
    return {'status': 'unsupported' if not supported(facts) else 'collecting' if missing else 'candidate_identified',
            'scenario': 'hk_fsie_dividend' if supported(facts) and not missing else None,
            'missing_fields': missing, 'professional_validation': 'pending_final_review'}


def next_field(doc):
    facts = values(doc)
    if not supported(facts):
        return None
    deferred = doc.get('dialogue', {}).get('deferred', {})
    conflict = next((k for k, v in facts.items() if v == 'conflict' and k not in deferred), None)
    if conflict:
        return conflict
    return next((k for k in required_fields(doc) if k not in facts and k not in deferred), None)


def question(doc, field, attempt=1):
    facts = values(doc)
    if facts.get(field) == 'conflict':
        pair = doc.get('fact_conflicts', {}).get(field, {})
        from packages.chat.facts import catalog
        label = next((f['description_zh'] for f in catalog() if f['field_name'] == field), field)
        text = f'关于“{label}”，之前记录为 {pair.get("previous", "待核对")}，本次为 {pair.get("candidate", "待核对")}，本次应采用哪个值？'
        why, example = '保留双方陈述，未澄清前不选择其一。', '请给出本次正确值；无法确认也可以说明。'
    else:
        text, why, example = PROMPTS[field]
        if facts.get('income_event_status') == 'planned' and field in ('accrual_date', 'bank_or_account_path', 'transaction_flow_description'):
            text = '请按目前计划说明：' + text
            why += ' 本项按计划记录，不代表已经发生。'
    if attempt == 2:
        text = '换一种说明方式：' + text + ' 可以参考后面的示例，暂时不能提供也可以说明。'
    revision = doc.get('revision', 0) + 1
    return {'id': f'{VERSION}:{field}:{revision}:{attempt}', 'kind': 'fact', 'field': field,
            'text': text, 'why': why, 'example': example, 'attempt': attempt, 'based_on_revision': revision}


def choice(doc):
    return {'id': f'{VERSION}:choice:{doc.get("revision", 0) + 1}', 'kind': 'choice', 'field': None,
            'text': '您想继续补充其他信息、先看部分整理，还是暂停？',
            'why': '缺口会保留，相关判断不会补猜。', 'example': '继续补充 / 先看部分整理 / 暂停',
            'attempt': 1, 'based_on_revision': doc.get('revision', 0) + 1}


def mode_question(doc):
    return {'id': f'{VERSION}:mode:{doc.get("revision", 0) + 1}', 'kind': 'mode', 'field': None,
            'text': '您是想查一般规定，还是分析自己这笔交易？', 'why': '先确定本次任务，再决定是否需要案情。',
            'example': '查一般规定 / 分析这笔交易', 'attempt': 1, 'based_on_revision': doc.get('revision', 0) + 1}


def render_question(q):
    return q['text'] + '\n\n' + q['why'] + '\n例如：' + q['example']


def normalize(text):
    return text.strip().rstrip('。.!！?？').casefold()


COMMANDS = {
    '暂停': 'pause', '先暂停': 'pause', 'pause': 'pause',
    '继续补充': 'resume', '继续补充其他信息': 'resume', '继续案件': 'resume', '恢复案件': 'resume',
    '继续整理': 'resume', '继续整理我的情况': 'resume', 'resume': 'resume',
    '先看部分整理': 'partial', '先看部分结果': 'partial', '先按已有信息出部分稿': 'partial', 'partial summary': 'partial',
    '重试检索': 'retry_research', 'retry search': 'retry_research',
}
UNKNOWN = {'不知道', '不清楚', '不确定', 'unknown', "i don't know"}
UNAVAILABLE = {'暂时没有资料', '暂时无法提供', '先跳过', 'skip', 'not available'}


def deterministic_turn(doc, text):
    """Exact dialog controls only; arbitrary natural language still uses the model."""
    value = normalize(text)
    state = doc.get('dialogue', {})
    pending = state.get('pending')
    if explicit_summary_request(text):
        return {'intent': 'intake', 'facts': {}, 'reply': '将汇总已提供的信息。', 'query': '', 'action': 'summary'}
    if state.get('status') in ('paused', 'suspended') and value in UNKNOWN | {'是', '否', 'yes', 'no'}:
        return {'intent': 'clarify', 'facts': {}, 'reply': '请说明本次问题。', 'query': ''}
    action = COMMANDS.get(value)
    if not action and pending and state.get('status') == 'active':
        if value in UNKNOWN:
            action = 'unknown'
        elif value in UNAVAILABLE:
            action = 'unavailable'
        elif pending.get('field'):
            # An exact answer is meaningful only for the active question and its enum.
            from packages.chat.facts import catalog
            spec = next((f for f in catalog() if f['field_name'] == pending['field']), {})
            aliases = {'公司': 'company', '个人': 'individual', '股息': 'dividend', '利息': 'interest',
                       '有': 'yes', '是': 'yes', '没有': 'no', '否': 'no', '已发生': 'occurred',
                       '已经发生': 'occurred', '计划发生': 'planned', '适用范围': 'scope', '收款路径': 'receipt',
                       '参股条件': 'participation', '经济实质': 'substance', '整体梳理': 'full_analysis',
                       '现金': 'cash', '非现金': 'in_kind', '分配股份': 'in_kind', '两者都有': 'mixed'}
            answer = aliases.get(value, value)
            if answer in spec.get('enum_values', []) and answer not in ('unknown', 'conflict'):
                return {'intent': 'intake', 'facts': {pending['field']: answer}, 'reply': '已记录回答。', 'query': ''}
    if not action:
        return None
    return {'intent': 'intake', 'facts': {}, 'reply': '已记录本次选择。', 'query': '', 'action': action}


def query_date(facts):
    date = facts.get('accrual_date')
    status = facts.get('income_event_status')
    if resolved(date) and status in ('planned', 'occurred'):
        return date, 'planned' if status == 'planned' else 'actual'
    return None, 'unknown'


def explicit_partial_request(text):
    value = normalize(text)
    if re.search(r'不要|不想|不需要|别给|do not|don.t|什么是|是什么意思|如何|怎么|解释|what is|how to', value, re.I):
        return False
    return (bool(re.search(r'部分|不完整|partial|incomplete', value, re.I)) and
            bool(re.search(r'先看|先出|先按|先整理|按已有|按现有|生成|输出|给我|我同意|同意先|show me|generate|give me|partial summary', value, re.I)))


def explicit_summary_request(text):
    value = normalize(text)
    if re.search(r'不要(?:汇总|总结|列出)|不用(?:汇总|总结|列出)|do not summarize|don.t summarize', value, re.I):
        return False
    return bool(re.search(r'(?:列出|汇总|总结|列出来).{0,30}(?:已提供|已经提供|已知|案情|事实|信息)|'
                          r'(?:已提供|已经提供|已知).{0,20}(?:列出来|列出|汇总|总结)|'
                          r'summari[sz]e.{0,25}(?:facts|case information)', value, re.I))


def numeric_correction_value_present(field, value, quote):
    if field != 'dividend_amount':
        return bool(re.search(r'(?<![\d.])' + re.escape(format(value, 'g')) + r'(?![\d.])', quote))
    from decimal import Decimal
    for number, unit in re.findall(r'(?<![\d.])([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*(万|亿|million|thousand)?', quote, re.I):
        multiplier = {'万':10000, '亿':100000000, 'million':1000000, 'thousand':1000}.get(unit.casefold(), 1)
        if Decimal(number.replace(',', '')) * multiplier == Decimal(str(value)):
            return True
    return False


def correction_fields(turn, text, doc):
    """Require a field-specific, user-supplied correction span; never use a global '改' flag."""
    authorized = set()
    for field, quote in turn.get('corrections', {}).items():
        if not isinstance(quote, str) or not quote.strip() or quote not in text:
            continue
        if re.search(r'更正|纠正|改为|改成|说错|写错|应为|应该是|不是.{1,30}而是|correct|correction|instead|meant', quote, re.I):
            value = turn['facts'].get(field)
            # Field association is semantic model output; require literal value and field label too.
            from packages.chat.facts import catalog
            spec = next((f for f in catalog() if f['field_name'] == field), {})
            aliases = {
                'recipient_type': ('主体', '个人', '公司', 'recipient'), 'dividend_amount': ('金额', '股息', 'amount'),
                'holding_percentage_pct': ('持股', '比例', 'holding'), 'accrual_date': ('累算', 'accrual'),
                'receipt_date': ('收款', '收取', 'receipt'), 'income_type': ('收入', '股息', '利息', 'income'),
                'analysis_jurisdiction': ('地区', '香港', 'jurisdiction'), 'consultation_goal': ('目标', '问题', 'goal'),
            }.get(field, (field, spec.get('description_zh', field), spec.get('label_en', field)))
            value_alias = {'company': '公司', 'individual': '个人', 'dividend': '股息', 'interest': '利息'}.get(value) if isinstance(value, str) else None
            value_present = (numeric_correction_value_present(field, value, quote)
                             if isinstance(value, (int, float)) else str(value).casefold() in quote.casefold())
            if any(alias.casefold() in quote.casefold() for alias in aliases) and (value_present or value_alias and value_alias in quote):
                authorized.add(field)
    pending = doc.get('dialogue', {}).get('pending')
    if pending and pending.get('field') in turn['facts'] and doc.get('dialogue', {}).get('status') == 'active':
        field = pending['field']
        if values(doc).get(field) == 'conflict':
            authorized.add(field)
    return authorized


def partial_text(doc):
    from packages.chat.facts import catalog
    labels = {f['field_name']: f['description_zh'] for f in catalog()}
    facts = values(doc)
    known = [f'- {labels.get(k, k)}：{v}' for k, v in facts.items() if resolved(v)]
    missing = [f'- {labels.get(g["field"], g["field"])}：{g["reason"]}；{g["impact"]}' for g in gaps(doc)]
    return ('已按您的选择整理当前信息；这不是完整分析或税务结论。\n\n已知陈述：\n' + '\n'.join(known or ['- 暂无']) +
            '\n\n待补与待核对：\n' + '\n'.join(missing or ['- 当前访谈必需项已记录，事实与依据仍需核对。']) +
            '\n\n判断性事项保留至最终顾问复核。可在案例信息中核对事实后生成研究稿，也可继续补充。')


def summary_text(doc):
    from packages.chat.facts import catalog
    labels = {f['field_name']: f['description_zh'] for f in catalog()}
    rows = [f'- {labels.get(k,k)}：{v}' for k,v in values(doc).items()]
    missing = [f'- {labels.get(g["field"],g["field"])}：{g["reason"]}；{g["impact"]}' for g in gaps(doc)]
    return ('以下是当前已记录的用户陈述，unknown 表示未知，conflict 表示存在冲突；尚未确认或形成税务结论。'
            '\n\n已提供的信息：\n' + '\n'.join(rows or ['- 暂无']) +
            '\n\n待补与待核对：\n' + '\n'.join(missing or ['- 仍需核对事实与对应依据。']) +
            '\n\n本次仅汇总信息，原追问进度保留；不会自动确认事实或授权部分分析稿。')


def update_dialogue(doc, turn, patch):
    """Returns metadata, question and reply. doc already contains projected candidate facts."""
    state = deepcopy(doc.get('dialogue', {}))
    state.setdefault('policy_version', VERSION)
    state.setdefault('deferred', {})
    state.setdefault('attempts', {})
    state.setdefault('pending', None)
    if patch:
        state.pop('partial_consent', None)
        for field in patch:
            if resolved(values(doc).get(field)):
                state['deferred'].pop(field, None)
                state['attempts'].pop(field, None)
    action = turn.get('action', 'continue')
    if action == 'summary':
        return state, None, summary_text(doc)
    if action == 'new_case':
        state['status'] = 'suspended'
        return state, None, '这是另一笔案件，请使用“新对话”建立独立记录，避免覆盖当前案件。'
    if turn['intent'] in ('chat', 'research'):
        state['status'] = 'suspended'
        return state, None, turn['reply']
    if turn['intent'] == 'unsupported':
        state['status'], state['pending'] = 'unsupported', None
        return state, None, turn['reply']
    if action == 'pause':
        state['status'] = 'paused'
        return state, None, '已暂停并保存当前进度。需要继续时可以说“继续案件”。'
    doc = {**doc, 'dialogue': state}
    if action == 'partial':
        state['status'], state['pending'] = 'partial', None
        state['partial_consent'] = {'facts_hash': fingerprint(doc), 'revision': doc.get('revision', 0) + 1}
        return state, None, partial_text(doc)
    if turn['intent'] == 'clarify':
        q = mode_question(doc)
        state['status'], state['pending'] = 'active', q
        return state, q, render_question(q)
    if action == 'resume' and not patch and state.get('pending') and state['pending'].get('field') and \
            not resolved(values(doc).get(state['pending']['field'])):
        state['status'] = 'active'
        return state, state['pending'], render_question(state['pending'])
    pending = state['pending']
    unresolved_response = action in ('unknown', 'unavailable') or any(v == 'unknown' for v in patch.values())
    if (unresolved_response and pending and pending.get('field') and
        (patch.get(pending['field']) == 'unknown' or action in ('unknown', 'unavailable') and not patch)):
        state['deferred'][pending['field']] = 'unknown' if action == 'unknown' or patch.get(pending['field']) == 'unknown' else 'unavailable'
    if unresolved_response:
        q = choice(doc)
        state['status'], state['pending'] = 'active', q
        return state, q, '已保留未知或暂缺信息，相关判断会暂停。\n\n' + render_question(q)
    field = next_field(doc)
    if field:
        attempt = state['attempts'].get(field, 0) + 1
        if attempt > 2:
            state['deferred'][field] = 'unanswered'
            q = choice(doc)
            reply = '这项信息仍未确定，先保留缺口。\n\n' + render_question(q)
        else:
            q = question(doc, field, attempt)
            state['attempts'][field] = attempt
            reply = ('已记录本次信息。\n\n' if patch else '') + render_question(q)
        state['status'], state['pending'] = 'active', q
        return state, q, reply
    if gaps(doc):
        q = choice(doc)
        state['status'], state['pending'] = 'active', q
        return state, q, '目前仍有未知、暂缺或冲突信息，不能形成完整判断。\n\n' + render_question(q)
    state['status'], state['pending'] = 'ready', None
    return state, None, '当前任务所需的描述已整理，请核对事实后开始研究分析。判断性事项和依据仍需最终复核。'
