from copy import deepcopy
from decimal import Decimal, localcontext
import hashlib
from pathlib import Path
import pytest
from packages.income_tax.china_foreign_credit import calculate


def paper():
    return dict(tax_year=2026,method='per_country',domestic_taxable_income='1000',
        countries=[dict(country='sg',taxable_income='1000',eligible_current_tax='400'),
                   dict(country='hk',taxable_income='1000',eligible_current_tax='100')],
        ordinary_25_percent_positive_bases_verified=True,
        income_tax_eligibility_and_fx_verified=True,
        method_lock_and_carryforward_history_verified=True)


def test_pooling_does_not_share_country_limits_without_election():
    p=paper();separate=calculate(p)
    assert separate['allowed_foreign_tax_credit']==350
    assert separate['ordinary_tax_after_foreign_credit']==400
    p['method']='pooled';pooled=calculate(p)
    assert pooled['allowed_foreign_tax_credit']==500
    assert pooled['ordinary_tax_after_foreign_credit']==250
    assert pooled['pools'][0]['current_excess']==0


def test_current_credit_first_and_last_year_expiry():
    p=paper();p['countries']=p['countries'][:1];row=p['countries'][0]
    row['eligible_current_tax']='200'
    row['prior_excess']=[dict(origin_year=2025,amount='40'),dict(origin_year=2020,amount='60'),dict(origin_year=2021,amount='80')]
    result=calculate(p)['pools'][0]
    assert result['current_credit_used']==200 and result['prior_credit_used']==50
    old=result['carryforward_history']
    assert old[0]['expired_amount']==60 and old[0]['credit_used']==0
    assert old[1]['last_usable_year']==2026 and old[1]['credit_used']==50 and old[1]['closing_excess']==30
    assert old[1]['expires_after_current_year']==30 and old[1]['next_year_carryforward']==0
    assert old[2]['credit_used']==0 and old[2]['closing_excess']==40
    assert old[2]['next_year_carryforward']==40


def test_current_excess_does_not_displace_current_credit_with_old_credit():
    p=paper();p['countries'][0]['prior_excess']=[dict(origin_year=2021,amount='80')]
    row=calculate(p)['pools'][0]
    assert row['current_excess']==150 and row['current_excess_last_usable_year']==2031
    assert row['prior_credit_used']==0 and row['carryforward_history'][0]['closing_excess']==80


def test_pooled_old_credit_retains_country_and_original_expiry():
    p=paper();p['method']='pooled';p['countries'][0]['eligible_current_tax']='100'
    p['countries'][0]['prior_excess']=[dict(origin_year=2021,amount='400')]
    row=calculate(p)['pools'][0]
    assert row['prior_credit_used']==300
    assert row['carryforward_history'][0]['country']=='sg'
    assert row['carryforward_history'][0]['closing_excess']==100
    assert row['carryforward_history'][0]['last_usable_year']==2026


@pytest.mark.parametrize('flag',['ordinary_25_percent_positive_bases_verified','income_tax_eligibility_and_fx_verified','method_lock_and_carryforward_history_verified'])
def test_unverified_workpaper_rejected(flag):
    p=paper();p[flag]=False
    with pytest.raises(ValueError):calculate(p)


@pytest.mark.parametrize('change',['domestic_country','duplicate_country','negative_base','current_origin','duplicate_origin','invalid_method'])
def test_unsupported_or_ambiguous_input_rejected(change):
    p=paper();row=p['countries'][0]
    if change=='domestic_country':row['country']='cn'
    elif change=='duplicate_country':p['countries'][1]['country']='sg'
    elif change=='negative_base':row['taxable_income']='-1'
    elif change=='current_origin':row['prior_excess']=[dict(origin_year=2026,amount='1')]
    elif change=='duplicate_origin':row['prior_excess']=[dict(origin_year=2025,amount='1')]*2
    else:p['method']='automatic_best'
    with pytest.raises(ValueError):calculate(p)


def test_exact_decimal_and_sources_immutable():
    p=paper();p['countries'][0]['taxable_income']='1000.000001';original=deepcopy(p)
    with localcontext() as ctx:
        ctx.prec=6
        r=calculate(p)
    assert r['pools'][0]['credit_limit']==Decimal('250.00000025')
    assert p==original
    root=Path(__file__).resolve().parents[2]
    for source in r['sources']:
        assert hashlib.sha256((root/source['file']).read_bytes()).hexdigest()==source['sha256']
    r['sources'][0]['doc_id']='changed'
    assert calculate(p)['sources'][0]['doc_id']=='cn.cs.2009-125'


@pytest.mark.parametrize('country',['hk','sg','id','vn','my','th','ae','jp','kr','in'])
def test_every_other_dividend_jurisdiction_can_be_a_credit_pool(country):
    p=paper();p['countries']=[dict(country=country,taxable_income='100',eligible_current_tax='10')]
    row=calculate(p)['pools'][0]
    assert row['pool']==country and row['allowed_credit']==10 and row['credit_limit']==25
