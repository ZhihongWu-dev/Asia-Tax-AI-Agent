from copy import deepcopy
from decimal import Decimal, localcontext

import pytest

from packages.income_tax.malaysia_foreign_credit import calculate


def receipt(id, gross, country=None, tax='0', method='none', domestic=True):
    return dict(receipt_id=id, gross_income=gross, taxing_country=country,
                eligible_foreign_tax=tax, method=method, malaysia_derived=domestic)


def paper():
    # PR3/2026 example5: common consultancy business, separate domestic rent.
    return dict(total_income='520000', sources=[
        dict(source_id='consultancy', statutory_income='495000', receipts=[
            receipt('local', '500000'),
            receipt('india', '75000', 'in', '7500', 'bilateral')]),
        dict(source_id='rent', statutory_income='25000', receipts=[receipt('rent', '30000')])],
        resident_and_taxable_income_verified=True,
        source_grouping_and_total_income_verified=True,
        treaty_tax_period_fx_and_no_duplicate_claim_verified=True)


def test_official_shared_business_example_5():
    result = calculate(paper(), malaysian_tax_before_credit='124800')
    row = result['source_credits'][0]
    assert round(row['allocated_statutory_income']) == 64565
    assert round(row['malaysian_tax_limit']) == 15496
    assert result['allowed_foreign_tax_credit'] == 7500
    assert result['tax_after_credit'] == 117300


def test_split_receipts_do_not_change_country_source_limit():
    p = paper()
    p['sources'][0]['receipts'][1:] = [
        receipt('in-a', '25000', 'in', '2500', 'bilateral'),
        receipt('in-b', '50000', 'in', '5000', 'bilateral')]
    assert calculate(p, malaysian_tax_before_credit='124800') == calculate(
        paper(), malaysian_tax_before_credit='124800')


def test_unilateral_half_tax_and_statutory_limit():
    p = paper()
    r = p['sources'][0]['receipts'][1]
    r.update(method='unilateral', taxing_country='by', malaysia_derived=False)
    assert calculate(p, malaysian_tax_before_credit='124800')['allowed_foreign_tax_credit'] == 3750
    r['eligible_foreign_tax'] = '100000'
    result = calculate(p, malaysian_tax_before_credit='124800')
    assert result['allowed_foreign_tax_credit'] == result['source_credits'][0]['malaysian_tax_limit']


def test_source_caps_do_not_pool_high_tax_into_other_sources():
    p = paper()
    p['sources'][0]['receipts'][1]['eligible_foreign_tax'] = '100000'
    p['sources'][1]['receipts'][0].update(taxing_country='jp', method='bilateral', eligible_foreign_tax='1')
    result = calculate(p, malaysian_tax_before_credit='124800')
    with localcontext() as ctx:
        ctx.prec = 40
        assert result['allowed_foreign_tax_credit'] == result['source_credits'][0]['malaysian_tax_limit'] + 1


def test_overall_cap_is_explicit_without_inventing_source_allocation():
    p = paper()
    p['total_income'] = '10000'
    p['sources'][0]['receipts'][1]['eligible_foreign_tax'] = '100000'
    result = calculate(p, malaysian_tax_before_credit='2400')
    assert result['allowed_foreign_tax_credit'] == 2400
    assert result['overall_cap_reduction'] > 0
    assert result['tax_after_credit'] == 0
    assert result['unrelieved_foreign_tax'] == 97600


@pytest.mark.parametrize('change', ['duplicate_source', 'duplicate_receipt', 'unilateral_domestic',
    'domestic_tax_country', 'unverified', 'unreconciled_total', 'zero_gross', 'negative_tax'])
def test_invalid_workpapers(change):
    p = deepcopy(paper())
    tax = '124800'
    if change == 'duplicate_source': p['sources'][1]['source_id'] = 'consultancy'
    if change == 'duplicate_receipt': p['sources'][1]['receipts'][0]['receipt_id'] = 'local'
    if change == 'unilateral_domestic': p['sources'][0]['receipts'][1]['method'] = 'unilateral'
    if change == 'domestic_tax_country': p['sources'][0]['receipts'][1]['taxing_country'] = 'my'
    if change == 'unverified': p['resident_and_taxable_income_verified'] = False
    if change == 'unreconciled_total': p['total_income'] = '520001'
    if change == 'zero_gross': p['sources'][1]['receipts'][0]['gross_income'] = '0'
    if change == 'negative_tax': tax = '-1'
    with pytest.raises(ValueError): calculate(p, malaysian_tax_before_credit=tax)


def test_zero_tax_has_no_credit_or_carryforward():
    p = paper()
    p['total_income'] = '0'
    result = calculate(p, malaysian_tax_before_credit='0')
    assert result['allowed_foreign_tax_credit'] == 0
    assert result['unrelieved_foreign_tax'] == 7500


def test_internal_derived_tax_precision_is_preserved():
    result = calculate(paper(), malaysian_tax_before_credit=Decimal('124800.00000024'))
    assert result['tax_after_credit'] == Decimal('117300.00000024')
