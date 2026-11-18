"""Thai foreign-tax attribution before treaty entitlement and credit limits.

RD November2025 manual, Part1 item1.2 (PDF page19): attribute tax paid on
one foreign income pool to the portion remitted. Inputs are consistently
converted THB amounts for the same country, income type and earnings pool.
This arithmetic does not establish that the resulting tax is creditable.
"""
from decimal import localcontext
import re

from .arithmetic import amount


SOURCE = 'https://www.rd.go.th/fileadmin/user_upload/porphor/GuideTaxFromAbroad_EN.pdf'


def attribute_remitted_tax(*, total_foreign_income, foreign_income_tax_paid,
                           remitted_income, tax_year, source_and_fx_verified):
    """Return Part1 G/H, without pooling countries or deciding final credit.

    Tax paid must exclude penalties and non-income taxes. The caller must
    establish source, earnings-pool tracing, tax-payment evidence and a
    consistent permitted remittance-date exchange rate. A saved remitted
    income amount alone is not a valid substitute for total foreign earnings.
    """
    if type(tax_year) is not int or tax_year != 2026:
        raise ValueError('This policy covers tax year2026 only')
    if source_and_fx_verified is not True:
        raise ValueError('Verify income pool, paid income tax, remittance tracing and FX basis')
    income, paid, remitted = map(amount, (total_foreign_income, foreign_income_tax_paid, remitted_income))
    if income == 0 or remitted > income:
        raise ValueError('Foreign earnings must be positive and cover the remitted income')
    with localcontext() as context:
        context.prec = 40
        # Multiply first to avoid rounding the remittance fraction prematurely.
        attributable = remitted * paid / income
        return dict(tax_year=tax_year, currency='THB',
                    total_foreign_income=income, foreign_income_tax_paid=paid,
                    remitted_income=remitted,
                    remitted_percentage=remitted * 100 / income,
                    foreign_tax_attributable_to_remittance=attributable,
                    stage='foreign_tax_attribution_before_entitlement_and_credit_limit',
                    sources=[SOURCE])


def country_credit_limits(countries, *, domestic_assessable_income,
                          thai_tax_before_foreign_credit, tax_year,
                          entitlement_and_basis_verified):
    """Apply Part3 limits to already reviewed country totals, before rounding.

    Every foreign assessable receipt belongs in a country's remitted income,
    including receipts without credit entitlement. eligible_attributable_tax
    must already exclude tax beyond treaty taxing rights, non-income taxes,
    penalties and tax on excluded income. This function does not infer that
    eligibility or calculate taxable income/expenses from gross receipts.
    """
    if type(tax_year) is not int or tax_year != 2026:
        raise ValueError('This policy covers tax year2026 only')
    if entitlement_and_basis_verified is not True:
        raise ValueError('Verify treaty entitlement, source tax caps and complete assessable income')
    if not isinstance(countries, (list, tuple)) or not 1 <= len(countries) <= 250:
        raise ValueError('Provide complete foreign-country totals')
    domestic, thai_tax = map(amount, (domestic_assessable_income, thai_tax_before_foreign_credit))
    seen, inputs = set(), []
    for row in countries:
        if not isinstance(row, dict) or set(row) != {'country', 'remitted_assessable_income', 'eligible_attributable_tax'}:
            raise ValueError('Each country requires remitted assessable income and eligible attributable tax')
        country = row['country']
        if not isinstance(country, str) or not re.fullmatch('[a-z]{2}', country) or country == 'th' or country in seen:
            raise ValueError('Use distinct foreign-country codes')
        seen.add(country)
        income, paid = map(amount, (row['remitted_assessable_income'], row['eligible_attributable_tax']))
        if income == 0 and paid != 0:
            raise ValueError('Credit requires attributable assessable income')
        inputs.append((country, income, paid))
    with localcontext() as context:
        context.prec = 40
        total = domestic + sum((income for _, income, _ in inputs), amount(0))
        if total == 0 and thai_tax != 0:
            raise ValueError('Tax cannot be allocated without assessable income')
        output = []
        for country, income, paid in sorted(inputs):
            limit = income * thai_tax / total if total else amount(0)
            allowed = min(paid, limit)
            output.append(dict(country=country, remitted_assessable_income=income,
                               eligible_attributable_tax=paid, credit_limit=limit,
                               allowable_foreign_credit=allowed, unused_foreign_tax=paid-allowed))
        return dict(tax_year=tax_year, currency='THB', countries=output,
                    total_assessable_income=total, domestic_assessable_income=domestic,
                    thai_tax_before_foreign_credit=thai_tax,
                    allowable_foreign_credit=sum((r['allowable_foreign_credit'] for r in output), amount(0)),
                    stage='reviewed_country_credit_limits_before_rounding_and_settlement',
                    sources=[SOURCE, 'https://www.rd.go.th/fileadmin/user_upload/porphor/GuideTaxFromAbroad_TH.pdf'])
