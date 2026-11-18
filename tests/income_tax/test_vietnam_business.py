from decimal import Decimal, localcontext

import pytest

from packages.income_tax.vietnam_business import resident_business_tax


def activity(revenue, category='goods', deduction=0):
    return dict(category=category, revenue=revenue, allocated_revenue_deduction=deduction)


def assess(**changes):
    args = dict(tax_year=2026, resident=True, method='revenue',
        activities=[activity(2000000000, deduction=1000000000)],
        all_annual_business_revenue=2000000000, deductible_expenses=None,
        prepaid_tax=0, ordinary_domestic_business_verified=True,
        revenue_and_expense_evidence_verified=True,
        method_election_and_continuity_verified=True,
        revenue_method_started_within_limit=True)
    args.update(changes)
    return resident_business_tax(**args)


def test_amended_threshold_and_overpayment():
    result = assess(activities=[activity(1000000000)],
        all_annual_business_revenue=1000000000, prepaid_tax=12345)
    assert result['final_tax'] == 0
    assert result['balance_due'] == -12345
    result = assess(activities=[activity(1000000001, deduction=1000000000)],
        all_annual_business_revenue=1000000001)
    assert result['final_tax'] == Decimal('.0035')


def test_mixed_categories_share_one_explicit_allowance():
    result = assess(activities=[activity(800000000, 'digital_content', 800000000),
        activity(1200000000, 'goods', 200000000)])
    assert result['tax_before_relief'] == 5000000
    assert result['annual_reduction'] == 1500000
    assert result['final_tax'] == 3500000
    with pytest.raises(ValueError, match='shared'):
        assess(activities=[activity(1000000000, 'goods', 1000000000),
            activity(1000000000, 'digital_content', 1000000000)])


@pytest.mark.parametrize('category,expected', [
    ('goods', 3500000), ('services_without_materials', 14000000),
    ('asset_rental_or_specified_agency', 35000000),
    ('production_transport_with_materials', 10500000),
    ('digital_content', 35000000), ('other_business', 7000000)])
def test_annex_category_rates(category, expected):
    assert assess(activities=[activity(2000000000, category, 1000000000)])['final_tax'] == expected


@pytest.mark.parametrize('revenue,rate,relief', [
    (3000000000, '.15', '.30'), (3000000001, '.17', '.30'),
    (10000000000, '.17', '.30'), (10000000001, '.17', '0'),
    (50000000000, '.17', '0'), (50000000001, '.20', '0')])
def test_profit_and_reduction_boundaries(revenue, rate, relief):
    result = assess(method='profit', revenue_method_started_within_limit=False,
        activities=[activity(revenue)], all_annual_business_revenue=revenue,
        deductible_expenses=revenue-1000000)
    assert result['rate'] == Decimal(rate)
    assert result['reduction_rate'] == Decimal(relief)
    assert result['final_tax'] == Decimal(1000000)*Decimal(rate)*(1-Decimal(relief))


def test_crossing_revenue_method_limit_is_not_a_retroactive_method_change():
    result = assess(activities=[activity(4000000000, deduction=1000000000)],
        all_annual_business_revenue=4000000000)
    assert result['next_year_profit_method_required'] is True
    assert result['final_tax'] == 10500000
    with pytest.raises(ValueError, match='eligibility'):
        assess(revenue_method_started_within_limit=False)


def test_profit_loss_has_no_negative_tax_and_reconciles_prepayment():
    result = assess(method='profit', revenue_method_started_within_limit=False,
        activities=[activity(2000000000)], deductible_expenses=2100000000,
        prepaid_tax=1000000)
    assert result['taxable_base'] == 0
    assert result['final_tax'] == 0
    assert result['balance_due'] == -1000000


@pytest.mark.parametrize('changes', [
    {'tax_year': 2027}, {'resident': False}, {'resident': 1},
    {'method_election_and_continuity_verified': False},
    {'ordinary_domestic_business_verified': None},
    {'revenue_and_expense_evidence_verified': 1},
    {'activities': []}, {'activities': [activity(2000000000, 'property_rental')]},
    {'activities': [activity(2000000000.0)]}, {'prepaid_tax': 'NaN'},
    {'all_annual_business_revenue': 1999999999}, {'deductible_expenses': 0},
    {'activities': [activity(1000000000, deduction=1000000001)]},
])
def test_invalid_or_unverified_inputs_do_not_produce_a_result(changes):
    with pytest.raises(ValueError):
        assess(**changes)


def test_precision_and_source_snapshots_are_isolated():
    expected = assess()
    with localcontext() as ctx:
        ctx.prec = 5
        assert assess() == expected
    expected['sources'][0]['provisions'].append('untrusted')
    assert 'untrusted' not in assess()['sources'][0]['provisions']
