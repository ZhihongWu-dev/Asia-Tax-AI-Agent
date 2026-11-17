"""2026 ordinary salary annual national-tax calculation using standard credit.

This assembles reviewed components. It is not yet a payroll cash settlement:
payment credits, local withholding and return-level rounding are separate.
"""
from decimal import Decimal, localcontext

from .arithmetic import amount, marginal_tax
from .korea import PERSONAL
from .korea_rounding import taxable_base_won
from .korea_employment import employment_deduction, employment_credit_reference, SOURCE, _year
from .korea_personal_deductions import personal_deductions
from .korea_children import child_credit_reference


def standard_salary_annual(gross_salary, people, children, *, tax_year,
        female_taxpayer, has_spouse, household_head, public_pension_paid,
        ordinary_salary_and_standard_credit_verified,
        family_eligibility_and_allocation_verified, pension_eligibility_verified):
    """Ordinary resident salary only, with standard instead of special credits.

Scope verification means no special deductions under Article52, special credits
under Article59-4(6), rent credit, special employment reduction, pension-account
credit, foreign/special income, or other deductions/credits. Public pension is
Article51-3, distinct from pension-account tax credits. Family documents must be
submitted; use a separate Article54 workflow if omitted.
"""
    _year(tax_year)
    if any(flag is not True for flag in (ordinary_salary_and_standard_credit_verified,
            family_eligibility_and_allocation_verified,pension_eligibility_verified)):
        raise ValueError('Verify ordinary salary, standard-credit election, family and pension evidence')
    salary=amount(gross_salary)
    pension=amount(public_pension_paid)
    if salary != salary.to_integral_value() or pension != pension.to_integral_value():
        raise ValueError('Annual salary and paid pension inputs must be established in whole won')
    wage=employment_deduction(salary,tax_year=tax_year,aggregated_ordinary_salary_verified=True)
    family=personal_deductions(wage['employment_income'],people,tax_year=tax_year,
        female_taxpayer=female_taxpayer,has_spouse=has_spouse,household_head=household_head,
        deduction_documents_submitted=True,eligibility_dates_and_unique_claims_verified=True)
    child=child_credit_reference(children,tax_year=tax_year,
        eligibility_allocation_and_event_evidence_verified=True)
    family_map={p.identifier:p for p in people}
    relations={'child':'descendant','grandchild':'descendant','adopted_child':'adopted_child','foster_child':'foster_child'}
    for record in children:
        person=family_map.get(record.identifier)
        if person is None or person.relationship!=relations[record.relationship] or person.basic_eligible!=record.basic_deduction_eligible:
            raise ValueError('Child credits must reconcile to the same family deduction records')
    with localcontext() as context:
        context.prec=40
        remaining=family['income_after_personal_deductions']
        pension_used=min(pension,remaining)
        base=taxable_base_won(remaining-pension_used)
        gross_tax,bands=marginal_tax(base,PERSONAL)
        earned=employment_credit_reference(salary,gross_tax,tax_year=tax_year,
            ordinary_attribution_without_special_reductions_verified=True)
        standard=Decimal(130000) if salary>0 else Decimal(0)
        requested=earned['employment_credit_reference']+child['child_credit_reference']+standard
        used=min(gross_tax,requested)
        annual=gross_tax-used
    return dict(policy_version='kr-salary-standard-national-2026-2026-11-18',currency='KRW',
        tax_year=tax_year,tax_scope='ordinary_salary_standard_credit_national_annual_only',
        employment=wage,personal_deductions=family,child_credit=child,
        public_pension_paid=pension,public_pension_deduction=pension_used,
        national_taxable_base=base,gross_tax=gross_tax,bands=bands,
        employment_credit=earned,standard_credit_reference=standard,
        credit_reference_total=requested,credits_used=used,unused_credit_reference=requested-used,
        annual_liability_before_return_rounding=annual,
        sources=[dict(SOURCE,provisions=['Article47','Articles50-51','Article51-3',
            'Article55','Article59','Article59-2','Article59-4(9)(1)','Article60','Article61',
            'Act21548 supplementary Article2'])],
        stage='national_salary_annual_before_return_rounding_payments_and_local_tax')
