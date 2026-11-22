from decimal import Decimal
from fractions import Fraction
from pathlib import Path
import hashlib
import pytest
from packages.income_tax.japan_foreign_credit import current_national_credits,SOURCES


def args():
    return dict(statutory_worldwide_income='100000000',foreign_income_before_exempt='40000000',
        foreign_income_exempt_from_foreign_tax='0',eligible_foreign_corporate_tax='12000000',
        corporation_tax_reference='23200000',local_corporation_tax_reference='2389600',
        defence_tax_reference='728000',defence_applicable=True,
        statutory_reference_amounts_and_current_tax_eligibility_verified=True,
        no_history_group_or_special_credit_adjustments_verified=True)


def test_three_national_taxes_use_sequential_caps_and_leave_local_review_balance():
    r=current_national_credits(**args())
    assert r['corporation_credit']==9280000
    assert r['local_corporation_credit']==955840
    assert r['defence_credit']==291200
    assert r['total_current_national_credit']==10527040
    assert r['remaining_for_local_and_history_review']==1472960


@pytest.mark.parametrize('paid,expected',[(0,(0,0,0)),(100,(100,0,0)),
    (9280000,(9280000,0,0)),(9300000,(9280000,20000,0)),
    (10235840,(9280000,955840,0)),(10300000,(9280000,955840,64160))])
def test_credit_moves_to_next_tax_only_after_prior_limit(paid,expected):
    p=args();p['eligible_foreign_corporate_tax']=paid;r=current_national_credits(**p)
    assert tuple(r[k] for k in ('corporation_credit','local_corporation_credit','defence_credit'))==expected


def test_ninety_percent_cap_and_full_exempt_foreign_income_exclusion():
    p=args();p.update(foreign_income_before_exempt='150000000',eligible_foreign_corporate_tax='50000000')
    r=current_national_credits(**p)
    assert r['foreign_income_ratio']==Decimal('.9')
    p['foreign_income_exempt_from_foreign_tax']='140000000'
    assert current_national_credits(**p)['foreign_income_ratio']==Decimal('.1')
    p['foreign_income_exempt_from_foreign_tax']='150000000'
    assert current_national_credits(**p)['total_current_national_credit']==0


def test_period_before_defence_commencement_has_no_defence_credit():
    p=args();p.update(defence_applicable=False,defence_tax_reference='0')
    assert current_national_credits(**p)['defence_credit']==0


def test_repeating_ratio_preserves_exact_fraction_for_later_rounding():
    p=args();p.update(statutory_worldwide_income=3,foreign_income_before_exempt=1,corporation_tax_reference=1)
    r=current_national_credits(**p)
    f=r['exact_fractions']['corporation_credit_limit']
    assert Fraction(int(f['numerator']),int(f['denominator']))==Fraction(1,3)


@pytest.mark.parametrize('key,value',[
    ('statutory_worldwide_income',0),('foreign_income_exempt_from_foreign_tax','40000001'),
    ('eligible_foreign_corporate_tax','-1'),('corporation_tax_reference','1.1'),
    ('defence_applicable',1),('defence_applicable',False),
    ('statutory_reference_amounts_and_current_tax_eligibility_verified',False),
    ('no_history_group_or_special_credit_adjustments_verified',False)])
def test_invalid_or_unverified_basis_rejected(key,value):
    p=args();p[key]=value
    with pytest.raises(ValueError):current_national_credits(**p)


def test_archived_original_hashes():
    root=Path(__file__).resolve().parents[2]
    for source in SOURCES:
        assert hashlib.sha256((root/source['file']).read_bytes()).hexdigest()==source['sha256']
