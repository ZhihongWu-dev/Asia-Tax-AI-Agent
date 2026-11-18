from decimal import Decimal

import pytest
from pydantic import TypeAdapter

from packages.contracts.income_assessment import Assessment
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.assessment import calculate
from packages.income_tax.vietnam_rental import resident_property_rental_tax


def inputs(revenue='2000000000', deduction='1000000000'):
    return dict(tax_year=2026, resident=True, all_annual_rental_revenue=revenue,
        rental_only_scope_verified=True, annual_recognition_and_all_contracts_verified=True,
        contracts=[dict(contract_id='lease-A', revenue=revenue,
            allocated_revenue_deduction=deduction, prepaid_tax='1000000',
            tenant_files=True, filing_and_allocation_verified=True)])


@pytest.mark.parametrize('revenue,deduction,expected', [
    ('0','0','0'), ('1000000000','1000000000','0'),
    ('1000000001','1000000000','.035'),
    ('2000000000','1000000000','35000000'),
    ('10000000000','1000000000','315000000'),
    ('10000000001','1000000000','450000000.05')])
def test_rental_annual_threshold_and_relief_boundaries(revenue,deduction,expected):
    result = resident_property_rental_tax(**inputs(revenue,deduction))
    assert result['final_tax'] == Decimal(expected)
    assert result['balance_due'] == Decimal(expected)-1000000
    assert len(result['sources']) == 6


def test_multiple_contracts_share_allowance_and_preserve_filing_responsibility():
    args = inputs()
    args['contracts'][0].update(revenue='800000000',allocated_revenue_deduction='800000000')
    args['contracts'].append(dict(contract_id='lease-B',revenue='1200000000',
        allocated_revenue_deduction='200000000',prepaid_tax='2000000',
        tenant_files=False,filing_and_allocation_verified=True))
    result = resident_property_rental_tax(**args)
    assert result['final_tax'] == 35000000
    assert result['balance_due'] == 32000000
    assert result['contracts'][0]['balance_due'] == -1000000
    assert result['contracts'][1]['balance_due'] == 33000000
    assert [r['tenant_files'] for r in result['contracts']] == [True,False]


@pytest.mark.parametrize('mutation', ['scope','recognition','year','resident','empty',
    'duplicate','allowance','over_revenue','reconciliation','filing','bool','float','negative','nan'])
def test_unverified_or_inconsistent_rental_facts_fail(mutation):
    args = inputs()
    row = args['contracts'][0]
    if mutation=='scope': args['rental_only_scope_verified']=False
    elif mutation=='recognition': args['annual_recognition_and_all_contracts_verified']=False
    elif mutation=='year': args['tax_year']=2027
    elif mutation=='resident': args['resident']=False
    elif mutation=='empty': args['contracts']=[]
    elif mutation=='duplicate': args['contracts'].append(dict(row))
    elif mutation=='allowance': row['allocated_revenue_deduction']='1000000001'
    elif mutation=='over_revenue': row['allocated_revenue_deduction']='3000000000'
    elif mutation=='reconciliation': args['all_annual_rental_revenue']='2000000001'
    elif mutation=='filing': row['filing_and_allocation_verified']=False
    elif mutation=='bool': row['tenant_files']=1
    elif mutation=='float': row['prepaid_tax']=1.5
    elif mutation=='negative': row['prepaid_tax']='-1'
    elif mutation=='nan': row['revenue']='NaN'
    with pytest.raises(ValueError): resident_property_rental_tax(**args)


def case_and_basis():
    args = inputs()
    row = args['contracts'][0]
    case = dict(subject='individual',jurisdiction='vn',currency='VND',residency='resident',
        period_start='2026-01-01',period_end='2026-12-31',facts_confirmed=True,
        claimed_deductions='1000000000',carried_losses='0',
        incomes=[dict(category='rental',source_jurisdiction='vn',gross_amount=row['revenue'],
            description='Annual domestic property lease receipts')])
    contract = {k:v for k,v in row.items() if k!='revenue'}
    basis = dict(policy='vn_property_rental_2026',contracts=[dict(contract,income_index=0)],
        rental_only_scope_verified=True,annual_recognition_and_all_contracts_verified=True,
        basis_confirmed=True,basis_explanation='All annual domestic leases and contractual filing allocations verified.')
    return case,basis


def run(case,basis):
    return calculate(IncomeTaxCase(**case),TypeAdapter(Assessment).validate_python(basis))


def test_saved_rental_basis_derives_revenue_and_keeps_contract_identity():
    result = run(*case_and_basis())
    assert Decimal(result['final_tax']) == 35000000
    assert result['contracts'][0]['contract_id']=='lease-A'
    assert result['contracts'][0]['income_index']==0


@pytest.mark.parametrize('mutation',['index','deduction','loss','foreign','credit',
    'company','residency','period','business'])
def test_saved_case_rejects_mismatched_rental_basis(mutation):
    case,basis = case_and_basis()
    if mutation=='index': basis['contracts'][0]['income_index']=1
    elif mutation=='deduction': case['claimed_deductions']='0'
    elif mutation=='loss': case['carried_losses']='1'
    elif mutation=='foreign': case['incomes'][0]['source_jurisdiction']='sg'
    elif mutation=='credit': case['incomes'][0]['foreign_tax_paid']='1'
    elif mutation=='company': case['subject']='company'
    elif mutation=='residency': case['residency']='nonresident'
    elif mutation=='period': case['period_start']='2026-07-01'
    elif mutation=='business': case['incomes'][0]['category']='business'
    with pytest.raises(ValueError): run(case,basis)


def test_rental_api_persists_contracts_and_invalidates_after_edit(tmp_path):
    from types import SimpleNamespace
    from uuid import uuid4
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.api import auth, chat
    from packages.chat.store import ChatStore
    from tests.chat.auth_support import fixture_user

    url = 'sqlite:///' + str(tmp_path/'rental.sqlite')
    service = SimpleNamespace(store=ChatStore(url))
    app = FastAPI()
    app.include_router(auth.router)
    app.include_router(chat.router)
    app.dependency_overrides[auth.optional_user] = fixture_user
    app.dependency_overrides[chat.get_service] = lambda: service
    headers = {'x-asiatax-request':'1'}
    case,basis = case_and_basis()
    with TestClient(app) as client:
        client.get('/api/auth/session')
        case_id = client.post('/api/cases',headers=headers).json()['id']
        path = f'/api/cases/{case_id}/income-tax'
        saved = client.put(path,headers=headers,json=dict(revision=0,request_id=str(uuid4()),inputs=case))
        assert saved.status_code == 200, saved.text
        request = dict(revision=1,request_id=str(uuid4()),basis=basis)
        response = client.post(path+'/runs',headers=headers,json=request)
        assert response.status_code == 200, response.text
        record = response.json()
        assert Decimal(record['result']['balance_due']) == 34000000
        assert record['result']['contracts'][0]['tenant_files'] is True
        service.store.engine.dispose()
        service.store = ChatStore(url)
        assert client.get(path+'/runs/'+record['id']).json() == record
        assert client.post(path+'/runs',headers=headers,json=request).json() == record
        case['incomes'][0]['gross_amount']='3000000000'
        assert client.put(path,headers=headers,json=dict(revision=2,request_id=str(uuid4()),inputs=case)).status_code == 200
        assert client.get(path).json()['income_tax_result'] is None
        assert client.get(path+'/runs/'+record['id']).json() == record
    service.store.engine.dispose()
