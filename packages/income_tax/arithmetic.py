"""Exact marginal-band arithmetic. Country adapters supply legally reviewed inputs."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext

ZERO = Decimal("0")


def amount(value, *, max_decimal_places=6, max_value=Decimal("1e18")):
    if isinstance(value, (float, bool)):
        raise ValueError("Use a decimal string, integer or Decimal, never a binary float")
    try:
        result = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Invalid decimal amount") from None
    if not result.is_finite() or result < 0 or result > max_value:
        raise ValueError(f"Amount must be finite and between zero and {max_value}")
    if result.as_tuple().exponent < -max_decimal_places:
        raise ValueError("Amount precision exceeds six decimal places" if max_decimal_places == 6 else "Derived amount exceeds internal precision limit")
    return result


def computed_amount(value):
    """Validated internal aggregates/products; never use for public money inputs.

    Up to200 saved income rows and statutory factors fit within22 integer and18
    fractional places in the fixed40-digit calculation context.
    """
    return amount(value, max_decimal_places=18, max_value=Decimal('1e22'))


@dataclass(frozen=True)
class Band:
    upper: Decimal | None
    rate: Decimal


@dataclass(frozen=True)
class BandResult:
    lower: Decimal
    upper: Decimal | None
    taxable: Decimal
    rate: Decimal
    tax: Decimal


def marginal_tax(base, bands, *, computed_base=False):
    base = computed_amount(base) if computed_base else amount(base)
    bands = tuple(bands)
    if not bands or bands[-1].upper is not None:
        raise ValueError("Schedule must end in an unbounded band")
    lower, output = ZERO, []
    with localcontext() as context:
        context.prec = 40
        for index, band in enumerate(bands):
            rate = amount(band.rate)
            if rate > 1:
                raise ValueError("Rate must be a fraction between zero and one")
            upper = None if band.upper is None else amount(band.upper)
            if upper is None and index != len(bands) - 1:
                raise ValueError("Only the final band may be unbounded")
            if upper is not None and upper <= lower:
                raise ValueError("Band thresholds must strictly increase")
            taxable = max(ZERO, (base if upper is None else min(base, upper)) - lower)
            output.append(BandResult(lower, upper, taxable, rate, taxable * rate))
            if upper is not None:
                lower = upper
        return sum((row.tax for row in output), ZERO), tuple(output)
