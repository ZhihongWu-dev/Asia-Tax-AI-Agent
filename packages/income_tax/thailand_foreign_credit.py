"""Thai foreign-tax attribution before treaty entitlement and credit limits.

RD November2025 manual, Part1 item1.2 (PDF page19): attribute tax paid on
one foreign income pool to the portion remitted. Inputs are consistently
converted THB amounts for the same country, income type and earnings pool.
This arithmetic does not establish that the resulting tax is creditable.
"""
from decimal import localcontext

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
