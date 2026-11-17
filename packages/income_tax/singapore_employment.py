"""YA2026 resident ordinary employment calculation on verified deductions.

CPF and other personal relief entitlements must be established separately.
This computes their overall cap, earned-income relief and PTR utilisation;
it does not infer CPF eligibility, family allocation or tax-clearance treatment.
"""
from datetime import date
from decimal import Decimal, localcontext

from .arithmetic import ZERO, amount
from .singapore import check_year, resident_individual_tax

RELIEF_ROOT = 'https://www.iras.gov.sg/taxes/individual-income-tax/basics-of-individual-income-tax/tax-reliefs-rebates-and-deductions/tax-reliefs'
SOURCES = [RELIEF_ROOT, RELIEF_ROOT + '/earned-income-relief',
           RELIEF_ROOT + '/parenthood-tax-rebate-(ptr)']


def resident_employment_tax(gross_employment_income, *, assessment_year, birth_date,
                            disability_relief_eligible, allowed_employment_expenses,
                            allowed_donation_deduction, allowed_cpf_relief,
                            allowed_other_personal_reliefs, available_parenthood_rebate,
                            prepaid_tax, eligibility_and_allocations_verified):
    check_year(assessment_year)
    if eligibility_and_allocations_verified is not True:
        raise ValueError('YA2026 deduction eligibility, relief allocation and PTR balance must be verified')
    if type(disability_relief_eligible) is not bool:
        raise ValueError('Disability eligibility must be explicit')
    if type(birth_date) is not date or birth_date > date(2025, 12, 31):
        raise ValueError('Birth date must fall on or before the income year end')
    gross, expenses, donation, cpf, other, ptr, prepaid = map(amount, (
        gross_employment_income, allowed_employment_expenses, allowed_donation_deduction,
        allowed_cpf_relief, allowed_other_personal_reliefs, available_parenthood_rebate, prepaid_tax))
    with localcontext() as ctx:
        ctx.prec = 40
        if expenses > gross:
            raise ValueError('Employment expenses cannot exceed saved taxable employment income')
        net = gross - expenses
        if donation > net:
            raise ValueError('Enter only the donation deduction usable this year; excess carry-forward needs separate review')
        if cpf > gross:
            raise ValueError('Verified employee CPF relief cannot exceed employment income')
        age = 2025 - birth_date.year
        band = 0 if age < 55 else 1 if age < 60 else 2
        ceiling = (4000, 10000, 12000)[band] if disability_relief_eligible else (1000, 6000, 8000)[band]
        earned = min(net, Decimal(ceiling))
        relief_total = earned + cpf + other
        relief_allowed = min(relief_total, Decimal('80000'))
        assessable = net - donation
        chargeable = max(ZERO, assessable - relief_allowed)
        result = resident_individual_tax(chargeable, assessment_year=assessment_year)
        tax = result['gross_tax']
        ptr_used = min(ptr, tax)
        liability = tax - ptr_used
        balance = liability - prepaid
        return {**result, 'policy_version': 'sg-employment-ya2026-2026-11-18',
                'gross_employment_income': gross, 'allowed_employment_expenses': expenses,
                'net_employment_income': net, 'allowed_donation_deduction': donation,
                'assessable_income': assessable, 'age_at_income_year_end': age,
                'earned_income_relief': earned, 'allowed_cpf_relief': cpf,
                'allowed_other_personal_reliefs': other, 'personal_reliefs_before_cap': relief_total,
                'personal_reliefs_allowed': relief_allowed,
                'personal_reliefs_disallowed_by_cap': relief_total - relief_allowed,
                'parenthood_rebate_used': ptr_used, 'parenthood_rebate_carried_forward': ptr - ptr_used,
                'annual_liability': liability, 'prepaid_tax': prepaid, 'balance_due': balance,
                'amount_payable': max(ZERO, balance), 'refund_due': max(ZERO, -balance),
                'sources': [result['source'], *({'url': url} for url in SOURCES)],
                'stage': 'resident_employment_before_assessment_rounding'}
