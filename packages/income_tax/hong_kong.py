"""Hong Kong 2025/26 ordinary-rate arithmetic on established tax bases.

Not a source/FSIE determination, joint/personal-assessment election, incentive
review, foreign-credit calculation or provisional-tax assessment.
"""
from copy import deepcopy
from decimal import Decimal, localcontext
import json
from pathlib import Path
from .arithmetic import Band, ZERO, amount, marginal_tax

POLICY_VERSION = 'hk-2025-26-2026-11-16'
SOURCES = json.loads(Path(__file__).with_name('hk_2025_26_sources.json').read_text(encoding='utf-8'))['sources']
PROFITS_BASIS_SOURCES = json.loads(Path(__file__).with_name('hk_profits_basis_sources.json').read_text(encoding='utf-8'))['sources']
SALARY_BASIS_SOURCES = json.loads(Path(__file__).with_name('hk_salary_basis_sources.json').read_text(encoding='utf-8'))['sources']
SALARIES_BANDS = tuple(Band(None if cap is None else Decimal(cap), Decimal(rate))
    for cap,rate in [('50000','.02'),('100000','.06'),('150000','.10'),('200000','.14'),(None,'.17')])


def check_year(year):
    if year != '2025/26':
        raise ValueError('This policy is verified only for assessment year 2025/26')


def salaries_tax(net_income, *, assessment_year, allowed_allowances, prepaid_final_tax,
                 ordinary_separate_assessment_confirmed):
    """Net income is after verified deductions and before allowances.

Return exact amounts before assessment rounding. Prepaid_final_tax is the
amount allocated to this final assessment, not a provisional-tax bill for the
next year. No allowance amount or eligibility is inferred.
"""
    check_year(assessment_year)
    if ordinary_separate_assessment_confirmed is not True:
        raise ValueError('Ordinary separate salaries assessment must be confirmed')
    net, allowances, prepaid = map(amount,(net_income,allowed_allowances,prepaid_final_tax))
    with localcontext() as ctx:
        ctx.prec=40
        chargeable=max(ZERO,net-allowances)
        progressive,bands=marginal_tax(chargeable,SALARIES_BANDS)
        standard=min(net,Decimal('5000000'))*Decimal('.15')+max(ZERO,net-Decimal('5000000'))*Decimal('.16')
        gross=min(progressive,standard)
        reduction=min(gross,Decimal('3000'))
        liability=gross-reduction
        return {'policy_version':POLICY_VERSION,'assessment_year':assessment_year,'currency':'HKD',
                'net_income_before_allowances':net,'allowed_allowances':allowances,'net_chargeable_income':chargeable,
                'progressive_tax':progressive,'standard_rate_tax':standard,'bands':bands,
                'selected_basis':'progressive' if progressive<=standard else 'standard',
                'gross_tax':gross,'tax_reduction':reduction,'final_tax':liability,
                'prepaid_final_tax':prepaid,'balance_due':liability-prepaid,
                'sources':deepcopy([SOURCES[0],SOURCES[2]]),'stage':'separate_salaries_before_assessment_rounding'}


def profits_tax(assessable_profits, *, assessment_year, business_form, two_tier_eligible,
                ordinary_regime_confirmed, prepaid_final_tax):
    """Ordinary corporate or sole-proprietor profits, after verified adjustments.

Partnership allocations, concessionary income and personal assessment are
separate. Eligibility includes connected-entity nomination and statutory
exclusions; it cannot be inferred from turnover or business form alone.
"""
    check_year(assessment_year)
    if business_form not in ('corporation','sole_proprietor'):
        raise ValueError('Unsupported business form')
    if ordinary_regime_confirmed is not True or type(two_tier_eligible) is not bool:
        raise ValueError('Regime and two-tier eligibility require explicit confirmation')
    base,prepaid=map(amount,(assessable_profits,prepaid_final_tax))
    rate=Decimal('.165') if business_form=='corporation' else Decimal('.15')
    with localcontext() as ctx:
        ctx.prec=40
        lower=min(base,Decimal('2000000')) if two_tier_eligible else ZERO
        gross=lower*rate/2+(base-lower)*rate
        reduction=min(gross,Decimal('3000'))
        liability=gross-reduction
        return {'policy_version':POLICY_VERSION,'assessment_year':assessment_year,'currency':'HKD',
                'business_form':business_form,'assessable_profits':base,'two_tier_eligible':two_tier_eligible,
                'lower_tier_profits':lower,'ordinary_rate':rate,'gross_tax':gross,'tax_reduction':reduction,
                'final_tax':liability,'prepaid_final_tax':prepaid,'balance_due':liability-prepaid,
                'sources':deepcopy([SOURCES[1],SOURCES[2]]),'stage':'ordinary_profits_before_assessment_rounding'}
