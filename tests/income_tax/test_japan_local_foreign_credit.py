import hashlib
from pathlib import Path
import pytest
from packages.income_tax.japan_local_foreign_credit import allocate_current,SOURCES
from tests.income_tax.test_japan_foreign_credit import args


def paper():
    return dict(prefectural_credit_limit=92800,municipal_credit_limit=556800,
        prefectures=[dict(filing_id='Osaka prefecture',verified_employee_weight=10,available_corporation_levy_before_final_rounding=464000)],
        municipalities=[dict(filing_id='Osaka city',verified_employee_weight=10,available_corporation_levy_before_final_rounding=1902400)],
        statutory_limits_elections_weights_and_levies_verified=True,
        no_history_groups_reorganizations_or_tokyo_special_ward_composition_verified=True)


def test_local_credit_follows_all_three_national_limits():
    r=allocate_current(args(),paper())
    assert r['national_form_limit']==10527040
    assert r['prefectural']['current_credit']==92800
    assert r['municipal']['current_credit']==556800
    assert r['foreign_tax_above_all_current_limits']==823360


def test_prefectural_levy_shortfall_does_not_increase_municipal_credit():
    n=args();n['eligible_foreign_corporate_tax']=10600000
    p=paper();p['prefectures'][0]['available_corporation_levy_before_final_rounding']=100
    r=allocate_current(n,p)
    assert r['prefectural']['credit_pool']==72960
    assert r['prefectural']['current_credit']==100
    assert r['prefectural']['unrelieved_due_to_levy_shortfall']==72860
    assert r['municipal']['current_credit']==0
    assert r['foreign_tax_above_all_current_limits']==0


def test_employee_allocation_rounds_each_filing_and_does_not_redistribute_shortfall():
    n=args();n['eligible_foreign_corporate_tax']=10527047
    p=paper();p['prefectures']=[dict(filing_id=str(i),verified_employee_weight=1,
        available_corporation_levy_before_final_rounding=0 if i==0 else 100) for i in range(3)]
    r=allocate_current(n,p)['prefectural']
    assert [row['allocated_credit'] for row in r['filings']]==[2,2,2]
    assert r['current_credit']==4
    assert r['unrelieved_due_to_levy_shortfall']==2
    assert r['unallocated_rounding_residual']==1


@pytest.mark.parametrize('paid',[0,100,9280000,9500000,10527040,10527041,10619840,11176640,12000000])
def test_allocation_conserves_foreign_tax_without_combining_balance_types(paid):
    n=args();n['eligible_foreign_corporate_tax']=paid;r=allocate_current(n,paper())
    total=r['national_credit']['total_current_national_credit']+r['foreign_tax_above_all_current_limits']
    for layer in ('prefectural','municipal'):
        total+=sum(r[layer][key] for key in ('current_credit','unrelieved_due_to_levy_shortfall','unallocated_rounding_residual'))
    assert total==paid


@pytest.mark.parametrize('change',['duplicate','zero_weight','bool_weight','fraction_levy','limit','evidence'])
def test_invalid_local_workpaper_rejected(change):
    p=paper()
    if change=='duplicate':p['prefectures']*=2
    elif change=='zero_weight':p['municipalities'][0]['verified_employee_weight']=0
    elif change=='bool_weight':p['municipalities'][0]['verified_employee_weight']=True
    elif change=='fraction_levy':p['municipalities'][0]['available_corporation_levy_before_final_rounding']='1.5'
    elif change=='limit':p['municipal_credit_limit']=-1
    else:p['statutory_limits_elections_weights_and_levies_verified']=False
    with pytest.raises(ValueError):allocate_current(args(),p)


def test_sources_match_archived_originals():
    root=Path(__file__).resolve().parents[2]
    for source in SOURCES:
        assert hashlib.sha256((root/source['file']).read_bytes()).hexdigest()==source['sha256']


@pytest.mark.parametrize('paid,national,prefectural,municipal,excluded',[
    (0,9280000,92800,556800,1247040),
    (9000000,280000,92800,556800,1247040),
    (9280000,0,92800,556800,1247040),
    (9500000,0,92800,556800,1027040),
    (10527040,0,92800,556800,0),
    (10600000,0,19840,556800,0),
    (10619840,0,0,556800,0),
    (11000000,0,0,176640,0),
    (11176640,0,0,0,0),
    (12000000,0,0,0,0),
])
def test_schedule6_3_capacity_is_not_combined_unused_national_limits(paid,national,prefectural,municipal,excluded):
    n=args();n['eligible_foreign_corporate_tax']=paid
    r=allocate_current(n,paper())
    assert r['current_unused_capacity_before_history']==dict(
        national=national,prefectural=prefectural,municipal=municipal)
    assert r['unused_national_limits_not_in_carry_capacity']==excluded


def test_local_levy_shortfall_does_not_restore_statutory_unused_capacity():
    p=paper();p['prefectures'][0]['available_corporation_levy_before_final_rounding']=0
    r=allocate_current(args(),p)
    assert r['prefectural']['unrelieved_due_to_levy_shortfall']==92800
    assert r['current_unused_capacity_before_history']['prefectural']==0
