"""China 2026 domestic normal-rate arithmetic with explicit tax-basis inputs.

These functions do not determine residency, incentive eligibility, treaty relief,
foreign tax credits or the deductibility of claimed expenses. They are building
blocks for the country workflow, not a completed return or filing instruction.
"""
from decimal import Decimal, localcontext
from copy import deepcopy
import json
from pathlib import Path
from .arithmetic import Band, ZERO, amount, marginal_tax

POLICY_VERSION = 'cn-2026-2026-11-16'
SOURCE_MANIFEST = json.loads(Path(__file__).with_name('cn_2026_sources.json').read_text(encoding='utf-8'))
SOURCE_BY_ID = {source['doc_id']: source for source in SOURCE_MANIFEST['sources']}
COMPREHENSIVE_BANDS = tuple(Band(None if cap is None else Decimal(cap), Decimal(rate))
    for cap, rate in [('36000', '.03'), ('144000', '.10'), ('300000', '.20'),
                      ('420000', '.25'), ('660000', '.30'), ('960000', '.35'), (None, '.45')])


def check_year(tax_year):
    if type(tax_year) is not int or tax_year != 2026:
        raise ValueError('This policy is verified only for tax year 2026')


def resident_comprehensive_tax(*, tax_year, wages, service_remuneration, author_remuneration,
                               royalties, allowed_special_deductions, allowed_additional_deductions,
                               allowed_other_deductions, allowed_donations, allowed_tax_reductions,
                               prepaid_tax, domestic_normal_treatment_confirmed):
    """Annual comprehensive income only, excluding separately taxed bonus/equity schemes.

All amounts must already be in CNY. Deduction/reduction inputs are approved
amounts, not user claims. Do not feed dividends or business income into this
schedule. Foreign-source relief and nonresident monthly withholding are separate.
"""
    check_year(tax_year)
    if domestic_normal_treatment_confirmed is not True:
        raise ValueError('Domestic resident normal comprehensive treatment must be confirmed')
    wages, services, authors, royalties = map(amount, (wages, service_remuneration, author_remuneration, royalties))
    special, additional, other, donations, reduction, prepaid = map(amount, (
        allowed_special_deductions, allowed_additional_deductions, allowed_other_deductions,
        allowed_donations, allowed_tax_reductions, prepaid_tax))
    with localcontext() as ctx:
        ctx.prec = 40
        assessable = wages + services * Decimal('.8') + authors * Decimal('.56') + royalties * Decimal('.8')
        before_donations = max(ZERO, assessable - Decimal('60000') - special - additional - other)
        if donations > before_donations:
            raise ValueError('Allowed donations exceed the remaining income basis')
        taxable = before_donations - donations
        tax, bands = marginal_tax(taxable, COMPREHENSIVE_BANDS)
        if reduction > tax:
            raise ValueError('Allowed reductions exceed gross tax')
        liability = tax - reduction
        return {'policy_version': POLICY_VERSION, 'tax_year': tax_year, 'currency': 'CNY',
                'assessable_comprehensive_income': assessable, 'basic_deduction': Decimal('60000'),
                'taxable_income': taxable, 'bands': bands, 'gross_tax': tax,
                'allowed_tax_reductions': reduction, 'annual_liability': liability,
                'prepaid_tax': prepaid, 'balance_due': liability - prepaid,
                'source_ids': ['cn.law.iit#2', 'cn.law.iit#6', 'cn.iit.comprehensive-rate-table'],
                'sources': deepcopy([SOURCE_BY_ID['cn.law.iit'], SOURCE_BY_ID['cn.iit.comprehensive-rate-table']]),
                'stage': 'domestic_resident_comprehensive_before_assessment_rounding'}


def normal_company_tax(taxable_income, *, tax_year, normal_rate_confirmed, allowed_tax_credits, prepaid_tax):
    """25% regime after verified tax adjustments/loss use, before rounding.

Explicit confirmation excludes small-low-profit, high-tech, zone/incentive,
nonresident withholding and other concessionary regimes. Accounting profit is
not an established taxable-income basis.
"""
    check_year(tax_year)
    if normal_rate_confirmed is not True:
        raise ValueError('Normal corporate rate eligibility must be confirmed')
    base, credits, prepaid = map(amount, (taxable_income, allowed_tax_credits, prepaid_tax))
    with localcontext() as ctx:
        ctx.prec = 40
        gross = base * Decimal('.25')
        if credits > gross:
            raise ValueError('Allowed credits exceed gross tax')
        liability = gross - credits
        return {'policy_version': POLICY_VERSION, 'tax_year': tax_year, 'currency': 'CNY',
                'taxable_income': base, 'rate': Decimal('.25'), 'gross_tax': gross,
                'allowed_tax_credits': credits, 'annual_liability': liability,
                'prepaid_tax': prepaid, 'balance_due': liability - prepaid,
                'source_ids': ['cn.law.eit#4', 'cn.law.eit#5'],
                'sources': deepcopy([SOURCE_BY_ID['cn.law.eit']]),
                'stage': 'normal_corporate_rate_before_assessment_rounding'}
