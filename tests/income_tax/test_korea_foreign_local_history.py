import pytest
from packages.income_tax.korea_foreign_local_history import reconcile_history


def lot(identifier='old',year='2020',kind='direct',original='100',prior='30',expiry='2035-12-31'):
    return dict(identifier=identifier,kind=kind,origin_period_end=year+'-12-31',
        verified_expiry_date=expiry,original_amount=original,previously_deducted=prior)


def run(lots,base='100',addback='0',direct='50',fund='0'):
    return reconcile_history(dict(lots=lots,original_local_entitlement_expiry_and_prior_usage_verified=True,
        local_eligibility_addback_and_no_duplicate_amounts_verified=True),period_start='2026-01-01',period_end='2026-12-31',
        national_taxable_base=base,expired_foreign_tax_deducted_nationally=addback,
        article57_foreign_tax=direct,article57_2_eligible_fund_credit=fund)


def test_oldest_origin_first_even_when_workpaper_is_not_sorted():
    r=run([lot('new','2024',original='60',prior='0'),lot()])
    rows=r['historical_local_deductions']
    assert [x['identifier'] for x in rows]==['old','new']
    assert [x['current_deduction'] for x in rows]==[70,30]
    assert r['current_local_foreign_tax_deduction']==0
    assert r['historical_next_carryforward']==30
    assert r['total_next_carryforward']==80
    assert r['local_taxable_base']==0


def test_prior_usage_reconciles_and_current_amount_uses_remaining_capacity():
    r=run([lot()])
    assert r['historical_local_deduction_used']==70
    assert r['current_local_foreign_tax_deduction']==30
    assert r['excess_current_local_deduction']==20
    assert r['total_local_deduction']==100


def test_fund_history_does_not_consume_direct_only_addback_capacity():
    r=run([lot(kind='fund',original='130',prior='0')],addback='50',direct='70')
    assert r['historical_local_deduction_used']==100
    assert r['current_direct_local_deduction']==50
    assert r['historical_next_carryforward']==30
    assert r['excess_current_local_deduction']==20


@pytest.mark.parametrize('expiry,used,next_carry,excluded',[
    ('2025-12-31',0,0,70),('2026-12-31',40,0,30),('2027-12-31',40,30,0)])
def test_expiry_excludes_unused_amounts_from_next_period(expiry,used,next_carry,excluded):
    r=run([lot(expiry=expiry)],base='40',direct='0')
    row=r['historical_local_deductions'][0]
    assert row['current_deduction']==used
    assert row['next_carryforward']==next_carry
    assert row['excluded_from_next_carry']==excluded
    assert row['available_amount']==used+next_carry+excluded


@pytest.mark.parametrize('change',['duplicate','prior_excess','current_origin','invalid_expiry'])
def test_invalid_ledger_rejected(change):
    item=lot();lots=[item]
    if change=='duplicate':lots.append(dict(item,identifier=' old '))
    elif change=='prior_excess':item['previously_deducted']='101'
    elif change=='current_origin':item['origin_period_end']='2026-01-01'
    else:item['verified_expiry_date']='2020-12-31'
    with pytest.raises(ValueError):run(lots)
