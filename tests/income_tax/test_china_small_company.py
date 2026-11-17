from decimal import Decimal

import pytest

from packages.income_tax.china import small_low_profit_company_tax


def compute(base='3000000', **changes):
    args = dict(tax_year=2026, annual_average_employees='300', annual_average_assets='50000000',
        unrestricted_industry_confirmed=True, statutory_averages_and_eligibility_verified=True,
        allowed_tax_credits='0', prepaid_tax='0')
    args.update(changes)
    return small_low_profit_company_tax(base, **args)


@pytest.mark.parametrize('base,expected', [('0','0'), ('1000000','50000'),
    ('1000000.01','50000.0005'), ('3000000','150000')])
def test_whole_eligible_base_uses_current_five_percent_not_old_bands(base, expected):
    result = compute(base)
    assert result['annual_liability'] == Decimal(expected)
    assert result['rate'] == Decimal('.2')
    assert result['income_inclusion_fraction'] == Decimal('.25')


@pytest.mark.parametrize('base,change', [('3000000.01', {}),
    ('3000000', dict(annual_average_employees='300.001')),
    ('3000000', dict(annual_average_assets='50000000.01'))])
def test_any_exceeded_threshold_disqualifies_entire_preference(base, change):
    with pytest.raises(ValueError, match='threshold'):
        compute(base, **change)


def test_fractional_statutory_average_is_not_rounded_to_create_eligibility():
    assert compute(annual_average_employees='299.875')['annual_liability'] == 150000
    with pytest.raises(ValueError):
        compute(annual_average_employees='300.125')


def test_credit_cap_and_overpayment_refund():
    result = compute(allowed_tax_credits='10000', prepaid_tax='200000')
    assert result['annual_liability'] == 140000
    assert result['refundable'] == 60000
    assert result['payable'] == 0
    with pytest.raises(ValueError, match='credits'):
        compute(allowed_tax_credits='150000.01')


@pytest.mark.parametrize('change', [dict(unrestricted_industry_confirmed=False),
    dict(unrestricted_industry_confirmed=1), dict(statutory_averages_and_eligibility_verified=False),
    dict(tax_year=2025), dict(tax_year=True), dict(annual_average_assets=0.1)])
def test_unverified_or_invalid_values_fail(change):
    with pytest.raises(ValueError):
        compute(**change)


def saved_inputs():
    from tests.income_tax.test_assessment_workflow import COMMON, facts
    case = facts()
    case['incomes'][0]['gross_amount'] = '4000000'
    case.update(claimed_deductions='900000', carried_losses='100000')
    basis = dict(policy='cn_small_company_2026', taxable_income='3000000',
        annual_average_employees='300', annual_average_assets='50000000',
        unrestricted_industry_confirmed=True, statutory_averages_and_eligibility_verified=True,
        allowed_tax_credits='10000', prepaid_tax='200000', **COMMON)
    return case, basis


def test_saved_case_reconciles_base_and_keeps_refund():
    from packages.contracts.income_tax import IncomeTaxCase
    from packages.income_tax.assessment import calculate
    from tests.income_tax.test_assessment_workflow import ADAPTER
    case, basis = saved_inputs()
    result = calculate(IncomeTaxCase(**case), ADAPTER.validate_python(basis))
    assert Decimal(result['refundable']) == 60000


@pytest.mark.parametrize('field,value', [('subject','individual'), ('residency','nonresident'),
    ('claimed_deductions','0'), ('carried_losses','0'), ('period_end','2026-06-30')])
def test_mismatched_saved_case_cannot_claim_preference(field, value):
    from packages.contracts.income_tax import IncomeTaxCase
    from packages.income_tax.assessment import calculate
    from tests.income_tax.test_assessment_workflow import ADAPTER
    case, basis = saved_inputs()
    case[field] = value
    with pytest.raises(ValueError):
        calculate(IncomeTaxCase(**case), ADAPTER.validate_python(basis))
