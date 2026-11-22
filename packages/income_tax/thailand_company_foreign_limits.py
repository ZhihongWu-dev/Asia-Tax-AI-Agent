"""Notification65 clauses3-5: ordinary-rate country limits, not settlement.

Inputs are reconciled Thai-law bases. Annual expense interaction, overall
liability, treaty entitlement and SME rates are deliberately not inferred.
"""
from decimal import Decimal, localcontext
from datetime import date
from fractions import Fraction
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool
from packages.contracts.income_tax import Money, Jurisdiction


class ForeignPeriodTax(BaseModel):
    """One paid foreign assessment, split on actual profits or gross receipts.

    Amounts use the foreign assessment currency. Market FX is THB per unit on
    payment date. A loss-containing allocation requires separate review.
    """
    model_config = ConfigDict(extra='forbid')
    foreign_period_start: date
    foreign_period_end: date
    thai_period_start: date
    thai_period_end: date
    foreign_tax_base: Literal['net_profit', 'gross_receipts']
    total_foreign_period_basis: Money
    basis_in_overlapping_period: Money
    foreign_tax_paid: Money
    payment_date: date
    payment_date_market_thb_per_unit: Money
    thai_return_filed_on: date | None = None
    actual_period_basis_and_payment_evidence_verified: StrictBool


def allocate_foreign_period_tax(workpaper):
    """Notification65 clauses7-9; not day-proration or income-year FX.

    The exact fraction is retained alongside a decimal for downstream audit.
    The caller still needs Thai-law income/expense reconciliation and credit
    eligibility. Payment timing determines amendment, not income attribution.
    """
    p = ForeignPeriodTax.model_validate(workpaper)
    if not p.actual_period_basis_and_payment_evidence_verified:
        raise ValueError('Actual period basis and foreign payment evidence require verification')
    if p.foreign_period_start > p.foreign_period_end or p.thai_period_start > p.thai_period_end:
        raise ValueError('Accounting periods must be ordered')
    start = max(p.foreign_period_start, p.thai_period_start)
    end = min(p.foreign_period_end, p.thai_period_end)
    if start > end:
        raise ValueError('Foreign assessment must overlap the Thai accounting period')
    total, overlap = p.total_foreign_period_basis, p.basis_in_overlapping_period
    if total <= 0 or overlap > total:
        raise ValueError('Positive total basis and an overlap between zero and total are required')
    if (start, end) == (p.foreign_period_start, p.foreign_period_end) and overlap != total:
        raise ValueError('A fully covered foreign period requires the full foreign basis')
    if p.payment_date_market_thb_per_unit <= 0:
        raise ValueError('Payment-date market exchange rate must be positive')
    if p.thai_return_filed_on is not None and p.thai_return_filed_on < p.thai_period_end:
        raise ValueError('Annual return filing cannot precede its accounting period end')
    tax = Fraction(p.foreign_tax_paid) * Fraction(p.payment_date_market_thb_per_unit)
    allocated = tax * Fraction(overlap) / Fraction(total)
    def decimal(value):
        with localcontext() as context:
            context.prec = 40
            return Decimal(value.numerator) / Decimal(value.denominator)
    return dict(foreign_tax_base=p.foreign_tax_base, overlap_start=start, overlap_end=end,
        foreign_period_start=p.foreign_period_start, foreign_period_end=p.foreign_period_end,
        thai_period_start=p.thai_period_start, thai_period_end=p.thai_period_end,
        payment_date=p.payment_date, payment_date_market_thb_per_unit=p.payment_date_market_thb_per_unit,
        total_foreign_period_basis=total, basis_in_overlapping_period=overlap,
        foreign_tax_paid_thb=decimal(tax), allocated_tax_before_credit_limits=decimal(allocated),
        tax_outside_thai_period=decimal(tax-allocated),
        exact_allocated_tax=dict(numerator=str(allocated.numerator), denominator=str(allocated.denominator)),
        amendment_required=None if p.thai_return_filed_on is None else p.payment_date > p.thai_return_filed_on,
        amendment_timing_known=p.thai_return_filed_on is not None,
        stage='foreign_paid_tax_period_allocation_before_credit_limits',
        legal_reference='https://www.rd.go.th/3161.html', locator='Clauses7-9')


class CountryBasis(BaseModel):
    model_config = ConfigDict(extra='forbid')
    country: Jurisdiction
    treatment: Literal['business_net', 'company_receipts', 'mixed_combined', 'mixed_separate']
    business_revenue: Money = Decimal(0)
    business_allowable_expenses: Money = Decimal(0)
    company_receipts: Money = Decimal(0)
    company_receipt_allowable_expenses: Money = Decimal(0)
    business_foreign_tax_paid: Money = Decimal(0)
    company_receipt_foreign_tax_paid: Money = Decimal(0)
    separate_receipts_excluded_from_foreign_annual_tax_verified: StrictBool = False


class Workpaper(BaseModel):
    model_config = ConfigDict(extra='forbid')
    countries: list[CountryBasis] = Field(min_length=1, max_length=200)
    ordinary_twenty_percent_rate_verified: StrictBool
    thai_law_bases_period_fx_and_paid_tax_evidence_verified: StrictBool


def calculate(workpaper):
    p = Workpaper.model_validate(workpaper)
    if not (p.ordinary_twenty_percent_rate_verified and
            p.thai_law_bases_period_fx_and_paid_tax_evidence_verified):
        raise ValueError('Ordinary rate and reconciled bases, period, FX and paid-tax evidence require verification')
    if len({s.country for s in p.countries}) != len(p.countries):
        raise ValueError('Aggregate each foreign country exactly once')
    rows = []
    with localcontext() as context:
        context.prec = 40
        for s in p.countries:
            if s.country == 'th':
                raise ValueError('Thai income is not a foreign-country basis')
            separate = s.treatment == 'mixed_separate'
            if separate != s.separate_receipts_excluded_from_foreign_annual_tax_verified:
                raise ValueError('Separate mixed receipts require clause4 exclusion verification exactly for that treatment')
            if s.treatment == 'business_net' and any((s.company_receipts,
                    s.company_receipt_allowable_expenses, s.company_receipt_foreign_tax_paid)):
                raise ValueError('Business-only treatment cannot contain company receipts')
            if s.treatment == 'company_receipts' and any((s.business_revenue,
                    s.business_allowable_expenses, s.business_foreign_tax_paid)):
                raise ValueError('Receipts-only treatment cannot contain business amounts')
            if s.treatment != 'mixed_combined' and s.company_receipt_allowable_expenses:
                raise ValueError('Clause3(2) uses receipts before expenses; expenses belong in annual reconciliation')
            parts = []
            def part(kind, base, paid):
                limit = max(Decimal(0), base) * Decimal('.20')
                candidate = min(paid, limit)
                parts.append(dict(kind=kind, basis=base, thai_tax_limit=limit,
                    foreign_tax_paid=paid, credit_before_annual_reconciliation=candidate,
                    excess_before_expense_reconciliation=paid-candidate))
            if s.treatment == 'mixed_combined':
                part('combined_net', s.business_revenue+s.company_receipts-
                     s.business_allowable_expenses-s.company_receipt_allowable_expenses,
                     s.business_foreign_tax_paid+s.company_receipt_foreign_tax_paid)
            else:
                if s.treatment in ('business_net', 'mixed_separate'):
                    part('business_net', s.business_revenue-s.business_allowable_expenses,
                         s.business_foreign_tax_paid)
                if s.treatment in ('company_receipts', 'mixed_separate'):
                    part('company_receipts', s.company_receipts, s.company_receipt_foreign_tax_paid)
            rows.append(dict(country=s.country, treatment=s.treatment, parts=parts))
        candidate = sum((part['credit_before_annual_reconciliation']
                         for row in rows for part in row['parts']), Decimal(0))
    return dict(policy_version='th-notification65-country-limits-20261122', currency='THB',
        countries=rows, credit_before_annual_reconciliation=candidate,
        stage='country_limits_only_before_annual_expense_and_liability_reconciliation',
        annual_settlement_supported=False,
        legal_references=['https://www.rd.go.th/3161.html', 'https://www.rd.go.th/2787.html',
                          'https://www.rd.go.th/49005.html'])
