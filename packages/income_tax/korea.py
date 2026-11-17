"""Korean national/local statutory gross schedules; not a final assessment.

Bases must be separately established. Credits, minimum/additional taxes,
municipal treatment, rounding and special income still need assessment logic.
No API policy is enabled by this module.
"""
from decimal import Decimal
from copy import deepcopy
import json
from pathlib import Path

from .arithmetic import Band, marginal_tax
from .korea_rounding import taxable_base_won

_SOURCES = json.loads(Path(__file__).with_name('kr_2026_sources.json').read_text(encoding='utf-8'))


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


def company_minimum_reference(restored_taxable_base, *, tax_year, regime,
        annual_applicability_and_restoration_confirmed):
    """Article132(1) national reference amount, not final tax or a new tax base.

The supplied base restores the specified deductions/exclusions under Article132.
SME graduation categories require established statutory eligibility and dates;
they are not inferred from company age. Excluded cooperatives and short periods
need separate treatment. Relief limits and post-comparison credits follow later.
"""
    if type(tax_year) is not int or tax_year != 2026:
        raise ValueError('Only 2026 has been reviewed')
    if annual_applicability_and_restoration_confirmed is not True:
        raise ValueError('Annual applicability and statutory base restoration must be verified')
    flat_rates = {'sme': '.07', 'graduated_first_three_years': '.08',
                  'graduated_next_two_years': '.09'}
    if regime == 'general':
        schedule = _schedule([('10000000000','.10'),('100000000000','.12'),(None,'.17')])
    elif isinstance(regime,str) and regime in flat_rates:
        schedule = _schedule([(None,flat_rates[regime])])
    else:
        raise ValueError('Verified statutory minimum-tax regime required')
    restored_taxable_base = taxable_base_won(restored_taxable_base)
    reference,bands = marginal_tax(restored_taxable_base,schedule)
    return dict(currency='KRW',tax_year=tax_year,regime=regime,
        restored_taxable_base=restored_taxable_base,
        minimum_reference_tax=reference,bands=bands,
        sources=deepcopy(_SOURCES['corporate_minimum'] + _SOURCES['rounding'][:1]),
        stage='national_minimum_reference_before_relief_limitation_and_excluded_credits')


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
    national_taxable_base = taxable_base_won(national_taxable_base)
    local_taxable_base = taxable_base_won(local_taxable_base)
    national_tax, national_bands = marginal_tax(national_taxable_base,national)
    local_tax, local_bands = marginal_tax(local_taxable_base,local)
    return dict(currency='KRW',tax_year=tax_year,subject=subject,
        sources=deepcopy(_SOURCES[subject] + _SOURCES['rounding']),
        national_taxable_base=national_taxable_base,local_taxable_base=local_taxable_base,
        national_gross_tax=national_tax,local_gross_tax=local_tax,
        national_bands=national_bands,local_bands=local_bands,
        stage='gross_schedules_before_credits_minimum_additional_tax_and_rounding')
