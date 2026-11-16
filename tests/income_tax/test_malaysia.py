from decimal import Decimal
import hashlib
from pathlib import Path
import pytest
from pydantic import TypeAdapter
from packages.contracts.income_tax import IncomeTaxCase
from packages.contracts.income_assessment import Assessment
from packages.income_tax.assessment import calculate
from packages.income_tax.malaysia import company_tax, individual_tax, SOURCES

COMMON=dict(assessment_year=2026,ordinary_treatment_confirmed=True,allowed_rebates='0',
            allowed_tax_credits='0',prepaid_tax='0')


@pytest.mark.parametrize('base,tax',[('0','0'),('5000','0'),('20000','150'),('35000','600'),
    ('50000','1500'),('70000','3700'),('100000','9400'),('400000','84400'),
    ('600000','136400'),('2000000','528400'),('2000000.01','528400.003')])
def test_resident_schedule_cumulative_boundaries(base,tax):
    assert individual_tax(base,residency='resident',**COMMON)['gross_tax']==Decimal(tax)


@pytest.mark.parametrize('base,tax',[('0','0'),('150000','22500'),('150000.01','22500.0017'),
    ('600000','99000'),('600000.01','99000.0024'),('1000000','195000')])
def test_sme_thresholds(base,tax):
    assert company_tax(base,scheme='sme',sme_eligibility_confirmed=True,**COMMON)['gross_tax']==Decimal(tax)


def test_ordinary_company_and_nonresident_individual():
    assert company_tax('1000000',scheme='ordinary',sme_eligibility_confirmed=False,**COMMON)['gross_tax']==240000
    assert individual_tax('100000',residency='nonresident',**COMMON)['gross_tax']==30000


def test_allowed_rebate_credit_and_prepayment_do_not_mix():
    result=individual_tax('35000',residency='resident',**{**COMMON,'allowed_rebates':'400','allowed_tax_credits':'50','prepaid_tax':'300'})
    assert result['final_tax']==150 and result['balance_due']==-150
    for changes in [dict(allowed_rebates='601'),dict(allowed_rebates='400',allowed_tax_credits='201'),
                    dict(ordinary_treatment_confirmed=1),dict(assessment_year=True),dict(assessment_year=2025)]:
        with pytest.raises(ValueError): individual_tax('35000',residency='resident',**{**COMMON,**changes})
    with pytest.raises(ValueError):
        individual_tax('35000',residency='nonresident',**{**COMMON,'allowed_rebates':'400'})
    with pytest.raises(ValueError):
        company_tax('1000000',scheme='sme',sme_eligibility_confirmed=False,**COMMON)


@pytest.mark.parametrize('bad',[True,0.1,'NaN','-1','0.0000001','1000000000000000001'])
def test_invalid_money_fails(bad):
    with pytest.raises(ValueError): individual_tax(bad,residency='resident',**COMMON)


def test_source_original_hash():
    root=Path(__file__).resolve().parents[2]
    for source in SOURCES:
        assert hashlib.sha256((root/source['file']).read_bytes()).hexdigest()==source['sha256']


def test_case_adapter_rejects_mixed_dividends_and_nonresident_sme():
    data=dict(subject='company',jurisdiction='my',period_start='2026-01-01',period_end='2026-12-31',
              currency='MYR',residency='resident',claimed_deductions='0',carried_losses='0',facts_confirmed=True,
              incomes=[dict(category='business',source_jurisdiction='my',gross_amount='1000000',description='Business receipts')])
    basis=TypeAdapter(Assessment).validate_python(dict(policy='my_company_2026',chargeable_income='1000000',
        scheme='sme',sme_eligibility_confirmed=True,basis_confirmed=True,basis_explanation='Verified chargeable basis and SME conditions',
        **{k:v for k,v in COMMON.items() if k!='assessment_year'}))
    assert Decimal(calculate(IncomeTaxCase(**data),basis)['final_tax'])==195000
    data['residency']='nonresident'
    with pytest.raises(ValueError,match='residence'): calculate(IncomeTaxCase(**data),basis)
    data['residency']='resident';data['incomes'][0]['category']='dividend'
    with pytest.raises(ValueError,match='Dividend'): calculate(IncomeTaxCase(**data),basis)
