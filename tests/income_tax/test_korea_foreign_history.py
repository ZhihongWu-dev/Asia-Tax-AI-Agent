import pytest
from packages.income_tax.korea_foreign_credit import calculate
from packages.income_tax.korea_foreign_history import allocate_history
from tests.income_tax.test_korea_foreign_credit import fixture


def run(lots):
    current=calculate(fixture(),national_tax_before_credit='200',national_taxable_base='1000')
    return allocate_history(current,lots,period_start='2026-01-01',period_end='2026-12-31',
        history_entitlement_expiry_and_order_verified=True)


def lot(identifier='old',country='cn',expiry='2026-12-31',amount='30'):
    return dict(identifier=identifier,country=country,origin_period_end='2020-12-31',
        verified_expiry_date=expiry,available_amount=amount)


def test_history_precedes_current_and_preserves_expense_excess():
    result=run([lot()]);row=result['current_country_usage'][0]
    assert result['historical_credit_used']==30
    assert row['current_credit_used']==50
    assert row['current_ordinary_carryforward']==80
    assert row['expense_related_excess_not_carried']==20
    assert result['total_credit_used']==80


def test_other_country_history_cannot_use_current_country_capacity():
    result=run([lot(country='sg')])
    assert result['historical_credit_used']==0
    assert result['historical_lots'][0]['remaining']==30
    assert result['current_credit_used']==80


@pytest.mark.parametrize('expiry,used,review',[('2026-12-31',30,False),('2026-12-30',0,True),('2025-12-31',0,True),('2025-12-30',0,False)])
def test_year_end_expiry_and_deduction_review_window(expiry,used,review):
    result=run([lot(expiry=expiry)])
    assert result['historical_credit_used']==used
    assert result['historical_lots'][0]['expires_at_current_period_end']==(expiry=='2026-12-31')
    assert result['historical_lots'][0]['expired_deduction_review_in_current_period']==review


def test_verified_lot_order_and_remaining_history():
    result=run([lot('a',amount='60'),lot('b',amount='40')])
    assert [r['used'] for r in result['historical_lots']]==[60,20]
    assert result['historical_lots'][1]['remaining']==20
    assert result['current_country_usage'][0]['current_ordinary_carryforward']==130


@pytest.mark.parametrize('change',['duplicate','domestic','current_origin','bad_expiry'])
def test_invalid_history_rejected(change):
    item=lot();items=[item]
    if change=='duplicate':items.append(dict(item))
    elif change=='domestic':item['country']='kr'
    elif change=='current_origin':item['origin_period_end']='2026-01-01'
    else:item['verified_expiry_date']='2020-12-31'
    with pytest.raises(ValueError):run(items)
