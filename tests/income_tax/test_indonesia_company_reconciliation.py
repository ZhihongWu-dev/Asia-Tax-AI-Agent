from decimal import Decimal
import pytest
from pydantic import TypeAdapter
from packages.contracts.income_tax import IncomeTaxCase
from packages.contracts.income_assessment import Assessment
from packages.income_tax.assessment import calculate


def inputs():
    case=dict(subject='company',jurisdiction='id',currency='IDR',residency='resident',
        period_start='2026-01-01',period_end='2026-12-31',claimed_deductions='5390000000',
        carried_losses='0',facts_confirmed=True,incomes=[dict(category='business',
        source_jurisdiction='id',gross_amount='6000000000',description='Complete ordinary fiscal receipts')])
    basis=dict(policy='id_company_2026',taxable_income_before_rounding='610000000',
        gross_receipts_scope_confirmed=True,ordinary_annual_treatment_confirmed=True,
        prepaid_tax='130000000',basis_confirmed=True,
        basis_explanation='Verified ordinary fiscal income, deductions and eligible prior-loss amounts.')
    return case,basis


def run(case,basis):
    return calculate(IncomeTaxCase(**case),TypeAdapter(Assessment).validate_python(basis))


@pytest.mark.parametrize('field,value',[('claimed_deductions','0'),('carried_losses','1')])
def test_unreconciled_saved_amounts_rejected(field,value):
    case,basis=inputs();case[field]=value
    with pytest.raises(ValueError,match='must reconcile'):run(case,basis)


def test_loss_deduction_does_not_reduce_article31e_receipts():
    case,basis=inputs();case['carried_losses']='10000000';basis['taxable_income_before_rounding']='600000000'
    result=run(case,basis)
    assert Decimal(result['article31e_gross_receipts'])==6000000000
    assert Decimal(result['article31e_eligible_base'])==480000000
    assert Decimal(result['final_tax'])==79200000
    assert Decimal(result['basis_reconciliation']['prior_losses_used'])==10000000


@pytest.mark.parametrize('gross,expenses,losses,base,current,used,unused',[
    ('100','200','50','0','100','0','50'),
    ('100','0','150','0','0','100','50'),
    ('10001999','0','0','10001999','0','0','0'),
])
def test_loss_and_rounding_stages(gross,expenses,losses,base,current,used,unused):
    case,basis=inputs();case['incomes'][0]['gross_amount']=gross
    case.update(claimed_deductions=expenses,carried_losses=losses)
    basis['taxable_income_before_rounding']=base
    result=run(case,basis);rec=result['basis_reconciliation']
    assert Decimal(rec['taxable_income'])==Decimal(base)
    assert Decimal(rec['current_period_loss'])==Decimal(current)
    assert Decimal(rec['prior_losses_used'])==Decimal(used)
    assert Decimal(rec['prior_losses_unused'])==Decimal(unused)
    if base=='10001999':assert Decimal(result['taxable_income'])==10001000
