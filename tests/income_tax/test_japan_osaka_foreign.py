from decimal import localcontext
import hashlib
from pathlib import Path
import pytest
from packages.contracts.income_tax import IncomeTaxCase,CURRENCIES
from packages.income_tax.japan_osaka_foreign import settle,Workpaper
from tests.income_tax.test_japan_foreign_reconciliation import fixture


def paper():
    p=dict(registered_capital=10000000,capital_reserve=0,adjusted_statutory_capital=10000000,
        enterprise_income_additions=0,enterprise_income_deductions=0,
        wards=[dict(ward_name='北区',employees=10)],
        local_adjustments_explanation='Verified ordinary enterprise base with no additional local adjustments.')
    for name in Workpaper.model_fields:
        if name.endswith('_verified'):p[name]=True
        if name.endswith('_interim_liability'):p[name]=0
    return p


def run(case=None,source=None,local=None):
    if case is None:case,source=fixture()
    saved=IncomeTaxCase.model_validate_json(IncomeTaxCase(**case).model_dump_json())
    return settle(saved,source,local or paper(),rate_regime='ordinary',rate_classification_verified=True,
        no_other_tax_credits_additions_or_history_verified=True)


@pytest.mark.parametrize('country',[c for c in CURRENCIES if c!='jp'])
def test_saved_cross_border_case_settles_nine_components(country):
    case,source=fixture(country);r=run(case,source)
    assert {k:v['annual_liability'] for k,v in r['settlements'].items()}==dict(
        corporation=13920000,local_corporation=1433700,defence=436800,
        enterprise=7258200,special_enterprise=2513000,prefectural_inhabitant=371200,
        city_inhabitant=1345600,prefectural_capitation=20000,city_capitation=50000)
    assert r['total_annual_liability']==27348500
    assert r['total_payable']==27348500
    assert r['total_refundable']==0
    assert r['current_foreign_credit']['foreign_tax_above_all_current_limits']==823360


def test_refunds_remain_separate_from_other_tax_payments():
    p=paper();p.update(corporation_interim_liability=14000000,
        city_inhabitant_interim_liability=2000000,city_capitation_interim_liability=100000)
    r=run(local=p)
    assert r['total_refundable']==784400
    assert r['total_payable']==12032900
    assert r['settlements']['corporation']['refundable']==80000
    assert r['settlements']['city_inhabitant']['refundable']==654400
    assert r['settlements']['city_capitation']['refundable']==50000


def test_one_yen_city_credit_is_applied_before_final_hundred_yen_truncation():
    case,s=fixture();case['incomes'][1]['foreign_tax_paid']='10619841'
    s['groups'][1]['eligible_foreign_corporate_tax']='10619841'
    r=run(case,s)['settlements']['city_inhabitant']
    assert r['reference_tax']==1902400
    assert r['current_foreign_credit']==1
    assert r['after_credit_before_final_rounding']==1902399
    assert r['annual_liability']==1902300


def test_second_ward_only_adds_capitation_not_a_second_municipal_credit():
    p=paper();p['wards'].append(dict(ward_name='中央区',employees=51))
    r=run(local=p)
    assert r['settlements']['city_capitation']['annual_liability']==170000
    assert r['settlements']['prefectural_capitation']['annual_liability']==20000
    assert len(r['current_foreign_credit']['municipal']['filings'])==1
    assert r['settlements']['city_inhabitant']['annual_liability']==1345600


def test_enterprise_adjustments_do_not_rewrite_national_credit_denominator():
    p=paper();p['enterprise_income_deductions']=10000000
    r=run(local=p)
    assert r['enterprise_reconciliation']['taxable_income']==90000000
    assert r['source_reconciliation']['statutory_worldwide_income']==100000000
    assert r['settlements']['corporation']['annual_liability']==13920000
    assert r['settlements']['enterprise']['annual_liability']==6510200


@pytest.mark.parametrize('flag',[name for name in Workpaper.model_fields if name.endswith('_verified')])
def test_unverified_scope_requires_separate_treatment(flag):
    p=paper();p[flag]=False
    with pytest.raises(ValueError):run(local=p)


@pytest.mark.parametrize('change',['fractional_interim','duplicate_ward','outside_ward','large_capital','blank_reason'])
def test_invalid_local_inputs_rejected(change):
    p=paper()
    if change=='fractional_interim':p['city_inhabitant_interim_liability']=1
    elif change=='duplicate_ward':p['wards']*=2
    elif change=='outside_ward':p['wards'][0]['ward_name']='Tokyo'
    elif change=='large_capital':p['registered_capital']=100000001
    else:p['local_adjustments_explanation']=' '*30
    with pytest.raises(ValueError):run(local=p)


def test_settlement_is_independent_of_ambient_decimal_precision():
    expected=run()
    with localcontext() as context:
        context.prec=6
        assert run()==expected


def test_all_source_archives_match_including_local_return_rounding():
    sources=run()['sources'];ids=[s['doc_id'] for s in sources]
    assert len(ids)==len(set(ids))
    assert 'jp.osaka-prefecture-return-instructions.202607' in ids
    assert 'jp.osaka-city-return-instructions' in ids
    root=Path(__file__).resolve().parents[2]
    for s in sources:
        assert hashlib.sha256((root/s['file']).read_bytes()).hexdigest()==s['sha256']
