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
from packages.contracts.income_assessment import Assessment
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.assessment import calculate
from tests.chat.auth_support import fixture_user


def inputs():
    case = dict(subject='individual', jurisdiction='vn', currency='VND',
        residency='resident', period_start='2026-01-01', period_end='2026-12-31',
        facts_confirmed=True, claimed_deductions='1000000000', carried_losses='0',
        incomes=[dict(category='business', source_jurisdiction='vn',
            gross_amount='800000000', description='Verified digital content receipts'),
            dict(category='business', source_jurisdiction='vn', gross_amount='1200000000',
                description='Verified ordinary goods receipts')])
    basis = dict(policy='vn_business_2026', method='revenue',
        activities=[dict(income_index=1, category='goods', allocated_revenue_deduction='200000000'),
            dict(income_index=0, category='digital_content', allocated_revenue_deduction='800000000')],
        deductible_expenses=None, prepaid_tax='1000000', ordinary_domestic_business_verified=True,
        revenue_and_expense_evidence_verified=True, method_election_and_continuity_verified=True,
        revenue_method_started_within_limit=True, basis_confirmed=True,
        basis_explanation='Annual receipts, business classification, allocation and method election reconciled.')
    return case, basis


def run(case, basis):
    return calculate(IncomeTaxCase(**case), TypeAdapter(Assessment).validate_python(basis))


def test_saved_amounts_and_indices_drive_business_calculation():
    result = run(*inputs())
    assert Decimal(result['final_tax']) == 3500000
    assert Decimal(result['balance_due']) == 2500000
    assert [a['income_index'] for a in result['activities']] == [0, 1]
    assert result['activities'][0]['category'] == 'digital_content'
    assert len(result['sources']) == 5


@pytest.mark.parametrize('mutation', ['duplicate', 'missing', 'deductions', 'loss',
    'foreign', 'credit', 'subject', 'residency', 'period', 'employment'])
def test_case_reconciliation_rejects_inconsistent_basis(mutation):
    case, basis = inputs()
    if mutation == 'duplicate': basis['activities'][0]['income_index'] = 0
    elif mutation == 'missing': basis['activities'].pop()
    elif mutation == 'deductions': case['claimed_deductions'] = '0'
    elif mutation == 'loss': case['carried_losses'] = '1'
    elif mutation == 'foreign': case['incomes'][0]['source_jurisdiction'] = 'sg'
    elif mutation == 'credit': case['incomes'][0]['foreign_tax_paid'] = '1'
    elif mutation == 'subject': case['subject'] = 'company'
    elif mutation == 'residency': case['residency'] = 'nonresident'
    elif mutation == 'period': case['period_start'] = '2026-07-01'
    elif mutation == 'employment': case['incomes'][0]['category'] = 'employment'
    with pytest.raises(ValueError): run(case, basis)


def test_profit_basis_uses_saved_receipts_and_deductions():
    case, basis = inputs()
    basis.update(method='profit', deductible_expenses='1000000000',
        revenue_method_started_within_limit=False)
    for activity in basis['activities']: activity['allocated_revenue_deduction'] = '0'
    assert Decimal(run(case, basis)['final_tax']) == 105000000


def test_business_run_persists_through_store_restart_and_fact_changes(tmp_path):
    url = 'sqlite:///' + str(tmp_path/'business.sqlite')
    service = SimpleNamespace(store=ChatStore(url))
    app = FastAPI()
    app.include_router(auth.router)
    app.include_router(chat.router)
    app.dependency_overrides[auth.optional_user] = fixture_user
    app.dependency_overrides[chat.get_service] = lambda: service
    headers = {'x-asiatax-request': '1'}
    case, basis = inputs()
    with TestClient(app) as client:
        client.get('/api/auth/session')
        case_id = client.post('/api/cases', headers=headers).json()['id']
        path = f'/api/cases/{case_id}/income-tax'
        saved = client.put(path, headers=headers, json=dict(revision=0,
            request_id=str(uuid4()), inputs=case))
        assert saved.status_code == 200, saved.text
        request = dict(revision=1, request_id=str(uuid4()), basis=basis)
        response = client.post(path+'/runs', headers=headers, json=request)
        assert response.status_code == 200, response.text
        run_doc = response.json()
        assert Decimal(run_doc['result']['balance_due']) == 2500000
        service.store.engine.dispose()
        service.store = ChatStore(url)
        assert client.get(path+'/runs/'+run_doc['id']).json() == run_doc
        assert client.post(path+'/runs', headers=headers, json=request).json() == run_doc
        amended = deepcopy(case)
        amended['incomes'][0]['gross_amount'] = '900000000'
        assert client.put(path, headers=headers, json=dict(revision=2,
            request_id=str(uuid4()), inputs=amended)).status_code == 200
        assert client.get(path).json()['income_tax_result'] is None
        assert client.get(path+'/runs/'+run_doc['id']).json() == run_doc
    service.store.engine.dispose()
