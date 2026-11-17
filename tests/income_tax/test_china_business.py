from decimal import Decimal

import pytest

from packages.income_tax.china_business import annual_business_tax


def calculate(base, **changes):
    options = dict(tax_year=2026, business_form='individual_operator',
        allowed_other_tax_reductions='0', prepaid_tax='0',
        annual_aggregation_and_classification_verified=True,
        deductions_losses_and_no_double_claim_verified=True)
    options.update(changes)
    return annual_business_tax(base, **options)


@pytest.mark.parametrize('base,gross', [
    ('0','0'), ('30000','1500'), ('30000.01','1500.001'),
    ('90000','7500'), ('90000.01','7500.002'), ('300000','49500'),
    ('300000.01','49500.003'), ('500000','109500'), ('500000.01','109500.0035'),
])
def test_business_schedule_boundaries(base, gross):
    result = calculate(base, business_form='other_business')
    assert result['gross_tax'] == Decimal(gross)
    assert result['annual_liability'] == Decimal(gross)
    assert result['individual_operator_half_reduction'] == 0


@pytest.mark.parametrize('base,other,relief,liability', [
    ('80000','2000','2250','2250'),
    ('2400000','6000','314750','453750'),
    ('2000000','0','317250','317250'),
    ('2000001','0','317250','317250.35'),
    ('2300000','0','317250','422250'),
])
def test_official_examples_and_single_annual_cap(base, other, relief, liability):
    result = calculate(base, allowed_other_tax_reductions=other)
    assert result['individual_operator_half_reduction'] == Decimal(relief)
    assert result['annual_liability'] == Decimal(liability)


def test_zero_income_and_excess_prepaid_return_refund_without_division_by_zero():
    result = calculate('0', prepaid_tax='123.45')
    assert result['annual_liability'] == result['payable'] == 0
    assert result['refundable'] == Decimal('123.45')


@pytest.mark.parametrize('change', [dict(tax_year=2025), dict(tax_year=True),
    dict(business_form='company'), dict(annual_aggregation_and_classification_verified=False),
    dict(annual_aggregation_and_classification_verified=1),
    dict(deductions_losses_and_no_double_claim_verified=False),
    dict(allowed_other_tax_reductions='6501'), dict(prepaid_tax=0.1)])
def test_invalid_or_unverified_inputs_fail(change):
    with pytest.raises(ValueError):
        calculate('80000', **change)


def test_unestablished_relief_allocation_is_not_turned_into_negative_relief():
    with pytest.raises(ValueError, match='allocation'):
        calculate('2400000', allowed_other_tax_reductions='774500')


def saved_inputs():
    from tests.income_tax.test_assessment_workflow import COMMON, facts
    case = facts('cn', 'individual')
    case['incomes'] = [dict(category='business', source_jurisdiction='cn',
        gross_amount=value, description='Verified business receipts') for value in ('1200000', '1800000')]
    case.update(claimed_deductions='500000', carried_losses='100000')
    basis = dict(policy='cn_business_2026', taxable_income='2400000',
        business_form='individual_operator', allowed_other_tax_reductions='6000',
        prepaid_tax='500000', annual_aggregation_and_classification_verified=True,
        deductions_losses_and_no_double_claim_verified=True, **COMMON)
    return case, basis


def test_saved_case_aggregates_businesses_and_preserves_refund():
    from packages.contracts.income_tax import IncomeTaxCase
    from packages.income_tax.assessment import calculate as assess
    from tests.income_tax.test_assessment_workflow import ADAPTER
    case, basis = saved_inputs()
    result = assess(IncomeTaxCase(**case), ADAPTER.validate_python(basis))
    assert Decimal(result['annual_liability']) == 453750
    assert Decimal(result['refundable']) == 46250
    assert Decimal(result['half_relief_eligible_base']) == 2000000


@pytest.mark.parametrize('field,value', [('subject','company'), ('residency','nonresident'),
    ('claimed_deductions','0'), ('carried_losses','0'), ('period_start','2025-01-01')])
def test_saved_case_incompatible_facts_fail(field, value):
    from packages.contracts.income_tax import IncomeTaxCase
    from packages.income_tax.assessment import calculate as assess
    from tests.income_tax.test_assessment_workflow import ADAPTER
    case, basis = saved_inputs()
    case[field] = value
    with pytest.raises(ValueError):
        assess(IncomeTaxCase(**case), ADAPTER.validate_python(basis))


@pytest.mark.parametrize('change', [dict(category='employment'),
    dict(source_jurisdiction='hk', foreign_tax_paid='0'), dict(foreign_tax_paid='10')])
def test_nonbusiness_or_foreign_income_cannot_enter_domestic_pool(change):
    from packages.contracts.income_tax import IncomeTaxCase
    from packages.income_tax.assessment import calculate as assess
    from tests.income_tax.test_assessment_workflow import ADAPTER
    case, basis = saved_inputs()
    case['incomes'][0].update(change)
    with pytest.raises(ValueError):
        assess(IncomeTaxCase(**case), ADAPTER.validate_python(basis))
