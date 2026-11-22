"""Saved-source Osaka annual settlement with two explicit historical ledgers."""
from copy import deepcopy
from decimal import Decimal,localcontext
from .japan import yen
from .japan_osaka import ordinary_enterprise,annual_inhabitant,annual_capitation
from .japan_osaka_foreign import HistoricalWorkpaper
from .japan_foreign_reconciliation import saved_reference_amounts
from .japan_foreign_credit import _current_national_return_component
from .japan_local_foreign_credit import AllocationInputs,_allocate_current_component
from .japan_foreign_history_settlement import settle_national_and_local_history


def settle(case,source_workpaper,local_workpaper,limit_history,levy_history,*,
        rate_regime,rate_classification_verified,no_other_tax_credits_or_additions_verified):
    p=HistoricalWorkpaper.model_validate(local_workpaper)
    for field in HistoricalWorkpaper.model_fields:
        if field.endswith('_verified') and getattr(p,field) is not True:
            raise ValueError('Verify Osaka historical settlement scope: '+field)
    reference=saved_reference_amounts(case,source_workpaper,rate_regime=rate_regime,
        rate_classification_verified=rate_classification_verified,
        no_other_tax_credits_or_additions_verified=no_other_tax_credits_or_additions_verified)
    reconciled=reference['reconciliation'];refs=reference['reference_taxes']
    national=_current_national_return_component(**{k:reconciled[k] for k in (
        'statutory_worldwide_income','foreign_income_before_exempt',
        'foreign_income_exempt_from_foreign_tax','eligible_foreign_corporate_tax')},**refs)
    with localcontext() as context:
        context.prec=40
        world=reconciled['statutory_worldwide_income']
        additions=yen(p.enterprise_income_additions);deductions=yen(p.enterprise_income_deductions)
        enterprise_base=max(Decimal(0),world+additions-deductions)
        enterprise=ordinary_enterprise(enterprise_base,fiscal_start_year=2026,months=12,
            registered_capital=p.registered_capital,ordinary_single_prefecture_scope_verified=True)
        inhabitant=annual_inhabitant(refs['corporation_tax_reference'],
            registered_capital=p.registered_capital,fiscal_start_year=2026,
            ordinary_osaka_city_only_no_credits_verified=True)
        capitation=annual_capitation(fiscal_start_year=2026,registered_capital=p.registered_capital,
            capital_reserve=p.capital_reserve,adjusted_statutory_capital=p.adjusted_statutory_capital,
            wards=p.wards,full_year_osaka_city_scope_verified=True)
        pref_before=inhabitant['taxable_levy_base']*inhabitant['prefectural_rate']
        city_before=inhabitant['taxable_levy_base']*inhabitant['city_rate']
        employees=sum(w.employees for w in p.wards)
        corp_limit=int(national['corporation_credit_limit'])
        allocation=_allocate_current_component(national,reconciled['eligible_foreign_corporate_tax'],
            AllocationInputs(prefectural_credit_limit=corp_limit//100,
                municipal_credit_limit=corp_limit*6//100,
                prefectures=[dict(filing_id='Osaka prefecture',verified_employee_weight=employees,
                    available_corporation_levy_before_final_rounding=pref_before)],
                municipalities=[dict(filing_id='Osaka city',verified_employee_weight=employees,
                    available_corporation_levy_before_final_rounding=city_before)]))
        allocation['limit_method']='standard_one_and_six_percent_of_corporation_credit_limit'
        combined=settle_national_and_local_history(allocation,limit_history,levy_history,
            reference_taxes={k:v for k,v in refs.items() if k.endswith('_tax_reference')},
            period_start=case.period_start,period_end=case.period_end,
            corporation_interim_liability=p.corporation_interim_liability,
            local_corporation_interim_liability=p.local_corporation_interim_liability,
            prefectural_interim_liability=p.prefectural_inhabitant_interim_liability,
            municipal_interim_liability=p.city_inhabitant_interim_liability,
            ordinary_final_return_without_other_credits_or_additions_verified=
                no_other_tax_credits_or_additions_verified)
        settlements=deepcopy(combined['settlements'])
        settlements['city_inhabitant']=settlements.pop('municipal_inhabitant')
        for name,tax in dict(enterprise=enterprise['enterprise_tax_before_credits'],
                special_enterprise=enterprise['special_enterprise_tax_before_credits'],
                prefectural_capitation=capitation['prefectural_capitation'],
                city_capitation=capitation['city_capitation']).items():
            prepaid=yen(getattr(p,name+'_interim_liability'))
            if prepaid%100:
                raise ValueError('Local interim liabilities must be whole hundreds of yen')
            balance=tax-prepaid
            settlements[name]=dict(annual_liability=tax,interim_return_liability=prepaid,
                balance_due=balance,payable=max(Decimal(0),balance),
                interim_refund=max(Decimal(0),-balance),refundable=max(Decimal(0),-balance))
        sources={}
        for part in (combined,reference,enterprise,inhabitant,capitation):
            for source in part['sources']:
                key=source['doc_id']
                if key not in sources:sources[key]=deepcopy(source)
                else:
                    if sources[key]['sha256']!=source['sha256']:
                        raise ValueError('Saved annual settlement source versions must reconcile')
                    sources[key]['provisions']=list(dict.fromkeys(
                        sources[key].get('provisions',[])+source.get('provisions',[])))
        return dict(policy_version='jp-osaka-history-foreign-settlement-20261122',currency='JPY',
            scope='ordinary_full_year_osaka_city_standard_limits_with_verified_history',
            source_reconciliation=reconciled,reference_taxes=refs,current_foreign_credit=allocation,
            enterprise_reconciliation=dict(national_income=world,additions=additions,deductions=deductions,
                taxable_income=enterprise_base,explanation=p.local_adjustments_explanation),
            enterprise=enterprise,capitation=capitation,settlements=settlements,
            **{k:combined[k] for k in ('history_matching','local_levy_history','current_period_levy_shortfall',
                'expired_levy_shortfall','next_period_levy_shortfall','total_foreign_credit_refund')},
            **{'total_'+field:sum((row[field] for row in settlements.values()),Decimal(0))
                for field in ('annual_liability','payable','refundable','interim_refund')},
            sources=list(sources.values()),stage='osaka_nine_tax_annual_settlement_with_verified_history')
