"""Ordinary corporate local-tax allocation under Decree88 and form44-6(A).

Inputs are statutory year-end employee/area totals aggregated by municipality.
Special facilities, cross-boundary premises and filing-city grouping must be
established before using these ratios. This is not a local tax assessment.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction

from .arithmetic import amount
from .korea_rounding import _cash_result


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


def _withholding_credits(withheld, burdens, ratios, head_office):
    if withheld > sum(burdens.values(), Decimal('0')):
        credits = {key: value for key, value in burdens.items() if key != head_office}
        credits[head_office] = withheld-sum(credits.values(), Decimal('0'))
        return credits, 'branch_burden_then_head_office_remainder'
    return {key: withheld*Decimal(ratio) for key, ratio in ratios.items()}, 'proportional'


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
        credits, mode = _withholding_credits(withheld, checked, ratios, head_office)
        return dict(currency='KRW', total_withheld=withheld, total_burden=total_burden,
            credits=credits, allocation_mode=mode,
            stage='withholding_allocation_before_cash_rounding')


@dataclass(frozen=True)
class LocalFilingAdjustments:
    relief: Decimal | str | int
    penalty: Decimal | str | int
    additional_tax: Decimal | str | int
    other_payments: Decimal | str | int
    rate_adjustment_increase: Decimal | str | int
    rate_adjustment_decrease: Decimal | str | int


def settle_local_return(standard_gross_tax, total_withheld, filing_ratios, adjustments,
        *, head_office, initial_return_and_filing_groups_verified,
        relief_caps_rate_adjustments_and_payments_verified, installment):
    """Form43 lines44-51 for ordinary initial filings, one result per authority.

    Standard gross tax is independently established under the local schedule.
    Final form43 ratios and city filing groups are explicitly verified inputs.
    Relief, penalties, recapture/additions, rate adjustments and other payment
    credits are established independently; national reliefs do not flow here.
    Revised assessments, installment distribution and special taxes are separate.
    """
    if relief_caps_rate_adjustments_and_payments_verified is not True or installment is not False:
        raise ValueError('Verify local adjustments and use separate installment treatment')
    if not isinstance(adjustments, dict) or not isinstance(filing_ratios, dict) or adjustments.keys() != filing_ratios.keys():
        raise ValueError('Local adjustments must cover exactly the final filing groups')
    # Validate all ratios/group context before doing any allocation arithmetic.
    allocate_withholding(0, dict.fromkeys(adjustments, 0), filing_ratios,
        head_office=head_office, initial_return_and_filing_groups_verified=initial_return_and_filing_groups_verified)
    gross = amount(standard_gross_tax)
    with localcontext() as context:
        context.prec = 40
        rows, burdens = {}, {}
        for key, item in adjustments.items():
            if not isinstance(item, LocalFilingAdjustments):
                raise ValueError('Expected LocalFilingAdjustments')
            relief, penalty, addition, paid, increase, decrease = map(amount,
                (item.relief, item.penalty, item.additional_tax, item.other_payments,
                 item.rate_adjustment_increase, item.rate_adjustment_decrease))
            allocated = gross * Decimal(filing_ratios[key])
            if relief > allocated or (increase and decrease):
                raise ValueError('Local relief exceeds allocated tax or rate adjustment has conflicting directions')
            burden = allocated-relief+penalty+addition
            rows[key] = dict(allocated_gross_tax=allocated, relief=relief, penalty=penalty,
                additional_tax=addition, total_burden=burden, other_payments=paid,
                rate_adjustment=increase-decrease)
            # Preserve exact products beyond user-input precision for the
            # proportional withholding branch rather than rounding prematurely.
            burdens[key] = burden
        withheld = amount(total_withheld)
        credits, mode = _withholding_credits(withheld, burdens, filing_ratios, head_office)
        for key, row in rows.items():
            row['withholding_credit'] = credits[key]
            row['settlement'] = _cash_result(row['total_burden']-credits[key]-row['other_payments']+row['rate_adjustment'])
        return dict(currency='KRW', standard_gross_tax=gross, total_withheld=withheld,
            filings=rows, withholding_allocation_mode=mode,
            total_payable=sum((r['settlement']['payable'] for r in rows.values()), Decimal('0')),
            total_refundable=sum((r['settlement']['refundable'] for r in rows.values()), Decimal('0')),
            stage='local_initial_return_cash_before_installments')
