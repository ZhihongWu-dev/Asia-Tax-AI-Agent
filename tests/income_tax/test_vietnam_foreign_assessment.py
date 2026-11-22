from copy import deepcopy
from decimal import Decimal
import hashlib
from pathlib import Path
import pytest
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.vietnam_foreign_assessment import assess,TREATIES


def fixture(country='cn',category='business'):
    case=dict(subject='company',jurisdiction='vn',currency='VND',residency='resident',
        period_start='2026-01-01',period_end='2026-12-31',facts_confirmed=True,
        claimed_deductions='90000000000',carried_losses='0',incomes=[
            dict(category='business',source_jurisdiction='vn',gross_amount='80000000000',description='Domestic receipts'),
            dict(category=category,source_jurisdiction=country,gross_amount='20000000000',foreign_tax_paid='700000000',description='Foreign receipts')])
    p=dict(groups=[dict(source_id='home',income_indexes=[0],allowable_expenses='72000000000',eligible_foreign_tax_paid='0'),
        dict(source_id='foreign',income_indexes=[1],allowable_expenses='18000000000',eligible_foreign_tax_paid='700000000')],
        previous_full_year_statutory_revenue='100000000000',current_full_year_statutory_revenue='100000000000',
        vietnam_establishment_ordinary20_and_full_calendar_periods_verified=True,
        statutory_revenue_and_no_exemptions_incentives_or_losses_verified=True,
        source_basis_expenses_and_no_foreign_tax_deduction_verified=True,
        treaty_source_entitlement_mli_payment_fx_and_filing_verified=True,
        no_other_sparing_underlying_topup_or_special_tax_claims_verified=True)
    return case,p


@pytest.mark.parametrize('country',list(TREATIES))
def test_all_ten_foreign_business_sources_cap_paid_tax_and_preserve_sources(country):
    case,p=fixture(country)
    r=assess(IncomeTaxCase.model_validate(case),p,'1700000000')
    assert r['taxable_income']==10000000000
    assert r['gross_tax']==2000000000
    assert r['allowed_foreign_tax_credit']==400000000
    assert r['final_tax']==1600000000
    assert r['balance_due']==-100000000
    root=Path(__file__).resolve().parents[2]
    for source in r['sources']:
        assert hashlib.sha256((root/source['file']).read_bytes()).hexdigest()==source['sha256']


@pytest.mark.parametrize('country,method,basis',[('sg','singapore_deemed_floor',2000000000),('id','indonesia_deemed_replacement',3000000000)])
def test_special_treaty_credit_measure_is_not_silently_replaced_by_paid_tax(country,method,basis):
    case,p=fixture(country,'royalty');p['groups'][1]['eligible_foreign_tax_paid']='100000000'
    r=assess(IncomeTaxCase.model_validate(case),p,0)
    assert r['source_credits'][1]['method']==method
    assert r['source_credits'][1]['credit_basis']==basis
    assert r['allowed_foreign_tax_credit']==400000000


@pytest.mark.parametrize('change',['prior_threshold','current_threshold','revenue','deductions','duplicate','omitted','mixed',
    'negative_index','loss','paid','missing_paid','domestic_paid','unconfirmed','evidence','dividend'])
def test_unreconciled_or_unreviewed_cases_rejected(change):
    case,p=fixture();g=p['groups'][1]
    if change=='prior_threshold':p['previous_full_year_statutory_revenue']='50000000000'
    elif change=='current_threshold':p['current_full_year_statutory_revenue']='10000000000'
    elif change=='revenue':p['current_full_year_statutory_revenue']='100000000001'
    elif change=='deductions':case['claimed_deductions']='89999999999'
    elif change=='duplicate':g['income_indexes']=[1,1]
    elif change=='omitted':p['groups']=[g]
    elif change=='mixed':g['income_indexes']=[0,1];p['groups']=[g];g['allowable_expenses']=case['claimed_deductions']
    elif change=='negative_index':g['income_indexes']=[-1]
    elif change=='loss':g['allowable_expenses']='21000000000';p['groups'][0]['allowable_expenses']='69000000000'
    elif change=='paid':g['eligible_foreign_tax_paid']='700000001'
    elif change=='missing_paid':case['incomes'][1].pop('foreign_tax_paid')
    elif change=='domestic_paid':case['incomes'][0]['foreign_tax_paid']='1'
    elif change=='unconfirmed':case['facts_confirmed']=False
    elif change=='dividend':case['incomes'][1]['category']='dividend'
    else:p['treaty_source_entitlement_mli_payment_fx_and_filing_verified']=False
    with pytest.raises(ValueError):assess(IncomeTaxCase.model_validate(case),p,0)


def test_split_saved_receipts_do_not_change_country_source_assessment():
    case,p=fixture();expected=assess(IncomeTaxCase.model_validate(case),p,0)
    extra=deepcopy(case['incomes'][1]);extra.update(gross_amount='10000000000',foreign_tax_paid='350000000')
    case['incomes'][1].update(gross_amount='10000000000',foreign_tax_paid='350000000')
    case['incomes'].append(extra);p['groups'][1]['income_indexes']=[1,2]
    assert assess(IncomeTaxCase.model_validate(case),p,0)==expected


@pytest.mark.parametrize('country,category',[('cn','business'),('sg','royalty'),('id','interest')])
def test_saved_api_reopen_replay_and_reports(tmp_path,country,category):
    from types import SimpleNamespace
    from uuid import uuid4
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.api import auth,chat
    from packages.chat.store import ChatStore
    from tests.chat.auth_support import fixture_user
    case,p=fixture(country,category)
    basis=dict(policy='vn_company_foreign_ordinary20_2026',workpaper=p,prepaid_tax='1700000000',
        basis_confirmed=True,basis_explanation='Verified full-year ordinary revenues, source expenses and treaty payment evidence.')
    url='sqlite:///'+str(tmp_path/'vietnam.db')
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
            case_path=f"/api/cases/{created.json()['id']}"
            path=case_path+'/income-tax'
            saved=client.put(path,headers=headers,json=dict(revision=0,request_id=str(uuid4()),inputs=case))
            assert saved.status_code==200,saved.text
            request=dict(revision=saved.json()['revision'],request_id=str(uuid4()),basis=basis)
            response=client.post(path+'/runs',headers=headers,json=request)
            assert response.status_code==200,response.text
            run=response.json()
            assert Decimal(run['result']['final_tax'])==1600000000
            assert Decimal(run['result']['balance_due'])==-100000000
            reports={}
            for locale,heading in [('zh','越南境外抵免明细'),('en','Vietnam foreign credit details')]:
                report=client.get(path+'/runs/'+run['id']+'/report?locale='+locale)
                assert report.status_code==200,report.text
                reports[locale]=report.json()['markdown']
                assert heading in reports[locale]
                for source in run['result']['sources']:assert source['sha256'] in reports[locale]
            service.store.engine.dispose();service.store=ChatStore(url)
            assert client.get(path+'/runs/'+run['id']).json()==run
            assert client.post(path+'/runs',headers=headers,json=request).json()==run
            invalid=deepcopy(request)
            invalid.update(revision=client.get(case_path).json()['revision'],request_id=str(uuid4()))
            invalid['basis']['workpaper']['groups'][1]['eligible_foreign_tax_paid']='700000001'
            rejected=client.post(path+'/runs',headers=headers,json=invalid)
            assert rejected.status_code==422,rejected.text
            assert rejected.json()=={'detail':'invalid_facts'}
            for locale,original in reports.items():
                assert client.get(path+'/runs/'+run['id']+'/report?locale='+locale).json()['markdown']==original
    finally:service.store.engine.dispose()
