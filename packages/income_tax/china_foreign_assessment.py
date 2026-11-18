"""Reconcile ordinary direct-credit workpapers to saved gross income facts."""
from decimal import Decimal, localcontext
from copy import deepcopy
from .china import SOURCE_BY_ID
from typing import Literal
from pydantic import Field, StrictBool
from packages.contracts.income_tax import Money, Jurisdiction
from .china_foreign_credit import Strict, Excess, calculate as credit

class Allocation(Strict):
    country: Jurisdiction
    deductions: Money
    exempt_income: Money
    non_taxable_income: Money
    eligible_prior_losses: Money
    eligible_direct_tax: Money
    prior_excess: list[Excess] = Field(default_factory=list,max_length=100)

class DirectWorkpaper(Strict):
    method: Literal['per_country','pooled']
    allocations: list[Allocation] = Field(min_length=1,max_length=11)
    ordinary_25_percent_positive_bases_verified: StrictBool
    income_tax_eligibility_and_fx_verified: StrictBool
    method_lock_and_carryforward_history_verified: StrictBool
    direct_tax_only_no_other_reliefs_verified: StrictBool
    gross_before_withholding_and_expense_allocation_verified: StrictBool


def assess(case, workpaper, prepaid_tax):
    p=DirectWorkpaper.model_validate(workpaper)
    if case.subject!='company' or case.residency!='resident' or case.jurisdiction!='cn':
        raise ValueError('China resident company required')
    if not p.direct_tax_only_no_other_reliefs_verified or not p.gross_before_withholding_and_expense_allocation_verified:
        raise ValueError('Direct taxes, gross-before-withholding income, expense allocation and absence of other reliefs must be verified')
    countries={item.source_jurisdiction for item in case.incomes}
    codes=[row.country for row in p.allocations]
    if len(set(codes))!=len(codes) or not countries<=set(codes) or countries=={'cn'}:
        raise ValueError('Each saved source jurisdiction requires exactly one allocation, including foreign income')
    with localcontext() as ctx:
        ctx.prec=40
        if sum((row.deductions for row in p.allocations),Decimal(0))!=case.claimed_deductions:
            raise ValueError('Allocated deductions must reconcile to saved deductions')
        if sum((row.eligible_prior_losses for row in p.allocations),Decimal(0))!=case.carried_losses:
            raise ValueError('Allocated eligible prior losses must reconcile to saved losses')
        reconciliation=[];foreign=[];domestic=Decimal(0)
        for row in p.allocations:
            items=[item for item in case.incomes if item.source_jurisdiction==row.country]
            if any(item.foreign_tax_paid is None for item in items if row.country!='cn'):
                raise ValueError('Foreign tax paid must be recorded, including explicit zero')
            gross=sum((item.gross_amount for item in items),Decimal(0))
            paid=sum((item.foreign_tax_paid or Decimal(0) for item in items),Decimal(0))
            if row.country not in countries and (not row.prior_excess or any((row.deductions,row.exempt_income,row.non_taxable_income,row.eligible_prior_losses,row.eligible_direct_tax))):
                raise ValueError('An additional country row is only for prior excess without current activity')
            exclusions=row.exempt_income+row.non_taxable_income
            before=gross-exclusions-row.deductions
            if exclusions>gross or before<0 or row.eligible_prior_losses>before:
                raise ValueError('Negative bases or unused income losses require a separate loss workpaper')
            base=before-row.eligible_prior_losses
            if row.eligible_direct_tax>paid:
                raise ValueError('Eligible direct credit cannot exceed saved foreign tax paid')
            if row.country=='cn':
                if paid or row.eligible_direct_tax or row.prior_excess:
                    raise ValueError('Domestic income cannot carry a foreign credit')
                domestic=base
            else:
                foreign.append(dict(country=row.country,taxable_income=base,
                    eligible_current_tax=row.eligible_direct_tax,prior_excess=row.prior_excess))
            reconciliation.append(dict(country=row.country,gross_income=gross,
                deductions=row.deductions,exempt_income=row.exempt_income,
                non_taxable_income=row.non_taxable_income,prior_losses_used=row.eligible_prior_losses,
                taxable_income=base,foreign_tax_paid=paid,eligible_direct_tax=row.eligible_direct_tax))
        result=credit(dict(tax_year=2026,method=p.method,domestic_taxable_income=domestic,
            countries=foreign,ordinary_25_percent_positive_bases_verified=p.ordinary_25_percent_positive_bases_verified,
            income_tax_eligibility_and_fx_verified=p.income_tax_eligibility_and_fx_verified,
            method_lock_and_carryforward_history_verified=p.method_lock_and_carryforward_history_verified))
        result['sources'].append(deepcopy(SOURCE_BY_ID['cn.law.eit']))
        liability=result['ordinary_tax_after_foreign_credit']
        result.update(country_basis_reconciliation=reconciliation,
            taxable_income=domestic+result['foreign_taxable_income'],
            gross_tax=result['ordinary_worldwide_tax_before_credits'],annual_liability=liability,
            final_tax=liability,prepaid_tax=prepaid_tax,balance_due=liability-prepaid_tax,
            tax_scope='china_resident_ordinary_direct_foreign_credit_positive_bases',
            stage='annual_direct_credit_assessment_before_filing_rounding',
            scope_note='Established gross CNY income and direct eligible paid tax only. No indirect/deemed credits, special rates, other tax reliefs or negative country income. Verify treaty eligibility, income recognition, FX and loss history.')
        return result
