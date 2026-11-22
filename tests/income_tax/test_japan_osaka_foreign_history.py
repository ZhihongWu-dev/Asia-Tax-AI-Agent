from copy import deepcopy
from decimal import localcontext
from types import SimpleNamespace
from uuid import uuid4
import pytest
from pydantic import TypeAdapter
from fastapi import FastAPI
from fastapi.testclient import TestClient
from apps.api import auth,chat
from packages.chat.store import ChatStore
from packages.contracts.income_tax import IncomeTaxCase,CURRENCIES
from packages.contracts.income_assessment import Assessment
from packages.income_tax.assessment import calculate
from tests.chat.auth_support import fixture_user
from tests.income_tax.test_japan_foreign_reconciliation import fixture
from tests.income_tax.test_japan_osaka_foreign import paper
from tests.income_tax.test_japan_local_foreign_history import limits,lot,local_history,local_lot


def facts(country='sg'):
    case,source=fixture(country);p=paper()
    del p['no_other_local_credits_additions_history_losses_or_treaty_amendments_verified']
    p.update(no_other_local_credits_additions_losses_or_treaty_amendments_verified=True,
        corporation_interim_liability=14000000,prefectural_inhabitant_interim_liability=100,
        city_inhabitant_interim_liability=200)
    basis=dict(policy='jp_osaka_company_foreign_history_starting_2026',
        source_workpaper=source,local_workpaper=p,rate_regime='ordinary',rate_classification_verified=True,
        no_other_tax_credits_or_additions_verified=True,
        limit_history=limits(lot(2025,national=100000,prefectural=100000,municipal=200000)),
        levy_history=local_history(local_lot(2025,500000,2000000)),
        basis_confirmed=True,basis_explanation='Verified saved sources, original returns, original balances, prior usage and unchanged Osaka filing scope.')
    return case,basis


def run(case,basis):
    saved=IncomeTaxCase.model_validate_json(IncomeTaxCase(**case).model_dump_json())
    adapter=TypeAdapter(Assessment)
    typed=adapter.validate_python(basis)
    return calculate(saved,adapter.validate_json(adapter.dump_json(typed)))


@pytest.mark.parametrize('country',[c for c in CURRENCIES if c!='jp'])
def test_saved_sources_derive_nine_taxes_and_two_history_ledgers(country):
    case,basis=facts(country);r=run(case,basis)
    assert r['total_annual_liability']=='25531700'
    assert r['total_payable']=='11711700'
    assert r['total_refundable']=='180300'
    assert r['total_foreign_credit_refund']=='0'
    assert r['total_interim_refund']=='180300'
    assert len(r['settlements'])==9
    assert r['settlements']['corporation']['annual_liability']=='13820000'
    assert r['settlements']['enterprise']['annual_liability']=='7258200'
    assert r['settlements']['city_capitation']['annual_liability']=='50000'
    assert r['next_period_levy_shortfall']==dict(prefectural='228800',municipal='854400')
    assert r['history_matching']['current_excess_remaining']=='423360'


def test_saved_national_credit_refund_and_local_carry_are_not_netted():
    case,b=facts('kr')
    case['incomes'][0]['gross_amount']='20000000'
    case['incomes'][1].update(gross_amount='100000000',foreign_tax_paid='31500000')
    b['source_workpaper']['groups'][1]['eligible_foreign_corporate_tax']='31500000'
    b['local_workpaper']['corporation_interim_liability']=1000000
    b['limit_history']=limits(lot(2025,national=3000000,prefectural=200000,municipal=1000000))
    r=run(case,b)
    assert r['total_annual_liability']=='10152900'
    assert r['total_payable']=='10152900'
    assert r['total_refundable']=='1680300'
    assert r['total_foreign_credit_refund']=='680000'
    assert r['total_interim_refund']=='1000300'
    assert r['next_period_levy_shortfall']==dict(prefectural='444800',municipal='2350400')
    assert r['settlements']['corporation']['annual_liability']=='0'


@pytest.mark.parametrize('change',['legacy_flag','unverified','wrong_filing','source_paid','period','loss'])
def test_invalid_saved_historical_basis_rejected(change):
    case,b=facts()
    if change=='legacy_flag':b['no_other_tax_credits_additions_or_history_verified']=True
    if change=='unverified':b['no_other_tax_credits_or_additions_verified']=False
    if change=='wrong_filing':b['levy_history']['municipal_filing_id']='Kyoto'
    if change=='source_paid':b['source_workpaper']['groups'][1]['eligible_foreign_corporate_tax']='12000001'
    if change=='period':case['period_end']='2026-12-31'
    if change=='loss':case['carried_losses']='1'
    with pytest.raises(ValueError):run(case,b)


def test_saved_input_immutable_and_low_precision_exact():
    case,b=facts();before=deepcopy((case,b));expected=run(case,b)
    with localcontext() as context:
        context.prec=4
        assert run(case,b)==expected
    assert (case,b)==before


@pytest.mark.parametrize('country',['sg','cn','id'])
def test_history_api_reopen_replay_reports_and_rejection_preserves_original(tmp_path,country):
    case,basis=facts(country)
    url='sqlite:///'+str(tmp_path/'history.db');service=SimpleNamespace(store=ChatStore(url))
    app=FastAPI();app.include_router(auth.router);app.include_router(chat.router)
    app.dependency_overrides[auth.optional_user]=fixture_user
    app.dependency_overrides[chat.get_service]=lambda:service
    headers={'x-asiatax-request':'1'}
    try:
        with TestClient(app) as client:
            client.get('/api/auth/session')
            created=client.post('/api/cases',headers=headers);assert created.status_code==201
            case_path=f"/api/cases/{created.json()['id']}";path=case_path+'/income-tax'
            saved=client.put(path,headers=headers,json=dict(revision=0,request_id=str(uuid4()),inputs=case))
            assert saved.status_code==200,saved.text
            request=dict(revision=saved.json()['revision'],request_id=str(uuid4()),basis=basis)
            response=client.post(path+'/runs',headers=headers,json=request)
            assert response.status_code==200,response.text
            stored=response.json();r=stored['result']
            assert r['total_payable']=='11711700' and r['total_refundable']=='180300'
            reports={}
            for locale,heading in [('zh','日本大阪历史抵免年度结算'),('en','Japan Osaka annual settlement with historical credits')]:
                report=client.get(path+'/runs/'+stored['id']+'/report?locale='+locale)
                assert report.status_code==200,report.text
                text=report.json()['markdown'];reports[locale]=text
                assert heading in text
                for value in ('228800','854400','423360','180300','192800','756800'):assert value in text
                assert ('地方税未抵免台账' if locale=='zh' else 'Local levy-shortfall ledger') in text
                assert ('预缴退款' if locale=='zh' else 'Interim refund') in text
                for source in r['sources']:assert source['sha256'] in text
            service.store.engine.dispose();service.store=ChatStore(url)
            assert client.get(path+'/runs/'+stored['id']).json()==stored
            assert client.post(path+'/runs',headers=headers,json=request).json()==stored
            invalid=deepcopy(request)
            invalid.update(revision=client.get(case_path).json()['revision'],request_id=str(uuid4()))
            invalid['basis']['levy_history']['single_unchanged_prefecture_and_municipality_verified']=False
            rejected=client.post(path+'/runs',headers=headers,json=invalid)
            assert rejected.status_code==422 and rejected.json()=={'detail':'invalid_facts'}
            for locale,text in reports.items():
                assert client.get(path+'/runs/'+stored['id']+'/report?locale='+locale).json()['markdown']==text
    finally:service.store.engine.dispose()
