from copy import deepcopy
from decimal import Decimal
import pytest
from packages.income_tax.hong_kong_foreign_credit import calculate


def fixture():
    return dict(sources=[dict(source_id='receipt_a',country='sg',income_type='dividend',
        direct_foreign_tax_paid='100',cdta_applies=False,bilateral_credit_eligible_tax=None,
        underlying_tax_paid='200',underlying_tax_in_bilateral_claim='0',
        equity_fraction_at_distribution='.10',hong_kong_tax_on_same_income='250',
        taxable_fsie_receipt_and_similar_tax_verified=True,
        treaty_ownership_and_no_duplicate_tax_verified=True)],
        hong_kong_resident_mne_verified=True,source_tax_attribution_and_gross_up_verified=True,
        payment_fx_and_claim_evidence_verified=True)


@pytest.mark.parametrize('ownership,credit,underlying', [('.099999','100','0'),('.10','250','200'),('1','250','200')])
def test_underlying_unilateral_threshold(ownership,credit,underlying):
    p=fixture();p['sources'][0]['equity_fraction_at_distribution']=ownership
    result=calculate(p,total_hong_kong_tax='1000')
    assert result['foreign_tax_credit']==Decimal(credit)
    assert result['source_credits'][0]['unilateral_underlying_tax']==Decimal(underlying)


def test_cdta_and_supplementary_underlying_credit_do_not_duplicate():
    p=fixture()
    p['sources'][0].update(country='cn',cdta_applies=True,bilateral_credit_eligible_tax='180',
        underlying_tax_in_bilateral_claim='100',hong_kong_tax_on_same_income='500')
    result=calculate(p,total_hong_kong_tax='1000')
    row=result['source_credits'][0]
    assert row['bilateral_eligible_tax']==180
    assert row['unilateral_direct_tax']==0
    assert row['unilateral_underlying_tax']==100
    assert result['foreign_tax_credit']==280


def test_zero_bilateral_direct_entitlement_does_not_become_unilateral():
    p=fixture()
    p['sources'][0].update(cdta_applies=True,bilateral_credit_eligible_tax='0',
        underlying_tax_paid='0')
    assert calculate(p,total_hong_kong_tax='1000')['foreign_tax_credit']==0


def test_source_limits_do_not_pool_with_same_country():
    p=fixture();second=deepcopy(p['sources'][0])
    second.update(source_id='receipt_b',direct_foreign_tax_paid='10',underlying_tax_paid='0',
        hong_kong_tax_on_same_income='500')
    p['sources'].append(second)
    result=calculate(p,total_hong_kong_tax='1000')
    assert result['foreign_tax_credit']==260
    assert result['tax_after_credit_before_other_adjustments']==740


@pytest.mark.parametrize('kind',['interest','disposal_gain','ip_income'])
def test_other_taxable_fsie_income(kind):
    p=fixture();p['sources'][0].update(income_type=kind,underlying_tax_paid='0',
        equity_fraction_at_distribution=None)
    assert calculate(p,total_hong_kong_tax='1000')['foreign_tax_credit']==100


@pytest.mark.parametrize('change',['duplicate','domestic','exempt','nonresident','attribution',
    'ownership','underlying','bilateral','missing_bilateral','nondividend','no_cdta'])
def test_invalid_claims_rejected(change):
    p=fixture();s=p['sources'][0]
    if change=='duplicate':p['sources'].append(deepcopy(s))
    elif change=='domestic':s['country']='hk'
    elif change=='exempt':s['taxable_fsie_receipt_and_similar_tax_verified']=False
    elif change=='nonresident':p['hong_kong_resident_mne_verified']=False
    elif change=='attribution':s['hong_kong_tax_on_same_income']='1001'
    elif change=='ownership':s['equity_fraction_at_distribution']='1.01'
    elif change=='underlying':s['underlying_tax_in_bilateral_claim']='201'
    elif change=='bilateral':s.update(cdta_applies=True,bilateral_credit_eligible_tax='301')
    elif change=='missing_bilateral':s['cdta_applies']=True
    elif change=='nondividend':s['income_type']='interest'
    else:s['underlying_tax_in_bilateral_claim']='1'
    with pytest.raises(ValueError):calculate(p,total_hong_kong_tax='1000')


def test_source_archive_hash():
    import hashlib
    from pathlib import Path
    source=calculate(fixture(),total_hong_kong_tax='1000')['sources'][0]
    root=Path(__file__).resolve().parents[2]
    assert hashlib.sha256((root/source['file']).read_bytes()).hexdigest()==source['sha256']
