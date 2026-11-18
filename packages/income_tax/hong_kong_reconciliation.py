"""Reconcile established ordinary Hong Kong profits before and after loss relief.

BIR51 notes distinguish current assessable profits/adjusted loss from the
subsequent set-off of brought-forward losses. These are verified tax amounts,
not automatic determinations of source, donations or capital allowances.
"""
from decimal import localcontext
from .arithmetic import ZERO, amount


def reconcile(case, *, additions=ZERO, excluded_income=ZERO):
    """Return a workpaper without relabelling net taxable profits as assessable profits.

    Saved deductions contain established allowable expenses, donations and
    statutory allowances, never accounting depreciation/non-deductible costs
    or the separately saved eligible prior losses. Additions cover taxable
    adjustments not already included in saved receipts. Exclusions must not
    also be included in deductions. Eligibility and statutory limits must be
    established in supporting schedules before calling this function.
    """
    additions, excluded = map(amount, (additions, excluded_income))
    if case.claimed_deductions is None or case.carried_losses is None:
        raise ValueError('Hong Kong profits reconciliation requires known deductions and losses')
    with localcontext() as context:
        context.prec = 40
        receipts = sum((item.gross_amount for item in case.incomes), ZERO)
        total = receipts + additions
        if excluded > total:
            raise ValueError('Excluded income exceeds saved receipts and taxable additions')
        adjusted = total - excluded - case.claimed_deductions
        profits = max(ZERO, adjusted)
        used = min(profits, case.carried_losses)
        return dict(saved_receipts=receipts, taxable_additions=additions,
            excluded_income=excluded, allowed_deductions=case.claimed_deductions,
            assessable_profits_before_losses=profits,
            adjusted_current_loss=max(ZERO, -adjusted),
            eligible_prior_losses=case.carried_losses, prior_losses_used=used,
            prior_losses_unused=case.carried_losses-used,
            net_taxable_profits=profits-used,
            scope='Established ordinary profits amounts only; no determination of source, FSIE, donation limits, capital allowances, loss eligibility or future carryforward entitlement')
