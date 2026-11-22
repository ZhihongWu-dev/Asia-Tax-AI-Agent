"""Reconcile established RD300 country bases to saved annual company facts.

This validates a final expense workpaper, rather than inferring expense
eligibility or solving an assumed excess-tax deduction formula.
"""
from decimal import Decimal, localcontext

from pydantic import BaseModel, ConfigDict, Field, StrictBool
from packages.contracts.income_tax import Money
from .thailand_company_foreign_limits import CountryBasis, calculate

SOURCES = [
    dict(doc_id='th.rd300.foreign-credit', title='Royal Decree300 foreign tax exemption',
         url='https://www.rd.go.th/2787.html', file='database/raw/th/th.rd300.foreign-credit.20261122.html',
         sha256='b2b69039afba7aeb1b477858472681be5669e4f090833ba1ecdaec3fa6656fbc', locator='Section3'),
    dict(doc_id='th.notification65.foreign-credit', title='Notification65 company foreign tax exemption',
         url='https://www.rd.go.th/3161.html', file='database/raw/th/th.notification65.foreign-credit.20261122.html',
         sha256='07351b2c536dbc4ea21059f4a70375b184be5f9e286eecc6eaedee7bf206ba76', locator='Clauses1-11'),
]


class CountryExpenses(BaseModel):
    model_config = ConfigDict(extra='forbid')
    basis: CountryBasis
    annual_allowable_expenses: Money
    foreign_tax_in_annual_expenses: Money


class SavedWorkpaper(BaseModel):
    model_config = ConfigDict(extra='forbid')
    countries: list[CountryExpenses] = Field(min_length=1, max_length=200)
    domestic_allowable_expenses: Money
    thai_incorporation_and_rd300_election_verified: StrictBool
    final_expense_bases_and_foreign_tax_deductions_verified: StrictBool
    source_period_fx_and_certified_payment_evidence_verified: StrictBool


def reconcile(case, workpaper, *, scheme, exempt_income, allowed_tax_credits):
    p = SavedWorkpaper.model_validate(workpaper)
    if not all((p.thai_incorporation_and_rd300_election_verified,
                p.final_expense_bases_and_foreign_tax_deductions_verified,
                p.source_period_fx_and_certified_payment_evidence_verified)):
        raise ValueError('RD300 election, final expense bases and certified tax evidence require verification')
    if (case.subject != 'company' or case.jurisdiction != 'th' or
            case.residency != 'resident' or case.missing_for_calculation()):
        raise ValueError('Confirmed Thai resident company facts required')
    if (case.period_start.isoformat(), case.period_end.isoformat()) != ('2026-01-01', '2026-12-31'):
        raise ValueError('Calendar2026 required')
    if scheme != 'ordinary' or exempt_income or case.carried_losses:
        raise ValueError('RD300 reconciliation currently requires ordinary rate, no exemptions or carried losses')
    by_country = {}
    for income in case.incomes:
        if income.category not in {'business', 'interest', 'royalty', 'rental', 'dividend', 'capital_gain'}:
            raise ValueError('Unsupported corporate income category')
        if income.source_jurisdiction == 'th':
            if income.foreign_tax_paid not in (None, 0):
                raise ValueError('Domestic income cannot carry foreign tax in this RD300 workpaper')
            continue
        if income.foreign_tax_paid is None:
            raise ValueError('Record foreign paid tax, including explicit zero')
        by_country.setdefault(income.source_jurisdiction, []).append(income)
    countries = [row.basis.country for row in p.countries]
    if len(set(countries)) != len(countries) or set(countries) != set(by_country):
        raise ValueError('Workpaper must cover every saved foreign country exactly once')
    limits = calculate(dict(countries=[row.basis.model_dump() for row in p.countries],
        ordinary_twenty_percent_rate_verified=True,
        thai_law_bases_period_fx_and_paid_tax_evidence_verified=True))
    with localcontext() as context:
        context.prec = 40
        if p.domestic_allowable_expenses + sum((r.annual_allowable_expenses for r in p.countries), Decimal(0)) != case.claimed_deductions:
            raise ValueError('Domestic and foreign expenses must reconcile to saved annual deductions')
        rows = []
        for row, country_limit in zip(p.countries, limits['countries']):
            b = row.basis
            items = by_country[b.country]
            gross = sum((i.gross_amount for i in items), Decimal(0))
            paid = sum((i.foreign_tax_paid for i in items), Decimal(0))
            if b.business_revenue + b.company_receipts != gross:
                raise ValueError('Country revenue must reconcile to saved gross income before foreign tax')
            if b.business_foreign_tax_paid + b.company_receipt_foreign_tax_paid != paid:
                raise ValueError('Country paid tax must reconcile to saved foreign tax')
            net_method_expenses = b.business_allowable_expenses + b.company_receipt_allowable_expenses
            if (row.annual_allowable_expenses < net_method_expenses or
                    b.treatment in ('business_net', 'mixed_combined') and row.annual_allowable_expenses != net_method_expenses):
                raise ValueError('Country limit expenses must reconcile to final annual expenses for the selected method')
            credit = sum((part['credit_before_annual_reconciliation'] for part in country_limit['parts']), Decimal(0))
            deducted = row.foreign_tax_in_annual_expenses
            if deducted > row.annual_allowable_expenses or deducted + credit > paid:
                raise ValueError('Credited foreign tax cannot also be deducted as an expense')
            rows.append(dict(country=b.country, gross_income=gross, foreign_tax_paid=paid,
                annual_allowable_expenses=row.annual_allowable_expenses,
                foreign_tax_in_annual_expenses=deducted, rd300_exemption=credit,
                uncredited_and_undeducted_foreign_tax=paid-credit-deducted))
        derived_credit = limits['credit_before_annual_reconciliation']
        if allowed_tax_credits != derived_credit:
            raise ValueError('Allowed credits must equal the derived RD300 exemption; separate other credit paths')
    return dict(country_limits=limits, country_reconciliation=rows,
        derived_rd300_exemption=derived_credit, expense_eligibility='user_verified_final_bases',
        stage='saved_rd300_reconciliation_before_annual_settlement')
