from copy import deepcopy
from decimal import localcontext
from fractions import Fraction as F
import json
import pytest
from packages.income_tax.hong_kong_saved_credit_constraints import Workpaper, reconcile_constraints
from packages.income_tax.hong_kong_foreign_credit import calculate, calculate_eligibility
from tests.income_tax.test_hong_kong_foreign_reconciliation import fixture as saved_fixture
from tests.income_tax.test_hong_kong_foreign_credit import fixture as credit_fixture


def fixture(country='sg'):
    case,p=saved_fixture();data=case.model_dump()
    data['claimed_deductions']='0'
    data['incomes'][0]['gross_amount']='0'
    data['incomes'][1].update(source_jurisdiction=country,gross_amount='100000',foreign_tax_paid='20000')
    p['groups'][0]['allowable_expenses']='0'
    p['groups'][1]['underlying_tax_gross_up']='0'
    claim=p['groups'][1]['foreign_credit']
    del claim['hong_kong_tax_on_same_income']
    claim.update(country=country,direct_foreign_tax_paid='20000',underlying_tax_paid='0',
                 underlying_unilateral_eligible_tax='0')
    p.update(hong_kong_resident_mne_verified=True,
        source_tax_attribution_and_gross_up_verified=True,payment_fx_and_claim_evidence_verified=True)
    return data,p


def run(case,p,**overrides):
    args=dict(established_credit_rate=F(27,200),tax_bands=[(None,F(165,1000))],
        tax_reduction=F(3000),annual_rate_schedule_and_deduction_eligibility_verified=True)
    args.update(overrides)
    return reconcile_constraints(case,p,**args)


def exact(value):
    return F(int(value['numerator']),int(value['denominator']))


@pytest.mark.parametrize('country',['cn','sg','id','vn','my','th','ae','jp','kr','in'])
def test_all_catalog_foreign_sources_reconcile_saved_payments_without_fake_tax_limit(country):
    case,p=fixture(country)
    # These synthetic eligibility facts do not assert any specific treaty entitlement.
    validated=Workpaper.model_validate(p)
    assert 'hong_kong_tax_on_same_income' not in validated.model_dump_json()
    result=run(case,Workpaper.model_validate_json(validated.model_dump_json()))
    aggregate=result['exact_constraints']['aggregate']
    assert exact(aggregate['foreign_tax_credit'])==F(2040000,167)
    assert exact(aggregate['excess_foreign_tax_deduction'])==F(1300000,167)
    assert exact(aggregate['tax_after_credit'])==0
    assert result['source_eligibility'][0]['country']==country
    assert result['source_eligibility'][0]['total_eligible_tax']==20000
    assert not result['constraints']['allocation_required']
    assert 'final_tax' not in result
    json.dumps(result,default=str)


def test_distinct_sources_retain_allocation_requirement_and_explicit_reconciliation():
    case,p=fixture();case['incomes'][1].update(gross_amount='50000',foreign_tax_paid='10000')
    p['groups'][1]['foreign_credit']['direct_foreign_tax_paid']='10000'
    extra=deepcopy(case['incomes'][1]);extra['source_jurisdiction']='cn';case['incomes'].append(extra)
    group=deepcopy(p['groups'][1]);group.update(source_id='receipt_b',income_indexes=[2])
    group['foreign_credit'].update(source_id='receipt_b',country='cn');p['groups'].append(group)
    result=run(case,p)
    assert result['constraints']['allocation_required']
    assert result['constraints']['source_reconciliation'] is None
    allocations={'receipt_a':F(1020000,167),'receipt_b':F(1020000,167)}
    completed=run(case,p,allocations=allocations)
    assert not completed['constraints']['allocation_required']
    assert len(completed['constraints']['source_reconciliation'])==2


def test_underlying_tax_and_saved_direct_tax_remain_separate():
    case,p=fixture();claim=p['groups'][1]['foreign_credit']
    claim.update(underlying_tax_paid='5000',underlying_unilateral_eligible_tax='5000')
    p['groups'][1]['underlying_tax_gross_up']='5000'
    result=run(case,p)
    assert result['source_eligibility'][0]['total_eligible_tax']==25000
    assert result['saved_receipt_reconciliation'][1]['underlying_tax_gross_up']==5000
    assert case['incomes'][1]['foreign_tax_paid']=='20000'
    assert result['saved_receipt_reconciliation'][1]['source_basis_before_excess_foreign_tax_deduction']==105000


def test_saved_two_tier_case_reconciles_across_threshold():
    case,p=fixture()
    case['incomes'][1].update(gross_amount='2100000',foreign_tax_paid='600000')
    p['groups'][1]['foreign_credit']['direct_foreign_tax_paid']='600000'
    result=run(case,p,established_credit_rate=F(17,200),
        tax_bands=[(F(2000000),F(825,10000)),(None,F(165,1000))])
    aggregate=result['exact_constraints']['aggregate']
    assert exact(aggregate['foreign_tax_credit'])==F(48300000,367)
    assert exact(aggregate['income_after_foreign_tax_deduction'])<2000000
    assert exact(aggregate['tax_after_credit'])==0


def test_exempt_receipt_is_retained_without_entering_credit_or_deduction_pool():
    case,p=fixture()
    case['incomes'].append(dict(category='interest',source_jurisdiction='cn',gross_amount='5000',
        foreign_tax_paid='500',description='Verified exempt receipt'))
    p['groups'].append(dict(source_id='exempt',income_indexes=[2],allowable_expenses='0',
        taxable_additions='0',excluded_income='5000',underlying_tax_gross_up='0'))
    result=run(case,p)
    assert len(result['saved_receipt_reconciliation'])==3
    assert len(result['source_eligibility'])==1
    aggregate=result['exact_constraints']['aggregate']
    assert exact(aggregate['foreign_tax_credit'])+exact(aggregate['excess_foreign_tax_deduction'])==20000


def test_case_and_workpaper_are_unchanged_under_low_decimal_precision():
    case,p=fixture();original=deepcopy((case,p));expected=run(case,p)
    with localcontext() as context:
        context.prec=3
        actual=run(case,p)
    assert actual==expected
    assert (case,p)==original


@pytest.mark.parametrize('change',['paid','missing_paid','expenses','unknown_limit','gross_up',
    'missing_evidence','ownership','duplicate','excluded','loss','annual_evidence','float_rate'])
def test_inconsistent_saved_inputs_do_not_reach_aggregate_result(change):
    case,p=fixture();claim=p['groups'][1]['foreign_credit'];args={}
    if change=='paid':case['incomes'][1]['foreign_tax_paid']='19999'
    elif change=='missing_paid':case['incomes'][1]['foreign_tax_paid']=None
    elif change=='expenses':case['claimed_deductions']='1'
    elif change=='unknown_limit':claim['hong_kong_tax_on_same_income']='100'
    elif change=='gross_up':claim.update(underlying_tax_paid='100',underlying_unilateral_eligible_tax='100')
    elif change=='missing_evidence':p['payment_fx_and_claim_evidence_verified']=False
    elif change=='ownership':
        claim.update(underlying_tax_paid='100',underlying_unilateral_eligible_tax='100',equity_fraction_at_distribution='.01')
        p['groups'][1]['underlying_tax_gross_up']='100'
    elif change=='duplicate':p['groups'].append(deepcopy(p['groups'][1]))
    elif change=='excluded':p['groups'][1]['excluded_income']='100000'
    elif change=='loss':case['carried_losses']='1'
    elif change=='annual_evidence':args['annual_rate_schedule_and_deduction_eligibility_verified']=False
    elif change=='float_rate':args['established_credit_rate']=.135
    with pytest.raises(ValueError):run(case,p,**args)


def test_extracted_eligibility_matches_legacy_credit_inputs_and_precision():
    p=credit_fixture();facts=deepcopy(p)
    for item in facts['sources']:del item['hong_kong_tax_on_same_income']
    eligible=calculate_eligibility(facts)
    with localcontext() as context:
        context.prec=3
        legacy=calculate(p,total_hong_kong_tax='1000.123456')
    for key,value in eligible['source_eligibility'][0].items():
        assert legacy['source_credits'][0][key]==value
    assert legacy['tax_after_credit_before_other_adjustments']==F('750.123456')
