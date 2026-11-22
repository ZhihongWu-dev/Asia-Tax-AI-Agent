"""UAE resident-company direct FTC reconciled to confirmed saved income groups."""
from copy import deepcopy
from decimal import Decimal,localcontext
import json
from pathlib import Path
from pydantic import Field,StrictBool,StrictInt
from packages.contracts.income_tax import Money
from .uae_foreign_credit import Strict,calculate
from .united_arab_emirates import SOURCES,BASIS_SOURCES
from .arithmetic import amount


class IncomeGroup(Strict):
    source_id: str=Field(min_length=1,max_length=120)
    income_indexes: list[StrictInt]=Field(min_length=1,max_length=200)
    taxable_additions: Money
    linked_deductions: Money
    exempt_income: Money
    eligible_foreign_tax: Money
    source_treatment_and_eligibility_verified: StrictBool


class SavedWorkpaper(Strict):
    groups: list[IncomeGroup]=Field(min_length=1,max_length=200)
    ordinary_resident_company_no_reliefs_verified: StrictBool
    distinct_sources_and_linked_expenses_verified: StrictBool
    foreign_tax_eligibility_treaty_and_fx_verified: StrictBool


def assess(case,workpaper,prepaid_tax):
    p=SavedWorkpaper.model_validate(workpaper)
    if (case.jurisdiction!='ae' or case.subject!='company' or case.residency!='resident'
            or case.missing_for_calculation()):
        raise ValueError('Confirmed UAE resident company facts required')
    if (case.period_start.isoformat(),case.period_end.isoformat())!=('2026-01-01','2026-12-31'):
        raise ValueError('Calendar2026 required')
    if not p.ordinary_resident_company_no_reliefs_verified or case.carried_losses:
        raise ValueError('Ordinary standalone company without relief elections or carried losses required')
    ids=[g.source_id for g in p.groups]
    indexes=[n for g in p.groups for n in g.income_indexes]
    if len(ids)!=len(set(ids)) or sorted(indexes)!=list(range(len(case.incomes))):
        raise ValueError('Unique source groups must cover every saved income exactly once')
    with localcontext() as ctx:
        ctx.prec=40
        if sum((g.linked_deductions for g in p.groups),Decimal(0))!=case.claimed_deductions:
            raise ValueError('Linked expenses must reconcile to saved deductions')
        domestic=Decimal(0);foreign=[];reconciliation=[]
        for group in p.groups:
            items=[case.incomes[n] for n in group.income_indexes]
            countries={i.source_jurisdiction for i in items}
            categories={i.category for i in items}
            if len(countries)!=1 or len(categories)!=1 or not group.source_treatment_and_eligibility_verified:
                raise ValueError('Each verified source must have one country and income category')
            if not categories<={'business','interest','dividend','rental','royalty','capital_gain'}:
                raise ValueError('Unsupported corporate income category')
            country=next(iter(countries))
            if country!='ae' and any(i.foreign_tax_paid is None for i in items):
                raise ValueError('Record foreign paid tax, including explicit zero')
            gross=sum((i.gross_amount for i in items),Decimal(0))
            paid=sum((i.foreign_tax_paid or Decimal(0) for i in items),Decimal(0))
            net=gross+group.taxable_additions-group.exempt_income-group.linked_deductions
            if group.exempt_income>gross or net<0:
                raise ValueError('Exclusions or negative source income require separate treatment')
            if group.eligible_foreign_tax>paid:
                raise ValueError('Eligible foreign tax exceeds saved paid tax')
            if country=='ae':
                if paid or group.eligible_foreign_tax:
                    raise ValueError('Domestic income cannot carry foreign tax')
                domestic+=net
            else:
                if group.exempt_income and group.eligible_foreign_tax:
                    raise ValueError('Separate exempt and taxable foreign receipts before claiming credit')
                foreign.append(dict(source_id=group.source_id,country=country,
                    net_taxable_income=net,eligible_foreign_tax=group.eligible_foreign_tax))
            reconciliation.append(dict(source_id=group.source_id,income_indexes=group.income_indexes,
                country=country,gross_income=gross,taxable_additions=group.taxable_additions,
                exempt_income=group.exempt_income,linked_deductions=group.linked_deductions,
                net_taxable_income=net,foreign_tax_paid=paid))
        result=calculate(dict(domestic_taxable_income=domestic,foreign_incomes=foreign,
            ordinary_positive_taxable_income_verified=True,
            distinct_sources_and_linked_expenses_verified=p.distinct_sources_and_linked_expenses_verified,
            foreign_tax_eligibility_treaty_and_fx_verified=p.foreign_tax_eligibility_treaty_and_fx_verified))
        prepaid=amount(prepaid_tax)
        result.update(final_tax=result['tax_after_credit'],annual_liability=result['tax_after_credit'],
            prepaid_tax=prepaid,balance_due=result['tax_after_credit']-prepaid,
            source_reconciliation=reconciliation,
            sources=[deepcopy(SOURCES[0]),*deepcopy(BASIS_SOURCES),
                *json.loads(Path(__file__).with_name('ae_foreign_credit_sources.json').read_text(encoding='utf-8'))['sources']],
            stage='ordinary_resident_company_direct_credit_before_filing_rounding')
        return result
