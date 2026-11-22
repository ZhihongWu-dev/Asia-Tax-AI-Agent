"""User-authorized synthetic business scenarios; not customer sign-off."""
from copy import deepcopy
from decimal import Decimal
import json
import os
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from apps.api import auth, chat
from packages.chat.store import ChatStore
from tests.chat.auth_support import fixture_user

CASES = json.loads(Path(__file__).with_name('synthetic_business_cases_20261119.json').read_text(encoding='utf-8'))

@pytest.mark.parametrize('scenario', CASES, ids=[s['id'] for s in CASES])
def test_synthetic_business_round_trip(tmp_path, scenario):
    url = 'sqlite:///' + str(tmp_path/'acceptance.sqlite')
    service = SimpleNamespace(store=ChatStore(url))
    app = FastAPI(); app.include_router(auth.router); app.include_router(chat.router)
    app.dependency_overrides[auth.optional_user] = fixture_user
    app.dependency_overrides[chat.get_service] = lambda: service
    headers = {'x-asiatax-request':'1'}
    with TestClient(app) as client:
        client.get('/api/auth/session')
        created = client.post('/api/cases', headers=headers)
        assert created.status_code == 201, created.text
        path = '/api/cases/'+created.json()['id']+'/income-tax'
        saved = client.put(path, headers=headers, json=dict(revision=0, request_id=str(uuid4()), inputs=scenario['inputs']))
        assert saved.status_code == 200, saved.text
        payload = dict(revision=1, request_id=str(uuid4()), basis=scenario['basis'])
        calculated = client.post(path+'/runs', headers=headers, json=payload)
        assert calculated.status_code == 200, calculated.text
        run = calculated.json(); observed = {}
        for key, expected in scenario['expected'].items():
            value = run['result']
            for part in key.split('.'): value = value[part]
            assert Decimal(value) == Decimal(expected), (key, value, expected)
            observed[key] = value
        if scenario['id'] == 'company_cross_border':
            jp = next(c for c in run['result']['pools'] if c['pool']=='jp')
            assert Decimal(jp['current_excess']) == 15000
            assert jp['current_excess_last_usable_year'] == 2031
        if scenario['id'] == 'personal_mixed_income':
            sg = next(c for c in run['result']['country_limits'] if c['country']=='sg')
            assert Decimal(sg['credit_limit']) == 5792
            assert Decimal(sg['carryforward_history'][0]['expires_after_current_year']) == 208
        service.store.engine.dispose(); service.store = ChatStore(url)
        assert client.get(path+'/runs/'+run['id']).json() == run
        assert client.post(path+'/runs', headers=headers, json=payload).json() == run
        reports = {}
        for locale in ('zh','en'):
            report = client.get(path+'/runs/'+run['id']+'/report?locale='+locale)
            assert report.status_code == 200, report.text
            reports[locale] = report.json()['markdown']
            assert run['snapshot_hash'] in reports[locale]
            for source in run['result']['sources']: assert source['sha256'] in reports[locale]
        before = client.get(path).json()
        invalid = deepcopy(scenario['basis'])
        if scenario['id'] == 'company_cross_border':
            invalid['workpaper']['allocations'][1]['eligible_direct_tax'] = '60001'
        elif scenario['id'] == 'personal_mixed_income':
            invalid['workpaper']['countries'][1]['eligible_foreign_tax_paid'] = '5001'
        else:
            invalid['osaka_local']['wards'][1]['ward_name'] = '北区'
        rejected = client.post(path+'/runs', headers=headers, json=dict(revision=before['revision'], request_id=str(uuid4()), basis=invalid))
        assert rejected.status_code == 422, rejected.text
        assert client.get(path).json() == before
        amended_inputs = deepcopy(scenario['inputs'])
        amended_inputs['incomes'][0]['gross_amount'] = str(Decimal(amended_inputs['incomes'][0]['gross_amount']) + 1000)
        amended = client.put(path, headers=headers, json=dict(revision=before['revision'], request_id=str(uuid4()), inputs=amended_inputs))
        assert amended.status_code == 200, amended.text
        after = client.get(path).json()
        assert after['income_tax_result'] is None
        service.store.engine.dispose(); service.store = ChatStore(url)
        assert client.get(path+'/runs/'+run['id']).json() == run
        replay = client.post(path+'/runs', headers=headers, json=payload)
        assert replay.status_code == 200 and replay.json() == run
        assert client.get(path).json() == after
        for locale, original in reports.items():
            assert client.get(path+'/runs/'+run['id']+'/report?locale='+locale).json()['markdown'] == original
        if output := os.environ.get('SYNTHETIC_CASE_OUTPUT'):
            target = Path(output)/scenario['id']; target.mkdir(parents=True, exist_ok=True)
            for locale, content in reports.items(): (target/f'report-{locale}.md').write_text(content, encoding='utf-8')
            (target/'result.json').write_text(json.dumps(dict(synthetic=True,scenario=scenario,observed=observed,run=run,checks=['HTTP save/calculate','independent expected amounts','SQLite reopen','request replay','bilingual report and source hashes','invalid basis preserves state']),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    service.store.engine.dispose()
