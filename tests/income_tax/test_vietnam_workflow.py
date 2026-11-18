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


def company_facts():
    data = facts()
    data.update(subject='company', claimed_deductions='9000000000')
    data['incomes'] = [dict(category='business',source_jurisdiction='vn',
        gross_amount='10000000000', description='All statutory domestic revenue before revenue deductions')]
    return data


def company_basis():
    return dict(policy='vn_company_2026',basis_confirmed=True,
        basis_explanation='Ordinary domestic tax basis reconciled after deductions, losses and adjustments.',
        taxable_income='1000000000', vietnam_established=True, new_in_current_period=False,
        previous_period_revenue='4000000000',previous_active_months=12,
        exemption_related_enterprise_disqualified=False,reduced_rate_related_enterprise_disqualified=False,
        formed_by_split_after_resolution=False,all_split_entities_revenue=None,
        other_incentive_reduction='20000000',prepaid_tax='150000000',
        ordinary_domestic_income_confirmed=True,statutory_revenue_scope_confirmed=True,
        other_incentives_verified=True)


def test_company_current_revenue_comes_from_all_saved_receipts():
    data = company_facts()
    result = run(data,company_basis())
    assert Decimal(result['final_tax']) == 105000000
    assert Decimal(result['annual_reduction']) == 45000000
    assert Decimal(result['balance_due']) == -45000000
    data['incomes'].append(dict(category='interest',source_jurisdiction='vn',
        gross_amount='1',description='Additional ordinary financial revenue'))
    # Matching allowed cost keeps the profit base fixed while gross revenue crosses the relief threshold.
    data['claimed_deductions']='9000000001'
    result = run(data,company_basis())
    assert Decimal(result['final_tax']) == 150000000
    assert Decimal(result['rate']) == Decimal('.17')


@pytest.mark.parametrize('change', [dict(category='dividend'),dict(category='capital_gain'),
    dict(source_jurisdiction='sg',foreign_tax_paid='0'),dict(foreign_tax_paid='1')])
def test_company_unsupported_income_rejected(change):
    data = company_facts(); data['incomes'][0].update(change)
    with pytest.raises(ValueError):
        run(data,company_basis())


@pytest.mark.parametrize('change', [dict(previous_active_months=True),
    dict(previous_active_months='12'),dict(previous_active_months=0),
    dict(previous_active_months=13),dict(taxable_income=1.5),
    dict(current_period_statutory_revenue='1')])
def test_company_contract_rejects_coercion_and_duplicate_current_revenue(change):
    assertion = company_basis(); assertion.update(change)
    with pytest.raises(ValidationError):
        run(company_facts(),assertion)


def test_company_new_entity_requires_absent_prior_period_facts():
    assertion = company_basis(); assertion['new_in_current_period'] = True
    with pytest.raises(ValueError):
        run(company_facts(),assertion)
    assertion.update(previous_period_revenue=None,previous_active_months=None)
    assert Decimal(run(company_facts(),assertion)['final_tax']) == 105000000


@pytest.mark.parametrize('make_facts,make_basis,tax,source_hash', [
    (facts,basis,78000000,'6b4803e79a068a7ed5727cfe174e337bbb8b1dbb1b1e48f72119b5f5825e9685'),
    (company_facts,company_basis,105000000,'ae706468190afe8d111dd0fccf240e7a980eb002c5d0b5cb1cfe127d92f9c1cd')])
def test_api_persists_vietnam_provenance_and_result_after_restart(tmp_path,make_facts,make_basis,tax,source_hash):
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
            request_id=str(uuid4()),inputs=make_facts()))
        assert saved.status_code == 200, saved.text
        response = client.post(path+'/runs',headers=headers,json=dict(revision=1,
            request_id=str(uuid4()),basis=make_basis()))
        assert response.status_code == 200, response.text
        recorded = response.json()
        assert Decimal(recorded['result']['final_tax']) == tax
        assert recorded['result']['sources'][0]['sha256'] == source_hash
        service.store.engine.dispose()
        service.store = ChatStore(url)
        assert client.get(path+'/runs/'+recorded['id']).json() == recorded
    service.store.engine.dispose()
