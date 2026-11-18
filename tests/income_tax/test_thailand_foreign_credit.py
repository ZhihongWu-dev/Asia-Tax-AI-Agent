from decimal import Decimal, localcontext

import pytest

from packages.income_tax.thailand_foreign_credit import attribute_remitted_tax
from packages.income_tax.thailand_foreign_credit import country_credit_limits


def calculate(**changes):
    values = dict(total_foreign_income='1000000', foreign_income_tax_paid='200000',
                  remitted_income='400000', tax_year=2026, source_and_fx_verified=True)
    values.update(changes)
    return attribute_remitted_tax(**values)


def test_partial_remittance_does_not_claim_all_paid_tax():
    result = calculate()
    assert result['foreign_tax_attributable_to_remittance'] == 80000
    assert result['remitted_percentage'] == 40
    assert 'allowed_tax_credits' not in result
    assert 'final_tax' not in result


@pytest.mark.parametrize('remitted,expected', [('0', '0'), ('1000000', '200000'), ('250000', '50000')])
def test_zero_full_and_partial_remittance(remitted, expected):
    assert calculate(remitted_income=remitted)['foreign_tax_attributable_to_remittance'] == Decimal(expected)


def test_manual_income_type_example_then_partial_remittance():
    # Manual PDF page18 allocates a 200000 payment: salary120000/royalty80000.
    salary = calculate(total_foreign_income='600000', foreign_income_tax_paid='120000', remitted_income='300000')
    royalty = calculate(total_foreign_income='400000', foreign_income_tax_paid='80000', remitted_income='100000')
    assert salary['foreign_tax_attributable_to_remittance'] == 60000
    assert royalty['foreign_tax_attributable_to_remittance'] == 20000


def test_decimal_context_does_not_round_intermediate_fraction():
    with localcontext() as context:
        context.prec = 3
        result = calculate(total_foreign_income='3', foreign_income_tax_paid='3', remitted_income='1')
    assert result['foreign_tax_attributable_to_remittance'] == 1


@pytest.mark.parametrize('changes', [
    {'total_foreign_income': '0'}, {'remitted_income': '1000000.01'},
    {'foreign_income_tax_paid': '-1'}, {'remitted_income': float('nan')},
    {'total_foreign_income': 'Infinity'}, {'foreign_income_tax_paid': True},
    {'remitted_income': '0.0000001'}, {'tax_year': 2025}, {'tax_year': 2026.0},
    {'source_and_fx_verified': False}, {'source_and_fx_verified': 1},
])
def test_invalid_or_unverified_basis_rejected(changes):
    with pytest.raises(ValueError): calculate(**changes)


def country(code, income, tax):
    return dict(country=code, remitted_assessable_income=income, eligible_attributable_tax=tax)


def limits(rows=None, **changes):
    args = dict(domestic_assessable_income='1000000', thai_tax_before_foreign_credit='318750',
                tax_year=2026, entitlement_and_basis_verified=True)
    args.update(changes)
    return country_credit_limits(rows if rows is not None else [country('vn','750000','225000'),
        country('cn','225000','22500')], **args)


def test_thai_manual_example_uses_formula_not_printed_arithmetic_error():
    result = limits()
    by_country = {r['country']: r for r in result['countries']}
    assert result['total_assessable_income'] == 1975000
    # Thai PDF page26 prints121004.30; its stated formula yields121044.30.
    assert by_country['vn']['credit_limit'].quantize(Decimal('.01')) == Decimal('121044.30')
    assert by_country['cn']['credit_limit'].quantize(Decimal('.01')) == Decimal('36313.29')
    assert by_country['cn']['allowable_foreign_credit'] == 22500
    assert result['allowable_foreign_credit'].quantize(Decimal('.01')) == Decimal('143544.30')


def test_countries_cannot_use_each_others_unused_limit():
    result = limits([country('jp','100','100'), country('sg','100','0')],
                    domestic_assessable_income=0, thai_tax_before_foreign_credit=20)
    assert result['allowable_foreign_credit'] == 10


def test_income_without_credit_entitlement_remains_in_denominator():
    result = limits([country('vn','100','100'), country('cn','300','0')],
                    domestic_assessable_income=100, thai_tax_before_foreign_credit=50)
    assert result['total_assessable_income'] == 500
    assert result['allowable_foreign_credit'] == 10


def test_zero_income_zero_tax():
    assert limits([country('vn',0,0)], domestic_assessable_income=0,
                  thai_tax_before_foreign_credit=0)['allowable_foreign_credit'] == 0


@pytest.mark.parametrize('rows', [[], [country('th',1,1)], [country('vn',1,1),country('vn',1,1)],
    [country('VN',1,1)], [country('vn',0,1)], [country('vn',-1,1)],
    [{'country':'vn','remitted_assessable_income':1}]])
def test_invalid_country_totals_rejected(rows):
    with pytest.raises(ValueError): limits(rows)


@pytest.mark.parametrize('changes', [{'entitlement_and_basis_verified':False},
    {'entitlement_and_basis_verified':1}, {'tax_year':2025}, {'tax_year':2026.0}])
def test_unverified_country_limits_rejected(changes):
    with pytest.raises(ValueError): limits(**changes)
