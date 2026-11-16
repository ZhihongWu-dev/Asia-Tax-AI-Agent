from decimal import localcontext
import pytest
from packages.income_tax.vietnam_reliefs import company_small_revenue_exemption
from packages.income_tax.vietnam_reliefs import company_2026_2027_reduction, resident_business_2026_2027_reduction


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


def company_reduction(**changes):
    facts = dict(tax_after_other_incentives='70000000', tax_year=2026,
        current_period_statutory_revenue='10000000000', vietnam_established=True,
        formed_by_split_after_resolution=False, all_split_entities_revenue=None,
        statutory_revenue_and_period_confirmed=True, prior_incentives_applied=True)
    facts.update(changes)
    return company_2026_2027_reduction(**facts)


def personal_reduction(**changes):
    facts = dict(business_income_tax='100000000', tax_year=2026,
        annual_actual_business_revenue='10000000000', resident=True,
        business_income_only_confirmed=True, statutory_revenue_scope_confirmed=True)
    facts.update(changes)
    return resident_business_2026_2027_reduction(**facts)


@pytest.mark.parametrize('year', [2026, 2027])
def test_reduction_of_tax_after_incentives_and_inclusive_limit(year):
    result = company_reduction(tax_year=year)
    assert result['reduction'] == 21000000
    assert result['tax_after_reduction'] == 49000000
    assert personal_reduction(tax_year=year)['reduction'] == 30000000
    assert company_reduction(current_period_statutory_revenue='10000000001')['reduction'] == 0
    assert personal_reduction(annual_actual_business_revenue='10000000001')['reduction'] == 0


def test_split_aggregation_and_independent_eligibility_facts():
    assert company_reduction(formed_by_split_after_resolution=True,
                             all_split_entities_revenue='10000000000')['eligible']
    assert not company_reduction(formed_by_split_after_resolution=True,
                                 all_split_entities_revenue='10000000001')['eligible']
    assert not company_reduction(vietnam_established=False)['eligible']
    assert not personal_reduction(resident=False)['eligible']


def test_reduction_preserves_exact_money_under_low_ambient_precision():
    with localcontext() as ctx:
        ctx.prec = 6
        result = company_reduction(tax_after_other_incentives='123456789.123456')
    assert str(result['reduction']) == '37037036.73703680'
    assert result['tax_before_reduction'] == result['tax_after_reduction'] + result['reduction']
    assert company_reduction(tax_after_other_incentives='0')['tax_after_reduction'] == 0


@pytest.mark.parametrize('changes', [
    {'tax_year': 2025}, {'tax_year': 2028}, {'tax_year': True},
    {'prior_incentives_applied': False}, {'statutory_revenue_and_period_confirmed': None},
    {'vietnam_established': None}, {'formed_by_split_after_resolution': None},
    {'formed_by_split_after_resolution': True},
    {'formed_by_split_after_resolution': True, 'all_split_entities_revenue': '1'},
    {'all_split_entities_revenue': '10000000000'}, {'tax_after_other_incentives': -1}])
def test_company_reduction_rejects_unverified_or_inconsistent_facts(changes):
    with pytest.raises(ValueError): company_reduction(**changes)


@pytest.mark.parametrize('changes', [
    {'resident': None}, {'business_income_only_confirmed': False},
    {'statutory_revenue_scope_confirmed': False}, {'tax_year': 2028},
    {'annual_actual_business_revenue': None}, {'business_income_tax': 1.0}])
def test_personal_reduction_requires_resident_business_scope(changes):
    with pytest.raises(ValueError): personal_reduction(**changes)
