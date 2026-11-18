from types import SimpleNamespace
from uuid import uuid4
from fastapi import FastAPI
from fastapi.testclient import TestClient
from apps.api import auth, chat
from packages.chat.store import ChatStore
from tests.chat.auth_support import fixture_user
from copy import deepcopy
from decimal import Decimal
import pytest
from pydantic import TypeAdapter
from packages.contracts.income_tax import IncomeTaxCase
from packages.contracts.income_assessment import Assessment
from packages.income_tax.assessment import calculate


def facts():
    return dict(subject='individual',jurisdiction='cn',currency='CNY',residency='resident',
        period_start='2026-01-01',period_end='2026-12-31',facts_confirmed=True,claimed_deductions='0',carried_losses='0',
        incomes=[dict(category=k,source_jurisdiction=c,gross_amount=a,foreign_tax_paid=t,description='Verified gross CNY ordinary income')
        for k,c,a,t in [('employment','cn','60000','0'),('employment','sg','40000','1500'),('interest','sg','10000','500'),('business','hk','30000','500')]])


def basis():
    return dict(policy='cn_personal_foreign_2026',basis_confirmed=True,basis_explanation='Verified ordinary annual categories, country allocation and historical evidence.',prepaid_tax='3000',
        workpaper=dict(comprehensive_deductions='0',comprehensive_tax_reductions='0',business_tax_reductions='0',
            ordinary_categories_and_no_special_treatment_verified=True,source_fx_deductions_and_losses_verified=True,
            paid_tax_evidence_and_history_verified=True,countries=[dict(country=c,business_deductions='0',business_prior_losses='0',eligible_foreign_tax_paid=t,
            prior_excess=[dict(origin_year=2021,amount='1000')] if c=='sg' else []) for c,t in [('cn','0'),('sg','2000'),('hk','500')]]))


def run(data=None,paper=None):
    return calculate(IncomeTaxCase(**(data or facts())),TypeAdapter(Assessment).validate_python(paper or basis()))


def test_mixed_saved_income_computes_bases_tax_and_country_credit():
    r=run()
    assert Decimal(r['comprehensive_taxable_income'])==40000
    assert Decimal(r['business_taxable_income'])==30000
    assert Decimal(r['tax_before_foreign_credit'])==4980
    assert Decimal(r['allowed_credit'])==3092
    assert Decimal(r['final_tax'])==1888 and Decimal(r['balance_due'])==-1112
    sg=r['country_limits'][0]
    assert Decimal(sg['credit_limit'])==2592
    assert Decimal(sg['carryforward_history'][0]['expires_after_current_year'])==408


@pytest.mark.parametrize('issue',['subject','resident','period','deduction','loss','missing_country','duplicate','missing_paid','excess_paid','negative_business','rental','unverified'])
def test_inconsistent_saved_case_rejected(issue):
    d,p=facts(),basis();rows=p['workpaper']['countries']
    if issue=='subject':d['subject']='company';d['incomes']=[d['incomes'][-1]]
    elif issue=='resident':d['residency']='nonresident'
    elif issue=='period':d['period_start']='2025-01-01'
    elif issue=='deduction':d['claimed_deductions']='1'
    elif issue=='loss':d['carried_losses']='1'
    elif issue=='missing_country':rows.pop()
    elif issue=='duplicate':rows.append(deepcopy(rows[1]))
    elif issue=='missing_paid':d['incomes'][1]['foreign_tax_paid']=None
    elif issue=='excess_paid':rows[1]['eligible_foreign_tax_paid']='2001'
    elif issue=='negative_business':rows[2]['business_deductions']='30001';d['claimed_deductions']='30001'
    elif issue=='rental':d['incomes'][2]['category']='rental'
    else:p['workpaper']['paid_tax_evidence_and_history_verified']=False
    with pytest.raises(ValueError):run(d,p)


@pytest.mark.parametrize('with_transfers',[False,True])
def test_saved_api_restart_and_report_preserve_credit_pool(tmp_path,with_transfers):
    saved_facts,saved_basis=transfer_case() if with_transfers else (facts(),basis())
    url='sqlite:///'+str(tmp_path/'credit.sqlite');service=SimpleNamespace(store=ChatStore(url))
    app=FastAPI();app.include_router(auth.router);app.include_router(chat.router)
    app.dependency_overrides[auth.optional_user]=fixture_user
    app.dependency_overrides[chat.get_service]=lambda:service
    headers={'x-asiatax-request':'1'}
    with TestClient(app) as client:
        client.get('/api/auth/session');case=client.post('/api/cases',headers=headers).json()['id']
        path=f'/api/cases/{case}/income-tax'
        saved=client.put(path,headers=headers,json=dict(revision=0,request_id=str(uuid4()),inputs=saved_facts))
        assert saved.status_code==200,saved.text
        response=client.post(path+'/runs',headers=headers,json=dict(revision=1,request_id=str(uuid4()),basis=saved_basis))
        assert response.status_code==200,response.text
        record=response.json();service.store.engine.dispose();service.store=ChatStore(url)
        assert client.get(path+'/runs/'+record['id']).json()==record
        report=client.get(path+'/runs/'+record['id']+'/report?locale=en')
        assert report.status_code==200 and 'country_basis_reconciliation' in report.text
        for source in record['result']['sources']:assert source['sha256'] in report.text
        before=client.get(path).json();invalid=deepcopy(saved_basis);invalid['workpaper']['countries'][1]['eligible_foreign_tax_paid']='2001'
        rejected=client.post(path+'/runs',headers=headers,json=dict(revision=before['revision'],request_id=str(uuid4()),basis=invalid))
        assert rejected.status_code==422 and client.get(path).json()==before
    service.store.engine.dispose()

@pytest.mark.parametrize('category,factor',[('service_remuneration','0.8'),('author_remuneration','0.56'),('royalty','0.8')])
def test_six_decimal_saved_income_preserves_derived_expense_precision(category,factor):
    d=facts();d['incomes'][1].update(category=category,gross_amount='40000.000001')
    r=run(d,basis())
    expected=Decimal('40000.000001')*Decimal(factor)
    assert Decimal(r['country_basis_reconciliation'][1]['comprehensive_income_amount'])==expected
    assert Decimal(r['comprehensive_taxable_income'])==expected
    assert Decimal(r['final_tax']).is_finite()


def test_public_money_still_rejects_more_than_six_places():
    d=facts();d['incomes'][1]['gross_amount']='40000.0000001'
    with pytest.raises(ValueError,match='six decimal'):run(d,basis())


def test_derived_precision_is_independent_of_ambient_context():
    from decimal import localcontext
    d=facts();d['incomes'][1].update(category='author_remuneration',gross_amount='40000.000001')
    expected=run(d,basis())
    with localcontext() as ctx:
        ctx.prec=4
        assert run(d,basis())==expected


def transfer_case():
    d,p=facts(),basis();d['claimed_deductions']='2600'
    for _ in range(2):d['incomes'].append(dict(category='capital_gain',source_jurisdiction='sg',gross_amount='1000',foreign_tax_paid='0',description='One ordinary20percent sale; gross proceeds'))
    p['workpaper']['countries'][1]['prior_excess']=[]
    p['workpaper']['transfers']=[dict(income_index=n,original_cost=c,reasonable_transfer_expenses='100',allowed_donation='0',allowed_tax_reduction='0',single_transaction_source_and_ordinary_rate_verified=True,original_cost_expenses_and_reliefs_verified=True) for n,c in [(4,'400'),(5,'2000')]]
    return d,p


def test_saved_transfer_tax_adds_to_country_cap_without_netting_transaction_losses():
    d,p=transfer_case();r=run(d,p)
    assert Decimal(r['tax_before_foreign_credit'])==5080
    assert Decimal(r['country_limits'][0]['credit_limit'])==2692
    assert Decimal(r['final_tax'])==2580
    assert Decimal(r['property_transfers']['transactions'][1]['unoffset_loss'])==1100


@pytest.mark.parametrize('issue',['missing','deductions','wrong_income','unverified'])
def test_transfer_workpaper_must_reconcile_to_saved_income(issue):
    d,p=transfer_case()
    if issue=='missing':p['workpaper']['transfers'].pop()
    elif issue=='deductions':d['claimed_deductions']='2500'
    elif issue=='wrong_income':p['workpaper']['transfers'][0]['income_index']=0
    else:p['workpaper']['transfers'][0]['single_transaction_source_and_ordinary_rate_verified']=False
    with pytest.raises(ValueError):run(d,p)
