from decimal import Decimal, localcontext

import pytest

from packages.income_tax.korea_employment import employment_deduction, employment_credit_reference


def deduction(gross, **kwargs):
    return employment_deduction(gross, tax_year=2026,
        aggregated_ordinary_salary_verified=True, **kwargs)


def credit(gross, tax):
    return employment_credit_reference(gross, tax, tax_year=2026,
        ordinary_attribution_without_special_reductions_verified=True)


@pytest.mark.parametrize('gross,expected', [(0,0),(2900000,2030000),(5000000,3500000),
    (15000000,7500000),(45000000,12000000),(100000000,14750000),
    (362500000,20000000),(1000000000,20000000)])
def test_deduction_statutory_thresholds_and_cap(gross,expected):
    result=deduction(gross)
    assert result['employment_deduction']==expected
    assert result['employment_income']==gross-expected


def test_multiple_employers_must_be_aggregated_before_deduction():
    assert deduction(10000000)['employment_deduction']==5500000
    assert deduction(5000000)['employment_deduction']*2==7000000


@pytest.mark.parametrize('gross,cap', [('33000000','740000'),('33000001','739999.992'),
    ('40000000','684000'),('43000000','660000'),('70000000','660000'),
    ('70000001','659999.5'),('70320000','500000'),('120000000','500000'),
    ('120000001','499999.5'),('120600000','200000'),('1000000000','200000')])
def test_credit_cap_phaseouts(gross,cap):
    result=credit(gross,'10000000')
    assert result['salary_credit_cap']==Decimal(cap)
    assert result['employment_credit_reference']==Decimal(cap)


@pytest.mark.parametrize('tax,expected', [('0','0'),('1000000','550000'),
    ('1300000','715000'),('1300001','715000.30'),('2000000','740000')])
def test_credit_threshold_before_salary_cap(tax,expected):
    assert credit('30000000',tax)['employment_credit_reference']==Decimal(expected)


def test_components_keep_fractional_results_until_return_rounding():
    with localcontext() as context:
        context.prec=5
        assert deduction('5000001')['employment_deduction']==Decimal('3500000.40')
        assert credit('33000001','2000000')['employment_credit_reference']==Decimal('739999.992')


@pytest.mark.parametrize('value', [True,1.2,'NaN','Infinity','-1','1000000000000000001','0.0000001'])
def test_invalid_money_rejected(value):
    with pytest.raises(ValueError):deduction(value)
    with pytest.raises(ValueError):credit(value,0)
    with pytest.raises(ValueError):credit(10000000,value)


def test_scope_and_year_are_not_implicitly_assumed():
    with pytest.raises(ValueError):
        employment_deduction(100, tax_year=2026, aggregated_ordinary_salary_verified=1)
    with pytest.raises(ValueError):
        employment_credit_reference(100,1,tax_year=2026,
            ordinary_attribution_without_special_reductions_verified=False)
    with pytest.raises(ValueError):
        employment_deduction(100,tax_year=2025,aggregated_ordinary_salary_verified=True)
    with pytest.raises(ValueError):credit(0,1)
