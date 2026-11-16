from decimal import Decimal
import hashlib
from pathlib import Path
import pytest
from pydantic import TypeAdapter
from packages.contracts.income_tax import IncomeTaxCase
from packages.contracts.income_assessment import Assessment
from packages.income_tax.assessment import calculate
from packages.income_tax.thailand import company_tax, resident_individual_tax, SOURCES

COMMON=dict(tax_year=2026,ordinary_treatment_confirmed=True,allowed_tax_credits='0',prepaid_tax='0')


@pytest.mark.parametrize('base,tax',[('0','0'),('150000','0'),('300000','7500'),
    ('500000','27500'),('750000','65000'),('1000000','115000'),('2000000','365000'),
    ('5000000','1265000'),('5000000.01','1265000.0035')])
def test_progressive_boundaries(base,tax):
    result=resident_individual_tax(base,nonemployment_assessable_gross='0',**COMMON)
    assert result['final_tax']==Decimal(tax)


@pytest.mark.parametrize('gross,raw,minimum',[('119999.99','0','0'),('120000','600','0'),
    ('1000000','5000','0'),('1000000.01','5000.00005','5000.00005'),('2000000','10000','10000')])
def test_minimum_threshold_and_inclusive_exemption(gross,raw,minimum):
    result=resident_individual_tax('0',nonemployment_assessable_gross=gross,**COMMON)
    assert result['minimum_tax_before_exemption']==Decimal(raw)
    assert result['final_tax']==Decimal(minimum)
    assert result['minimum_tax_exempt']==(Decimal(raw)<=5000)


def test_progressive_wins_and_prepayment_is_separate():
    result=resident_individual_tax('1000000',nonemployment_assessable_gross='2000000',
        **{**COMMON,'allowed_tax_credits':'1000','prepaid_tax':'120000'})
    assert result['selected_basis']=='progressive'
    assert result['final_tax']==114000 and result['balance_due']==-6000


@pytest.mark.parametrize('base,tax',[('300000','0'),('300000.01','0.0015'),
    ('3000000','405000'),('4000000','605000')])
def test_sme_boundaries(base,tax):
    assert company_tax(base,scheme='sme',sme_eligibility_confirmed=True,**COMMON)['final_tax']==Decimal(tax)


def test_company_normal_rate_and_explicit_eligibility():
    assert company_tax('4000000',scheme='ordinary',sme_eligibility_confirmed=False,**COMMON)['final_tax']==800000
    with pytest.raises(ValueError):
        company_tax('4000000',scheme='sme',sme_eligibility_confirmed=False,**COMMON)
    for changes in [dict(tax_year=2025),dict(tax_year=True),dict(ordinary_treatment_confirmed=1),dict(allowed_tax_credits='1')]:
        with pytest.raises(ValueError):
            resident_individual_tax('0',nonemployment_assessable_gross='0',**{**COMMON,**changes})


@pytest.mark.parametrize('bad',[True,0.1,'NaN','-1','0.0000001','1000000000000000001'])
def test_invalid_money(bad):
    with pytest.raises(ValueError):
        resident_individual_tax(bad,nonemployment_assessable_gross='0',**COMMON)


def test_original_source_hashes():
    root=Path(__file__).resolve().parents[2]
    for source in SOURCES:
        assert hashlib.sha256((root/source['file']).read_bytes()).hexdigest()==source['sha256']


def test_adapter_derives_gross_excluding_employment_and_rejects_unsupported_inputs():
    data=dict(subject='individual',jurisdiction='th',period_start='2026-01-01',period_end='2026-12-31',
        currency='THB',residency='resident',claimed_deductions='0',carried_losses='0',facts_confirmed=True,
        incomes=[dict(category='business',source_jurisdiction='th',gross_amount='1000000',description='Business receipts'),
                 dict(category='employment',source_jurisdiction='th',gross_amount='2000000',description='Employment receipts')])
    raw=dict(policy='th_resident_2026',net_taxable_income='150000',assessable_income_classification_confirmed=True,
        basis_confirmed=True,basis_explanation='Verified section 40 classification and deductions',
        **{k:v for k,v in COMMON.items() if k!='tax_year'})
    adapter=TypeAdapter(Assessment)
    result=calculate(IncomeTaxCase(**data),adapter.validate_python(raw))
    assert Decimal(result['nonemployment_assessable_gross'])==1000000
    assert Decimal(result['final_tax'])==0
    data['incomes'][0]['gross_amount']='1000000.01'
    assert Decimal(calculate(IncomeTaxCase(**data),adapter.validate_python(raw))['final_tax'])==Decimal('5000.00005')
    for changes in [dict(assessable_income_classification_confirmed=False),dict(net_taxable_income='4000000')]:
        with pytest.raises(ValueError): calculate(IncomeTaxCase(**data),adapter.validate_python({**raw,**changes}))
    for changes in [dict(residency='nonresident'),dict(subject='company')]:
        with pytest.raises(ValueError): calculate(IncomeTaxCase(**{**data,**changes}),adapter.validate_python(raw))
    for category,source in [('dividend','th'),('interest','th'),('business','sg')]:
        data['incomes'][0].update(category=category,source_jurisdiction=source)
        with pytest.raises(ValueError): calculate(IncomeTaxCase(**data),adapter.validate_python(raw))
