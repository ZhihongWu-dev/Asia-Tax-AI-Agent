from decimal import Decimal
import pytest
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.hong_kong_reconciliation import reconcile
from tests.income_tax.test_assessment_workflow import facts


@pytest.mark.parametrize('subject', ['company', 'individual'])
def test_current_assessable_profits_are_not_reduced_by_prior_losses(subject):
    data=facts('hk',subject)
    data['incomes'][0]['category']='business'
    data.update(claimed_deductions='200000',carried_losses='300000')
    result=reconcile(IncomeTaxCase(**data),additions='50000',excluded_income='100000')
    assert result['assessable_profits_before_losses']==Decimal('750000')
    assert result['prior_losses_used']==Decimal('300000')
    assert result['net_taxable_profits']==Decimal('450000')
    assert result['adjusted_current_loss']==0


@pytest.mark.parametrize('deductions,losses,profits,current_loss,used,unused,net', [
    ('200000','1000000','800000','0','800000','200000','0'),
    ('1200000','300000','0','200000','0','300000','0'),
    ('1000000','0','0','0','0','0','0'),
    ('0','0','1000000','0','0','0','1000000'),
])
def test_loss_setoff_is_bounded_and_current_losses_stay_separate(deductions,losses,profits,current_loss,used,unused,net):
    data=facts('hk');data.update(claimed_deductions=deductions,carried_losses=losses)
    result=reconcile(IncomeTaxCase(**data))
    for key,value in dict(assessable_profits_before_losses=profits,adjusted_current_loss=current_loss,
        prior_losses_used=used,prior_losses_unused=unused,net_taxable_profits=net).items():
        assert result[key]==Decimal(value)


def test_exclusions_cannot_exceed_receipts_plus_additions():
    with pytest.raises(ValueError,match='Excluded income exceeds'):
        reconcile(IncomeTaxCase(**facts('hk')),additions='1',excluded_income='1000002')


@pytest.mark.parametrize('field',['claimed_deductions','carried_losses'])
def test_unknown_deduction_or_loss_is_not_zero(field):
    data=facts('hk');data[field]=None
    with pytest.raises(ValueError,match='known deductions and losses'):
        reconcile(IncomeTaxCase(**data))


def inputs(subject='company'):
    from tests.income_tax.test_assessment_workflow import COMMON
    case=facts('hk',subject);case['incomes'][0]['category']='business'
    case.update(claimed_deductions='200000',carried_losses='300000')
    basis=dict(policy='hk_profits_2025_26',assessable_profits='450000',
        taxable_additions='50000',excluded_income='100000',
        business_form='corporation' if subject=='company' else 'sole_proprietor',
        two_tier_eligible=True,ordinary_regime_confirmed=True,prepaid_final_tax='0',**COMMON)
    return case,basis


@pytest.mark.parametrize('subject,tax',[('company','34125'),('individual','30750')])
def test_saved_case_adapter_taxes_only_the_reconciled_net(subject,tax):
    from tests.income_tax.test_assessment_workflow import ADAPTER
    from packages.income_tax.assessment import calculate
    case,basis=inputs(subject)
    result=calculate(IncomeTaxCase(**case),ADAPTER.validate_python(basis))
    assert Decimal(result['final_tax'])==Decimal(tax)
    rec=result['hong_kong_profits_reconciliation']
    assert Decimal(rec['assessable_profits_before_losses'])==750000
    assert Decimal(rec['net_taxable_profits'])==450000
    assert len(result['sources'])==4


@pytest.mark.parametrize('field',['claimed_deductions','carried_losses'])
def test_saved_fact_changes_cannot_reuse_an_inconsistent_tax_base(field):
    from tests.income_tax.test_assessment_workflow import ADAPTER
    from packages.income_tax.assessment import calculate
    case,basis=inputs();case[field]='0'
    with pytest.raises(ValueError,match='must reconcile'):
        calculate(IncomeTaxCase(**case),ADAPTER.validate_python(basis))
