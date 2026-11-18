from decimal import Decimal
from copy import deepcopy

import pytest
from pydantic import TypeAdapter

from packages.contracts.income_assessment import Assessment
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.assessment import calculate


def inputs():
    case=dict(subject='individual',jurisdiction='th',period_start='2026-01-01',
        period_end='2026-12-31',currency='THB',residency='resident',claimed_deductions='160000',
        carried_losses='0',facts_confirmed=True,incomes=[
            dict(category='employment',source_jurisdiction='th',gross_amount='1000000',description='Domestic salary'),
            dict(category='employment',source_jurisdiction='vn',gross_amount='500000',foreign_tax_paid='150000',description='Remitted foreign salary')])
    basis=dict(policy='th_foreign_income_2026',net_taxable_income='1340000',prepaid_tax='100000',
        ordinary_treatment_confirmed=True,assessable_income_classification_confirmed=True,
        tracing_fx_and_entitlement_verified=True,saved_tax_represents_original_pool_tax=True,
        basis_confirmed=True,basis_explanation='Verified original tax evidence, remittance tracing, treaty entitlement and FX',
        pools=[dict(pool_id='salary-2024',income_index=1,total_foreign_income='500000',
            foreign_income_tax_paid='150000',eligible_foreign_income_tax_paid='150000',previously_remitted_income='0',
            entitlement_and_fx_explanation='Verified VN treaty salary treatment and documented THB conversion',
            remittances=[dict(income_index=1,remitted_income='500000',income_date='2024-06-01',
                remittance_date='2026-06-01',days_in_thailand_in_income_year=180)])])
    return case,basis


def run(case,basis):
    return calculate(IncomeTaxCase(**case),TypeAdapter(Assessment).validate_python(basis))


def test_official_single_country_example_through_assessment_entry():
    result=run(*inputs())
    assert Decimal(result['gross_tax'])==200000
    assert Decimal(result['allowed_tax_credits']).quantize(Decimal('.01'))==Decimal('66666.67')
    assert Decimal(result['final_tax']).quantize(Decimal('.01'))==Decimal('133333.33')
    assert Decimal(result['balance_due']).quantize(Decimal('.01'))==Decimal('33333.33')
    assert result['foreign_income_reconciliation']['pools'][0]['income_index']==1


def test_pre2024_receipt_is_excluded_from_both_tax_base_and_credit():
    case,basis=inputs()
    basis['pools'][0]['remittances'][0]['income_date']='2023-06-01'
    basis['net_taxable_income']='840000'
    result=run(case,basis)
    assert Decimal(result['allowed_tax_credits'])==0
    assert Decimal(result['gross_tax'])==83000


def test_partial_remittance_keeps_original_tax_and_limits_attributed_fraction():
    case,basis=inputs()
    basis['pools'][0]['total_foreign_income']='1000000'
    basis['pools'][0]['eligible_foreign_income_tax_paid']='10000'
    result=run(case,basis)
    assert Decimal(result['allowed_tax_credits'])==5000


@pytest.mark.parametrize('change',['net','paid','meaning','entitlement','classification','resident','period','losses','index'])
def test_invalid_case_or_unverified_basis_cannot_assess(change):
    case,basis=inputs()
    if change=='net':basis['net_taxable_income']='1340001'
    if change=='paid':basis['pools'][0]['foreign_income_tax_paid']='149999'
    if change=='meaning':basis['saved_tax_represents_original_pool_tax']=False
    if change=='entitlement':basis['tracing_fx_and_entitlement_verified']=False
    if change=='classification':basis['assessable_income_classification_confirmed']=False
    if change=='resident':case['residency']='nonresident'
    if change=='period':case['period_start']='2025-01-01'
    if change=='losses':case['carried_losses']='1'
    if change=='index':basis['pools'][0]['remittances'][0]['income_index']=0
    with pytest.raises(ValueError):run(case,basis)


def test_repeating_attribution_is_not_rounded_or_rejected_between_stages():
    case,basis=inputs()
    basis['pools'][0]['total_foreign_income']='1500000'
    basis['pools'][0]['eligible_foreign_income_tax_paid']='10000'
    result=run(case,basis)
    assert Decimal(result['allowed_tax_credits']).quantize(Decimal('.01'))==Decimal('3333.33')


def test_multi_country_multi_category_split_receipts_follow_official_formula():
    case,basis=inputs()
    template=deepcopy(basis['pools'][0])
    for country,category,gross,original,paid,index in [
        ('vn','dividend','250000','250000','75000',2),
        ('cn','employment','200000','200000','20000',3),
        ('cn','dividend','25000','50000','5000',4),
    ]:
        case['incomes'].append(dict(category=category,source_jurisdiction=country,
            gross_amount=gross,foreign_tax_paid=paid,description='Traced foreign income for official example'))
        pool=deepcopy(template)
        pool.update(pool_id=f'{country}-{index}',income_index=index,total_foreign_income=original,
                    foreign_income_tax_paid=paid,eligible_foreign_income_tax_paid=paid)
        pool['remittances'][0].update(income_index=index,remitted_income=gross)
        if index==4:
            pool['remittances'][0]['remitted_income']='10000'
            second=deepcopy(pool['remittances'][0]);second['remitted_income']='15000'
            second['remittance_date']='2026-07-01';pool['remittances'].append(second)
        basis['pools'].append(pool)
    basis['net_taxable_income']='1815000'
    result=run(case,basis)
    assert Decimal(result['gross_tax'])==318750
    countries={r['country']:r for r in result['foreign_credit']['countries']}
    assert Decimal(countries['vn']['remitted_assessable_income'])==750000
    assert Decimal(countries['cn']['eligible_attributable_tax'])==22500
    assert Decimal(result['allowed_tax_credits']).quantize(Decimal('.01'))==Decimal('143544.30')
    assert Decimal(result['final_tax']).quantize(Decimal('.01'))==Decimal('175205.70')
    assert len(result['foreign_income_reconciliation']['pools'])==4
