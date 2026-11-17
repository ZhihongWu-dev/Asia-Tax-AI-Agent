from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import TypeAdapter, ValidationError
from fastapi import FastAPI
from fastapi.testclient import TestClient
from apps.api import auth, chat
from packages.chat.store import ChatStore
from tests.chat.auth_support import fixture_user
from packages.contracts.income_assessment import Assessment
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.assessment import calculate


def facts():
    return dict(subject='individual',jurisdiction='jp',currency='JPY',
        period_start='2026-01-01',period_end='2026-12-31',residency='resident',
        facts_confirmed=True,claimed_deductions='960000',carried_losses='0',
        incomes=[dict(category='employment',source_jurisdiction='jp',gross_amount='6000000',description='Annual domestic salary')])


def basis():
    return dict(policy='jp_resident_ordinary_2026',basis_confirmed=True,
        basis_explanation='Annual salary-only national return; statutory deductions and withholding reconciled.',
        business_expenses='0',other_income_deductions='960000',income_tax_credits='0',
        salary_adjustment_eligible=False,withheld_tax='176100',estimated_tax='0',
        annual_domestic_ordinary_scope_confirmed=True,deductions_and_credits_verified=True)


def run(data=None,assertion=None):
    return calculate(IncomeTaxCase(**(data or facts())),TypeAdapter(Assessment).validate_python(assertion or basis()))


def test_saved_multiple_employers_aggregate_before_salary_deduction():
    data=facts();data['incomes'][0]['gross_amount']='3000000';data['incomes']*=2
    result=run(data)
    assert Decimal(result['final_tax']) == 141408
    assert Decimal(result['balance_due']) == -34692
    assert result['tax_scope'] == 'national_income_and_reconstruction_tax_only'


@pytest.mark.parametrize('changes',[dict(residency='nonresident'),dict(period_start='2026-04-01'),
    dict(subject='company'),dict(carried_losses='1'),dict(claimed_deductions='2000000')])
def test_case_scope_or_deduction_mismatch_rejected(changes):
    data=facts();data.update(changes)
    with pytest.raises((ValueError,ValidationError)):
        run(data)


@pytest.mark.parametrize('changes',[dict(category='dividend'),dict(source_jurisdiction='sg',foreign_tax_paid='0'),
    dict(foreign_tax_paid='1'),dict(gross_amount='6000000.5')])
def test_income_scope_rejected(changes):
    data=facts();data['incomes'][0].update(changes)
    with pytest.raises(ValueError):run(data)


def test_flags_cannot_be_coerced():
    assertion=basis();assertion['salary_adjustment_eligible']='false'
    with pytest.raises(ValidationError):run(assertion=assertion)


def test_business_example_uses_saved_revenue_and_reconciled_expenses():
    data=facts();data['incomes'][0].update(category='business',gross_amount='10000000')
    data['claimed_deductions']='7720000'
    assertion=basis();assertion.update(business_expenses='7000000',other_income_deductions='720000',withheld_tax='0')
    assert Decimal(run(data,assertion)['balance_due']) == 63300


def test_api_persists_national_scope_sources_and_refund_after_restart(tmp_path):
    url='sqlite:///'+str(tmp_path/'japan.sqlite')
    service=SimpleNamespace(store=ChatStore(url))
    app=FastAPI();app.include_router(auth.router);app.include_router(chat.router)
    app.dependency_overrides[auth.optional_user]=fixture_user
    app.dependency_overrides[chat.get_service]=lambda:service
    headers={'x-asiatax-request':'1'}
    with TestClient(app) as client:
        client.get('/api/auth/session')
        case_id=client.post('/api/cases',headers=headers).json()['id']
        path=f'/api/cases/{case_id}/income-tax'
        response=client.put(path,headers=headers,json=dict(revision=0,request_id=str(uuid4()),inputs=facts()))
        assert response.status_code==200,response.text
        intent=dict(revision=1,request_id=str(uuid4()),basis=basis())
        response=client.post(path+'/runs',headers=headers,json=intent)
        assert response.status_code==200,response.text
        saved=response.json()
        assert Decimal(saved['result']['balance_due'])==-34692
        assert saved['result']['local_tax_calculated'] is False
        assert len(saved['result']['sources'])==9
        service.store.engine.dispose();service.store=ChatStore(url)
        assert client.get(path+'/runs/'+saved['id']).json()==saved
        assert client.post(path+'/runs',headers=headers,json=intent).json()==saved
    service.store.engine.dispose()
