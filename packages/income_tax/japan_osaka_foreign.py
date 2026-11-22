"""Saved ordinary cross-border company settlement for Osaka-city offices.

Current credits only. Historical balances, actual-rate elections, foreign
offices, groups and competing reliefs require separate supported workflows.
"""
from decimal import Decimal,localcontext
from pydantic import BaseModel,ConfigDict,Field,StrictBool
from packages.contracts.income_tax import Money
from .japan import yen
from .japan_osaka import OsakaWard,ordinary_enterprise,annual_inhabitant,annual_capitation
from .japan_foreign_reconciliation import current_national_settlement,current_standard_local_workpaper


class Workpaper(BaseModel):
    model_config=ConfigDict(extra='forbid')
    registered_capital: Money
    capital_reserve: Money
    adjusted_statutory_capital: Money
    enterprise_income_additions: Money
    enterprise_income_deductions: Money
    corporation_interim_liability: Money
    local_corporation_interim_liability: Money
    enterprise_interim_liability: Money
    special_enterprise_interim_liability: Money
    prefectural_inhabitant_interim_liability: Money
    city_inhabitant_interim_liability: Money
    prefectural_capitation_interim_liability: Money
    city_capitation_interim_liability: Money
    wards: list[OsakaWard]=Field(min_length=1,max_length=24)
    all_offices_in_osaka_city_full_year_no_foreign_offices_verified: StrictBool
    ordinary_domestic_entity_and_size_based_exclusion_verified: StrictBool
    capital_employees_and_enterprise_adjustments_verified: StrictBool
    standard_local_limits_no_actual_rate_election_verified: StrictBool
    no_other_local_credits_additions_history_losses_or_treaty_amendments_verified: StrictBool
    local_adjustments_explanation: str=Field(min_length=20,max_length=4000,pattern=r'\S')


def settle(case,source_workpaper,local_workpaper,*,rate_regime,rate_classification_verified,
           no_other_tax_credits_additions_or_history_verified):
    p=Workpaper.model_validate(local_workpaper)
    for field in Workpaper.model_fields:
        if field.endswith('_verified') and getattr(p,field) is not True:
            raise ValueError('Verify Osaka foreign settlement scope: '+field)
    reference_options=dict(rate_regime=rate_regime,rate_classification_verified=rate_classification_verified,
        no_other_tax_credits_additions_or_history_verified=no_other_tax_credits_additions_or_history_verified)
    national=current_national_settlement(case,source_workpaper,
        corporation_interim_liability=p.corporation_interim_liability,
        local_corporation_interim_liability=p.local_corporation_interim_liability,**reference_options)
    with localcontext() as context:
        context.prec=40
        world=national['source_reconciliation']['statutory_worldwide_income']
        additions=yen(p.enterprise_income_additions);deductions=yen(p.enterprise_income_deductions)
        enterprise_base=max(Decimal(0),world+additions-deductions)
        enterprise=ordinary_enterprise(enterprise_base,fiscal_start_year=2026,months=12,
            registered_capital=p.registered_capital,ordinary_single_prefecture_scope_verified=True)
        # Reuse the ordinary pre-credit base/rates, not its rounded final levies.
        inhabitant=annual_inhabitant(national['reference_taxes']['corporation_tax_reference'],
            registered_capital=p.registered_capital,fiscal_start_year=2026,
            ordinary_osaka_city_only_no_credits_verified=True)
        capitation=annual_capitation(fiscal_start_year=2026,registered_capital=p.registered_capital,
            capital_reserve=p.capital_reserve,adjusted_statutory_capital=p.adjusted_statutory_capital,
            wards=p.wards,full_year_osaka_city_scope_verified=True)
        pref_before=inhabitant['taxable_levy_base']*inhabitant['prefectural_rate']
        city_before=inhabitant['taxable_levy_base']*inhabitant['city_rate']
        # There is one prefecture and one municipality. Wards affect capitation,
        # not the number of municipal corporation-levy credit allocations.
        employees=sum(w.employees for w in p.wards)
        local=current_standard_local_workpaper(case,source_workpaper,dict(
            prefectures=[dict(filing_id='Osaka prefecture',verified_employee_weight=employees,
                available_corporation_levy_before_final_rounding=pref_before)],
            municipalities=[dict(filing_id='Osaka city',verified_employee_weight=employees,
                available_corporation_levy_before_final_rounding=city_before)],
            standard_limits_without_actual_rate_election_verified=True,
            employee_weights_and_available_levies_verified=True,
            no_history_groups_reorganizations_or_tokyo_special_ward_composition_verified=True),**reference_options)
        allocation=local['current_foreign_credit']
        if allocation['national_credit']!=national['current_foreign_credit']:
            raise ValueError('National and local credit computations must reconcile')
        pref_credit=allocation['prefectural']['current_credit']
        city_credit=allocation['municipal']['current_credit']
        local_taxes=dict(enterprise=enterprise['enterprise_tax_before_credits'],
            special_enterprise=enterprise['special_enterprise_tax_before_credits'],
            prefectural_inhabitant=((pref_before-pref_credit)//100)*100,
            city_inhabitant=((city_before-city_credit)//100)*100,
            prefectural_capitation=capitation['prefectural_capitation'],city_capitation=capitation['city_capitation'])
        settlements=dict(national['settlements'])
        for name,liability in local_taxes.items():
            interim=yen(getattr(p,name+'_interim_liability'))
            if interim%100:
                raise ValueError('Local interim return liabilities must be whole hundreds of yen')
            balance=liability-interim
            settlements[name]=dict(annual_liability=liability,interim_return_liability=interim,
                balance_due=balance,payable=max(Decimal(0),balance),refundable=max(Decimal(0),-balance))
        for name,before,credit in [('prefectural_inhabitant',pref_before,pref_credit),
                                    ('city_inhabitant',city_before,city_credit)]:
            settlements[name].update(reference_tax=before,current_foreign_credit=credit,
                after_credit_before_final_rounding=before-credit)
        sources={s['doc_id']:s for part in (national,local,enterprise,inhabitant,capitation) for s in part['sources']}
        return dict(policy_version='jp-osaka-current-foreign-settlement-20261122',currency='JPY',
            scope='ordinary_full_year_osaka_city_offices_current_foreign_credit_standard_limits',
            source_reconciliation=national['source_reconciliation'],reference_taxes=national['reference_taxes'],
            current_foreign_credit=allocation,
            enterprise_reconciliation=dict(national_income=world,additions=additions,deductions=deductions,
                taxable_income=enterprise_base,explanation=p.local_adjustments_explanation),
            enterprise=enterprise,capitation=capitation,settlements=settlements,
            total_annual_liability=sum((v['annual_liability'] for v in settlements.values()),Decimal(0)),
            total_payable=sum((v['payable'] for v in settlements.values()),Decimal(0)),
            total_refundable=sum((v['refundable'] for v in settlements.values()),Decimal(0)),
            sources=list(sources.values()),stage='saved_current_year_settlement_history_and_api_ui_pending')
