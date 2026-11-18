"""Saved-fact reconciliation for ordinary Chinese resident foreign personal income."""
from copy import deepcopy
from decimal import Decimal, localcontext
from pydantic import Field, StrictBool
from packages.contracts.income_tax import Money, Jurisdiction
from .arithmetic import marginal_tax
from .china import COMPREHENSIVE_BANDS, SOURCE_BY_ID
from .china_business import BANDS, SOURCES as BUSINESS_SOURCES
from .china_personal_transfers import Transfer, calculate as transfer_tax
from .china_personal_rental import RentalYear, calculate as rental_tax
from .china_personal_foreign_credit import Strict, Excess, calculate

ZERO=Decimal(0)
FACTORS={'employment':Decimal(1),'service_remuneration':Decimal('.8'),
         'author_remuneration':Decimal('.56'),'royalty':Decimal('.8')}

class CountryBasis(Strict):
    country: Jurisdiction
    business_deductions: Money
    business_prior_losses: Money
    eligible_foreign_tax_paid: Money
    prior_excess: list[Excess] = Field(default_factory=list,max_length=100)

class PersonalWorkpaper(Strict):
    rentals: list[RentalYear] = Field(default_factory=list,max_length=200)
    transfers: list[Transfer] = Field(default_factory=list,max_length=200)
    countries: list[CountryBasis] = Field(min_length=1,max_length=11)
    comprehensive_deductions: Money
    comprehensive_tax_reductions: Money
    business_tax_reductions: Money
    ordinary_categories_and_no_special_treatment_verified: StrictBool
    source_fx_deductions_and_losses_verified: StrictBool
    paid_tax_evidence_and_history_verified: StrictBool


def assess(case,workpaper,prepaid_tax):
    p=PersonalWorkpaper.model_validate(workpaper)
    if case.subject!='individual' or case.residency!='resident' or case.jurisdiction!='cn':
        raise ValueError('Chinese resident individual required')
    if not all((p.ordinary_categories_and_no_special_treatment_verified,
                p.source_fx_deductions_and_losses_verified,p.paid_tax_evidence_and_history_verified)):
        raise ValueError('Ordinary treatment, allocation, evidence and history require verification')
    if any(i.category not in {*FACTORS,'business','dividend','interest','capital_gain','rental'} for i in case.incomes):
        raise ValueError('Other income and special treatment require separate category workpapers')
    saved={i.source_jurisdiction for i in case.incomes};codes=[r.country for r in p.countries]
    if len(set(codes))!=len(codes) or not saved<=set(codes) or saved=={'cn'}:
        raise ValueError('Unique rows covering all saved countries and foreign income required')
    with localcontext() as ctx:
        ctx.prec=40
        has_rentals=any(i.category=='rental' for i in case.incomes)
        if p.rentals and not has_rentals:raise ValueError('Rental workpapers require saved rental income')
        rentals=rental_tax(case,p.rentals) if has_rentals else None
        rental_deductions=rentals['established_deductions'] if rentals else ZERO
        has_transfers=any(i.category=='capital_gain' for i in case.incomes)
        if p.transfers and not has_transfers:raise ValueError('Transfer workpapers require saved transfer income')
        transfers=transfer_tax(case,p.transfers) if has_transfers else None
        transfer_deductions=sum((r.original_cost+r.reasonable_transfer_expenses+r.allowed_donation for r in p.transfers),ZERO)
        if rental_deductions+transfer_deductions+p.comprehensive_deductions+sum((r.business_deductions for r in p.countries),ZERO)!=case.claimed_deductions:
            raise ValueError('Category deductions including transfer costs and rental taxes, subrent, repairs used and donations must reconcile to saved deductions, excluding statutory expenses and basic60000')
        if sum((r.business_prior_losses for r in p.countries),ZERO)!=case.carried_losses:
            raise ValueError('Country business losses must reconcile to saved eligible losses')
        rows=[];reconciliation=[]
        for r in p.countries:
            items=[i for i in case.incomes if i.source_jurisdiction==r.country]
            if not items and (not r.prior_excess or r.business_deductions or r.business_prior_losses or r.eligible_foreign_tax_paid):
                raise ValueError('Extra country is only for established prior excess')
            if r.country!='cn' and any(i.foreign_tax_paid is None for i in items):
                raise ValueError('Foreign paid tax must be explicit, including zero')
            paid=sum((i.foreign_tax_paid or ZERO for i in items),ZERO)
            if r.eligible_foreign_tax_paid>paid or (r.country=='cn' and (paid or r.prior_excess)):
                raise ValueError('Eligible foreign tax cannot exceed saved paid tax or attach to domestic income')
            comp=sum((i.gross_amount*FACTORS[i.category] for i in items if i.category in FACTORS),ZERO)
            gross_business=sum((i.gross_amount for i in items if i.category=='business'),ZERO)
            business=gross_business-r.business_deductions-r.business_prior_losses
            if business<0:raise ValueError('Negative country business income or unused losses need separate loss tracking')
            investment=sum((i.gross_amount for i in items if i.category in ('dividend','interest')),ZERO)
            investment_tax=investment*Decimal('.2')
            country_transfer_tax=sum((v['tax_after_reduction'] for v in transfers['transactions'] if v['country']==r.country),ZERO) if transfers else ZERO
            country_rental_tax=sum((v['tax_after_reduction'] for v in rentals['properties'] if v['country']==r.country),ZERO) if rentals else ZERO
            other=investment_tax+country_transfer_tax+country_rental_tax
            rows.append(dict(country=r.country,comprehensive_income_amount=comp,business_taxable_income=business,
                other_category_chinese_tax=other,eligible_foreign_tax_paid=r.eligible_foreign_tax_paid,prior_excess=r.prior_excess))
            reconciliation.append(dict(country=r.country,comprehensive_income_amount=comp,gross_business_income=gross_business,
                business_deductions=r.business_deductions,business_prior_losses=r.business_prior_losses,
                business_taxable_income=business,investment_income=investment,investment_tax=investment_tax,transfer_tax=country_transfer_tax,rental_tax=country_rental_tax,foreign_tax_paid=paid))
        comp_total=sum((r['comprehensive_income_amount'] for r in rows),ZERO)
        if not comp_total and p.comprehensive_deductions:raise ValueError('Comprehensive deductions require comprehensive income')
        comp_base=max(ZERO,comp_total-Decimal('60000')-p.comprehensive_deductions)
        comp_tax=marginal_tax(comp_base,COMPREHENSIVE_BANDS,computed_base=True)[0]
        business_base=sum((r['business_taxable_income'] for r in rows),ZERO)
        business_tax=marginal_tax(business_base,BANDS,computed_base=True)[0]
        result=calculate(dict(tax_year=2026,countries=rows,worldwide_comprehensive_tax=comp_tax,
            worldwide_business_tax=business_tax,comprehensive_tax_reductions=p.comprehensive_tax_reductions,
            business_tax_reductions=p.business_tax_reductions,resident_source_fx_and_category_bases_verified=True,
            annual_category_taxes_and_reliefs_verified=True,direct_paid_tax_eligibility_and_evidence_verified=True,
            carryforward_history_verified=True))
        before=comp_tax-p.comprehensive_tax_reductions+business_tax-p.business_tax_reductions+sum((r['other_category_chinese_tax'] for r in rows),ZERO)
        final=before-result['allowed_credit']
        result.update(country_basis_reconciliation=reconciliation,comprehensive_taxable_income=comp_base,
            business_taxable_income=business_base,tax_before_foreign_credit=before,annual_liability=final,
            final_tax=final,prepaid_tax=prepaid_tax,balance_due=final-prepaid_tax,
            tax_scope='china_resident_ordinary_comprehensive_business_investment_foreign_credit',
            stage='annual_workpaper_before_filing_rounding',
            scope_note='Ordinary comprehensive, nonnegative country business bases and ordinary20percent dividend/interest and separately established ordinary property transfers. Excludes rental, special bonuses/equity, treaty deemed credits and automatic business incentive eligibility. Verified reductions, FX, deductions and loss histories required; domestic investment tax included in full-year total, not a B-form filing instruction.')
        if transfers:result['property_transfers']=transfers
        if rentals:
            result['property_rentals']=rentals
            result['scope_note']=result['scope_note'].replace('Excludes rental, special','Includes separately established ordinary20percent monthly rental workpapers. Excludes special')
        sources=result['sources']+[SOURCE_BY_ID['cn.law.iit'],SOURCE_BY_ID['cn.iit.comprehensive-rate-table']]+BUSINESS_SOURCES
        if rentals:sources+=rentals['sources']
        result['sources']=deepcopy(list({s['doc_id']:s for s in sources}.values()))
        return result
