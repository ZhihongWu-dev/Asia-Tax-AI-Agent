"""Ordinary20% personal property transfers, calculated separately per transaction."""
from copy import deepcopy
from decimal import Decimal,localcontext
from pydantic import Field,StrictBool,StrictInt
from packages.contracts.income_tax import Money
from .china_personal_foreign_credit import Strict,SOURCES
from .china import SOURCE_BY_ID

class Transfer(Strict):
    income_index: StrictInt = Field(ge=0,le=199)
    original_cost: Money
    reasonable_transfer_expenses: Money
    allowed_donation: Money
    allowed_tax_reduction: Money
    single_transaction_source_and_ordinary_rate_verified: StrictBool
    original_cost_expenses_and_reliefs_verified: StrictBool


def calculate(case,transfers):
    papers=[Transfer.model_validate(v) for v in transfers]
    expected={n for n,i in enumerate(case.incomes) if i.category=='capital_gain'}
    indices=[r.income_index for r in papers]
    if len(set(indices))!=len(indices) or set(indices)!=expected or not expected:
        raise ValueError('Each saved transfer requires exactly one transaction workpaper')
    if case.subject!='individual' or case.jurisdiction!='cn' or case.residency!='resident':
        raise ValueError('Chinese resident individual required')
    if str(case.period_start)!='2026-01-01' or str(case.period_end)!='2026-12-31':
        raise ValueError('Calendar2026 required')
    rows=[]
    with localcontext() as ctx:
        ctx.prec=40
        for p in papers:
            if not p.single_transaction_source_and_ordinary_rate_verified or not p.original_cost_expenses_and_reliefs_verified:
                raise ValueError('Single transfer, source classification, ordinary20percent treatment and established costs/reliefs required')
            item=case.incomes[p.income_index]
            gain=item.gross_amount-p.original_cost-p.reasonable_transfer_expenses
            before=max(Decimal(0),gain)
            if p.allowed_donation>before:raise ValueError('Allowed donation exceeds positive transaction income')
            taxable=before-p.allowed_donation
            gross=taxable*Decimal('.2')
            if p.allowed_tax_reduction>gross:raise ValueError('Allowed tax reduction exceeds transaction tax')
            rows.append(dict(income_index=p.income_index,country=item.source_jurisdiction,
                gross_proceeds=item.gross_amount,original_cost=p.original_cost,
                reasonable_transfer_expenses=p.reasonable_transfer_expenses,
                gain_before_donation=gain,unoffset_loss=max(Decimal(0),-gain),
                allowed_donation=p.allowed_donation,taxable_income=taxable,
                gross_tax=gross,allowed_tax_reduction=p.allowed_tax_reduction,
                tax_after_reduction=gross-p.allowed_tax_reduction))
        return dict(transactions=rows,tax_after_reduction=sum((r['tax_after_reduction'] for r in rows),Decimal(0)),
            stage='internal_separate_transfer_component_before_foreign_credit',
            scope_note='Each saved capital_gain row is one ordinary20percent transfer and gross_amount is gross proceeds, not gain. Source classification including indirect China real-estate interests, cost evidence, donations and exemptions must be established. No inter-transaction loss offset, deemed costs or special securities treatment inferred.',
            sources=deepcopy([SOURCE_BY_ID['cn.law.iit']]+[s for s in SOURCES if s['doc_id'] in ('cn.reg.iit','cn.cs.2020-03')]))
