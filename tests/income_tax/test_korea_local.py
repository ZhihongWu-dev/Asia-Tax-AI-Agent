from decimal import Decimal, localcontext

import pytest

from packages.income_tax.korea_local import MunicipalityBasis as B, allocation_ratios


def compute(rows, head='hq', **kwargs):
    return allocation_ratios(rows, head_office_municipality=head,
        statutory_totals_verified=kwargs.get('verified', True))


def test_employee_and_area_shares_are_averaged():
    result = compute([B('hq', 3, 100), B('branch', 1, 300)])
    assert result['ratios'] == {'hq': Decimal('.5'), 'branch': Decimal('.5')}


def test_six_place_truncation_residual_goes_only_to_head_office():
    rows = [B('a', 1, 1), B('hq', 1, 1), B('b', 1, 1)]
    result = compute(rows)
    assert result['ratios'] == dict(a=Decimal('.333333'), hq=Decimal('.333334'), b=Decimal('.333333'))
    assert result['head_office_residual'] == Decimal('.000001')
    assert sum(result['ratios'].values()) == 1
    assert compute(list(reversed(rows)))['ratios'] == result['ratios']


def test_decimal_counts_and_low_precision_do_not_change_statutory_truncation():
    with localcontext() as context:
        context.prec = 3
        result = compute([B('hq', '.1', '.2'), B('a', '.2', '.1')])
    assert result['ratios'] == dict(hq=Decimal('.5'), a=Decimal('.5'))


def test_single_municipality_receives_all():
    assert compute([B('hq', 10, 20)])['ratios'] == {'hq': 1}


@pytest.mark.parametrize('rows', [[], [B('hq', 0, 10)], [B('hq', 10, 0)],
    [B('hq', 1, 2), B('hq', 2, 3)], [B('hq', True, 1)], [B('hq', 1, '-1')],
    [B('hq', 'NaN', 1)], [B('', 1, 1)], [{}]])
def test_invalid_and_unresolved_cases_rejected(rows):
    with pytest.raises(ValueError): compute(rows)


def test_missing_head_office_and_unverified_totals_rejected():
    with pytest.raises(ValueError): compute([B('branch', 1, 1)])
    with pytest.raises(ValueError): compute([B('hq', 1, 1)], verified=False)
