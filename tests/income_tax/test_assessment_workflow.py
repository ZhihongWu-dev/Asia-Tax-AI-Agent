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
from packages.contracts.income_tax import IncomeTaxCase, CURRENCIES
from packages.income_tax.assessment import calculate
from tests.chat.auth_support import fixture_user

ADAPTER = TypeAdapter(Assessment)
HEADERS = {'x-asiatax-request': '1'}
COMMON = dict(basis_confirmed=True, basis_explanation='Tax basis reconciled to the supporting income and deduction schedule.')


def facts(jur='cn', subject='company'):
    start, end = {'cn': ('2026-01-01','2026-12-31'), 'ae': ('2026-01-01','2026-12-31'),
                  'sg': ('2025-01-01','2025-12-31'), 'hk': ('2025-04-01','2026-03-31')}[jur]
    return dict(subject=subject, jurisdiction=jur, period_start=start, period_end=end,
                currency=CURRENCIES[jur], residency='resident', facts_confirmed=True,
                claimed_deductions='0', carried_losses='0', incomes=[dict(
                    category='business' if subject=='company' else 'employment',
                    source_jurisdiction=jur, gross_amount='1000000', description='Annual income')])


COMPANY = dict(policy='cn_company_2026', taxable_income='1000000', normal_rate_confirmed=True,
               allowed_tax_credits='0', prepaid_tax='1000', **COMMON)


@pytest.mark.parametrize('jur,subject,basis,key,expected', [
    ('cn','company',COMPANY,'balance_due','249000'),
    ('cn','individual',dict(policy='cn_comprehensive_2026', allowed_special_deductions='0',
        allowed_additional_deductions='0', allowed_other_deductions='0', allowed_donations='0',
        allowed_tax_reductions='0', prepaid_tax='0', domestic_normal_treatment_confirmed=True),
        'annual_liability','243080'),
    ('sg','company',dict(policy='sg_company_ya2026', normal_chargeable_income='100000',
        exemption_scheme='partial', startup_eligibility_confirmed=False, cash_grant_eligible=False,
        allowed_tax_setoff='0', ordinary_regime_confirmed=True),'net_tax','4037.5'),
    ('sg','individual',dict(policy='sg_resident_ya2026',chargeable_income='80000'),'gross_tax','3350'),
    ('hk','company',dict(policy='hk_profits_2025_26',assessable_profits='1000000',
        business_form='corporation',two_tier_eligible=True,ordinary_regime_confirmed=True,
        prepaid_final_tax='0'),'final_tax','79500'),
    ('hk','individual',dict(policy='hk_salaries_2025_26',net_income='380000',allowed_allowances='132000',
        prepaid_final_tax='10000',ordinary_separate_assessment_confirmed=True),'balance_due','11160'),
    ('ae','company',dict(policy='ae_ordinary_2026',taxable_income='1000000',ordinary_regime_confirmed=True,
        no_relief_elected_confirmed=True,allowed_foreign_tax_credit='0',prepaid_tax='0'),'final_tax','56250'),
])
def test_supported_policies_through_saved_case_contract(jur, subject, basis, key, expected):
    data=facts(jur,subject)
    if basis['policy']=='sg_company_ya2026':data['claimed_deductions']='900000'
    result = calculate(IncomeTaxCase(**data), ADAPTER.validate_python({**COMMON, **basis}))
    assert isinstance(result[key], str)  # never serialize money as a binary float
    assert Decimal(result[key]) == Decimal(expected)
    assert result['policy_version'] and result['stage']


@pytest.mark.parametrize('change', [dict(facts_confirmed=False),dict(claimed_deductions=None),
    dict(period_start='2025-01-01'),dict(subject='individual')])
def test_case_mismatch_cannot_compute(change):
    data = facts(); data.update(change)
    with pytest.raises(ValueError):
        calculate(IncomeTaxCase(**data),ADAPTER.validate_python(COMPANY))


def test_unknown_policy_extra_fields_and_float_fail():
    for changes in [dict(policy='in_company_2026'),dict(unverified_credit='1'),
                    dict(taxable_income=1.25),dict(basis_confirmed=1)]:
        with pytest.raises(ValidationError):
            ADAPTER.validate_python({**COMPANY, **changes})


def test_policy_cannot_cross_jurisdiction_or_residency_boundary():
    with pytest.raises(ValueError, match='jurisdiction'):
        calculate(IncomeTaxCase(**facts('ae')),ADAPTER.validate_python(COMPANY))
    data = facts('sg','individual'); data['residency']='nonresident'
    with pytest.raises(ValueError, match='resident'):
        calculate(IncomeTaxCase(**data),ADAPTER.validate_python(dict(
            policy='sg_resident_ya2026',chargeable_income='80000',**COMMON)))


def test_natural_person_turnover_reconciles_to_saved_income():
    data = facts('ae','individual')
    data['incomes'][0].update(category='business',gross_amount='3600000')
    data['incomes'].append(dict(category='employment',source_jurisdiction='ae',
                               gross_amount='200000',description='Excluded wage'))
    data['claimed_deductions']='1800000'
    basis = dict(policy='ae_ordinary_2026',taxable_income='1800000',ordinary_regime_confirmed=True,
                 no_relief_elected_confirmed=True,allowed_foreign_tax_credit='0',prepaid_tax='0',
                 natural_person_business_turnover='3600000',
                 natural_person_activity_classification_confirmed=True,**COMMON)
    assert Decimal(calculate(IncomeTaxCase(**data),ADAPTER.validate_python(basis))['final_tax'])==128250
    for change in [dict(natural_person_business_turnover='3800000'),
                   dict(natural_person_activity_classification_confirmed=False)]:
        with pytest.raises(ValueError):
            calculate(IncomeTaxCase(**data),ADAPTER.validate_python({**basis,**change}))


def test_runs_survive_restart_and_edit_with_owner_and_retry_boundaries(tmp_path):
    url = 'sqlite:///' + str(tmp_path/'cases.sqlite')
    service = SimpleNamespace(store=ChatStore(url))
    app = FastAPI(); app.include_router(auth.router); app.include_router(chat.router)
    app.dependency_overrides[auth.optional_user] = fixture_user
    app.dependency_overrides[chat.get_service] = lambda: service
    with TestClient(app) as alice, TestClient(app) as bob, TestClient(app) as anon:
        alice.get('/api/auth/session'); bob.get('/api/auth/session')
        case_id = alice.post('/api/cases',headers=HEADERS).json()['id']
        path = f'/api/cases/{case_id}/income-tax'
        assert alice.put(path,headers=HEADERS,json=dict(revision=0,request_id=str(uuid4()),inputs=facts())).status_code==200
        request = dict(revision=1,request_id=str(uuid4()),basis=COMPANY)
        assert anon.post(path+'/runs',headers=HEADERS,json=request).status_code==401
        assert alice.post(path+'/runs',json=request).status_code==403
        assert bob.post(path+'/runs',headers=HEADERS,json=request).status_code==404
        response = alice.post(path+'/runs',headers=HEADERS,json=request)
        assert response.status_code==200,response.text
        run = response.json()
        assert run['status']=='calculated_basis'
        assert Decimal(run['result']['balance_due'])==249000
        service.store.engine.dispose()
        service.store = ChatStore(url)
        run_path = path+'/runs/'+run['id']
        assert alice.get(run_path).json()==run
        assert bob.get(run_path).status_code==404
        assert anon.get(run_path).status_code==401
        assert alice.post(path+'/runs',headers=HEADERS,json=request).json()==run
        changed = deepcopy(request); changed['basis']['taxable_income']='2000000'
        assert alice.post(path+'/runs',headers=HEADERS,json=changed).status_code==409
        assert alice.get(path).json()['revision']==2
        updated = facts(); updated['incomes'][0]['gross_amount']='2000000'
        assert alice.put(path,headers=HEADERS,json=dict(revision=2,request_id=str(uuid4()),inputs=updated)).status_code==200
        assert alice.get(path).json()['income_tax_result'] is None
        assert alice.get(run_path).json()==run
        assert alice.post(path+'/runs',headers=HEADERS,json=request).json()==run
        assert alice.get(path).json()['income_tax_result'] is None
        stale = {**request,'request_id':str(uuid4())}
        assert alice.post(path+'/runs',headers=HEADERS,json=stale).status_code==409
        invalid = {**stale,'revision':3,'basis':{**COMPANY,'basis_confirmed':False}}
        assert alice.post(path+'/runs',headers=HEADERS,json=invalid).status_code==422
        assert alice.get(path).json()['revision']==3
        assert 'income_tax_runs' not in alice.get(f'/api/cases/{case_id}').json()
    service.store.engine.dispose()


@pytest.mark.parametrize('mixed', [False, True])
def test_hong_kong_profits_does_not_absorb_employment_income(mixed):
    data = facts('hk', 'individual')
    if mixed:
        data['incomes'].append(dict(category='business', source_jurisdiction='hk',
            gross_amount='500000', description='Separate sole proprietor receipts'))
    basis = ADAPTER.validate_python(dict(policy='hk_profits_2025_26',
        assessable_profits='1000000', business_form='sole_proprietor',
        two_tier_eligible=True, ordinary_regime_confirmed=True,
        prepaid_final_tax='0', **COMMON))
    with pytest.raises(ValueError, match='employment'):
        calculate(IncomeTaxCase(**data), basis)
    data['incomes'] = [dict(category='business', source_jurisdiction='hk',
                           gross_amount='1000000', description='Sole proprietor business')]
    assert Decimal(calculate(IncomeTaxCase(**data), basis)['final_tax']) == 72000
