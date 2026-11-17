"""2026 Article59-2 child-credit reference with Act21548 transition.

Basic-deduction eligibility (income, support, age exceptions, allocation between
parents) must already be established for each child. Credit utilization remains
subject to the return-level Article60/61 limitation, not a refundable allowance.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .korea_employment import SOURCE, _year


@dataclass(frozen=True)
class ChildCreditFacts:
    identifier: str
    birth_date: date
    relationship: str
    basic_deduction_eligible: bool
    # Verified statutory order of a birth/adoption registered during 2026.
    # None means no current-year birth/adoption credit claim.
    current_year_birth_adoption_order: int | None = None


def child_credit_reference(children, *, tax_year,
        eligibility_allocation_and_event_evidence_verified):
    _year(tax_year)
    if eligibility_allocation_and_event_evidence_verified is not True:
        raise ValueError('Verify basic eligibility, unique claimant allocation and birth/adoption evidence')
    if not isinstance(children, (list, tuple)) or len(children) > 1000:
        raise ValueError('Expected at most 1000 child records')
    seen, rows, qualifying, events = set(), [], 0, 0
    for child in children:
        if not isinstance(child, ChildCreditFacts):
            raise ValueError('Expected ChildCreditFacts')
        if not isinstance(child.identifier, str) or not child.identifier.strip() or child.identifier in seen:
            raise ValueError('Child identifiers must be nonempty and unique')
        seen.add(child.identifier)
        if type(child.birth_date) is not date or child.birth_date > date(2026,12,31):
            raise ValueError('A valid birth date no later than the tax-year end is required')
        if child.relationship not in ('child', 'adopted_child', 'foster_child', 'grandchild'):
            raise ValueError('Unsupported child-credit relationship')
        if type(child.basic_deduction_eligible) is not bool:
            raise ValueError('Basic-deduction eligibility must be explicit')
        age = 2026-child.birth_date.year
        # Act21548 supplementary Article2(3): the 2017 birth cohort cannot
        # use the 9-year transition; the general 13-year rule still applies.
        minimum_age = 13 if child.birth_date.year == 2017 else 9
        eligible = child.basic_deduction_eligible and age >= minimum_age
        qualifying += int(eligible)
        order = child.current_year_birth_adoption_order
        event_credit = 0
        if order is not None:
            if type(order) is not int or not 1 <= order <= 1000:
                raise ValueError('Verified birth/adoption order must be a positive integer')
            if not child.basic_deduction_eligible or child.relationship not in ('child','adopted_child'):
                raise ValueError('Birth/adoption credit requires an eligible child or adopted child')
            if child.relationship == 'child' and child.birth_date.year != 2026:
                raise ValueError('Birth credit requires birth during 2026')
            event_credit = 300000 if order == 1 else 500000 if order == 2 else 700000
        events += event_credit
        rows.append(dict(identifier=child.identifier, birth_date=child.birth_date.isoformat(),
            age_attained_in_tax_year=age, minimum_age=minimum_age,
            birth_2017_transition_excluded=child.birth_date.year == 2017,
            basic_deduction_eligible=child.basic_deduction_eligible,
            regular_credit_eligible=eligible, birth_adoption_credit=Decimal(event_credit)))
    regular = 0 if not qualifying else 250000 if qualifying == 1 else 550000+(qualifying-2)*400000
    return dict(currency='KRW', tax_year=tax_year, qualifying_children=qualifying,
        regular_child_credit=Decimal(regular), birth_adoption_credit=Decimal(events),
        child_credit_reference=Decimal(regular+events), children=rows,
        sources=[dict(SOURCE, provisions=['Article59-2(1),(3)',
            'Act21548 supplementary Article2(1)-(3)'])],
        stage='child_credit_reference_before_return_credit_limitations')
