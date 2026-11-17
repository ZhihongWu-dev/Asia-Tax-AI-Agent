from decimal import Decimal, localcontext

import pytest

from packages.income_tax.korea_local import MunicipalityBasis as B, allocation_ratios, allocate_withholding


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


def withholding(total, burdens=None, ratios=None, **changes):
    args = dict(head_office='hq', initial_return_and_filing_groups_verified=True)
    args.update(changes)
    return allocate_withholding(total, burdens or {'hq': 600, 'branch': 400},
        ratios or {'hq': '.6', 'branch': '.4'}, **args)


def test_withholding_below_or_equal_burden_uses_verified_ratios():
    assert withholding(500)['credits'] == {'hq': 300, 'branch': 200}
    assert withholding(1000)['allocation_mode'] == 'proportional'


def test_excess_withholding_is_refunded_at_head_office_not_all_branches():
    result = withholding(1500)
    assert result['credits'] == {'hq': 1100, 'branch': 400}
    assert result['allocation_mode'] == 'branch_burden_then_head_office_remainder'
    assert sum(result['credits'].values()) == 1500


def test_zero_burden_assigns_all_withholding_to_head_office():
    assert withholding(20, burdens={'hq': 0, 'branch': 0})['credits'] == {'hq': 20, 'branch': 0}


def test_eight_decimal_ratios_and_low_context_preserve_total():
    with localcontext() as context:
        context.prec = 3
        result = withholding('999.999999', ratios={'hq': '.33333333', 'branch': '.66666667'})
    assert sum(result['credits'].values()) == Decimal('999.999999')


@pytest.mark.parametrize('changes', [dict(head_office='missing'),
    dict(initial_return_and_filing_groups_verified=False),
    dict(ratios={'hq': '.5'}), dict(ratios={'hq': '.5', 'branch': '.4'}),
    dict(ratios={'hq': True, 'branch': 0}), dict(ratios={'hq': 'NaN', 'branch': 0}),
    dict(burdens={'hq': '-1', 'branch': 400})])
def test_unverified_or_inconsistent_withholding_allocation_rejected(changes):
    with pytest.raises(ValueError): withholding(100, **changes)
