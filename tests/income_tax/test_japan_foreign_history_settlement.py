from copy import deepcopy
from decimal import localcontext
import hashlib
from pathlib import Path
import pytest
from packages.income_tax.japan_foreign_history_settlement import settle_national_history
from tests.income_tax.test_japan_foreign_history import history, lot
from tests.income_tax.test_japan_foreign_credit import args
from tests.income_tax.test_japan_local_foreign_credit import paper
from packages.income_tax.japan_local_foreign_credit import allocate_current
from packages.contracts.income_tax import CURRENCIES
from tests.income_tax.test_japan_osaka_foreign import run as current_osaka, fixture, paper as osaka_paper


def run(h=None, *, paid=31500000, **changes):
    options=dict(reference_taxes=dict(corporation_tax_reference=23200000,
        local_corporation_tax_reference=2389600, defence_tax_reference=728000),
        period_start='2026-04-01', period_end='2027-03-31',
        corporation_interim_liability=0, local_corporation_interim_liability=0,
        ordinary_final_return_without_other_credits_or_additions_verified=True)
    options.update(changes)
    # Foreign net income90m, eligible tax31.5m (35%); world100m.
    # A current payment beyond all limits can legitimately exceed the remaining
    # corporation liability when matched to historical national capacity.
    n=args();n.update(foreign_income_before_exempt=90000000,eligible_foreign_corporate_tax=paid)
    p=paper();p.update(prefectural_credit_limit=208800,municipal_credit_limit=1252800)
    return settle_national_history(allocate_current(n,p), h or history(lot(2025)), **options)


def test_history_refund_and_interim_refund_are_separate_from_nonnegative_tax():
    r=run(history(lot(2025,national=3000000)),
        corporation_interim_liability=1000000)
    c=r['settlements']['corporation']
    assert c['eligible_foreign_credit']==23880000
    assert c['foreign_credit_applied_to_tax']==23200000
    assert c['foreign_credit_refund']==680000
    assert c['annual_liability']==0
    assert c['interim_refund']==1000000
    assert c['refundable']==1680000
    assert r['total_payable']==311700
    assert r['total_refundable']==1680000
    assert r['total_foreign_credit_refund']==680000
    assert r['total_interim_refund']==1000000
    assert r['history_matching']['periods'][0]['next_period_capacity']['national']==0


@pytest.mark.parametrize('used',[0,1,99,100,2319999,2320000,2320001])
def test_tax_hundred_yen_truncation_and_credit_refund_whole_yen_boundary(used):
    r=run(history(lot(2025,national=used)))
    c=r['settlements']['corporation']
    assert c['annual_liability']==max(0,2320000-used)//100*100
    assert c['foreign_credit_refund']==max(0,used-2320000)
    assert c['eligible_foreign_credit']==c['foreign_credit_applied_to_tax']+c['foreign_credit_refund']
    # Unmatched tax is not a refund and is not lost from the history ledger.
    assert r['history_matching']['current_excess_remaining']==6352560-used


def test_prior_excess_uses_current_capacity_without_crediting_local_history_to_national():
    r=run(history(lot(2025,excess=3000000)),paid=20000000)
    c=r['settlements']['corporation']
    assert c['current_foreign_credit']==20000000
    assert c['historical_excess_credit']==880000
    assert c['eligible_foreign_credit']==20880000
    assert c['annual_liability']==2320000
    assert c['foreign_credit_refund']==0
    assert r['history_matching']['historical_excess_used_by_layer']['municipal']==1252800
    for name,liability in [('local_corporation',2389600),('defence',728000)]:
        assert r['settlements'][name]['annual_liability']==liability
        assert r['settlements'][name]['historical_excess_credit']==0
    assert r['stage']=='national_annual_history_settlement_local_history_not_settled'


def test_expired_capacity_never_produces_refund():
    r=run(history(lot(2022,national=50000000)))
    assert r['total_foreign_credit_refund']==0
    assert r['settlements']['corporation']['annual_liability']==2320000


@pytest.mark.parametrize('value',[False,1,'true',None])
def test_final_return_scope_requires_explicit_true(value):
    with pytest.raises(ValueError):
        run(ordinary_final_return_without_other_credits_or_additions_verified=value)


@pytest.mark.parametrize('value',[-100,1,'100.5'])
def test_invalid_interim_liability(value):
    with pytest.raises(ValueError):
        run(corporation_interim_liability=value)


def test_reference_must_cover_current_statutory_limit():
    with pytest.raises(ValueError,match='reconcile'):
        run(reference_taxes=dict(corporation_tax_reference=100,
            local_corporation_tax_reference=2389600,defence_tax_reference=728000))


def test_defence_tax_cannot_be_applied_to_early_2026_start():
    with pytest.raises(ValueError,match='Defence tax'):
        run(history(lot(2024)),period_start='2026-01-01',period_end='2026-12-31')


def test_immutable_history_exact_low_precision_and_archived_sources():
    h=history(lot(2025,national=2320001));before=deepcopy(h)
    expected=run(h)
    with localcontext() as context:
        context.prec=4
        assert run(h)==expected
    assert h==before
    for source in expected['sources']:
        assert hashlib.sha256(Path(source['file']).read_bytes()).hexdigest()==source['sha256']


@pytest.mark.parametrize('country',[c for c in CURRENCIES if c!='jp'])
def test_zero_opening_history_reconciles_saved_case_national_settlement(country):
    case,source=fixture(country)
    local=osaka_paper();local['corporation_interim_liability']=14000000
    original=current_osaka(case,source,local)
    before=deepcopy(original)
    r=settle_national_history(original['current_foreign_credit'],history(lot(2025)),
        reference_taxes={k:v for k,v in original['reference_taxes'].items() if k.endswith('_tax_reference')},
        period_start=case['period_start'],period_end=case['period_end'],
        corporation_interim_liability=14000000,local_corporation_interim_liability=0,
        ordinary_final_return_without_other_credits_or_additions_verified=True)
    for name in ('corporation','local_corporation','defence'):
        for key in ('annual_liability','payable','refundable','balance_due'):
            assert r['settlements'][name][key]==original['settlements'][name][key]
    assert r['total_interim_refund']==80000
    assert r['total_foreign_credit_refund']==0
    assert original==before
