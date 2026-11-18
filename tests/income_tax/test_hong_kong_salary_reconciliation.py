from decimal import Decimal
import pytest
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.hong_kong_salary_reconciliation import SalaryWorkpaper,reconcile
from packages.income_tax.assessment import calculate
from tests.income_tax.test_assessment_workflow import facts,COMMON,ADAPTER


def paper(**changes):
    data=dict(balancing_charge='0',employment_expenses='0',machinery_allowances='0',self_education='0',concessionary_deductions='0',eligibility_and_salary_loss_verified=True)
    data.update(changes);return data


def inputs():
    case=facts('hk','individual');case['incomes'][0]['gross_amount']='400000';case['claimed_deductions']='20000'
    basis=dict(policy='hk_salaries_2025_26',net_income='380000',allowed_allowances='132000',prepaid_final_tax='10000',ordinary_separate_assessment_confirmed=True,workpaper=paper(concessionary_deductions='20000'),**COMMON)
    return case,basis


def test_allowances_do_not_reduce_the_standard_rate_comparison_base_twice():
    case,basis=inputs();result=calculate(IncomeTaxCase(**case),ADAPTER.validate_python(basis))
    assert Decimal(result['net_income_before_allowances'])==380000
    assert Decimal(result['net_chargeable_income'])==248000
    assert Decimal(result['balance_due'])==11160


@pytest.mark.parametrize('field',['self_education','concessionary_deductions','employment_expenses','machinery_allowances'])
def test_only_section12ab_expenses_create_current_excess(field):
    case=facts('hk','individual');case['incomes'][0]['gross_amount']='10000';case['claimed_deductions']='20000'
    result=reconcile(IncomeTaxCase(**case),SalaryWorkpaper(**paper(**{field:'20000'})))
    assert result['net_income_before_allowances']==0
    assert result['current_section12a_excess']==(10000 if field in ('employment_expenses','machinery_allowances') else 0)


def test_prior_salary_loss_and_balancing_charge_are_separate():
    case=facts('hk','individual');case['incomes'][0]['gross_amount']='10000';case.update(claimed_deductions='5000',carried_losses='30000')
    result=reconcile(IncomeTaxCase(**case),SalaryWorkpaper(**paper(balancing_charge='2000',employment_expenses='5000')))
    assert result['prior_salary_losses_used']==7000
    assert result['prior_salary_losses_unused']==23000
    assert result['current_section12a_excess']==0


@pytest.mark.parametrize('change',['missing','base','summary','unverified'])
def test_missing_or_inconsistent_workpaper_rejected(change):
    case,basis=inputs()
    if change=='missing':basis.pop('workpaper')
    if change=='base':basis['net_income']='400000'
    if change=='summary':case['claimed_deductions']='0'
    if change=='unverified':basis['workpaper']['eligibility_and_salary_loss_verified']=False
    with pytest.raises(ValueError):calculate(IncomeTaxCase(**case),ADAPTER.validate_python(basis))
