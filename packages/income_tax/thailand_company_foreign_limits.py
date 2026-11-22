"""Notification65 clauses3-5: ordinary-rate country limits, not settlement.

Inputs are reconciled Thai-law bases. Annual expense interaction, overall
liability, treaty entitlement and SME rates are deliberately not inferred.
"""
from decimal import Decimal, localcontext
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool
from packages.contracts.income_tax import Money, Jurisdiction


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
