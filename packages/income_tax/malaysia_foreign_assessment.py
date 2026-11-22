"""Saved Malaysian ordinary resident-company direct-credit workpaper."""
from decimal import Decimal, localcontext
from typing import Literal

from pydantic import Field, StrictBool, StrictInt

from packages.contracts.income_tax import Money
from .malaysia import company_tax
from .malaysia_foreign_credit import Strict, calculate
from .arithmetic import amount


class SavedReceipt(Strict):
    income_index: StrictInt = Field(ge=0)
    exempt_income: Money
    taxing_country: str | None = Field(default=None, pattern=r'^[a-z]{2}$')
    method: Literal['none', 'bilateral', 'unilateral']
    eligible_foreign_tax: Money
    taxable_status_and_credit_eligibility_verified: StrictBool


class SavedSource(Strict):
    source_id: str = Field(min_length=1, max_length=120)
    receipts: list[SavedReceipt] = Field(min_length=1, max_length=200)
    additions: Money
    expenses: Money
    statutory_charges: Money
    statutory_allowances: Money
    same_source_allocation_verified: StrictBool


class SavedWorkpaper(Strict):
    groups: list[SavedSource] = Field(min_length=1, max_length=200)
    total_income_deductions: Money
    scheme: Literal['ordinary', 'sme']
    sme_eligibility_verified: StrictBool
    ordinary_resident_company_no_losses_verified: StrictBool
    deductions_and_source_allocation_verified: StrictBool
    treaty_tax_period_fx_and_no_duplicate_claim_verified: StrictBool


def assess(case, workpaper, prepaid_tax):
    p = SavedWorkpaper.model_validate(workpaper)
    if (case.jurisdiction != 'my' or case.subject != 'company' or case.residency != 'resident'
            or case.missing_for_calculation()):
        raise ValueError('Confirmed Malaysian resident company facts required')
    if (case.period_start.isoformat(), case.period_end.isoformat()) != ('2026-01-01', '2026-12-31'):
        raise ValueError('Calendar2026 basis period required')
    if not p.ordinary_resident_company_no_losses_verified or case.carried_losses:
        raise ValueError('Ordinary standalone resident company without carried losses required')
    indexes = [r.income_index for g in p.groups for r in g.receipts]
    ids = [g.source_id for g in p.groups]
    if sorted(indexes) != list(range(len(case.incomes))) or len(ids) != len(set(ids)):
        raise ValueError('Unique source groups must cover each saved income exactly once')
    with localcontext() as ctx:
        ctx.prec = 40
        deductions = sum((g.expenses + g.statutory_allowances for g in p.groups), Decimal(0))
        if deductions + p.total_income_deductions != case.claimed_deductions:
            raise ValueError('Workpaper deductions must reconcile to saved deductions')
        sources = []
        reconciliation = []
        for group in p.groups:
            items = [case.incomes[r.income_index] for r in group.receipts]
            categories = {i.category for i in items}
            if (len(categories) != 1 or not categories <= {'business', 'interest', 'rental', 'royalty', 'dividend'}
                    or not group.same_source_allocation_verified):
                raise ValueError('Each verified ordinary source must have one eligible income category')
            if 'business' not in categories and (group.statutory_charges or group.statutory_allowances):
                raise ValueError('Nonbusiness source cannot use business statutory charges or allowances')
            if 'business' not in categories and len({i.source_jurisdiction for i in items}) != 1:
                raise ValueError('Separate nonbusiness country sources before allocating expenses')
            receipts = []
            gross = excluded = paid = Decimal(0)
            for r, item in zip(group.receipts, items):
                if not r.taxable_status_and_credit_eligibility_verified:
                    raise ValueError('Receipt taxable status and credit eligibility require verification')
                if r.exempt_income > item.gross_amount:
                    raise ValueError('Exempt income exceeds saved gross income')
                if r.exempt_income and r.eligible_foreign_tax:
                    raise ValueError('Separate exempt and taxable receipts before claiming credit')
                if item.category == 'dividend' and item.source_jurisdiction == 'my' and r.exempt_income != item.gross_amount:
                    raise ValueError('Domestic dividends require separately established exemption treatment')
                if item.foreign_tax_paid is None and (item.source_jurisdiction != 'my' or r.method != 'none'):
                    raise ValueError('Record paid foreign tax, including explicit zero')
                tax = item.foreign_tax_paid or Decimal(0)
                if r.eligible_foreign_tax > tax:
                    raise ValueError('Eligible foreign tax exceeds saved paid tax')
                gross += item.gross_amount
                excluded += r.exempt_income
                paid += tax
                receipts.append(dict(receipt_id=str(r.income_index), gross_income=item.gross_amount-r.exempt_income,
                    taxing_country=r.taxing_country, method=r.method, eligible_foreign_tax=r.eligible_foreign_tax,
                    malaysia_derived=item.source_jurisdiction == 'my'))
            adjusted = gross-excluded+group.additions-group.expenses
            statutory = adjusted+group.statutory_charges-group.statutory_allowances
            if adjusted < 0 or statutory < 0:
                raise ValueError('Source losses and unabsorbed allowances require separate treatment')
            sources.append(dict(source_id=group.source_id, statutory_income=statutory, receipts=receipts))
            reconciliation.append(dict(source_id=group.source_id, income_indexes=[r.income_index for r in group.receipts],
                gross_income=gross, exempt_income=excluded, additions=group.additions, expenses=group.expenses,
                statutory_charges=group.statutory_charges, statutory_allowances=group.statutory_allowances,
                statutory_income=statutory, foreign_tax_paid=paid))
        total = sum((s['statutory_income'] for s in sources), Decimal(0))-p.total_income_deductions
        if total < 0:
            raise ValueError('Total-income deductions exceed statutory income')
        domestic = company_tax(total, assessment_year=2026, scheme=p.scheme,
            sme_eligibility_confirmed=p.sme_eligibility_verified, ordinary_treatment_confirmed=True,
            allowed_rebates='0', allowed_tax_credits='0', prepaid_tax='0')
        result = calculate(dict(total_income=total, sources=sources, resident_and_taxable_income_verified=True,
            source_grouping_and_total_income_verified=p.deductions_and_source_allocation_verified,
            treaty_tax_period_fx_and_no_duplicate_claim_verified=p.treaty_tax_period_fx_and_no_duplicate_claim_verified),
            malaysian_tax_before_credit=domestic['gross_tax'])
        prepaid = amount(prepaid_tax)
        result.update(assessment_year=2026, scheme=p.scheme, bands=domestic['bands'],
            chargeable_income=total, total_income_deductions=p.total_income_deductions,
            gross_tax=domestic['gross_tax'], final_tax=result['tax_after_credit'],
            annual_liability=result['tax_after_credit'], prepaid_tax=prepaid,
            balance_due=result['tax_after_credit']-prepaid, source_reconciliation=reconciliation,
            stage='ordinary_resident_company_direct_credit_before_filing_rounding')
        # The same Act supports rates, basis and credits. Preserve all locators
        # in one reference rather than duplicating the identical file/hash.
        result['sources'][0]['locator'] += '; sections 42-44; ' + domestic['sources'][0]['locator']
        return result
