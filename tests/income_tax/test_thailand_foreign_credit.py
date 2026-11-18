from decimal import Decimal, localcontext

import pytest

from packages.income_tax.thailand_foreign_credit import attribute_remitted_tax


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
