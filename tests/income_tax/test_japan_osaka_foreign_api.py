from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from apps.api import auth,chat
from packages.chat.store import ChatStore
from tests.chat.auth_support import fixture_user
from tests.income_tax.test_japan_foreign_reconciliation import fixture
from tests.income_tax.test_japan_osaka_foreign import paper


@pytest.mark.parametrize('country',['sg','cn','id'])
def test_saved_osaka_foreign_api_reopen_replay_and_bilingual_reports(tmp_path,country):
    case,source=fixture(country);local=paper()
    local['corporation_interim_liability']=14000000
    basis=dict(policy='jp_osaka_company_foreign_starting_2026',source_workpaper=source,
        local_workpaper=local,rate_regime='ordinary',rate_classification_verified=True,
        no_other_tax_credits_additions_or_history_verified=True,
        basis_confirmed=True,basis_explanation='Verified saved ordinary foreign receipts, source tax and Osaka local workpapers.')
    url='sqlite:///'+str(tmp_path/'osaka.db')
    service=SimpleNamespace(store=ChatStore(url))
    app=FastAPI();app.include_router(auth.router);app.include_router(chat.router)
    app.dependency_overrides[auth.optional_user]=fixture_user
    app.dependency_overrides[chat.get_service]=lambda:service
    headers={'x-asiatax-request':'1'}
    try:
        with TestClient(app) as client:
            client.get('/api/auth/session')
            created=client.post('/api/cases',headers=headers)
            assert created.status_code==201
            case_path=f"/api/cases/{created.json()['id']}";path=case_path+'/income-tax'
            saved=client.put(path,headers=headers,json=dict(revision=0,request_id=str(uuid4()),inputs=case))
            assert saved.status_code==200,saved.text
            request=dict(revision=saved.json()['revision'],request_id=str(uuid4()),basis=basis)
            response=client.post(path+'/runs',headers=headers,json=request)
            assert response.status_code==200,response.text
            run=response.json();r=run['result']
            assert r['total_annual_liability']=='27348500'
            assert r['total_refundable']=='80000'
            assert r['total_payable']=='13428500'
            assert len(r['settlements'])==9
            reports={}
            for locale,heading in [('zh','日本大阪跨境企业结算'),('en','Japan Osaka cross-border company settlement')]:
                report=client.get(path+'/runs/'+run['id']+'/report?locale='+locale)
                assert report.status_code==200,report.text
                text=report.json()['markdown'];reports[locale]=text
                assert heading in text
                assert ('结转资格待核验' if locale=='zh' else 'carryforward eligibility unverified') in text
                assert '823360' in text and '80000' in text and '371200' in text
                for s in r['sources']:assert s['sha256'] in text
            service.store.engine.dispose();service.store=ChatStore(url)
            assert client.get(path+'/runs/'+run['id']).json()==run
            assert client.post(path+'/runs',headers=headers,json=request).json()==run
            invalid=deepcopy(request)
            invalid.update(revision=client.get(case_path).json()['revision'],request_id=str(uuid4()))
            invalid['basis']['source_workpaper']['groups'][1]['eligible_foreign_corporate_tax']='12000001'
            rejected=client.post(path+'/runs',headers=headers,json=invalid)
            assert rejected.status_code==422,rejected.text
            assert rejected.json()=={'detail':'invalid_facts'}
            for locale,text in reports.items():
                assert client.get(path+'/runs/'+run['id']+'/report?locale='+locale).json()['markdown']==text
    finally:service.store.engine.dispose()
