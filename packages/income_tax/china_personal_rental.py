"""Internal monthly rental expense calculation; not an annual assessment route.

The caller must first establish the month, source, rental aggregation unit and
eligible preceding deductions. Repair entitlement/carry is deliberately not
inferred from an annual expense total here.
"""
from copy import deepcopy
from decimal import Decimal, localcontext
import json
from pathlib import Path
from pydantic import Field, StrictBool, StrictInt

from packages.contracts.income_tax import Money

from .arithmetic import amount
from .china import SOURCE_BY_ID
from .china_personal_foreign_credit import Strict

SOURCES = json.loads(Path(__file__).with_name('cn_personal_rental_sources.json').read_text(encoding='utf-8'))['sources']


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
    rent is insufficient. The future annual route must also reconcile deductions
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
