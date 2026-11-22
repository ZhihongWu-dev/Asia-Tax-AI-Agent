from copy import deepcopy
import pytest
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.korea_foreign_reconciliation import reconcile
from packages.income_tax.korea_foreign_credit import calculate


def fixture():
    case = dict(subject='company', jurisdiction='kr', currency='KRW', residency='resident',
        period_start='2026-01-01', period_end='2026-12-31', facts_confirmed=True,
        claimed_deductions='200', carried_losses='0', incomes=[
            dict(category='business', source_jurisdiction='kr', gross_amount='600', description='Domestic'),
            dict(category='business', source_jurisdiction='sg', gross_amount='600', foreign_tax_paid='150', description='Foreign')])
    p = dict(groups=[dict(source_id='home', income_indexes=[0], expenses_already_in_foreign_income='0',
        corresponding_expenses='0', eligible_direct_foreign_tax='0'),
        dict(source_id='abroad', income_indexes=[1], expenses_already_in_foreign_income='100',
        corresponding_expenses='100', eligible_direct_foreign_tax='150')],
        korean_income_basis_and_expense_classification_verified=True,
        direct_paid_tax_treaty_fx_and_filing_evidence_verified=True,
        no_losses_exemptions_special_income_or_other_base_adjustments_verified=True)
    return case, p


def test_saved_expenses_reconcile_to_credit_and_carry_without_double_deduction():
    case, p = fixture()
    r = reconcile(IncomeTaxCase.model_validate(case), p)
    assert r['national_taxable_base'] == 1000
    c = calculate(dict(countries=r['countries'], resident_company_and_direct_tax_scope_verified=True,
        country_income_expenses_and_relief_allocations_verified=True,
        treaty_caps_payment_fx_and_filing_evidence_verified=True,
        no_prior_credits_other_reliefs_or_source_losses_verified=True),
        national_tax_before_credit=200, national_taxable_base=r['national_taxable_base'])
    row = c['country_credits'][0]
    assert row['current_foreign_tax_credit'] == 80
    assert row['expense_related_excess_not_carried'] == 20
    assert row['eligible_current_year_carryforward'] == 50


def test_multiple_sources_aggregate_once_per_country():
    case, p = fixture()
    extra = deepcopy(case['incomes'][1])
    extra.update(gross_amount='200', foreign_tax_paid='20')
    case['incomes'].append(extra)
    p['groups'].append(dict(source_id='second', income_indexes=[2], expenses_already_in_foreign_income='0',
        corresponding_expenses='0', eligible_direct_foreign_tax='20'))
    r = reconcile(IncomeTaxCase.model_validate(case), p)
    assert r['national_taxable_base'] == 1200
    assert len(r['countries']) == 1
    assert r['countries'][0]['eligible_direct_foreign_tax'] == 170
    assert r['countries'][0]['foreign_income_before_corresponding_expenses'] == 700


@pytest.mark.parametrize('change', ['duplicate', 'missing', 'negative_index', 'duplicate_id', 'expenses',
    'eligible', 'missing_paid', 'domestic_paid', 'domestic_expenses', 'mixed_country', 'dividend',
    'loss', 'period', 'resident', 'unconfirmed', 'evidence'])
def test_inconsistent_saved_facts_cannot_reach_credit_calculation(change):
    case, p = fixture()
    g = p['groups'][1]
    if change == 'duplicate': g['income_indexes'] = [1, 1]
    elif change == 'missing': p['groups'] = [g]
    elif change == 'negative_index': g['income_indexes'] = [-1]
    elif change == 'duplicate_id': g['source_id'] = ' home '
    elif change == 'expenses': g['corresponding_expenses'] = '101'
    elif change == 'eligible': g['eligible_direct_foreign_tax'] = '151'
    elif change == 'missing_paid': case['incomes'][1].pop('foreign_tax_paid')
    elif change == 'domestic_paid': case['incomes'][0]['foreign_tax_paid'] = '1'
    elif change == 'domestic_expenses':
        p['groups'][0]['corresponding_expenses'] = '100'
        g['corresponding_expenses'] = '0'
    elif change == 'mixed_country':
        g['income_indexes'] = [0, 1]
        p['groups'] = [g]
    elif change == 'dividend': case['incomes'][1]['category'] = 'dividend'
    elif change == 'loss': case['incomes'][1]['gross_amount'] = '199'
    elif change == 'period': case['period_start'] = '2026-02-01'
    elif change == 'resident': case['residency'] = 'nonresident'
    elif change == 'unconfirmed': case['facts_confirmed'] = False
    else: p['direct_paid_tax_treaty_fx_and_filing_evidence_verified'] = False
    with pytest.raises(ValueError):
        reconcile(IncomeTaxCase.model_validate(case), p)
