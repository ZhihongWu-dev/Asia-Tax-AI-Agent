from datetime import date
from decimal import Decimal, localcontext

import pytest

from packages.income_tax.korea_children import ChildCreditFacts
from packages.income_tax.korea_personal_deductions import PersonalDeductionPerson
from packages.income_tax.korea_salary import standard_salary_annual


SELF=PersonalDeductionPerson('self','self',True,False,False)


def run(salary=50000000,people=(SELF,),children=(),**changes):
    options=dict(tax_year=2026,female_taxpayer=False,has_spouse=False,household_head=False,
        public_pension_paid=0,ordinary_salary_and_standard_credit_verified=True,
        family_eligibility_and_allocation_verified=True,pension_eligibility_verified=True)
    options.update(changes)
    return standard_salary_annual(salary,people,children,**options)


def test_salary_to_annual_liability_reconciles_all_components():
    result=run(public_pension_paid=2000000)
    # 50m salary - 12.25m employment deduction - 1.5m self - 2m pension.
    assert result['national_taxable_base']==34250000
    assert result['gross_tax']==3877500
    assert result['employment_credit']['employment_credit_reference']==660000
    assert result['standard_credit_reference']==130000
    assert result['annual_liability_before_return_rounding']==3087500


def test_children_reconcile_to_family_and_reduce_tax_after_deductions():
    people=(SELF,PersonalDeductionPerson('child','descendant',True,False,False))
    children=(ChildCreditFacts('child',date(2016,1,1),'child',True),)
    result=run(people=people,children=children)
    assert result['personal_deductions']['single_parent_deduction']==1000000
    assert result['national_taxable_base']==33750000
    assert result['child_credit']['child_credit_reference']==250000
    assert result['annual_liability_before_return_rounding']==2762500


def test_2017_child_still_gets_basic_deduction_but_not_regular_credit():
    people=(SELF,PersonalDeductionPerson('child','descendant',True,False,False))
    children=(ChildCreditFacts('child',date(2017,1,1),'child',True),)
    result=run(people=people,children=children)
    assert result['personal_deductions']['basic_deduction']==3000000
    assert result['child_credit']['child_credit_reference']==0


def test_nonrefundable_credits_cannot_create_negative_annual_tax():
    result=run(salary=5000000)
    assert result['gross_tax']==0
    assert result['annual_liability_before_return_rounding']==0
    assert result['credits_used']==0
    assert result['unused_credit_reference']==130000


def test_pension_deduction_limited_after_personal_deductions():
    result=run(salary=10000000,public_pension_paid=4000000)
    assert result['public_pension_deduction']==3000000
    assert result['national_taxable_base']==0


def test_child_record_cannot_claim_credit_outside_saved_family():
    with pytest.raises(ValueError,match='reconcile'):
        run(children=(ChildCreditFacts('missing',date(2010,1,1),'child',True),))


def test_child_eligibility_cannot_disagree_between_components():
    with pytest.raises(ValueError,match='reconcile'):
        run(people=(SELF,PersonalDeductionPerson('child','descendant',False,False,False)),
            children=(ChildCreditFacts('child',date(2010,1,1),'child',True),))


def test_precision_context_does_not_change_annual_tax():
    expected=run(salary='50000001')['annual_liability_before_return_rounding']
    with localcontext() as context:
        context.prec=5
        assert run(salary='50000001')['annual_liability_before_return_rounding']==expected


@pytest.mark.parametrize('flag',['ordinary_salary_and_standard_credit_verified',
    'family_eligibility_and_allocation_verified','pension_eligibility_verified'])
def test_no_silent_scope_assumptions(flag):
    with pytest.raises(ValueError):run(**{flag:False})


@pytest.mark.parametrize('changes',[dict(salary='10000000.000001'),dict(public_pension_paid='1.1')])
def test_unestablished_fractional_cash_inputs_rejected(changes):
    with pytest.raises(ValueError,match='whole won'):run(**changes)
