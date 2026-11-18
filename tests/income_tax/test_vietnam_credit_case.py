from copy import deepcopy
from decimal import Decimal

import pytest

from packages.income_tax.vietnam_credit_case import credit_workpaper


def inputs():
    case = dict(subject='company', jurisdiction='vn', currency='VND', residency='resident',
        period_start='2026-01-01', period_end='2026-12-31', claimed_deductions='0',
        carried_losses='0', facts_confirmed=True, incomes=[
            dict(category='business', source_jurisdiction='vn', gross_amount='2000', description='Domestic'),
            dict(category='dividend', source_jurisdiction='id', gross_amount='1000', foreign_tax_paid='50', description='Indonesia'),
            dict(category='royalty', source_jurisdiction='sg', gross_amount='1000', foreign_tax_paid='50', description='Singapore'),
            dict(category='dividend', source_jurisdiction='hk', gross_amount='80', foreign_tax_paid='0', description='Hong Kong')])
    common = dict(vietnam_tax_limit='200', treaty_and_same_income_basis_verified=True,
                  basis_explanation='Verified treaty eligibility and the tax attributable to this income.')
    lines = [dict(common, income_index=1, method='indonesia_deemed'),
             dict(common, income_index=2, method='singapore_interest_royalty', eligible_singapore_tax_paid='50'),
             dict(common, income_index=3, method='underlying_dividend', qualifying_holding_percent='10',
                  distributing_profit_after_tax='800', corporate_tax_paid_on_profit='200',
                  corporate_recipient_and_pool_verified=True, vietnam_tax_limit='20')]
    return case, lines


def test_mixed_saved_incomes_keep_gross_amounts_and_tax_components_separate():
    case, lines = inputs()
    original = deepcopy((case, lines))
    result = credit_workpaper(case, lines)
    assert result['assessed_credit_subtotal'] == 270
    assert [row['credit'] for row in result['items']] == [150, 100, 20]
    assert result['items'][0]['calculation']['gross_income'] == 1000  # not1050
    assert result['all_foreign_items_assessed']
    assert result['unassessed_foreign_income_indexes'] == []
    assert 'final_tax' not in result
    assert (case, lines) == original


def test_partial_workpaper_explicitly_identifies_unassessed_income():
    case, lines = inputs()
    result = credit_workpaper(case, lines[:1])
    assert result['assessed_credit_subtotal'] == 150
    assert not result['all_foreign_items_assessed']
    assert result['unassessed_foreign_income_indexes'] == [2, 3]


@pytest.mark.parametrize('change', ['duplicate', 'domestic', 'outside', 'country', 'category',
    'paid', 'shareholder_tax', 'confirmed', 'resident', 'individual', 'period', 'missing_tax'])
def test_wrong_income_binding_or_unconfirmed_case_rejected(change):
    case, lines = inputs()
    if change=='duplicate': lines.append(deepcopy(lines[0]))
    elif change=='domestic': lines[0]['income_index']=0
    elif change=='outside': lines[0]['income_index']=10
    elif change=='country': case['incomes'][1]['source_jurisdiction']='my'
    elif change=='category': case['incomes'][1]['category']='business'
    elif change=='paid': lines[1]['eligible_singapore_tax_paid']='51'
    elif change=='shareholder_tax': case['incomes'][3]['foreign_tax_paid']='1'
    elif change=='confirmed': lines[0]['treaty_and_same_income_basis_verified']=False
    elif change=='resident': case['residency']='nonresident'
    elif change=='individual': case['subject']='individual'
    elif change=='period': case['period_start']='2025-01-01'
    elif change=='missing_tax': case['incomes'][1]['foreign_tax_paid']=None
    with pytest.raises(ValueError):
        credit_workpaper(case, lines)


def test_fractional_underlying_tax_is_not_reparsed_as_external_money():
    case, lines = inputs()
    case['incomes'][3]['gross_amount']='1'
    lines[2].update(distributing_profit_after_tax='3', corporate_tax_paid_on_profit='1')
    result = credit_workpaper(case, lines[2:])
    assert result['assessed_credit_subtotal'] == Decimal('0.'+'3'*40)
