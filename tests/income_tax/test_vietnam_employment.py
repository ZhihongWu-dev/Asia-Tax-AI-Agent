from decimal import Decimal

import pytest

from packages.income_tax.vietnam_employment import resident_employment_tax


def compute(**changes):
    facts = dict(chargeable_employment_income='786000000', tax_year=2026,
        resident=True, full_calendar_year_confirmed=True, dependent_months=[],
        deductible_insurance='0', article11_deductions='0', prepaid_tax='0',
        income_and_deductions_verified=True)
    facts.update(changes)
    return resident_employment_tax(**facts)


@pytest.mark.parametrize('base,tax', [(0, 0), (120000000, 6000000),
    (360000000, 30000000), (720000000, 102000000),
    (1200000000, 246000000), (1300000000, 281000000)])
def test_annual_brackets(base, tax):
    result = compute(chargeable_employment_income=base + 186000000)
    assert result['taxable_income'] == base
    assert result['final_tax'] == tax


def test_deductions_and_refund_do_not_trigger_business_relief():
    r = compute(dependent_months=[12, 6], deductible_insurance='24000000',
        article11_deductions='4200000', prepaid_tax='100000000')
    assert r['dependent_deduction'] == 111600000
    assert r['taxable_income'] == 460200000
    assert r['final_tax'] == 50040000
    assert r['balance_due'] == -49960000


def test_deductions_floor_at_zero():
    assert compute(chargeable_employment_income='1', dependent_months=[12])['final_tax'] == 0


def test_fraction_above_boundary():
    assert compute(chargeable_employment_income='306000000.000001')['final_tax'] == Decimal('6000000.0000001')


def test_employment_provenance_excludes_company_reliefs_and_is_isolated():
    sources = compute()['sources']
    assert [s['doc_id'] for s in sources] == ['vn.law.pit2026.vi']
    assert sources[0]['sha256'] == '6b4803e79a068a7ed5727cfe174e337bbb8b1dbb1b1e48f72119b5f5825e9685'
    sources[0]['provisions'].clear()
    assert compute()['sources'][0]['provisions']


@pytest.mark.parametrize('changes', [dict(tax_year=2025), dict(tax_year=True),
    dict(resident=False), dict(full_calendar_year_confirmed=False),
    dict(income_and_deductions_verified=False), dict(dependent_months=[13]),
    dict(dependent_months=[-1]), dict(dependent_months=[True]),
    dict(dependent_months=[1.5]), dict(dependent_months=None),
    dict(deductible_insurance=-1), dict(article11_deductions=0.1),
    dict(prepaid_tax='NaN'), dict(chargeable_employment_income='Infinity')])
def test_invalid_or_unverified_facts_rejected(changes):
    with pytest.raises(ValueError):
        compute(**changes)
