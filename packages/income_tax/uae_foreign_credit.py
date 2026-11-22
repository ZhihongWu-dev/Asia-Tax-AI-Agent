"""UAE ordinary positive-income foreign credit, FTA CTGFSI1 section8.3.

Separate income caps use gross UAE CT times net source income / total income.
Excess foreign tax is forfeited, not pooled, carried or deducted from income.
"""
from decimal import Decimal,localcontext
from fractions import Fraction
from pydantic import BaseModel,ConfigDict,Field,StrictBool
from packages.contracts.income_tax import Money,Jurisdiction


class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid')


class ForeignIncome(Strict):
    source_id: str=Field(min_length=1,max_length=120)
    country: Jurisdiction
    net_taxable_income: Money
    eligible_foreign_tax: Money


class Workpaper(Strict):
    domestic_taxable_income: Money
    foreign_incomes: list[ForeignIncome]=Field(min_length=1,max_length=200)
    ordinary_positive_taxable_income_verified: StrictBool
    foreign_tax_eligibility_treaty_and_fx_verified: StrictBool
    distinct_sources_and_linked_expenses_verified: StrictBool


def calculate(workpaper):
    p=Workpaper.model_validate(workpaper)
    if not all((p.ordinary_positive_taxable_income_verified,
        p.foreign_tax_eligibility_treaty_and_fx_verified,p.distinct_sources_and_linked_expenses_verified)):
        raise ValueError('Ordinary income, distinct sources, linked expenses and foreign tax eligibility require verification')
    ids=[s.source_id for s in p.foreign_incomes]
    if len(set(ids))!=len(ids) or any(s.country=='ae' for s in p.foreign_incomes):
        raise ValueError('Unique foreign source IDs and non-UAE countries required')
    total=Fraction(p.domestic_taxable_income)+sum((Fraction(s.net_taxable_income) for s in p.foreign_incomes),Fraction(0))
    gross=max(Fraction(0),total-375000)*Fraction(9,100)
    used=Fraction(0);rows=[]
    for source in p.foreign_incomes:
        cap=gross*Fraction(source.net_taxable_income)/total if total else Fraction(0)
        paid=Fraction(source.eligible_foreign_tax)
        applied=min(paid,cap);used+=applied
        rows.append(dict(source_id=source.source_id,country=source.country,
            net_taxable_income=Fraction(source.net_taxable_income),eligible_foreign_tax=paid,
            credit_limit=cap,credit_used=applied,forfeited_excess=paid-applied))
    def convert(v):
        if isinstance(v,Fraction):
            with localcontext() as ctx:
                ctx.prec=40
                return Decimal(v.numerator)/Decimal(v.denominator)
        if isinstance(v,list): return [convert(x) for x in v]
        if isinstance(v,dict): return {k:convert(x) for k,x in v.items()}
        return v
    return convert(dict(policy_version='ae-ordinary-foreign-credit-20261122',currency='AED',
        taxable_income=total,gross_tax=gross,allowed_foreign_tax_credit=used,
        tax_after_credit=gross-used,source_credits=rows,
        forfeited_excess=sum((row['forfeited_excess'] for row in rows),Fraction(0)),
        stage='verified_positive_income_credit_component_before_settlement'))
