"""Ordinary rental workpapers for the Chinese resident foreign-income route.

The caller must first establish the month, source, rental aggregation unit and
eligible preceding deductions. Repair entitlement/carry is deliberately not
inferred from an annual expense total here.
"""
from copy import deepcopy
from decimal import Decimal, localcontext
import json
from pathlib import Path
from pydantic import Field, StrictBool, StrictInt, StrictStr

from packages.contracts.income_tax import Money

from .arithmetic import amount
from .china import SOURCE_BY_ID
from .china_personal_foreign_credit import Strict, SOURCES as FOREIGN_SOURCES

SOURCES = json.loads(Path(__file__).with_name('cn_personal_rental_sources.json').read_text(encoding='utf-8'))['sources']


class RentalMonth(Strict):
    month: StrictInt = Field(ge=1, le=12)
    gross_income: Money
    eligible_taxes_and_fees: Money
    eligible_sublease_rent: Money
    eligible_new_repairs: Money
    established_repair_deduction: Money
    allowed_donation: Money
    allowed_tax_reduction: Money


class RentalYear(Strict):
    income_index: StrictInt = Field(ge=0, le=199)
    property_id: StrictStr = Field(min_length=1, max_length=120, pattern=r'^\S(?:.*\S)?$')
    opening_eligible_repairs: Money
    months: list[RentalMonth] = Field(min_length=12, max_length=12)
    ordinary_rate_source_and_monthly_allocation_verified: StrictBool
    property_aggregation_deductions_and_history_verified: StrictBool


def calculate(case, workpapers):
    """Ordinary20% rentals with established monthly allocation and deductions."""
    papers = [RentalYear.model_validate(value) for value in workpapers]
    expected = {n for n, item in enumerate(case.incomes) if item.category == 'rental'}
    indices = [p.income_index for p in papers]
    if not expected or set(indices) != expected or len(set(indices)) != len(indices):
        raise ValueError('Each saved rental income requires exactly one annual property workpaper')
    if len({p.property_id for p in papers}) != len(papers):
        raise ValueError('A property cannot be split into duplicate annual rental workpapers')
    if case.subject != 'individual' or case.jurisdiction != 'cn' or case.residency != 'resident':
        raise ValueError('Chinese resident individual required')
    if str(case.period_start) != '2026-01-01' or str(case.period_end) != '2026-12-31':
        raise ValueError('Calendar2026 required')
    rows = []
    with localcontext() as ctx:
        ctx.prec = 40
        for p in papers:
            if not p.ordinary_rate_source_and_monthly_allocation_verified or not p.property_aggregation_deductions_and_history_verified:
                raise ValueError('Ordinary20percent treatment, source, monthly allocation and property deduction evidence required')
            item = case.incomes[p.income_index]
            if sum((m.gross_income for m in p.months), Decimal(0)) != item.gross_amount:
                raise ValueError('Monthly rental income must reconcile to saved annual gross income')
            ledger = repair_ledger(dict(opening_eligible_repairs=p.opening_eligible_repairs,
                same_property_history_and_monthly_eligibility_verified=True,
                months=[dict(month=m.month, eligible_new_repairs=m.eligible_new_repairs,
                             established_repair_deduction=m.established_repair_deduction) for m in p.months]))
            months = []
            for m in sorted(p.months, key=lambda row: row.month):
                deductions = m.eligible_taxes_and_fees + m.eligible_sublease_rent + m.established_repair_deduction
                base = monthly_expense_base(m.gross_income, deductions)
                taxable = base['income_after_statutory_expense'] - m.allowed_donation
                if taxable < 0:
                    raise ValueError('Donation exceeds monthly rental income after expenses')
                tax = taxable * Decimal('.2')
                if m.allowed_tax_reduction > tax:
                    raise ValueError('Reduction exceeds monthly rental tax')
                months.append(dict(**m.model_dump(),
                    balance_before_statutory_expense=base['balance_before_statutory_expense'],
                    statutory_expense=base['statutory_expense'], taxable_income=taxable,
                    gross_tax=tax, tax_after_reduction=tax-m.allowed_tax_reduction))
            rows.append(dict(income_index=p.income_index, property_id=p.property_id,
                country=item.source_jurisdiction, months=months, repair_ledger=ledger,
                established_deductions=sum((m.eligible_taxes_and_fees+m.eligible_sublease_rent+m.established_repair_deduction+m.allowed_donation for m in p.months), Decimal(0)),
                tax_after_reduction=sum((m['tax_after_reduction'] for m in months), Decimal(0))))
        return dict(properties=rows,
            established_deductions=sum((r['established_deductions'] for r in rows), Decimal(0)),
            tax_after_reduction=sum((r['tax_after_reduction'] for r in rows), Decimal(0)),
            stage='internal_ordinary_rental_component_before_foreign_credit',
            scope_note='Each saved rental row covers one established property and12 explicit months. Ordinary20percent only; housing concessions, deemed assessment, automatic allocation of advance rent and deduction eligibility are not inferred. New repairs are not automatically current deductions. Negative monthly balances require separate treatment. Statutory expenses excluded from established_deductions.',
            sources=deepcopy([SOURCE_BY_ID['cn.law.iit']]+SOURCES+[s for s in FOREIGN_SOURCES if s['doc_id'] in ('cn.reg.iit','cn.cs.2020-03')]))


class RepairMonth(Strict):
    month: StrictInt = Field(ge=1, le=12)
    eligible_new_repairs: Money
    established_repair_deduction: Money


class RepairYear(Strict):
    opening_eligible_repairs: Money
    months: list[RepairMonth] = Field(min_length=12, max_length=12)
    same_property_history_and_monthly_eligibility_verified: StrictBool


def repair_ledger(workpaper):
    """Reconcile established monthly repair deductions for one rental property.

    All months are explicit, including inactive months. This validates chronology,
    the statutory monthly cap and conservation, not deduction eligibility when
    rent is insufficient. The annual calculator also reconciles deductions
    to the corresponding monthly income, tax/fee and subrent workpapers.
    """
    paper = RepairYear.model_validate(workpaper)
    if not paper.same_property_history_and_monthly_eligibility_verified:
        raise ValueError('Same-property repair history and monthly eligibility must be established')
    if {row.month for row in paper.months} != set(range(1, 13)):
        raise ValueError('Each calendar month requires exactly one repair row')
    with localcontext() as ctx:
        ctx.prec = 40
        balance = paper.opening_eligible_repairs
        rows = []
        for row in sorted(paper.months, key=lambda item: item.month):
            available = balance + row.eligible_new_repairs
            used = row.established_repair_deduction
            if used > min(Decimal('800'), available):
                raise ValueError('Monthly repair deduction exceeds800 or available eligible repairs')
            closing = available - used
            rows.append(dict(month=row.month, opening_eligible_repairs=balance,
                eligible_new_repairs=row.eligible_new_repairs,
                established_repair_deduction=used, closing_eligible_repairs=closing))
            balance = closing
        return dict(months=rows, opening_eligible_repairs=paper.opening_eligible_repairs,
            total_new_repairs=sum((r.eligible_new_repairs for r in paper.months), Decimal(0)),
            total_repair_deductions=sum((r.established_repair_deduction for r in paper.months), Decimal(0)),
            closing_eligible_repairs=balance,
            stage='internal_same_property_repair_reconciliation_not_eligibility_determination',
            sources=deepcopy([s for s in SOURCES if s['doc_id']=='cn.rental.1994-89']))


def monthly_expense_base(gross_income, eligible_preceding_deductions):
    """Apply statutory expenses AFTER established taxes, subrent and repairs.

    This computes a base, not tax or repair eligibility. It cannot establish
    housing relief, foreign credit, a loss carryforward or monthly allocation.
    Inputs are already RMB amounts on the same established monthly basis.
    """
    gross = amount(gross_income)
    preceding = amount(eligible_preceding_deductions)
    with localcontext() as ctx:
        ctx.prec = 40
        if preceding > gross:
            raise ValueError('Deductions exceeding monthly income require separate eligibility and carry treatment')
        balance = gross - preceding
        expense = min(balance, Decimal('800')) if balance <= 4000 else balance * Decimal('.2')
        return {
            'gross_income': gross,
            'eligible_preceding_deductions': preceding,
            'balance_before_statutory_expense': balance,
            'statutory_expense': expense,
            'income_after_statutory_expense': balance - expense,
            'stage': 'internal_monthly_rental_base_before_donation_tax_and_credit',
            'sources': deepcopy([SOURCE_BY_ID['cn.law.iit']] + SOURCES),
        }
