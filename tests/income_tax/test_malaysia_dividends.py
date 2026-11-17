from decimal import Decimal, localcontext

import pytest

from packages.income_tax.malaysia_dividends import (
    allocate_dividend_income, dividend_statutory_income,
)


def allocate(a, b, c, **kwargs):
    args = dict(assessment_year=2026, residency='resident',
                dividend_statutory_income=a, aggregate_income=b,
                chargeable_income=c, bases_verified=True)
    args.update(kwargs)
    return allocate_dividend_income(**args)


def test_hasil_b2_official_example():
    assert dividend_statutory_income('2500000', scope_verified=True) == Decimal('2400000')


@pytest.mark.parametrize('value,expected', [('0','0'),('99999','0'),('100000','0'),('100001','1')])
def test_annual_threshold_boundary(value, expected):
    assert dividend_statutory_income(value, scope_verified=True) == Decimal(expected)


@pytest.mark.parametrize('residency', ['resident','nonresident'])
def test_mixed_income_allocation_and_conservation(residency):
    result = allocate('50000','150000','135000',residency=residency)
    assert result['dividend_chargeable_income'] == Decimal('45000')
    assert result['ordinary_chargeable_income'] == Decimal('90000')
    assert result['dividend_tax'] == Decimal('900')


def test_dividend_only_reliefs_reduce_dividend_base():
    result=allocate('200000','200000','191000')
    assert result['dividend_tax'] == Decimal('3820')
    assert result['ordinary_chargeable_income'] == 0


def test_zero_aggregate_has_no_division_by_zero():
    assert allocate('0','0','0')['dividend_tax'] == 0


def test_repeating_allocation_does_not_round_early():
    result=allocate('1','3','2')
    with localcontext() as ctx:
        ctx.prec=40
        assert result['dividend_chargeable_income'] == Decimal(2)/3
        assert result['ordinary_chargeable_income']+result['dividend_chargeable_income'] == 2


@pytest.mark.parametrize('a,b,c', [('1','0','0'),('11','10','5'),('1','10','11')])
def test_inconsistent_bases_rejected(a,b,c):
    with pytest.raises(ValueError): allocate(a,b,c)


@pytest.mark.parametrize('overrides', [dict(assessment_year=2025),dict(assessment_year=True),
    dict(residency='unknown'),dict(bases_verified=False),dict(bases_verified=1),
    dict(dividend_statutory_income=1.2),dict(aggregate_income='NaN'),dict(chargeable_income='-1')])
def test_invalid_inputs_rejected(overrides):
    with pytest.raises(ValueError): allocate('1','10','5',**overrides)


def test_threshold_requires_strict_verification():
    with pytest.raises(ValueError): dividend_statutory_income('200000',scope_verified=1)
