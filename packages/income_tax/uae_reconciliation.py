"""Ordinary UAE CT basis reconciliation and Article37 own-loss limitation."""
from decimal import Decimal, localcontext
from .arithmetic import ZERO, amount


def reconcile(case, *, taxable_income, additions=ZERO, exempt_income=ZERO):
    """Reconcile already verified tax amounts; never infer exemption eligibility.

    Business income includes applicable accounting/tax valuation adjustments.
    Saved deductions include only allowable business deductions, not excluded
    personal expenses or carried losses. Losses are eligible own prior losses,
    after Article39 review; transfers/group relief need another workpaper.
    """
    base, additions, exempt = map(amount,(taxable_income,additions,exempt_income))
    if case.claimed_deductions is None or case.carried_losses is None:
        raise ValueError('UAE reconciliation requires known deductions and losses')
    if case.subject=='individual' and any(item.category not in
        {'business','employment','dividend','interest','capital_gain','rental'} for item in case.incomes):
        raise ValueError('Classify all in-scope UAE personal business receipts as business; other receipts require verified statutory exclusion')
    with localcontext() as context:
        context.prec=40
        total=sum((item.gross_amount for item in case.incomes),ZERO)
        business=sum((item.gross_amount for item in case.incomes
            if case.subject=='company' or item.category=='business'),ZERO)
        if exempt>business+additions:
            raise ValueError('Exempt income exceeds in-scope income plus taxable additions')
        before=business+additions-exempt-case.claimed_deductions
        available=max(ZERO,before)
        limit=available*Decimal('.75')
        used=min(case.carried_losses,limit)
        net=available-used
        if base!=net:
            raise ValueError('UAE taxable income must reconcile to saved business income, adjustments, deductions and the 75% prior-loss limit')
        return dict(total_saved_income=total,excluded_personal_income=total-business,
            in_scope_income=business,taxable_additions=additions,exempt_income=exempt,
            allowed_deductions=case.claimed_deductions,income_before_loss_relief=before,
            current_period_loss=max(ZERO,-before),prior_loss_limit=limit,
            prior_losses_used=used,prior_losses_unused=case.carried_losses-used,
            taxable_income=net,
            scope='Ordinary standalone own-loss relief; verified statutory classification, deductions, exemptions and eligible losses. No group/transferred-loss computation or future carryforward approval.')
