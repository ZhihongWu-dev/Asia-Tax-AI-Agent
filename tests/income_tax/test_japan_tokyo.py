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
    return dict(subject='company',jurisdiction='jp',currency='JPY',residency='resident',
        period_start='2026-04-01',period_end='2027-03-31',facts_confirmed=True,
        claimed_deductions='0',carried_losses='0',incomes=[dict(category='business',
        source_jurisdiction='jp',gross_amount='10000000',description='Domestic ordinary receipts')])


def basis():
    paper=dict(registered_capital='10000000',capital_reserve='0',adjusted_statutory_capital='10000000',
        enterprise_income_additions='0',enterprise_income_deductions='0',eligible_enterprise_prior_losses='0',
        enterprise_interim_liability='0',special_enterprise_interim_liability='0',
        inhabitant_interim_liability='0',per_capita_interim_liability='0',
        wards=[dict(ward_code='13101',employees=50,principal=True)],
        all_offices_in_wards_for_full_year_verified=True,ordinary_domestic_entity_verified=True,
        size_based_exclusion_including_2025_2026_verified=True,capital_employees_and_local_base_verified=True,
        no_local_tax_credits_or_treaty_amendments_verified=True,
        local_adjustments_explanation='Verified fiscal bases, local loss vintages, capital history, control and unchanged ward offices.')
    return dict(policy='jp_company_starting_2026',taxable_income_before_rounding='10000000',
        rate_regime='sme_reduced',rate_classification_verified=True,ordinary_no_adjustments_confirmed=True,
        corporation_interim_liability='0',local_corporation_interim_liability='0',
        basis_confirmed=True,basis_explanation='Verified ordinary company classification and complete annual fiscal adjustments.',tokyo_local=paper)


def run(data=None,assertion=None):
    return calculate(IncomeTaxCase(**(data or facts())),TypeAdapter(Assessment).validate_python(assertion or basis()))


def test_full_year_ordinary_ward_assessment_combines_national_and_local_components():
    result=run()
    assert Decimal(result['national_final_tax'])==1835300
    assert Decimal(result['final_tax'])==2695700
    assert result['local_taxes_calculated'] is True
    assert result['tokyo_local']['local_tax_components']==dict(enterprise='492000',special_enterprise='182000',inhabitant='116400',per_capita='70000')
    assert result['tokyo_local']['local_refunds']=='0'
    assert len(result['tokyo_local']['wards'])==1


def test_multiple_wards_count_prefecture_once_and_do_not_offset_refunds():
    b=basis();p=b['tokyo_local']
    p['wards'].append(dict(ward_code='13102',employees=51,principal=False))
    p['enterprise_interim_liability']='600000'
    result=run(assertion=b)['tokyo_local']
    assert result['local_tax_components']['per_capita']=='190000'
    assert result['local_balances']['enterprise']=='-108000'
    assert result['local_refunds']=='108000'
    assert result['local_amounts_payable']=='488400'


def test_local_loss_basis_is_separate_from_national_loss_basis():
    data=facts();data['claimed_deductions']='12000000'
    b=basis();b['taxable_income_before_rounding']='0';p=b['tokyo_local']
    p.update(enterprise_income_additions='3000000',eligible_enterprise_prior_losses='200000')
    r=run(data,b)
    assert r['national_final_tax']=='0'
    assert r['tokyo_local']['local_income_reconciliation']['enterprise_taxable_income']=='800000'
    assert r['tokyo_local']['local_final_tax']=='108300'


def test_capital_reserve_floor_changes_per_capita_band():
    b=basis();b['tokyo_local']['capital_reserve']='10000000'
    r=run(assertion=b)['tokyo_local']
    assert r['local_income_reconciliation']['capital_for_per_capita_band']=='20000000'
    assert r['local_tax_components']['per_capita']=='180000'


@pytest.mark.parametrize('field',[
    'all_offices_in_wards_for_full_year_verified','ordinary_domestic_entity_verified',
    'size_based_exclusion_including_2025_2026_verified','capital_employees_and_local_base_verified',
    'no_local_tax_credits_or_treaty_amendments_verified'])
def test_unverified_local_scope_rejected(field):
    b=basis();b['tokyo_local'][field]=False
    with pytest.raises(ValueError):run(assertion=b)


@pytest.mark.parametrize('change', ['duplicate','no_principal','two_principals','large_capital','fractional_interim'])
def test_invalid_workpaper_rejected(change):
    b=basis();p=b['tokyo_local']
    if change=='duplicate':p['wards'].append(dict(p['wards'][0],principal=False))
    elif change=='no_principal':p['wards'][0]['principal']=False
    elif change=='two_principals':p['wards'].append(dict(p['wards'][0],ward_code='13102'))
    elif change=='large_capital':p['registered_capital']='100000001'
    else:p['enterprise_interim_liability']='1'
    with pytest.raises(ValueError):run(assertion=b)


def test_invalid_ward_cannot_be_labelled_tokyo():
    b=basis();b['tokyo_local']['wards'][0]['ward_code']='13201'
    with pytest.raises(ValidationError):run(assertion=b)


def test_national_only_request_remains_national_only():
    b=basis();del b['tokyo_local']
    r=run(assertion=b)
    assert r['local_taxes_calculated'] is False
    assert Decimal(r['final_tax'])==1835300


def test_api_restart_export_and_rejected_scope_preserve_original(tmp_path):
    url='sqlite:///'+str(tmp_path/'tokyo.sqlite')
    service=SimpleNamespace(store=ChatStore(url))
    app=FastAPI();app.include_router(auth.router);app.include_router(chat.router)
    app.dependency_overrides[auth.optional_user]=fixture_user
    app.dependency_overrides[chat.get_service]=lambda:service
    headers={'x-asiatax-request':'1'}
    with TestClient(app) as client:
        client.get('/api/auth/session')
        case_id=client.post('/api/cases',headers=headers).json()['id']
        path=f'/api/cases/{case_id}/income-tax'
        saved=client.put(path,headers=headers,json=dict(revision=0,request_id=str(uuid4()),inputs=facts()))
        assert saved.status_code==200,saved.text
        response=client.post(path+'/runs',headers=headers,json=dict(revision=1,request_id=str(uuid4()),basis=basis()))
        assert response.status_code==200,response.text
        record=response.json()
        assert record['result']['final_tax']=='2695700'
        service.store.engine.dispose();service.store=ChatStore(url)
        assert client.get(path+'/runs/'+record['id']).json()==record
        report=client.get(path+'/runs/'+record['id']+'/report?locale=en')
        assert report.status_code==200
        assert 'local_income_reconciliation' in report.text
        assert 'Tokyo 23-ward local tax details' in report.text
        assert 'totals above are national taxes' in report.text
        assert '| Local annual tax total | 860400 |' in report.text
        zh=client.get(path+'/runs/'+record['id']+'/report?locale=zh')
        assert zh.status_code==200
        assert '东京23区地方税明细' in zh.text
        assert '| 地方税年度合计 | 860400 |' in zh.text
        for source in record['result']['sources']:assert source['sha256'] in report.text
        before=client.get(path).json();invalid=basis()
        invalid['tokyo_local']['size_based_exclusion_including_2025_2026_verified']=False
        rejected=client.post(path+'/runs',headers=headers,json=dict(revision=before['revision'],request_id=str(uuid4()),basis=invalid))
        assert rejected.status_code==422,rejected.text
        assert client.get(path).json()==before
    service.store.engine.dispose()


@pytest.mark.parametrize('income,rate',[('25000999','0.035'),('25001000','0.0375')])
def test_enterprise_surcharge_threshold_uses_thousand_yen_base(income,rate):
    data=facts();data['incomes'][0]['gross_amount']=income
    b=basis();b['taxable_income_before_rounding']=income
    r=run(data,b)['tokyo_local']
    assert r['enterprise']['bands'][0]['rate']==rate
