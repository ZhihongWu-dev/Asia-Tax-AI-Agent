from copy import deepcopy
from decimal import localcontext
from pathlib import Path
import hashlib
import pytest
from packages.income_tax.japan_local_foreign_history import settle_local_history,LevyHistory
from tests.income_tax.test_japan_foreign_history import current,history,lot
from packages.income_tax.japan_foreign_history_settlement import settle_national_and_local_history
from tests.income_tax.test_japan_foreign_credit import args
from tests.income_tax.test_japan_local_foreign_credit import paper
from packages.income_tax.japan_local_foreign_credit import allocate_current


def limits(*rows):
    p=history(*rows)
    del p['no_local_levy_shortfall_balances_or_special_adjustments_verified']
    return p


def local_lot(year,pref=0,city=0):
    return dict(identifier=str(year),period_start=f'{year}-04-01',period_end=f'{year+1}-03-31',
        prefectural=pref,municipal=city)


def local_history(*rows):
    p=dict(periods=list(rows),prefectural_filing_id='Osaka prefecture',municipal_filing_id='Osaka city')
    p.update({k:True for k in LevyHistory.model_fields if k.endswith('_verified')})
    return p


def run(local=None,statutory=None,allocation=None,**changes):
    options=dict(period_start='2026-04-01',period_end='2027-03-31',
        prefectural_interim_liability=0,municipal_interim_liability=0)
    options.update(changes)
    return settle_local_history(allocation or current(),statutory or limits(),local or local_history(),**options)


def test_old_levy_shortfall_precedes_new_credit_and_never_restores_statutory_capacity():
    r=run(local_history(local_lot(2025,500000,2000000)),
        limits(lot(2025,prefectural=100000,municipal=200000)),
        prefectural_interim_liability=100,municipal_interim_liability=200)
    assert r['total_payable']==0
    assert r['total_refundable']==300  # Only interim refunds, not unused foreign tax.
    assert r['local_levy_history'][0]['used']==dict(prefectural=464000,municipal=1902400)
    assert r['local_levy_history'][0]['next_period']==dict(prefectural=36000,municipal=97600)
    assert r['current_period_levy_shortfall']['balances']==dict(prefectural=192800,municipal=756800)
    assert r['next_period_levy_shortfall']==dict(prefectural=228800,municipal=854400)
    matched=r['history_matching']
    assert matched['periods'][0]['next_period_capacity']==dict(national=0,prefectural=0,municipal=0)
    assert matched['current_excess_remaining']==523360


def test_oldest_local_shortfall_first_even_when_input_reversed():
    h=local_history(local_lot(2024,300000,1000000),local_lot(2023,300000,1000000))
    r=run(h)
    assert [p['identifier'] for p in r['local_levy_history']]==['2023','2024']
    assert r['local_levy_history'][0]['used']==dict(prefectural=300000,municipal=1000000)
    assert r['local_levy_history'][1]['used']==dict(prefectural=164000,municipal=902400)
    assert r==run(local_history(*reversed(h['periods'])))


def test_inclusive_three_year_start_window_and_expiry_before_next_period():
    old=local_lot(2022,123,456);old.update(period_start='2023-03-31',period_end='2023-03-31')
    r=run(local_history(old,local_lot(2023,500000,2000000)))
    assert r['local_levy_history'][0]['expired_before_current'] is True
    assert r['local_levy_history'][0]['used']==dict(prefectural=0,municipal=0)
    assert r['local_levy_history'][1]['expired_before_current'] is False
    assert r['local_levy_history'][1]['expired']==dict(prefectural=36000,municipal=97600)
    assert r['next_period_levy_shortfall']==dict(prefectural=92800,municipal=556800)
    assert r['expired_levy_shortfall']==dict(prefectural=36123,municipal=98056)


def test_one_yen_prior_credit_applies_before_hundred_yen_tax_truncation():
    r=run(local_history(local_lot(2025,1,1)))
    assert r['settlements']['prefectural']['annual_liability']==371100
    assert r['settlements']['municipal']['annual_liability']==1345500


def test_prior_excess_matched_to_current_local_capacity_is_added_once():
    r=run(local_history(local_lot(2025,20000,20000)),
        limits(lot(2025,excess=1000000)),current(9000000))
    assert r['settlements']['prefectural']['historical_limit_credit']==92800
    assert r['settlements']['municipal']['historical_limit_credit']==556800
    assert r['settlements']['prefectural']['annual_liability']==351200
    assert r['settlements']['municipal']['annual_liability']==1325600
    assert r['current_period_levy_shortfall']['balances']==dict(prefectural=0,municipal=0)


@pytest.mark.parametrize('pref,city',[(0,0),(1,1),(400000,1800000),(500000,2000000),(1000000,3000000)])
def test_separate_ledgers_conserve_balances(pref,city):
    r=run(local_history(local_lot(2025,pref,city)))
    for layer,opening in [('prefectural',pref),('municipal',city)]:
        s=r['settlements'][layer]
        assert opening+s['current_period_eligible_credit']==s['total_foreign_credit_applied']+r['next_period_levy_shortfall'][layer]
        assert s['reference_tax']==s['total_foreign_credit_applied']+s['after_credit_before_final_rounding']
        assert s['annual_liability']>=0
        assert s['refundable']==0


@pytest.mark.parametrize('flag',[k for k in LevyHistory.model_fields if k.endswith('_verified')])
def test_unverified_local_history_rejected(flag):
    h=local_history();h[flag]=False
    with pytest.raises(ValueError):run(h)


@pytest.mark.parametrize('change',['duplicate_id','overlap','current_period','fraction','calendar','filing_id','multiple_filings','interim'])
def test_inconsistent_or_unsupported_ledger_facts_rejected(change):
    h=local_history(local_lot(2025,100,100));s=limits();c=current();options={}
    if change=='duplicate_id':h['periods'].append(local_lot(2025))
    if change=='overlap':h['periods'].append(dict(local_lot(2025),identifier='other'))
    if change=='current_period':h['periods']=[local_lot(2026)]
    if change=='fraction':h['periods'][0]['municipal']='1.5'
    if change=='calendar':
        row=lot(2025,national=1);row.update(period_start='2025-01-01',period_end='2025-12-31');s=limits(row)
    if change=='filing_id':h['municipal_filing_id']='Another city'
    if change=='multiple_filings':c['municipal']['filings'].append(deepcopy(c['municipal']['filings'][0]))
    if change=='interim':options['prefectural_interim_liability']=1
    with pytest.raises(ValueError):run(h,s,c,**options)


def test_exact_with_low_precision_no_input_mutation_and_source_hashes():
    h=local_history(local_lot(2025,500000,2000000));s=limits(lot(2025,prefectural=100000))
    c=current();before=deepcopy((h,s,c));expected=run(h,s,c)
    with localcontext() as context:
        context.prec=4
        assert run(h,s,c)==expected
    assert (h,s,c)==before
    for source in expected['sources']:
        assert hashlib.sha256(Path(source['file']).read_bytes()).hexdigest()==source['sha256']


def test_five_tax_settlement_combines_national_refund_with_local_carry_without_double_use():
    n=args();n.update(foreign_income_before_exempt=90000000,eligible_foreign_corporate_tax=31500000)
    p=paper();p.update(prefectural_credit_limit=208800,municipal_credit_limit=1252800)
    c=allocate_current(n,p)
    r=settle_national_and_local_history(c,
        limits(lot(2025,national=3000000,prefectural=200000,municipal=1000000)),
        local_history(local_lot(2025,500000,2000000)),
        reference_taxes={k:n[k] for k in ('corporation_tax_reference','local_corporation_tax_reference','defence_tax_reference')},
        period_start='2026-04-01',period_end='2027-03-31',corporation_interim_liability=1000000,
        local_corporation_interim_liability=0,prefectural_interim_liability=100,municipal_interim_liability=200,
        ordinary_final_return_without_other_credits_or_additions_verified=True)
    assert len(r['settlements'])==5
    assert r['total_payable']==311700
    assert r['total_refundable']==1680300
    assert r['total_foreign_credit_refund']==680000
    assert r['total_interim_refund']==1000300
    assert r['next_period_levy_shortfall']==dict(prefectural=444800,municipal=2350400)
    assert r['history_matching']['current_excess_remaining']==2152560
    assert r['history_matching']['periods'][0]['next_period_capacity']==dict(national=0,prefectural=0,municipal=0)
    assert any('74(1)(3)' in provision for source in r['sources'] for provision in source.get('provisions',[]))
    assert any('9-7(17)' in provision for source in r['sources'] for provision in source.get('provisions',[]))
