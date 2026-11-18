from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import TypeAdapter
from apps.api import auth, chat
from packages.chat.store import ChatStore
from packages.contracts.income_tax import IncomeTaxCase
from packages.contracts.income_assessment import Assessment
from packages.income_tax.assessment import calculate
from tests.chat.auth_support import fixture_user


def facts():
    return dict(subject='company',jurisdiction='cn',currency='CNY',residency='resident',
        period_start='2026-01-01',period_end='2026-12-31',facts_confirmed=True,
        claimed_deductions='0',carried_losses='0',incomes=[dict(category='business' if c=='cn' else 'dividend',
        source_jurisdiction=c,gross_amount='1000',foreign_tax_paid=t,
        description='Established gross income before withholding') for c,t in [('cn','0'),('sg','400'),('hk','100')]])


def basis():
    return dict(policy='cn_company_foreign_direct_2026',basis_confirmed=True,
        basis_explanation='Verified gross CNY amounts, eligible direct tax, election history and source allocation.',prepaid_tax='500',
        workpaper=dict(method='per_country',allocations=[dict(country=c,deductions='0',exempt_income='0',
            non_taxable_income='0',eligible_prior_losses='0',eligible_direct_tax=t) for c,t in [('cn','0'),('sg','400'),('hk','100')]],
            ordinary_25_percent_positive_bases_verified=True,income_tax_eligibility_and_fx_verified=True,
            method_lock_and_carryforward_history_verified=True,direct_tax_only_no_other_reliefs_verified=True,
            gross_before_withholding_and_expense_allocation_verified=True))


def run(data,paper):
    return calculate(IncomeTaxCase(**data),TypeAdapter(Assessment).validate_python(paper))


def test_reconciled_bases_preserve_country_cap_and_negative_payment_balance():
    r=run(facts(),basis())
    assert Decimal(r['final_tax'])==400 and Decimal(r['balance_due'])==-100
    assert Decimal(r['allowed_foreign_tax_credit'])==350
    assert len(r['country_basis_reconciliation'])==3


def test_deductions_and_income_losses_allocated_once():
    data=facts();data.update(claimed_deductions='100',carried_losses='50')
    p=basis();p['workpaper']['allocations'][1].update(deductions='100',eligible_prior_losses='50')
    r=run(data,p)
    assert Decimal(r['foreign_taxable_income'])==1850
    assert Decimal(r['pools'][0]['credit_limit'])==Decimal('212.5')
    assert Decimal(r['final_tax'])==400


@pytest.mark.parametrize('mutation',['missing_country','duplicate_country','missing_paid','excess_credit','deduction_mismatch','loss_mismatch','negative_base','domestic_credit','nonresident','individual','wrong_period','unconfirmed'])
def test_inconsistent_saved_facts_rejected(mutation):
    data=facts();p=basis();rows=p['workpaper']['allocations']
    if mutation=='missing_country':rows.pop()
    elif mutation=='duplicate_country':rows.append(deepcopy(rows[1]))
    elif mutation=='missing_paid':data['incomes'][1]['foreign_tax_paid']=None
    elif mutation=='excess_credit':rows[1]['eligible_direct_tax']='401'
    elif mutation=='deduction_mismatch':rows[1]['deductions']='1'
    elif mutation=='loss_mismatch':rows[1]['eligible_prior_losses']='1'
    elif mutation=='negative_base':rows[1]['deductions']='1001';data['claimed_deductions']='1001'
    elif mutation=='domestic_credit':rows[0]['eligible_direct_tax']='1';data['incomes'][0]['foreign_tax_paid']='1'
    elif mutation=='nonresident':data['residency']='nonresident'
    elif mutation=='individual':data['subject']='individual'
    elif mutation=='wrong_period':data['period_start']='2025-01-01'
    else:p['workpaper']['direct_tax_only_no_other_reliefs_verified']=False
    with pytest.raises(ValueError):run(data,p)


def test_saved_api_restart_and_report_preserve_credit_pool(tmp_path):
    url='sqlite:///'+str(tmp_path/'credit.sqlite');service=SimpleNamespace(store=ChatStore(url))
    app=FastAPI();app.include_router(auth.router);app.include_router(chat.router)
    app.dependency_overrides[auth.optional_user]=fixture_user
    app.dependency_overrides[chat.get_service]=lambda:service
    headers={'x-asiatax-request':'1'}
    with TestClient(app) as client:
        client.get('/api/auth/session');case=client.post('/api/cases',headers=headers).json()['id']
        path=f'/api/cases/{case}/income-tax'
        saved=client.put(path,headers=headers,json=dict(revision=0,request_id=str(uuid4()),inputs=facts()))
        assert saved.status_code==200,saved.text
        response=client.post(path+'/runs',headers=headers,json=dict(revision=1,request_id=str(uuid4()),basis=basis()))
        assert response.status_code==200,response.text
        record=response.json();service.store.engine.dispose();service.store=ChatStore(url)
        assert client.get(path+'/runs/'+record['id']).json()==record
        report=client.get(path+'/runs/'+record['id']+'/report?locale=en')
        assert report.status_code==200 and 'country_basis_reconciliation' in report.text
        for source in record['result']['sources']:assert source['sha256'] in report.text
        before=client.get(path).json();invalid=basis();invalid['workpaper']['allocations'][1]['eligible_direct_tax']='401'
        rejected=client.post(path+'/runs',headers=headers,json=dict(revision=before['revision'],request_id=str(uuid4()),basis=invalid))
        assert rejected.status_code==422 and client.get(path).json()==before
    service.store.engine.dispose()
