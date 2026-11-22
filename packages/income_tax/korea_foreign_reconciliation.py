"""Reconcile saved ordinary company income with Korean country-credit bases.

Corresponding expenses are distinguished from expenses already included in
foreign income. This prepares inputs, not a completed national/local return.
"""
from decimal import Decimal, localcontext
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt
from packages.contracts.income_tax import Money
from .korea_foreign_credit import Country


class Group(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source_id: str = Field(min_length=1, max_length=120, pattern=r'\S')
    income_indexes: list[StrictInt] = Field(min_length=1, max_length=200)
    expenses_already_in_foreign_income: Money
    corresponding_expenses: Money
    eligible_direct_foreign_tax: Money


class SavedWorkpaper(BaseModel):
    model_config = ConfigDict(extra='forbid')
    groups: list[Group] = Field(min_length=1, max_length=200)
    korean_income_basis_and_expense_classification_verified: StrictBool
    direct_paid_tax_treaty_fx_and_filing_evidence_verified: StrictBool
    no_losses_exemptions_special_income_or_other_base_adjustments_verified: StrictBool


def reconcile(case, workpaper):
    p = SavedWorkpaper.model_validate(workpaper)
    if not all((p.korean_income_basis_and_expense_classification_verified,
            p.direct_paid_tax_treaty_fx_and_filing_evidence_verified,
            p.no_losses_exemptions_special_income_or_other_base_adjustments_verified)):
        raise ValueError('Verify Korean income basis, expense classification, foreign tax evidence and adjustments')
    if (case.subject != 'company' or case.jurisdiction != 'kr' or case.residency != 'resident'
            or case.missing_for_calculation() or case.carried_losses):
        raise ValueError('Confirmed Korean resident company without carried losses required')
    if (case.period_start.isoformat(), case.period_end.isoformat()) != ('2026-01-01', '2026-12-31'):
        raise ValueError('Reviewed calendar business year2026 required')
    indexes = [i for g in p.groups for i in g.income_indexes]
    ids = [g.source_id.strip() for g in p.groups]
    if sorted(indexes) != list(range(len(case.incomes))) or len(ids) != len(set(ids)):
        raise ValueError('Unique source groups must cover every saved income exactly once')
    countries, rows = {}, []
    with localcontext() as context:
        context.prec = 40
        expenses = sum((g.expenses_already_in_foreign_income + g.corresponding_expenses
                        for g in p.groups), Decimal(0))
        if expenses != case.claimed_deductions:
            raise ValueError('Both expense classes must reconcile to saved deductions without duplication')
        total = Decimal(0)
        for g in p.groups:
            items = [case.incomes[i] for i in g.income_indexes]
            codes = {i.source_jurisdiction for i in items}
            categories = {i.category for i in items}
            if len(codes) != 1 or len(categories) != 1 or not categories <= {'business', 'interest', 'royalty', 'rental'}:
                raise ValueError('Each group requires one country and ordinary company income category')
            country = next(iter(codes))
            gross = sum((i.gross_amount for i in items), Decimal(0))
            before = gross - g.expenses_already_in_foreign_income
            net = before - g.corresponding_expenses
            if net < 0:
                raise ValueError('Source losses require separate statutory allocation')
            total += net
            if country == 'kr':
                if g.corresponding_expenses or g.eligible_direct_foreign_tax or any(i.foreign_tax_paid not in (None, 0) for i in items):
                    raise ValueError('Domestic sources cannot carry foreign tax or foreign corresponding expenses')
                paid = Decimal(0)
            else:
                if any(i.foreign_tax_paid is None for i in items):
                    raise ValueError('Record foreign tax paid, including zero')
                paid = sum((i.foreign_tax_paid for i in items), Decimal(0))
                if g.eligible_direct_foreign_tax > paid:
                    raise ValueError('Eligible direct tax cannot exceed saved foreign tax paid')
                row = countries.setdefault(country, dict(country=country,
                    foreign_income_before_corresponding_expenses=Decimal(0), corresponding_expenses=Decimal(0),
                    allocated_losses_exclusions_and_deductions=Decimal(0), income_reduction_for_tax_relief=Decimal(0),
                    foreign_tax_paid_or_payable=Decimal(0), eligible_direct_foreign_tax=Decimal(0)))
                for key, value in (('foreign_income_before_corresponding_expenses', before),
                        ('corresponding_expenses', g.corresponding_expenses),
                        ('foreign_tax_paid_or_payable', paid), ('eligible_direct_foreign_tax', g.eligible_direct_foreign_tax)):
                    row[key] += value
            rows.append(dict(source_id=g.source_id.strip(), country=country, gross_income=gross,
                expenses_already_in_foreign_income=g.expenses_already_in_foreign_income,
                corresponding_expenses=g.corresponding_expenses, net_taxable_income=net,
                foreign_tax_paid=paid, eligible_direct_foreign_tax=g.eligible_direct_foreign_tax))
    if not countries or total <= 0:
        raise ValueError('Positive national base and at least one foreign country required')
    return dict(national_taxable_base=total, source_reconciliation=rows,
        countries=[Country.model_validate(row).model_dump() for row in countries.values()],
        stage='saved_income_reconciliation_before_credit_and_annual_settlement')
