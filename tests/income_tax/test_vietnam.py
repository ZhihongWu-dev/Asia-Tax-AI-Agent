from decimal import Decimal
import pytest
from packages.income_tax.vietnam import company_tax


def compute(**changes):
    facts = dict(taxable_income='1000000000', tax_year=2026, vietnam_established=True, new_in_current_period=False,
        previous_period_revenue='4000000000', previous_active_months=12,
        current_period_statutory_revenue='10000000000',
        exemption_related_enterprise_disqualified=False, reduced_rate_related_enterprise_disqualified=False,
        formed_by_split_after_resolution=False, all_split_entities_revenue=None,
        other_incentive_reduction='20000000', prepaid_tax='150000000',
        ordinary_domestic_income_confirmed=True, statutory_revenue_scope_confirmed=True,
        other_incentives_verified=True)
    facts.update(changes)
    return company_tax(**facts)


def test_company_sequence_and_prepayment_not_in_relief_base():
    r = compute()
    assert r['rate'] == Decimal('.17')
    assert r['gross_tax'] == 170000000
    assert r['annual_reduction'] == 45000000
    assert r['final_tax'] == 105000000
    assert r['balance_due'] == -45000000
    assert compute(prepaid_tax='0')['final_tax'] == r['final_tax']


def test_company_provenance_includes_amendments_without_claiming_registration():
    sources = compute()['sources']
    assert {s['doc_id'] for s in sources} == {'vn.law.cit67.2025.vi',
        'vn.law09.2026.vi', 'vn.decree320.2025.vi', 'vn.decree141.2026.vi',
        'vn.decree398.2026.vi'}
    assert all(s['registration_status'] == 'pending' for s in sources)
    assert all(len(s['sha256']) == 64 and s['url'].startswith('https://') for s in sources)
    sources[0]['provisions'].clear()
    assert compute()['sources'][0]['provisions']


def test_fractional_base_preserves_intermediate_tax_without_rounding():
    r = compute(taxable_income='123456789.123456', other_incentive_reduction='0', prepaid_tax='0')
    assert r['gross_tax'] == Decimal('20987654.15098752')
    assert r['annual_reduction'] == Decimal('6296296.245296256')
    assert r['final_tax'] == Decimal('14691357.905691264')


def test_prior_revenue_exemption_separate_from_current_reduction_revenue():
    r = compute(previous_period_revenue='1000000000', other_incentive_reduction='0')
    assert r['exemption_eligibility']['eligible']
    assert r['final_tax'] == 0 and r['balance_due'] == -150000000
    r = compute(current_period_statutory_revenue='10000000001')
    assert r['rate'] == Decimal('.17') and r['annual_reduction'] == 0
    assert r['final_tax'] == 150000000


def test_different_relationship_thresholds_are_preserved():
    r = compute(previous_period_revenue='1000000000',
        exemption_related_enterprise_disqualified=True, other_incentive_reduction='0')
    assert not r['exemption_eligibility']['eligible']
    assert r['rate'] == Decimal('.15') and r['final_tax'] == 105000000


def test_new_company_and_split_aggregation():
    r = compute(new_in_current_period=True, previous_period_revenue=None,
        previous_active_months=None, current_period_statutory_revenue='2000000000',
        formed_by_split_after_resolution=True, all_split_entities_revenue='11000000000',
        other_incentive_reduction='0')
    assert r['rate'] == Decimal('.15') and r['annual_reduction'] == 0
    assert r['final_tax'] == 150000000


@pytest.mark.parametrize('changes', [
    {'vietnam_established': False}, {'vietnam_established': None},
    {'ordinary_domestic_income_confirmed': False}, {'other_incentives_verified': False},
    {'statutory_revenue_scope_confirmed': False}, {'other_incentive_reduction': '170000001'},
    {'previous_period_revenue': '1000000000'},
    {'reduced_rate_related_enterprise_disqualified': True},
    {'current_period_statutory_revenue': '0'}, {'tax_year': 2027},
    {'exemption_related_enterprise_disqualified': None}])
def test_unverified_and_contradictory_facts_fail(changes):
    with pytest.raises(ValueError): compute(**changes)
