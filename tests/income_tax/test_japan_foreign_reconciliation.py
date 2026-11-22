from copy import deepcopy
import pytest
from packages.contracts.income_tax import IncomeTaxCase,CURRENCIES
from packages.income_tax.japan_foreign_reconciliation import reconcile,current_credit_workpaper
from packages.income_tax.japan_foreign_credit import current_national_credits


def fixture(country='sg'):
    case=dict(subject='company',jurisdiction='jp',currency='JPY',residency='resident',
        period_start='2026-04-01',period_end='2027-03-31',facts_confirmed=True,
        claimed_deductions='20000000',carried_losses='0',incomes=[
            dict(category='business',source_jurisdiction='jp',gross_amount='70000000',description='Domestic ordinary receipts'),
            dict(category='royalty',source_jurisdiction=country,gross_amount='50000000',foreign_tax_paid='12000000',description='Foreign ordinary receipts')])
    workpaper=dict(groups=[dict(source_id='home',income_indexes=[0],allowable_expenses='10000000',foreign_income_exempt_from_foreign_tax='0',eligible_foreign_corporate_tax='0'),
        dict(source_id='overseas',income_indexes=[1],allowable_expenses='10000000',foreign_income_exempt_from_foreign_tax='0',eligible_foreign_corporate_tax='12000000')],
        japanese_source_income_and_expense_allocation_verified=True,
        foreign_tax_eligibility_high_tax_exclusions_treaty_fx_and_period_verified=True,
        foreign_tax_exempt_income_and_no_double_deduction_verified=True,
        no_losses_dividend_exemptions_pe_adjustments_groups_or_special_regimes_verified=True)
    return case,workpaper


@pytest.mark.parametrize('country',[c for c in CURRENCIES if c!='jp'])
def test_saved_sources_across_catalog_feed_current_national_credit_component(country):
    case,p=fixture(country);r=reconcile(IncomeTaxCase(**case),p)
    assert r['statutory_worldwide_income']==100000000
    assert r['foreign_income_before_exempt']==40000000
    credit=current_national_credits(**{k:r[k] for k in ('statutory_worldwide_income',
        'foreign_income_before_exempt','foreign_income_exempt_from_foreign_tax','eligible_foreign_corporate_tax')},
        corporation_tax_reference='23200000',local_corporation_tax_reference='2389600',defence_tax_reference='728000',
        defence_applicable=True,statutory_reference_amounts_and_current_tax_eligibility_verified=True,
        no_history_group_or_special_credit_adjustments_verified=True)
    assert credit['total_current_national_credit']==10527040


def test_saved_split_receipts_do_not_change_source_or_credit_inputs():
    case,p=fixture();expected=reconcile(IncomeTaxCase(**case),p)
    item=deepcopy(case['incomes'][1]);item.update(gross_amount='25000000',foreign_tax_paid='6000000')
    case['incomes'][1]=deepcopy(item);case['incomes'].append(item)
    p['groups'][1]['income_indexes']=[1,2]
    assert reconcile(IncomeTaxCase(**case),p)==expected


def test_exempt_foreign_income_is_separate_from_worldwide_taxable_income():
    case,p=fixture();p['groups'][1]['foreign_income_exempt_from_foreign_tax']='10000000'
    p['groups'][1]['eligible_foreign_corporate_tax']='9000000'
    r=reconcile(IncomeTaxCase(**case),p)
    assert r['statutory_worldwide_income']==100000000
    assert r['foreign_income_exempt_from_foreign_tax']==10000000
    assert r['eligible_foreign_corporate_tax']==9000000


@pytest.mark.parametrize('change',['duplicate','omitted','negative_index','id','mixed','expenses','loss',
    'paid','missing_paid','domestic_paid','exempt','domestic_exempt','fraction','unconfirmed','prior_loss','period','dividend','evidence'])
def test_invalid_saved_workpapers_rejected(change):
    case,p=fixture();g=p['groups'][1]
    if change=='duplicate':g['income_indexes']=[1,1]
    elif change=='omitted':p['groups']=[g]
    elif change=='negative_index':g['income_indexes']=[-1]
    elif change=='id':g['source_id']=' home '
    elif change=='mixed':g['income_indexes']=[0,1];g['allowable_expenses']='20000000';p['groups']=[g]
    elif change=='expenses':g['allowable_expenses']='1'
    elif change=='loss':g['allowable_expenses']='50000001';case['claimed_deductions']='60000001'
    elif change=='paid':g['eligible_foreign_corporate_tax']='12000001'
    elif change=='missing_paid':case['incomes'][1].pop('foreign_tax_paid')
    elif change=='domestic_paid':case['incomes'][0]['foreign_tax_paid']='1'
    elif change=='exempt':g['foreign_income_exempt_from_foreign_tax']='40000001'
    elif change=='domestic_exempt':p['groups'][0]['foreign_income_exempt_from_foreign_tax']='1'
    elif change=='fraction':case['incomes'][1]['gross_amount']='50000000.1'
    elif change=='unconfirmed':case['facts_confirmed']=False
    elif change=='prior_loss':case['carried_losses']='1'
    elif change=='period':case['period_end']='2026-12-31'
    elif change=='dividend':case['incomes'][1]['category']='dividend'
    else:p['foreign_tax_eligibility_high_tax_exclusions_treaty_fx_and_period_verified']=False
    with pytest.raises(ValueError):reconcile(IncomeTaxCase(**case),p)


def workpaper(case,p,**changes):
    options=dict(rate_regime='ordinary',rate_classification_verified=True,
        no_other_tax_credits_additions_or_history_verified=True)
    options.update(changes)
    return current_credit_workpaper(IncomeTaxCase(**case),p,**options)


def test_saved_workpaper_derives_three_reference_taxes_without_manual_tax_inputs():
    case,p=fixture();r=workpaper(case,p)
    assert r['reference_taxes']==dict(corporation_tax_reference=23200000,
        local_corporation_tax_reference=2389600,defence_tax_reference=728000,defence_applicable=True)
    assert r['current_national_credit']['total_current_national_credit']==10527040
    assert 'final_tax' not in r


def test_statutory_denominator_and_reference_tax_are_not_final_rounded_amounts():
    from fractions import Fraction
    case,p=fixture();case['incomes'][0]['gross_amount']='70001999'
    r=workpaper(case,p)
    assert r['reconciliation']['statutory_worldwide_income']==100001999
    assert r['corporation_taxable_base']==100001000
    assert r['reference_taxes']['corporation_tax_reference']==23200232
    assert r['local_corporation_tax_base']==23200000
    fraction=r['current_national_credit']['exact_fractions']['corporation_credit_limit']
    assert Fraction(int(fraction['numerator']),int(fraction['denominator']))==Fraction(23200232*40000000,100001999)


@pytest.mark.parametrize('start,end,applies',[
    ('2026-01-01','2026-12-31',False),('2026-03-31','2027-03-30',False),
    ('2026-04-01','2027-03-31',True)])
def test_defence_commencement_is_derived_from_saved_period(start,end,applies):
    case,p=fixture();case.update(period_start=start,period_end=end)
    r=workpaper(case,p)
    assert r['reference_taxes']['defence_applicable'] is applies
    assert r['reference_taxes']['defence_tax_reference']==(728000 if applies else 0)


@pytest.mark.parametrize('scheme,reference',[('sme_reduced',22544000),('sme_excluded',22864000)])
def test_verified_sme_rate_classification_changes_derived_credit_reference(scheme,reference):
    case,p=fixture();r=workpaper(case,p,rate_regime=scheme)
    assert r['reference_taxes']['corporation_tax_reference']==reference


@pytest.mark.parametrize('options',[dict(rate_classification_verified=False),
    dict(no_other_tax_credits_additions_or_history_verified=False),dict(rate_regime='unknown')])
def test_unverified_reference_or_excluded_adjustments_rejected(options):
    case,p=fixture()
    with pytest.raises(ValueError):workpaper(case,p,**options)


def test_derived_reference_sources_have_archived_originals():
    from pathlib import Path
    import hashlib
    case,p=fixture();root=Path(__file__).resolve().parents[2]
    for source in workpaper(case,p)['sources']:
        assert hashlib.sha256((root/source['file']).read_bytes()).hexdigest()==source['sha256']
