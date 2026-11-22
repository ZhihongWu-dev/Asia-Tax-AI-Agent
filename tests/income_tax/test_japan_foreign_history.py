from copy import deepcopy
from decimal import localcontext
import hashlib
from pathlib import Path
import pytest
from packages.income_tax.japan_foreign_history import match_history
from packages.income_tax.japan_local_foreign_credit import allocate_current
from tests.income_tax.test_japan_foreign_credit import args
from tests.income_tax.test_japan_local_foreign_credit import paper


def current(paid=12000000):
    n=args();n['eligible_foreign_corporate_tax']=paid
    return allocate_current(n,paper())


def lot(year,*,national=0,prefectural=0,municipal=0,excess=0):
    return dict(identifier=str(year),period_start=f'{year}-04-01',period_end=f'{year+1}-03-31',
        unused_capacity=dict(national=national,prefectural=prefectural,municipal=municipal),excess_foreign_tax=excess)


def history(*rows):
    return dict(periods=list(rows),
        original_returns_entitlement_prior_usage_and_continuous_filings_verified=True,
        no_foreign_tax_expense_elections_reductions_groups_or_reorganizations_verified=True,
        no_local_levy_shortfall_balances_or_special_adjustments_verified=True)


def run(h,c=None):
    return match_history(c or current(),h,period_start='2026-04-01',period_end='2027-03-31')


def test_oldest_period_precedes_newer_national_capacity_and_same_year_layer_order():
    h=history(lot(2024,national=200000,prefectural=50000,municipal=60000),
        lot(2023,national=100000,prefectural=20000,municipal=30000))
    r=run(h,current(11626640)) # Current excess450000.
    assert [p['identifier'] for p in r['periods']]==['2023','2024']
    assert r['historical_capacity_used_by_layer']==dict(national=300000,prefectural=70000,municipal=80000)
    assert r['periods'][1]['next_period_capacity']==dict(national=0,prefectural=0,municipal=10000)
    assert r['current_excess_remaining']==0
    assert run(history(*reversed(h['periods'])),current(11626640))==r


def test_older_excess_consumes_current_national_then_local_capacity():
    r=run(history(lot(2024,excess=700000),lot(2023,excess=300000)),current(9000000))
    assert r['periods'][0]['excess_matched_to_current_capacity']==dict(national=280000,prefectural=20000,municipal=0)
    assert r['periods'][1]['excess_matched_to_current_capacity']==dict(national=0,prefectural=72800,municipal=556800)
    assert r['periods'][1]['next_period_excess']==70400
    assert r['current_capacity_remaining']==dict(national=0,prefectural=0,municipal=0)


def test_unused_local_corporation_and_defence_limits_never_become_history_capacity():
    r=run(history(lot(2025,excess=2000000)),current(9500000))
    assert r['historical_excess_used_by_layer']==dict(national=0,prefectural=92800,municipal=556800)
    assert r['periods'][0]['next_period_excess']==1350400


def test_three_year_window_uses_origin_start_inclusive_not_origin_end():
    old=lot(2022,excess=123);old.update(period_start='2023-03-31',period_end='2023-03-31')
    boundary=lot(2023,excess=1000000)
    r=run(history(old,boundary),current(9000000))
    assert r['earliest_eligible_origin_start']=='2023-04-01'
    assert r['periods'][0]['expired_before_current'] is True
    assert r['periods'][0]['expired_excess']==123
    assert r['periods'][1]['expired_before_current'] is False
    assert r['periods'][1]['remaining_excess_after_matching']==70400
    assert r['periods'][1]['expired_excess']==70400
    assert r['periods'][1]['next_period_excess']==0


def test_short_periods_are_not_reduced_to_last_three_records():
    rows=[]
    for month in (1,2,3,4):
        row=lot(2025,national=100);row.update(identifier=str(month),period_start=f'2025-{month:02}-01',period_end=f'2025-{month:02}-20')
        rows.append(row)
    assert run(history(*rows))['historical_capacity_used_by_layer']['national']==400


@pytest.mark.parametrize('paid',[0,9000000,9280000,9500000,10527040,10600000,11176640,12000000])
def test_opening_balances_equal_used_plus_expired_plus_next_period(paid):
    h=history(lot(2023,national=100000,prefectural=20000,municipal=30000),lot(2024,excess=900000))
    c=current(paid);r=run(h,c)
    for row in r['periods']:
        for layer in ('national','prefectural','municipal'):
            assert row['opening_capacity'][layer]==sum(row[k][layer] for k in (
                'capacity_matched_to_current_excess','expired_capacity','next_period_capacity'))
        assert row['opening_excess']==sum(row['excess_matched_to_current_capacity'].values())+row['expired_excess']+row['next_period_excess']
    assert c['foreign_tax_above_all_current_limits']==sum(r['historical_capacity_used_by_layer'].values())+r['current_excess_remaining']
    for layer in ('national','prefectural','municipal'):
        assert c['current_unused_capacity_before_history'][layer]==r['historical_excess_used_by_layer'][layer]+r['current_capacity_remaining'][layer]


@pytest.mark.parametrize('change',['identifier','overlap','current','future','long_period','both','fraction','negative','flag','shortfall'])
def test_invalid_or_unverified_history_rejected(change):
    h=history(lot(2024,excess=100),lot(2025,excess=100))
    if change=='identifier':h['periods'][1]['identifier']='2024'
    elif change=='overlap':h['periods'][1]['period_start']='2025-03-31'
    elif change=='current':h['periods'][1]['period_end']='2026-04-01'
    elif change=='future':h['periods'][1]['period_start']='2027-01-01'
    elif change=='long_period':h['periods'][0]['period_start']='2023-01-01'
    elif change=='both':h['periods'][0]['unused_capacity']['national']=1
    elif change=='fraction':h['periods'][0]['excess_foreign_tax']='1.5'
    elif change=='negative':h['periods'][0]['excess_foreign_tax']=-1
    elif change=='shortfall':h['no_local_levy_shortfall_balances_or_special_adjustments_verified']=False
    else:h['original_returns_entitlement_prior_usage_and_continuous_filings_verified']=False
    with pytest.raises(ValueError):run(h)


def test_matching_preserves_inputs_and_ignores_ambient_decimal_precision():
    h=history(lot(2025,excess=1000000));c=current(9000000);original=deepcopy((h,c))
    expected=run(h,c)
    with localcontext() as context:
        context.prec=4
        assert run(h,c)==expected
    assert (h,c)==original
    root=Path(__file__).resolve().parents[2]
    for source in expected['sources']:
        assert hashlib.sha256((root/source['file']).read_bytes()).hexdigest()==source['sha256']
