"""Ordinary20% Vietnamese company settlement outside annual relief thresholds.

Treaty source entitlement and foreign payments require evidence. This adapter
does not decide the unresolved Decree398 relief/foreign-credit composition.
"""
import json
from copy import deepcopy
from decimal import Decimal, localcontext
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt
from packages.contracts.income_tax import Money
from .arithmetic import amount
from .vietnam_sources import sources_for
from .vietnam_foreign_credit import singapore_interest_royalty_credit, indonesia_deemed_credit

TREATIES=json.loads(Path(__file__).with_name('vn_direct_treaty_sources.json').read_text(encoding='utf-8'))


class Group(BaseModel):
    model_config=ConfigDict(extra='forbid')
    source_id: str=Field(min_length=1,max_length=120,pattern=r'\S')
    income_indexes: list[StrictInt]=Field(min_length=1,max_length=200)
    allowable_expenses: Money
    eligible_foreign_tax_paid: Money


class SavedWorkpaper(BaseModel):
    model_config=ConfigDict(extra='forbid')
    groups: list[Group]=Field(min_length=1,max_length=200)
    previous_full_year_statutory_revenue: Money
    current_full_year_statutory_revenue: Money
    vietnam_establishment_ordinary20_and_full_calendar_periods_verified: StrictBool
    statutory_revenue_and_no_exemptions_incentives_or_losses_verified: StrictBool
    source_basis_expenses_and_no_foreign_tax_deduction_verified: StrictBool
    treaty_source_entitlement_mli_payment_fx_and_filing_verified: StrictBool
    no_other_sparing_underlying_topup_or_special_tax_claims_verified: StrictBool


def assess(case,workpaper,prepaid_tax):
    p=SavedWorkpaper.model_validate(workpaper)
    if not all((p.vietnam_establishment_ordinary20_and_full_calendar_periods_verified,
            p.statutory_revenue_and_no_exemptions_incentives_or_losses_verified,
            p.source_basis_expenses_and_no_foreign_tax_deduction_verified,
            p.treaty_source_entitlement_mli_payment_fx_and_filing_verified,
            p.no_other_sparing_underlying_topup_or_special_tax_claims_verified)):
        raise ValueError('Verify ordinary regime, full-year revenues, source allocation, treaty evidence and exclusions')
    if (case.subject!='company' or case.jurisdiction!='vn' or case.residency!='resident'
            or case.missing_for_calculation() or case.carried_losses):
        raise ValueError('Confirmed resident Vietnam company without carried losses required')
    if (case.period_start.isoformat(),case.period_end.isoformat())!=('2026-01-01','2026-12-31'):
        raise ValueError('Calendar2026 required')
    if p.previous_full_year_statutory_revenue<=Decimal('50000000000'):
        raise ValueError('Prior full-year revenue must exceed the reduced ordinary-rate threshold')
    if p.current_full_year_statutory_revenue<=Decimal('10000000000'):
        raise ValueError('Annual relief/foreign-credit composition requires separate treatment within the Decree398 threshold')
    indexes=[i for g in p.groups for i in g.income_indexes]
    ids=[g.source_id.strip() for g in p.groups]
    if sorted(indexes)!=list(range(len(case.incomes))) or len(ids)!=len(set(ids)):
        raise ValueError('Unique groups must cover every saved income exactly once')
    sources=sources_for('company');rows=[];foreign_count=0
    with localcontext() as context:
        context.prec=40
        revenue=sum((i.gross_amount for i in case.incomes),Decimal(0))
        if revenue!=p.current_full_year_statutory_revenue:
            raise ValueError('Saved ordinary receipts must reconcile to complete current statutory revenue')
        if sum((g.allowable_expenses for g in p.groups),Decimal(0))!=case.claimed_deductions:
            raise ValueError('Group expenses must reconcile to saved deductions')
        total_base=Decimal(0);total_credit=Decimal(0)
        for g in p.groups:
            items=[case.incomes[i] for i in g.income_indexes]
            countries={i.source_jurisdiction for i in items};categories={i.category for i in items}
            if len(countries)!=1 or len(categories)!=1 or not categories<={'business','interest','rental','royalty'}:
                raise ValueError('Each group requires one country and ordinary income category')
            country=next(iter(countries));category=next(iter(categories))
            gross=sum((i.gross_amount for i in items),Decimal(0));net=gross-g.allowable_expenses
            if net<0:
                raise ValueError('Source losses require separate statutory allocation')
            limit=net*Decimal('.20');total_base+=net
            paid=Decimal(0);credit=Decimal(0);credit_basis=Decimal(0);method='domestic'
            if country=='vn':
                if g.eligible_foreign_tax_paid or any(i.foreign_tax_paid not in (None,0) for i in items):
                    raise ValueError('Domestic income cannot claim foreign tax')
            else:
                foreign_count+=1
                if any(i.foreign_tax_paid is None for i in items):
                    raise ValueError('Record foreign tax paid, including zero')
                paid=sum((i.foreign_tax_paid for i in items),Decimal(0))
                if g.eligible_foreign_tax_paid>paid:
                    raise ValueError('Eligible tax exceeds saved foreign payments')
                sources.append(deepcopy(TREATIES[country]))
                credit_basis=g.eligible_foreign_tax_paid;method='treaty_direct_paid'
                if country=='sg' and category in ('interest','royalty'):
                    detail=singapore_interest_royalty_credit(gross,income_type=category,
                        eligible_singapore_tax_paid=g.eligible_foreign_tax_paid,vietnam_tax_limit=0,
                        article11_or12_and_treaty_entitlement_verified=True)
                    credit_basis=detail['credit_basis'];sources.extend(detail['sources']);method='singapore_deemed_floor'
                elif country=='id' and category in ('interest','royalty'):
                    detail=indonesia_deemed_credit(gross,income_type=category,vietnam_tax_limit=0,
                        paragraph2_and_treaty_entitlement_verified=True)
                    credit_basis=detail['deemed_paid_tax'];sources.extend(detail['sources']);method='indonesia_deemed_replacement'
                # Treaty helpers establish the eligible/deemed measure. Apply
                # the derived same-income cap here without six-place input
                # revalidation of an internal decimal product.
                credit=min(credit_basis,limit);total_credit+=credit
            rows.append(dict(source_id=g.source_id.strip(),country=country,category=category,
                gross_income=gross,allowable_expenses=g.allowable_expenses,net_taxable_income=net,
                foreign_tax_paid=paid,eligible_foreign_tax_paid=g.eligible_foreign_tax_paid,
                method=method,credit_basis=credit_basis,vietnam_same_income_limit=limit,
                allowed_credit=credit,credit_basis_above_limit=credit_basis-credit))
        if not foreign_count:
            raise ValueError('At least one foreign source required')
        gross_tax=total_base*Decimal('.20');final=gross_tax-total_credit;prepaid=amount(prepaid_tax)
        merged={}
        for source in sources:
            if source['doc_id'] not in merged:merged[source['doc_id']]=deepcopy(source)
            else:
                old=merged[source['doc_id']]
                old['provisions']=list(dict.fromkeys(old.get('provisions',[])+source.get('provisions',[])))
        return dict(policy_version='vn-company-foreign-ordinary20-2026-20261122',currency='VND',tax_year=2026,
            taxable_income=total_base,ordinary_rate=Decimal('.20'),gross_tax=gross_tax,
            annual_reduction=Decimal(0),allowed_foreign_tax_credit=total_credit,final_tax=final,
            prepaid_tax=prepaid,balance_due=final-prepaid,source_credits=rows,
            previous_full_year_statutory_revenue=p.previous_full_year_statutory_revenue,
            current_full_year_statutory_revenue=revenue,sources=list(merged.values()),
            stage='ordinary20_treaty_credit_settlement_before_filing_rounding_interest_and_penalties')
