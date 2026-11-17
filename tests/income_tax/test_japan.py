from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path

import pytest

from packages.income_tax.japan import resident_ordinary_tax, salary_income, resident_basic_deduction


def compute(**changes):
    args = dict(gross_salary='6000000', gross_business_income='0', tax_year=2026,
        business_expenses='0', other_income_deductions='960000', income_tax_credits='0',
        salary_adjustment_eligible=False, withheld_tax='176100', estimated_tax='0',
        annual_domestic_ordinary_scope_confirmed=True, deductions_and_credits_verified=True)
    args.update(changes)
    return resident_ordinary_tax(**args)


def test_official_2026_salary_refund_example_nta1000():
    result = compute()
    assert result['salary_income_before_adjustment'] == 4360000
    assert result['basic_deduction'] == 1040000
    assert result['taxable_income'] == 2360000
    assert result['gross_tax'] == 138500
    assert result['reconstruction_tax'] == 2908  # 2908.5 is truncated, not rounded up.
    assert result['balance_due'] == -34692  # Refund is not truncated to hundreds.
    assert result['local_tax_calculated'] is False


def test_official_2026_business_example_nta1000():
    result = compute(gross_salary='0', gross_business_income='10000000',
        business_expenses='7000000', other_income_deductions='720000', withheld_tax='0')
    assert result['net_business_income'] == 3000000
    assert result['taxable_income'] == 1240000
    assert result['gross_tax'] == 62000
    assert result['reconstruction_tax'] == 1302
    assert result['final_tax'] == 63302
    assert result['return_rounding_adjustment'] == -2
    assert result['balance_due'] == 63300


def test_all_1103_independent_official_salary_table_intervals():
    fixture = json.loads(Path(__file__).with_name('fixtures').joinpath('jp_salary_2026.json').read_text(encoding='utf-8'))
    root = Path(__file__).resolve().parents[2]
    assert hashlib.sha256((root/'database/raw/jp/jp.nta.salary-table.20261117.pdf').read_bytes()).hexdigest() == fixture['source_sha256']
    assert len(fixture['rows']) == 1103
    for lower, upper, expected, _ in fixture['rows']:
        assert salary_income(lower) == expected, lower
        assert salary_income(upper-1) == expected, upper-1


@pytest.mark.parametrize('gross,expected', [(0,0),(740999,0),(741000,1000),
    (2190999,1450999),(6600000,4840000),(6600001,4840000),
    (8499999,6549999),(8500000,6550000),(10000000,8050000),(30000000,28050000)])
def test_salary_table_ends_and_high_income_rounding(gross,expected):
    assert salary_income(gross) == expected


@pytest.mark.parametrize('income,deduction', [(0,1040000),(4890000,1040000),(4890001,670000),
    (6550000,670000),(6550001,620000),(23500000,620000),(23500001,480000),
    (24000000,480000),(24000001,320000),(24500000,320000),(24500001,160000),
    (25000000,160000),(25000001,0)])
def test_resident_basic_deduction_boundaries(income,deduction):
    assert resident_basic_deduction(income) == deduction


def test_adjustment_rounded_up_before_basic_deduction_income_test():
    result = compute(gross_salary='8500001',salary_adjustment_eligible=True)
    assert result['salary_income_adjustment'] == 1
    assert result['total_income'] == 6550000
    assert result['basic_deduction'] == 670000
    assert compute(gross_salary='8500001')['basic_deduction'] == 620000
    assert compute(gross_salary='11000000',salary_adjustment_eligible=True)['salary_income_adjustment'] == 150000


def test_credits_precede_reconstruction_and_withholding_precedes_positive_rounding():
    result = compute(income_tax_credits='38500',withheld_tax='19',estimated_tax='120000')
    assert result['reconstruction_tax'] == 2100
    assert result['final_tax'] == 102100
    assert result['declared_tax_after_withholding'] == 102000
    assert result['balance_due'] == -18000
    assert 'prepaid_tax' not in result  # Estimated liability may be unpaid.


def test_sub_thousand_base_and_zero_income():
    result = compute(gross_salary='0',gross_business_income='1040999',other_income_deductions='0',withheld_tax='0')
    assert result['taxable_income'] == result['final_tax'] == result['balance_due'] == 0
    assert compute(gross_salary='0')['balance_due'] == -176100


@pytest.mark.parametrize('base,tax', [(1950000,97500),(3300000,232500),(6950000,962500),
    (7000000,974000),(9000000,1434000),(18000000,4404000),(40000000,13204000)])
def test_statutory_national_brackets(base,tax):
    # Pure business net income >25m has no basic deduction. Supplying an
    # independently verified deduction reaches each desired bracket boundary.
    result=compute(gross_salary='0',gross_business_income='50000000',
        other_income_deductions=str(50000000-base),withheld_tax='0')
    assert result['gross_tax'] == tax


@pytest.mark.parametrize('changes', [dict(tax_year=2025),dict(tax_year=2026.0),
    dict(annual_domestic_ordinary_scope_confirmed=False),dict(deductions_and_credits_verified=1),
    dict(salary_adjustment_eligible=None),dict(salary_adjustment_eligible='false'),
    dict(business_expenses='1'),dict(gross_business_income='330000001',gross_salary='0'),
    dict(estimated_tax='1'),dict(income_tax_credits='138501'),dict(gross_salary='1.1'),
    dict(gross_salary=1.0),dict(withheld_tax=True),dict(other_income_deductions='NaN')])
def test_invalid_or_unhandled_scope_is_rejected(changes):
    with pytest.raises(ValueError):
        compute(**changes)


def test_exact_calculation_is_independent_of_callers_decimal_precision():
    with localcontext() as context:
        context.prec=6
        assert compute()['balance_due'] == -34692


def test_registered_sources_match_originals_and_are_detached():
    root = Path(__file__).resolve().parents[2]
    result = compute()
    assert len(result['sources']) == 9
    for source in result['sources']:
        assert hashlib.sha256((root/source['file']).read_bytes()).hexdigest() == source['sha256']
    result['sources'][0]['sha256'] = 'modified'
    assert compute()['sources'][0]['sha256'] != 'modified'
