from decimal import Decimal
import pytest
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.singapore_foreign_assessment import credit_from_saved_case


def fixture():
    case=IncomeTaxCase(subject='company',jurisdiction='sg',currency='SGD',residency='resident',
        period_start='2025-01-01',period_end='2025-12-31',facts_confirmed=True,
        claimed_deductions='16100',carried_losses='0',incomes=[
        dict(category=kind,source_jurisdiction=country,gross_amount=gross,foreign_tax_paid=paid,
            description='Synthetic source with independently established entitlement')
        for kind,country,gross,paid in [('business','sg','300000','0'),('business','my','50000','10000'),('interest','jp','20000','1000')]])
    def source(index,tax): return dict(income_index=index,eligible_direct_tax=tax,pool_elected=False,headline_rate_percent='20',credit_entitlement_verified=True)
    paper=dict(groups=[dict(source_id='trade',kind='trade',deductions='15000',sources=[source(0,'0'),source(1,'10000')]),
        dict(source_id='interest',kind='passive',deductions='100',sources=[source(2,'1000')])],approved_donations='1000',
        resident_same_income_and_allocation_verified=True,direct_tax_ordinary_positive_sources_verified=True)
    return case,paper


def run(case,paper):
    return credit_from_saved_case(case,paper,exemption_scheme='partial',startup_eligibility_confirmed=False)


def test_caps_derived_from_saved_income_and_company_tax():
    result=run(*fixture())
    assert result['gross_tax_before_credit']==42738
    assert result['chargeable_income_before_exemption']==353900
    assert result['allowed_foreign_tax_credit'].quantize(Decimal('.01'))==Decimal('6763.08')


@pytest.mark.parametrize('change',['duplicate','missing','overclaim','deductions','residence','period','loss','category'])
def test_unreconciled_facts_rejected(change):
    case,p=fixture()
    if change=='duplicate': p['groups'][1]['sources'][0]['income_index']=1
    if change=='missing': p['groups'].pop()
    if change=='overclaim': p['groups'][0]['sources'][1]['eligible_direct_tax']='10001'
    if change=='deductions': case.claimed_deductions=Decimal(1)
    if change=='residence': case.residency='nonresident'
    if change=='period': case.period_start=case.period_start.replace(year=2024)
    if change=='loss': case.carried_losses=Decimal(1)
    if change=='category': case.incomes[1].category='employment'
    with pytest.raises(ValueError): run(case,p)

@pytest.mark.parametrize('grant,expected',[(False,'17987.46'),(True,'19987.46')])
def test_assessment_router_settles_credit_before_rebate(grant,expected):
    from pydantic import TypeAdapter
    from packages.contracts.income_assessment import Assessment
    from packages.income_tax.assessment import calculate
    case,p=fixture()
    basis=TypeAdapter(Assessment).validate_python(dict(policy='sg_company_foreign_direct_ya2026',
        workpaper=p,exemption_scheme='partial',startup_eligibility_confirmed=False,
        cash_grant_eligible=grant,prepaid_tax='20000',basis_confirmed=True,
        basis_explanation='Verified direct foreign tax eligibility and expense allocation'))
    result=calculate(case,basis)
    assert Decimal(result['final_tax']).quantize(Decimal('.01'))==Decimal(expected)
    from fractions import Fraction
    assert Fraction(result['balance_due'])==Fraction(result['final_tax'])-20000
    assert Decimal(result['cash_grant_separate'])==(2000 if grant else 0)
    assert Decimal(result['allowed_tax_setoff']).quantize(Decimal('.01'))==Decimal('6763.08')
    import hashlib
    from pathlib import Path
    for source in result['sources']:
        path=Path(source['file'])
        if source['file'].startswith('raw/'): path=Path('database')/path
        assert hashlib.sha256(path.read_bytes()).hexdigest()==source['sha256']

@pytest.mark.parametrize('pooled,expected',[(False,'17987.46'),(True,'17289.25')])
def test_saved_api_reopen_replay_and_rejection(tmp_path,pooled,expected):
    from copy import deepcopy
    from types import SimpleNamespace
    from uuid import uuid4
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.api import auth,chat
    from packages.chat.store import ChatStore
    from tests.chat.auth_support import fixture_user
    case,p=fixture()
    if pooled:
        for group in p['groups']:
            for source in group['sources']:
                source['pool_elected']=source['income_index']!=0
    basis=dict(policy='sg_company_foreign_direct_ya2026',workpaper=p,
        exemption_scheme='partial',startup_eligibility_confirmed=False,
        cash_grant_eligible=False,prepaid_tax='20000',basis_confirmed=True,
        basis_explanation='Verified direct credit, ordinary income and source allocations')
    url='sqlite:///'+str(tmp_path/'sg.sqlite')
    service=SimpleNamespace(store=ChatStore(url))
    app=FastAPI();app.include_router(auth.router);app.include_router(chat.router)
    app.dependency_overrides[auth.optional_user]=fixture_user
    app.dependency_overrides[chat.get_service]=lambda:service
    headers={'x-asiatax-request':'1'}
    try:
        with TestClient(app) as client:
            client.get('/api/auth/session')
            created=client.post('/api/cases',headers=headers)
            assert created.status_code==201,created.text
            path=f"/api/cases/{created.json()['id']}/income-tax"
            saved=client.put(path,headers=headers,json=dict(revision=0,request_id=str(uuid4()),inputs=case.model_dump(mode='json')))
            assert saved.status_code==200,saved.text
            request=dict(revision=saved.json()['revision'],request_id=str(uuid4()),basis=basis)
            response=client.post(path+'/runs',headers=headers,json=request)
            assert response.status_code==200,response.text
            run=response.json()
            assert Decimal(run['result']['final_tax']).quantize(Decimal('.01'))==Decimal(expected)
            reports={}
            for locale in ('en','zh'):
                report=client.get(path+'/runs/'+run['id']+'/report?locale='+locale)
                assert report.status_code==200,report.text
                reports[locale]=report.json()['markdown']
                assert ('Singapore direct foreign credit details' if locale=='en' else '???????????') in reports[locale]
                assert ('Separate cash grant' if locale=='en' else '??????') in reports[locale]
                assert '| trade | MY |' in reports[locale]
                assert '| interest | JP |' in reports[locale]
                assert run['snapshot_hash'] in reports[locale]
                for source in run['result']['sources']:
                    assert source['sha256'] in reports[locale]
            service.store.engine.dispose();service.store=ChatStore(url)
            assert client.get(path+'/runs/'+run['id']).json()==run
            assert client.post(path+'/runs',headers=headers,json=request).json()==run
            current=client.get(path).json()
            bad=deepcopy(request)
            bad.update(revision=current['revision'],request_id=str(uuid4()))
            bad['basis']['workpaper']['groups'][0]['sources'][1]['eligible_direct_tax']='10001'
            rejected=client.post(path+'/runs',headers=headers,json=bad)
            assert rejected.status_code==422,rejected.text
            assert client.get(path).json()==current
            for locale,original in reports.items():
                assert client.get(path+'/runs/'+run['id']+'/report?locale='+locale).json()['markdown']==original
    finally:
        service.store.engine.dispose()


def test_six_place_saved_income_preserves_derived_tax_precision():
    from fractions import Fraction
    case,p=fixture()
    case.incomes[0].gross_amount += Decimal('0.000001')
    result=run(case,p)
    assert result['gross_tax_before_credit']==Decimal('42738.00000017')
    trade=Fraction(50000)/Fraction('350000.000001')*Fraction('335000.000001')/Fraction('354900.000001')*Fraction('42738.00000017')
    expected=trade+1000
    assert abs(Fraction(result['allowed_foreign_tax_credit'])-expected)<Fraction(1,10**34)


def test_public_saved_income_still_rejects_seven_decimal_places():
    case,_=fixture()
    data=case.model_dump(mode='json')
    data['incomes'][0]['gross_amount']='300000.0000001'
    with pytest.raises(ValueError,match='precision'):
        IncomeTaxCase.model_validate(data)
