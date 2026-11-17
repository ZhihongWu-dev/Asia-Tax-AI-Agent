"""Articles50/51 personal deductions from verified Article53 family facts."""
from dataclasses import dataclass
from decimal import Decimal, localcontext

from .arithmetic import amount
from .korea_employment import SOURCE, _year


@dataclass(frozen=True)
class PersonalDeductionPerson:
    identifier: str
    relationship: str
    basic_eligible: bool
    senior_70_at_statutory_date: bool
    statutory_disability: bool


def personal_deductions(comprehensive_income, people, *, tax_year,
        female_taxpayer, has_spouse, household_head,
        deduction_documents_submitted, eligibility_dates_and_unique_claims_verified):
    """Eligibility includes income/support/age tests and the statutory status date.

Do not infer senior eligibility from age reached later in the year after death.
The verified basic-eligible input includes Article50 income thresholds and
Article53 exceptions. Article54(2) document omission allows self basic only;
the separately computed standard tax credit is not a personal deduction here.
"""
    _year(tax_year)
    flags=(female_taxpayer,has_spouse,household_head,deduction_documents_submitted,
           eligibility_dates_and_unique_claims_verified)
    if any(type(flag) is not bool for flag in flags) or not eligibility_dates_and_unique_claims_verified:
        raise ValueError('Verify eligibility, statutory dates and unique claimant allocation')
    income=amount(comprehensive_income)
    if not isinstance(people,(list,tuple)) or not 1 <= len(people) <= 1000:
        raise ValueError('Expected taxpayer and at most 999 family records')
    seen, rows, self_count, spouse_count = set(), [], 0, 0
    allowed={'self','spouse','ascendant','descendant','adopted_child','sibling',
             'welfare_recipient','foster_child','disabled_descendant_spouse'}
    for person in people:
        if not isinstance(person,PersonalDeductionPerson):
            raise ValueError('Expected PersonalDeductionPerson')
        if not isinstance(person.identifier,str) or not person.identifier.strip() or person.identifier.strip() in seen:
            raise ValueError('Person identifiers must be nonempty and unique')
        seen.add(person.identifier.strip())
        if person.relationship not in allowed or any(type(flag) is not bool for flag in
                (person.basic_eligible,person.senior_70_at_statutory_date,person.statutory_disability)):
            raise ValueError('Verified relationship and explicit eligibility flags required')
        self_count += int(person.relationship=='self')
        spouse_count += int(person.relationship=='spouse')
        if person.relationship=='self' and not person.basic_eligible:
            raise ValueError('Resident taxpayer qualifies for the self basic deduction')
        eligible=person.basic_eligible and (deduction_documents_submitted or person.relationship=='self')
        rows.append(dict(identifier=person.identifier,relationship=person.relationship,
            eligible=eligible,basic=Decimal(1500000 if eligible else 0),
            senior=Decimal(1000000 if eligible and deduction_documents_submitted and person.senior_70_at_statutory_date else 0),
            disability=Decimal(2000000 if eligible and deduction_documents_submitted and person.statutory_disability else 0)))
    if self_count!=1 or spouse_count>1 or (spouse_count and not has_spouse):
        raise ValueError('Exactly one taxpayer and consistent spouse facts required')
    eligible_dependent=any(row['eligible'] and row['relationship'] not in ('self','spouse') for row in rows)
    eligible_descendant=any(row['eligible'] and row['relationship'] in ('descendant','adopted_child') for row in rows)
    single_parent=deduction_documents_submitted and not has_spouse and eligible_descendant
    woman=deduction_documents_submitted and female_taxpayer and income<=30000000 and (
        has_spouse or (household_head and eligible_dependent)) and not single_parent
    with localcontext() as context:
        context.prec=40
        basic=sum((row['basic'] for row in rows),Decimal(0))
        senior=sum((row['senior'] for row in rows),Decimal(0))
        disability=sum((row['disability'] for row in rows),Decimal(0))
        woman_amount=Decimal(500000 if woman else 0)
        parent_amount=Decimal(1000000 if single_parent else 0)
        requested=basic+senior+disability+woman_amount+parent_amount
        allowed_total=min(income,requested)
        remaining=income-allowed_total
    return dict(currency='KRW',tax_year=tax_year,comprehensive_income=income,people=rows,
        basic_deduction=basic,senior_deduction=senior,disability_deduction=disability,
        female_deduction=woman_amount,single_parent_deduction=parent_amount,
        personal_deductions_before_income_cap=requested,personal_deductions=allowed_total,
        income_after_personal_deductions=remaining,
        sources=[dict(SOURCE,provisions=['Article50','Article51','Article53','Article54(2)'])],
        stage='personal_deductions_before_pension_special_and_other_deductions')
