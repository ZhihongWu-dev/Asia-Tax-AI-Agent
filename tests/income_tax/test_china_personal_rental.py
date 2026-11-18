from decimal import Decimal, localcontext
from hashlib import sha256
from pathlib import Path

import pytest

from packages.income_tax.china_personal_rental import monthly_expense_base


@pytest.mark.parametrize('gross,deductions,base', [
    ('5000', '1200', '3000'),  # Gross exceeds4000, but the relevant balance does not.
    ('5000', '1000', '3200'),
    ('5000', '999.999999', '3200.0000008'),
    ('5000', '0', '4000'),
    ('800', '0', '0'),
    ('600', '0', '0'),
    ('800', '800', '0'),
    ('0', '0', '0'),
])
def test_monthly_threshold_after_preceding_deductions(gross, deductions, base):
    result = monthly_expense_base(gross, deductions)
    assert result['income_after_statutory_expense'] == Decimal(base)
    assert result['statutory_expense'] + result['income_after_statutory_expense'] == Decimal(gross) - Decimal(deductions)


def test_annual_aggregation_does_not_replace_monthly_calculation():
    monthly = sum(monthly_expense_base('1000', '0')['income_after_statutory_expense'] for _ in range(12))
    assert monthly == 2400
    assert monthly_expense_base('12000', '0')['income_after_statutory_expense'] == 9600


@pytest.mark.parametrize('gross,deductions', [('500', '501'), ('-1', '0'), ('1.0000001', '0'), (True, '0'), ('NaN', '0')])
def test_unestablished_negative_balance_and_invalid_money_rejected(gross, deductions):
    with pytest.raises(ValueError):
        monthly_expense_base(gross, deductions)


def test_context_independence_and_archived_sources():
    expected = monthly_expense_base('5000', '999.999999')
    with localcontext() as ctx:
        ctx.prec = 4
        assert monthly_expense_base('5000', '999.999999') == expected
    for source in expected['sources']:
        assert sha256(Path(source['file']).read_bytes()).hexdigest() == source['sha256']
