from copy import deepcopy
from decimal import Decimal, localcontext
from hashlib import sha256
from pathlib import Path
import pytest
from packages.income_tax.china_personal_foreign_credit import calculate


def paper():
    return dict(tax_year=2026,worldwide_comprehensive_tax='10000',worldwide_business_tax='20000',
        resident_source_fx_and_category_bases_verified=True,annual_category_taxes_and_reliefs_verified=True,
        direct_paid_tax_eligibility_and_evidence_verified=True,countries=[
        dict(country=c,comprehensive_income_amount=a,business_taxable_income=b,
             other_category_chinese_tax=t,eligible_foreign_tax_paid=p)
        for c,a,b,t,p in [('cn','50000','10000','0','0'),('sg','30000','60000','2000','17000'),('hk','20000','30000','1000','500')]])


def test_mixed_categories_use_distinct_denominators_and_country_limits():
    r=calculate(paper());sg,hk=r['country_limits']
    assert sg['comprehensive_credit_limit']==3000
    assert sg['business_credit_limit']==12000
    assert sg['credit_limit']==17000 and sg['current_credit_used']==17000
    assert hk['credit_limit']==9000 and hk['current_credit_used']==500
    assert r['current_credit_used']==17500


def test_excess_never_moves_to_other_country_and_retains_five_year_expiry():
    p=paper();p['countries'][1]['eligible_foreign_tax_paid']='20000'
    r=calculate(p);sg,hk=r['country_limits']
    assert sg['current_excess']==3000 and sg['current_excess_last_usable_year']==2031
    assert hk['remaining_credit_capacity']==8500
    assert r['current_credit_used']==17500


def test_other_categories_only_do_not_divide_by_zero():
    p=paper();p.update(worldwide_comprehensive_tax='0',worldwide_business_tax='0')
    for row in p['countries']:row.update(comprehensive_income_amount='0',business_taxable_income='0')
    assert calculate(p)['country_limits'][0]['credit_limit']==2000


@pytest.mark.parametrize('country',['hk','sg','id','vn','my','th','ae','jp','kr','in'])
def test_every_existing_foreign_dividend_jurisdiction(country):
    p=paper();p['countries']=p['countries'][:2];p['countries'][1]['country']=country
    assert calculate(p)['country_limits'][0]['country']==country


@pytest.mark.parametrize('mutation',['duplicate','domestic_paid','no_foreign','zero_comp','zero_business','negative','unknown','unverified','extra'])
def test_inconsistent_workpapers_rejected(mutation):
    p=paper()
    if mutation=='duplicate':p['countries'].append(deepcopy(p['countries'][1]))
    elif mutation=='domestic_paid':p['countries'][0]['eligible_foreign_tax_paid']='1'
    elif mutation=='no_foreign':p['countries']=p['countries'][:1]
    elif mutation=='zero_comp':
        for r in p['countries']:r['comprehensive_income_amount']='0'
    elif mutation=='zero_business':
        for r in p['countries']:r['business_taxable_income']='0'
    elif mutation=='negative':p['countries'][1]['business_taxable_income']='-1'
    elif mutation=='unknown':p['countries'][1]['country']='xx'
    elif mutation=='unverified':p['annual_category_taxes_and_reliefs_verified']=False
    else:p['pooled']=True
    with pytest.raises(ValueError):calculate(p)


def test_decimal_context_and_original_source_are_preserved():
    expected=calculate(paper())
    with localcontext() as ctx:
        ctx.prec=4
        assert calculate(paper())==expected
    for source in expected['sources']:
        assert sha256(Path(source['file']).read_bytes()).hexdigest()==source['sha256']
    expected['sources'][0]['title']='changed'
    assert calculate(paper())['sources'][0]['title']!='changed'


def test_reliefs_reduce_each_category_before_country_allocation():
    p=paper();p.update(comprehensive_tax_reductions='1000',business_tax_reductions='2000')
    p['countries'][1]['other_category_tax_reductions']='500'
    r=calculate(p);sg,hk=r['country_limits']
    assert r['comprehensive_tax_after_reductions']==9000
    assert r['business_tax_after_reductions']==18000
    assert sg['comprehensive_credit_limit']==2700
    assert sg['business_credit_limit']==10800
    assert sg['other_category_credit_limit']==1500
    assert sg['credit_limit']==15000 and sg['current_excess']==2000
    assert hk['credit_limit']==8200
    assert r['current_credit_used']==15500


@pytest.mark.parametrize('category',['comprehensive','business','other'])
def test_reductions_cannot_exceed_tax_in_their_own_category(category):
    p=paper()
    if category=='other':p['countries'][1]['other_category_tax_reductions']='2001'
    elif category=='comprehensive':p['comprehensive_tax_reductions']='10001'
    else:p['business_tax_reductions']='20001'
    with pytest.raises(ValueError,match='reductions'):calculate(p)


def test_full_relief_leaves_no_foreign_credit_capacity():
    p=paper();p.update(comprehensive_tax_reductions='10000',business_tax_reductions='20000')
    for row in p['countries']:row['other_category_tax_reductions']=row['other_category_chinese_tax']
    r=calculate(p)
    assert r['current_credit_used']==0
    assert r['country_limits'][0]['current_excess']==17000


def test_current_tax_first_then_oldest_valid_credit_without_cross_country_use():
    p=paper();p['carryforward_history_verified']=True
    p['countries'][2]['prior_excess']=[dict(origin_year=2025,amount='10000'),dict(origin_year=2020,amount='600'),dict(origin_year=2021,amount='9000')]
    r=calculate(p);hk=r['country_limits'][1]
    assert hk['current_credit_used']==500 and hk['prior_credit_used']==8500
    assert hk['allowed_credit']==9000 and hk['remaining_credit_capacity']==0
    expired,last,new=hk['carryforward_history']
    assert expired['expired_amount']==600 and expired['credit_used']==0
    assert last['credit_used']==8500 and last['expires_after_current_year']==500
    assert last['next_year_carryforward']==0
    assert new['credit_used']==0 and new['next_year_carryforward']==10000
    assert r['allowed_credit']==26000


@pytest.mark.parametrize('issue',['duplicate','current','future','unverified','domestic'])
def test_invalid_credit_history_rejected(issue):
    p=paper();p['carryforward_history_verified']=True
    p['countries'][1]['prior_excess']=[dict(origin_year=2021,amount='1')]
    if issue=='duplicate':p['countries'][1]['prior_excess']*=2
    elif issue=='current':p['countries'][1]['prior_excess'][0]['origin_year']=2026
    elif issue=='future':p['countries'][1]['prior_excess'][0]['origin_year']=2027
    elif issue=='unverified':p['carryforward_history_verified']=False
    else:p['countries'][0]['prior_excess']=p['countries'][1]['prior_excess']
    with pytest.raises(ValueError):calculate(p)


def test_country_with_no_current_income_keeps_unexpired_credit_without_using_it():
    p=paper();p['carryforward_history_verified']=True
    p['countries'].append(dict(country='kr',comprehensive_income_amount='0',business_taxable_income='0',other_category_chinese_tax='0',eligible_foreign_tax_paid='0',prior_excess=[dict(origin_year=2025,amount='300')]))
    kr=calculate(p)['country_limits'][-1]
    assert kr['allowed_credit']==0
    assert kr['carryforward_history'][0]['next_year_carryforward']==300

@pytest.mark.parametrize('parts,tax',[([8816,4787,4713,7495],'23.09'),([1,1,1],'1')])
def test_exact_country_allocation_does_not_create_residual_tax_or_refund(parts,tax):
    p=paper();p.update(worldwide_comprehensive_tax=tax,worldwide_business_tax='0')
    p['countries']=[dict(country=c,comprehensive_income_amount=str(v),business_taxable_income='0',other_category_chinese_tax='0',eligible_foreign_tax_paid='100') for c,v in zip(['sg','hk','jp','kr'],parts)]
    result=calculate(p)
    assert result['allowed_credit']==Decimal(tax)
    assert result['current_credit_used']==Decimal(tax)
    p['countries'].reverse()
    assert calculate(p)['allowed_credit']==Decimal(tax)
