from copy import deepcopy
from fractions import Fraction
import hashlib
from pathlib import Path
import pytest
from packages.income_tax.korea_foreign_credit import calculate


def fixture():
    return dict(countries=[dict(country='cn',foreign_income_before_corresponding_expenses='500',
        corresponding_expenses='100',allocated_losses_exclusions_and_deductions='0',
        income_reduction_for_tax_relief='0',foreign_tax_paid_or_payable='150',eligible_direct_foreign_tax='150')],
        resident_company_and_direct_tax_scope_verified=True,
        country_income_expenses_and_relief_allocations_verified=True,
        treaty_caps_payment_fx_and_filing_evidence_verified=True,
        no_prior_credits_other_reliefs_or_source_losses_verified=True)


@pytest.mark.parametrize('eligible,credit,expense,carry',[('150',80,20,50),('90',80,10,0),('50',50,0,0),('0',0,0,0)])
def test_expense_excess_is_not_ordinary_carryforward(eligible,credit,expense,carry):
    p=fixture();p['countries'][0]['eligible_direct_foreign_tax']=eligible
    result=calculate(p,national_tax_before_credit='200',national_taxable_base='1000')
    row=result['country_credits'][0]
    assert row['current_foreign_tax_credit']==credit
    assert row['expense_related_excess_not_carried']==expense
    assert row['eligible_current_year_carryforward']==carry
    assert result['national_tax_after_current_credit']==200-credit


def test_country_limits_are_not_pooled():
    p=fixture();second=deepcopy(p['countries'][0]);second.update(country='sg',corresponding_expenses='0',
        foreign_tax_paid_or_payable='10',eligible_direct_foreign_tax='10')
    p['countries'].append(second)
    assert calculate(p,national_tax_before_credit='200',national_taxable_base='1000')['current_foreign_tax_credit']==90


def test_income_reliefs_reduce_country_numerator():
    p=fixture();p['countries'][0].update(income_reduction_for_tax_relief='100',allocated_losses_exclusions_and_deductions='50')
    row=calculate(p,national_tax_before_credit='200',national_taxable_base='1000')['country_credits'][0]
    assert row['credit_limit']==50
    assert row['expense_related_excess_not_carried']==20
    assert row['eligible_current_year_carryforward']==80


def test_fractional_amounts_conserve_foreign_tax_exactly():
    p=fixture();p['countries'][0].update(foreign_income_before_corresponding_expenses='1',corresponding_expenses='.1',
        foreign_tax_paid_or_payable='1',eligible_direct_foreign_tax='1')
    row=calculate(p,national_tax_before_credit='1',national_taxable_base='3')['country_credits'][0]
    def exact(key):
        v=row['exact_amounts'][key];return Fraction(int(v['numerator']),int(v['denominator']))
    assert sum(exact(k) for k in ['current_foreign_tax_credit','expense_related_excess_not_carried','eligible_current_year_carryforward'])==1


@pytest.mark.parametrize('change',['duplicate','domestic','loss','eligible','total','evidence','zero_base'])
def test_invalid_scope_rejected(change):
    p=fixture();c=p['countries'][0];base='1000'
    if change=='duplicate':p['countries'].append(deepcopy(c))
    elif change=='domestic':c['country']='kr'
    elif change=='loss':c['corresponding_expenses']='501'
    elif change=='eligible':c['eligible_direct_foreign_tax']='151'
    elif change=='total':base='300'
    elif change=='zero_base':base='0'
    else:p['no_prior_credits_other_reliefs_or_source_losses_verified']=False
    with pytest.raises(ValueError):calculate(p,national_tax_before_credit='200',national_taxable_base=base)


def test_archived_authority_hashes():
    root=Path(__file__).resolve().parents[2]
    for source in calculate(fixture(),national_tax_before_credit='200',national_taxable_base='1000')['sources']:
        assert hashlib.sha256((root/source['file']).read_bytes()).hexdigest()==source['sha256']
