"""Section41/P161/P162 applicability for individually traced foreign income.

This component determines inclusion before exemptions, deductions, treaty relief
or foreign tax credits. It must not be presented as a final tax assessment.
"""
from calendar import isleap
from datetime import date

from .arithmetic import ZERO, amount


def classify_remittance(remitted_income, *, income_date, remittance_date,
                        days_in_thailand_in_income_year, tax_year,
                        foreign_income_and_tracing_verified):
    """Classify a traced income portion remitted in calendar2026, in THB.

The amount is the income portion, not an unclassified bank transfer (which may
contain capital). Residency is tested in the income year. No special exemption
or treaty entitlement is inferred from an excluded/included classification.
"""
    if type(tax_year) is not int or tax_year != 2026:
        raise ValueError('This policy covers remittances in tax year2026 only')
    if type(income_date) is not date or type(remittance_date) is not date:
        raise ValueError('Provide exact income and remittance dates')
    if remittance_date.year != tax_year or income_date > remittance_date:
        raise ValueError('Remittance must be in the assessment year and follow income')
    days = days_in_thailand_in_income_year
    if type(days) is not int or not 0 <= days <= 365 + int(isleap(income_date.year)):
        raise ValueError('Income-year presence must be a valid whole-day count')
    if foreign_income_and_tracing_verified is not True:
        raise ValueError('Verify foreign source, income character and remittance tracing')
    value = amount(remitted_income)
    if income_date < date(2024, 1, 1):
        reason = 'pre_2024_income_excluded_from_p161'
        included = ZERO
    elif days < 180:
        reason = 'not_resident_in_income_year'
        included = ZERO
    else:
        reason = 'resident_income_remitted_in_assessment_year'
        included = value
    return dict(tax_year=tax_year, currency='THB', income_date=income_date,
                remittance_date=remittance_date, income_year=income_date.year,
                income_year_presence_days=days, remitted_income=value,
                included_before_relief= included, excluded_from_section41_remittance=value-included,
                reason=reason, stage='remittance_inclusion_before_reliefs_and_tax',
                sources=[
                    'https://www.rd.go.th/5937.html',
                    'https://www.rd.go.th/fileadmin/user_upload/kormor/newlaw/dn161A.pdf',
                    'https://www.rd.go.th/fileadmin/user_upload/kormor/newlaw/dn162A.pdf'])
