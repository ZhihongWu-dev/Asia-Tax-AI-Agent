from copy import deepcopy
from decimal import Decimal
import pytest
from packages.contracts.income_tax import IncomeTaxCase
from packages.contracts.income_assessment import INForeignCompany
from packages.income_tax.assessment import calculate


def fixture(scheme='section200'):
    case = IncomeTaxCase(subject='company', jurisdiction='in', currency='INR', residency='resident',
        period_start='2026-04-01', period_end='2027-03-31', claimed_deductions='1000000',
        carried_losses='0', facts_confirmed=True, incomes=[
            dict(category='business', source_jurisdiction='in', gross_amount='4000000', description='Domestic business'),
            dict(category='royalty', source_jurisdiction='sg', gross_amount='1000000', foreign_tax_paid='200000', description='Foreign ordinary royalty')])
    p = dict(groups=[dict(source_id='domestic',income_indexes=[0],allowable_expenses='1000000'),
        dict(source_id='royalty',income_indexes=[1],allowable_expenses='0',foreign_credit=dict(
            source_id='royalty',country='sg',foreign_tax_paid_inr='200000',disputed_tax_excluded_inr='0',
            treaty_applies=True,treaty_permitted_tax_inr='100000',normal_indian_tax_attributable='251680'))],
        scheme=scheme, domestic_company_regime_and_base_verified=True,source_attribution_and_expenses_verified=True,
        tax_year_fx_disputes_and_treaty_limits_verified=True,required_filings_and_accountant_verification_confirmed=True,
        no_prior_credit_refunds_special_regimes_or_losses_verified=True,period_prepayments_verified=True,
        no_legacy_mat_credit_or_other_reliefs_verified=True)
    if scheme=='normal':
        p.update(turnover_2024_25='10000000',mat_book_profit_before_rounding='10000000')
        p['groups'][1]['foreign_credit'].update(normal_indian_tax_attributable='260000',section206_tax_attributable='145600')
    return case, p


def run(case, p):
    return calculate(case, INForeignCompany(policy='in_company_foreign_ty2026_27',workpaper=p,prepaid_tax='1000000',
        basis_confirmed=True,basis_explanation='Verified statutory source attribution, company regime, filings and current prepayments.'))


def test_section200_foreign_credit_then_period_prepayments():
    result=run(*fixture())
    assert Decimal(result['annual_tax_before_foreign_credit'])==1006720
    assert Decimal(result['allowed_foreign_tax_credit'])==100000
    assert Decimal(result['final_tax'])==906720
    assert Decimal(result['balance_due'])==-93280


def test_normal_mat_comparison_preserves_distinct_credit_paths():
    result=run(*fixture('normal'))
    assert result['mat_applies'] is True
    assert Decimal(result['annual_tax_before_foreign_credit'])==1456000
    assert Decimal(result['final_tax'])==1356000
    assert Decimal(result['balance_due'])==356000


def test_mat_uses_its_credit_even_when_different_from_normal_credit():
    case,p=fixture('normal')
    p['groups'][1]['foreign_credit'].update(treaty_permitted_tax_inr='200000',normal_indian_tax_attributable='50000')
    result=run(case,p)
    assert Decimal(result['allowed_foreign_tax_credit'])==145600
    assert Decimal(result['final_tax'])==1310400


def test_normal_company_without_mat_uses_normal_foreign_credit():
    case,p=fixture('normal')
    p['mat_book_profit_before_rounding']='0'
    p['groups'][1]['foreign_credit']['section206_tax_attributable']='0'
    result=run(case,p)
    assert result['mat_applies'] is False
    assert Decimal(result['final_tax'])==940000
    p['no_legacy_mat_credit_or_other_reliefs_verified']=False
    with pytest.raises(ValueError,match='Verify'):
        run(case,p)


@pytest.mark.parametrize('change',['expense','paid','country','source','duplicate','omit','evidence','negative','mat'])
def test_saved_source_mismatch_rejected(change):
    case,p=fixture()
    row=p['groups'][1]
    if change=='expense': row['allowable_expenses']='1'
    elif change=='paid': row['foreign_credit']['foreign_tax_paid_inr']='200001'
    elif change=='country': row['foreign_credit']['country']='jp'
    elif change=='source': row['foreign_credit']['source_id']='other'
    elif change=='duplicate': p['groups'].append(deepcopy(row))
    elif change=='omit': p['groups'].pop()
    elif change=='evidence': p['required_filings_and_accountant_verification_confirmed']=False
    elif change=='negative': row['income_indexes']=[-1]
    else: p['mat_book_profit_before_rounding']='0'
    with pytest.raises(ValueError): run(case,p)


def test_split_receipt_reconciles_to_one_source_without_extra_credit():
    case,p=fixture()
    expected=run(case,p)
    facts=case.model_dump()
    facts['incomes'][1].update(gross_amount='600000',foreign_tax_paid='120000')
    facts['incomes'].append(dict(category='royalty',source_jurisdiction='sg',gross_amount='400000',foreign_tax_paid='80000',description='Second receipt'))
    p['groups'][1]['income_indexes']=[1,2]
    assert run(IncomeTaxCase(**facts),p)==expected


@pytest.mark.parametrize('scheme', ['section200','normal'])
def test_api_reopen_replay_reports_and_rejected_foreign_payment(tmp_path,scheme):
    from types import SimpleNamespace
    from uuid import uuid4
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.api import auth,chat
    from packages.chat.store import ChatStore
    from tests.chat.auth_support import fixture_user
    case,p=fixture(scheme)
    basis=dict(policy='in_company_foreign_ty2026_27',workpaper=p,prepaid_tax='1000000',
        basis_confirmed=True,basis_explanation='Verified ordinary domestic company, foreign source tax and payment evidence.')
    url='sqlite:///'+str(tmp_path/'india-foreign.sqlite')
    service=SimpleNamespace(store=ChatStore(url))
    app=FastAPI()
    app.include_router(auth.router);app.include_router(chat.router)
    app.dependency_overrides[auth.optional_user]=fixture_user
    app.dependency_overrides[chat.get_service]=lambda:service
    headers={'x-asiatax-request':'1'}
    try:
        with TestClient(app) as client:
            client.get('/api/auth/session')
            created=client.post('/api/cases',headers=headers)
            assert created.status_code==201
            path=f"/api/cases/{created.json()['id']}/income-tax"
            saved=client.put(path,headers=headers,json=dict(revision=0,request_id=str(uuid4()),inputs=case.model_dump(mode='json')))
            assert saved.status_code==200,saved.text
            request=dict(revision=saved.json()['revision'],request_id=str(uuid4()),basis=basis)
            response=client.post(path+'/runs',headers=headers,json=request)
            assert response.status_code==200,response.text
            result=response.json()
            assert Decimal(result['result']['final_tax'])==(906720 if scheme=='section200' else 1356000)
            reports={}
            for locale in ('zh','en'):
                report=client.get(path+'/runs/'+result['id']+'/report?locale='+locale)
                assert report.status_code==200,report.text
                reports[locale]=report.json()['markdown']
                assert ('印度企业境外抵免' if locale=='zh' else 'Indian company foreign tax credits') in reports[locale]
                assert '| royalty | SG |' in reports[locale]
                for source in result['result']['sources']:
                    assert source['sha256'] in reports[locale]
            service.store.engine.dispose();service.store=ChatStore(url)
            assert client.get(path+'/runs/'+result['id']).json()==result
            assert client.post(path+'/runs',headers=headers,json=request).json()==result
            current=client.get(path).json()
            invalid=deepcopy(request)
            invalid.update(revision=current['revision'],request_id=str(uuid4()))
            invalid['basis']['workpaper']['groups'][1]['foreign_credit']['foreign_tax_paid_inr']='200001'
            rejected=client.post(path+'/runs',headers=headers,json=invalid)
            assert rejected.status_code==422,rejected.text
            assert client.get(path).json()==current
            for locale, original in reports.items():
                assert client.get(path+'/runs/'+result['id']+'/report?locale='+locale).json()['markdown']==original
    finally:
        service.store.engine.dispose()
