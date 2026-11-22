"""Source-country FTC allocation on verified ordinary positive statutory groups.

IRAS worked examples: trade foreign gross / trade gross * trade statutory /
total statutory * Singapore tax; passive net / total statutory * tax.
This component does not determine residence, treaty entitlement or final tax.
"""
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import Annotated, Literal
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StrictBool
from packages.contracts.income_tax import Money, Jurisdiction
from .arithmetic import computed_amount


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Source(Strict):
    country: Jurisdiction
    gross: Money
    eligible_foreign_tax: Money
    pool_elected: StrictBool
    headline_rate_percent: Money
    credit_entitlement_verified: StrictBool


class Group(Strict):
    source_id: str = Field(min_length=1, max_length=120)
    kind: Literal['trade', 'passive']
    deductions: Money
    sources: list[Source] = Field(min_length=1, max_length=11)


class Workpaper(Strict):
    groups: list[Group] = Field(min_length=1, max_length=200)
    singapore_tax_before_credit: Annotated[Decimal, BeforeValidator(computed_amount)]
    resident_same_income_and_allocation_verified: StrictBool


def calculate(workpaper):
    p = Workpaper.model_validate(workpaper)
    if not p.resident_same_income_and_allocation_verified:
        raise ValueError('Resident entitlement and ordinary source allocation require verification')
    if len({g.source_id for g in p.groups}) != len(p.groups):
        raise ValueError('Source groups must be unique')
    prepared = []
    total = Fraction(0)
    for group in p.groups:
        if len({s.country for s in group.sources}) != len(group.sources):
            raise ValueError('Aggregate each country once within its source group')
        if group.kind == 'passive' and len(group.sources) != 1:
            raise ValueError('Passive sources require separate country-specific net amounts')
        gross = sum((Fraction(s.gross) for s in group.sources), Fraction(0))
        net = gross - Fraction(group.deductions)
        if net < 0:
            raise ValueError('Loss allocation requires a separate workpaper')
        total += net
        prepared.append((group, gross, net))
    tax = Fraction(p.singapore_tax_before_credit)
    if total == 0 and tax:
        raise ValueError('Positive tax requires positive statutory income')
    rows = []
    pooled_tax = pooled_limit = individual = Fraction(0)
    for group, gross, net in prepared:
        for source in group.sources:
            if source.country == 'sg':
                if source.eligible_foreign_tax or source.pool_elected:
                    raise ValueError('Domestic income cannot claim foreign credit')
                continue
            paid = Fraction(source.eligible_foreign_tax)
            limit = Fraction(0) if not gross or not total else Fraction(source.gross) / gross * net / total * tax
            if paid and not source.credit_entitlement_verified:
                raise ValueError('Foreign credit entitlement must be established')
            if source.pool_elected:
                if not paid or not limit or source.headline_rate_percent < 15 or not source.credit_entitlement_verified:
                    raise ValueError('Pooling requires paid foreign tax, positive Singapore tax, headline rate at least15 and entitlement')
                pooled_tax += paid
                pooled_limit += limit
            else:
                individual += min(paid, limit)
            rows.append(dict(source_id=group.source_id, country=source.country,
                singapore_tax_limit=limit, eligible_foreign_tax=paid,
                pool_elected=source.pool_elected,
                individual_credit=None if source.pool_elected else min(paid, limit)))
    pooled = min(pooled_tax, pooled_limit)
    def decimalize(value):
        if isinstance(value, Fraction):
            with localcontext() as ctx:
                ctx.prec = 40
                return Decimal(value.numerator) / Decimal(value.denominator)
        if isinstance(value, list): return [decimalize(v) for v in value]
        if isinstance(value, dict): return {k: decimalize(v) for k, v in value.items()}
        return value
    return decimalize(dict(total_statutory_income=total, sources=rows,
        individual_credit=individual, pooled_credit=pooled,
        pooled_foreign_tax=pooled_tax, pooled_singapore_tax_limit=pooled_limit,
        allowed_foreign_tax_credit=individual+pooled,
        stage='verified_allocation_component_not_complete_assessment'))
