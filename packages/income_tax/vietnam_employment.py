"""Resident calendar-year employment assessment under Law 109/2025/QH15.

Deductible insurance and Article 11 amounts must already be verified against
implementing conditions. This is not a gross payroll or withholding calculator.
API enablement, special exemptions and foreign tax credits remain separate work.
"""
from decimal import Decimal, localcontext

from .arithmetic import Band, ZERO, amount, marginal_tax
from .vietnam_sources import sources_for


SCHEDULE = tuple(Band(None if cap is None else Decimal(cap), Decimal(rate))
    for cap, rate in [('120000000', '.05'), ('360000000', '.10'),
                      ('720000000', '.20'), ('1200000000', '.30'), (None, '.35')])


def resident_employment_tax(chargeable_employment_income, *, tax_year, resident,
        full_calendar_year_confirmed, dependent_months, deductible_insurance,
        article11_deductions, prepaid_tax, income_and_deductions_verified):
    """Use chargeable pay after exemptions, before personal deductions.

Each dependent appears once with verified eligible months (0..12), including
confirmation that another taxpayer does not claim the same dependent-month.
No automatic 30% business-income relief applies to employment income.
"""
    if type(tax_year) is not int or tax_year != 2026:
        raise ValueError('Only tax year 2026 has been reviewed')
    if resident is not True or full_calendar_year_confirmed is not True:
        raise ValueError('Requires resident full calendar-year assessment')
    if income_and_deductions_verified is not True:
        raise ValueError('Chargeable income and deduction eligibility must be verified')
    if not isinstance(dependent_months, (list, tuple)) or any(
            type(months) is not int or not 0 <= months <= 12 for months in dependent_months):
        raise ValueError('Each dependent must have 0..12 verified eligible months')
    income, insurance, other, prepaid = map(amount, (chargeable_employment_income,
        deductible_insurance, article11_deductions, prepaid_tax))
    with localcontext() as ctx:
        ctx.prec = 40
        personal = Decimal('186000000')
        dependents = Decimal('6200000') * sum(dependent_months)
        deductions = personal + dependents + insurance + other
        base = max(ZERO, income - deductions)
        liability, bands = marginal_tax(base, SCHEDULE)
        return dict(policy_version='vn-resident-employment-2026-2026-11-17',
            tax_year=tax_year, currency='VND', chargeable_income=income,
            personal_deduction=personal, dependent_deduction=dependents,
            deductible_insurance=insurance, article11_deductions=other,
            total_deductions=deductions, taxable_income=base, bands=bands,
            final_tax=liability, prepaid_tax=prepaid, balance_due=liability-prepaid,
            calculation_stage='before_assessment_rounding',
            sources=sources_for('employment'),
            legal_basis=('vn.law.pit2026.vi Articles 8-11',
                         'vn.law.pit2026.vi Article 29(2)'))
