"""2026 resident ordinary domestic business PIT; VAT and property rent are separate."""
from decimal import Decimal, localcontext

from .arithmetic import amount, ZERO
from .vietnam_sources import sources_for


REVENUE_RATES = {
    'goods': Decimal('.005'),
    'services_without_materials': Decimal('.02'),
    'asset_rental_or_specified_agency': Decimal('.05'),
    'production_transport_with_materials': Decimal('.015'),
    'digital_content': Decimal('.05'),
    'other_business': Decimal('.01'),
}
EXEMPT_REVENUE = Decimal('1000000000')
REVENUE_METHOD_LIMIT = Decimal('3000000000')
RELIEF_REVENUE_LIMIT = Decimal('10000000000')


def resident_business_tax(*, tax_year, resident, method, activities,
        all_annual_business_revenue, deductible_expenses, prepaid_tax,
        ordinary_domestic_business_verified, revenue_and_expense_evidence_verified,
        method_election_and_continuity_verified, revenue_method_started_within_limit):
    """Activities contain category, revenue and allocated_revenue_deduction.

    Include all locations and platform receipts, including amounts taxed by a
    withholding payer. Classifications/recognition follow Decree 68 Articles 5–6
    and Decree 253's annex. Property rental, foreign business, exemptions and
    special regimes need separate policies; the scope attestation excludes them.
    Election verification includes Decree 68 Article 4(5)(d)'s two-year rule.
    A revenue-method business crossing 3bn switches in the following year, not
    retroactively merely because its final revenue crossed the boundary.
    """
    if type(tax_year) is not int or tax_year != 2026 or resident is not True:
        raise ValueError('Requires a resident individual and tax year 2026')
    if any(value is not True for value in (
            ordinary_domestic_business_verified, revenue_and_expense_evidence_verified,
            method_election_and_continuity_verified)):
        raise ValueError('Business scope, evidence, election and continuity must be verified')
    if method not in ('revenue', 'profit'):
        raise ValueError('Explicit revenue or profit method is required')
    if type(revenue_method_started_within_limit) is not bool:
        raise ValueError('Revenue-method entry status must be explicit')
    if method == 'revenue' and revenue_method_started_within_limit is not True:
        raise ValueError('Revenue-method eligibility at entry must be established')
    if method == 'profit' and revenue_method_started_within_limit:
        raise ValueError('Revenue-method entry claim conflicts with profit method')
    if not isinstance(activities, (list, tuple)) or not 1 <= len(activities) <= 100:
        raise ValueError('Supply between one and 100 reconciled business activities')
    annual = amount(all_annual_business_revenue)
    paid = amount(prepaid_tax)
    if method == 'revenue':
        if deductible_expenses is not None:
            raise ValueError('Revenue method cannot deduct expenses')
        expenses = ZERO
    else:
        expenses = amount(deductible_expenses)
    with localcontext() as ctx:
        ctx.prec = 40
        rows = []
        for item in activities:
            if not isinstance(item, dict) or set(item) != {
                    'category', 'revenue', 'allocated_revenue_deduction'}:
                raise ValueError('Each activity requires category, revenue and deduction only')
            category = item['category']
            if not isinstance(category, str) or category not in REVENUE_RATES:
                raise ValueError('Unverified or unsupported business classification')
            revenue = amount(item['revenue'])
            deduction = amount(item['allocated_revenue_deduction'])
            if deduction > revenue or (method == 'profit' and deduction != ZERO):
                raise ValueError('Deduction exceeds revenue or is inapplicable to profit method')
            rows.append(dict(category=category, revenue=revenue,
                allocated_revenue_deduction=deduction))
        if sum((r['revenue'] for r in rows), ZERO) != annual:
            raise ValueError('Activity revenues must reconcile to all annual business revenue')
        allocated = sum((r['allocated_revenue_deduction'] for r in rows), ZERO)
        if allocated > min(annual, EXEMPT_REVENUE):
            raise ValueError('One annual revenue deduction is shared by all activities')
        exempt = annual <= EXEMPT_REVENUE
        if method == 'revenue':
            for row in rows:
                row['taxable_revenue'] = ZERO if exempt else (
                    row['revenue'] - row['allocated_revenue_deduction'])
                row['rate'] = REVENUE_RATES[row['category']]
                row['tax_before_relief'] = row['taxable_revenue'] * row['rate']
            base = sum((r['taxable_revenue'] for r in rows), ZERO)
            before = sum((r['tax_before_relief'] for r in rows), ZERO)
            rate = None
        else:
            base = ZERO if exempt else max(ZERO, annual - expenses)
            rate = (Decimal('.15') if annual <= REVENUE_METHOD_LIMIT else
                    Decimal('.17') if annual <= Decimal('50000000000') else Decimal('.20'))
            before = base * rate
        reduction_rate = Decimal('.30') if annual <= RELIEF_REVENUE_LIMIT else ZERO
        reduction = before * reduction_rate
        final = before - reduction
        return dict(policy_version='vn-resident-business-2026-2026-11-18',
            currency='VND', tax_year=tax_year, method=method, activities=rows,
            annual_business_revenue=annual, revenue_exempt=exempt,
            deductible_expenses=expenses if method == 'profit' else None,
            allocated_revenue_deduction=allocated,
            unused_revenue_deduction=(min(annual, EXEMPT_REVENUE)-allocated
                if method == 'revenue' else None), taxable_base=base, rate=rate,
            tax_before_relief=before, reduction_rate=reduction_rate,
            annual_reduction=reduction, final_tax=final, prepaid_tax=paid,
            balance_due=final-paid,
            next_year_profit_method_required=(method == 'revenue' and annual > REVENUE_METHOD_LIMIT),
            method_continuity_review_required=(method == 'profit'),
            calculation_stage='before_assessment_rounding',
            scope='resident_ordinary_domestic_business_excluding_property_rent_and_VAT',
            sources=sources_for('business'))
