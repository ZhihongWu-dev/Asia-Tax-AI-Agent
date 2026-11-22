from fractions import Fraction
import pytest
from packages.income_tax.hong_kong_credit_basis import reconcile_excess_tax


def calculate(income='500',foreign='165',rate='.16',verified=True):
    return reconcile_excess_tax(source_income_before_foreign_tax_deduction=income,
        eligible_foreign_tax=foreign,established_credit_rate=rate,
        statutory_rate_and_deduction_eligibility_verified=verified)


def exact(result,key):
    item=result['exact_amounts'][key]
    return Fraction(int(item['numerator']),int(item['denominator']))


def test_official_historical_example_before_display_rounding():
    result=calculate()
    # Official illustration truncates to whole dollars (63,102,398).
    # This component deliberately preserves exact pre-rounding amounts.
    assert exact(result,'foreign_tax_credit')==Fraction(1340,21)
    assert exact(result,'excess_foreign_tax_deduction')==Fraction(2125,21)
    assert exact(result,'source_income_after_foreign_tax_deduction')==Fraction(8375,21)
    assert exact(result,'source_tax_after_credit')==0


@pytest.mark.parametrize('foreign,credit,deduction,tax', [('0',0,0,80),('50',50,0,30),('80',80,0,0),('500',0,500,0)])
def test_below_at_and_above_limit(foreign,credit,deduction,tax):
    result=calculate(foreign=foreign)
    assert result['foreign_tax_credit']==credit
    assert result['excess_foreign_tax_deduction']==deduction
    assert result['source_tax_after_credit']==tax


@pytest.mark.parametrize('rate',['0','.0825','.165','.162345'])
def test_exact_credit_basis_and_tax_conservation(rate):
    result=calculate(income='1000000.123456',foreign='250000.987654',rate=rate)
    c=exact(result,'foreign_tax_credit');d=exact(result,'excess_foreign_tax_deduction')
    base=exact(result,'source_income_after_foreign_tax_deduction')
    assert c+d==Fraction('250000.987654')
    assert base+d==Fraction('1000000.123456')
    assert c<=base*Fraction(rate)
    assert exact(result,'source_tax_after_credit')>=0


@pytest.mark.parametrize('kwargs',[{'rate':'1'},{'foreign':'501'},{'verified':False},{'rate':'-.1'},{'income':True}])
def test_invalid_or_unverified_inputs_rejected(kwargs):
    with pytest.raises(ValueError):calculate(**kwargs)
