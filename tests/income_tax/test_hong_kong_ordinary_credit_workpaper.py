from copy import deepcopy
from decimal import localcontext
from fractions import Fraction as F
import hashlib
from pathlib import Path
import pytest
from packages.income_tax.hong_kong_ordinary_credit_workpaper import prepare
from tests.income_tax.test_hong_kong_saved_credit_constraints import fixture, exact


def run(case,p,**args):
    defaults=dict(two_tier_eligible=False,ordinary_annual_basis_and_reduction_ordering_verified=True,
        ongoing_business_unchanged_accounting_year_verified=True)
    defaults.update(args)
    return prepare(case,p,**defaults)


def test_ordinary_rate_is_derived_from_saved_income_before_excess_deduction():
    case,p=fixture();result=run(case,p)
    basis=result['exact_annual_rate_basis'];aggregate=result['exact_constraints']['aggregate']
    assert exact(basis['rate_denominator'])==100000
    assert exact(basis['gross_tax_on_rate_basis'])==16500
    assert exact(basis['tax_reduction_on_rate_basis'])==3000
    assert exact(basis['average_credit_rate'])==F(27,200)
    assert exact(aggregate['foreign_tax_credit'])==F(2040000,167)
    assert exact(aggregate['income_after_foreign_tax_deduction'])!=exact(basis['rate_denominator'])
    assert 'final_tax' not in result


def test_underlying_gross_up_is_excluded_only_from_rate_basis():
    case,p=fixture();claim=p['groups'][1]['foreign_credit']
    claim.update(underlying_tax_paid='5000',underlying_unilateral_eligible_tax='5000')
    p['groups'][1]['underlying_tax_gross_up']='5000'
    result=run(case,p);basis=result['exact_annual_rate_basis']
    assert exact(basis['income_before_excess_tax_deduction'])==105000
    assert exact(basis['underlying_tax_gross_up_excluded'])==5000
    assert exact(basis['rate_denominator'])==100000
    assert exact(basis['average_credit_rate'])==F(27,200)
    aggregate=result['exact_constraints']['aggregate']
    assert exact(aggregate['income_after_foreign_tax_deduction'])+exact(aggregate['excess_foreign_tax_deduction'])==105000


@pytest.mark.parametrize('start,end',[('2025-01-01','2025-12-31'),
    ('2024-07-01','2025-06-30'),('2025-04-01','2026-03-31'),
    ('2024-04-02','2025-04-01'),('2025-03-01','2026-02-28')])
def test_ordinary_annual_accounts_ending_within_assessment_year(start,end):
    case,p=fixture();case.update(period_start=start,period_end=end)
    result=run(case,p)
    assert result['basis_period']['start']==start
    assert result['basis_period']['end']==end
    assert result['assessment_year']=='2025/26'
    assert exact(result['exact_constraints']['aggregate']['foreign_tax_credit'])==F(2040000,167)


@pytest.mark.parametrize('start,end,verified',[
    ('2024-04-01','2025-03-31',True),('2025-04-02','2026-04-01',True),
    ('2025-01-02','2025-12-31',True),('2024-12-31','2025-12-31',True),
    ('2025-01-01','2025-12-31',False),('2025-01-01','2025-12-31',1)])
def test_special_or_unverified_accounting_period_not_treated_as_ordinary(start,end,verified):
    case,p=fixture();case.update(period_start=start,period_end=end)
    with pytest.raises(ValueError):run(case,p,ongoing_business_unchanged_accounting_year_verified=verified)


def test_two_tier_rate_and_recomputed_tax_use_their_respective_bases():
    case,p=fixture();case['incomes'][1].update(gross_amount='2100000',foreign_tax_paid='600000')
    p['groups'][1]['foreign_credit']['direct_foreign_tax_paid']='600000'
    result=run(case,p,two_tier_eligible=True)
    assert exact(result['exact_annual_rate_basis']['average_credit_rate'])==F(17,200)
    aggregate=result['exact_constraints']['aggregate']
    assert exact(aggregate['foreign_tax_credit'])==F(48300000,367)
    assert exact(aggregate['income_after_foreign_tax_deduction'])<2000000


@pytest.mark.parametrize('income,paid',[('0','0'),('1000','100')])
def test_zero_tax_rate_basis_does_not_divide_by_zero_or_create_refund(income,paid):
    case,p=fixture();case['incomes'][1].update(gross_amount=income,foreign_tax_paid=paid)
    p['groups'][1]['foreign_credit']['direct_foreign_tax_paid']=paid
    result=run(case,p)
    assert exact(result['exact_annual_rate_basis']['average_credit_rate'])==0
    assert exact(result['exact_constraints']['aggregate']['tax_after_credit'])==0


def test_source_hashes_and_input_immutability_with_low_context_precision():
    case,p=fixture();original=deepcopy((case,p));expected=run(case,p)
    with localcontext() as context:
        context.prec=3
        assert run(case,p)==expected
    assert (case,p)==original
    assert len({source['doc_id'] for source in expected['sources']})==len(expected['sources'])
    for source in expected['sources']:
        assert hashlib.sha256(Path(source['file']).read_bytes()).hexdigest()==source['sha256']


@pytest.mark.parametrize('change',['year','unverified','coerced_bool','underlying_loss','underlying_mismatch'])
def test_unverified_or_unsupported_bases_are_rejected(change):
    case,p=fixture();args={}
    if change=='year':case.update(period_start='2026-04-01',period_end='2027-03-31')
    elif change=='unverified':args['ordinary_annual_basis_and_reduction_ordering_verified']=False
    elif change=='coerced_bool':args['two_tier_eligible']=1
    elif change=='underlying_loss':
        case['claimed_deductions']='100001';p['groups'][1]['allowable_expenses']='100001'
        p['groups'][1]['underlying_tax_gross_up']='5000'
        p['groups'][1]['foreign_credit'].update(underlying_tax_paid='5000',underlying_unilateral_eligible_tax='5000')
    else:p['groups'][1]['foreign_credit'].update(underlying_tax_paid='5000',underlying_unilateral_eligible_tax='5000')
    with pytest.raises(ValueError):run(case,p,**args)
