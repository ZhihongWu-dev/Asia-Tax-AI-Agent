"""Current-year direct foreign credits under CTA57 and Decree94.

Verified country bases, without prior credits, tax-sparing, underlying taxes,
income-excluded dividends or other reliefs. Not a national/local settlement.
"""
from decimal import Decimal, localcontext
from fractions import Fraction
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from packages.contracts.income_tax import Jurisdiction, Money
from .arithmetic import computed_amount


class Country(BaseModel):
    model_config=ConfigDict(extra='forbid')
    country: Jurisdiction
    foreign_income_before_corresponding_expenses: Money
    corresponding_expenses: Money
    allocated_losses_exclusions_and_deductions: Money
    income_reduction_for_tax_relief: Money
    foreign_tax_paid_or_payable: Money
    eligible_direct_foreign_tax: Money


class Workpaper(BaseModel):
    model_config=ConfigDict(extra='forbid')
    countries: list[Country]=Field(min_length=1,max_length=10)
    resident_company_and_direct_tax_scope_verified: StrictBool
    country_income_expenses_and_relief_allocations_verified: StrictBool
    treaty_caps_payment_fx_and_filing_evidence_verified: StrictBool
    no_prior_credits_other_reliefs_or_source_losses_verified: StrictBool


def calculate(workpaper, *, national_tax_before_credit, national_taxable_base):
    p=Workpaper.model_validate(workpaper)
    if not all((p.resident_company_and_direct_tax_scope_verified,
        p.country_income_expenses_and_relief_allocations_verified,
        p.treaty_caps_payment_fx_and_filing_evidence_verified,
        p.no_prior_credits_other_reliefs_or_source_losses_verified)):
        raise ValueError('Verify direct-tax scope, country bases, expenses, treaty caps, evidence and exclusions')
    codes=[c.country for c in p.countries]
    if 'kr' in codes or len(codes)!=len(set(codes)):
        raise ValueError('Foreign countries must be unique and exclude Korea')
    tax=Fraction(computed_amount(national_tax_before_credit))
    base=Fraction(computed_amount(national_taxable_base))
    if not base:
        raise ValueError('Positive national taxable base required; loss cases need separate treatment')
    rows=[];net_total=Fraction(0);credit_total=Fraction(0)
    with localcontext() as context:
        context.prec=40
        def decimal(value):return Decimal(value.numerator)/Decimal(value.denominator)
        for c in p.countries:
            gross,expenses,adjustments,relief,paid,eligible=map(Fraction,(
                c.foreign_income_before_corresponding_expenses,c.corresponding_expenses,
                c.allocated_losses_exclusions_and_deductions,c.income_reduction_for_tax_relief,
                c.foreign_tax_paid_or_payable,c.eligible_direct_foreign_tax))
            before=gross-adjustments-relief
            after=before-expenses
            if after<0:
                raise ValueError('Country source loss or adjustments exceeding income require separate review')
            if eligible>paid:
                raise ValueError('Eligible direct tax exceeds paid or payable foreign tax')
            net_total+=after
            pre_limit=tax*before/base
            limit=tax*after/base
            credit=min(eligible,limit)
            unused=eligible-credit
            # Decree94(15) removes the expense-related portion from ordinary
            # carryforward. It cannot exceed the actual eligible unused tax.
            expense_excess=min(unused,pre_limit-limit)
            carry=unused-expense_excess
            credit_total+=credit
            values=dict(income_before_corresponding_expenses=before,
                income_for_credit_limit=after,limit_before_corresponding_expenses=pre_limit,
                credit_limit=limit,current_foreign_tax_credit=credit,
                expense_related_excess_not_carried=expense_excess,
                eligible_current_year_carryforward=carry,foreign_tax_excluded=paid-eligible)
            rows.append(dict(country=c.country,**{k:decimal(v) for k,v in values.items()},
                exact_amounts={k:dict(numerator=str(v.numerator),denominator=str(v.denominator)) for k,v in values.items()}))
        if net_total>base:
            raise ValueError('Country income exceeds total base; domestic losses and competing limits need separate allocation')
        return dict(policy_version='kr-direct-country-credit-component-20261122',currency='KRW',
            country_credits=rows,current_foreign_tax_credit=decimal(credit_total),
            national_tax_after_current_credit=decimal(tax-credit_total),
            stage='current_direct_country_credits_before_history_other_reliefs_local_tax_and_settlement',
            sources=[dict(doc_id='kr.corporate-tax-act.20260701.ko',
                url='https://www.law.go.kr/LSW/lsInfoP.do?lsId=001563',
                file='database/raw/kr/kr.corporate-tax-act.20260701.ko.pdf',
                sha256='257a709a6264d79df36f9f0d4ec42934304a0d07e99dcb875606e5c4ed21c599',provisions=['Article57(1),(2),(7)']),
                dict(doc_id='kr.corporate-decree.20261001',
                    url='https://www.law.go.kr/LSW/lsInfoR.do?lsiSeq=290843&efYd=20261001&chrClsCd=010202&lsId=003608',
                    file='database/raw/kr/kr.corporate-decree.20261001.html',
                    sha256='765c698aedb7b4a5dc78b76f768bf3200801137900153bf2b639e634e4fb8f2a',
                    provisions=['Article94(1),(2),(6),(7),(15)'])])
