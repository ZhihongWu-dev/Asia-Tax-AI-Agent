"""Article 3 personal foreign-credit limits from established annual category taxes.

Internal component: does not establish annual tax bases, source-country eligibility,
prior credits, deemed credits, filing rounding or final liability.
"""
from copy import deepcopy
from decimal import Decimal, localcontext
import json
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from packages.contracts.income_tax import Jurisdiction, Money

SOURCES = json.loads(Path(__file__).with_name('cn_personal_foreign_sources.json').read_text(encoding='utf-8'))['sources']
ZERO = Decimal(0)

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Country(Strict):
    country: Jurisdiction
    comprehensive_income_amount: Money
    business_taxable_income: Money
    other_category_chinese_tax: Money
    eligible_foreign_tax_paid: Money

class Workpaper(Strict):
    tax_year: Literal[2026]
    countries: list[Country] = Field(min_length=1, max_length=11)
    worldwide_comprehensive_tax: Money
    worldwide_business_tax: Money
    resident_source_fx_and_category_bases_verified: StrictBool
    annual_category_taxes_and_reliefs_verified: StrictBool
    direct_paid_tax_eligibility_and_evidence_verified: StrictBool


def calculate(workpaper):
    p = Workpaper.model_validate(workpaper)
    if not all((p.resident_source_fx_and_category_bases_verified,
                p.annual_category_taxes_and_reliefs_verified,
                p.direct_paid_tax_eligibility_and_evidence_verified)):
        raise ValueError('Resident source, category bases, annual taxes and eligible paid-tax evidence must be verified')
    codes = [r.country for r in p.countries]
    if len(set(codes)) != len(codes) or not any(c != 'cn' for c in codes):
        raise ValueError('Unique country rows including a foreign jurisdiction required')
    if any(r.country == 'cn' and r.eligible_foreign_tax_paid for r in p.countries):
        raise ValueError('Domestic income cannot carry foreign tax')
    with localcontext() as ctx:
        ctx.prec = 40
        comprehensive = sum((r.comprehensive_income_amount for r in p.countries), ZERO)
        business = sum((r.business_taxable_income for r in p.countries), ZERO)
        if (not comprehensive and p.worldwide_comprehensive_tax) or (not business and p.worldwide_business_tax):
            raise ValueError('Positive annual category tax requires a positive category allocation denominator')
        rows = []
        for r in p.countries:
            if r.country == 'cn':
                continue
            comp_limit = p.worldwide_comprehensive_tax * r.comprehensive_income_amount / comprehensive if comprehensive else ZERO
            business_limit = p.worldwide_business_tax * r.business_taxable_income / business if business else ZERO
            limit = comp_limit + business_limit + r.other_category_chinese_tax
            used = min(r.eligible_foreign_tax_paid, limit)
            rows.append(dict(country=r.country, comprehensive_credit_limit=comp_limit,
                business_credit_limit=business_limit, other_category_credit_limit=r.other_category_chinese_tax,
                credit_limit=limit, eligible_current_tax=r.eligible_foreign_tax_paid,
                current_credit_used=used, current_excess=r.eligible_foreign_tax_paid-used,
                current_excess_last_usable_year=p.tax_year+5, remaining_credit_capacity=limit-used))
        return dict(policy_version='cn-personal-foreign-credit-limits-2026-11-19', tax_year=p.tax_year,
            currency='CNY', method='per_country', comprehensive_income_denominator=comprehensive,
            business_taxable_income_denominator=business, country_limits=rows,
            current_credit_used=sum((r['current_credit_used'] for r in rows), ZERO),
            stage='internal_current_credit_limits_before_prior_credits_and_final_assessment',
            sources=deepcopy(SOURCES))
