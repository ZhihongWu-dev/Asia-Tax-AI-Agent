"""Malaysian Schedule 7 direct credits on established taxable source groups.

PR3/2026 sections 5(l), 6(b), example 5. Shared-source statutory income is
allocated by gross receipts. Separate passive sources must be separate groups.
This component does not decide exemptions, treaty entitlement or filing approval.
"""
from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from packages.contracts.income_tax import Money
from .arithmetic import computed_amount
from .malaysia import SOURCES


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Receipt(Strict):
    receipt_id: str = Field(min_length=1, max_length=120)
    gross_income: Money
    taxing_country: str | None = Field(default=None, pattern=r'^[a-z]{2}$')
    method: Literal['none', 'bilateral', 'unilateral']
    eligible_foreign_tax: Money
    malaysia_derived: StrictBool


class Source(Strict):
    source_id: str = Field(min_length=1, max_length=120)
    statutory_income: Money
    receipts: list[Receipt] = Field(min_length=1, max_length=200)


class Workpaper(Strict):
    total_income: Money
    sources: list[Source] = Field(min_length=1, max_length=200)
    resident_and_taxable_income_verified: StrictBool
    source_grouping_and_total_income_verified: StrictBool
    treaty_tax_period_fx_and_no_duplicate_claim_verified: StrictBool


def calculate(workpaper, *, malaysian_tax_before_credit):
    """Return source limits and aggregate credit before filing rounding.

    Overall tax cap is applied after source limits; when binding, source amounts
    remain explicitly provisional, not invented allocations of the overall cap.
    """
    p = Workpaper.model_validate(workpaper)
    if not all((p.resident_and_taxable_income_verified,
                p.source_grouping_and_total_income_verified,
                p.treaty_tax_period_fx_and_no_duplicate_claim_verified)):
        raise ValueError('Residence, taxable income, grouping and foreign-credit entitlement require verification')
    gross = Fraction(computed_amount(malaysian_tax_before_credit))
    total = Fraction(p.total_income)
    if total == 0 and gross:
        raise ValueError('Zero total income cannot support positive Malaysian tax')
    ids = [s.source_id for s in p.sources]
    receipt_ids = [r.receipt_id for s in p.sources for r in s.receipts]
    if len(set(ids)) != len(ids) or len(set(receipt_ids)) != len(receipt_ids):
        raise ValueError('Source and receipt IDs must be unique')
    if total > sum((Fraction(s.statutory_income) for s in p.sources), Fraction(0)):
        raise ValueError('Total income exceeds reconciled statutory sources')
    rows = []
    for source in p.sources:
        source_gross = sum((Fraction(r.gross_income) for r in source.receipts), Fraction(0))
        statutory = Fraction(source.statutory_income)
        if not source_gross and statutory:
            raise ValueError('Positive statutory source requires a gross allocation denominator')
        grouped = {}
        for receipt in source.receipts:
            if receipt.method == 'none':
                if receipt.eligible_foreign_tax or receipt.taxing_country is not None:
                    raise ValueError('Nonclaim receipt cannot contain eligible foreign tax or taxing country')
                continue
            if receipt.taxing_country in (None, 'my'):
                raise ValueError('Credit requires a foreign taxing country')
            if receipt.method == 'unilateral' and receipt.malaysia_derived:
                raise ValueError('Malaysia-derived income cannot claim unilateral credit')
            if not receipt.gross_income and receipt.eligible_foreign_tax:
                raise ValueError('Foreign tax requires corresponding gross income')
            key = receipt.taxing_country
            row = grouped.setdefault(key, dict(method=receipt.method, gross=Fraction(0), tax=Fraction(0)))
            if row['method'] != receipt.method:
                raise ValueError('One source-country cannot mix bilateral and unilateral treatment')
            row['gross'] += Fraction(receipt.gross_income)
            row['tax'] += Fraction(receipt.eligible_foreign_tax)
        for country, data in sorted(grouped.items()):
            allocated = statutory * data['gross'] / source_gross if source_gross else Fraction(0)
            cap = gross * allocated / total if total else Fraction(0)
            tax_cap = data['tax'] / (2 if data['method'] == 'unilateral' else 1)
            available = min(cap, tax_cap)
            rows.append(dict(source_id=source.source_id, taxing_country=country,
                method=data['method'], allocated_statutory_income=allocated,
                eligible_foreign_tax=data['tax'], foreign_tax_limit=tax_cap,
                malaysian_tax_limit=cap, credit_before_overall_cap=available))
    provisional = sum((r['credit_before_overall_cap'] for r in rows), Fraction(0))
    used = min(gross, provisional)
    paid = sum((r['eligible_foreign_tax'] for r in rows), Fraction(0))

    def convert(value):
        if isinstance(value, Fraction):
            with localcontext() as ctx:
                ctx.prec = 40
                return Decimal(value.numerator) / Decimal(value.denominator)
        if isinstance(value, list):
            return [convert(v) for v in value]
        if isinstance(value, dict):
            return {k: convert(v) for k, v in value.items()}
        return value

    sources = deepcopy(SOURCES)
    for source in sources:
        source['locator'] = 'Schedule 7 paragraphs 1-7, 9, 13-16; sections 132 and 133'
    return convert(dict(policy_version='my-schedule7-direct-credit-20261122', sources=sources,
        currency='MYR', total_income=total, malaysian_tax_before_credit=gross,
        source_credits=rows, credit_before_overall_cap=provisional,
        overall_cap_reduction=provisional-used, allowed_foreign_tax_credit=used,
        unrelieved_foreign_tax=paid-used, tax_after_credit=gross-used,
        stage='verified_source_credit_component_before_filing_rounding'))
