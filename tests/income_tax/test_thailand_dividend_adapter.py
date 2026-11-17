from copy import deepcopy
from decimal import Decimal

import pytest
from pydantic import TypeAdapter, ValidationError

from packages.contracts.income_assessment import Assessment
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.assessment import calculate


def inputs():
    case = dict(subject='individual', jurisdiction='th', period_start='2026-01-01',
        period_end='2026-12-31', currency='THB', residency='resident',
        claimed_deductions='160000', carried_losses='0', facts_confirmed=True,
        incomes=[dict(category='employment', source_jurisdiction='th', gross_amount='1000000', description='Salary'),
                 dict(category='dividend', source_jurisdiction='th', gross_amount='80000', description='Certified dividend')])
    basis = dict(policy='th_dividend_2026', election='aggregate',
        tranches=[dict(income_index=1, gross_dividend='80000', corporate_rate_percent='20', withholding_tax='8000', credit_eligible=True)],
        allowed_expenses_and_allowances='160000', other_prepaid_tax='100000',
        certificates_verified=True, recipient_eligibility_verified=True,
        election_scope_verified=True, ordinary_income_classification_verified=True,
        basis_confirmed=True, basis_explanation='Verified annual income, deductions and all dividend certificates')
    return case, basis


def run(case, basis):
    return calculate(IncomeTaxCase(**case), TypeAdapter(Assessment).validate_python(basis))


def test_saved_case_reconciles_and_returns_traceable_results():
    case, basis = inputs()
    original = deepcopy(basis)
    result = run(case, basis)
    assert Decimal(result['refund_due']) == 25000
    assert result['dividend_components']['tranches'][0]['income_index'] == 1
    assert basis == original


def test_multiple_rate_tranches_can_reconcile_one_saved_income():
    case, basis = inputs()
    basis['tranches'][0]['gross_dividend'] = '40000'
    basis['tranches'][0]['withholding_tax'] = '4000'
    basis['tranches'].append(dict(income_index=1, gross_dividend='40000',
        corporate_rate_percent='0', withholding_tax='4000', credit_eligible=True))
    result = run(case, basis)
    assert Decimal(result['dividend_credit']) == 10000
    assert len(result['dividend_components']['tranches']) == 2


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'wrong_index', 'outside_index', 'amount'])
def test_unreconciled_certificates_rejected(change):
    case, basis = inputs()
    if change == 'missing':
        case['incomes'].append(dict(category='dividend', source_jurisdiction='th', gross_amount='1', description='Other payer'))
    elif change == 'duplicate': basis['tranches'].append(deepcopy(basis['tranches'][0]))
    elif change == 'wrong_index': basis['tranches'][0]['income_index'] = 0
    elif change == 'outside_index': basis['tranches'][0]['income_index'] = 2
    else: basis['tranches'][0]['gross_dividend'] = '79999'
    with pytest.raises(ValueError): run(case, basis)


@pytest.mark.parametrize('change', [dict(residency='nonresident'), dict(claimed_deductions='0'),
    dict(carried_losses='1'), dict(period_end='2026-11-30')])
def test_case_scope_rejected(change):
    case, basis = inputs()
    with pytest.raises(ValueError): run({**case, **change}, basis)


@pytest.mark.parametrize('field', ['certificates_verified', 'recipient_eligibility_verified',
    'election_scope_verified', 'ordinary_income_classification_verified'])
def test_unverified_facts_rejected(field):
    case, basis = inputs()
    basis[field] = False
    with pytest.raises(ValueError): run(case, basis)


def test_foreign_tax_cannot_be_silently_ignored():
    case, basis = inputs()
    case['incomes'][1]['foreign_tax_paid'] = '1'
    with pytest.raises(ValueError): run(case, basis)


def test_contract_rejects_boolean_index():
    case, basis = inputs()
    basis['tranches'][0]['income_index'] = True
    with pytest.raises(ValidationError): run(case, basis)


def test_final_election_preserves_only_salary_prepayment():
    case, basis = inputs()
    basis['election'] = 'final_withholding'
    result = run(case, basis)
    assert Decimal(result['prepaid_tax']) == 100000
    assert Decimal(result['separate_final_dividend_tax']) == 8000
    assert Decimal(result['dividend_credit']) == 0
