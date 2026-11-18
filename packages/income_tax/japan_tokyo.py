"""Full-year ordinary domestic company workpaper for Tokyo's 23 wards.

A scoped integration step; other Japanese locations and special regimes remain
separate work. National and enterprise income/loss bases need not be identical.
"""
from decimal import Decimal, localcontext
from pathlib import Path
import json
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt
from packages.contracts.income_tax import Money
from .japan import yen
from .japan_local import ordinary_enterprise_levies, ordinary_per_capita_component, ordinary_inhabitant_levy


WORKPAPER_SOURCES = json.loads(Path(__file__).with_name('jp_tokyo_workpaper_sources.json').read_text(encoding='utf-8'))['sources']


class Ward(BaseModel):
    model_config = ConfigDict(extra='forbid')
    ward_code: str = Field(pattern=r'^131(?:0[1-9]|1[0-9]|2[0-3])$')
    employees: StrictInt = Field(ge=0)
    principal: StrictBool


class TokyoWorkpaper(BaseModel):
    model_config = ConfigDict(extra='forbid')
    registered_capital: Money
    capital_reserve: Money
    adjusted_statutory_capital: Money
    enterprise_income_additions: Money
    enterprise_income_deductions: Money
    eligible_enterprise_prior_losses: Money
    enterprise_interim_liability: Money
    special_enterprise_interim_liability: Money
    inhabitant_interim_liability: Money
    per_capita_interim_liability: Money
    wards: list[Ward] = Field(min_length=1,max_length=23)
    all_offices_in_wards_for_full_year_verified: StrictBool
    ordinary_domestic_entity_verified: StrictBool
    size_based_exclusion_including_2025_2026_verified: StrictBool
    capital_employees_and_local_base_verified: StrictBool
    no_local_tax_credits_or_treaty_amendments_verified: StrictBool
    local_adjustments_explanation: str = Field(min_length=20,max_length=4000)


def assess(national, reconciliation, paper):
    for name in ('all_offices_in_wards_for_full_year_verified','ordinary_domestic_entity_verified',
                 'size_based_exclusion_including_2025_2026_verified',
                 'capital_employees_and_local_base_verified','no_local_tax_credits_or_treaty_amendments_verified'):
        if getattr(paper,name) is not True:
            raise ValueError('Tokyo local workpaper requires verified scope: '+name)
    codes=[ward.ward_code for ward in paper.wards]
    if len(set(codes))!=len(codes) or sum(ward.principal for ward in paper.wards)!=1:
        raise ValueError('Aggregate each ward once and identify exactly one principal ward')
    money_fields=('registered_capital','capital_reserve','adjusted_statutory_capital',
        'enterprise_income_additions','enterprise_income_deductions','eligible_enterprise_prior_losses',
        'enterprise_interim_liability','special_enterprise_interim_liability',
        'inhabitant_interim_liability','per_capita_interim_liability')
    values={name:yen(getattr(paper,name)) for name in money_fields}
    if values['registered_capital']>100000000:
        raise ValueError('Registered capital above JPY100m requires the size-based enterprise workflow')
    for name in money_fields[-4:]:
        if values[name]%100:
            raise ValueError('Local interim return liabilities must be whole hundreds of yen')
    with localcontext() as ctx:
        ctx.prec=40
        before_losses=(reconciliation['income_before_loss_relief']+
                       values['enterprise_income_additions']-values['enterprise_income_deductions'])
        available=max(Decimal(0),before_losses)
        losses_used=min(available,values['eligible_enterprise_prior_losses'])
        income=available-losses_used
        capital=max(values['adjusted_statutory_capital'],
                    values['registered_capital']+values['capital_reserve'])
        # Only one prefecture: the three-or-more-prefecture reduced-band
        # exclusion does not apply. Expanded size-based exclusions are confirmed above.
        enterprise=ordinary_enterprise_levies(income,fiscal_start_year=2026,months=12,
            reduced_bands_eligible=True,tokyo_surcharge_applies=(income//1000)*1000>25000000,
            ordinary_income_based_scope_verified=True)
        inhabitant=ordinary_inhabitant_levy(national['corporation_tax_reference'],
            fiscal_start_year=2026,months=12,registered_capital=values['registered_capital'],
            ward_allocated_base=national['corporation_tax_reference'],municipality_allocated_base=0,
            ordinary_domestic_scope_verified=True,prepaid_levy=values['inhabitant_interim_liability'])
        ward_results=[]
        for ward in paper.wards:
            row=ordinary_per_capita_component(capital,fiscal_start_year=2026,
                employees_in_ward=ward.employees,office_months=12,
                component='wards_only_principal' if ward.principal else 'ward_only',
                ordinary_capital_scope_verified=True)
            row['ward_code']=ward.ward_code
            ward_results.append(row)
        per_capita=sum((row['per_capita_tax_before_prepayments'] for row in ward_results),Decimal(0))
        taxes={'enterprise':enterprise['enterprise_tax_before_credits'],
               'special_enterprise':enterprise['special_enterprise_tax_before_credits'],
               'inhabitant':inhabitant['final_levy'],'per_capita':per_capita}
        balances={key:tax-values[key+'_interim_liability'] for key,tax in taxes.items()}
        return dict(scope='ordinary_domestic_full_year_tokyo_23_wards_only',
            local_income_reconciliation=dict(national_income_before_losses=reconciliation['income_before_loss_relief'],
                enterprise_additions=values['enterprise_income_additions'],
                enterprise_deductions=values['enterprise_income_deductions'],
                enterprise_income_before_losses=before_losses,enterprise_prior_losses_used=losses_used,
                enterprise_prior_losses_unused=values['eligible_enterprise_prior_losses']-losses_used,
                enterprise_taxable_income=income,capital_for_per_capita_band=capital),
            enterprise=enterprise,inhabitant=inhabitant,wards=ward_results,
            local_tax_components=taxes,local_final_tax=sum(taxes.values(),Decimal(0)),
            local_interim_liabilities={key:values[key+'_interim_liability'] for key in taxes},
            local_balances=balances,
            local_amounts_payable=sum((max(Decimal(0),v) for v in balances.values()),Decimal(0)),
            local_refunds=sum((max(Decimal(0),-v) for v in balances.values()),Decimal(0)),
            scope_note='Separate component balances; no automatic cross-tax offset, future loss approval, or other-municipality liability.')
