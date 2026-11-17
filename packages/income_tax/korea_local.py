"""Ordinary corporate local-tax allocation under Decree88 and form44-6(A).

Inputs are statutory year-end employee/area totals aggregated by municipality.
Special facilities, cross-boundary premises and filing-city grouping must be
established before using these ratios. This is not a local tax assessment.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction

from .arithmetic import amount


@dataclass(frozen=True)
class MunicipalityBasis:
    municipality: str
    employees: Decimal | str | int
    area: Decimal | str | int


def allocation_ratios(bases, *, head_office_municipality, statutory_totals_verified):
    """Average employee and floor-area shares, truncate6 decimals, residual to HQ.

    Exact rational arithmetic avoids a repeating fraction rounding up before
    truncation. Zero aggregate criteria need the separate statutory treatment.
    """
    if statutory_totals_verified is not True:
        raise ValueError('Verify statutory year-end municipality totals')
    if not isinstance(bases, (list, tuple)) or not 1 <= len(bases) <= 1000:
        raise ValueError('Expected 1 to 1000 municipality totals')
    rows, seen = [], set()
    for item in bases:
        if not isinstance(item, MunicipalityBasis) or not isinstance(item.municipality, str):
            raise ValueError('Expected municipality basis')
        if not item.municipality.strip() or item.municipality in seen:
            raise ValueError('Municipality identifiers must be nonempty and unique')
        seen.add(item.municipality)
        rows.append((item.municipality, Fraction(amount(item.employees)), Fraction(amount(item.area))))
    if not isinstance(head_office_municipality, str) or head_office_municipality not in seen:
        raise ValueError('Head-office municipality must be present')
    employees, area = sum(r[1] for r in rows), sum(r[2] for r in rows)
    if not employees or not area:
        raise ValueError('Zero total employees or area requires separate allocation treatment')
    units = {}
    for municipality, count, space in rows:
        exact = (count / employees + space / area) / 2
        units[municipality] = (exact.numerator * 1000000) // exact.denominator
    residual = 1000000 - sum(units.values())
    units[head_office_municipality] += residual
    # Construct directly from a decimal string so caller precision cannot alter it.
    decimal_units = lambda n: Decimal(f'{n // 1000000}.{n % 1000000:06d}')
    return dict(ratios={key: decimal_units(value) for key, value in units.items()},
        head_office_residual=decimal_units(residual),
        stage='municipality_ratios_before_city_filing_grouping_and_tax_settlement')


def allocate_withholding(total_withheld, burdens, filing_ratios, *, head_office,
        initial_return_and_filing_groups_verified):
    """Form43 instruction24: allocate special withholding, with excess at HQ.

    Inputs are final verified filing groups, not ungrouped city districts.
    The six-place form44-6 ratios are not automatically assumed to be the
    final form43 ratios. Amended returns with unchanged withholding retain
    original allocation and must not use this initial-return function.
    """
    if initial_return_and_filing_groups_verified is not True:
        raise ValueError('Verify initial-return status and final filing groups/ratios')
    if not isinstance(burdens, dict) or not 1 <= len(burdens) <= 1000:
        raise ValueError('Expected 1 to 1000 filing-group burdens')
    if not isinstance(filing_ratios, dict) or filing_ratios.keys() != burdens.keys():
        raise ValueError('Ratios must cover exactly the filing groups')
    if not isinstance(head_office, str) or head_office not in burdens:
        raise ValueError('Head office must be a filing group')
    if any(not isinstance(key, str) or not key.strip() for key in burdens):
        raise ValueError('Filing-group identifiers must be nonempty strings')
    withheld = amount(total_withheld)
    checked = {key: amount(value) for key, value in burdens.items()}
    ratios = {}
    for key, value in filing_ratios.items():
        if isinstance(value, (float, bool)):
            raise ValueError('Use exact decimal ratios')
        try:
            ratio = Decimal(value)
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError('Invalid filing ratio') from None
        if not ratio.is_finite() or not 0 <= ratio <= 1 or ratio.as_tuple().exponent < -8:
            raise ValueError('Filing ratios must be between zero and one with at most8 decimals')
        ratios[key] = ratio
    with localcontext() as context:
        context.prec = 40
        if sum(ratios.values(), Decimal('0')) != 1:
            raise ValueError('Final filing ratios must sum exactly to one')
        total_burden = sum(checked.values(), Decimal('0'))
        if withheld > total_burden:
            credits = {key: value for key, value in checked.items() if key != head_office}
            credits[head_office] = withheld - sum(credits.values(), Decimal('0'))
            mode = 'branch_burden_then_head_office_remainder'
        else:
            credits = {key: withheld * ratio for key, ratio in ratios.items()}
            mode = 'proportional'
        return dict(currency='KRW', total_withheld=withheld, total_burden=total_burden,
            credits=credits, allocation_mode=mode,
            stage='withholding_allocation_before_cash_rounding')
