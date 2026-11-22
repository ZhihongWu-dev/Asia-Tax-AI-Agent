"""Bind Singapore source allocations to saved facts before computing FTC caps."""
from decimal import Decimal, localcontext
from typing import Literal
from pydantic import Field, StrictBool, StrictInt
from packages.contracts.income_tax import Money
from .singapore_foreign_credit import Strict, calculate
from .singapore import company_tax


class SavedSource(Strict):
    income_index: StrictInt = Field(ge=0, le=199)
    eligible_direct_tax: Money
    pool_elected: StrictBool
    headline_rate_percent: Money = Field(le=100)
    credit_entitlement_verified: StrictBool


class SavedGroup(Strict):
    source_id: str = Field(min_length=1, max_length=120)
    kind: Literal['trade', 'passive']
    deductions: Money
    sources: list[SavedSource] = Field(min_length=1, max_length=200)


class SavedWorkpaper(Strict):
    groups: list[SavedGroup] = Field(min_length=1, max_length=200)
    approved_donations: Money
    resident_same_income_and_allocation_verified: StrictBool
    direct_tax_ordinary_positive_sources_verified: StrictBool


def credit_from_saved_case(case, workpaper, *, exemption_scheme, startup_eligibility_confirmed):
    p = SavedWorkpaper.model_validate(workpaper)
    if (case.jurisdiction != 'sg' or case.subject != 'company' or case.residency != 'resident'
            or case.missing_for_calculation()):
        raise ValueError('Complete confirmed Singapore resident company facts required')
    if (case.period_start.isoformat(), case.period_end.isoformat()) != ('2025-01-01', '2025-12-31'):
        raise ValueError('Calendar2025 basis period for YA2026 required')
    if not p.direct_tax_ordinary_positive_sources_verified or case.carried_losses:
        raise ValueError('Direct ordinary positive sources without carried losses require verification')
    indexes = [s.income_index for g in p.groups for s in g.sources]
    if sorted(indexes) != list(range(len(case.incomes))):
        raise ValueError('Every saved income must occur exactly once')
    groups = []
    with localcontext() as ctx:
        ctx.prec = 40
        deductions = sum((g.deductions for g in p.groups), Decimal(0)) + p.approved_donations
        if deductions != case.claimed_deductions:
            raise ValueError('Group deductions and donations must reconcile to saved deductions')
        for group in p.groups:
            if group.kind == "passive" and len({case.incomes[s.income_index].category for s in group.sources}) != 1:
                raise ValueError("Different passive income categories require separate source groups")
            buckets = {}
            for source in group.sources:
                item = case.incomes[source.income_index]
                if group.kind == 'trade' and item.category != 'business':
                    raise ValueError('Trade groups require saved business income')
                if group.kind == 'passive' and item.category not in ('interest', 'dividend', 'rental', 'royalty'):
                    raise ValueError('Passive group requires identified passive income')
                if item.foreign_tax_paid is None and item.source_jurisdiction != 'sg':
                    raise ValueError('Foreign paid tax must be recorded, including explicit zero')
                if source.eligible_direct_tax > (item.foreign_tax_paid or 0):
                    raise ValueError('Eligible direct credit exceeds saved foreign tax paid')
                key = item.source_jurisdiction
                flags = (source.pool_elected, source.headline_rate_percent, source.credit_entitlement_verified)
                if key in buckets and buckets[key]['flags'] != flags:
                    raise ValueError('Same-source country rows require consistent credit elections')
                row = buckets.setdefault(key, dict(country=key,gross=Decimal(0),eligible_foreign_tax=Decimal(0),flags=flags))
                row['gross'] += item.gross_amount
                row['eligible_foreign_tax'] += source.eligible_direct_tax
            rows=[]
            for row in buckets.values():
                elected, rate, verified = row.pop('flags')
                rows.append(dict(**row,pool_elected=elected,headline_rate_percent=rate,credit_entitlement_verified=verified))
            groups.append(dict(source_id=group.source_id,kind=group.kind,deductions=group.deductions,sources=rows))
        base = sum((i.gross_amount for i in case.incomes), Decimal(0)) - deductions
        if base < 0:
            raise ValueError('Donations exceed remaining positive statutory income')
        tax = company_tax(base,assessment_year=2026,exemption_scheme=exemption_scheme,
            startup_eligibility_confirmed=startup_eligibility_confirmed,cash_grant_eligible=False,allowed_tax_setoff=0)
        result = calculate(dict(groups=groups,singapore_tax_before_credit=tax['gross_tax'],
            resident_same_income_and_allocation_verified=p.resident_same_income_and_allocation_verified))
        result.update(chargeable_income_before_exemption=base,gross_tax_before_credit=tax['gross_tax'],
            stage='saved_fact_credit_workpaper_before_final_settlement')
        return result


def assess(case, workpaper, *, exemption_scheme, startup_eligibility_confirmed,
           cash_grant_eligible, prepaid_tax):
    """Ordinary YA2026 settlement, with derived FTC before the CIT rebate.

    All values precede filing rounding; the separate cash grant is not a
    prepayment and is never subtracted a second time from the balance.
    """
    from copy import deepcopy
    import json
    from pathlib import Path
    from .singapore import COMPANY_BASIS_SOURCES
    from .arithmetic import amount
    prepaid = amount(prepaid_tax)
    credit = credit_from_saved_case(case, workpaper,
        exemption_scheme=exemption_scheme,
        startup_eligibility_confirmed=startup_eligibility_confirmed)
    company = company_tax(credit['chargeable_income_before_exemption'],assessment_year=2026,
        exemption_scheme=exemption_scheme,startup_eligibility_confirmed=startup_eligibility_confirmed,
        cash_grant_eligible=cash_grant_eligible,allowed_tax_setoff=0)
    with localcontext() as ctx:
        ctx.prec = 40
        before_rebate = company['gross_tax'] - credit['allowed_foreign_tax_credit']
        grant = company['cash_grant_separate']
        rebate = max(Decimal(0), min(before_rebate * Decimal('.50'), Decimal('40000')) - grant)
        liability = before_rebate - rebate
        company.update(policy_version='sg-company-foreign-direct-ya2026-20261122',
            foreign_credit=credit,allowed_tax_setoff=credit['allowed_foreign_tax_credit'],
            tax_before_rebate=before_rebate,cit_rebate=rebate,net_tax=liability,
            final_tax=liability,annual_liability=liability,prepaid_tax=prepaid,
            balance_due=liability-prepaid,
            stage='ordinary_direct_foreign_credit_assessment_before_filing_rounding',
            sources=[deepcopy(company['source']),*deepcopy(COMPANY_BASIS_SOURCES),
                *json.loads(Path(__file__).with_name('sg_foreign_credit_sources.json').read_text(encoding='utf-8'))['sources']])
        return company
