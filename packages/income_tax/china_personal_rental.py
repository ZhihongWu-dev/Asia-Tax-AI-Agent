"""Internal monthly rental expense calculation; not an annual assessment route.

The caller must first establish the month, source, rental aggregation unit and
eligible preceding deductions. Repair entitlement/carry is deliberately not
inferred from an annual expense total here.
"""
from copy import deepcopy
from decimal import Decimal, localcontext
import json
from pathlib import Path

from .arithmetic import amount
from .china import SOURCE_BY_ID

SOURCES = json.loads(Path(__file__).with_name('cn_personal_rental_sources.json').read_text(encoding='utf-8'))['sources']


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
