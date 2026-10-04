"""Real-model / Mock-knowledge evaluation through the unchanged FastAPI routes.

Never imports the browser fake parser. Credentials are used in memory only.
No case or model output in this file is a professional tax gold label.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import inspect
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time
from unittest.mock import patch
from urllib.parse import urlsplit
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import httpx
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from apps.api.main import app
from apps.api.auth import optional_user
from apps.api.chat import get_service, get_provider
from packages.agent.providers import MockKnowledgeProvider
from packages.chat.service import ChatService
from packages.chat.store import ChatStore
from packages.chat.facts import catalog, validate_patch
from packages.model_adapter.client import ModelConfig, ModelError, OpenAICompatibleClient

DATASET = ROOT / 'evals/b_workflow/v0.1/cases.json'
HEADERS = {'x-asiatax-request': '1'}
USER = {'id': 'b67031e1-2c79-48a1-8a60-2b6977b6ff67', 'email': 'synthetic@example.invalid'}
MARKER = 'BWF_DISPLAY_ONLY_SENTINEL_20261003'
OPS = {'message','reload','provider','edit','confirm','analyze','review','replay','replay_changed'}
EXPECT_KEYS = {'error','kind','task','facts_empty','facts','facts_absent','question_present',
    'question_field','question_kind','no_analysis','analysis_count','review_pending','reason',
    'status','search_min','search_max','query_contains','independent_search','no_passages',
    'messages_count','no_new_calls','forbidden','answer_contains','answer_contains_any'}


def load_dataset(path=DATASET):
    data = json.loads(Path(path).read_text())
    ids = [c['id'] for c in data['cases']]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate case IDs')
    for case in data['cases']:
        if case.get('synthetic') is not True or len(case['steps']) < 2:
            raise ValueError('Only multi-step synthetic scripts are accepted')
        validate_patch(case['seed_facts'])
        for step in case['steps']:
            if step['op'] not in OPS or set(step['expect']) - EXPECT_KEYS:
                raise ValueError('Unknown operation or assertion')
            if step['op'] == 'message' and not step.get('text', '').strip():
                raise ValueError('Missing message')
            validate_patch(step['expect'].get('facts', {}))
            fields = {f['field_name'] for f in catalog()} | {'expert_decision_status','tax_conclusion'}
            if set(step['expect'].get('facts_absent', [])) - fields:
                raise ValueError('Unknown expected field')
    return data


class RecordingProvider(MockKnowledgeProvider):
    def __init__(self, scenario):
        super().__init__(scenario)
        self.searches = []
        self.reads = []
        # Include a unique marker in display-only sources to detect later history leaks.
        if scenario == 'MOCK-03':
            for item in self.fixture['display_store']:
                item['text'] += '\n' + MARKER
                item['content_hash'] = hashlib.sha256(item['text'].encode()).hexdigest()
                for evidence in self.fixture['search_response']['evidence']:
                    if evidence['evidence_id'] == item['reference']['evidence_id']:
                        evidence['content_hash'] = item['content_hash']

    def search_evidence(self, request, context):
        self.searches.append({'query': request.query, 'date': request.applicable_date,
                             'filters': request.fact_filters, 'case_id': context.case_id})
        return super().search_evidence(request, context)

    def get_evidence(self, reference, purpose, context):
        self.reads.append({'purpose': purpose, 'case_id': context.case_id})
        return super().get_evidence(reference, purpose, context)


class Meter:
    def __init__(self, config, max_calls=40, interval=3):
        self.config, self.limit, self.interval = config, max_calls, interval
        self.calls = []
        self.last_started = 0
        self.blocked = False
        self.leaked = False
        self.original = OpenAICompatibleClient._post

    def call(self, client, path, payload):
        if len(self.calls) >= self.limit:
            self.blocked = True
            raise ModelError('Evaluation request cap reached')
        if MARKER in json.dumps(payload, ensure_ascii=False):
            self.leaked = True
            raise ModelError('Evaluation detected display-only context leak')
        if client.config.base_url != self.config.base_url or payload.get('model') != self.config.model_name:
            raise ModelError('Unapproved evaluation provider/model')
        delay = self.interval - (time.monotonic() - self.last_started)
        if delay > 0:
            time.sleep(delay)
        self.last_started = time.monotonic()
        stage = next((f.function for f in inspect.stack() if f.function in ('plan_turn', 'plan_next', 'extract_facts')), 'other')
        record = {'index': len(self.calls)+1, 'status': 'started', 'stage': stage}
        self.calls.append(record)
        try:
            result = self.original(client, path, payload)
            record.update(status='ok', usage=result.get('usage', {}))
            return result
        except Exception as exc:
            # Provider errors may echo secrets/request bodies: log exception type only.
            detail = str(exc).lower()
            category = 'tls' if 'certificate_verify_failed' in detail else 'timeout' if ('timeout' in detail or 'timed out' in detail or 'deadline' in detail) else 'rate_limit' if 'http 429' in detail else 'provider_or_transport'
            record.update(status='error', exception=type(exc).__name__, category=category)
            raise
        finally:
            record['duration_ms'] = round((time.monotonic()-self.last_started)*1000, 2)


def check(expect, doc, outcome, new_searches, call_delta):
    failures = []
    def require(ok, reason):
        if not ok:
            failures.append(reason)
    error = outcome.get('error')
    require(error == expect.get('error'), f'error expected={expect.get("error")} actual={error}')
    if error:
        if 'search_max' in expect:
            require(len(new_searches) <= expect['search_max'], 'Failure exceeded retrieval budget')
        return failures
    facts = {k:v['value'] for k,v in doc.get('facts', {}).items()}
    msg = doc.get('messages', [])[-1] if doc.get('messages') else {}
    question = msg.get('question') or {}
    workflow = doc.get('workflow', {})
    for key, value in expect.get('facts', {}).items():
        require(facts.get(key) == value, f'fact {key} expected={value!r} actual={facts.get(key)!r}')
    for key in expect.get('facts_absent', []):
        require(key not in facts, f'fact unexpectedly inferred: {key}')
    if expect.get('facts_empty'):
        require(not facts, 'General question mutated case facts')
    for key, actual in [('kind',msg.get('kind')),('task',workflow.get('effective_task')),
                        ('reason',workflow.get('reason_code')),('status',workflow.get('status')),
                        ('question_field',question.get('field')),('question_kind',question.get('kind'))]:
        if key in expect:
            require(actual == expect[key], f'{key} expected={expect[key]} actual={actual}')
    if 'question_present' in expect:
        require(bool(question) == expect['question_present'], 'Question presence differs')
    if expect.get('no_analysis'):
        require(not doc.get('analyses'), 'Premature analysis produced')
    if 'analysis_count' in expect:
        require(len(doc.get('analyses', [])) == expect['analysis_count'], 'Analysis count differs')
    if expect.get('review_pending'):
        require(bool(doc.get('analyses')) and doc['analyses'][-1].get('review', {}).get('status') != 'approved', 'Report lacks final-review boundary')
    if 'messages_count' in expect:
        require(len(doc.get('messages', [])) == expect['messages_count'], 'Failure committed messages')
    if 'search_min' in expect:
        require(len(new_searches) >= expect['search_min'], 'Expected retrieval did not run')
    if 'search_max' in expect:
        require(len(new_searches) <= expect['search_max'], 'Unexpected/excess retrieval calls')
    for token in expect.get('query_contains', []):
        require(any(token.casefold() in s['query'].casefold() for s in new_searches), f'Retrieval lost locator {token}')
    if expect.get('independent_search'):
        require(bool(new_searches) and all(s['case_id'] is None and not s['filters'] and s['date'] is None for s in new_searches), 'Independent query inherited case scope')
    if expect.get('no_new_calls'):
        require(call_delta == 0 and not new_searches, 'Replay called external tools')
    if expect.get('no_passages'):
        bundles = msg.get('research_results') or [msg.get('research', {})]
        require(all(not b.get('passages') for b in bundles), 'Forbidden evidence displayed')
    for text in expect.get('forbidden', []):
        require(text not in msg.get('text',''), f'Forbidden unsupported statement: {text}')
    for text in expect.get('answer_contains', []):
        require(text in msg.get('text',''), f'Answer missing requested fact/limitation: {text}')
    for alternatives in expect.get('answer_contains_any', []):
        require(any(text in msg.get('text','') for text in alternatives), 'Answer omits requested fact values')
    # Global engineering boundaries independent of scenario-specific expectations.
    require(len(doc.get('questions', [])) <= 1, 'Multiple major questions in one turn')
    require(all(a.get('review', {}).get('status') != 'approved' for a in doc.get('analyses', [])), 'Unauthorized approval')
    return failures


def request(client, path, body=None, method='post', sse=False):
    headers = {**HEADERS, **({'accept':'text/event-stream'} if sse else {})}
    response = getattr(client, method)(path, headers=headers, **({'json':body} if body is not None else {}))
    if response.status_code >= 400:
        return {'error':response.json().get('detail'), 'http_status':response.status_code}, None
    if sse:
        events=[json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
        if not events:
            return {'error':'missing_sse_event'}, None
        event=events[-1]
        return ({'error':event['code']}, None) if event['type']=='error' else ({}, event['case'])
    return {}, response.json()


def run_case(spec, config, meter, directory):
    store = ChatStore(f'sqlite:///{directory}/{spec["id"]}.sqlite')
    provider = RecordingProvider(spec['mock'])
    service = ChatService(store, provider=provider, orchestration='hybrid', dynamic_planner=True)
    # These are the only substitutes: synthetic authentication and unfinished C retrieval.
    # Model turner and planner remain production implementations.
    saved = dict(app.dependency_overrides)
    app.dependency_overrides.update({optional_user:lambda:USER, get_service:lambda:service, get_provider:lambda:provider})
    previous_request = None
    rows=[]
    try:
        with TestClient(app) as client:
            _, doc = request(client, '/api/cases')
            path = f'/api/cases/{doc["id"]}'
            if spec['seed_facts']:
                _, doc = request(client, path+'/facts', dict(revision=doc['revision'], request_id=str(uuid4()), facts=spec['seed_facts']), method='patch')
            for index, step in enumerate(spec['steps'], 1):
                before_calls, before_searches = len(meter.calls), len(provider.searches)
                started=time.monotonic()
                body={'revision':doc['revision'], 'request_id':str(uuid4())}
                outcome, next_doc = {}, None
                action=step['op']
                if action=='message':
                    body.update(text=step['text'], data_approved=True, entry_hint=step.get('entry_hint','auto'))
                    if step.get('bind_question'):
                        body['reply_to_question_id']=(doc['messages'][-1].get('question') or {}).get('id')
                    if step.get('reply_to_question_id'):
                        body['reply_to_question_id']=step['reply_to_question_id']
                    previous_request=deepcopy(body)
                    outcome,next_doc=request(client, path+'/messages',body,sse=step.get('transport')=='sse')
                elif action in ('replay','replay_changed'):
                    body=deepcopy(previous_request)
                    if action=='replay_changed':
                        body['entry_hint']='fact_intake'
                    outcome,next_doc=request(client,path+'/messages',body)
                elif action=='reload':
                    outcome,next_doc=request(client,path,method='get')
                elif action=='provider':
                    provider=RecordingProvider(step['scenario'])
                    service.provider=provider
                    before_searches=0
                elif action=='edit':
                    body['facts']=step['facts']
                    outcome,next_doc=request(client,path+'/facts',body,method='patch')
                elif action in ('confirm','analyze'):
                    outcome,next_doc=request(client,path+'/'+action,body)
                elif action=='review':
                    report=doc['analyses'][-1]
                    body.update(report_hash=report['report_hash'], decision=step['decision'], note='Synthetic evaluation only')
                    outcome,next_doc=request(client,path+f'/analyses/{report["id"]}/review',body)
                if next_doc:
                    doc=next_doc
                else:
                    _,doc=request(client,path,method='get')
                searches=provider.searches[before_searches:]
                errors=check(step['expect'],doc,outcome,searches,len(meter.calls)-before_calls)
                if meter.leaked:
                    errors.append('Display-only source sent to model')
                rows.append(dict(step=index, operation=action, input=step.get('text'), outcome=outcome,
                    expected=step['expect'], checks_failed=errors, duration_ms=round((time.monotonic()-started)*1000,2),
                    model_calls=len(meter.calls)-before_calls, searches=searches,
                    actual={'workflow':doc.get('workflow',{}), 'facts':{k:v['value'] for k,v in doc['facts'].items()},
                            'last_message':doc['messages'][-1] if doc['messages'] else None}))
                if meter.blocked:
                    return dict(id=spec['id'], name=spec['name'], status='blocked', reason='request_cap', steps=rows)
                if errors:
                    return dict(id=spec['id'], name=spec['name'], status='failed', steps=rows)
            return dict(id=spec['id'], name=spec['name'], status='passed', steps=rows)
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)
        store.engine.dispose()


def write_report(report, output):
    output.parent.mkdir(parents=True, exist_ok=True)
    counts={s:sum(r['status']==s for r in report['results']) for s in ('passed','failed','blocked')}
    report['summary']=counts
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str)+'\n')
    output.with_suffix('.md').write_text('# B Agent 实际模型评测记录\n\n'+
        f"时间：{report['started_at']}。层次：{report['layer']}。模型：{report.get('model','未配置')}。\n\n"+
        f"选中 {len(report['results'])} 个脚本；通过 {counts['passed']}，失败 {counts['failed']}，阻断 {counts['blocked']}。\n\n"+
        f"真实模型调用 {len(report.get('model_calls',[]))} 次。全局状态：{report['status']}。\n\n"+
        '检索与身份为合成替身，不代表真实 C、登录、PG 或专业税务验收。\n\n'+
        '| 脚本 | 状态 | 问题 |\n|---|---|---|\n'+''.join(
            f"| {r['id']} | {r['status']} | "+str(r.get('reason') or '; '.join(e for s in r.get('steps',[]) for e in s['checks_failed'])).replace('|','/')+' |\n' for r in report['results']))
    print(json.dumps({'status':report['status'], **counts, 'model_calls':len(report.get('model_calls',[])), 'report':str(output)}, ensure_ascii=False))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite',choices=['smoke','full'],default='smoke')
    parser.add_argument('--select',help='Comma-separated script IDs')
    parser.add_argument('--dataset',type=Path,default=DATASET)
    parser.add_argument('--validate-only',action='store_true')
    parser.add_argument('--provider',choices=['openrouter','existing-plan'],default='openrouter')
    parser.add_argument('--env-file',type=Path,default=ROOT/'.env')
    parser.add_argument('--model',default='qwen/qwen3.8-27b:free')
    parser.add_argument('--max-calls',type=int,default=40)
    parser.add_argument('--interval',type=float,default=3)
    parser.add_argument('--authorized-existing-plan',action='store_true')
    parser.add_argument('--output',type=Path,default=ROOT/'evals/b_workflow/runs/latest.json')
    args=parser.parse_args(argv)
    if not 1<=args.max_calls<=200 or not 0<=args.interval<=60:
        parser.error('Invalid bounded evaluation budget')
    data=load_dataset(args.dataset)
    selected=[c for c in data['cases'] if args.suite=='full' or c['smoke']]
    if args.select:
        ids=set(args.select.split(','))
        selected=[c for c in data['cases'] if c['id'] in ids]
        if len(selected)!=len(ids): parser.error('Unknown script ID')
    report=dict(started_at=datetime.now(timezone.utc).isoformat(), dataset_version=data['version'],
        dataset_sha256=hashlib.sha256(args.dataset.read_bytes()).hexdigest(), layer='M-model/D-knowledge/API',
        provider=args.provider, status='blocked', results=[], model_calls=[], sources=data['sources'])
    if args.validate_only:
        print(json.dumps({'dataset_valid':True, 'scripts':len(data['cases']), 'selected':len(selected),
                          'steps':sum(len(c['steps']) for c in data['cases']), 'live_calls':0}))
        return 0
    values={**dotenv_values(args.env_file),**os.environ}
    reason=None
    if args.provider=='openrouter':
        config=ModelConfig('https://openrouter.ai/api/v1',values.get('OPENROUTER_API_KEY',''),args.model,max_retries=0)
        if not config.api_key: reason='missing_openrouter_key'
        elif not args.model.endswith(':free') or args.model.startswith('openai/'):
            reason='only_explicit_non_openai_free_models_allowed'
        else:
            try:
                response=httpx.get('https://openrouter.ai/api/v1/models',timeout=12)
                response.raise_for_status()
                item=next(m for m in response.json()['data'] if m['id']==args.model)
                pricing=item.get('pricing',{})
                if not {'prompt','completion'}.issubset(pricing) or any(float(v)!=0 for v in pricing.values()):
                    reason='nonzero_or_unknown_price'
                if not reason:
                    quota=httpx.get('https://openrouter.ai/api/v1/key',
                        headers={'Authorization':'Bearer '+config.api_key},timeout=12)
                    quota.raise_for_status()
                    remaining=quota.json().get('data',{}).get('free_model_daily_requests',{}).get('remaining')
                    if isinstance(remaining,int):
                        report['free_daily_remaining_before']=remaining
                        args.max_calls=min(args.max_calls,remaining)
                        if remaining<=0: reason='free_daily_quota_exhausted'
            except (httpx.HTTPError,ValueError,KeyError,StopIteration,TypeError):
                reason='free_price_preflight_failed'
    else:
        config=ModelConfig(values.get('FSIE_MODEL_BASE_URL','').rstrip('/'),values.get('FSIE_MODEL_API_KEY',''),
                           values.get('FSIE_MODEL_NAME',''),max_retries=0)
        endpoint=urlsplit(config.base_url)
        if not args.authorized_existing_plan: reason='existing_plan_needs_user_authorization'
        elif not config.is_configured: reason='existing_plan_not_configured'
        elif endpoint.scheme!='https' or not (endpoint.hostname or '').endswith('.aliyuncs.com') or \
                endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
            reason='unsupported_existing_plan_endpoint'
    if reason:
        report['results']=[dict(id=c['id'],name=c['name'],status='blocked',reason=reason) for c in selected]
        write_report(report,args.output)
        return 2
    meter=Meter(config,args.max_calls,args.interval)
    report['model']=config.model_name
    with TemporaryDirectory(prefix='b-real-eval-') as directory, ExitStack() as stack:
        stack.enter_context(patch('packages.chat.service.current_model_config',return_value=config))
        stack.enter_context(patch.object(OpenAICompatibleClient,'_post',lambda client,path,payload:meter.call(client,path,payload)))
        for spec in selected:
            if meter.blocked:
                result=dict(id=spec['id'],name=spec['name'],status='blocked',reason='request_cap')
            else:
                try:
                    result=run_case(spec,config,meter,directory)
                except Exception as exc:
                    result=dict(id=spec['id'],name=spec['name'],status='failed',reason=type(exc).__name__)
            report['results'].append(result)
            report['model_calls']=meter.calls
            report['status']='running'
            write_report(report,args.output)
    report['status']='complete' if all(r['status']=='passed' for r in report['results']) else 'incomplete'
    write_report(report,args.output)
    return 0 if report['status']=='complete' else 1


if __name__=='__main__':
    raise SystemExit(main())
