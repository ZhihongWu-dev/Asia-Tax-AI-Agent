from decimal import Decimal

import pytest

from packages.income_tax.thailand_company_foreign_limits import allocate_foreign_period_tax


def data(**changes):
    return dict(dict(foreign_period_start='2025-07-01', foreign_period_end='2026-06-30',
        thai_period_start='2026-01-01', thai_period_end='2026-12-31',
        foreign_tax_base='net_profit', total_foreign_period_basis='1000000',
        basis_in_overlapping_period='300000', foreign_tax_paid='100000',
        payment_date='2027-07-01', payment_date_market_thb_per_unit='0.25',
        thai_return_filed_on='2027-05-25',
        actual_period_basis_and_payment_evidence_verified=True), **changes)


@pytest.mark.parametrize('base', ['net_profit', 'gross_receipts'])
def test_actual_basis_not_days_drives_allocation(base):
    result = allocate_foreign_period_tax(data(foreign_tax_base=base))
    assert result['allocated_tax_before_credit_limits'] == 7500
    assert result['tax_outside_thai_period'] == 17500
    assert result['amendment_required'] is True
    assert str(result['thai_period_end']) == '2026-12-31'
    assert str(result['overlap_end']) == '2026-06-30'


def test_complementary_accounting_periods_conserve_paid_tax():
    current = allocate_foreign_period_tax(data())
    previous = allocate_foreign_period_tax(data(thai_period_start='2025-01-01',
        thai_period_end='2025-12-31', basis_in_overlapping_period='700000'))
    assert current['allocated_tax_before_credit_limits'] + previous['allocated_tax_before_credit_limits'] == 25000


def test_full_foreign_period_is_not_reduced_by_longer_thai_period():
    result = allocate_foreign_period_tax(data(foreign_period_start='2026-01-01',
        basis_in_overlapping_period='1000000'))
    assert result['allocated_tax_before_credit_limits'] == 25000


def test_fraction_retained_and_zero_overlap_income_allowed():
    result = allocate_foreign_period_tax(data(total_foreign_period_basis='3',
        basis_in_overlapping_period='1', foreign_tax_paid='1', payment_date_market_thb_per_unit='1'))
    assert result['exact_allocated_tax'] == dict(numerator='1', denominator='3')
    assert result['allocated_tax_before_credit_limits'] == Decimal('0.'+'3'*40)
    assert allocate_foreign_period_tax(data(basis_in_overlapping_period='0'))['allocated_tax_before_credit_limits'] == 0


@pytest.mark.parametrize('changes', [
    dict(foreign_period_start='2027-01-01', foreign_period_end='2027-12-31'),
    dict(foreign_period_start='2026-07-01'),
    dict(thai_period_start='2027-01-01'),
    dict(total_foreign_period_basis='0'),
    dict(basis_in_overlapping_period='1000001'),
    dict(basis_in_overlapping_period='-1'),
    dict(foreign_period_start='2026-01-01'),
    dict(payment_date_market_thb_per_unit='0'),
    dict(thai_return_filed_on='2026-06-30'),
    dict(actual_period_basis_and_payment_evidence_verified=False),
])
def test_inconsistent_periods_or_unverified_inputs_rejected(changes):
    with pytest.raises(ValueError):
        allocate_foreign_period_tax(data(**changes))


def test_payment_on_filing_day_and_unknown_filing_date():
    assert not allocate_foreign_period_tax(data(payment_date='2027-05-25'))['amendment_required']
    result = allocate_foreign_period_tax(data(thai_return_filed_on=None))
    assert not result['amendment_timing_known']
    assert result['amendment_required'] is None
