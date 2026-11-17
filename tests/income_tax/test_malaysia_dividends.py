from decimal import Decimal, localcontext

import pytest

from packages.income_tax.malaysia_dividends import (
    allocate_dividend_income, annual_dividend_assessment, dividend_statutory_income,
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


def annual(**kwargs):
    args = dict(assessment_year=2026, residency='resident',
                dividend_statutory_income='50000', aggregate_income='150000',
                chargeable_income='135000', bases_verified=True,
                allowed_rebates='0', allowed_tax_credits='0', prepaid_tax='0',
                settlement_inputs_verified=True)
    args.update(kwargs)
    return annual_dividend_assessment(**args)


def test_resident_annual_combines_separate_rates_before_settlement():
    result=annual(allowed_tax_credits='400',prepaid_tax='9000')
    assert result['ordinary_tax'] == Decimal('7500')
    assert result['dividend_tax'] == Decimal('900')
    assert result['gross_tax'] == Decimal('8400')
    assert result['final_tax'] == Decimal('8000')
    assert result['refund_due'] == Decimal('1000')
    assert result['amount_payable'] == 0


def test_nonresident_annual_uses_30_percent_only_for_ordinary_remainder():
    result=annual(residency='nonresident',prepaid_tax='1000')
    assert result['ordinary_tax'] == Decimal('27000')
    assert result['final_tax'] == Decimal('27900')
    assert result['amount_payable'] == Decimal('26900')


def test_no_dividend_still_preserves_ordinary_schedule():
    result=annual(dividend_statutory_income='0',aggregate_income='50000',chargeable_income='35000',allowed_rebates='400')
    assert result['dividend_tax'] == 0
    assert result['gross_tax'] == Decimal('600')
    assert result['final_tax'] == Decimal('200')


def test_annual_dividend_only_does_not_apply_progressive_rates():
    result=annual(dividend_statutory_income='2400000',aggregate_income='2400000',chargeable_income='2391000')
    assert result['ordinary_tax'] == 0
    assert result['dividend_tax'] == Decimal('47820')


def test_repeating_ordinary_base_is_not_rejected_or_rounded_to_six_decimals():
    result=annual(dividend_statutory_income='50000',aggregate_income='150001',chargeable_income='135000')
    assert result['ordinary_chargeable_income'].as_tuple().exponent < -6
    with localcontext() as ctx:
        ctx.prec=40
        assert result['gross_tax'] == result['ordinary_tax']+result['dividend_tax']


@pytest.mark.parametrize('overrides', [dict(allowed_rebates='8401'),
    dict(allowed_rebates='400',allowed_tax_credits='8001'),
    dict(residency='nonresident',allowed_rebates='1'),dict(prepaid_tax='-1'),
    dict(settlement_inputs_verified=False),dict(settlement_inputs_verified=1)])
def test_annual_rejects_invalid_settlement(overrides):
    with pytest.raises(ValueError): annual(**overrides)
