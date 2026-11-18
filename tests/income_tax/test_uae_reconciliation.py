from decimal import Decimal
import pytest
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.uae_reconciliation import reconcile
from tests.income_tax.test_assessment_workflow import facts


@pytest.mark.parametrize('losses,used,unused,net',[
    ('0','0','0','2000000'),('500000','500000','0','1500000'),
    ('1500000','1500000','0','500000'),('2000000','1500000','500000','500000')])
def test_prior_loss_limit_is_applied_before_the_zero_rate_band(losses,used,unused,net):
    data=facts('ae');data['incomes'][0]['gross_amount']='3000000'
    data.update(claimed_deductions='1000000',carried_losses=losses)
    result=reconcile(IncomeTaxCase(**data),taxable_income=net)
    for key,value in dict(prior_loss_limit='1500000',prior_losses_used=used,
        prior_losses_unused=unused,taxable_income=net).items():
        assert result[key]==Decimal(value)


def test_personal_wages_do_not_increase_business_loss_capacity():
    data=facts('ae','individual');data['incomes'][0].update(category='business',gross_amount='3000000')
    data['incomes'].append(dict(category='employment',gross_amount='1000000',source_jurisdiction='ae',description='Excluded wages'))
    data.update(claimed_deductions='1000000',carried_losses='2000000')
    result=reconcile(IncomeTaxCase(**data),taxable_income='500000')
    assert result['excluded_personal_income']==1000000
    assert result['prior_loss_limit']==1500000


def test_current_loss_does_not_consume_prior_losses():
    data=facts('ae');data.update(claimed_deductions='1100000',carried_losses='500000')
    result=reconcile(IncomeTaxCase(**data),taxable_income='0')
    assert result['current_period_loss']==100000
    assert result['prior_losses_used']==0
    assert result['prior_losses_unused']==500000


def test_full_offset_above_limit_is_rejected():
    data=facts('ae');data['carried_losses']='1000000'
    with pytest.raises(ValueError,match='75% prior-loss limit'):
        reconcile(IncomeTaxCase(**data),taxable_income='0')


def test_adjustments_and_exemptions_reconcile_separately():
    data=facts('ae');data['claimed_deductions']='200000'
    result=reconcile(IncomeTaxCase(**data),taxable_income='750000',additions='50000',exempt_income='100000')
    assert result['income_before_loss_relief']==750000


def test_unclassified_service_income_is_not_silently_excluded():
    data=facts('ae','individual');data['incomes'][0]['category']='service_remuneration'
    with pytest.raises(ValueError,match='Classify all'):
        reconcile(IncomeTaxCase(**data),taxable_income='0')


def inputs():
    from tests.income_tax.test_assessment_workflow import COMMON
    case=facts('ae');case['incomes'][0]['gross_amount']='3000000'
    case.update(claimed_deductions='1000000',carried_losses='2000000')
    basis=dict(policy='ae_ordinary_2026',taxable_income='500000',
        ordinary_regime_confirmed=True,no_relief_elected_confirmed=True,
        allowed_foreign_tax_credit='0',prepaid_tax='0',**COMMON)
    return case,basis


def test_adapter_caps_losses_before_applying_375000_zero_rate_band():
    from tests.income_tax.test_assessment_workflow import ADAPTER
    from packages.income_tax.assessment import calculate
    case,basis=inputs()
    result=calculate(IncomeTaxCase(**case),ADAPTER.validate_python(basis))
    assert Decimal(result['final_tax'])==11250
    assert Decimal(result['uae_basis_reconciliation']['prior_loss_limit'])==1500000
    with pytest.raises(ValueError,match='must reconcile'):
        calculate(IncomeTaxCase(**case),ADAPTER.validate_python({**basis,'taxable_income':'0'}))
