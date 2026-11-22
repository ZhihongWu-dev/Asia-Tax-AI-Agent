import pytest
from packages.income_tax.indonesia_foreign_credit import calculate


def paper():
    return dict(taxable_income='8000000000',foreign_incomes=[
        dict(country='jp',category='business',net_taxable_income='1000000000',foreign_tax='300000000',treaty_applies=False),
        dict(country='sg',category='interest',net_taxable_income='3000000000',foreign_tax='450000000',treaty_applies=False)],
        prior_credit_reduction_or_refund='0',taxable_scope_source_period_and_fx_verified=True,
        treaty_entitlement_and_tax_evidence_verified=True,recapture_of_previously_credited_tax_verified=True)


def test_historical_appendix_b1_allocation_only():
    # Country codes are placeholders for the official example's X/Y, not treaty conclusions.
    r=calculate(paper(),indonesian_tax_before_credit='2000000000')
    assert r['allowed_foreign_tax_credit']==700000000
    assert [s['credit_before_overall_cap'] for s in r['source_credits']]==[250000000,450000000]
    assert r['unrelieved_foreign_tax']==50000000


def test_appendix_b2_treaty_cap():
    p=paper();p['foreign_incomes'][1].update(treaty_applies=True,treaty_permitted_tax='300000000')
    assert calculate(p,indonesian_tax_before_credit='2000000000')['allowed_foreign_tax_credit']==550000000


def test_appendix_b3_domestic_loss_caps_credit_at_total_tax():
    p=paper();p['taxable_income']='800000000';p['foreign_incomes']=p['foreign_incomes'][:1]
    r=calculate(p,indonesian_tax_before_credit='200000000')
    assert r['source_credits'][0]['indonesian_tax_limit']==200000000
    assert r['allowed_foreign_tax_credit']==200000000


def test_treaty_exclusive_residence_taxation_produces_zero_credit():
    p=paper();p['foreign_incomes'][0].update(treaty_applies=True,treaty_permitted_tax='0')
    assert calculate(p,indonesian_tax_before_credit='2000000000')['allowed_foreign_tax_credit']==450000000


def test_overall_cap_and_recapture_are_separate():
    p=paper();p['taxable_income']='100000000';p['prior_credit_reduction_or_refund']='5000000'
    r=calculate(p,indonesian_tax_before_credit='25000000')
    assert r['allowed_foreign_tax_credit']==25000000
    assert r['overall_cap_reduction']==25000000
    assert r['liability_after_recapture']==5000000


@pytest.mark.parametrize('change',['duplicate','domestic','negative_net','missing_treaty_cap','unexpected_treaty_cap','unverified','zero_base'])
def test_invalid_inputs(change):
    p=paper();s=p['foreign_incomes'][0]
    if change=='duplicate':p['foreign_incomes'].append(dict(s))
    if change=='domestic':s['country']='id'
    if change=='negative_net':s['net_taxable_income']='-1'
    if change=='missing_treaty_cap':s['treaty_applies']=True
    if change=='unexpected_treaty_cap':s['treaty_permitted_tax']='1'
    if change=='unverified':p['recapture_of_previously_credited_tax_verified']=False
    if change=='zero_base':p['taxable_income']='0'
    with pytest.raises(ValueError):calculate(p,indonesian_tax_before_credit='2000000000')
