from decimal import Decimal, localcontext
from pathlib import Path
from hashlib import sha256
import pytest
from packages.income_tax.japan_osaka import ordinary_enterprise
from packages.income_tax.japan_osaka import annual_capitation


def capitation(**changes):
    data=dict(fiscal_start_year=2026,registered_capital='10000000',capital_reserve='0',adjusted_statutory_capital='10000000',
        wards=[dict(ward_name='北区',employees=50),dict(ward_name='中央区',employees=51)],full_year_osaka_city_scope_verified=True)
    data.update(changes)
    return annual_capitation(**data)


def test_prefecture_charged_once_and_city_per_ward():
    r=capitation()
    assert r['prefectural_capitation']==20000
    assert [w['annual_city_capitation'] for w in r['wards']]==[50000,120000]
    assert r['total_capitation']==190000
    for s in r['sources']:assert sha256(Path(s['file']).read_bytes()).hexdigest()==s['sha256']


@pytest.mark.parametrize('capital,prefecture,city', [('10000001',75000,280000),('100000000',75000,280000),('100000001',260000,560000),('1000000000',260000,560000),('1000000001',1080000,2160000),('5000000000',1080000,2160000),('5000000001',1600000,3410000)])
def test_capital_bands(capital,prefecture,city):
    r=capitation(adjusted_statutory_capital=capital)
    assert r['prefectural_capitation']==prefecture and r['city_capitation']==city


def test_capital_reserve_floor_and_context():
    r=capitation(capital_reserve='1',adjusted_statutory_capital='0')
    assert r['capital_for_rate_band']==10000001 and r['total_capitation']==355000
    with localcontext() as ctx:
        ctx.prec=3
        assert capitation(capital_reserve='1',adjusted_statutory_capital='0')==r


@pytest.mark.parametrize('changes', [{'wards':[]},{'wards':[dict(ward_name='北区',employees=1)]*2},{'wards':[dict(ward_name='北区',employees=True)]},{'full_year_osaka_city_scope_verified':False},{'fiscal_start_year':2027}])
def test_capitation_scope_rejected(changes):
    with pytest.raises(ValueError):capitation(**changes)


def run(income='10000000', **changes):
    args=dict(fiscal_start_year=2026,months=12,registered_capital='10000000',ordinary_single_prefecture_scope_verified=True)
    args.update(changes)
    return ordinary_enterprise(income,**args)


def test_standard_ordinary_components():
    r=run()
    assert r['enterprise_tax_before_credits']==492000
    assert r['special_enterprise_tax_before_credits']==182000
    assert not r['surcharge_applies']
    assert all('osaka' in s['doc_id'] for s in r['sources'])
    for s in r['sources']:assert sha256(Path(s['file']).read_bytes()).hexdigest()==s['sha256']


@pytest.mark.parametrize('income,applies',[('25001000',False),('50000000',False),('50000999',False),('50001000',True)])
def test_osaka_threshold_uses_thousand_yen_truncation(income,applies):
    r=run(income)
    assert r['surcharge_applies'] is applies
    assert r['bands'][0]['rate']==Decimal('.0375' if applies else '.035')


def test_short_period_bands_before_rounding():
    r=run('2856420',months=4)
    assert [b['taxable_base'] for b in r['bands']]==[1333000,1333000,189000]
    assert r['enterprise_tax_before_credits']==130400
    assert r['special_enterprise_tax_before_credits']==48200
    with localcontext() as ctx:
        ctx.prec=4
        assert run('2856420',months=4)==r


@pytest.mark.parametrize('changes',[{'months':True},{'months':13},{'fiscal_start_year':2027},{'registered_capital':'100000001'},{'ordinary_single_prefecture_scope_verified':False}])
def test_unreviewed_scope_rejected(changes):
    with pytest.raises(ValueError):run(**changes)
