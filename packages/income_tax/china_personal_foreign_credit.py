"""Article 3 personal foreign-credit limits from established annual category taxes.

Internal component: does not establish annual tax bases, source-country eligibility,
deemed credits, filing rounding or final liability.
"""
from copy import deepcopy
from decimal import Decimal, localcontext
import json
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt
from packages.contracts.income_tax import Jurisdiction, Money

SOURCES = json.loads(Path(__file__).with_name('cn_personal_foreign_sources.json').read_text(encoding='utf-8'))['sources']
ZERO = Decimal(0)

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Excess(Strict):
    origin_year: StrictInt = Field(ge=2008)
    amount: Money

class Country(Strict):
    country: Jurisdiction
    comprehensive_income_amount: Money
    business_taxable_income: Money
    other_category_chinese_tax: Money
    other_category_tax_reductions: Money = Decimal(0)
    eligible_foreign_tax_paid: Money
    prior_excess: list[Excess] = Field(default_factory=list, max_length=100)

class Workpaper(Strict):
    tax_year: Literal[2026]
    countries: list[Country] = Field(min_length=1, max_length=11)
    worldwide_comprehensive_tax: Money
    worldwide_business_tax: Money
    comprehensive_tax_reductions: Money = Decimal(0)
    business_tax_reductions: Money = Decimal(0)
    resident_source_fx_and_category_bases_verified: StrictBool
    annual_category_taxes_and_reliefs_verified: StrictBool
    direct_paid_tax_eligibility_and_evidence_verified: StrictBool
    carryforward_history_verified: StrictBool = False


def calculate(workpaper):
    p = Workpaper.model_validate(workpaper)
    if not all((p.resident_source_fx_and_category_bases_verified,
                p.annual_category_taxes_and_reliefs_verified,
                p.direct_paid_tax_eligibility_and_evidence_verified)):
        raise ValueError('Resident source, category bases, annual taxes and eligible paid-tax evidence must be verified')
    codes = [r.country for r in p.countries]
    if len(set(codes)) != len(codes) or not any(c != 'cn' for c in codes):
        raise ValueError('Unique country rows including a foreign jurisdiction required')
    for row in p.countries:
        years = [v.origin_year for v in row.prior_excess]
        if len(set(years)) != len(years) or any(y >= p.tax_year for y in years):
            raise ValueError('Prior credit requires unique original years earlier than current year')
        if row.prior_excess and not p.carryforward_history_verified:
            raise ValueError('Carryforward history must be verified')
    if any(r.country == 'cn' and (r.eligible_foreign_tax_paid or r.prior_excess) for r in p.countries):
        raise ValueError('Domestic income cannot carry foreign tax')
    with localcontext() as ctx:
        ctx.prec = 40
        comprehensive = sum((r.comprehensive_income_amount for r in p.countries), ZERO)
        business = sum((r.business_taxable_income for r in p.countries), ZERO)
        if (not comprehensive and p.worldwide_comprehensive_tax) or (not business and p.worldwide_business_tax):
            raise ValueError('Positive annual category tax requires a positive category allocation denominator')
        if p.comprehensive_tax_reductions > p.worldwide_comprehensive_tax or p.business_tax_reductions > p.worldwide_business_tax:
            raise ValueError('Category reductions cannot exceed corresponding annual tax')
        if any(r.other_category_tax_reductions > r.other_category_chinese_tax for r in p.countries):
            raise ValueError('Other category reductions cannot exceed corresponding country tax')
        comprehensive_net = p.worldwide_comprehensive_tax - p.comprehensive_tax_reductions
        business_net = p.worldwide_business_tax - p.business_tax_reductions
        rows = []
        for r in p.countries:
            if r.country == 'cn':
                continue
            comp_limit = comprehensive_net * r.comprehensive_income_amount / comprehensive if comprehensive else ZERO
            business_limit = business_net * r.business_taxable_income / business if business else ZERO
            other_net = r.other_category_chinese_tax - r.other_category_tax_reductions
            limit = comp_limit + business_limit + other_net
            used = min(r.eligible_foreign_tax_paid, limit)
            capacity = limit - used
            history = []
            for old in sorted(r.prior_excess, key=lambda v: v.origin_year):
                expired = old.origin_year + 5 < p.tax_year
                applied = ZERO if expired else min(old.amount, capacity)
                capacity -= applied
                balance = ZERO if expired else old.amount - applied
                history.append(dict(origin_year=old.origin_year, last_usable_year=old.origin_year+5,
                    opening_excess=old.amount, credit_used=applied,
                    expired_amount=old.amount if expired else ZERO,
                    expires_after_current_year=balance if old.origin_year+5==p.tax_year else ZERO,
                    next_year_carryforward=balance if old.origin_year+5>p.tax_year else ZERO))
            prior_used = sum((h['credit_used'] for h in history), ZERO)
            rows.append(dict(country=r.country, comprehensive_credit_limit=comp_limit,
                business_credit_limit=business_limit, other_category_credit_limit=other_net,
                credit_limit=limit, eligible_current_tax=r.eligible_foreign_tax_paid,
                current_credit_used=used, current_excess=r.eligible_foreign_tax_paid-used,
                current_excess_last_usable_year=p.tax_year+5, remaining_credit_capacity=capacity,
                prior_credit_used=prior_used, allowed_credit=used+prior_used, carryforward_history=history))
        return dict(policy_version='cn-personal-foreign-credit-limits-2026-11-19', tax_year=p.tax_year,
            currency='CNY', method='per_country', comprehensive_income_denominator=comprehensive,
            business_taxable_income_denominator=business, country_limits=rows,
            comprehensive_tax_after_reductions=comprehensive_net, business_tax_after_reductions=business_net,
            current_credit_used=sum((r['current_credit_used'] for r in rows), ZERO),
            allowed_credit=sum((r['allowed_credit'] for r in rows), ZERO),
            allocation_order='current_year_then_oldest_eligible_prior_excess_within_same_country',
            stage='internal_credit_workpaper_before_final_assessment',
            sources=deepcopy(SOURCES))
