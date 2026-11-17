"""Korean base and final cash rounding, separate from tax assessment.

National Treasury Management Act47(1)-(2); Local Tax Basic Act59.
Decree109-2 has a separate first-installment remainder rule: this module
does not round individual installments. Call once per collecting authority,
after credits, penalties, adjustments and prior payments have been reconciled.
"""
from decimal import Decimal, ROUND_DOWN, localcontext

from .arithmetic import amount


def taxable_base_won(base):
    """Discard a fractional won in an already established tax base (Art47(2))."""
    return amount(base).to_integral_value(rounding=ROUND_DOWN)


def _cash_result(net):
    """Round an internally computed exact balance, without input re-quantization."""
    if not isinstance(net, Decimal) or not net.is_finite():
        raise ValueError('Expected a finite exact balance')
    with localcontext() as context:
        context.prec = 40
        cash = (net / Decimal('10')).to_integral_value(rounding=ROUND_DOWN) * 10
        return {'currency': 'KRW', 'balance_before_cash_rounding': net,
                'payable': max(Decimal('0'), cash), 'refundable': max(Decimal('0'), -cash),
                'discarded_fraction': net-cash}


def final_cash_balance(liability, prior_payments, *, installment):
    """Net verified amounts, then discard sub-KRW10 cash, including refunds.

    This does not establish liability, tax credits, minimum tax or entitlement
    to refund. National and local amounts must never be netted together.
    """
    if installment is not False:
        raise ValueError('Installment allocation requires the separate statutory remainder rule')
    liability, prior_payments = amount(liability), amount(prior_payments)
    with localcontext() as context:
        context.prec = 40
        net = liability - prior_payments
        return _cash_result(net)
