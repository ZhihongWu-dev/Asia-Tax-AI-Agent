from decimal import Decimal
import pytest
from packages.income_tax.uae_foreign_credit import calculate


def paper(domestic,items):
    return dict(domestic_taxable_income=str(domestic),foreign_incomes=[dict(source_id=str(i),country='sg',net_taxable_income=str(net),eligible_foreign_tax=str(tax)) for i,(net,tax) in enumerate(items)],ordinary_positive_taxable_income_verified=True,foreign_tax_eligibility_treaty_and_fx_verified=True,distinct_sources_and_linked_expenses_verified=True)


@pytest.mark.parametrize('domestic,items,liability,excess',[
    (9000000,[(1000000,50000)],816250,0),
    (0,[(800000,100000)],0,61750),
    (0,[(100000,1000),(500000,50000)],2375,33125),
])
def test_fta_examples_10_11_12(domestic,items,liability,excess):
    result=calculate(paper(domestic,items))
    assert result['tax_after_credit']==liability
    assert result['forfeited_excess']==excess


@pytest.mark.parametrize('income',[0,1,375000])
def test_zero_rate_income_has_no_credit_capacity(income):
    result=calculate(paper(0,[(income,100)]))
    assert result['allowed_foreign_tax_credit']==0
    assert result['forfeited_excess']==100


def test_same_country_different_sources_cannot_share_excess():
    result=calculate(paper(0,[(100000,1000),(500000,50000)]))
    assert result['source_credits'][0]['credit_limit']==3375
    assert result['source_credits'][1]['credit_limit']==16875
    assert result['allowed_foreign_tax_credit']==17875


@pytest.mark.parametrize('change',['duplicate','domestic','negative','unverified'])
def test_invalid_workpaper(change):
    p=paper(0,[(100000,1000),(500000,50000)])
    if change=='duplicate': p['foreign_incomes'][1]['source_id']='0'
    if change=='domestic': p['foreign_incomes'][0]['country']='ae'
    if change=='negative': p['foreign_incomes'][0]['net_taxable_income']='-1'
    if change=='unverified': p['distinct_sources_and_linked_expenses_verified']=False
    with pytest.raises(ValueError): calculate(p)


def test_fractional_inputs_retain_internal_precision():
    result=calculate(paper('9000000.000001',[(1000000,50000)]))
    assert result['gross_tax']==Decimal('866250.00000009')
    assert result['tax_after_credit']==Decimal('816250.00000009')
