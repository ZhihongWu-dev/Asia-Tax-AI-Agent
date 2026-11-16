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
    return dict(subject='individual', jurisdiction='vn', currency='VND',
        period_start='2026-01-01', period_end='2026-12-31', residency='resident',
        facts_confirmed=True, claimed_deductions='186000000', carried_losses='0',
        incomes=[dict(category='employment', source_jurisdiction='vn',
            gross_amount='786000000', description='Annual domestic salary')])


def basis():
    return dict(policy='vn_employment_2026', basis_confirmed=True,
        basis_explanation='Chargeable pay and deductible amounts reconciled to supporting records.',
        chargeable_employment_income='786000000', full_calendar_year_confirmed=True,
        dependent_months=[], deductible_insurance='0', article11_deductions='0',
        prepaid_tax='80000000', income_and_deductions_verified=True)


def run(data=None, assertion=None):
    return calculate(IncomeTaxCase(**(data or facts())),
        TypeAdapter(Assessment).validate_python(assertion or basis()))


def test_saved_case_routes_to_exact_serializable_result_with_sources():
    result = run()
    assert Decimal(result['final_tax']) == 78000000
    assert Decimal(result['balance_due']) == -2000000
    assert result['sources'][0]['doc_id'] == 'vn.law.pit2026.vi'
    assert result['bands'][0]['tax'] == '6000000.00'


@pytest.mark.parametrize('field,value', [('residency','nonresident'),
    ('period_start','2026-07-01'), ('carried_losses','1'), ('facts_confirmed',False)])
def test_case_scope_rejected(field,value):
    data = facts(); data[field] = value
    with pytest.raises(ValueError):
        run(data)


@pytest.mark.parametrize('changes', [dict(category='business'),
    dict(source_jurisdiction='sg',foreign_tax_paid='0'),
    dict(foreign_tax_paid='1'),dict(gross_amount='1000000')])
def test_income_scope_or_unreconciled_pay_rejected(changes):
    data = facts(); data['incomes'][0].update(changes)
    with pytest.raises(ValueError):
        run(data)


@pytest.mark.parametrize('months', [[True],['12'],[12.0],[13],[-1],[1]*201])
def test_contract_does_not_coerce_dependent_months(months):
    assertion = basis(); assertion['dependent_months'] = months
    with pytest.raises(ValidationError):
        run(assertion=assertion)


def test_policy_cannot_be_used_for_company():
    data = facts(); data['subject'] = 'company'; data['incomes'][0]['category'] = 'business'
    with pytest.raises(ValueError, match='subject'):
        run(data)


def test_api_persists_vietnam_provenance_and_result_after_restart(tmp_path):
    url = 'sqlite:///' + str(tmp_path/'vietnam.sqlite')
    service = SimpleNamespace(store=ChatStore(url))
    app = FastAPI(); app.include_router(auth.router); app.include_router(chat.router)
    app.dependency_overrides[auth.optional_user] = fixture_user
    app.dependency_overrides[chat.get_service] = lambda: service
    headers = {'x-asiatax-request': '1'}
    with TestClient(app) as client:
        client.get('/api/auth/session')
        case_id = client.post('/api/cases',headers=headers).json()['id']
        path = f'/api/cases/{case_id}/income-tax'
        saved = client.put(path,headers=headers,json=dict(revision=0,
            request_id=str(uuid4()),inputs=facts()))
        assert saved.status_code == 200, saved.text
        response = client.post(path+'/runs',headers=headers,json=dict(revision=1,
            request_id=str(uuid4()),basis=basis()))
        assert response.status_code == 200, response.text
        recorded = response.json()
        assert Decimal(recorded['result']['final_tax']) == 78000000
        assert recorded['result']['sources'][0]['sha256'] == '6b4803e79a068a7ed5727cfe174e337bbb8b1dbb1b1e48f72119b5f5825e9685'
        service.store.engine.dispose()
        service.store = ChatStore(url)
        assert client.get(path+'/runs/'+recorded['id']).json() == recorded
    service.store.engine.dispose()
