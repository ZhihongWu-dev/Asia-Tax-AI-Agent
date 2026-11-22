"""Form43-13 local foreign-tax deduction ledger, distinct from national FTC."""
from datetime import date
from decimal import Decimal, localcontext
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from packages.contracts.income_tax import Money
from .korea_foreign_local_basis import reconcile_local_base
from .korea_foreign_history import Lot


class LocalLot(BaseModel):
    model_config=ConfigDict(extra='forbid')
    identifier: str=Field(min_length=1,max_length=120,pattern=r'\S')
    kind: Literal['direct','fund']
    origin_period_end: date
    verified_expiry_date: date
    original_amount: Money
    previously_deducted: Money


class LocalHistory(BaseModel):
    model_config=ConfigDict(extra='forbid')
    lots: list[LocalLot]=Field(min_length=1,max_length=200)
    original_local_entitlement_expiry_and_prior_usage_verified: StrictBool
    local_eligibility_addback_and_no_duplicate_amounts_verified: StrictBool


class SavedBalances(BaseModel):
    model_config=ConfigDict(extra='forbid')
    national_lots: list[Lot]=Field(max_length=200)
    local_history: LocalHistory
    national_entitlement_expiry_and_order_or_absence_verified: StrictBool
    no_expired_national_credit_deductions_or_other_base_adjustments_verified: StrictBool
    no_competing_national_reliefs_or_separate_taxes_verified: StrictBool


def reconcile_history(workpaper, *, period_start, period_end, national_taxable_base,
        expired_foreign_tax_deducted_nationally, article57_foreign_tax, article57_2_eligible_fund_credit):
    p=LocalHistory.model_validate(workpaper)
    if not p.original_local_entitlement_expiry_and_prior_usage_verified or not p.local_eligibility_addback_and_no_duplicate_amounts_verified:
        raise ValueError('Verify local entitlement, original amounts, prior deductions, expiry and addback')
    start=date.fromisoformat(str(period_start));end=date.fromisoformat(str(period_end))
    if end<start:
        raise ValueError('Invalid current business period')
    ids=[lot.identifier.strip() for lot in p.lots]
    if len(ids)!=len(set(ids)):
        raise ValueError('Local lot references must be unique')
    for lot in p.lots:
        if lot.origin_period_end>=start or lot.verified_expiry_date<=lot.origin_period_end or lot.previously_deducted>lot.original_amount:
            raise ValueError('Local lots require prior origins, verified later expiry and reconciled cumulative deductions')
    current=reconcile_local_base(national_taxable_base=national_taxable_base,
        expired_foreign_tax_deducted_nationally=expired_foreign_tax_deducted_nationally,
        article57_foreign_tax=article57_foreign_tax,article57_2_eligible_fund_credit=article57_2_eligible_fund_credit,
        local_eligibility_addback_and_no_duplicate_amounts_verified=True,
        no_prior_local_foreign_tax_deductions_verified=True)
    with localcontext() as context:
        context.prec=40
        remaining=current['local_base_before_foreign_tax_deduction']
        fund_capacity=current['national_taxable_base']
        rows=[];history_used=Decimal(0);excluded=Decimal(0);carry=Decimal(0)
        # Earlier originating business years precede later years and current
        # amounts. Stable ordering within the same year follows the workpaper.
        for lot in sorted(p.lots,key=lambda row:row.origin_period_end):
            available=lot.original_amount-lot.previously_deducted
            expired=lot.verified_expiry_date<end
            used=Decimal(0) if expired else min(available,remaining,fund_capacity if lot.kind=='fund' else remaining)
            remaining-=used
            if lot.kind=='fund':fund_capacity-=used
            unused=available-used
            expires_now=lot.verified_expiry_date==end
            lost=unused if expired or expires_now else Decimal(0)
            next_amount=unused-lost
            excluded+=lost;carry+=next_amount;history_used+=used
            rows.append(dict(identifier=lot.identifier.strip(),kind=lot.kind,
                origin_period_end=lot.origin_period_end.isoformat(),verified_expiry_date=lot.verified_expiry_date.isoformat(),
                original_amount=lot.original_amount,previously_deducted=lot.previously_deducted,
                available_amount=available,current_deduction=used,unused_after_allocation=unused,
                expired_before_current_year_end=expired,expires_at_current_year_end=expires_now,
                excluded_from_next_carry=lost,next_carryforward=next_amount))
        direct_used=min(current['article57_foreign_tax'],remaining);remaining-=direct_used
        fund_used=min(current['article57_2_eligible_fund_credit'],remaining,fund_capacity);remaining-=fund_used
        current_used=direct_used+fund_used
        current_carry=current['article57_foreign_tax']+current['article57_2_eligible_fund_credit']-current_used
        current.update(policy_version='kr-local-foreign-history-form43-13-20261122',
            historical_local_deductions=rows,historical_local_deduction_used=history_used,
            current_direct_local_deduction=direct_used,current_fund_local_deduction=fund_used,
            current_local_foreign_tax_deduction=current_used,local_taxable_base=remaining,
            excess_current_local_deduction=current_carry,
            historical_excluded_from_next_carry=excluded,historical_next_carryforward=carry,
            total_local_deduction=history_used+current_used,total_next_carryforward=carry+current_carry)
    return current
