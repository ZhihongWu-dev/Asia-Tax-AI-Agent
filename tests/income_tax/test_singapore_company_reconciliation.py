from decimal import Decimal
import pytest
from pydantic import TypeAdapter
from packages.contracts.income_assessment import Assessment
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.assessment import calculate
from tests.income_tax.test_assessment_workflow import facts, COMMON


def inputs():
    case=facts('sg','company');case['claimed_deductions']='900000'
    basis=dict(policy='sg_company_ya2026',normal_chargeable_income='100000',
        exemption_scheme='partial',startup_eligibility_confirmed=False,cash_grant_eligible=False,
        allowed_tax_setoff='0',ordinary_regime_confirmed=True,**COMMON)
    return case,basis


def run(case,basis):
    return calculate(IncomeTaxCase(**case),TypeAdapter(Assessment).validate_python(basis))


@pytest.mark.parametrize('field,value',[('claimed_deductions','0'),('carried_losses','1')])
def test_saved_case_mismatch_is_rejected(field,value):
    case,basis=inputs();case[field]=value
    with pytest.raises(ValueError,match='must reconcile'):run(case,basis)


@pytest.mark.parametrize('scheme,exemption',[('partial','52500'),('startup','75000'),('none','0')])
def test_automatic_exemption_follows_reconciliation(scheme,exemption):
    case,basis=inputs();case['claimed_deductions']='850000';case['carried_losses']='50000'
    basis.update(exemption_scheme=scheme,startup_eligibility_confirmed=scheme=='startup')
    result=run(case,basis)
    assert Decimal(result['normal_chargeable_income'])==100000
    assert Decimal(result['exempt_amount'])==Decimal(exemption)
    rec=result['singapore_basis_reconciliation']
    assert Decimal(rec['established_prior_loss_deduction'])==50000
    assert Decimal(rec['chargeable_income_before_exemption'])==100000


def test_negative_reconciliation_is_not_classified_as_carryforward_loss():
    case,basis=inputs();case['claimed_deductions']='1100000';basis['normal_chargeable_income']='0'
    result=run(case,basis);rec=result['singapore_basis_reconciliation']
    assert Decimal(rec['net_before_zero_floor'])==-100000
    assert Decimal(result['net_tax'])==0
    assert 'current_period_loss' not in rec and 'prior_losses_unused' not in rec
