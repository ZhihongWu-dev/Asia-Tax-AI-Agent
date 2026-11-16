from decimal import localcontext
import pytest
from packages.income_tax.vietnam_reliefs import company_small_revenue_exemption


def eligibility(**changes):
    facts = dict(tax_year=2026, vietnam_established=True, new_in_current_period=False,
                 previous_period_revenue='1000000000', previous_active_months=12,
                 current_period_actual_revenue=None, related_enterprise_disqualified=False,
                 statutory_revenue_scope_confirmed=True)
    facts.update(changes)
    return company_small_revenue_exemption(**facts)


@pytest.mark.parametrize('revenue,months,expected', [
    ('1000000000', 12, True), ('1000000001', 12, False),
    ('500000000', 6, True), ('500000001', 6, False),
    ('250000000', 3, True), ('250000001', 3, False),
    ('83333333.333333', 1, True), ('83333333.333334', 1, False)])
def test_annualized_threshold_without_rounding(revenue, months, expected):
    with localcontext() as ctx:
        ctx.prec = 6
        assert eligibility(previous_period_revenue=revenue,
                           previous_active_months=months)['eligible'] is expected


@pytest.mark.parametrize('changes', [
    {'vietnam_established': False}, {'related_enterprise_disqualified': True}])
def test_revenue_alone_does_not_establish_exemption(changes):
    result = eligibility(**changes)
    assert result['within_revenue_threshold'] is True
    assert result['eligible'] is False


def test_new_enterprise_requires_actual_current_revenue():
    facts = dict(new_in_current_period=True, previous_period_revenue=None,
                 previous_active_months=None, current_period_actual_revenue='1000000000')
    assert eligibility(**facts)['eligible'] is True
    facts['current_period_actual_revenue'] = '1000000001'
    assert eligibility(**facts)['eligible'] is False
    facts['current_period_actual_revenue'] = None
    with pytest.raises(ValueError): eligibility(**facts)


@pytest.mark.parametrize('changes', [
    {'tax_year': 2025}, {'tax_year': True}, {'vietnam_established': None},
    {'related_enterprise_disqualified': None}, {'statutory_revenue_scope_confirmed': False},
    {'previous_active_months': 0}, {'previous_active_months': True},
    {'previous_active_months': 13}, {'previous_period_revenue': None},
    {'previous_period_revenue': 1.0}, {'new_in_current_period': True},
    {'current_period_actual_revenue': '1000000000'}])
def test_unknown_inconsistent_or_out_of_scope_inputs_rejected(changes):
    with pytest.raises(ValueError): eligibility(**changes)
