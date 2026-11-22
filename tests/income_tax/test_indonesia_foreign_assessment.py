from decimal import Decimal, localcontext
import pytest
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.indonesia_foreign_assessment import assess


def fixture():
    case=IncomeTaxCase(subject='company',jurisdiction='id',currency='IDR',residency='resident',
        period_start='2026-01-01',period_end='2026-12-31',facts_confirmed=True,
        claimed_deductions='1000000000',carried_losses='0',incomes=[
            dict(category='business',source_jurisdiction='id',gross_amount='5000000000',foreign_tax_paid='0',description='Synthetic domestic ordinary business'),
            dict(category='business',source_jurisdiction='jp',gross_amount='1000000000',foreign_tax_paid='300000000',description='Synthetic foreign ordinary branch'),
            dict(category='interest',source_jurisdiction='sg',gross_amount='3000000000',foreign_tax_paid='450000000',description='Synthetic taxable foreign interest')])
    groups=[]
    for n in range(3):
        groups.append(dict(source_id=f'source{n}',income_indexes=[n],additions='0',allowed_expenses='1000000000' if n==0 else '0',exempt_income='0',
            creditable_foreign_tax=['0','300000000','450000000'][n],treaty_applies=n>0,
            treaty_permitted_tax=[None,'300000000','300000000'][n],separate_source_and_taxable_treatment_verified=True))
    return case,dict(groups=groups,prior_credit_reduction_or_refund='0',
        ordinary_resident_no_final_special_or_carried_losses_verified=True,complete_article31e_gross_receipts_verified=True,
        source_period_expenses_and_fx_verified=True,treaty_entitlement_and_tax_evidence_verified=True,
        recapture_of_previously_credited_tax_verified=True)


def test_2026_article31e_uses_domestic_and_foreign_gross():
    case,p=fixture();r=assess(case,p,'1000000000')
    assert r['article31e']['article31e_gross_receipts']==9000000000
    assert r['taxable_income']==8000000000
    assert r['gross_tax']==Decimal('1290666740')
    assert r['allowed_foreign_tax_credit']==Decimal('461333342.5')
    assert r['final_tax']==Decimal('829333397.5')
    assert r['balance_due']==Decimal('-170666602.5')


def test_foreign_loss_is_excluded_before_country_aggregation():
    case,p=fixture()
    p['groups'][1]['allowed_expenses']='1200000000'
    case.claimed_deductions=Decimal('2200000000')
    r=assess(case,p,'0')
    assert r['taxable_income']==7000000000
    assert r['source_reconciliation'][1]['excluded_foreign_loss']==200000000
    assert r['source_credits'][0]['net_taxable_income']==0


def test_domestic_loss_and_recapture_remain_distinct():
    case,p=fixture()
    p['groups'][0]['allowed_expenses']='6000000000'
    case.claimed_deductions=Decimal('6000000000')
    p['prior_credit_reduction_or_refund']='5000000'
    r=assess(case,p,'0')
    assert r['taxable_income']==3000000000
    with localcontext() as ctx:
        ctx.prec=40
        assert r['final_tax']==r['tax_after_credit']+5000000


def test_exempt_foreign_receipt_stays_in_turnover_without_creating_credit():
    case,p=fixture()
    p['groups'][2].update(exempt_income='3000000000',creditable_foreign_tax='0',treaty_permitted_tax='0')
    r=assess(case,p,'0')
    assert r['article31e']['article31e_gross_receipts']==9000000000
    assert r['taxable_income']==5000000000
    assert r['gross_tax']==806666740
    assert r['allowed_foreign_tax_credit']==161333348
    assert r['final_tax']==645333392
    assert next(row for row in r['source_credits'] if row['country']=='sg')['credit_before_overall_cap']==0


def test_zero_current_tax_does_not_erase_prior_credit_recapture():
    case,p=fixture()
    p['groups'][0]['allowed_expenses']='10000000000'
    case.claimed_deductions=Decimal('10000000000')
    p['prior_credit_reduction_or_refund']='5000000'
    r=assess(case,p,'7000000')
    assert r['taxable_income']==0
    assert r['allowed_foreign_tax_credit']==0
    assert r['annual_liability']==5000000
    assert r['balance_due']==-2000000


def test_splitting_one_receipt_and_reordering_groups_preserves_liability():
    case,p=fixture()
    baseline=assess(case,p,'1000000000')
    original=case.incomes[1]
    case.incomes[1]=original.model_copy(update={'gross_amount':Decimal('400000000'),'foreign_tax_paid':Decimal('120000000')})
    case.incomes.append(original.model_copy(update={'gross_amount':Decimal('600000000'),'foreign_tax_paid':Decimal('180000000')}))
    p['groups'][1]['income_indexes']=[1,3]
    p['groups'].reverse()
    actual=assess(case,p,'1000000000')
    for key in ('taxable_income','gross_tax','allowed_foreign_tax_credit','final_tax','balance_due','article31e'):
        assert actual[key]==baseline[key]


@pytest.mark.parametrize('change',['duplicate','missing','overclaim','deductions','exempt_credit','unverified','carried_loss','missing_treaty'])
def test_saved_inputs_cannot_bypass_reconciliation(change):
    case,p=fixture();g=p['groups'][1]
    if change=='duplicate':g['income_indexes']=[0]
    if change=='missing':g['income_indexes']=[3]
    if change=='overclaim':g['creditable_foreign_tax']='300000001'
    if change=='deductions':case.claimed_deductions=Decimal(0)
    if change=='exempt_credit':g['exempt_income']='1'
    if change=='unverified':p['complete_article31e_gross_receipts_verified']=False
    if change=='carried_loss':case.carried_losses=Decimal(1)
    if change=='missing_treaty':g['treaty_permitted_tax']=None
    with pytest.raises(ValueError):assess(case,p,'0')


def test_saved_api_reopen_replay_and_invalid_claim_atomicity(tmp_path):
    from copy import deepcopy
    from types import SimpleNamespace
    from uuid import uuid4
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.api import auth, chat
    from packages.chat.store import ChatStore
    from tests.chat.auth_support import fixture_user
    case, p = fixture()
    basis = dict(policy='id_company_foreign_direct_2026', workpaper=p, prepaid_tax='1000000000',
        basis_confirmed=True, basis_explanation='Verified source expenses, Article31E gross receipts and foreign treaty ceilings')
    url = 'sqlite:///' + str(tmp_path/'id-foreign.sqlite')
    service = SimpleNamespace(store=ChatStore(url))
    app = FastAPI()
    app.include_router(auth.router)
    app.include_router(chat.router)
    app.dependency_overrides[auth.optional_user] = fixture_user
    app.dependency_overrides[chat.get_service] = lambda: service
    headers = {'x-asiatax-request': '1'}
    try:
        with TestClient(app) as client:
            client.get('/api/auth/session')
            created = client.post('/api/cases', headers=headers)
            assert created.status_code == 201, created.text
            path = f"/api/cases/{created.json()['id']}/income-tax"
            saved = client.put(path, headers=headers, json=dict(revision=0, request_id=str(uuid4()),
                inputs=case.model_dump(mode='json')))
            assert saved.status_code == 200, saved.text
            request = dict(revision=saved.json()['revision'], request_id=str(uuid4()), basis=basis)
            response = client.post(path+'/runs', headers=headers, json=request)
            assert response.status_code == 200, response.text
            run = response.json()
            assert Decimal(run['result']['final_tax']) == Decimal('829333397.5')
            assert Decimal(run['result']['balance_due']) == Decimal('-170666602.5')
            reports = {}
            for locale in ('en', 'zh'):
                report = client.get(path+'/runs/'+run['id']+'/report?locale='+locale)
                assert report.status_code == 200, report.text
                reports[locale] = report.json()['markdown']
                assert run['snapshot_hash'] in reports[locale]
                assert ('Indonesia foreign credits by country and income type' if locale == 'en' else '印尼分国分类境外抵免') in reports[locale]
                assert (r'Prior\-credit recapture' if locale == 'en' else '以前抵免补回') in reports[locale]
                assert '| JP | business |' in reports[locale]
                for source in run['result']['sources']:
                    assert source['sha256'] in reports[locale]
            service.store.engine.dispose()
            service.store = ChatStore(url)
            assert client.get(path+'/runs/'+run['id']).json() == run
            assert client.post(path+'/runs', headers=headers, json=request).json() == run
            current = client.get(path).json()
            invalid = deepcopy(request)
            invalid.update(revision=current['revision'], request_id=str(uuid4()))
            invalid['basis']['workpaper']['groups'][1]['creditable_foreign_tax'] = '300000001'
            rejected = client.post(path+'/runs', headers=headers, json=invalid)
            assert rejected.status_code == 422, rejected.text
            assert client.get(path).json() == current
            for locale, original in reports.items():
                assert client.get(path+'/runs/'+run['id']+'/report?locale='+locale).json()['markdown'] == original
    finally:
        service.store.engine.dispose()
