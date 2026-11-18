from decimal import Decimal, localcontext
from pathlib import Path
from hashlib import sha256
import pytest
from packages.income_tax.japan_osaka import ordinary_enterprise


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
