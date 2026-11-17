from decimal import Decimal, localcontext

import pytest
from pydantic import TypeAdapter

from packages.contracts.income_assessment import Assessment
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.assessment import calculate
from packages.income_tax.india_company import normal_company_tax


def inputs(**changes):
    values=dict(taxable_income_before_rounding='1000000', period_start='2026-04-01',
        period_end='2027-03-31',turnover_2024_25='4000000000',mat_book_profit_before_rounding='1000000',
        regime_and_base_verified=True,ordinary_domestic_scope_confirmed=True,
        turnover_and_mat_adjustments_verified=True)
    values.update(changes)
    return values


@pytest.mark.parametrize('turnover,rate,tax',[('3999999999','.25',260000),
    ('4000000000','.25',260000),('4000000000.01','.30',312000)])
def test_historical_turnover_threshold(turnover,rate,tax):
    result=normal_company_tax(**inputs(turnover_2024_25=turnover))
    assert result['normal_company_rate']==Decimal(rate)
    assert result['final_tax']==tax
    assert result['mat_applies'] is False


def test_mat_14_percent_with_separate_surcharge_bases():
    result=normal_company_tax(**inputs(taxable_income_before_rounding='100000000',
        mat_book_profit_before_rounding='200000000'))
    assert result['normal_tax_including_surcharge_cess']==27820000
    assert result['mat_tax_including_surcharge_cess']==32614400
    assert result['final_tax']==32614400
    assert result['mat_applies'] is True
    assert result['legacy_mat_credit_used']==0
    assert result['new_mat_credit']==0


def test_compare_after_surcharge_not_only_basic_tax():
    result=normal_company_tax(**inputs(taxable_income_before_rounding='5600010',
        mat_book_profit_before_rounding='10000010'))
    assert result['normal_components']['gross_income_tax'] > result['mat_components']['gross_income_tax']
    assert result['mat_applies'] is True
    assert result['annual_tax_before_rounding']==Decimal('1456010.4')
    assert result['final_tax']==1456010


@pytest.mark.parametrize('base,expected',[('10000000',2600000),('10000010',2600010),
    ('100000000',27820000),('100000010',27820010)])
def test_ordinary_surcharge_thresholds(base,expected):
    result=normal_company_tax(**inputs(taxable_income_before_rounding=base,mat_book_profit_before_rounding='0'))
    assert result['final_tax']==expected


def test_zero_regular_income_does_not_remove_mat():
    result=normal_company_tax(**inputs(taxable_income_before_rounding='0',mat_book_profit_before_rounding='20000000'))
    assert result['final_tax']==3115840


def test_equal_computations_keep_normal_tax_without_new_credit():
    result=normal_company_tax(**inputs(taxable_income_before_rounding='5600000',mat_book_profit_before_rounding='10000000'))
    assert result['mat_applies'] is False
    assert result['final_tax']==1456000


@pytest.mark.parametrize('changes',[{'turnover_2024_25':None},{'mat_book_profit_before_rounding':-1},
    {'turnover_and_mat_adjustments_verified':1},{'period_start':'2025-04-01'},
    {'ordinary_domestic_scope_confirmed':False}])
def test_unverified_and_wrong_year_rejected(changes):
    with pytest.raises(ValueError):normal_company_tax(**inputs(**changes))


def test_decimal_context_is_isolated():
    expected=normal_company_tax(**inputs(taxable_income_before_rounding='100000010'))
    with localcontext() as context:
        context.prec=6
        assert normal_company_tax(**inputs(taxable_income_before_rounding='100000010'))==expected


def test_saved_company_normal_and_settlement():
    case=IncomeTaxCase(subject='company',jurisdiction='in',currency='INR',residency='resident',
        period_start='2026-04-01',period_end='2027-03-31',facts_confirmed=True,
        claimed_deductions='100000',carried_losses='0',incomes=[dict(category='business',
            source_jurisdiction='in',gross_amount='1100000',description='Domestic ordinary business')])
    args=inputs()
    for key in ('period_start','period_end'):del args[key]
    basis=TypeAdapter(Assessment).validate_python(dict(policy='in_company_normal_ty2026_27',
        basis_confirmed=True,basis_explanation='Normal domestic regime; historical turnover and adjusted statutory book profit verified.',
        settlement_requested=True,tds_tcs_credit='100000',advance_tax_paid='200000',self_assessment_paid='0',
        total_interest_due='0',total_fee_due='0',settlement_verified=True,**args))
    result=calculate(case,basis)
    assert Decimal(result['final_tax'])==260000
    assert Decimal(result['balance_due'])==-40000
    case.subject='individual'
    with pytest.raises(ValueError,match='subject'):calculate(case,basis)
