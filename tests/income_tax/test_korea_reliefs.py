from decimal import Decimal

import pytest

from packages.income_tax.korea_reliefs import CompanyRelief, allocate_company_reliefs


def calculate(gross, minimum, lots, **changes):
    facts = dict(tax_year=2026, eligibility_caps_and_expiry_verified=True,
                 no_base_changing_incentives=True)
    facts.update(changes)
    return allocate_company_reliefs(gross, minimum, lots, **facts)


def lot(identifier, value, category='reduction', year=2026, subject=True):
    return CompanyRelief(identifier, value, category, year, subject)


def test_minimum_subject_reliefs_first_then_exempt_relief_can_go_below_minimum():
    result = calculate(100, 70, [lot('exempt', 20, subject=False), lot('limited', 50)])
    assert [r['identifier'] for r in result['reliefs']] == ['limited', 'exempt']
    assert [r['used'] for r in result['reliefs']] == [30, 20]
    assert result['tax_after_reliefs'] == 50
    assert result['reliefs'][0]['unused'] == 20


def test_minimum_reference_never_increases_gross_tax_by_itself():
    assert calculate(50, 70, [])['tax_after_reliefs'] == 50
    result = calculate(50, 70, [lot('limited', 20), lot('exempt', 10, subject=False)])
    assert result['tax_after_reliefs'] == 40
    assert result['reliefs'][0]['used'] == 0


def test_statutory_order_and_oldest_carryforward_are_independent_of_input_order():
    lots = [lot('special', 30, 'article58_3_credit'), lot('new', 20, 'carry_credit'),
            lot('old', 20, 'carry_credit', 2024), lot('reduction', 10),
            lot('noncarry', 20, 'noncarry_credit')]
    result = calculate(70, 0, lots)
    assert [r['identifier'] for r in result['reliefs']] == ['reduction', 'noncarry', 'old', 'new', 'special']
    assert [r['used'] for r in result['reliefs']] == [10, 20, 20, 20, 0]
    assert result['tax_after_reliefs'] == 0


def test_excess_relief_does_not_create_refund_or_assume_carryforward():
    result = calculate('10.25', 0, [lot('credit', '20.5', 'carry_credit')])
    assert result['tax_after_reliefs'] == 0
    assert result['reliefs'][0]['unused'] == Decimal('10.25')
    assert 'carryforward' not in result['reliefs'][0]


@pytest.mark.parametrize('changes', [dict(tax_year=True), dict(tax_year=2025),
    dict(eligibility_caps_and_expiry_verified=False), dict(no_base_changing_incentives=False)])
def test_unverified_or_base_changing_incentives_rejected(changes):
    with pytest.raises(ValueError): calculate(100, 70, [], **changes)


@pytest.mark.parametrize('lots', [[lot('x', 1), lot('x', 2)], [lot('', 1)],
    [lot('x', True)], [lot('x', '-1')], [lot('x', 1, 'other')],
    [lot('x', 1, year=2025)], [lot('x', 1, year=True)],
    [lot('x', 1, 'carry_credit', 2027)], [lot('x', 1, subject=1)], [{}]])
def test_invalid_lots_rejected(lots):
    with pytest.raises(ValueError): calculate(100, 70, lots)
