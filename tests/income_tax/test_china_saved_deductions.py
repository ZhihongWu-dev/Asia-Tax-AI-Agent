from decimal import Decimal

import pytest

from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.assessment import calculate
from tests.income_tax.test_assessment_workflow import ADAPTER, COMMON, facts


def inputs():
    case = facts('cn', 'individual')
    case['claimed_deductions'] = '43000'
    basis = dict(policy='cn_comprehensive_2026', allowed_special_deductions='20000',
        allowed_additional_deductions='12000', allowed_other_deductions='6000',
        allowed_donations='5000', allowed_tax_reductions='1000', prepaid_tax='200000',
        domestic_normal_treatment_confirmed=True, **COMMON)
    return case, basis


def test_saved_manual_deductions_reconcile_without_double_counting_automatic_amounts():
    case, basis = inputs()
    result = calculate(IncomeTaxCase(**case), ADAPTER.validate_python(basis))
    assert Decimal(result['taxable_income']) == 897000
    assert Decimal(result['annual_liability']) == 227030
    assert Decimal(result['balance_due']) == 27030


@pytest.mark.parametrize('claimed', ['0', '42999', '43001', '103000'])
def test_conflicting_saved_deductions_are_not_silently_ignored(claimed):
    case, basis = inputs()
    case['claimed_deductions'] = claimed
    with pytest.raises(ValueError, match='deductions must reconcile'):
        calculate(IncomeTaxCase(**case), ADAPTER.validate_python(basis))


def test_comprehensive_income_does_not_silently_consume_business_losses():
    case, basis = inputs()
    case['carried_losses'] = '1'
    with pytest.raises(ValueError, match='carried losses'):
        calculate(IncomeTaxCase(**case), ADAPTER.validate_python(basis))


def test_domestic_policy_does_not_silently_drop_saved_foreign_tax():
    case, basis = inputs()
    case['incomes'][0]['foreign_tax_paid'] = '1'
    with pytest.raises(ValueError, match='foreign tax'):
        calculate(IncomeTaxCase(**case), ADAPTER.validate_python(basis))
