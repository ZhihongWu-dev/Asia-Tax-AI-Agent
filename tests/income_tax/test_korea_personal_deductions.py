from decimal import Decimal, localcontext

import pytest

from packages.income_tax.korea_personal_deductions import PersonalDeductionPerson as Person, personal_deductions


SELF=Person('taxpayer','self',True,False,False)
CHILD=Person('child','descendant',True,False,False)


def run(people=(SELF,),income=30000000,**changes):
    options=dict(tax_year=2026,female_taxpayer=False,has_spouse=False,household_head=False,
        deduction_documents_submitted=True,eligibility_dates_and_unique_claims_verified=True)
    options.update(changes)
    return personal_deductions(income,people,**options)


def test_single_parent_overrides_female_deduction():
    result=run((SELF,CHILD),female_taxpayer=True,household_head=True)
    assert result['basic_deduction']==3000000
    assert result['single_parent_deduction']==1000000
    assert result['female_deduction']==0
    assert result['personal_deductions']==4000000


def test_senior_and_disability_additions_stack_for_eligible_person():
    elder=Person('parent','ascendant',True,True,True)
    result=run((SELF,elder))
    assert result['personal_deductions']==6000000
    assert run((SELF,Person('parent','ascendant',False,True,True)))['personal_deductions']==1500000


@pytest.mark.parametrize('income,expected', [(30000000,500000),(30000001,0)])
def test_female_threshold_uses_comprehensive_income_not_salary(income,expected):
    assert run(income=income,female_taxpayer=True,has_spouse=True)['female_deduction']==expected


def test_spouse_eligibility_not_required_for_married_female_addition():
    spouse=Person('spouse','spouse',False,False,False)
    result=run((SELF,spouse),female_taxpayer=True,has_spouse=True)
    assert result['basic_deduction']==1500000
    assert result['female_deduction']==500000


def test_unmarried_female_requires_household_head_and_eligible_dependent():
    parent=Person('parent','ascendant',True,False,False)
    assert run((SELF,parent),female_taxpayer=True)['female_deduction']==0
    assert run((SELF,parent),female_taxpayer=True,household_head=True)['female_deduction']==500000
    assert run(female_taxpayer=True,household_head=True)['female_deduction']==0


def test_foster_child_does_not_create_single_parent_descendant_entitlement():
    foster=Person('foster','foster_child',True,False,False)
    assert run((SELF,foster))['single_parent_deduction']==0


def test_missing_documents_restrict_to_self_basic_even_with_senior_disability():
    taxpayer=Person('self','self',True,True,True)
    result=run((taxpayer,CHILD),female_taxpayer=True,household_head=True,deduction_documents_submitted=False)
    assert result['personal_deductions']==1500000
    assert result['people'][1]['eligible'] is False


@pytest.mark.parametrize('income', [0,100,1499999])
def test_deductions_cannot_exceed_income(income):
    assert run(income=income)['personal_deductions']==income
    assert run(income=income)['income_after_personal_deductions']==0


def test_low_precision_context_does_not_corrupt_remaining_income():
    with localcontext() as context:
        context.prec=5
        assert run(income='999999999999999999.123456')['income_after_personal_deductions']==Decimal('999999999998499999.123456')


@pytest.mark.parametrize('people', [(),(CHILD,),(SELF,SELF),(SELF,Person(' taxpayer ','sibling',True,False,False)),
    (Person('self','self',False,False,False),),(SELF,Person('x','invalid',True,False,False)),
    (SELF,Person('spouse','spouse',True,False,False)),(SELF,Person('x','sibling',1,False,False))])
def test_contradictory_or_duplicate_people_rejected(people):
    with pytest.raises(ValueError):run(people)


@pytest.mark.parametrize('changes',[dict(eligibility_dates_and_unique_claims_verified=False),
    dict(female_taxpayer=1),dict(tax_year=2025),dict(income=-1)])
def test_unverified_or_invalid_context_rejected(changes):
    with pytest.raises(ValueError):run(**changes)
