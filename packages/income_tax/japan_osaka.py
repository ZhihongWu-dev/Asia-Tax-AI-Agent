"""Osaka ordinary enterprise component; not a complete local assessment."""
from copy import deepcopy
from decimal import Decimal, localcontext
import json
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr

from .japan import yen
from .japan_local import ordinary_enterprise_levies

SOURCES = json.loads(Path(__file__).with_name('jp_osaka_enterprise_sources.json').read_text(encoding='utf-8'))['sources']
CITY_SOURCES = json.loads(Path(__file__).with_name('jp_osaka_city_sources.json').read_text(encoding='utf-8'))['sources']


class OsakaWard(BaseModel):
    model_config = ConfigDict(extra='forbid')
    ward_name: StrictStr = Field(min_length=1, max_length=80, pattern=r'^\S(?:.*\S)?$')
    employees: StrictInt = Field(ge=0)


def annual_capitation(*, fiscal_start_year, registered_capital, capital_reserve,
                      adjusted_statutory_capital, wards, full_year_osaka_city_scope_verified):
    """Full-year ordinary capital corporation with offices in Osaka city only.

    Registered capital is not the statutory capital-band amount. Confirm the
    actual Osaka wards and aggregate offices per ward; no partial-year/dormitory
    exemptions, other municipalities or entity exemptions are inferred.
    """
    if type(fiscal_start_year) is not int or fiscal_start_year != 2026:
        raise ValueError('Only fiscal years starting in2026 reviewed')
    if full_year_osaka_city_scope_verified is not True:
        raise ValueError('Full-year ordinary capital corporation and Osaka city ward scope must be verified')
    rows = [OsakaWard.model_validate(w) for w in wards]
    if not 1 <= len(rows) <= 24 or len({w.ward_name for w in rows}) != len(rows):
        raise ValueError('Aggregate each Osaka city ward exactly once,1 through24 wards')
    registered, reserve, adjusted = map(yen, (registered_capital, capital_reserve, adjusted_statutory_capital))
    with localcontext() as ctx:
        ctx.prec = 40
        capital = max(adjusted, registered + reserve)
        bands = [(10000000,20000,50000,120000),(100000000,75000,130000,150000),
                 (1000000000,260000,160000,400000),(5000000000,1080000,410000,1750000),
                 (None,1600000,410000,3000000)]
        for ceiling, prefecture, small, large in bands:
            if ceiling is None or capital <= ceiling:
                break
        ward_results = [dict(ward_name=w.ward_name, employees=w.employees,
                            annual_city_capitation=Decimal(small if w.employees<=50 else large)) for w in rows]
        city = sum((w['annual_city_capitation'] for w in ward_results), Decimal(0))
        sources = CITY_SOURCES + [s for s in SOURCES if s['doc_id']=='jp.osaka-prefecture-surcharges']
        return dict(policy_version='jp-osaka-annual-capitation-20261119',
            stage='internal_full_year_capitation_before_interim_payments',
            capital_for_rate_band=capital, prefectural_capitation=Decimal(prefecture),
            wards=ward_results, city_capitation=city, total_capitation=Decimal(prefecture)+city,
            sources=deepcopy(sources))


def ordinary_enterprise(income, *, fiscal_start_year, months, registered_capital,
                        ordinary_single_prefecture_scope_verified):
    """Income-based domestic ordinary entity, all offices in Osaka prefecture.

    Caller establishes exclusion from expanded size-based taxation and special
    industries. A2026 start and at most12 months falls within the verified2029
    surcharge sunset. Income is the reconciled enterprise base, not national
    final taxable income automatically. Credits/interim payments are separate.
    """
    if ordinary_single_prefecture_scope_verified is not True:
        raise ValueError('Ordinary domestic, Osaka-only and size-based exclusion scope must be verified')
    if type(fiscal_start_year) is not int or fiscal_start_year != 2026:
        raise ValueError('Only fiscal years starting in2026 reviewed')
    if type(months) is not int or not 1 <= months <= 12:
        raise ValueError('Established period months must be1 through12')
    capital, income = yen(registered_capital), yen(income)
    if capital > 100000000:
        raise ValueError('Capital aboveJPY100m requires a separate size-based workflow')
    with localcontext() as ctx:
        ctx.prec = 40
        threshold = Decimal(50000000) * months / 12
        comparison_income = (income // 1000) * 1000
        surcharge = comparison_income > threshold
        # Osaka's current tables and R8.7 p7 confirm identical band arithmetic,
        # rates and37% standard-rate special levy. Only the surcharge gate differs.
        result = ordinary_enterprise_levies(income, fiscal_start_year=fiscal_start_year,
            months=months, reduced_bands_eligible=True,
            tokyo_surcharge_applies=surcharge, ordinary_income_based_scope_verified=True)
        result.update(policy_version='jp-osaka-ordinary-enterprise-component-20261119',
            registered_capital=capital, surcharge_applies=surcharge,
            surcharge_income_threshold=threshold, surcharge_comparison_income=comparison_income,
            scope='ordinary_domestic_osaka_only_income_based_company',
            sources=deepcopy(SOURCES))
        return result
