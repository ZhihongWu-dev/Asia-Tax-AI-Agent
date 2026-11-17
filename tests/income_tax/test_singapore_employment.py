from datetime import date
from decimal import Decimal

import pytest

from packages.income_tax.singapore_employment import resident_employment_tax


def compute(gross='80000', **changes):
    args = dict(assessment_year=2026, birth_date=date(1990, 1, 1),
                disability_relief_eligible=False, allowed_employment_expenses='0',
                allowed_donation_deduction='0', allowed_cpf_relief='16000',
                allowed_other_personal_reliefs='12000', available_parenthood_rebate='2500',
                prepaid_tax='0', eligibility_and_allocations_verified=True)
    return resident_employment_tax(gross, **{**args, **changes})


def test_iras_ya2026_mrs_chen_example():
    result = compute()
    assert result['chargeable_income'] == Decimal('51000')
    assert result['gross_tax'] == Decimal('1320')
    assert result['parenthood_rebate_used'] == Decimal('1320')
    assert result['parenthood_rebate_carried_forward'] == Decimal('1180')
    assert result['annual_liability'] == 0
    assert result['refund_due'] == 0  # Unused PTR is carried, never refunded.


@pytest.mark.parametrize('born,disabled,expected', [
    (1971, False, 1000), (1970, False, 6000), (1966, False, 6000),
    (1965, False, 8000), (1971, True, 4000), (1970, True, 10000), (1965, True, 12000),
])
def test_age_at_end_of_income_year_and_disability(born, disabled, expected):
    result = compute(birth_date=date(born, 12, 31), disability_relief_eligible=disabled)
    assert result['earned_income_relief'] == expected


def test_relief_is_limited_to_net_earned_income_before_donation():
    result = compute('6000', birth_date=date(1970, 1, 1), allowed_employment_expenses='1000',
                     allowed_donation_deduction='2000', allowed_cpf_relief='0',
                     allowed_other_personal_reliefs='0')
    assert result['earned_income_relief'] == 5000
    assert result['assessable_income'] == 3000
    assert result['chargeable_income'] == 0


def test_overall_cap_does_not_cap_donation_deduction():
    result = compute('150000', allowed_donation_deduction='10000',
                     allowed_cpf_relief='20400', allowed_other_personal_reliefs='70000',
                     available_parenthood_rebate='0', prepaid_tax='3000')
    assert result['personal_reliefs_before_cap'] == 91400
    assert result['personal_reliefs_allowed'] == 80000
    assert result['chargeable_income'] == 60000
    assert result['annual_liability'] == 1950
    assert result['refund_due'] == 1050


@pytest.mark.parametrize('changes', [
    {'assessment_year': 2027}, {'eligibility_and_allocations_verified': False},
    {'eligibility_and_allocations_verified': 1}, {'disability_relief_eligible': 1},
    {'birth_date': date(2026, 1, 1)}, {'birth_date': '1990-01-01'},
    {'allowed_employment_expenses': '80001'}, {'allowed_donation_deduction': '80001'},
    {'allowed_cpf_relief': '80001'}, {'prepaid_tax': '-1'},
])
def test_invalid_or_unverified_basis_rejected(changes):
    with pytest.raises(ValueError):
        compute(**changes)


def saved_case_and_basis():
    from packages.contracts.income_tax import IncomeTaxCase
    from packages.contracts.income_assessment import SGEmployment
    case = IncomeTaxCase(subject='individual', jurisdiction='sg', residency='resident',
        period_start='2025-01-01', period_end='2025-12-31', currency='SGD',
        facts_confirmed=True, claimed_deductions='28000', carried_losses='0',
        incomes=[dict(category='employment', source_jurisdiction='sg', gross_amount='80000', description='Annual salary')])
    basis = SGEmployment(policy='sg_employment_ya2026', basis_confirmed=True,
        basis_explanation='Verified YA2026 resident salary, CPF and family relief allocations.',
        birth_date=date(1990, 1, 1), disability_relief_eligible=False,
        allowed_employment_expenses='0', allowed_donation_deduction='0',
        allowed_cpf_relief='16000', allowed_other_personal_reliefs='12000',
        available_parenthood_rebate='2500', prepaid_tax='100', eligibility_and_allocations_verified=True)
    return case, basis


def test_saved_income_drives_settlement_and_serializes_money_exactly():
    from packages.income_tax.assessment import calculate
    case, basis = saved_case_and_basis()
    result = calculate(case, basis)
    assert result['chargeable_income'] == '51000'
    assert Decimal(result['refund_due']) == 100
    assert Decimal(result['parenthood_rebate_carried_forward']) == 1180


@pytest.mark.parametrize('change', [
    {'claimed_deductions': Decimal('29000')}, {'carried_losses': Decimal('1')},
    {'subject': 'company'}, {'residency': 'nonresident'}, {'period_end': date(2026,12,31)},
])
def test_saved_case_inconsistent_or_outside_policy_rejected(change):
    from packages.income_tax.assessment import calculate
    case, basis = saved_case_and_basis()
    with pytest.raises(ValueError):
        calculate(case.model_copy(update=change), basis)


@pytest.mark.parametrize('change', [{'category':'business'}, {'source_jurisdiction':'my'}, {'foreign_tax_paid':Decimal('1')}])
def test_employment_route_does_not_silently_consume_other_income(change):
    from packages.income_tax.assessment import calculate
    case, basis = saved_case_and_basis()
    case.incomes[0] = case.incomes[0].model_copy(update=change)
    with pytest.raises(ValueError):
        calculate(case, basis)
