"""Reconcile saved Hong Kong corporate receipts to FSIE source workpapers.

This prepares an annual basis; it does not determine exemptions or compute
final annual tax. Foreign-tax deductions remain separate from expenses.
"""
from decimal import Decimal, localcontext
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt
from packages.contracts.income_tax import Money
from .hong_kong_foreign_credit import Source, SourceFacts


class FactsGroup(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source_id: str = Field(min_length=1,max_length=120,pattern=r'\S')
    income_indexes: list[StrictInt] = Field(min_length=1,max_length=200)
    allowable_expenses: Money
    taxable_additions: Money
    excluded_income: Money
    underlying_tax_gross_up: Money
    foreign_credit: SourceFacts | None = None


class FactsWorkpaper(BaseModel):
    model_config = ConfigDict(extra='forbid')
    groups: list[FactsGroup] = Field(min_length=1,max_length=200)
    receipt_year_source_exemptions_and_expenses_verified: StrictBool
    gross_up_and_no_foreign_tax_in_expenses_verified: StrictBool
    no_source_losses_or_special_regimes_verified: StrictBool


class Group(FactsGroup):
    foreign_credit: Source | None = None


class Workpaper(FactsWorkpaper):
    groups: list[Group] = Field(min_length=1,max_length=200)


def reconcile(case, workpaper):
    return _reconcile(case, Workpaper.model_validate(workpaper))


def reconcile_facts(case, workpaper):
    """Reconcile saved receipts before same-income tax limits are computed."""
    return _reconcile(case, FactsWorkpaper.model_validate(workpaper))


def _reconcile(case, p):
    if not all((p.receipt_year_source_exemptions_and_expenses_verified,
            p.gross_up_and_no_foreign_tax_in_expenses_verified,
            p.no_source_losses_or_special_regimes_verified)):
        raise ValueError('Receipt year, source, exemptions, expenses, gross-up and regime evidence required')
    if (case.subject!='company' or case.jurisdiction!='hk' or case.residency!='resident'
            or case.missing_for_calculation() or case.carried_losses):
        raise ValueError('Confirmed resident Hong Kong company without prior losses required')
    indexes=[n for g in p.groups for n in g.income_indexes]
    ids=[g.source_id.strip() for g in p.groups]
    if sorted(indexes)!=list(range(len(case.incomes))) or len(ids)!=len(set(ids)):
        raise ValueError('Unique sources must cover every saved income exactly once')
    rows=[];credits=[]
    categories={'interest':'interest','dividend':'dividend','capital_gain':'disposal_gain','royalty':'ip_income'}
    with localcontext() as context:
        context.prec=40
        if sum((g.allowable_expenses for g in p.groups),Decimal(0))!=case.claimed_deductions:
            raise ValueError('Source expenses must reconcile saved deductions')
        for g in p.groups:
            items=[case.incomes[n] for n in g.income_indexes]
            countries={i.source_jurisdiction for i in items};kinds={i.category for i in items}
            if len(countries)!=1 or len(kinds)!=1:
                raise ValueError('Each source must have one country and income category')
            country=next(iter(countries));kind=next(iter(kinds))
            gross=sum((i.gross_amount for i in items),Decimal(0))
            available=gross+g.taxable_additions+g.underlying_tax_gross_up
            if g.excluded_income>available:
                raise ValueError('Excluded income exceeds source income and additions')
            net=available-g.excluded_income-g.allowable_expenses
            if net<0:
                raise ValueError('Source losses require separate loss-allocation workpaper')
            c=g.foreign_credit
            if country=='hk':
                if c is not None or g.underlying_tax_gross_up or any(i.foreign_tax_paid not in (None,0) for i in items):
                    raise ValueError('Domestic source cannot claim foreign tax or underlying gross-up')
            elif c is not None:
                if kind not in categories or c.income_type!=categories[kind]:
                    raise ValueError('FSIE credit category must match saved income')
                if c.country!=country or c.source_id.strip()!=g.source_id.strip():
                    raise ValueError('Credit source identity must match saved income')
                paid=sum((i.foreign_tax_paid for i in items),Decimal(0))
                if paid!=c.direct_foreign_tax_paid:
                    raise ValueError('Direct foreign tax must reconcile saved payments; underlying tax is separate')
                if not net and ((isinstance(c,Source) and c.hong_kong_tax_on_same_income)
                                or c.direct_foreign_tax_paid or c.underlying_tax_paid):
                    raise ValueError('Excluded or zero-income source cannot claim foreign credits')
                if kind!='dividend' and g.underlying_tax_gross_up:
                    raise ValueError('Underlying tax gross-up is only available for dividends')
                if g.underlying_tax_gross_up>c.underlying_tax_paid:
                    raise ValueError('Underlying gross-up exceeds established underlying tax')
                credits.append(c.model_dump())
            elif net or g.underlying_tax_gross_up:
                raise ValueError('Taxable foreign source requires an FSIE credit workpaper, including zero paid tax')
            rows.append(dict(source_id=g.source_id.strip(),country=country,category=kind,
                saved_gross_income=gross,allowable_expenses=g.allowable_expenses,
                taxable_additions=g.taxable_additions,excluded_income=g.excluded_income,
                underlying_tax_gross_up=g.underlying_tax_gross_up,
                source_basis_before_excess_foreign_tax_deduction=net))
        total=sum((r['source_basis_before_excess_foreign_tax_deduction'] for r in rows),Decimal(0))
    if not credits:
        raise ValueError('At least one taxable foreign source workpaper required')
    return dict(source_reconciliation=rows,foreign_credit_sources=credits,
        total_basis_before_excess_foreign_tax_deduction=total,
        stage='saved_receipt_reconciliation_before_credit_and_annual_settlement')
