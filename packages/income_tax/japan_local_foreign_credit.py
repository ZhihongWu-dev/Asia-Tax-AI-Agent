"""Current local credit allocation with verified caps and filing weights.

This preserves separate limit excess, tax-shortfall and rounding residuals.
It does not approve historical carryforward or derive actual-rate elections.
"""
from copy import deepcopy
from decimal import Decimal
from pydantic import BaseModel,ConfigDict,Field,StrictBool,StrictInt
from packages.contracts.income_tax import Money
from .japan import yen
from .japan_foreign_credit import current_national_return_credits

SOURCES=[
 dict(doc_id='jp.defence-order.20261122',file='database/raw/jp/jp.defence-order.20261122.json',
  url='https://laws.e-gov.go.jp/law/507CO0000000134/20260401_508CO0000000105',
  sha256='baa3225cef5504c9020518b5e98a8e76a669ca58c23cc54b8bec4cc8e91edf73',
  provisions=['Article19: substitutions for Corporate Tax Order144(6)-(7),145(4), adding defence limits']),
 dict(doc_id='jp.nta.form6-3.2026',file='database/raw/jp/jp.nta.form6-3.2026.pdf',
  url='https://www.nta.go.jp/taxes/tetsuzuki/shinsei/annai/hojin/shinkoku/itiran2026/pdf/06%2803%29.pdf',
  sha256='85d9c1a4336717ea2eaa2fe8bc7c5ed78492f4135fe5dd96dd0a718428a04afd',provisions=['Lines8-12: current unused capacity and excess']),
 dict(doc_id='jp.nta.form6-3.instructions.2026',file='database/raw/jp/jp.nta.form6-3.instructions.2026.pdf',
  url='https://www.nta.go.jp/taxes/tetsuzuki/shinsei/annai/hojin/shinkoku/itiran2026/pdf/06%2803%29-ki.pdf',
  sha256='6a0cc634b8edb122862c9580eeba71b921383e502c85928bd77bb362f6863de5',provisions=['Instructions2-6: separate local elections, reorganizations and reduced foreign tax']),
 dict(doc_id='jp.osaka.foreign-form20-4.2026',file='database/raw/jp/jp.osaka.foreign-form20-4.2026.pdf',
  url='https://www.city.osaka.lg.jp/zaisei/cmsfiles/contents/0000006/6410/14_20gou4_R8.3.pdf',
  sha256='031029eb2fdbe0d4e3637ef029027f938b7c06e43bd7bdf41434ca64249509b1',provisions=['Lines4-15,19-23']),
 dict(doc_id='jp.osaka.foreign-form20-4.instructions.2026',file='database/raw/jp/jp.osaka.foreign-form20-4.instructions.2026.pdf',
  url='https://www.city.osaka.lg.jp/zaisei/cmsfiles/contents/0000006/6410/14_20gou4_betu1_2_3_4_5_6_7_tebiki_R8.3.pdf',
  sha256='9aa0eb38a4228c57de36564a9dfa40a2ff427a7122b7e897409d5f7dad6fe82b',provisions=['Form20-4 instructions6-11']),
 dict(doc_id='jp.osaka.foreign-form7-2.instructions.2026',file='database/raw/jp/jp.osaka.foreign-form7-2.instructions.2026.pdf',
  url='https://www.pref.osaka.lg.jp/documents/525/d7no2-s1-tebiki.pdf',
  sha256='cee2aff5b86eac5669b5177a06629eb329998e95751a61e09153bc9e35274f4b',provisions=['Instructions5-9']),
]


class Filing(BaseModel):
    model_config=ConfigDict(extra='forbid')
    filing_id: str=Field(min_length=1,max_length=120,pattern=r'^\S(?:.*\S)?$')
    verified_employee_weight: StrictInt=Field(ge=0,le=1000000000)
    available_corporation_levy_before_final_rounding: Money


class AllocationInputs(BaseModel):
    model_config=ConfigDict(extra='forbid')
    prefectural_credit_limit: Money
    municipal_credit_limit: Money
    prefectures: list[Filing]=Field(min_length=1,max_length=1000)
    municipalities: list[Filing]=Field(min_length=1,max_length=1000)


class Workpaper(AllocationInputs):
    statutory_limits_elections_weights_and_levies_verified: StrictBool
    no_history_groups_reorganizations_or_tokyo_special_ward_composition_verified: StrictBool


class StandardWorkpaper(BaseModel):
    """Standard statutory limits; callers cannot override derived caps."""
    model_config=ConfigDict(extra='forbid')
    prefectures: list[Filing]=Field(min_length=1,max_length=1000)
    municipalities: list[Filing]=Field(min_length=1,max_length=1000)
    standard_limits_without_actual_rate_election_verified: StrictBool
    employee_weights_and_available_levies_verified: StrictBool
    no_history_groups_reorganizations_or_tokyo_special_ward_composition_verified: StrictBool


def allocate_standard_current(national_inputs,workpaper):
    p=StandardWorkpaper.model_validate(workpaper)
    if (p.standard_limits_without_actual_rate_election_verified is not True or
            p.employee_weights_and_available_levies_verified is not True):
        raise ValueError('Verify standard-limit election, employee weights and available levies')
    national=current_national_return_credits(**national_inputs)
    corporation_limit=int(national['corporation_credit_limit'])
    result=allocate_current(national_inputs,dict(
        prefectural_credit_limit=corporation_limit//100,
        municipal_credit_limit=corporation_limit*6//100,
        prefectures=p.prefectures,municipalities=p.municipalities,
        statutory_limits_elections_weights_and_levies_verified=True,
        no_history_groups_reorganizations_or_tokyo_special_ward_composition_verified=
            p.no_history_groups_reorganizations_or_tokyo_special_ward_composition_verified))
    result['limit_method']='standard_one_and_six_percent_of_corporation_credit_limit'
    return result


def allocate_current(national_inputs,workpaper):
    p=Workpaper.model_validate(workpaper)
    if (p.statutory_limits_elections_weights_and_levies_verified is not True or
            p.no_history_groups_reorganizations_or_tokyo_special_ward_composition_verified is not True):
        raise ValueError('Verify local limits, weights, levy amounts and excluded adjustments')
    national=current_national_return_credits(**national_inputs)
    paid=int(yen(national_inputs['eligible_foreign_corporate_tax']))
    return _allocate_current_component(national,paid,p)


def _allocate_current_component(national,paid,workpaper):
    """Internal current component; no claim that the whole case lacks history."""
    p=AllocationInputs.model_validate({key:getattr(workpaper,key) for key in AllocationInputs.model_fields})
    paid=int(yen(paid))
    corp=int(national['corporation_credit_limit'])
    total_national=sum(int(national[k]) for k in (
        'corporation_credit_limit','local_corporation_credit_limit','defence_credit_limit'))
    # Forms7-2/20-4 line4 switches among corporation limit, paid tax and the
    # total national limit. With no history, this is max(corp,min(paid,total)).
    national_form_limit=max(corp,min(paid,total_national))
    pref_limit=int(yen(p.prefectural_credit_limit));city_limit=int(yen(p.municipal_credit_limit))
    pref_pool=min(max(0,paid-national_form_limit),pref_limit)
    city_pool=min(max(0,paid-national_form_limit-pref_limit),city_limit)
    def distribute(pool,filings):
        ids=[row.filing_id for row in filings]
        total_weight=sum(row.verified_employee_weight for row in filings)
        if len(ids)!=len(set(ids)) or total_weight==0:
            raise ValueError('Unique filing groups and positive total employee weight required')
        rows=[]
        for row in filings:
            assigned=pool*row.verified_employee_weight//total_weight
            levy=int(yen(row.available_corporation_levy_before_final_rounding))
            used=min(assigned,levy)
            rows.append(dict(filing_id=row.filing_id,employee_weight=row.verified_employee_weight,
                allocated_credit=Decimal(assigned),available_levy=Decimal(levy),
                current_credit=Decimal(used),unrelieved_due_to_levy_shortfall=Decimal(assigned-used)))
        return dict(credit_pool=Decimal(pool),filings=rows,
            current_credit=sum((r['current_credit'] for r in rows),Decimal(0)),
            unrelieved_due_to_levy_shortfall=sum((r['unrelieved_due_to_levy_shortfall'] for r in rows),Decimal(0)),
            unallocated_rounding_residual=Decimal(pool)-sum((r['allocated_credit'] for r in rows),Decimal(0)))
    pref=distribute(pref_pool,p.prefectures);city=distribute(city_pool,p.municipalities)
    return dict(policy_version='jp-current-local-foreign-allocation-20261122',currency='JPY',
        national_credit=national,national_form_limit=Decimal(national_form_limit),
        prefectural_credit_limit=Decimal(pref_limit),municipal_credit_limit=Decimal(city_limit),
        prefectural=pref,municipal=city,
        # Schedule6(3) lines8-10. National carry capacity is corporation-only;
        # unused local-corporation/defence limits are not included in line8.
        current_unused_capacity_before_history=dict(
            national=Decimal(max(0,corp-paid)),
            prefectural=Decimal(max(0,min(pref_limit,total_national+pref_limit-paid))),
            municipal=Decimal(max(0,min(city_limit,total_national+pref_limit+city_limit-paid)))),
        unused_national_limits_not_in_carry_capacity=sum((
            national[k+'_credit_limit']-national[k+'_credit']
            for k in ('local_corporation','defence')),Decimal(0)),
        foreign_tax_above_all_current_limits=Decimal(max(0,paid-total_national-pref_limit-city_limit)),
        sources=deepcopy(SOURCES),
        stage='current_local_allocation_not_final_tax_or_approved_carryforward')
