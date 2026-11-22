from decimal import Decimal
import pytest
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.uae_foreign_assessment import assess


def fixture():
    case=IncomeTaxCase(subject='company',jurisdiction='ae',currency='AED',residency='resident',period_start='2026-01-01',period_end='2026-12-31',facts_confirmed=True,claimed_deductions='200000',carried_losses='0',incomes=[dict(category='royalty',source_jurisdiction='sg',gross_amount='1000000',foreign_tax_paid='100000',description='Synthetic taxable foreign royalty with linked expenses')])
    paper=dict(groups=[dict(source_id='royalty',income_indexes=[0],taxable_additions='0',linked_deductions='200000',exempt_income='0',eligible_foreign_tax='100000',source_treatment_and_eligibility_verified=True)],ordinary_resident_company_no_reliefs_verified=True,distinct_sources_and_linked_expenses_verified=True,foreign_tax_eligibility_treaty_and_fx_verified=True)
    return case,paper


def test_saved_gross_expenses_credit_and_prepaid_settle():
    case,p=fixture();r=assess(case,p,'1000')
    assert r['taxable_income']==800000
    assert r['gross_tax']==38250
    assert r['final_tax']==0
    assert r['forfeited_excess']==61750
    assert r['balance_due']==-1000


@pytest.mark.parametrize('change',['duplicate','missing','overclaim','deductions','exempt_credit','unverified','negative','loss'])
def test_unreconciled_saved_facts_rejected(change):
    case,p=fixture();g=p['groups'][0]
    if change=='duplicate': g['income_indexes']=[0,0]
    if change=='missing': g['income_indexes']=[1]
    if change=='overclaim': g['eligible_foreign_tax']='100001'
    if change=='deductions': case.claimed_deductions=Decimal(0)
    if change=='exempt_credit': g['exempt_income']='1'
    if change=='unverified': g['source_treatment_and_eligibility_verified']=False
    if change=='negative': g['exempt_income']='900000'
    if change=='loss': case.carried_losses=Decimal(1)
    with pytest.raises(ValueError): assess(case,p,'0')


def test_saved_api_reopen_reports_and_invalid_credit(tmp_path):
    from copy import deepcopy
    from types import SimpleNamespace
    from uuid import uuid4
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.api import auth,chat
    from packages.chat.store import ChatStore
    from tests.chat.auth_support import fixture_user
    case,p=fixture()
    basis=dict(policy='ae_company_foreign_direct_2026',workpaper=p,prepaid_tax='1000',
        basis_confirmed=True,basis_explanation='Verified taxable royalty, linked expenses and same-income direct foreign tax')
    url='sqlite:///'+str(tmp_path/'uae.sqlite')
    service=SimpleNamespace(store=ChatStore(url))
    app=FastAPI();app.include_router(auth.router);app.include_router(chat.router)
    app.dependency_overrides[auth.optional_user]=fixture_user
    app.dependency_overrides[chat.get_service]=lambda:service
    headers={'x-asiatax-request':'1'}
    try:
        with TestClient(app) as client:
            client.get('/api/auth/session')
            created=client.post('/api/cases',headers=headers)
            assert created.status_code==201,created.text
            path=f"/api/cases/{created.json()['id']}/income-tax"
            saved=client.put(path,headers=headers,json=dict(revision=0,request_id=str(uuid4()),inputs=case.model_dump(mode='json')))
            assert saved.status_code==200,saved.text
            request=dict(revision=saved.json()['revision'],request_id=str(uuid4()),basis=basis)
            response=client.post(path+'/runs',headers=headers,json=request)
            assert response.status_code==200,response.text
            run=response.json()
            assert Decimal(run['result']['final_tax'])==0
            assert Decimal(run['result']['forfeited_excess'])==61750
            assert Decimal(run['result']['balance_due'])==-1000
            reports={}
            for locale in ('en','zh'):
                report=client.get(path+'/runs/'+run['id']+'/report?locale='+locale)
                assert report.status_code==200,report.text
                reports[locale]=report.json()['markdown']
                assert ('UAE income-by-income foreign credit' if locale=='en' else '阿联酋逐项境外抵免') in reports[locale]
                assert ('Forfeited excess' if locale=='en' else '不可结转余额') in reports[locale]
                assert '| royalty | SG | 800000 | 100000 | 38250 | 38250 | 61750 |' in reports[locale]
                assert run['snapshot_hash'] in reports[locale]
                for source in run['result']['sources']: assert source['sha256'] in reports[locale]
            service.store.engine.dispose();service.store=ChatStore(url)
            assert client.get(path+'/runs/'+run['id']).json()==run
            assert client.post(path+'/runs',headers=headers,json=request).json()==run
            current=client.get(path).json()
            invalid=deepcopy(request)
            invalid.update(revision=current['revision'],request_id=str(uuid4()))
            invalid['basis']['workpaper']['groups'][0]['eligible_foreign_tax']='100001'
            rejected=client.post(path+'/runs',headers=headers,json=invalid)
            assert rejected.status_code==422,rejected.text
            assert client.get(path).json()==current
            for locale,original in reports.items():
                assert client.get(path+'/runs/'+run['id']+'/report?locale='+locale).json()['markdown']==original
    finally:
        service.store.engine.dispose()
