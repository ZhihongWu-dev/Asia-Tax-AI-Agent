from decimal import Decimal
import pytest
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.assessment import calculate
from tests.income_tax.test_assessment_workflow import ADAPTER, COMPANY, facts
from tests.income_tax.test_china_small_company import saved_inputs


def run(data, basis):
    return calculate(IncomeTaxCase(**data), ADAPTER.validate_python(basis))


def test_ordinary_company_cannot_use_unrelated_manual_tax_base():
    data = facts()
    data['incomes'][0]['gross_amount'] = '100'
    with pytest.raises(ValueError, match='must reconcile'):
        run(data, COMPANY)


@pytest.mark.parametrize('small', [False, True])
def test_exclusions_are_separate_from_deductions_and_apply_before_losses(small):
    data, basis = saved_inputs() if small else (facts(), dict(COMPANY))
    data['incomes'][0]['gross_amount'] = '800000'
    data['incomes'].append(dict(category='dividend',source_jurisdiction='cn',
        gross_amount='200000',description='Verified qualifying domestic equity distribution'))
    data.update(claimed_deductions='300000', carried_losses='100000')
    basis.update(non_taxable_income='50000', exempt_income='200000', taxable_income='350000',
        allowed_tax_credits='0')
    result = run(data, basis)
    paper = result['basis_reconciliation']
    assert Decimal(paper['total_income']) == 1000000
    assert Decimal(paper['income_before_loss_relief']) == 450000
    assert Decimal(paper['prior_losses_used']) == 100000
    assert Decimal(paper['taxable_income']) == 350000
    assert Decimal(result['annual_liability']) == (17500 if small else 87500)


@pytest.mark.parametrize('deductions,losses,used,unused,current', [
    ('900000','300000','100000','200000','0'),
    ('1200000','300000','0','300000','200000'),
])
def test_loss_use_does_not_create_negative_base_or_consume_losses_during_current_loss(deductions,losses,used,unused,current):
    data = facts()
    data.update(claimed_deductions=deductions, carried_losses=losses)
    result = run(data, {**COMPANY, 'taxable_income':'0'})
    paper = result['basis_reconciliation']
    assert Decimal(result['annual_liability']) == 0
    assert Decimal(paper['prior_losses_used']) == Decimal(used)
    assert Decimal(paper['prior_losses_unused']) == Decimal(unused)
    assert Decimal(paper['current_period_loss']) == Decimal(current)


@pytest.mark.parametrize('small', [False, True])
def test_total_exclusions_cannot_exceed_income(small):
    data, basis = saved_inputs() if small else (facts(),dict(COMPANY))
    basis.update(non_taxable_income='3000000',exempt_income='2000000',taxable_income='0')
    with pytest.raises(ValueError,match='cannot exceed'):
        run(data,basis)


def test_verified_non_cash_statutory_income_can_increase_base_without_fake_expenses():
    data = facts()
    data['incomes'].append(dict(category='other',source_jurisdiction='cn',gross_amount='100000',
        description='Verified statutory non-cash income included in total income'))
    result = run(data,{**COMPANY,'taxable_income':'1100000'})
    assert Decimal(result['annual_liability']) == 275000
