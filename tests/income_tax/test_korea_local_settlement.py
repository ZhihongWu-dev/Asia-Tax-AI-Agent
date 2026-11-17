from decimal import Decimal

import pytest

from packages.income_tax.korea_local import LocalFilingAdjustments as A, settle_local_return


def adjustments(**changes):
    values = dict(relief=0, penalty=0, additional_tax=0, other_payments=0,
        rate_adjustment_increase=0, rate_adjustment_decrease=0)
    values.update(changes)
    return A(**values)


def compute(gross=1000, withheld=0, **changes):
    args = dict(filing_ratios={'hq': '.6', 'branch': '.4'},
        adjustments={'hq': adjustments(), 'branch': adjustments()}, head_office='hq',
        initial_return_and_filing_groups_verified=True,
        relief_caps_rate_adjustments_and_payments_verified=True, installment=False)
    args.update(changes)
    return settle_local_return(gross, withheld, **args)


def test_relief_additions_and_other_payments_are_separate_per_authority():
    r = compute(withheld=100, adjustments={'hq': adjustments(relief=100, penalty=21,
        additional_tax=10, other_payments=50), 'branch': adjustments(rate_adjustment_increase=20)})
    assert r['filings']['hq']['settlement']['payable'] == 420
    assert r['filings']['branch']['settlement']['payable'] == 380
    assert r['total_payable'] == 800


def test_excess_withholding_refund_goes_to_headquarters():
    r = compute(withheld=1509)
    assert r['filings']['branch']['withholding_credit'] == 400
    assert r['filings']['branch']['settlement']['refundable'] == 0
    assert r['filings']['hq']['settlement']['refundable'] == 500


def test_cash_rounding_occurs_per_authority_not_combined():
    r = compute(gross=38, filing_ratios={'hq': '.5', 'branch': '.5'})
    assert r['total_payable'] == 20


def test_exact_eight_place_products_survive_until_cash_rounding():
    r = compute(gross='100.000001', filing_ratios={'hq': '.33333333', 'branch': '.66666667'})
    assert r['filings']['hq']['allocated_gross_tax'] == Decimal('33.33333333333333')
    assert r['total_payable'] == 90


@pytest.mark.parametrize('changes', [dict(installment=True),
    dict(initial_return_and_filing_groups_verified=False),
    dict(relief_caps_rate_adjustments_and_payments_verified=False),
    dict(adjustments={'hq': adjustments()}),
    dict(adjustments={'hq': adjustments(relief=601), 'branch': adjustments()}),
    dict(adjustments={'hq': adjustments(rate_adjustment_increase=1, rate_adjustment_decrease=1), 'branch': adjustments()}),
    dict(adjustments={'hq': adjustments(penalty=-1), 'branch': adjustments()})])
def test_invalid_local_return_rejected(changes):
    with pytest.raises(ValueError): compute(**changes)
