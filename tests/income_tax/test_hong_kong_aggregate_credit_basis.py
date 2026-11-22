"""Arithmetic integration tests; these do not establish current HK policy."""
from decimal import localcontext
from fractions import Fraction as F
import pytest
from packages.income_tax.hong_kong_credit_basis import _reconcile_aggregate_cap


def solve(income=100000, foreign=20000, ceiling=F(2160000,173),
          bands=((None,F(165,1000)),), reduction=3000):
    return _reconcile_aggregate_cap(income=F(income),foreign_tax=F(foreign),
        source_ceiling=F(ceiling),bands=bands,reduction=F(reduction))


def test_flat_rate_counterexample_reconciles_deduction_and_total_cap_together():
    result=solve()
    assert result['foreign_tax_credit']==F(2040000,167)
    assert result['excess_foreign_tax_deduction']==F(1300000,167)
    assert result['tax_before_credit']==result['foreign_tax_credit']
    assert result['tax_after_credit']==0
    # Clamping the former negative final tax alone leaves the wrong deduction.
    assert result['excess_foreign_tax_deduction']!=F(1300000,173)


def test_two_tier_counterexample_selects_lower_band_after_deduction():
    result=solve(2100000,600000,F(8500000,61),
                 ((F(2000000),F(825,10000)),(None,F(165,1000))))
    assert result['foreign_tax_credit']==F(48300000,367)
    assert result['income_after_foreign_tax_deduction']<2000000
    assert result['tax_after_credit']==0


@pytest.mark.parametrize('income,foreign,ceiling,reduction',[
    (100000,1000,1000,3000),(100000,20000,10000,3000),
    (1000,500,100,3000),(100000,0,0,3000),(100000,100000,10000,0),
    (2500000,1000000,300000,0), (2100000,100000,100000,3000),
])
def test_cap_is_feasible_and_maximal_independent_schedule_evaluation(income,foreign,ceiling,reduction):
    bands=((F(2000000),F(825,10000)),(None,F(165,1000)))
    result=solve(income,foreign,ceiling,bands,reduction)
    credit=result['foreign_tax_credit'];base=result['income_after_foreign_tax_deduction']
    def tax(value):
        return max(F(0),min(value,2000000)*F(825,10000)+max(F(0),value-2000000)*F(165,1000)-reduction)
    assert 0<=credit<=ceiling
    assert credit+result['excess_foreign_tax_deduction']==foreign
    assert base+result['excess_foreign_tax_deduction']==income
    assert result['tax_after_credit']==tax(base)-credit>=0
    if credit<ceiling:
        higher=(credit+ceiling)/2
        assert tax(F(income-foreign)+higher)<higher


def test_exact_breakpoint_and_decimal_context_independence():
    bands=((F(2000000),F(825,10000)),(None,F(165,1000)))
    with localcontext() as context:
        context.prec=3
        result=solve(2100000,262000,200000,bands)
    assert result['foreign_tax_credit']==162000
    assert result['income_after_foreign_tax_deduction']==2000000
    assert result['tax_after_credit']==0


@pytest.mark.parametrize('changes',[
    {'income':-1},{'income':True},{'foreign_tax':F(100001)},
    {'source_ceiling':F(20001)},{'reduction':F(-1)},
    {'bands':[]},{'bands':[(F(100),F(1))]},
    {'bands':[(None,F(1))]},{'bands':[(None,F(-1,10))]},
    {'bands':[(None,F(1,10)),(None,F(1,10))]},
    {'bands':[(F(100),F(1,10)),(F(99),F(1,10)),(None,F(1,10))]},
])
def test_rejects_invalid_internal_inputs(changes):
    args=dict(income=F(100000),foreign_tax=F(20000),source_ceiling=F(10000),
              bands=[(None,F(165,1000))],reduction=F(3000))
    args.update(changes)
    with pytest.raises(ValueError):_reconcile_aggregate_cap(**args)
