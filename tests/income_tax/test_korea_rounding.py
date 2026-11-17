from decimal import Decimal, localcontext

import pytest

from packages.income_tax.korea_rounding import final_cash_balance, taxable_base_won


@pytest.mark.parametrize('base,expected', [('0.999999', 0), ('1', 1),
    ('199999999.999999', 199999999), ('200000000.000001', 200000000)])
def test_base_discards_only_fractional_won(base, expected):
    assert taxable_base_won(base) == expected


@pytest.mark.parametrize('liability,paid,payable,refund', [
    ('9.999999', '0', 0, 0), ('10', '0', 10, 0), ('19.999999', '0', 10, 0),
    ('0', '9.999999', 0, 0), ('0', '10', 0, 10), ('0', '19.999999', 0, 10),
    ('100.1', '90.2', 0, 0), ('90.2', '100.1', 0, 0),
    ('100.2', '90.1', 10, 0), ('90.1', '100.2', 0, 10),
])
def test_final_net_is_rounded_toward_zero_after_offset(liability, paid, payable, refund):
    result = final_cash_balance(liability, paid, installment=False)
    assert result['payable'] == payable
    assert result['refundable'] == refund
    assert result['balance_before_cash_rounding'] == Decimal(liability) - Decimal(paid)


def test_national_and_local_balances_remain_separate():
    national = final_cash_balance('19', '0', installment=False)
    local = final_cash_balance('0', '19', installment=False)
    assert national['payable'] == local['refundable'] == 10


def test_precision_is_independent_of_callers_decimal_context():
    with localcontext() as context:
        context.prec = 6
        result = final_cash_balance('999999999999999999.9', '0.1', installment=False)
    assert result['payable'] == Decimal('999999999999999990')
    assert result['discarded_fraction'] == Decimal('9.8')


@pytest.mark.parametrize('installment', [True, None, 0, 'false'])
def test_installment_or_ambiguous_context_is_not_silently_rounded(installment):
    with pytest.raises(ValueError):
        final_cash_balance('10', '0', installment=installment)


@pytest.mark.parametrize('bad', [True, 1.1, '-1', 'NaN', 'Infinity', '1.0000001'])
def test_invalid_inputs_rejected(bad):
    with pytest.raises(ValueError): taxable_base_won(bad)
    with pytest.raises(ValueError): final_cash_balance(bad, '0', installment=False)
    with pytest.raises(ValueError): final_cash_balance('0', bad, installment=False)
