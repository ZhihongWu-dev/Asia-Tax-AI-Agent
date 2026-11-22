"""Reconciled ordinary Indonesian resident-company annual foreign credits."""
from decimal import Decimal, localcontext
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt
from packages.contracts.income_tax import Money
from . import indonesia
from .indonesia_foreign_credit import calculate
from .arithmetic import amount


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class SourceGroup(Strict):
    source_id: str = Field(min_length=1,max_length=120)
    income_indexes: list[StrictInt] = Field(min_length=1,max_length=200)
    additions: Money
    allowed_expenses: Money
    exempt_income: Money
    creditable_foreign_tax: Money
    treaty_applies: StrictBool
    treaty_permitted_tax: Money | None = None
    separate_source_and_taxable_treatment_verified: StrictBool


class SavedWorkpaper(Strict):
    groups: list[SourceGroup] = Field(min_length=1,max_length=200)
    prior_credit_reduction_or_refund: Money
    ordinary_resident_no_final_special_or_carried_losses_verified: StrictBool
    complete_article31e_gross_receipts_verified: StrictBool
    source_period_expenses_and_fx_verified: StrictBool
    treaty_entitlement_and_tax_evidence_verified: StrictBool
    recapture_of_previously_credited_tax_verified: StrictBool


def assess(case, workpaper, prepaid_tax):
    p=SavedWorkpaper.model_validate(workpaper)
    if (case.jurisdiction!='id' or case.subject!='company' or case.residency!='resident'
            or case.missing_for_calculation()):
        raise ValueError('Confirmed Indonesian resident company facts required')
    if (case.period_start.isoformat(),case.period_end.isoformat())!=('2026-01-01','2026-12-31'):
        raise ValueError('Calendar2026 required')
    if not p.ordinary_resident_no_final_special_or_carried_losses_verified or case.carried_losses:
        raise ValueError('Ordinary company without final/special regimes or carried losses required')
    ids=[g.source_id for g in p.groups]
    indexes=[n for g in p.groups for n in g.income_indexes]
    if len(set(ids))!=len(ids) or sorted(indexes)!=list(range(len(case.incomes))):
        raise ValueError('Unique groups must cover every saved income exactly once')
    with localcontext() as ctx:
        ctx.prec=40
        if sum((g.allowed_expenses for g in p.groups),Decimal(0))!=case.claimed_deductions:
            raise ValueError('Group expenses must reconcile to saved deductions')
        domestic=Decimal(0); foreign={}; reconciliation=[]
        turnover=sum((i.gross_amount for i in case.incomes),Decimal(0))
        for group in p.groups:
            items=[case.incomes[n] for n in group.income_indexes]
            countries={i.source_jurisdiction for i in items}; categories={i.category for i in items}
            if (len(countries)!=1 or len(categories)!=1 or not group.separate_source_and_taxable_treatment_verified
                    or not categories<={'business','interest','royalty','rental','dividend','capital_gain'}):
                raise ValueError('Each independently verified source must have one country and eligible income type')
            country=next(iter(countries));category=next(iter(categories))
            gross=sum((i.gross_amount for i in items),Decimal(0))
            paid=sum((i.foreign_tax_paid or Decimal(0) for i in items),Decimal(0))
            if group.exempt_income>gross or group.creditable_foreign_tax>paid:
                raise ValueError('Exemption or creditable foreign tax exceeds saved amount')
            if group.exempt_income and (group.creditable_foreign_tax or group.allowed_expenses):
                raise ValueError('Separate exempt receipts and their costs from taxable-source deductions and credits')
            net=gross+group.additions-group.exempt_income-group.allowed_expenses
            excluded_loss=Decimal(0)
            if country=='id':
                if paid or group.creditable_foreign_tax or group.treaty_applies or group.treaty_permitted_tax is not None:
                    raise ValueError('Domestic sources cannot carry foreign credit inputs')
                domestic+=net
            else:
                if any(i.foreign_tax_paid is None for i in items):
                    raise ValueError('Record foreign tax including explicit zero')
                if group.treaty_applies != (group.treaty_permitted_tax is not None):
                    raise ValueError('Explicit treaty ceiling required exactly when treaty applies')
                excluded_loss=max(Decimal(0),-net)
                key=(country,category)
                row=foreign.setdefault(key,dict(country=country,category=category,net_taxable_income=Decimal(0),
                    foreign_tax=Decimal(0),treaty_applies=group.treaty_applies,
                    treaty_permitted_tax=Decimal(0) if group.treaty_applies else None))
                if row['treaty_applies']!=group.treaty_applies:
                    raise ValueError('Country/type treaty applicability must be consistent')
                row['net_taxable_income']+=max(Decimal(0),net)
                row['foreign_tax']+=group.creditable_foreign_tax
                if group.treaty_applies: row['treaty_permitted_tax']+=group.treaty_permitted_tax
            reconciliation.append(dict(source_id=group.source_id,income_indexes=group.income_indexes,
                country=country,category=category,gross_income=gross,additions=group.additions,
                exempt_income=group.exempt_income,allowed_expenses=group.allowed_expenses,
                net_income=net,excluded_foreign_loss=excluded_loss,foreign_tax_paid=paid))
        if not foreign:
            raise ValueError('At least one foreign income source required')
        raw=max(Decimal(0),domestic+sum((r['net_taxable_income'] for r in foreign.values()),Decimal(0)))
        annual=indonesia.company_tax(raw,tax_year=2026,article31e_gross_receipts=turnover,
            ordinary_annual_treatment_confirmed=True,gross_receipts_scope_confirmed=p.complete_article31e_gross_receipts_verified,
            prepaid_tax='0')
        result=calculate(dict(taxable_income=annual['taxable_income'],foreign_incomes=list(foreign.values()),
            prior_credit_reduction_or_refund=p.prior_credit_reduction_or_refund,
            taxable_scope_source_period_and_fx_verified=p.source_period_expenses_and_fx_verified,
            treaty_entitlement_and_tax_evidence_verified=p.treaty_entitlement_and_tax_evidence_verified,
            recapture_of_previously_credited_tax_verified=p.recapture_of_previously_credited_tax_verified),
            indonesian_tax_before_credit=annual['final_tax'])
        prepaid=amount(prepaid_tax)
        result.update(tax_year=2026,taxable_income_before_rounding=raw,source_reconciliation=reconciliation,
            article31e={k:v for k,v in annual.items() if k.startswith('article31e_') or k=='ordinary_rate_tax'},
            gross_tax=annual['final_tax'],final_tax=result['liability_after_recapture'],
            annual_liability=result['liability_after_recapture'],prepaid_tax=prepaid,
            balance_due=result['liability_after_recapture']-prepaid,
            stage='ordinary_resident_company_foreign_credit_before_return_rounding')
        result['sources'].extend(annual['sources'])
        return result
