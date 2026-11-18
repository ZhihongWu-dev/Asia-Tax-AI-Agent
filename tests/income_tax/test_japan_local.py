from decimal import Decimal, localcontext
import hashlib
from pathlib import Path
import pytest

from packages.income_tax.japan_local import ordinary_enterprise_levies, SOURCES


def compute(income, **changes):
    args = dict(fiscal_start_year=2026, months=12, reduced_bands_eligible=True,
        tokyo_surcharge_applies=False, ordinary_income_based_scope_verified=True)
    args.update(changes)
    return ordinary_enterprise_levies(income, **args)


def test_official_four_month_example_allocates_before_rounding():
    # Tokyo return instructions page15 gives these three independently rounded bases.
    result = compute('2856420', months=4)
    assert [r['taxable_base'] for r in result['bands']] == [1333000,1333000,189000]
    assert [r['allocated_before_rounding'] for r in result['bands']] == [1333333,1333333,189754]
    assert [r['tax'] for r in result['bands']] == [46600,70600,13200]
    assert result['enterprise_tax_before_credits'] == 130400
    assert result['special_enterprise_tax_before_credits'] == 48200


def test_surcharge_does_not_inflate_special_enterprise_tax():
    standard = compute('5000000')
    surcharge = compute('5000000', tokyo_surcharge_applies=True)
    assert standard['enterprise_tax_before_credits'] == 193000
    assert surcharge['enterprise_tax_before_credits'] == 206600
    assert surcharge['standard_rate_enterprise_tax'] == 193000
    assert standard['special_enterprise_tax_before_credits'] == surcharge['special_enterprise_tax_before_credits'] == 71400


def test_no_reduced_bands_taxes_entire_base_at_upper_rate():
    result = compute('5000000', reduced_bands_eligible=False, tokyo_surcharge_applies=True)
    assert len(result['bands']) == 1
    assert result['enterprise_tax_before_credits'] == 374000
    assert result['standard_rate_enterprise_tax'] == 350000
    assert result['special_enterprise_tax_before_credits'] == 129500


@pytest.mark.parametrize('income,enterprise,special',[
    ('0',0,0),('999',0,0),('2999',0,0),('3000',100,0),
    ('3999999',139900,51700),('4000000',140000,51800),
    ('4001999',140000,51800),('4002000',140100,51800),
    ('8000000',352000,130200),
])
def test_band_and_two_rounding_boundaries(income,enterprise,special):
    result = compute(income)
    assert result['enterprise_tax_before_credits'] == enterprise
    assert result['special_enterprise_tax_before_credits'] == special


@pytest.mark.parametrize('changes',[
    dict(months=0),dict(months=13),dict(months=True),dict(months='4'),
    dict(fiscal_start_year=2025),dict(fiscal_start_year=True),
    dict(reduced_bands_eligible=1),dict(tokyo_surcharge_applies=0),
    dict(ordinary_income_based_scope_verified=False),dict(ordinary_income_based_scope_verified=1),
])
def test_scope_and_eligibility_are_not_coerced(changes):
    with pytest.raises(ValueError): compute('1000000',**changes)


@pytest.mark.parametrize('income',['-1','0.1','NaN',True,1.1])
def test_whole_yen_inputs_only(income):
    with pytest.raises(ValueError): compute(income)


def test_precision_and_source_snapshot_isolation():
    with localcontext() as ctx:
        ctx.prec = 6
        result = compute('1000000000000000000')
        assert result['enterprise_tax_before_credits'] == Decimal('69999999999792000')
    result['sources'][0]['url'] = 'changed'
    assert compute('0')['sources'][0]['url'].startswith('https://www.tax.metro.tokyo.lg.jp/')
    root=Path(__file__).resolve().parents[2]
    assert len(SOURCES)==3
    for source in SOURCES:
        assert hashlib.sha256((root/source['file']).read_bytes()).hexdigest()==source['sha256']
