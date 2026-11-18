"""Separate salaries assessment: IRO sections12,12A and12B."""
from decimal import Decimal, localcontext
from pydantic import BaseModel, ConfigDict, StrictBool
from packages.contracts.income_tax import Money


class SalaryWorkpaper(BaseModel):
    model_config=ConfigDict(extra='forbid')
    balancing_charge: Money
    employment_expenses: Money
    machinery_allowances: Money
    self_education: Money
    concessionary_deductions: Money
    eligibility_and_salary_loss_verified: StrictBool


def reconcile(case,paper):
    if not paper.eligibility_and_salary_loss_verified:
        raise ValueError('Salaries deductions and section12A loss eligibility must be verified')
    if case.claimed_deductions is None or case.carried_losses is None:
        raise ValueError('Known salaries deductions and prior losses required')
    with localcontext() as context:
        context.prec=40
        total=sum((i.gross_amount for i in case.incomes),Decimal(0))
        deductions=paper.employment_expenses+paper.machinery_allowances+paper.self_education+paper.concessionary_deductions
        if deductions!=case.claimed_deductions:
            raise ValueError('Saved salaries deductions must reconcile to the workpaper')
        assessable=total+paper.balancing_charge
        after_expenses=assessable-paper.employment_expenses-paper.machinery_allowances
        available=max(Decimal(0),after_expenses)
        prior_used=min(available,case.carried_losses)
        net_assessable=max(Decimal(0),available-prior_used-paper.self_education)
        net_total=max(Decimal(0),net_assessable-paper.concessionary_deductions)
        return dict(saved_assessable_income=total,balancing_charge=paper.balancing_charge,
            employment_expenses=paper.employment_expenses,machinery_allowances=paper.machinery_allowances,
            current_section12a_excess=max(Decimal(0),-after_expenses),
            prior_salary_losses_used=prior_used,prior_salary_losses_unused=case.carried_losses-prior_used,
            self_education=paper.self_education,net_assessable_income=net_assessable,
            concessionary_deductions=paper.concessionary_deductions,net_income_before_allowances=net_total,
            scope='Verified separate salaries amounts; limits, source, section12A eligibility and allocation established externally. No joint/personal assessment or automatic carryforward approval.')
