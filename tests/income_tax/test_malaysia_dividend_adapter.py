from copy import deepcopy
from decimal import Decimal

import pytest
from pydantic import TypeAdapter

from packages.contracts.income_assessment import Assessment
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.assessment import calculate


def inputs():
    case = dict(subject='individual', jurisdiction='my', period_start='2026-01-01',
        period_end='2026-12-31', currency='MYR', residency='resident',
        claimed_deductions='15000', carried_losses='0', facts_confirmed=True,
        incomes=[dict(category='employment', source_jurisdiction='my', gross_amount='100000', description='Salary'),
                 dict(category='dividend', source_jurisdiction='my', gross_amount='150000', description='Domestic dividend')])
    basis = dict(policy='my_dividend_2026', dividend_statutory_before_threshold='150000',
        ordinary_statutory_income='100000', chargeable_income='135000',
        allowed_rebates='0', allowed_tax_credits='0', prepaid_tax='9000',
        separate_domestic_assessment_verified=True, dividend_scope_verified=True,
        bases_verified=True, settlement_inputs_verified=True, basis_confirmed=True,
        basis_explanation='Verified separate domestic dividend assessment and statutory deductions')
    return case, basis


def run(case, basis):
    return calculate(IncomeTaxCase(**case), TypeAdapter(Assessment).validate_python(basis))


def test_saved_case_matches_annual_result_without_mutating_inputs():
    case,basis=inputs(); original=deepcopy(basis)
    result=run(case,basis)
    assert Decimal(result['final_tax']) == 8400
    assert Decimal(result['refund_due']) == 600
    assert Decimal(result['dividend_threshold_used']) == 100000
    assert basis==original


def test_annual_threshold_is_not_repeated_for_multiple_payers():
    case,basis=inputs()
    case['incomes'][1]['gross_amount']='75000'
    case['incomes'].append({**case['incomes'][1], 'description':'Second payer'})
    result=run(case,basis)
    assert Decimal(result['dividend_statutory_income'])==50000


def test_expense_and_relief_split_reconciles_saved_deductions():
    case,basis=inputs();case['claimed_deductions']='20000'
    basis.update(dividend_statutory_before_threshold='148000',ordinary_statutory_income='97000')
    basis['chargeable_income']='130000'
    assert Decimal(run(case,basis)['reconciled_deductions'])==20000


@pytest.mark.parametrize('change', [dict(subject='company'),dict(carried_losses='1'),
    dict(claimed_deductions='115000'),dict(period_end='2026-11-30')])
def test_inconsistent_case_rejected(change):
    case,basis=inputs()
    with pytest.raises(ValueError):run({**case,**change},basis)


@pytest.mark.parametrize('change', [dict(dividend_statutory_before_threshold='150001'),
    dict(ordinary_statutory_income='100001'),dict(chargeable_income='150001'),
    dict(separate_domestic_assessment_verified=False),dict(dividend_scope_verified=False),
    dict(bases_verified=False),dict(settlement_inputs_verified=False)])
def test_unverified_or_inconsistent_basis_rejected(change):
    case,basis=inputs()
    with pytest.raises(ValueError):run(case,{**basis,**change})


@pytest.mark.parametrize('change', [dict(source_jurisdiction='sg'),
    dict(foreign_tax_paid='1'),dict(category='capital_gain')])
def test_outside_income_scope_rejected(change):
    case,basis=inputs();case['incomes'][1].update(change)
    with pytest.raises(ValueError):run(case,basis)


def test_nonresident_uses_separate_rate_and_rejects_resident_rebate():
    case,basis=inputs();case['residency']='nonresident'
    assert Decimal(run(case,basis)['final_tax'])==27900
    basis['allowed_rebates']='1'
    with pytest.raises(ValueError):run(case,basis)
