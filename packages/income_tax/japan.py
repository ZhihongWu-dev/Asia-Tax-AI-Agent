"""Japan 2026 resident domestic ordinary national annual-return calculation.

Employment and non-loss-making ordinary business income only. Local inhabitant
and enterprise taxes are separate, as are foreign/special income, carry-forwards,
blue-return relief, specific employment expenses and the high-income minimum tax.
The annual deductions effective 1 December 2026 must not be used for earlier
withholding, early death/departure returns or employer year-end settlement.
"""
from copy import deepcopy
from decimal import Decimal, ROUND_CEILING, ROUND_DOWN, localcontext
import json
from pathlib import Path

from .arithmetic import Band, amount, marginal_tax

_SOURCES = json.loads(Path(__file__).with_name('jp_2026_sources.json').read_text(encoding='utf-8'))
ZERO = Decimal('0')
PERSONAL = tuple(Band(None if cap is None else Decimal(cap), Decimal(rate)) for cap, rate in [
    ('1950000', '.05'), ('3300000', '.10'), ('6950000', '.20'),
    ('9000000', '.23'), ('18000000', '.33'), ('40000000', '.40'), (None, '.45')])


def yen(value):
    value = amount(value)
    if value != value.to_integral_value():
        raise ValueError('Amounts must be whole Japanese yen')
    return value


def salary_income(gross_salary):
    """2026 table amount before income adjustment / specific-expense relief."""
    gross = yen(gross_salary)
    with localcontext() as context:
        context.prec = 40
        if gross < 741000:
            return ZERO
        if gross < 2191000:
            return gross - 740000
        if gross < 2193000:
            return Decimal('1451000')
        if gross < 2196000:
            return Decimal('1453000')
        if gross < 2200000:
            return Decimal('1456000')
        if gross < 6600000:
            table_gross = (gross / 4000).to_integral_value(rounding=ROUND_DOWN) * 4000
            return table_gross * (Decimal('.7') if gross < 3600000 else Decimal('.8')) - (80000 if gross < 3600000 else 440000)
        if gross < 8500000:
            return (gross * Decimal('.9') - 1100000).to_integral_value(rounding=ROUND_DOWN)
        return gross - 1950000


def resident_basic_deduction(total_income):
    """2026 annual resident deduction; input is statutory total net income."""
    total = yen(total_income)
    for upper, deduction in [(4890000,1040000), (6550000,670000), (23500000,620000),
                              (24000000,480000), (24500000,320000), (25000000,160000)]:
        if total <= upper:
            return Decimal(deduction)
    return ZERO


def resident_ordinary_tax(gross_salary, gross_business_income, *, tax_year,
        business_expenses, other_income_deductions, income_tax_credits,
        salary_adjustment_eligible, withheld_tax, estimated_tax,
        annual_domestic_ordinary_scope_confirmed, deductions_and_credits_verified):
    if type(tax_year) is not int or tax_year != 2026:
        raise ValueError('Only the 2026 annual rules have been reviewed')
    if annual_domestic_ordinary_scope_confirmed is not True or deductions_and_credits_verified is not True:
        raise ValueError('Annual scope, deduction eligibility and credit limits must be verified')
    if type(salary_adjustment_eligible) is not bool:
        raise ValueError('Child/special-disability salary adjustment eligibility must be explicit')
    salary, receipts, expenses, deductions, credits, withheld, estimated = map(yen,
        [gross_salary, gross_business_income, business_expenses, other_income_deductions,
         income_tax_credits, withheld_tax, estimated_tax])
    if expenses > receipts:
        raise ValueError('Business losses need a separate loss-offset workflow')
    with localcontext() as context:
        context.prec = 40
        if estimated % 100:
            raise ValueError('Use the statutory estimated-tax notice amount in whole hundreds of yen')
        salary_net = salary_income(salary)
        adjustment = (max(ZERO, min(salary, Decimal('10000000')) - 8500000) * Decimal('.1')).to_integral_value(rounding=ROUND_CEILING) if salary_adjustment_eligible else ZERO
        business_net = receipts - expenses
        total = salary_net - adjustment + business_net
        if total > 330000000:
            raise ValueError('The high-income minimum-tax comparison requires a separate workflow')
        basic = resident_basic_deduction(total)
        taxable = (max(ZERO, total-basic-deductions)/1000).to_integral_value(rounding=ROUND_DOWN)*1000
        income_tax, bands = marginal_tax(taxable, PERSONAL)
        if credits > income_tax:
            raise ValueError('Enter only verified non-refundable credits within the national income-tax limit')
        base_tax = income_tax-credits
        reconstruction = (base_tax*Decimal('.021')).to_integral_value(rounding=ROUND_DOWN)
        national_tax = base_tax+reconstruction
        after_withholding = national_tax-withheld
        declared = (after_withholding/100).to_integral_value(rounding=ROUND_DOWN)*100 if after_withholding > 0 else after_withholding
        return dict(policy_version='jp-resident-ordinary-2026-2026-11-17', currency='JPY', tax_year=2026,
            tax_scope='national_income_and_reconstruction_tax_only',
            calculation_stage='annual_return_using_deductions_effective_2026_12_01',
            gross_salary=salary, salary_income_before_adjustment=salary_net,
            salary_income_adjustment=adjustment, net_business_income=business_net,
            total_income=total, basic_deduction=basic, other_income_deductions=deductions,
            taxable_income=taxable, gross_tax=income_tax, allowed_tax_credits=credits,
            reconstruction_tax=reconstruction, final_tax=national_tax,
            withheld_tax=withheld, estimated_tax=estimated,
            declared_tax_after_withholding=declared,
            return_rounding_adjustment=declared-after_withholding,
            balance_due=declared-estimated, bands=bands,
            local_tax_calculated=False, sources=deepcopy(_SOURCES['sources']))
