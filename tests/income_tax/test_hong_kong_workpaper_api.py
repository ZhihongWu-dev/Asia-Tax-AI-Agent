"""Isolated fixture-identity API tests, not hosted authentication evidence."""
from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import TypeAdapter
from apps.api import auth,chat
from packages.chat.store import ChatStore
from packages.contracts.income_assessment import Assessment
from packages.contracts.income_tax import IncomeTaxCase,CURRENCIES
from packages.income_tax.assessment import calculate
from tests.chat.auth_support import fixture_user
from tests.income_tax.test_hong_kong_saved_credit_constraints import fixture


def facts(country='sg',pending=False):
    case,p=fixture(country)
    case.update(period_start='2025-01-01',period_end='2025-12-31')
    if pending:
        case['incomes'][1].update(gross_amount='50000',foreign_tax_paid='10000')
        p['groups'][1]['foreign_credit']['direct_foreign_tax_paid']='10000'
        case['incomes'].append(deepcopy(case['incomes'][1]))
        group=deepcopy(p['groups'][1]);group.update(source_id='receipt_b',income_indexes=[2])
        group['foreign_credit']['source_id']='receipt_b';p['groups'].append(group)
    basis=dict(policy='hk_company_fsie_workpaper_2025_26',workpaper=p,two_tier_eligible=False,
        ordinary_annual_basis_and_reduction_ordering_verified=True,
        ongoing_business_unchanged_accounting_year_verified=True,allocations=None,
        basis_confirmed=True,basis_explanation='Synthetic verified ordinary workpaper premises; source allocation and assessment rounding remain separate review steps.')
    return (IncomeTaxCase.model_validate(case).model_dump(mode='json'),
            TypeAdapter(Assessment).validate_python(basis).model_dump(mode='json'))


def run(case,basis):
    adapter=TypeAdapter(Assessment)
    typed=adapter.validate_python(basis)
    return calculate(IncomeTaxCase.model_validate(case),adapter.validate_json(adapter.dump_json(typed)))


@pytest.mark.parametrize('country',[c for c in CURRENCIES if c!='hk'])
def test_typed_workpaper_routes_all_foreign_catalog_sources_without_final_assessment_claim(country):
    case,basis=facts(country)
    result=run(case,basis)
    assert result['exact_constraints']['aggregate']['foreign_tax_credit']==dict(numerator='2040000',denominator='167')
    assert result['basis_period']['start']=='2025-01-01'
    assert result['result_kind']=='workpaper'
    assert result['review_status']=='assessment_review_required'
    assert result['assessment_rounding_applied'] is False
    assert 'final_tax' not in result and 'total_payable' not in result


@pytest.mark.parametrize('value',[
    {'numerator':True,'denominator':'1'}, {'numerator':1,'denominator':'1'},
    {'numerator':'1','denominator':'0'}, {'numerator':'-1','denominator':'1'},
    {'numerator':'1.5','denominator':'1'}, {'numerator':'1'*121,'denominator':'1'},
    {'numerator':'1','denominator':'1','extra':True},
])
def test_exact_allocation_contract_rejects_coercion_zero_denominator_and_oversized_values(value):
    case,basis=facts();basis['allocations']={'receipt_a':value}
    with pytest.raises(ValueError):run(case,basis)


@pytest.mark.parametrize('change',['subject','period','short_period','unverified','period_evidence','wrong_source','wrong_total'])
def test_invalid_basis_or_allocation_rejected_by_router(change):
    case,basis=facts()
    if change=='subject':case['subject']='individual'
    elif change=='period':case.update(period_start='2026-01-01',period_end='2026-12-31')
    elif change=='short_period':case['period_start']='2025-02-01'
    elif change=='unverified':basis['ordinary_annual_basis_and_reduction_ordering_verified']=False
    elif change=='period_evidence':basis['ongoing_business_unchanged_accounting_year_verified']=False
    elif change=='wrong_source':basis['allocations']={'missing':dict(numerator='2040000',denominator='167')}
    else:basis['allocations']={'receipt_a':dict(numerator='1',denominator='1')}
    with pytest.raises(ValueError):run(case,basis)


@pytest.mark.parametrize('country',['sg','cn','id'])
def test_api_reopen_replay_reports_and_pending_allocation_survive_input_edits(tmp_path,country):
    pending=country=='cn';case,basis=facts(country,pending=pending)
    url='sqlite:///'+str(tmp_path/'hk-workpaper.db');service=SimpleNamespace(store=ChatStore(url))
    app=FastAPI();app.include_router(auth.router);app.include_router(chat.router)
    app.dependency_overrides[auth.optional_user]=fixture_user
    app.dependency_overrides[chat.get_service]=lambda:service
    headers={'x-asiatax-request':'1'}
    try:
        with TestClient(app) as client,TestClient(app) as other,TestClient(app) as anonymous:
            client.get('/api/auth/session');other.get('/api/auth/session')
            created=client.post('/api/cases',headers=headers);assert created.status_code==201
            case_path=f"/api/cases/{created.json()['id']}";path=case_path+'/income-tax'
            saved=client.put(path,headers=headers,json=dict(revision=0,request_id=str(uuid4()),inputs=case))
            assert saved.status_code==200,saved.text
            request=dict(revision=saved.json()['revision'],request_id=str(uuid4()),basis=basis)
            response=client.post(path+'/runs',headers=headers,json=request)
            assert response.status_code==200,response.text
            stored=response.json();result=stored['result'];run_path=path+'/runs/'+stored['id']
            assert result['result_kind']=='workpaper' and result['assessment_rounding_applied'] is False
            assert result['constraints']['allocation_required']==pending
            assert result['review_status']==('source_allocation_required' if pending else 'assessment_review_required')
            assert stored['basis']['ongoing_business_unchanged_accounting_year_verified'] is True
            reports={}
            for locale,heading in [('zh','香港境外所得抵免计算底稿'),('en','Hong Kong foreign-credit workpaper')]:
                report=client.get(run_path+'/report?locale='+locale)
                assert report.status_code==200 and report.headers['cache-control']=='private, no-store'
                text=report.json()['markdown'];reports[locale]=text
                assert heading in text and '27/200' in text
                if pending:
                    assert ('待确认：' if locale=='zh' else 'Pending:') in text
                for source in result['sources']:assert source['sha256'] in text
            assert other.get(run_path).status_code==404
            assert anonymous.get(run_path+'/report').status_code==401
            service.store.engine.dispose();service.store=ChatStore(url)
            assert client.get(run_path).json()==stored
            assert client.post(path+'/runs',headers=headers,json=request).json()==stored
            invalid=deepcopy(request)
            invalid.update(revision=client.get(case_path).json()['revision'],request_id=str(uuid4()))
            invalid['basis']['ordinary_annual_basis_and_reduction_ordering_verified']=False
            rejected=client.post(path+'/runs',headers=headers,json=invalid)
            assert rejected.status_code==422 and rejected.json()=={'detail':'invalid_facts'}
            assert client.get(run_path).json()==stored
            assert client.get(path).json()['income_tax_result']==stored
            if pending:
                allocated=deepcopy(request)
                allocated.update(revision=client.get(case_path).json()['revision'],request_id=str(uuid4()))
                allocated['basis']['allocations']={key:dict(numerator='1020000',denominator='167') for key in ('receipt_a','receipt_b')}
                updated=client.post(path+'/runs',headers=headers,json=allocated)
                assert updated.status_code==200,updated.text
                assert updated.json()['basis']['allocations']==allocated['basis']['allocations']
                assert updated.json()['result']['review_status']=='assessment_review_required'
                assert updated.json()['result']['constraints']['allocation_required'] is False
                assert client.get(run_path).json()==stored
            changed=deepcopy(case);changed['incomes'][1]['gross_amount']='120000'
            revision=client.get(case_path).json()['revision']
            edited=client.put(path,headers=headers,json=dict(revision=revision,request_id=str(uuid4()),inputs=changed))
            assert edited.status_code==200 and edited.json()['income_tax_result'] is None
            for locale,text in reports.items():
                assert client.get(run_path+'/report?locale='+locale).json()['markdown']==text
    finally:service.store.engine.dispose()
