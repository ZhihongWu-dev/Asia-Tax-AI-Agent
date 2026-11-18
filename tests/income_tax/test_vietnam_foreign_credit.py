from decimal import Decimal, localcontext

import pytest

from packages.income_tax.vietnam_foreign_credit import additional_top_up_credit, indonesia_deemed_credit
from packages.income_tax.vietnam_foreign_credit import singapore_interest_royalty_credit
from packages.income_tax.vietnam_foreign_credit import dividend_underlying_tax


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


@pytest.mark.parametrize('kind', ['dividend', 'interest', 'royalty'])
def test_indonesia_deemed_credit_is_not_limited_to_actual_withholding(kind):
    result = indonesia_deemed_credit('1000', income_type=kind, vietnam_tax_limit='200',
        paragraph2_and_treaty_entitlement_verified=True)
    assert result['deemed_paid_tax'] == 150
    assert result['allowed_tax_credit'] == 150
    assert result['vietnam_tax_after_credit'] == 50


def test_indonesia_deemed_credit_cannot_exceed_same_income_tax():
    result = indonesia_deemed_credit('1000', income_type='dividend', vietnam_tax_limit='100',
        paragraph2_and_treaty_entitlement_verified=True)
    assert result['allowed_tax_credit'] == 100
    assert result['deemed_tax_exceeding_limit'] == 50


@pytest.mark.parametrize('changes', [
    {'income_type': 'business'}, {'income_type': 'capital_gain'},
    {'paragraph2_and_treaty_entitlement_verified': False},
    {'paragraph2_and_treaty_entitlement_verified': 1},
    {'gross_income': '0'}, {'gross_income': '-1'}, {'gross_income': 1.5},
    {'vietnam_tax_limit': 'NaN'},
])
def test_indonesia_deemed_credit_rejects_other_routes_or_invalid_basis(changes):
    args = dict(gross_income='1000', income_type='dividend', vietnam_tax_limit='200',
                paragraph2_and_treaty_entitlement_verified=True)
    args.update(changes)
    with pytest.raises(ValueError):
        indonesia_deemed_credit(**args)


@pytest.mark.parametrize('kind', ['interest', 'royalty'])
@pytest.mark.parametrize('paid,expected,floor_applied', [
    ('0', '100', True), ('50', '100', True), ('100', '100', False),
])
def test_singapore_deemed_floor_replaces_not_adds_to_paid_tax(kind, paid, expected, floor_applied):
    result = singapore_interest_royalty_credit('1000', income_type=kind,
        eligible_singapore_tax_paid=paid, vietnam_tax_limit='200',
        article11_or12_and_treaty_entitlement_verified=True)
    assert result['allowed_tax_credit'] == Decimal(expected)
    assert result['deemed_floor_applied'] is floor_applied
    assert result['vietnam_tax_after_credit'] == 100


def test_singapore_credit_remains_capped_by_same_income_tax():
    result = singapore_interest_royalty_credit('1000', income_type='royalty',
        eligible_singapore_tax_paid='50', vietnam_tax_limit='70',
        article11_or12_and_treaty_entitlement_verified=True)
    assert result['allowed_tax_credit'] == 70
    assert result['credit_basis_exceeding_limit'] == 30


@pytest.mark.parametrize('changes', [
    {'income_type': 'dividend'}, {'income_type': 'business'},
    {'article11_or12_and_treaty_entitlement_verified': False},
    {'article11_or12_and_treaty_entitlement_verified': 1},
    {'eligible_singapore_tax_paid': 'NaN'}, {'eligible_singapore_tax_paid': -1},
    {'gross_income': '0'}, {'vietnam_tax_limit': float('inf')},
])
def test_singapore_rejects_dividends_unverified_entitlement_and_bad_inputs(changes):
    args = dict(gross_income='1000', income_type='interest', eligible_singapore_tax_paid='50',
                vietnam_tax_limit='200', article11_or12_and_treaty_entitlement_verified=True)
    args.update(changes)
    with pytest.raises(ValueError):
        singapore_interest_royalty_credit(**args)


def underlying(**changes):
    args = dict(source_country='hk', qualifying_holding_percent='10',
        dividend_before_withholding='80', distributing_profit_after_tax='800',
        corporate_tax_paid_on_profit='200', corporate_recipient_and_pool_verified=True)
    args.update(changes)
    return dividend_underlying_tax(**args)


@pytest.mark.parametrize('country', ['hk', 'sg'])
def test_underlying_credit_attributes_only_the_distributed_profit(country):
    result = underlying(source_country=country)
    assert result['attributable_underlying_tax'] == 20
    assert 'allowed_tax_credit' not in result
    assert 'final_tax' not in result


def test_ownership_is_a_gate_not_a_second_allocation_factor():
    # Dividend amount already reflects the shareholder's distribution.
    assert underlying(qualifying_holding_percent='25')['attributable_underlying_tax'] == 20
    assert underlying(dividend_before_withholding='800')['attributable_underlying_tax'] == 200


def test_zero_distribution_and_zero_pool_tax():
    assert underlying(dividend_before_withholding='0')['attributable_underlying_tax'] == 0
    assert underlying(corporate_tax_paid_on_profit='0')['attributable_underlying_tax'] == 0


@pytest.mark.parametrize('changes', [
    {'source_country': 'id'}, {'qualifying_holding_percent': '9.999999'},
    {'qualifying_holding_percent': '100.000001'},
    {'corporate_recipient_and_pool_verified': 1}, {'corporate_recipient_and_pool_verified': False},
    {'distributing_profit_after_tax': '0'}, {'dividend_before_withholding': '801'},
    {'corporate_tax_paid_on_profit': '-1'}, {'dividend_before_withholding': float('nan')},
])
def test_underlying_rejects_wrong_treaty_threshold_or_unmatched_pool(changes):
    with pytest.raises(ValueError):
        underlying(**changes)
