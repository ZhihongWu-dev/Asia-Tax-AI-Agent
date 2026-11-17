"""Ordinary corporate local-tax allocation under Decree88 and form44-6(A).

Inputs are statutory year-end employee/area totals aggregated by municipality.
Special facilities, cross-boundary premises and filing-city grouping must be
established before using these ratios. This is not a local tax assessment.
"""
from dataclasses import dataclass
from decimal import Decimal
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
