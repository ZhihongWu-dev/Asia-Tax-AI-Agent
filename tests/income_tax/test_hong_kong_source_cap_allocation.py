from copy import deepcopy
from fractions import Fraction as F
import pytest
from packages.income_tax.hong_kong_credit_basis import _reconcile_source_caps


def source(identifier='a', income=50000, foreign=10000, rate=F(27,200)):
    return dict(source_id=identifier,income=F(income),foreign_tax=F(foreign),rate=rate)


def calculate(sources=None, allocations=None, domestic=0, reduction=3000):
    return _reconcile_source_caps(domestic_income=F(domestic),
        sources=sources if sources is not None else [source(),source('b')],
        bands=[(None,F(165,1000))],reduction=F(reduction),allocations=allocations)


def test_binding_total_cap_reports_ambiguity_without_inventing_allocations():
    result=calculate()
    assert result['aggregate']['foreign_tax_credit']==F(2040000,167)
    assert result['allocation_required'] and not result['allocation_is_unique']
    assert result['source_reconciliation'] is None
    for row in result['source_credit_ranges']:
        assert row['minimum_credit']==F(2040000,167)-F(1080000,173)
        assert row['maximum_credit']==F(1080000,173)


@pytest.mark.parametrize('portion',[F(0),F(1,2),F(1)])
def test_distinct_feasible_allocations_preserve_total_but_reconcile_each_source(portion):
    base=calculate();bounds=base['source_credit_ranges'][0]
    a=bounds['minimum_credit']+portion*(bounds['maximum_credit']-bounds['minimum_credit'])
    allocations={'a':a,'b':base['aggregate']['foreign_tax_credit']-a}
    original=deepcopy(allocations)
    result=calculate(allocations=allocations)
    assert allocations==original
    assert result['aggregate']==base['aggregate']
    assert not result['allocation_required'] and not result['allocation_is_unique']
    rows=result['source_reconciliation']
    for row in rows:
        c=row['foreign_tax_credit'];d=row['excess_foreign_tax_deduction']
        assert c+d==10000
        assert row['source_income_after_foreign_tax_deduction']+d==50000
        assert c<=row['tax_on_reconciled_source']
    assert sum(row['excess_foreign_tax_deduction'] for row in rows)==result['aggregate']['excess_foreign_tax_deduction']
    assert sum(row['source_income_after_foreign_tax_deduction'] for row in rows)==result['aggregate']['income_after_foreign_tax_deduction']


@pytest.mark.parametrize('sources,domestic,reduction',[
    ([source(income=100000,foreign=20000)],0,3000),
    ([source(foreign=100),source('b',foreign=200)],100000,3000),
    ([source(income=100,foreign=20),source('b',income=200,foreign=40)],0,3000),
    ([source(foreign=0),source('b')],0,3000),
])
def test_unique_allocations_are_derived_automatically(sources,domestic,reduction):
    result=calculate(sources,domestic=domestic,reduction=reduction)
    assert result['allocation_is_unique'] and not result['allocation_required']
    assert sum(row['foreign_tax_credit'] for row in result['source_reconciliation'])==result['aggregate']['foreign_tax_credit']


def test_permutation_and_equal_source_split_preserve_aggregate():
    sources=[source(),source('b')];original=deepcopy(sources)
    first=calculate(sources);second=calculate(list(reversed(sources)))
    whole=calculate([source(income=100000,foreign=20000)])
    assert sources==original
    assert first['aggregate']==second['aggregate']==whole['aggregate']
    assert {r['source_id']:r for r in first['source_credit_ranges']}=={r['source_id']:r for r in second['source_credit_ranges']}


@pytest.mark.parametrize('allocations',[
    {},{'a':F(1)}, {'a':F(1),'b':F(1),'c':F(0)},
    {'a':F(0),'b':F(2040000,167)},
    {'a':F(-1),'b':F(2040000,167)+1},
    {'a':F(1),'b':F(1)}, {'a':0,'b':F(2040000,167)},
])
def test_invalid_allocation_cannot_be_hidden_by_correct_aggregate(allocations):
    with pytest.raises(ValueError):calculate(allocations=allocations)


@pytest.mark.parametrize('sources',[
    [],[source(),source(' a ')],[source(' ')],[source('x'*121)],
    [source(income=1,foreign=2)],[source(rate=F(1))],
    [source(rate=F(-1,10))],[source(rate=True)],
    [dict(source(),unexpected=F(1))],
])
def test_invalid_source_constraints_rejected(sources):
    with pytest.raises(ValueError):calculate(sources)
