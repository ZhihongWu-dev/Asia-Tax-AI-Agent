from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import TypeAdapter, ValidationError

from apps.api import auth, chat
from packages.chat.store import ChatStore
from packages.contracts.income_assessment import Assessment
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.assessment import calculate
from tests.chat.auth_support import fixture_user


def facts():
    return dict(subject='individual',jurisdiction='kr',currency='KRW',residency='resident',
        period_start='2026-01-01',period_end='2026-12-31',facts_confirmed=True,
        claimed_deductions='0',carried_losses='0',incomes=[dict(category='employment',
            source_jurisdiction='kr',gross_amount='50000009',description='Aggregated ordinary salary')])


def basis():
    return dict(policy='kr_salary_standard_payroll_2026',basis_confirmed=True,
        basis_explanation='Ordinary domestic salary, standard credit election and employer receipts reconciled.',
        people=[dict(identifier='self',relationship='self',basic_eligible=True,
            senior_70_at_statutory_date=False,statutory_disability=False)],children=[],
        female_taxpayer=False,has_spouse=False,household_head=False,public_pension_paid='0',
        ordinary_salary_and_standard_credit_verified=True,family_eligibility_and_allocation_verified=True,
        pension_eligibility_verified=True,current_employer_withheld='3400000',former_employer_settled_tax='0',
        decision_and_employer_records_verified=True,local_current_employer_withheld='300000',
        local_former_employer_settled_tax='0',employer_special_collection_verified=True,installment=False)


def run(data=None,payload=None):
    return calculate(IncomeTaxCase(**(data or facts())),TypeAdapter(Assessment).validate_python(payload or basis()))


def test_saved_salary_drives_separate_authority_balances():
    result=run()
    assert Decimal(result['annual']['decision_tax'])==3387501
    assert Decimal(result['total_payable'])==38750
    assert Decimal(result['total_refundable'])==12490


def test_employers_aggregate_before_salary_deduction():
    data=facts();data['incomes'][0]['gross_amount']='25000000'
    data['incomes'].append({**data['incomes'][0],'gross_amount':'25000009'})
    assert run(data)==run()


@pytest.mark.parametrize('change',[dict(subject='company'),dict(residency='nonresident'),
    dict(claimed_deductions='1'),dict(carried_losses='1'),dict(period_start='2025-01-01'),
    dict(facts_confirmed=False)])
def test_case_mismatch_rejected(change):
    data=facts();data.update(change)
    with pytest.raises(ValueError):run(data)


@pytest.mark.parametrize('change',[dict(category='business'),dict(source_jurisdiction='jp'),dict(foreign_tax_paid='1')])
def test_other_income_cannot_enter_payroll(change):
    data=facts();data['incomes'][0].update(change)
    with pytest.raises(ValueError):run(data)


def test_pension_reconciles_saved_manual_deductions():
    data=facts();data['claimed_deductions']='2000000'
    payload=basis();payload['public_pension_paid']='2000000'
    assert Decimal(run(data,payload)['annual']['public_pension_deduction'])==2000000


def test_child_birth_date_is_typed_and_2017_exception_survives_contract():
    payload=basis()
    payload['people'].append(dict(identifier='child',relationship='descendant',basic_eligible=True,
        senior_70_at_statutory_date=False,statutory_disability=False))
    payload['children']=[dict(identifier='child',birth_date='2017-01-01',relationship='child',basic_deduction_eligible=True)]
    result=run(payload=payload)
    assert result['annual']['child_credit']['children'][0]['birth_2017_transition_excluded'] is True
    assert Decimal(result['annual']['child_credit']['regular_child_credit'])==0
    payload['children'][0]['birth_date']='2016-12-31'
    assert Decimal(run(payload=payload)['annual']['child_credit']['regular_child_credit'])==250000


@pytest.mark.parametrize('change',[dict(installment=1),dict(public_pension_paid=1.5),dict(unknown_credit='1')])
def test_strict_contract(change):
    payload=basis();payload.update(change)
    with pytest.raises(ValidationError):run(payload=payload)


def test_api_persists_salary_result_and_guards_ownership_and_revision(tmp_path):
    url='sqlite:///'+str(tmp_path/'salary.sqlite')
    service=SimpleNamespace(store=ChatStore(url))
    app=FastAPI();app.include_router(auth.router);app.include_router(chat.router)
    app.dependency_overrides[auth.optional_user]=fixture_user
    app.dependency_overrides[chat.get_service]=lambda:service
    headers={'x-asiatax-request':'1'}
    with TestClient(app) as alice,TestClient(app) as bob:
        alice.get('/api/auth/session');bob.get('/api/auth/session')
        case_id=alice.post('/api/cases',headers=headers).json()['id']
        path=f'/api/cases/{case_id}/income-tax'
        assert alice.put(path,headers=headers,json=dict(revision=0,request_id=str(uuid4()),inputs=facts())).status_code==200
        request=dict(revision=1,request_id=str(uuid4()),basis=basis())
        assert bob.post(path+'/runs',headers=headers,json=request).status_code==404
        response=alice.post(path+'/runs',headers=headers,json=request)
        assert response.status_code==200,response.text
        result=response.json()
        assert Decimal(result['result']['total_refundable'])==12490
        service.store.engine.dispose();service.store=ChatStore(url)
        assert alice.get(path+'/runs/'+result['id']).json()==result
        assert alice.post(path+'/runs',headers=headers,json=request).json()==result
        stale=deepcopy(request);stale['request_id']=str(uuid4())
        assert alice.post(path+'/runs',headers=headers,json=stale).status_code==409
        assert bob.get(path+'/runs/'+result['id']).status_code==404
    service.store.engine.dispose()
