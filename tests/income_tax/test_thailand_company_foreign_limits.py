from decimal import Decimal

import pytest

from packages.income_tax.thailand_company_foreign_limits import calculate


def workpaper(*countries):
    return dict(countries=list(countries), ordinary_twenty_percent_rate_verified=True,
        thai_law_bases_period_fx_and_paid_tax_evidence_verified=True)


def mixed(**changes):
    return dict(country='sg', treatment='mixed_combined', business_revenue='1000000',
        business_allowable_expenses='800000', company_receipts='100000',
        business_foreign_tax_paid='100000', company_receipt_foreign_tax_paid='10000', **changes)


def test_clause4_combined_and_separate_produce_different_limits():
    combined = calculate(workpaper(mixed()))
    source = mixed()
    source.update(treatment='mixed_separate',
        separate_receipts_excluded_from_foreign_annual_tax_verified=True)
    separate = calculate(workpaper(source))
    assert combined['credit_before_annual_reconciliation'] == Decimal('60000')
    assert separate['credit_before_annual_reconciliation'] == Decimal('50000')
    assert not separate['annual_settlement_supported']
    assert 'final_tax' not in separate


def test_countries_do_not_pool_unused_limits_and_excess_is_not_forfeited():
    result = calculate(workpaper(
        dict(country='sg', treatment='company_receipts', company_receipts='100000',
             company_receipt_foreign_tax_paid='30000'),
        dict(country='jp', treatment='company_receipts', company_receipts='100000',
             company_receipt_foreign_tax_paid='1000')))
    assert result['credit_before_annual_reconciliation'] == Decimal('21000')
    assert result['countries'][0]['parts'][0]['excess_before_expense_reconciliation'] == 10000


def test_foreign_business_loss_has_zero_limit():
    result = calculate(workpaper(dict(country='sg', treatment='business_net',
        business_revenue='100', business_allowable_expenses='200', business_foreign_tax_paid='5')))
    assert result['credit_before_annual_reconciliation'] == 0
    assert result['countries'][0]['parts'][0]['basis'] == -100


@pytest.mark.parametrize('changes', [
    dict(country='th'),
    dict(treatment='mixed_separate'),
    dict(separate_receipts_excluded_from_foreign_annual_tax_verified=True),
    dict(treatment='business_net'),
    dict(treatment='company_receipts'),
    dict(business_foreign_tax_paid='-1'),
])
def test_invalid_or_unverified_classification_rejected(changes):
    source = mixed()
    source.update(changes)
    with pytest.raises(ValueError):
        calculate(workpaper(source))


def test_duplicate_country_and_unverified_rate_rejected():
    with pytest.raises(ValueError):
        calculate(workpaper(mixed(), mixed()))
    p = workpaper(mixed())
    p['ordinary_twenty_percent_rate_verified'] = False
    with pytest.raises(ValueError):
        calculate(p)


def test_gross_receipt_method_rejects_silent_expense_deduction():
    with pytest.raises(ValueError):
        calculate(workpaper(dict(country='sg', treatment='company_receipts',
            company_receipts='100', company_receipt_allowable_expenses='20')))
