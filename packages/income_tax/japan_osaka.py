"""Osaka ordinary enterprise component; not a complete local assessment."""
from copy import deepcopy
from decimal import Decimal, localcontext
import json
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr

from packages.contracts.income_tax import Money
from .japan import yen
from .japan_local import ordinary_enterprise_levies

SOURCES = json.loads(Path(__file__).with_name('jp_osaka_enterprise_sources.json').read_text(encoding='utf-8'))['sources']
CITY_SOURCES = json.loads(Path(__file__).with_name('jp_osaka_city_sources.json').read_text(encoding='utf-8'))['sources']


class OsakaWard(BaseModel):
    model_config = ConfigDict(extra='forbid')
    ward_name: StrictStr = Field(min_length=1, max_length=80, pattern=r'^\S(?:.*\S)?$')
    employees: StrictInt = Field(ge=0)


def annual_inhabitant(national_levy_base, *, registered_capital, fiscal_start_year,
                      ordinary_osaka_city_only_no_credits_verified):
    """Separate full-year prefectural/city corporation-tax-based levies.

    Base is the established national levy base before relevant credits, not
    national final tax. Scope excludes tax trusts, liquidation, group/foreign
    entities, other municipalities, local credits/additions and treaty relief.
    """
    if type(fiscal_start_year) is not int or fiscal_start_year != 2026:
        raise ValueError('Only fiscal years starting in2026 reviewed')
    if ordinary_osaka_city_only_no_credits_verified is not True:
        raise ValueError('Full-year ordinary Osaka-city-only levy base and no-credit scope must be verified')
    national, capital = yen(national_levy_base), yen(registered_capital)
    with localcontext() as ctx:
        ctx.prec = 40
        base = (national // 1000) * 1000
        surcharge = capital > 100000000 or base > 20000000
        pref_rate, city_rate = (Decimal('.02'),Decimal('.082')) if surcharge else (Decimal('.01'),Decimal('.06'))
        pref_tax = ((base * pref_rate) // 100) * 100
        city_tax = ((base * city_rate) // 100) * 100
        sources = CITY_SOURCES + [s for s in SOURCES if s['doc_id'] in ('jp.osaka-prefecture-surcharges','jp.osaka-prefecture-return-instructions.202607')]
        return dict(policy_version='jp-osaka-annual-inhabitant-20261119',
            stage='internal_full_year_inhabitant_excluding_capitation_and_interim_payments',
            national_levy_base=national, taxable_levy_base=base, registered_capital=capital,
            surcharge_applies=surcharge, prefectural_rate=pref_rate, city_rate=city_rate,
            prefectural_levy=pref_tax, city_levy=city_tax, total_levy=pref_tax+city_tax,
            sources=deepcopy(sources))


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


class OsakaWorkpaper(BaseModel):
    model_config = ConfigDict(extra='forbid')
    registered_capital: Money
    capital_reserve: Money
    adjusted_statutory_capital: Money
    enterprise_income_additions: Money
    enterprise_income_deductions: Money
    eligible_enterprise_prior_losses: Money
    enterprise_interim_liability: Money
    special_enterprise_interim_liability: Money
    prefectural_inhabitant_interim_liability: Money
    city_inhabitant_interim_liability: Money
    prefectural_capitation_interim_liability: Money
    city_capitation_interim_liability: Money
    wards: list[OsakaWard] = Field(min_length=1, max_length=24)
    all_offices_in_wards_for_full_year_verified: StrictBool
    ordinary_domestic_entity_verified: StrictBool
    size_based_exclusion_including_2025_2026_verified: StrictBool
    capital_employees_and_local_base_verified: StrictBool
    no_local_tax_credits_or_treaty_amendments_verified: StrictBool
    local_adjustments_explanation: str = Field(min_length=20, max_length=4000)


def assess(national, reconciliation, paper):
    for name in ('all_offices_in_wards_for_full_year_verified', 'ordinary_domestic_entity_verified',
                 'size_based_exclusion_including_2025_2026_verified',
                 'capital_employees_and_local_base_verified', 'no_local_tax_credits_or_treaty_amendments_verified'):
        if getattr(paper, name) is not True:
            raise ValueError('Osaka local workpaper requires verified scope: ' + name)
    components = ('enterprise', 'special_enterprise', 'prefectural_inhabitant',
                  'city_inhabitant', 'prefectural_capitation', 'city_capitation')
    with localcontext() as ctx:
        ctx.prec = 40
        interim = {key: yen(getattr(paper, key + '_interim_liability')) for key in components}
        if any(value % 100 for value in interim.values()):
            raise ValueError('Local interim return liabilities must be whole hundreds of yen')
        additions, deductions, losses = map(yen, (paper.enterprise_income_additions,
            paper.enterprise_income_deductions, paper.eligible_enterprise_prior_losses))
        before_losses = reconciliation['income_before_loss_relief'] + additions - deductions
        available = max(Decimal(0), before_losses)
        used = min(available, losses)
        income = available - used
        enterprise = ordinary_enterprise(income, fiscal_start_year=2026, months=12,
            registered_capital=paper.registered_capital, ordinary_single_prefecture_scope_verified=True)
        inhabitant = annual_inhabitant(national['corporation_tax_reference'], fiscal_start_year=2026,
            registered_capital=paper.registered_capital, ordinary_osaka_city_only_no_credits_verified=True)
        capitation = annual_capitation(fiscal_start_year=2026, registered_capital=paper.registered_capital,
            capital_reserve=paper.capital_reserve, adjusted_statutory_capital=paper.adjusted_statutory_capital,
            wards=paper.wards, full_year_osaka_city_scope_verified=True)
        taxes = dict(enterprise=enterprise['enterprise_tax_before_credits'],
            special_enterprise=enterprise['special_enterprise_tax_before_credits'],
            prefectural_inhabitant=inhabitant['prefectural_levy'], city_inhabitant=inhabitant['city_levy'],
            prefectural_capitation=capitation['prefectural_capitation'], city_capitation=capitation['city_capitation'])
        balances = {key: value - interim[key] for key, value in taxes.items()}
        sources = {s['doc_id']: s for part in (enterprise, inhabitant, capitation) for s in part['sources']}
        return dict(scope='ordinary_domestic_full_year_osaka_city_only',
            local_income_reconciliation=dict(national_income_before_losses=reconciliation['income_before_loss_relief'],
                enterprise_additions=additions, enterprise_deductions=deductions,
                enterprise_income_before_losses=before_losses, enterprise_prior_losses_used=used,
                enterprise_prior_losses_unused=losses-used, enterprise_taxable_income=income,
                capital_for_per_capita_band=capitation['capital_for_rate_band']),
            enterprise=enterprise, inhabitant=inhabitant, capitation=capitation,
            local_tax_components=taxes, local_final_tax=sum(taxes.values(), Decimal(0)),
            local_interim_liabilities=interim, local_balances=balances,
            local_amounts_payable=sum((max(Decimal(0), v) for v in balances.values()), Decimal(0)),
            local_refunds=sum((max(Decimal(0), -v) for v in balances.values()), Decimal(0)),
            sources=list(sources.values()),
            scope_note='Separate component balances; no automatic cross-tax offset or other-municipality liability.')
