from decimal import Decimal, localcontext
import hashlib
from pathlib import Path
import pytest
from pydantic import TypeAdapter
from packages.contracts.income_tax import IncomeTaxCase
from packages.contracts.income_assessment import Assessment
from packages.income_tax.assessment import calculate
from packages.income_tax.indonesia import company_tax, resident_individual_tax, SOURCES

COMMON=dict(tax_year=2026,ordinary_annual_treatment_confirmed=True,prepaid_tax='0')
PERSONAL=dict(ptkp_status='TK/0',ptkp_entitlement_confirmed=True,**COMMON)
COMPANY=dict(gross_receipts_scope_confirmed=True,**COMMON)


@pytest.mark.parametrize('base,tax',[('0','0'),('60000000','3000000'),('250000000','31500000'),
    ('500000000','94000000'),('5000000000','1444000000'),('5000001000','1444000350')])
def test_personal_cumulative_bands(base,tax):
    net=Decimal(base)+Decimal('54000000')
    assert resident_individual_tax(net,**PERSONAL)['final_tax']==Decimal(tax)


@pytest.mark.parametrize('net,base,tax',[('53999999.99','0','0'),('54000999.99','0','0'),
    ('54001000','1000','50'),('114000999.99','60000000','3000000'),('114001000','60001000','3000150')])
def test_personal_allowance_and_thousand_rounding(net,base,tax):
    result=resident_individual_tax(net,**PERSONAL)
    assert result['taxable_income']==Decimal(base)
    assert result['final_tax']==Decimal(tax)


@pytest.mark.parametrize('status,allowance',[('TK/0','54000000'),('TK/1','58500000'),('TK/2','63000000'),
    ('TK/3','67500000'),('K/0','58500000'),('K/1','63000000'),('K/2','67500000'),('K/3','72000000')])
def test_start_of_year_ptkp_entitlements(status,allowance):
    assert resident_individual_tax('300000000',**{**PERSONAL,'ptkp_status':status})['ptkp_allowance']==Decimal(allowance)


def test_dgt_personal_example_and_excess_prepayment():
    result=resident_individual_tax('300000000',**{**PERSONAL,'ptkp_status':'K/1','prepaid_tax':'15550000'})
    assert result['taxable_income']==237000000 and result['final_tax']==29550000
    assert result['balance_due']==14000000
    assert resident_individual_tax('0',**{**PERSONAL,'prepaid_tax':'1000'})['balance_due']==-1000


def test_dgt_company_example():
    result=company_tax('610000000',article31e_gross_receipts='6000000000',**{**COMPANY,'prepaid_tax':'130000000'})
    assert result['article31e_eligible_base']==488000000
    assert result['article31e_other_base']==122000000
    assert result['final_tax']==80520000 and result['balance_due']==-49480000


@pytest.mark.parametrize('turnover,eligible,tax',[('4800000000','1000000000','110000000'),
    ('4800000001','999999000','110000110'),('50000000000','96000000','209440000'),
    ('50000000001','0','220000000')])
def test_31e_boundaries_and_allocation_rounding(turnover,eligible,tax):
    result=company_tax('1000000999.99',article31e_gross_receipts=turnover,**COMPANY)
    assert result['taxable_income']==1000000000
    assert result['article31e_eligible_base']==Decimal(eligible)
    assert result['article31e_eligible_base']+result['article31e_other_base']==result['taxable_income']
    assert result['final_tax']==Decimal(tax)


def test_zero_turnover_and_decimal_context():
    assert company_tax('0',article31e_gross_receipts='0',**COMPANY)['final_tax']==0
    with pytest.raises(ValueError): company_tax('1',article31e_gross_receipts='0',**COMPANY)
    with localcontext() as ctx:
        ctx.prec=8
        result=company_tax('1000000000000000000',article31e_gross_receipts='1000000000000000000',**COMPANY)
        assert result['final_tax']==Decimal('220000000000000000')


@pytest.mark.parametrize('changes',[dict(tax_year=2025),dict(tax_year=True),
    dict(ordinary_annual_treatment_confirmed=1),dict(ptkp_status='K/I/1'),
    dict(ptkp_status='TK/4'),dict(ptkp_entitlement_confirmed=False),dict(ptkp_entitlement_confirmed=1)])
def test_unverified_or_unsupported_treatment(changes):
    with pytest.raises(ValueError): resident_individual_tax('300000000',**{**PERSONAL,**changes})


@pytest.mark.parametrize('bad',[True,0.1,'NaN','-1','0.0000001','1000000000000000001'])
def test_invalid_amounts(bad):
    with pytest.raises(ValueError): resident_individual_tax(bad,**PERSONAL)


def test_original_hashes():
    root=Path(__file__).resolve().parents[2]
    for source in SOURCES:
        assert hashlib.sha256((root/source['file']).read_bytes()).hexdigest()==source['sha256']


def test_adapter_uses_saved_gross_and_rejects_ineligible_cases():
    data=dict(subject='company',jurisdiction='id',period_start='2026-01-01',period_end='2026-12-31',
        currency='IDR',residency='resident',claimed_deductions='0',carried_losses='0',facts_confirmed=True,
        incomes=[dict(category='business',source_jurisdiction='id',gross_amount='6000000000',description='Total ordinary receipts')])
    raw=dict(policy='id_company_2026',taxable_income_before_rounding='610000000',gross_receipts_scope_confirmed=True,
        ordinary_annual_treatment_confirmed=True,prepaid_tax='130000000',basis_confirmed=True,
        basis_explanation='Verified ordinary receipts and all tax-basis adjustments')
    adapter=TypeAdapter(Assessment)
    assert Decimal(calculate(IncomeTaxCase(**data),adapter.validate_python(raw))['balance_due'])==-49480000
    with pytest.raises(ValueError): calculate(IncomeTaxCase(**data),adapter.validate_python({**raw,'gross_receipts_scope_confirmed':False}))
    for changes in [dict(residency='nonresident'),dict(subject='individual'),dict(period_start='2026-02-01')]:
        with pytest.raises(ValueError): calculate(IncomeTaxCase(**{**data,**changes}),adapter.validate_python(raw))
    for category,source in [('dividend','id'),('rental','id'),('business','sg')]:
        data['incomes'][0].update(category=category,source_jurisdiction=source,foreign_tax_paid='0')
        with pytest.raises(ValueError): calculate(IncomeTaxCase(**data),adapter.validate_python(raw))
    data['subject']='individual'
    data['incomes'][0].update(category='employment',source_jurisdiction='id',gross_amount='300000000')
    raw=dict(policy='id_resident_2026',net_income_before_ptkp='300000000',ptkp_status='K/1',
        ptkp_entitlement_confirmed=True,ordinary_annual_treatment_confirmed=True,prepaid_tax='15550000',
        basis_confirmed=True,basis_explanation='Verified net income, start-of-year PTKP and withheld tax')
    assert Decimal(calculate(IncomeTaxCase(**data),adapter.validate_python(raw))['balance_due'])==14000000
    with pytest.raises(ValueError): calculate(IncomeTaxCase(**data),adapter.validate_python({**raw,'net_income_before_ptkp':'300000001'}))
