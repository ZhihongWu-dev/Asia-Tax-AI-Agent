from decimal import Decimal
import pytest
from tests.income_tax.test_vietnam_workflow import company_facts,company_basis,run


@pytest.mark.parametrize('field,value',[('claimed_deductions','0'),('carried_losses','1')])
def test_saved_fact_change_invalidates_the_old_manual_base(field,value):
    case=company_facts();case[field]=value
    with pytest.raises(ValueError,match='must reconcile'):run(case,company_basis())


def test_exempt_income_and_prior_loss_do_not_reduce_annual_revenue_threshold():
    case=company_facts();case['carried_losses']='200000000'
    basis=company_basis();basis.update(exempt_income='100000000',taxable_income='700000000',other_incentive_reduction='0')
    result=run(case,basis);rec=result['basis_reconciliation']
    assert Decimal(rec['income_before_loss_relief'])==900000000
    assert Decimal(rec['prior_losses_used'])==200000000
    assert Decimal(result['final_tax'])==83300000
    assert Decimal(result['annual_reduction'])==35700000
    case['incomes'][0]['gross_amount']='10000000001'
    case['claimed_deductions']='9000000001'
    assert Decimal(run(case,basis)['annual_reduction'])==0


def test_current_loss_does_not_include_unused_prior_losses():
    case=company_facts();case.update(claimed_deductions='11000000000',carried_losses='300000000')
    basis=company_basis();basis.update(taxable_income='0',other_incentive_reduction='0')
    rec=run(case,basis)['basis_reconciliation']
    assert Decimal(rec['current_period_loss'])==1000000000
    assert Decimal(rec['prior_losses_used'])==0
    assert Decimal(rec['prior_losses_unused'])==300000000


def test_exemption_cannot_exceed_saved_income():
    basis=company_basis();basis['exempt_income']='10000000001'
    with pytest.raises(ValueError,match='Exempt income exceeds'):run(company_facts(),basis)
