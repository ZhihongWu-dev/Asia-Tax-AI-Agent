from decimal import Decimal, localcontext

import pytest

from packages.income_tax.thailand_dividends import DividendTranche, prepare_aggregated_dividends


def prepare(*rows, **kwargs):
    return prepare_aggregated_dividends(list(rows), certificates_verified=True,
                                      recipient_eligibility_verified=True, **kwargs)


def test_mixed_certified_rates_and_withholding_are_not_a_fixed_fraction():
    result = prepare(DividendTranche('80000', '20', '8000', True),
                     DividendTranche('70000', '30', '7000', True),
                     DividendTranche('50000', None, '5000', False))
    assert result['gross_dividends'] == 200000
    assert result['dividend_credit'] == 50000
    assert result['assessable_dividends'] == 250000
    assert result['withholding_tax'] == 20000
    assert result['tranches'][0]['net_cash_received'] == 72000
    assert result['tranches'][0]['dividend_credit'] == 20000
    assert result['tranches'][1]['dividend_credit'] == 30000
    assert 'final_tax' not in result  # Annual election/settlement is separate.


def test_zero_rate_and_noncreditable_dividends_remain_distinct():
    result = prepare(DividendTranche('100', '0', '10', True),
                     DividendTranche('100', None, '10', False))
    assert result['dividend_credit'] == 0
    assert result['assessable_dividends'] == 200
    assert result['tranches'][0]['credit_eligible'] is True
    assert result['tranches'][1]['credit_eligible'] is False


def test_repeating_rate_does_not_depend_on_callers_decimal_context():
    with localcontext() as ctx:
        ctx.prec = 6
        result = prepare(DividendTranche('100', '15', '10', True))
    with localcontext() as ctx:
        ctx.prec = 40
        assert result['dividend_credit'] == Decimal('1500') / 85


@pytest.mark.parametrize('rate', [None, '100', '101', '-1', 'NaN', True, 20.0])
def test_invalid_or_missing_eligible_rate(rate):
    with pytest.raises(ValueError):
        prepare(DividendTranche('100', rate, '10', True))


@pytest.mark.parametrize('row', [DividendTranche('100', '20', '101', True),
    DividendTranche('-1', '20', '0', True), DividendTranche('100', '20', '10', False),
    DividendTranche('100', '20', '10', 1), DividendTranche(100.0, '20', '10', True)])
def test_inconsistent_tranches_rejected(row):
    with pytest.raises(ValueError):
        prepare(row)


@pytest.mark.parametrize('flag', [False, 1, 'true', None])
def test_certificates_and_eligibility_are_strict(flag):
    row = DividendTranche('100', '20', '10', True)
    for field in ('certificates_verified', 'recipient_eligibility_verified'):
        args = dict(certificates_verified=True, recipient_eligibility_verified=True)
        args[field] = flag
        with pytest.raises(ValueError):
            prepare_aggregated_dividends([row], **args)


def test_empty_tranches_rejected():
    with pytest.raises(ValueError):
        prepare()
