"""Non-destructive smoke check of the running chat API with synthetic input only.

Uses a verified test account and deletes only its own empty/synthetic case.
Prints counts and statuses, never credentials, case content or raw exceptions.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx
from sqlalchemy import create_engine, text
from packages.persistence.config import get_settings


def main():
    report = {}
    case_id = owner = None
    engine = create_engine(get_settings().database_url, connect_args={'connect_timeout': 5})
    try:
        with httpx.Client(base_url='http://127.0.0.1:8000', timeout=65, trust_env=False,
                          headers={'X-AsiaTax-Request': '1'}) as client:
            def checked(response):
                response.raise_for_status()
                return response.json()

            email = os.environ.get('TAXORA_SMOKE_EMAIL')
            password = os.environ.get('TAXORA_SMOKE_PASSWORD')
            if not email or not password:
                raise RuntimeError('Verified smoke-test account credentials required')
            login = checked(client.post('/api/auth/login', json={'email': email, 'password': password}))
            owner = 'user:' + login['user']['id']
            checked(client.get('/api/session'))
            for query in ['Case 68', 'Case 72', 'Case 74', 'Case 75', 's.15M(2)', '经济实质', 'weather forecast']:
                result = checked(client.get('/api/knowledge/search', params={'q': query}))
                count = len(result['passages'])
                assert count == 7 if query.startswith('Case') else (count == 0 if query == 'weather forecast' else count > 0)
                report[query] = {'status': result['status'], 'passages': count}
                print('search_verified:', query, count, flush=True)

            doc = checked(client.post('/api/cases'))
            case_id = doc['id']

            def mutate(action, **payload):
                nonlocal doc
                method = client.patch if action == 'facts' else client.post
                body = {'revision': doc['revision'], 'request_id': str(uuid4()), **payload}
                response = method(f'/api/cases/{case_id}/{action}', json=body)
                if response.status_code == 503 and response.json().get('detail') == 'model_failed':
                    report['model_retries'] = report.get('model_retries', 0) + 1
                    print('retrying_model_with_same_request_id=True', flush=True)
                    response = method(f'/api/cases/{case_id}/{action}', json=body)
                doc = checked(response)

            for prompt in ['你好', '你能帮我做些什么？', '请把你刚才的介绍用英文再说一遍']:
                mutate('messages', text=prompt, data_approved=True)
                reply = doc['messages'][-1]
                assert reply['kind'] == 'chat' and reply['text'].strip()
                assert doc['facts'] == {} and doc['confirmed_revision'] is None
                print('normal_chat_verified=', reply['kind'], flush=True)
            report['live_normal_chat_turns'] = 3
            mutate('messages', text='Please show the official source for Case 68.', data_approved=True)
            assert doc['messages'][-1]['kind'] == 'research'
            assert len(doc['messages'][-1]['research']['passages']) == 7
            report['live_model_research_route'] = True
            print('live_model_research_route=True', flush=True)
            mutate('messages', text='Synthetic research case only: a multinational group entity carries on business in Hong Kong and received a foreign-sourced dividend of HKD 100000 in Hong Kong on 1 June 2025. The dividend accrued on 1 May 2025. It held 10% of the investee continuously for 24 months. Employee adequacy is unknown.', data_approved=True)
            assert doc['facts']['income_type']['value'] == 'dividend'
            report['live_model_fact_fields'] = len(doc['facts'])
            mutate('confirm')
            mutate('analyze')
            result = doc['analyses'][-1]
            assert result['retrieval_status'] == 'available' and not result['missing_locators']
            assert len(result['review_tasks']) == 5
            assert result['related_rulings']['status'] == 'available'
            assert len(result['related_rulings']['passages']) == 14
            assert result['professional_validation_status'] == 'unverified'
            assert checked(client.get(f'/api/cases/{case_id}')) == doc
            with engine.connect() as db:
                saved = db.execute(text('SELECT document FROM chat_cases WHERE id=:id AND owner=:owner'),
                                   {'id': case_id, 'owner': owner}).scalar_one()
                assert saved['analyses'][-1] == result
                assert db.execute(text("SELECT bool_and(relrowsecurity) FROM pg_class WHERE relname IN ('chat_cases','sources','legal_units') AND relnamespace='public'::regnamespace")).scalar() is True
            report['cloud_persisted_analysis'] = {
                'law_passages': len(result['passages']), 'ruling_sections': len(result['related_rulings']['passages']),
                'review_tasks': len(result['review_tasks']), 'rls_enabled': True,
            }
            print('cloud_analysis_persisted=True', flush=True)
            mutate('facts', facts={'dividend_amount': 110000})
            assert doc['analyses'][-1]['stale'] is True
            report['fact_edit_invalidates_analysis'] = True
        output = ROOT / 'reports/cloud-chat-verification.json'
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print('verification_complete=True', flush=True)
    except Exception as exc:
        print('verification_failed_type=' + type(exc).__name__, flush=True)
        if isinstance(exc, httpx.HTTPStatusError):
            print('http_status=', exc.response.status_code, flush=True)
        return 1
    finally:
        if case_id and owner:
            try:
                with engine.begin() as db:
                    db.execute(text('DELETE FROM chat_cases WHERE id=:id AND owner=:owner'), {'id': case_id, 'owner': owner})
                print('own_smoke_case_removed=True', flush=True)
            except Exception:
                print('own_smoke_case_cleanup_pending=True', flush=True)
        engine.dispose()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
