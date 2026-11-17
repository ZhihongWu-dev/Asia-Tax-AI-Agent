"""Allocate verified Korean corporate reliefs under CTA59 and STTCA132(3).

Eligibility, statutory individual caps and carryforward expiry are established
before allocation. Base-changing incentives require a separate restoration and
recalculation process; they cannot be represented as a tax credit here.
"""
from dataclasses import dataclass
from decimal import Decimal, localcontext

from .arithmetic import amount


@dataclass(frozen=True)
class CompanyRelief:
    identifier: str
    value: Decimal | str | int
    category: str
    origin_year: int
    minimum_tax_subject: bool


def allocate_company_reliefs(gross_tax, minimum_reference, reliefs, *, tax_year,
        eligibility_caps_and_expiry_verified, no_base_changing_incentives):
    """Return usage and unused amounts, not an entitlement to future credits.

    Minimum-tax subject reliefs go first; within each group reductions precede
    noncarry credits, carry credits, then CTA58-3 credits. Carried amounts precede
    current-year amounts. The minimum reference limits relief; it never creates
    tax above gross tax when no eligible relief can be withdrawn.
    """
    if type(tax_year) is not int or tax_year != 2026:
        raise ValueError('Only 2026 relief ordering has been reviewed')
    if eligibility_caps_and_expiry_verified is not True or no_base_changing_incentives is not True:
        raise ValueError('Verify eligibility/caps/expiry and handle base-changing incentives separately')
    gross_tax, minimum_reference = amount(gross_tax), amount(minimum_reference)
    if not isinstance(reliefs, (list, tuple)) or len(reliefs) > 1000:
        raise ValueError('Expected at most 1000 verified relief lots')
    order = {'reduction': 0, 'noncarry_credit': 1, 'carry_credit': 2, 'article58_3_credit': 3}
    checked, identifiers = [], set()
    for item in reliefs:
        if not isinstance(item, CompanyRelief):
            raise ValueError('Expected CompanyRelief')
        if not isinstance(item.identifier, str) or not item.identifier.strip() or item.identifier in identifiers:
            raise ValueError('Relief lot identifiers must be nonempty and unique')
        if not isinstance(item.category, str) or item.category not in order:
            raise ValueError('Unknown relief category')
        if type(item.minimum_tax_subject) is not bool or type(item.origin_year) is not int:
            raise ValueError('Explicit minimum-tax classification and origin year required')
        if not 1900 <= item.origin_year <= tax_year:
            raise ValueError('Invalid origin year')
        if item.category in ('reduction', 'noncarry_credit') and item.origin_year != tax_year:
            raise ValueError('Noncarry relief cannot originate in a prior year')
        identifiers.add(item.identifier)
        checked.append((item, amount(item.value)))
    checked.sort(key=lambda pair: (not pair[0].minimum_tax_subject,
        order[pair[0].category], pair[0].origin_year))
    with localcontext() as context:
        context.prec = 40
        remaining, allocations = gross_tax, []
        for item, requested in checked:
            capacity = max(Decimal('0'), remaining - minimum_reference) if item.minimum_tax_subject else remaining
            used = min(requested, capacity)
            remaining -= used
            allocations.append(dict(identifier=item.identifier, requested=requested, used=used,
                unused=requested-used, category=item.category, origin_year=item.origin_year,
                minimum_tax_subject=item.minimum_tax_subject))
        return dict(currency='KRW', tax_year=tax_year, gross_tax=gross_tax,
            minimum_reference=minimum_reference, reliefs=allocations,
            tax_after_reliefs=remaining, total_relief_used=gross_tax-remaining,
            stage='national_reliefs_before_additional_taxes_penalties_and_settlement')
