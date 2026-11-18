"""Ordinary 25% resident-company foreign credit pools on verified positive bases.

CS2009-125 VIII/IX and CS2017-84 I. This component does not establish foreign
income, indirect/deemed credit entitlement, losses, special rates or FX values.
Current-year credit precedes old excess; oldest unexpired excess is used first.
"""
from copy import deepcopy
from decimal import Decimal, localcontext
import json
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt
from packages.contracts.income_tax import Money, Jurisdiction
from .arithmetic import ZERO

SOURCES = json.loads(Path(__file__).with_name('cn_foreign_credit_sources.json').read_text(encoding='utf-8'))['sources']

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Excess(Strict):
    origin_year: StrictInt = Field(ge=2008)
    amount: Money

class Country(Strict):
    country: Jurisdiction
    taxable_income: Money
    eligible_current_tax: Money
    prior_excess: list[Excess] = Field(default_factory=list, max_length=100)

class Workpaper(Strict):
    tax_year: Literal[2026]
    method: Literal['per_country', 'pooled']
    domestic_taxable_income: Money
    countries: list[Country] = Field(min_length=1, max_length=10)
    ordinary_25_percent_positive_bases_verified: StrictBool
    income_tax_eligibility_and_fx_verified: StrictBool
    method_lock_and_carryforward_history_verified: StrictBool


def calculate(workpaper):
    p=Workpaper.model_validate(workpaper)
    if not all((p.ordinary_25_percent_positive_bases_verified,
                p.income_tax_eligibility_and_fx_verified,
                p.method_lock_and_carryforward_history_verified)):
        raise ValueError('Ordinary bases, tax eligibility, FX, method lock and carryforward history must be verified')
    codes=[row.country for row in p.countries]
    if 'cn' in codes or len(set(codes))!=len(codes):
        raise ValueError('Use unique foreign jurisdictions, with same-country income aggregated')
    for row in p.countries:
        years=[x.origin_year for x in row.prior_excess]
        if len(years)!=len(set(years)) or any(y>=p.tax_year for y in years):
            raise ValueError('Prior excess must have unique earlier origin years per country')
    groups=[p.countries] if p.method=='pooled' else [[row] for row in p.countries]
    with localcontext() as context:
        context.prec=40
        output=[]
        for rows in groups:
            income=sum((row.taxable_income for row in rows),ZERO)
            limit=income*Decimal('.25')
            current=sum((row.eligible_current_tax for row in rows),ZERO)
            used=min(current,limit);capacity=limit-used
            history=[]
            old=sorted(((entry.origin_year,row.country,entry.amount)
                        for row in rows for entry in row.prior_excess))
            for year,country,balance in old:
                expired=year+5<p.tax_year
                applied=ZERO if expired else min(balance,capacity)
                capacity-=applied
                history.append(dict(country=country,origin_year=year,last_usable_year=year+5,
                    opening_excess=balance,credit_used=applied,
                    expired_amount=balance if expired else ZERO,
                    closing_excess=ZERO if expired else balance-applied,
                    expires_after_current_year=balance-applied if year+5==p.tax_year else ZERO,
                    next_year_carryforward=balance-applied if year+5>p.tax_year else ZERO))
            prior_used=sum((row['credit_used'] for row in history),ZERO)
            output.append(dict(pool='all_foreign' if p.method=='pooled' else rows[0].country,
                countries=[row.country for row in rows],taxable_income=income,credit_limit=limit,
                eligible_current_tax=current,current_credit_used=used,
                current_excess=current-used,current_excess_last_usable_year=p.tax_year+5,
                prior_credit_used=prior_used,allowed_credit=used+prior_used,
                remaining_credit_capacity=capacity,carryforward_history=history))
        foreign=sum((row.taxable_income for row in p.countries),ZERO)
        worldwide=(p.domestic_taxable_income+foreign)*Decimal('.25')
        credit=sum((row['allowed_credit'] for row in output),ZERO)
        return dict(policy_version='cn-ordinary-foreign-credit-2026-11-19',currency='CNY',
            method=p.method,tax_year=p.tax_year,domestic_taxable_income=p.domestic_taxable_income,
            foreign_taxable_income=foreign,ordinary_worldwide_tax_before_credits=worldwide,
            allowed_foreign_tax_credit=credit,ordinary_tax_after_foreign_credit=worldwide-credit,
            pools=output,sources=deepcopy(SOURCES),
            stage='verified_positive_base_credit_component_before_other_reliefs_payments_and_rounding')
