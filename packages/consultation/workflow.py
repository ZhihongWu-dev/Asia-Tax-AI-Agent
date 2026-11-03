"""A bounded consultation workflow; old chat orchestrators are not called here."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4
from threading import Lock
from functools import wraps
from dataclasses import replace

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from packages.chat.attachments import attachment_source, MARKER
from packages.chat.service import WorkflowError, current_model_config, public
from packages.chat.store import RevisionConflict, now
from packages.model_adapter.client import OpenAICompatibleClient, ModelError

ROOT = Path(__file__).resolve().parents[2]
CORE = {
    'payer_jurisdiction': ('分红公司在哪个国家或地区？', 'Where is the dividend-paying company tax resident?'),
    'amount': ('本笔计划分红金额是多少？', 'What is the dividend amount?'),
    'currency': ('分红使用什么币种？', 'What currency is the dividend in?'),
    'payment_date': ('计划在哪一天分红？请给出年月日；不确定可回答未知。', 'What is the planned payment date (YYYY-MM-DD), or unknown?'),
    'direct_holder': ('目前谁直接持有分红公司（个人还是公司）？', 'Who directly holds the paying company (person or company)?'),
    'holding_pct': ('直接股东持股比例是多少？', 'What percentage does the direct shareholder hold?'),
    'beneficiary': ('最终希望把钱给谁？', 'Who is the ultimate intended recipient?'),
    'beneficiary_residence': ('最终收款人的税务居民地在哪里？', 'Where is the ultimate recipient tax resident?'),
    'intermediates': ('目前中间有没有香港、新加坡等控股公司？没有也请明确说明。', 'Are there existing holding companies, including Hong Kong or Singapore? State none if absent.'),
    'goal': ('希望马上取得个人现金，还是长期留在公司投资，或两者兼有？', 'Is the goal personal cash now, long-term corporate reinvestment, or both?'),
}
EXTRA = {'holder_jurisdiction', 'holder_type', 'acquisition_date', 'substance', 'beneficial_owner', 'group_revenue'}


def fingerprint(brief):
    return sha256(json.dumps({'facts': brief.get('facts', {}), 'answers': brief.get('answers', {}),
                             'conflicts': brief.get('conflicts', {}), 'context': brief.get('context', []),
                             'skill': brief.get('skill', {})}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class Fact(BaseModel):
    model_config = ConfigDict(extra='forbid')
    value: str | float | bool | None
    quote: str = Field(min_length=1, max_length=1500)


class Intake(BaseModel):
    model_config = ConfigDict(extra='forbid')
    facts: dict[str, Fact] = Field(default_factory=dict, max_length=25)
    answers: dict[str, Fact] = Field(default_factory=dict, max_length=12)
    reply: str = Field(default='', max_length=1200)


class Decision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    tool: Literal['search_law', 'calculate_tax', 'ask', 'finish']
    query: str = Field(default='', max_length=400)
    jurisdiction: str = Field(default='', max_length=80)
    questions: list[str] = Field(default_factory=list, max_length=3)
    question_keys: list[str] = Field(default_factory=list, max_length=3)
    diagnosis: str = Field(default='', max_length=800)
    alternatives: list[str] = Field(default_factory=list, max_length=4)
    recommendation: str = Field(default='', max_length=800)
    requirements: list[str] = Field(default_factory=list, max_length=8)
    implementation: list[str] = Field(default_factory=list, max_length=8)
    evidence_ids: list[str] = Field(default_factory=list, max_length=20)


def model(system, context, tokens=2400):
    try:
        config = replace(current_model_config(), timeout_seconds=30, total_timeout_seconds=35)
        if not config.is_configured:
            raise WorkflowError('model_not_configured')
        return OpenAICompatibleClient(config).chat_json(system, json.dumps(context, ensure_ascii=False), max_tokens=tokens)
    except (ModelError, ValidationError, ValueError, TypeError):
        raise WorkflowError('model_failed') from None


def normalized(key, value, quote):
    if value is None or (isinstance(value, str) and value.strip().lower() in ('unknown', '未知', '不清楚', '不知道')):
        if not re.search(r'未知|不清楚|不知道|不确定|待确认|unknown|not sure|uncertain', quote, re.I):
            raise ValueError('unknown_without_support')
        return None
    if key in ('amount', 'holding_pct'):
        if isinstance(value, bool):
            raise ValueError('invalid_number')
        number = Decimal(str(value))
        if not number.is_finite() or number < 0 or (key == 'holding_pct' and number > 100):
            raise ValueError('invalid_number')
        # Require the amount to be present in the quoted source, including Chinese units.
        candidates = [Decimal(n.replace(',', '')) * {'万': 10000, '亿': 100000000}.get(unit, 1)
                      for n, unit in re.findall(r'(\d[\d,]*(?:\.\d+)?)\s*([万亿]?)', quote)]
        if number not in candidates:
            raise ValueError('number_not_in_quote')
        return float(number)
    if key in ('payment_date', 'acquisition_date'):
        parsed = date.fromisoformat(str(value))
        digits = [int(n) for n in re.findall(r'\d+', quote)]
        if not all(n in digits for n in (parsed.year, parsed.month, parsed.day)):
            raise ValueError('date_not_in_quote')
        return parsed.isoformat()
    return str(value)[:1000]


def values(brief):
    return {k: r['value'] for k, r in brief.get('facts', {}).items()}


def country(value):
    return {'中国': 'CN', '中国大陆': 'CN', '中国内地': 'CN', '大陆': 'CN', '香港': 'HK',
            '新加坡': 'SG', 'china': 'CN', 'hong kong': 'HK', 'singapore': 'SG'}.get(str(value).strip().lower(), str(value))


def attachment_metadata(text):
    from packages.chat.pdf_attachments import MARKER as OLD_MARKER
    for marker in (MARKER, OLD_MARKER):
        if marker in text:
            try:
                payload = json.loads(text.split(marker, 1)[1])
                return {k: payload[k] for k in ('name', 'kind', 'pages', 'page_count', 'empty_pages', 'warnings') if k in payload}
            except (ValueError, TypeError):
                return None
    return None


def engine_case(brief):
    from packages.domain_bridge.bridge import DomainCase
    v = values(brief)
    missing = [k for k in ('holder_type', 'holder_jurisdiction', 'acquisition_date') if not v.get(k)]
    if missing:
        return None, missing
    if v['holder_type'] != 'company':
        return None, ['individual_tax_not_covered']
    if v.get('intermediates') not in ('none', '无', '没有'):
        return None, ['complex_structure_requires_verified_mapping']
    if v.get('currency') != 'CNY':
        return None, ['non_CNY_not_covered']
    if country(v.get('payer_jurisdiction')) not in ('CN', 'HK', 'SG') or country(v['holder_jurisdiction']) not in ('CN', 'HK', 'SG'):
        return None, ['jurisdiction_not_covered']
    if not v.get('payment_date') or v.get('amount') is None or not v.get('holding_pct'):
        return None, ['amount_date_or_shareholding_unknown']
    if v['acquisition_date'] > v['payment_date']:
        return None, ['acquisition_date_after_payment']
    data = {'template': 'holding', 'currency': 'CNY', 'roles': {'OP': {'loc': country(v['payer_jurisdiction'])},
            'ULT': {'loc': country(v['holder_jurisdiction'])}},
            'holds': [{'holder': 'ULT', 'held': 'OP', 'ratio': v['holding_pct'], 'since': v['acquisition_date']}],
            'flows': {'up1': {}}, 'present': {'HOLD': None, 'financing': 'EQUITY', 'payment': False},
            'event': {'dividend': v['amount'], 'on': v['payment_date'], 'as_at': v['payment_date']}, 'members': ['OP', 'ULT']}
    return DomainCase.model_validate(data), []


def calculate(brief):
    from packages.domain_bridge.bridge import run_domain, DomainError
    case, gaps = engine_case(brief)
    result = {'tool': 'calculate_tax', 'scope': 'corporate_dividend_only', 'currency': values(brief).get('currency'),
              'gaps': gaps, 'input_hash': fingerprint(brief), 'endpoint': 'direct_company_shareholder', 'horizon': 'single_dividend'}
    if case is None:
        return {**result, 'status': 'unsupported_or_missing'}
    answers = brief.get('answers', {'data': {}, 'actions': {}, 'rulings': {}, 'library': {}})
    try:
        for mode in ('assess_current', 'plan_structure'):
            result[mode] = run_domain(case, answers, today=date.today().isoformat(), mode=mode)
        result['status'] = 'completed'
    except DomainError as exc:
        result.update(status='unavailable', error=exc.code)
    return result


def research(brief, decision, provider, owner, case_id):
    from packages.agent.knowledge import retrieve
    from packages.agent.contracts import SearchRequest, TrustedContext
    when = values(brief).get('payment_date')
    result = retrieve(provider, SearchRequest(request_id=str(uuid4()), trace_id=str(uuid4()),
        query=decision.query or '股息 分红 控股公司 受益所有人 反滥用',
        jurisdiction=country(decision.jurisdiction) if decision.jurisdiction else None, topic=None,
        applicable_date=date.fromisoformat(when) if when else None, date_status='planned' if when else 'unknown',
        deadline_ms=8000, limit=4, kind='law'), TrustedContext(owner=owner, case_id=case_id))
    return {'tool': 'search_law', **result}


def model_tools(tools):
    """Never send display-only statutory texts or unbounded engine payloads to the model."""
    projected = []
    for tool in tools[-6:]:
        if tool['tool'] == 'search_law':
            projected.append({k: tool.get(k) for k in ('tool', 'status', 'query', 'gaps', 'model_evidence')})
        else:
            item = {k: v for k, v in tool.items() if k not in ('assess_current', 'plan_structure')}
            for mode in ('assess_current', 'plan_structure'):
                out = tool.get(mode, {})
                item[mode] = {k: out.get(k) for k in ('status', 'note', 'lower', 'upper', 'questions', 'candidate_count', 'candidate', 'unmodelled')}
            projected.append(item)
    return projected


def explicit_consent(text):
    # Full-match only: negations, quoted material and incidental mentions cannot authorize generation.
    return bool(re.fullmatch(r'(?:没有了[，,。 ]*)?(?:可以|请|确认)?生成\s*(?:PDF|pdf)?(?:报告|简报)?[了吧。！! ]*|generate (?:the )?pdf(?: report)?[.! ]*', text.strip(), re.I))


_locks_guard = Lock()
_case_locks = {}


def serial_case(fn):
    @wraps(fn)
    def wrapped(store, provider, owner, case_id, *args, **kwargs):
        with _locks_guard:
            lock = _case_locks.setdefault((owner, case_id), Lock())
        with lock:
            return fn(store, provider, owner, case_id, *args, **kwargs)
    return wrapped


@serial_case
def message(store, provider, owner, case_id, revision, request_id, text, approved, locale='zh', emit=lambda _: None, caller=None):
    caller = caller or model
    text = text.strip()
    if not text:
        raise WorkflowError('empty_message')
    doc = deepcopy(store.get(owner, case_id))
    payload_hash = sha256(json.dumps([text, approved, locale], ensure_ascii=False).encode()).hexdigest()
    receipt = doc.get('brief_receipts', {}).get(request_id)
    if receipt:
        if receipt != payload_hash:
            raise WorkflowError('request_payload_conflict')
        return public(doc)
    if doc['revision'] != revision:
        raise RevisionConflict()
    if not (approved or doc.get('data_approved')):
        raise WorkflowError('data_confirmation_required')
    if len(doc['messages']) >= 200:
        raise WorkflowError('case_limit')
    brief = doc.setdefault('consultation', {'version': 1, 'stage': 'collecting', 'facts': {}, 'tools': [], 'followup_rounds': 0,
        'answers': {'data': {}, 'actions': {}, 'rulings': {}, 'library': {}}, 'conflicts': {}})
    en = locale == 'en'
    say = lambda zh, english: english if en else zh
    user_message = {'id': str(uuid4()), 'role': 'user', 'text': text, 'kind': 'consultation', 'reply_locale': locale}
    source = attachment_source(text) or text
    if brief.get('stage') == 'ready' and explicit_consent(text) and fingerprint(brief) == brief.get('analyzed_hash'):
        brief['generation_consent'] = brief['analyzed_hash']
        reply = say('已确认。正在生成五页咨询简报，你可以在进度卡片中查看状态。', 'Confirmed. Your five-page brief is being prepared; follow the progress card.')
    else:
        emit(say('正在解析资料和本轮回答…', 'Reading your information…'))
        skill = (ROOT / 'config/dividend_brief_skill.md').read_text()
        brief['skill'] = {'name': 'dividend_brief', 'version': 1, 'sha256': sha256(skill.encode()).hexdigest()}
        extraction_prompt = skill + '''\nExtract only explicitly stated facts in the LATEST message. Return JSON:
{"facts":{"key":{"value":...,"quote":"exact verbatim substring of latest message"}},
"answers":{"engine_question_key":{"value":...,"quote":"exact substring"}},"reply":"brief acknowledgement"}.
Keys for facts: ''' + ', '.join([*CORE, *sorted(EXTRA)]) + '''.
Unknown is null only when the quote explicitly says unknown. Omitted information is absent, never null.
Use ISO dates, numeric amount/share percentage, ISO currency, country codes if clear.
holder_type: company or individual. intermediates: none only if explicitly absent; otherwise describe structure.
goal: personal_now, reinvest_company, mixed. Do not invent company identities or jurisdictions.
Engine answers only for supplied pending questions; no ruling/library answers. No data from prior facts as new facts.
No other keys.'''
        try:
            extracted = Intake.model_validate(caller(extraction_prompt, {'latest_message': source,
                'facts': brief['facts'], 'conflicts': brief.get('conflicts'), 'pending': brief.get('pending', []),
                'last_questions': brief.get('last_questions', []), 'attachment': attachment_metadata(text), 'language': locale}))
        except (ValidationError, ValueError, TypeError):
            raise WorkflowError('model_failed') from None
        old_hash = fingerprint(brief)
        brief.setdefault('context', []).append(source[:22000])
        brief['context'] = brief['context'][-6:]
        attachment = attachment_metadata(text)
        if attachment:
            brief.setdefault('attachments', []).append({'message_id': user_message['id'],
                **{k: v for k, v in attachment.items() if k != 'pages'}})
            brief['attachments'] = brief['attachments'][-12:]
        rejected = []
        for key, fact in extracted.facts.items():
            if key not in CORE and key not in EXTRA or fact.quote not in source:
                rejected.append(key); continue
            try:
                value = normalized(key, fact.value, fact.quote)
            except (ValueError, InvalidOperation):
                rejected.append(key); continue
            previous = brief['facts'].get(key)
            conflict = brief.get('conflicts', {}).get(key)
            if previous and previous['value'] != value and not conflict:
                brief['conflicts'][key] = {'previous': previous['value'], 'candidate': value}
                continue
            if conflict:
                if value not in (conflict['previous'], conflict['candidate']):
                    brief['conflicts'][key]['candidate'] = value
                    continue
                brief['conflicts'].pop(key)
            brief['facts'][key] = {'value': value, 'quote': fact.quote, 'message_id': user_message['id'], 'status': 'user_stated'}
        # Explicit identity labels can supply type/location without asking the same information again.
        holder = brief['facts'].get('direct_holder', {})
        label = str(holder.get('value') or '')
        if holder.get('message_id') == user_message['id'] and label in source and re.search(r'公司|company|corporation', label, re.I):
            explicit = {'holder_type': 'company'}
            jurisdiction = next((code for pattern, code in [('香港|hong kong', 'HK'), ('新加坡|singapore', 'SG'), ('中国内地|中国大陆|mainland china', 'CN')]
                                 if re.search(pattern, label, re.I)), None)
            if jurisdiction: explicit['holder_jurisdiction'] = jurisdiction
            for key, value in explicit.items():
                if key not in brief['facts']:
                    brief['facts'][key] = {'value': value, 'quote': label, 'message_id': user_message['id'], 'status': 'user_stated'}
        for key, fact in extracted.answers.items():
            pending = next((q for q in brief.get('pending', []) if q.get('key') == key), None)
            if not pending or pending.get('kind') not in ('data', 'blocking', 'joint', 'action') or fact.quote not in source:
                continue
            v = fact.value
            unknown = v is None and bool(re.search(r'未知|不清楚|不知道|unknown|not sure', fact.quote, re.I))
            schema = pending.get('answer_schema', {}).get('type', 'text')
            if pending['kind'] == 'action' or schema in ('boolean', 'action'):
                yes = bool(re.fullmatch(r'是|是的|有|可以|愿意|yes|true', fact.quote.strip(), re.I))
                no = bool(re.fullmatch(r'否|不是|没有|不愿意|no|false', fact.quote.strip(), re.I))
                if not yes and not no: continue
                v = ('yes' if yes else 'no') if pending['kind'] == 'action' else yes
            elif schema == 'number' and not unknown:
                try: v = normalized('amount', v, fact.quote)
                except (ValueError, InvalidOperation): continue
            elif schema == 'date' and not unknown:
                try: v = normalized('payment_date', v, fact.quote)
                except ValueError: continue
            elif not unknown and str(v) != fact.quote:
                continue
            brief['answers']['actions' if pending['kind'] == 'action' else 'data'][key] = 'unknown' if unknown else v
        changed = fingerprint(brief) != old_hash
        if changed:
            brief.pop('generation_consent', None)
            brief.pop('report_job', None)
            brief.pop('analysis', None)
            brief['stage'] = 'collecting'
        missing = [k for k in CORE if k not in brief['facts']]
        if brief.get('conflicts'):
            reply = say('资料与已保存的信息有差异。请明确采用以下哪一个值，再继续：', 'Please resolve these changed facts before continuing:') + '\n' + '\n'.join(
                f"- {k}: {v['previous']} / {v['candidate']}" for k, v in brief['conflicts'].items())
        elif missing or rejected:
            reply = (extracted.reply + '\n\n' if extracted.reply else '') + say('为准备股息咨询简报，请补充（不知道的可标记未知）：', 'For the dividend brief, please provide the following (unknown is acceptable):') + '\n' + '\n'.join(
                '- ' + CORE[k][int(en)] for k in missing)
            if rejected:
                reply += say('\n有些数值或日期无法与原文核对，请用明确金额、币种和年月日重新说明。', '\nSome values could not be matched to your text; please restate exact amounts and dates.')
        else:
            # Up to two tools per turn, with an actual observation before every next decision.
            emit(say('正在选择检索和计算工具…', 'Selecting research and calculation tools…'))
            allowed_ids = set()
            decision = Decision(tool='finish')
            for step in range(3):
                pending = [q for t in brief['tools'][-4:] for mode in ('assess_current', 'plan_structure')
                           for q in t.get(mode, {}).get('questions', [])]
                brief['pending'] = list({q['key']: q for q in pending}.values())[:60]
                known_hash = fingerprint(brief)
                tools_here = [t for t in brief['tools'] if t.get('input_hash') == known_hash]
                decision_prompt = skill + '''\nChoose the next bounded action using actual observations. Return ONLY JSON matching:
{"tool":"search_law|calculate_tax|ask|finish","query":"", "jurisdiction":"",
"questions":[],"question_keys":[],"diagnosis":"","alternatives":[],"recommendation":"","requirements":[],"implementation":[],"evidence_ids":[]}.
Try calculate_tax and search_law once per facts snapshot before finish. Do not repeat a failed tool for unchanged facts.
If calculation reports missing holder_type/holder_jurisdiction/acquisition_date, ask for them only when useful.
Ask for material engine data/action gaps; never claim a ruling/library answer or action consent.
For an engine follow-up, copy its key into question_keys, corresponding to the displayed questions.
For ordinary fact follow-ups, leave question_keys empty. Do not invent keys.
Never repeat questions already answered unknown. Maximum three questions, short and in the UI language.
When tools lack coverage, finish with a conditional research brief and concrete verification steps.
On the last decision (tools_remaining=0), choose ask or finish. Ask only for material unanswered variables.
If the user cannot supply a variable or says it is unknown, finish with an explicit conditional report
rather than repeating that question. Otherwise decide if more information is actually necessary.
Each narrative item <=200 characters; no tax rates, tax amounts, or savings numbers in narrative.
Tax Comparison will be rendered separately from audited tool results. evidence_ids must occur in authorized model_evidence.
Never claim implementation or a global optimum is legally validated. Do not output any other fields.'''
                raw = caller(decision_prompt, {'facts': brief['facts'], 'observations': model_tools(tools_here),
                    'latest_message': source, 'language': locale, 'tools_remaining': 2 - step,
                    'previous_requests': [s[:4000] for s in brief.get('context', [])[-4:]],
                    'followup_rounds': brief['followup_rounds'], 'answers': brief['answers']}, 3000)
                try: decision = Decision.model_validate(raw)
                except (ValidationError, ValueError, TypeError): raise WorkflowError('model_failed') from None
                needed = [key for t in tools_here if t['tool'] == 'calculate_tax' for key in t.get('gaps', [])
                          if key in ('holder_type', 'holder_jurisdiction', 'acquisition_date') and key not in brief['facts']]
                if decision.tool == 'finish' and needed:
                    wording = {'holder_type': ('直接股东是公司还是个人？', 'Is the direct shareholder a company or individual?'),
                               'holder_jurisdiction': ('直接股东的税务居民地是哪里？', 'Where is the direct shareholder tax resident?'),
                               'acquisition_date': ('直接股东在哪一天取得股份？不知道可以回答未知。', 'When did the direct shareholder acquire the shares, or unknown?')}
                    decision.tool = 'ask'
                    decision.questions = [wording[k][int(en)] for k in dict.fromkeys(needed)]
                if decision.tool == 'finish' and not brief.get('engine_question_rounds'):
                    material = [q for t in tools_here for q in t.get('plan_structure', {}).get('questions', [])
                                if q.get('kind') in ('data', 'blocking', 'joint', 'action') and
                                q['key'] not in brief['answers']['data'] and q['key'] not in brief['answers']['actions']]
                    if material:
                        material = material[:2]
                        decision.tool = 'ask'
                        decision.questions = [q['prompt'] for q in material]
                        decision.question_keys = [q['key'] for q in material]
                if decision.tool == 'finish' and step < 2:
                    missing_tools = [name for name in ('calculate_tax', 'search_law') if not any(t['tool'] == name for t in tools_here)]
                    if missing_tools:
                        decision.tool = missing_tools[0]
                if decision.tool in ('ask', 'finish') or step == 2:
                    break
                if any(t['tool'] == decision.tool for t in tools_here):
                    decision.tool = 'finish'
                    break
                emit(say('正在查阅法规资料…', 'Retrieving legal evidence…') if decision.tool == 'search_law' else say('正在试算现状和候选结构…', 'Calculating the current and alternative structures…'))
                if decision.tool == 'calculate_tax':
                    result = calculate(brief)
                else:
                    result = research(brief, decision, provider, owner, case_id)
                result.update(input_hash=known_hash, at=now())
                brief['tools'].append(result)
                brief['tools'] = brief['tools'][-12:]
            if decision.questions and decision.tool == 'ask':
                brief['followup_rounds'] += 1
                brief['pending'] = [q for q in brief.get('pending', []) if q['key'] in decision.question_keys]
                if brief['pending']:
                    brief['engine_question_rounds'] = brief.get('engine_question_rounds', 0) + 1
                brief['last_questions'] = decision.questions
                reply = say('为了让方案与实际安排匹配，还需核对：', 'To make the options fit your circumstances:') + '\n' + '\n'.join('- ' + q[:500] for q in decision.questions)
            else:
                # A terminal brief is always available even when the tools cannot establish an optimum.
                analysis = decision.model_dump(exclude={'tool', 'query', 'jurisdiction', 'questions', 'question_keys'})
                current_tools = [t for t in brief['tools'] if t.get('input_hash') == fingerprint(brief)]
                allowed_ids = {e['evidence_id'] for t in current_tools for e in t.get('model_evidence', [])}
                analysis['evidence_ids'] = [i for i in analysis['evidence_ids'] if i in allowed_ids]
                # Rates/amounts in model narrative are not accepted as computation evidence.
                for key in ('diagnosis', 'recommendation', 'alternatives', 'requirements', 'implementation'):
                    def clean(s):
                        return '' if re.search(r'\d\s*%|[¥$€]|(?:税额|节税|tax|saving)[^。\n]{0,20}\d', s, re.I) else s[:800]
                    analysis[key] = [clean(s) for s in analysis[key] if clean(s)] if isinstance(analysis[key], list) else clean(analysis[key])
                brief.update(stage='ready', analysis=analysis, analyzed_hash=fingerprint(brief))
                brief.pop('generation_consent', None)
                reply = (analysis['diagnosis'] or say('已完成基础资料整理与工具核对。', 'Intake and tool checks are complete.')) + '\n\n' + say(
                    '是否还有需要补充或更正的信息？没有的话，请点击“确认生成 PDF”，或回复“没有了，可以生成PDF报告”。缺失信息和未覆盖的税负将列入简报，不会作为已满足条件。',
                    'Anything to add or correct? Otherwise choose “Generate PDF” or reply “Generate PDF report”. Unknown facts and uncovered taxes will be listed explicitly in the brief.')
    doc['messages'].extend([user_message, {'id': str(uuid4()), 'role': 'assistant', 'text': reply,
        'kind': 'consultation', 'reply_locale': locale}])
    doc.update(data_approved=True, reply_locale=locale, state='consultation')
    doc['title'] = doc['title'] or source.split('\n')[0][:50]
    doc.setdefault('brief_receipts', {})[request_id] = payload_hash
    return public(store.save(owner, doc, revision))
