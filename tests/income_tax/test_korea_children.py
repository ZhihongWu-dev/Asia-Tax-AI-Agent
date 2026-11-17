from datetime import date, datetime

import pytest

from packages.income_tax.korea_children import ChildCreditFacts, child_credit_reference


def child(identifier='one', birth=date(2016,12,31), relation='child', eligible=True, order=None):
    return ChildCreditFacts(identifier,birth,relation,eligible,order)


def run(*children):
    return child_credit_reference(list(children),tax_year=2026,
        eligibility_allocation_and_event_evidence_verified=True)


@pytest.mark.parametrize('birth,expected', [(date(2016,12,31),250000),
    (date(2017,1,1),0),(date(2017,12,31),0),(date(2018,1,1),0)])
def test_transition_has_explicit_2017_cohort_exception(birth,expected):
    result=run(child(birth=birth))
    assert result['regular_child_credit']==expected
    assert result['children'][0]['birth_2017_transition_excluded']==(birth.year==2017)


@pytest.mark.parametrize('number,expected', [(0,0),(1,250000),(2,550000),(3,950000),(4,1350000)])
def test_regular_credit_uses_qualifying_count(number,expected):
    assert run(*(child(str(i)) for i in range(number)))['regular_child_credit']==expected


def test_ineligible_child_does_not_raise_qualifying_count():
    result=run(child(),child('two',eligible=False),child('three',birth=date(2017,1,1)))
    assert result['qualifying_children']==1
    assert result['child_credit_reference']==250000


def test_basic_eligibility_can_include_disabled_adult_without_assuming_upper_age():
    assert run(child(birth=date(1995,1,1)))['regular_child_credit']==250000


@pytest.mark.parametrize('relation', ['child','adopted_child','foster_child','grandchild'])
def test_statutory_relationships_regular_credit(relation):
    assert run(child(relation=relation))['regular_child_credit']==250000


@pytest.mark.parametrize('order,expected', [(1,300000),(2,500000),(3,700000),(4,700000)])
def test_birth_credit_is_independent_of_regular_minimum_age(order,expected):
    result=run(child(birth=date(2026,12,31),order=order))
    assert result['regular_child_credit']==0
    assert result['birth_adoption_credit']==expected


def test_current_year_adoption_can_qualify_for_both_components():
    result=run(child(relation='adopted_child',order=2))
    assert result['child_credit_reference']==750000


@pytest.mark.parametrize('record', [child(order=1),child(order=True),child(order=0),
    child(eligible=1),child(birth=datetime(2016,1,1)),child(birth=date(2027,1,1)),
    child(identifier=' '),child(relation='sibling'),child(relation='grandchild',order=1),
    child(relation='adopted_child',eligible=False,order=1)])
def test_invalid_or_contradictory_records_rejected(record):
    with pytest.raises(ValueError):run(record)


def test_duplicate_and_unverified_claims_rejected():
    with pytest.raises(ValueError):run(child(),child())
    with pytest.raises(ValueError):
        child_credit_reference([],tax_year=2026,eligibility_allocation_and_event_evidence_verified=False)
    with pytest.raises(ValueError):
        child_credit_reference([],tax_year=2027,eligibility_allocation_and_event_evidence_verified=True)
