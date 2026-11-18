"""Osaka ordinary enterprise component; not a complete local assessment."""
from copy import deepcopy
from decimal import Decimal, localcontext
import json
from pathlib import Path

from .japan import yen
from .japan_local import ordinary_enterprise_levies

SOURCES = json.loads(Path(__file__).with_name('jp_osaka_enterprise_sources.json').read_text(encoding='utf-8'))['sources']


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
