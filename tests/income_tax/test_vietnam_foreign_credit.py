from decimal import Decimal, localcontext

import pytest

from packages.income_tax.vietnam_foreign_credit import additional_top_up_credit


def calculate(**changes):
    values = dict(vietnam_tax_limit='200', established_ordinary_credit='150',
                  allocated_paid_top_up_tax='80', same_income_and_period_verified=True)
    values.update(changes)
    return additional_top_up_credit(**values)


def test_top_up_cannot_receive_a_second_full_credit_limit():
    result = calculate()
    assert result['remaining_limit_before_top_up'] == 50
    assert result['additional_top_up_credit'] == 50
    assert result['combined_credit'] == 200
    assert result['top_up_exceeding_limit'] == 30
    assert result['vietnam_tax_after_combined_credit'] == 0


@pytest.mark.parametrize('ordinary,top_up,expected,remaining', [
    ('0', '0', '0', '200'), ('0', '80', '80', '120'),
    ('200', '80', '200', '0'), ('150', '40', '190', '10'),
    ('150', '0', '150', '50'), ('0', '300', '200', '0'),
])
def test_cap_edges_and_unused_capacity(ordinary, top_up, expected, remaining):
    result = calculate(established_ordinary_credit=ordinary, allocated_paid_top_up_tax=top_up)
    assert result['combined_credit'] == Decimal(expected)
    assert result['vietnam_tax_after_combined_credit'] == Decimal(remaining)


def test_zero_tax_does_not_create_refundable_credit():
    result = calculate(vietnam_tax_limit='0', established_ordinary_credit='0')
    assert result['combined_credit'] == 0
    assert result['top_up_exceeding_limit'] == 80


def test_decimal_arithmetic_is_independent_of_callers_context():
    with localcontext() as context:
        context.prec = 3
        result = calculate(vietnam_tax_limit='999999999999999999.123456',
            established_ordinary_credit='999999999999999999.123455', allocated_paid_top_up_tax='1')
    assert result['additional_top_up_credit'] == Decimal('0.000001')
    assert result['top_up_exceeding_limit'] == Decimal('0.999999')


@pytest.mark.parametrize('changes', [
    {'vietnam_tax_limit': '-1'}, {'vietnam_tax_limit': 'NaN'},
    {'vietnam_tax_limit': '1e19'}, {'vietnam_tax_limit': True},
    {'allocated_paid_top_up_tax': 1.0}, {'allocated_paid_top_up_tax': '-1'},
    {'allocated_paid_top_up_tax': '0.0000001'},
    {'established_ordinary_credit': '201'}, {'established_ordinary_credit': '-1'},
    {'same_income_and_period_verified': False}, {'same_income_and_period_verified': 1},
])
def test_invalid_amounts_or_unverified_scope_rejected(changes):
    with pytest.raises(ValueError):
        calculate(**changes)


def test_outputs_preserve_the_established_ordinary_credit():
    result = calculate()
    assert result['established_ordinary_credit'] == 150
    assert result['combined_credit'] == (result['established_ordinary_credit']
                                         + result['additional_top_up_credit'])
    assert 'carry_forward_credit' not in result
    assert 'treaty_eligible' not in result
