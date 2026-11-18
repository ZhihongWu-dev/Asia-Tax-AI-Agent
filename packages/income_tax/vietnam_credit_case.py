"""Bind reviewed treaty-credit components to immutable saved income facts.

This is a credit workpaper, not a complete corporate assessment. It explicitly
reports foreign items not yet assessed so a caller cannot mistake a subtotal
for the case's full credit. Vietnam tax limits remain separately established.
"""
from decimal import Decimal, localcontext
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, TypeAdapter

from packages.contracts.income_tax import IncomeTaxCase, Money
from .vietnam_foreign_credit import (
    dividend_underlying_credit, indonesia_deemed_credit,
    singapore_interest_royalty_credit,
)


class CreditLine(BaseModel):
    model_config = ConfigDict(extra='forbid')
    income_index: int = Field(strict=True, ge=0, le=199)
    vietnam_tax_limit: Money
    treaty_and_same_income_basis_verified: StrictBool
    basis_explanation: str = Field(min_length=20, max_length=4000)


class IndonesiaDeemed(CreditLine):
    method: Literal['indonesia_deemed']


class SingaporeFloor(CreditLine):
    method: Literal['singapore_interest_royalty']
    eligible_singapore_tax_paid: Money


class UnderlyingDividend(CreditLine):
    method: Literal['underlying_dividend']
    qualifying_holding_percent: Money
    distributing_profit_after_tax: Money
    corporate_tax_paid_on_profit: Money
    corporate_recipient_and_pool_verified: StrictBool


TreatyCreditLine = Annotated[
    IndonesiaDeemed | SingaporeFloor | UnderlyingDividend,
    Field(discriminator='method'),
]
_LINES = TypeAdapter(Annotated[list[TreatyCreditLine], Field(min_length=1, max_length=200)])


def credit_workpaper(case, lines):
    """Reconcile method, gross income and actual paid tax before calculation.

    Underlying company tax is separate from saved foreign_tax_paid, which is
    shareholder-level tax. Ordinary HK/SG underlying-only treatment here requires
    that saved shareholder tax is zero; it never silently discards another claim.
    """
    if isinstance(case, IncomeTaxCase):
        case = case.model_dump()
    case = IncomeTaxCase.model_validate(case)
    if case.jurisdiction != 'vn' or case.subject != 'company' or case.residency != 'resident':
        raise ValueError('Credit workpaper requires a resident Vietnam company case')
    if (case.period_start.isoformat(), case.period_end.isoformat()) != ('2026-01-01', '2026-12-31'):
        raise ValueError('Credit workpaper currently requires calendar2026')
    if case.missing_for_calculation():
        raise ValueError('Saved income facts must be complete and confirmed')
    lines = _LINES.validate_python(lines)
    indexes = [line.income_index for line in lines]
    if len(set(indexes)) != len(indexes):
        raise ValueError('An income item cannot receive duplicate credit calculations')
    results = []
    for line in lines:
        if line.income_index >= len(case.incomes):
            raise ValueError('Credit income index is outside the saved case')
        item = case.incomes[line.income_index]
        if item.source_jurisdiction == 'vn':
            raise ValueError('A foreign-credit line cannot target domestic income')
        if line.treaty_and_same_income_basis_verified is not True or not line.basis_explanation.strip():
            raise ValueError('Treaty eligibility and same-income tax basis require an explanation and confirmation')
        if isinstance(line, IndonesiaDeemed):
            if item.source_jurisdiction != 'id':
                raise ValueError('Indonesia deemed credit must target Indonesian income')
            result = indonesia_deemed_credit(item.gross_amount, income_type=item.category,
                vietnam_tax_limit=line.vietnam_tax_limit,
                paragraph2_and_treaty_entitlement_verified=True)
            credit = result['allowed_tax_credit']
        elif isinstance(line, SingaporeFloor):
            if item.source_jurisdiction != 'sg':
                raise ValueError('Singapore credit must target Singapore income')
            if line.eligible_singapore_tax_paid > item.foreign_tax_paid:
                raise ValueError('Eligible paid tax exceeds the saved actual foreign tax')
            result = singapore_interest_royalty_credit(item.gross_amount, income_type=item.category,
                eligible_singapore_tax_paid=line.eligible_singapore_tax_paid,
                vietnam_tax_limit=line.vietnam_tax_limit,
                article11_or12_and_treaty_entitlement_verified=True)
            credit = result['allowed_tax_credit']
        else:
            if item.category != 'dividend' or item.foreign_tax_paid != 0:
                raise ValueError('Underlying-only route requires a dividend with zero shareholder-level foreign tax')
            result = dividend_underlying_credit(source_country=item.source_jurisdiction,
                qualifying_holding_percent=line.qualifying_holding_percent,
                dividend_before_withholding=item.gross_amount,
                distributing_profit_after_tax=line.distributing_profit_after_tax,
                corporate_tax_paid_on_profit=line.corporate_tax_paid_on_profit,
                vietnam_tax_limit=line.vietnam_tax_limit,
                corporate_recipient_and_pool_verified=line.corporate_recipient_and_pool_verified,
                treaty_and_vietnam_basis_verified=True)
            credit = result['allowed_underlying_credit']
        results.append(dict(income_index=line.income_index,
            saved_income=item.model_dump(mode='json'), basis=line.model_dump(mode='json'),
            credit=credit, calculation=result))
    remaining = [index for index, item in enumerate(case.incomes)
                 if item.source_jurisdiction != 'vn' and index not in indexes]
    with localcontext() as context:
        context.prec = 40
        subtotal = sum((row['credit'] for row in results), Decimal(0))
    return dict(policy_version='vn-credit-workpaper-2026-11-18', currency='VND',
        items=results, assessed_credit_subtotal=subtotal,
        unassessed_foreign_income_indexes=remaining,
        all_foreign_items_assessed=not remaining,
        stage='credit_workpaper_not_complete_income_tax_assessment')
