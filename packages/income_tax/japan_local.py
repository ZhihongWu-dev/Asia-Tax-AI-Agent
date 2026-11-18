"""Internal Tokyo ordinary corporate enterprise-tax arithmetic.

Not an enabled assessment policy. Eligibility, office allocation, period-month
counting, local taxable-income reconciliation and other local levies are still
required before this helper can support a complete user-facing assessment.
Only ordinary income-based corporations outside size-based/special regimes.
"""
from copy import deepcopy
from decimal import Decimal, localcontext
import json
from pathlib import Path

from .arithmetic import ZERO
from .japan import yen

SOURCES = json.loads(Path(__file__).with_name('jp_local_enterprise_sources.json').read_text(encoding='utf-8'))['sources']
STANDARD = tuple(map(Decimal, ('0.035', '0.053', '0.07')))
TOKYO_SURCHARGE = tuple(map(Decimal, ('0.0375', '0.05665', '0.0748')))


def _floor(value, unit):
    return (value // unit) * unit


def ordinary_enterprise_levies(income, *, fiscal_start_year, months,
        reduced_bands_eligible, tokyo_surcharge_applies,
        ordinary_income_based_scope_verified):
    """Compute verified local income components before credits/prepayments.

    months is the legally established band-proration count, not a day fraction
    or the separate per-capita-levy month count. One jurisdiction allocation is
    assumed: do not feed nationwide income of a multi-prefecture corporation.
    """
    if type(fiscal_start_year) is not int or fiscal_start_year != 2026:
        raise ValueError('Only fiscal years starting in 2026 have been reviewed')
    if type(months) is not int or not 1 <= months <= 12:
        raise ValueError('Verified band-proration months must be an integer from 1 to 12')
    if type(reduced_bands_eligible) is not bool or type(tokyo_surcharge_applies) is not bool:
        raise ValueError('Band eligibility and Tokyo surcharge require explicit booleans')
    if ordinary_income_based_scope_verified is not True:
        raise ValueError('Ordinary income-based scope must be verified; size-based/special regimes require separate treatment')
    income = yen(income)
    with localcontext() as ctx:
        ctx.prec = 40
        bounds = ((Decimal(4000000) * months // 12,
                   Decimal(8000000) * months // 12, None)
                  if reduced_bands_eligible else (None,))
        rates = TOKYO_SURCHARGE if tokyo_surcharge_applies else STANDARD
        if not reduced_bands_eligible:
            rates = (rates[-1],)
        standard_rates = STANDARD if reduced_bands_eligible else (STANDARD[-1],)
        lower = ZERO
        rows = []
        for upper, rate, standard_rate in zip(bounds, rates, standard_rates):
            allocated = max(ZERO, (income if upper is None else min(income, upper)) - lower)
            base = _floor(allocated, Decimal(1000))
            rows.append(dict(lower=lower, upper=upper, allocated_before_rounding=allocated,
                taxable_base=base, rate=rate, tax=_floor(base * rate, Decimal(100)),
                standard_rate=standard_rate,
                standard_rate_tax=_floor(base * standard_rate, Decimal(100))))
            if upper is not None:
                lower = upper
        enterprise = sum((row['tax'] for row in rows), ZERO)
        standard = sum((row['standard_rate_tax'] for row in rows), ZERO)
        special = _floor(standard * Decimal('0.37'), Decimal(100))
        return dict(policy_version='jp-tokyo-ordinary-enterprise-component-20261119',
            fiscal_start_year=fiscal_start_year, months=months, currency='JPY',
            established_enterprise_income=income, bands=rows,
            enterprise_tax_before_credits=enterprise,
            standard_rate_enterprise_tax=standard,
            special_enterprise_tax_before_credits=special,
            stage='internal_component_before_credits_and_prepayments_not_complete_assessment',
            sources=deepcopy(SOURCES))
