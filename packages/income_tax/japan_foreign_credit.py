"""Current national credit allocation under NTA2026 Schedule6(2).

This component consumes verified statutory reference amounts. It is not an
annual return: historical credits, municipal/prefectural credits, source-tax
eligibility, tax-reference derivation and filing rounding remain separate.
"""
from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
from .japan import yen

SOURCES = [
    dict(doc_id='jp.nta.form6-2.2026',
        file='database/raw/jp/jp.nta.form6-2.2026.pdf',
        url='https://www.nta.go.jp/taxes/tetsuzuki/shinsei/annai/hojin/shinkoku/itiran2026/pdf/06%2802%29.pdf',
        sha256='c04a265cba05cce104a20c9929805c292f70ed463f6c562d8f23d7851c5d473c',
        provisions=['Lines9-18,47-54,57-64; periods ending on/after2026-04-01']),
    dict(doc_id='jp.nta.form6-2.instructions.2026',
        file='database/raw/jp/jp.nta.form6-2.instructions.2026.pdf',
        url='https://www.nta.go.jp/taxes/tetsuzuki/shinsei/annai/hojin/shinkoku/itiran2026/pdf/06%2802%29-ki.pdf',
        sha256='2435e34d3b65d66c26c9e5b5ba9d3ac4194f023c5c674116ef65d7b3c1837996',
        provisions=['Parts1-3; separate corporation/local-corporation/defence computations']),
]


def current_national_credits(*, statutory_worldwide_income, foreign_income_before_exempt,
        foreign_income_exempt_from_foreign_tax, eligible_foreign_corporate_tax,
        corporation_tax_reference, local_corporation_tax_reference,
        defence_tax_reference, defence_applicable,
        statutory_reference_amounts_and_current_tax_eligibility_verified,
        no_history_group_or_special_credit_adjustments_verified):
    """Exact pre-filing arithmetic; reference taxes are Schedule6(2)2/51/61.

    Worldwide denominator is line9, NOT taxable income after loss relief or
    its JPY1000-truncated base. Foreign income is line12 before line13 exclusion.
    """
    if (statutory_reference_amounts_and_current_tax_eligibility_verified is not True
            or no_history_group_or_special_credit_adjustments_verified is not True):
        raise ValueError('Verify statutory reference amounts, eligibility and excluded adjustments')
    if type(defence_applicable) is not bool:
        raise ValueError('Explicit defence applicability required')
    world,foreign,exempt,paid,corp,local,defence=map(lambda v:Fraction(yen(v)),[
        statutory_worldwide_income,foreign_income_before_exempt,
        foreign_income_exempt_from_foreign_tax,eligible_foreign_corporate_tax,
        corporation_tax_reference,local_corporation_tax_reference,defence_tax_reference])
    if world<=0:
        raise ValueError('Positive statutory denominator required; loss cases require separate treatment')
    if exempt>foreign:
        raise ValueError('Exempt foreign income cannot exceed supplied foreign income')
    if not defence_applicable and defence:
        raise ValueError('Defence reference requires applicable period')
    adjusted=min(foreign-exempt,world*Fraction(9,10))
    ratio=adjusted/world
    corp_limit,local_limit,defence_limit=[tax*ratio for tax in (corp,local,defence)]
    corp_credit=min(paid,corp_limit)
    local_credit=min(max(Fraction(0),paid-corp_limit),local_limit)
    defence_credit=min(max(Fraction(0),paid-corp_limit-local_limit),defence_limit)
    used=corp_credit+local_credit+defence_credit
    exact=dict(adjusted_foreign_income=adjusted,foreign_income_ratio=ratio,
        corporation_credit_limit=corp_limit,local_corporation_credit_limit=local_limit,
        defence_credit_limit=defence_limit,corporation_credit=corp_credit,
        local_corporation_credit=local_credit,defence_credit=defence_credit,
        total_current_national_credit=used,remaining_for_local_and_history_review=paid-used)
    with localcontext() as ctx:
        ctx.prec=40
        values={key:Decimal(v.numerator)/Decimal(v.denominator) for key,v in exact.items()}
    return dict(policy_version='jp-current-national-foreign-component-20261122',currency='JPY',
        **values,exact_fractions={key:dict(numerator=str(v.numerator),denominator=str(v.denominator))
            for key,v in exact.items()},sources=deepcopy(SOURCES),
        stage='current_national_credit_allocation_before_return_rounding_not_annual_settlement')
