from datetime import date, datetime
from decimal import Decimal, localcontext
import pytest
from packages.income_tax.vietnam_transfer import personal_transfer_tax


def assess(**changes):
    values=dict(transfer_value='1000000000', recognition_date=date(2026,7,1), resident=True,
        asset_kind='capital_interest',purchase_cost='600000000',transfer_costs='10000000',
        cost_basis_established=True,ordinary_sale_confirmed=True,
        classification_valuation_and_scope_verified=True,prepaid_tax='0')
    values.update(changes)
    return personal_transfer_tax(**values)


@pytest.mark.parametrize('resident',[True,False])
def test_gain_cost_and_residence(resident):
    result=assess(resident=resident)
    assert result['taxable_base']==Decimal('390000000')
    assert result['final_tax']==Decimal('78000000')
    assert result['legal_basis'][0].endswith('#13' if resident else '#23')


def test_unknown_cost_is_not_optional_minimum():
    known=assess(); unknown=assess(cost_basis_established=False,purchase_cost=None,transfer_costs=None)
    assert known['final_tax']==Decimal('78000000')
    assert unknown['final_tax']==Decimal('20000000')


def test_securities_tax_gross_even_when_cost_would_exceed_price():
    result=assess(asset_kind='security',cost_basis_established=False,purchase_cost=None,transfer_costs=None)
    assert result['final_tax']==Decimal('1000000')
    with pytest.raises(ValueError):assess(asset_kind='security',purchase_cost='2000000000')


def test_capital_loss_and_prepayment():
    r=assess(purchase_cost='1100000000',prepaid_tax='10000')
    assert r['final_tax']==0 and r['balance_due']==-10000


@pytest.mark.parametrize('change',[
    dict(recognition_date=date(2026,6,30)),dict(recognition_date=date(2027,1,1)),
    dict(recognition_date=datetime(2026,7,1)),dict(resident=1),
    dict(cost_basis_established=0),dict(cost_basis_established=False),
    dict(purchase_cost=None),dict(ordinary_sale_confirmed=False),
    dict(classification_valuation_and_scope_verified=False),dict(asset_kind='real_estate'),
    dict(asset_kind='contribution'),dict(transfer_value=1.2),dict(transfer_value='NaN'),
    dict(transfer_costs='-1'),dict(prepaid_tax=True),dict(transfer_value='0.0000001')])
def test_invalid_or_unestablished_facts_rejected(change):
    with pytest.raises(ValueError):assess(**change)


def test_precision_independent_of_callers_context_and_sources_isolated():
    with localcontext() as ctx:
        ctx.prec=3
        r=assess(transfer_value='1000000000000000000',purchase_cost='0.000001',transfer_costs='0')
    assert r['final_tax']==Decimal('199999999999999999.9999998')
    r['sources'][0]['sha256']='changed'
    assert assess()['sources'][0]['sha256']!='changed'
