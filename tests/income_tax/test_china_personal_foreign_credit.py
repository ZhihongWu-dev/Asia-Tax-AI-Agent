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
