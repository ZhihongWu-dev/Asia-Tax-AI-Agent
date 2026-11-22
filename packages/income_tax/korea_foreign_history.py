"""Allocate verified historical direct credits within current country limits.

Origin/expiry dates and history ordering must be established from the original
returns and transitional rules. This component does not invent a new expiry
date for legacy lots or deduct expired amounts from the annual tax base.
"""
from datetime import date, timedelta
from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from packages.contracts.income_tax import Jurisdiction, Money


class Lot(BaseModel):
    model_config=ConfigDict(extra='forbid')
    identifier: str=Field(min_length=1,max_length=120,pattern=r'\S')
    country: Jurisdiction
    origin_period_end: date
    verified_expiry_date: date
    available_amount: Money


class SavedHistory(BaseModel):
    model_config=ConfigDict(extra='forbid')
    lots: list[Lot]=Field(min_length=1,max_length=200)
    history_entitlement_expiry_and_order_verified: StrictBool
    no_prior_local_balances_competing_reliefs_or_separate_taxes_verified: StrictBool
    no_expired_credit_deductions_or_other_base_adjustments_verified: StrictBool


def allocate_history(current, lots, *, period_start, period_end,
                     history_entitlement_expiry_and_order_verified):
    if history_entitlement_expiry_and_order_verified is not True:
        raise ValueError('Original entitlement, transitional expiry and history ordering must be verified')
    start=date.fromisoformat(str(period_start));end=date.fromisoformat(str(period_end))
    if end<start:
        raise ValueError('Invalid current business period')
    if current.get('policy_version')!='kr-direct-country-credit-component-20261122':
        raise ValueError('Expected current direct-country credit calculation')
    if not isinstance(lots,list) or len(lots)>200:
        raise ValueError('At most200 historical credit lots supported')
    checked=[Lot.model_validate(lot) for lot in lots]
    ids=[lot.identifier.strip() for lot in checked]
    if len(ids)!=len(set(ids)):
        raise ValueError('Historical credit identifiers must be unique')
    def exact(row,key):
        v=row['exact_amounts'][key]
        return Fraction(int(v['numerator']),int(v['denominator']))
    current_rows={row['country']:row for row in current['country_credits']}
    capacity={country:exact(row,'credit_limit') for country,row in current_rows.items()}
    history=[];history_used=Fraction(0)
    with localcontext() as context:
        context.prec=40
        def number(v):return Decimal(v.numerator)/Decimal(v.denominator)
        for lot in checked:
            if lot.country=='kr' or lot.origin_period_end>=start or lot.verified_expiry_date<=lot.origin_period_end:
                raise ValueError('Foreign historical lot requires a prior origin period and valid expiry')
            available=Fraction(lot.available_amount);used=Fraction(0)
            expired=end>lot.verified_expiry_date
            if not expired:
                used=min(available,capacity.get(lot.country,Fraction(0)))
                capacity[lot.country]=capacity.get(lot.country,Fraction(0))-used
            history_used+=used
            deduction_day=lot.verified_expiry_date+timedelta(days=1) if expired else None
            history.append(dict(identifier=lot.identifier.strip(),country=lot.country,
                origin_period_end=lot.origin_period_end.isoformat(),expiry_date=lot.verified_expiry_date.isoformat(),
                used=number(used),remaining=number(available-used) if not expired else Decimal(0),
                expired_amount=number(available) if expired else Decimal(0),
                expires_at_current_period_end=lot.verified_expiry_date==end,
                expired_deduction_review_in_current_period=bool(expired and start<=deduction_day<=end)))
        countries=[];current_used=Fraction(0)
        for country,row in current_rows.items():
            eligible=sum((exact(row,k) for k in ('current_foreign_tax_credit',
                'expense_related_excess_not_carried','eligible_current_year_carryforward')),Fraction(0))
            expense=exact(row,'expense_related_excess_not_carried')
            used=min(exact(row,'current_foreign_tax_credit'),capacity.get(country,Fraction(0)))
            carry=eligible-expense-used
            current_used+=used
            countries.append(dict(country=country,current_credit_used=number(used),
                current_ordinary_carryforward=number(carry),expense_related_excess_not_carried=number(expense),
                exact_amounts={key:dict(numerator=str(value.numerator),denominator=str(value.denominator))
                    for key,value in [('current_credit_used',used),('current_ordinary_carryforward',carry)]}))
        sources=deepcopy(current['sources'])
        for source in sources:
            if source['doc_id']=='kr.corporate-tax-act.20260701.ko':
                source['provisions'].append('Article59(1)(3)')
        return dict(currency='KRW',historical_lots=history,current_country_usage=countries,
            historical_credit_used=number(history_used),current_credit_used=number(current_used),
            total_credit_used=number(history_used+current_used),
            stage='verified_history_before_other_reliefs_expiry_deductions_and_annual_settlement',
            sources=sources,ordering='verified_history_order_before_current_year_CTA59')
