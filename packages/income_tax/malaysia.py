"""Malaysia YA2026 ordinary income tax on an established chargeable base.

Schedule 1 Part I, Act 53 updated at 1 January 2026. Separate dividend,
capital-gains, Labuan, incentive, reinsurance and minimum-tax regimes are outside
these calculations. Allowed rebates/credits are verified inputs, not claims.
"""
from copy import deepcopy
from decimal import Decimal, localcontext
import json
from pathlib import Path
from .arithmetic import Band, ZERO, amount, marginal_tax

POLICY_VERSION = 'my-ya2026-2026-11-16'
SOURCES = json.loads(Path(__file__).with_name('my_2026_sources.json').read_text(encoding='utf-8'))['sources']
RESIDENT_BANDS = tuple(Band(None if cap is None else Decimal(cap), Decimal(rate))
    for cap,rate in [('5000','0'),('20000','.01'),('35000','.03'),('50000','.06'),
                     ('70000','.11'),('100000','.19'),('400000','.25'),('600000','.26'),
                     ('2000000','.28'),(None,'.30')])
SME_BANDS = (Band(Decimal('150000'),Decimal('.15')),
             Band(Decimal('600000'),Decimal('.17')),Band(None,Decimal('.24')))


def check(assessment_year, ordinary_treatment_confirmed):
    if type(assessment_year) is not int or assessment_year != 2026:
        raise ValueError('This policy is verified only for YA2026')
    if ordinary_treatment_confirmed is not True:
        raise ValueError('Ordinary treatment and exclusion of separate regimes must be confirmed')


def settlement(gross, rebate, credit, prepaid):
    rebate,credit,prepaid=map(amount,(rebate,credit,prepaid))
    if rebate > gross or credit > gross-rebate:
        raise ValueError('Allowed rebates or credits exceed available tax')
    liability=gross-rebate-credit
    return dict(gross_tax=gross,allowed_rebates=rebate,allowed_tax_credits=credit,
                final_tax=liability,prepaid_tax=prepaid,balance_due=liability-prepaid)


def company_tax(chargeable_income, *, assessment_year, scheme, sme_eligibility_confirmed,
                ordinary_treatment_confirmed, allowed_rebates, allowed_tax_credits, prepaid_tax):
    """SME confirmation covers Schedule 1 paragraphs 2A-2C, not turnover alone.

Requires Malaysian incorporation/residence, ordinary paid-up capital <=2.5m at
period start, business gross income <=50m, related-company and >20% foreign
ownership exclusions. LLPs and special-rate industries need separate policies.
"""
    check(assessment_year,ordinary_treatment_confirmed)
    if scheme not in ('ordinary','sme') or type(sme_eligibility_confirmed) is not bool:
        raise ValueError('Explicit company scheme and eligibility are required')
    if scheme=='sme' and not sme_eligibility_confirmed:
        raise ValueError('SME eligibility must be confirmed')
    base=amount(chargeable_income)
    with localcontext() as ctx:
        ctx.prec=40
        gross,bands=marginal_tax(base,SME_BANDS if scheme=='sme' else (Band(None,Decimal('.24')),))
        return dict(policy_version=POLICY_VERSION,assessment_year=assessment_year,currency='MYR',
                    chargeable_income=base,scheme=scheme,bands=bands,
                    **settlement(gross,allowed_rebates,allowed_tax_credits,prepaid_tax),
                    sources=deepcopy(SOURCES),stage='ordinary_company_before_assessment_rounding')


def individual_tax(chargeable_income, *, assessment_year, residency,
                   ordinary_treatment_confirmed, allowed_rebates, allowed_tax_credits, prepaid_tax):
    """Ordinary separate individual assessment, after verified deductions/reliefs.

Nonresidents do not receive resident personal reliefs/rebates. Special-rate
income and dividends are not part of this schedule. Credits must already be
limited under the applicable credit rules and allocation ordering.
"""
    check(assessment_year,ordinary_treatment_confirmed)
    if residency not in ('resident','nonresident'):
        raise ValueError('Residency must be established')
    base=amount(chargeable_income)
    if residency=='nonresident' and amount(allowed_rebates)!=ZERO:
        raise ValueError('Resident rebates cannot be applied to a nonresident')
    with localcontext() as ctx:
        ctx.prec=40
        gross,bands=marginal_tax(base,RESIDENT_BANDS if residency=='resident' else (Band(None,Decimal('.30')),))
        return dict(policy_version=POLICY_VERSION,assessment_year=assessment_year,currency='MYR',
                    chargeable_income=base,residency=residency,bands=bands,
                    **settlement(gross,allowed_rebates,allowed_tax_credits,prepaid_tax),
                    sources=deepcopy(SOURCES),stage='ordinary_individual_before_assessment_rounding')
