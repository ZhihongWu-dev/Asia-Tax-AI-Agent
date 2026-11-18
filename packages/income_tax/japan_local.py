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


# Tokyo return instructions pp4-5, ordinary corporations with statutory capital.
# Each row: capital ceiling, prefectural annual amount, ward <=50, ward >50.
_PER_CAPITA = (
    (Decimal('10000000'), 20000, 50000, 120000),
    (Decimal('100000000'), 50000, 130000, 150000),
    (Decimal('1000000000'), 130000, 160000, 400000),
    (Decimal('5000000000'), 540000, 410000, 1750000),
    (None, 800000, 410000, 3000000),
)


def ordinary_per_capita_component(capital_for_rate_band, *, fiscal_start_year,
        employees_in_ward, office_months, component, ordinary_capital_scope_verified):
    """One verified Tokyo annual-return per-capita filing component.

    component: wards_only_principal combines prefectural and principal ward;
    ward_only covers supplementary wards or wards in mixed ward/city cases;
    prefectural_only covers the once-only prefectural line in mixed/city cases.
    Municipality levies outside the 23 wards are separate, not inferred here.
    Capital means the established statutory band amount after adjustments and
    the capital-plus-reserve floor, not simply registered capital. Office-month
    counts discard partial months, except an entire period below one month is
    one; this differs from enterprise band-proration months. Caller establishes
    these facts and aggregates offices without duplicate prefectural charges.
    """
    if type(fiscal_start_year) is not int or fiscal_start_year != 2026:
        raise ValueError('Only fiscal years starting in 2026 have been reviewed')
    if ordinary_capital_scope_verified is not True:
        raise ValueError('Ordinary corporation, statutory capital and office scope must be verified')
    if type(employees_in_ward) is not int or employees_in_ward < 0:
        raise ValueError('Verified ward employees must be a nonnegative integer')
    if type(office_months) is not int or not 1 <= office_months <= 12:
        raise ValueError('Verified per-capita office months must be from 1 to 12')
    if component not in ('wards_only_principal', 'ward_only', 'prefectural_only'):
        raise ValueError('Unknown Tokyo per-capita component; municipalities require their own levy')
    capital = yen(capital_for_rate_band)
    for ceiling, prefectural, ward_small, ward_large in _PER_CAPITA:
        if ceiling is None or capital <= ceiling:
            ward = ward_small if employees_in_ward <= 50 else ward_large
            break
    annual = Decimal(prefectural if component == 'prefectural_only' else
                     ward if component == 'ward_only' else prefectural + ward)
    with localcontext() as ctx:
        ctx.prec = 40
        # Floor only after prorating the actual filing component; splitting a
        # combined principal-ward component first would lose JPY100 in some months.
        tax = _floor(annual * office_months / 12, Decimal(100))
    return dict(policy_version='jp-tokyo-per-capita-component-20261119',
        fiscal_start_year=fiscal_start_year, currency='JPY', component=component,
        capital_for_rate_band=capital, employees_in_ward=employees_in_ward,
        office_months=office_months, annual_component_amount=annual,
        per_capita_tax_before_prepayments=tax,
        stage='internal_component_not_complete_assessment', sources=deepcopy(SOURCES))



def ordinary_inhabitant_levy(national_levy_base, *, fiscal_start_year, months,
        registered_capital, ward_allocated_base, municipality_allocated_base,
        ordinary_domestic_scope_verified, allowed_credits=0, tax_credit_additions=0,
        prepaid_levy=0):
    """Tokyo corporate-tax-based inhabitant levy from verified filing bases.

    The nationwide base is the legally adjusted corporation-tax levy base,
    not national final tax after credits. Determine the rate before geographic
    allocation. Municipality allocated base here receives only Tokyo's
    prefectural levy; each municipality's own levy remains separate.
    Verified additions/credits correspond to the net-levy line, not raw foreign
    tax paid. Treaty-amendment relief and group/foreign-PE forms are separate.
    """
    if type(fiscal_start_year) is not int or fiscal_start_year != 2026:
        raise ValueError('Only fiscal years starting in 2026 have been reviewed')
    if type(months) is not int or not 1 <= months <= 12:
        raise ValueError('Verified rate-threshold months must be from 1 to 12')
    if ordinary_domestic_scope_verified is not True:
        raise ValueError('Ordinary domestic levy bases, allocation and credit entitlement must be verified')
    national, capital, ward, municipal, credits, additions, prepaid = map(yen,
        (national_levy_base,registered_capital,ward_allocated_base,
         municipality_allocated_base,allowed_credits,tax_credit_additions,prepaid_levy))
    with localcontext() as ctx:
        ctx.prec = 40
        if ward + municipal > national:
            raise ValueError('Tokyo allocations exceed the nationwide corporation-tax levy base')
        national_rounded = _floor(national, Decimal(1000))
        surcharge = capital > 100000000 or national_rounded * 12 > Decimal(10000000) * months
        ward_rate, municipal_rate = ((Decimal('0.104'),Decimal('0.02')) if surcharge
                                    else (Decimal('0.07'),Decimal('0.01')))
        ward_base = _floor(ward,Decimal(1000))
        municipal_base = _floor(municipal,Decimal(1000))
        ward_tax = ward_base * ward_rate
        municipal_tax = municipal_base * municipal_rate
        gross = ward_tax + municipal_tax
        before_rounding = gross + additions - credits
        if before_rounding < ZERO:
            raise ValueError('Verified usable levy credits exceed tax plus additions')
        final = _floor(before_rounding,Decimal(100))
        return dict(policy_version='jp-tokyo-inhabitant-levy-component-20261119',
            fiscal_start_year=fiscal_start_year, months=months,currency='JPY',
            national_levy_base=national,national_rate_test_base=national_rounded,
            registered_capital=capital,surcharge_applies=surcharge,
            ward_allocated_base_before_rounding=ward,ward_taxable_base=ward_base,
            ward_rate=ward_rate,ward_levy_before_credits=ward_tax,
            municipality_allocated_base_before_rounding=municipal,
            municipality_prefectural_taxable_base=municipal_base,
            municipality_prefectural_rate=municipal_rate,
            municipality_prefectural_levy_before_credits=municipal_tax,
            levy_before_credits=gross,allowed_credits=credits,tax_credit_additions=additions,
            net_levy_before_rounding=before_rounding,final_levy=final,
            prepaid_levy=prepaid,balance_due=final-prepaid,
            stage='internal_tokyo_levy_component_excluding_per_capita_and_other_municipal_tax',
            sources=deepcopy(SOURCES))
