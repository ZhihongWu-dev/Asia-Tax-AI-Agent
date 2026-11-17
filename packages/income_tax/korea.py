"""Korean national/local statutory gross schedules; not a final assessment.

Bases must be separately established. Credits, minimum/additional taxes,
municipal treatment, rounding and special income still need assessment logic.
No API policy is enabled by this module.
"""
from decimal import Decimal

from .arithmetic import Band, marginal_tax


def _schedule(rows):
    return tuple(Band(None if cap is None else Decimal(cap), Decimal(rate)) for cap, rate in rows)


COMPANY = _schedule([('200000000','.10'),('20000000000','.20'),
    ('300000000000','.22'),(None,'.25')])
COMPANY_60_2 = _schedule([('20000000000','.20'),('300000000000','.22'),(None,'.25')])
PERSONAL = _schedule([('14000000','.06'),('50000000','.15'),('88000000','.24'),
    ('150000000','.35'),('300000000','.38'),('500000000','.40'),
    ('1000000000','.42'),(None,'.45')])
# Separate statutory schedules: local tax is not a percentage of national net tax.
LOCAL_COMPANY = _schedule([('200000000','.010'),('20000000000','.020'),
    ('300000000000','.022'),(None,'.025')])
LOCAL_COMPANY_60_2 = _schedule([('20000000000','.020'),('300000000000','.022'),(None,'.025')])
LOCAL_PERSONAL = _schedule([('14000000','.006'),('50000000','.015'),('88000000','.024'),
    ('150000000','.035'),('300000000','.038'),('500000000','.040'),
    ('1000000000','.042'),(None,'.045')])


def gross_taxes(national_taxable_base, local_taxable_base, *, tax_year, subject,
        article60_2_1_1_company, annual_standard_schedule_confirmed):
    """Apply annual standard schedules to verified bases, before tax adjustments.

The company exception is the specified Article60-2(1)(1) category, not every
small company or every corporation submitting a verification report.
Personal inputs are comprehensive-income bases, not retirement/capital gains.
"""
    if type(tax_year) is not int or tax_year != 2026:
        raise ValueError('Only 2026 schedules have been reviewed')
    if annual_standard_schedule_confirmed is not True:
        raise ValueError('Annual standard schedule applicability must be confirmed')
    if subject == 'company':
        if type(article60_2_1_1_company) is not bool:
            raise ValueError('Article60-2(1)(1) classification must be explicit')
        national, local = ((COMPANY_60_2,LOCAL_COMPANY_60_2) if article60_2_1_1_company
            else (COMPANY,LOCAL_COMPANY))
    elif subject == 'individual':
        if article60_2_1_1_company is not None:
            raise ValueError('Company classification is inapplicable to an individual')
        national, local = PERSONAL, LOCAL_PERSONAL
    else:
        raise ValueError('Unknown taxpayer subject')
    national_tax, national_bands = marginal_tax(national_taxable_base,national)
    local_tax, local_bands = marginal_tax(local_taxable_base,local)
    return dict(currency='KRW',tax_year=tax_year,subject=subject,
        national_gross_tax=national_tax,local_gross_tax=local_tax,
        national_bands=national_bands,local_bands=local_bands,
        stage='gross_schedules_before_credits_minimum_additional_tax_and_rounding')
