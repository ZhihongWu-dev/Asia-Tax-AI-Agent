"""Vietnam CIT small-revenue exemption eligibility, not a full assessment.

Decree 141/2026 Article 2 (adding Decree 320/2025 Article 4(15)),
image-reviewed original pages 2-3. Non-calendar transition assessments need
Article 4(3) allocation and are not represented by this eligibility helper.
"""
from decimal import Decimal, localcontext

from .arithmetic import amount


LIMIT = Decimal('1000000000')
REDUCTION_LIMIT = Decimal('10000000000')


def _reduction(tax, revenue, eligible, tax_year):
    if type(tax_year) is not int or tax_year not in (2026, 2027):
        raise ValueError('Decree 398 reduction applies to 2026 and 2027 only')
    # The composed calculator can produce eight fractional places from a
    # six-place base times a two-place rate. Preserve that exact intermediate;
    # external strings still use the normal six-place amount validation.
    if isinstance(tax, Decimal) and tax.is_finite() and tax.as_tuple().exponent >= -8:
        if not 0 <= tax <= Decimal('1e18'):
            raise ValueError('Invalid derived tax amount')
    else:
        tax = amount(tax)
    revenue = amount(revenue)
    eligible = eligible and revenue <= REDUCTION_LIMIT
    with localcontext() as ctx:
        ctx.prec = 40
        reduction = tax * Decimal('.30') if eligible else Decimal('0')
        remaining = tax - reduction
    return dict(tax_year=tax_year, currency='VND', eligible=eligible,
                annual_revenue=revenue, threshold=REDUCTION_LIMIT,
                tax_before_reduction=tax, reduction=reduction,
                tax_after_reduction=remaining, stage='before_assessment_rounding')


def company_2026_2027_reduction(tax_after_other_incentives, *, tax_year,
        current_period_statutory_revenue, vietnam_established,
        formed_by_split_after_resolution, all_split_entities_revenue,
        statutory_revenue_and_period_confirmed, prior_incentives_applied):
    """Decree398 Article3: annual CIT relief on tax after other incentives.

    Revenue includes dependent units, sales/services before deductions,
    financial revenue and other income. Where a short first/last period is
    combined, the confirmed inputs must isolate the specified 12-month period.
    A post-resolution split requires aggregate revenue of all resulting entities.
    This does not derive taxable income, other incentives, or payment credits.
    """
    if type(vietnam_established) is not bool or type(formed_by_split_after_resolution) is not bool:
        raise ValueError('Establishment and split facts must be explicit')
    if statutory_revenue_and_period_confirmed is not True or prior_incentives_applied is not True:
        raise ValueError('Statutory period, complete revenue and prior incentives must be confirmed')
    revenue = amount(current_period_statutory_revenue)
    aggregate = None
    if formed_by_split_after_resolution:
        aggregate = amount(all_split_entities_revenue)
        if aggregate < revenue:
            raise ValueError('Split aggregate cannot be less than this enterprise revenue')
    elif all_split_entities_revenue is not None:
        raise ValueError('Split aggregate requires a qualifying split')
    eligible = vietnam_established and (aggregate is None or aggregate <= REDUCTION_LIMIT)
    return {**_reduction(tax_after_other_incentives, revenue, eligible, tax_year),
            'subject': 'company', 'all_split_entities_revenue': aggregate}


def resident_business_2026_2027_reduction(business_income_tax, *, tax_year,
        annual_actual_business_revenue, resident, business_income_only_confirmed,
        statutory_revenue_scope_confirmed):
    """Decree398 Article2: final annual relief on resident business-income tax.

    Includes all business activities under Decree68 Articles4-5 as amended by
    Decree141, irrespective of the tax calculation method. Salary, investment
    and other nonbusiness tax must not enter this base. Provisional estimates
    and adjustment/late-payment interest are separate operations.
    """
    if type(resident) is not bool:
        raise ValueError('Residence must be explicit')
    if business_income_only_confirmed is not True or statutory_revenue_scope_confirmed is not True:
        raise ValueError('Business-only tax and complete statutory revenue must be confirmed')
    return {**_reduction(business_income_tax, annual_actual_business_revenue, resident, tax_year),
            'subject': 'individual_business'}


def company_small_revenue_exemption(*, tax_year, vietnam_established,
        new_in_current_period, previous_period_revenue, previous_active_months,
        current_period_actual_revenue, related_enterprise_disqualified,
        statutory_revenue_scope_confirmed, income_scope_eligible_confirmed):
    """Determine calendar-2026 eligibility from confirmed statutory revenue.

    Prior-period revenue includes sales/services before revenue deductions,
    financial revenue and other income. Active months include a partial month
    of establishment/reorganization as a whole month under Article 2(b).
    The relationship flag means a subsidiary/linked enterprise has a related
    enterprise that does not satisfy the exemption conditions. It must be
    explicitly established; missing facts must not be treated as False.
    For a newly established enterprise, actual year-end revenue is required;
    a provisional estimate alone does not establish final exemption.
    """
    if type(tax_year) is not int or tax_year != 2026:
        raise ValueError('Vietnam exemption eligibility is verified for calendar 2026 only')
    flags = (vietnam_established, new_in_current_period, related_enterprise_disqualified)
    if any(type(flag) is not bool for flag in flags):
        raise ValueError('Establishment and relationship facts must be explicit')
    if statutory_revenue_scope_confirmed is not True:
        raise ValueError('Statutory revenue scope must be confirmed')
    if income_scope_eligible_confirmed is not True:
        raise ValueError('Income must be verified outside Article 23(9) exclusions')
    if new_in_current_period:
        if previous_period_revenue is not None or previous_active_months is not None:
            raise ValueError('New enterprise cannot have a previous operating period')
        revenue = amount(current_period_actual_revenue)
        months = 12
        basis = 'current_period_actual_revenue'
    else:
        if current_period_actual_revenue is not None:
            raise ValueError('Existing enterprise eligibility uses the previous tax period')
        if type(previous_active_months) is not int or not 1 <= previous_active_months <= 12:
            raise ValueError('Previous active months must be between 1 and 12')
        revenue = amount(previous_period_revenue)
        months = previous_active_months
        basis = 'previous_period_annualized_revenue'
    with localcontext() as ctx:
        ctx.prec = 40
        # Compare cross-products exactly; do not round a recurring annualized
        # quotient down to the exemption boundary.
        below_limit = revenue * 12 <= LIMIT * months
    eligible = vietnam_established and not related_enterprise_disqualified and below_limit
    return dict(eligible=eligible, tax_year=tax_year, currency='VND',
                revenue_basis=basis, revenue=revenue, active_months=months,
                threshold=LIMIT, within_revenue_threshold=below_limit,
                vietnam_established=vietnam_established,
                related_enterprise_disqualified=related_enterprise_disqualified)


def company_ordinary_rate(*, tax_year, new_in_current_period,
        previous_period_revenue, previous_active_months, current_period_actual_revenue,
        related_enterprise_disqualified, income_excluded_from_reduced_rates,
        statutory_revenue_scope_confirmed, ordinary_rate_regime_confirmed):
    """Decree320 Article11 ordinary income rate, before exemptions/reductions.

    The 15/17 percent relationship test is distinct from the VND1bn exemption
    relationship test. Article23(9) excluded income gets the ordinary20 percent
    rate only where the caller confirms no oil/gas, resources, preferential,
    revenue-method or other special rate regime applies.
    """
    if type(tax_year) is not int or tax_year != 2026:
        raise ValueError('Ordinary rate verified for calendar 2026 only')
    if any(type(v) is not bool for v in (new_in_current_period,
            related_enterprise_disqualified, income_excluded_from_reduced_rates)):
        raise ValueError('Rate eligibility facts must be explicit')
    if statutory_revenue_scope_confirmed is not True or ordinary_rate_regime_confirmed is not True:
        raise ValueError('Statutory revenue and ordinary rate regime must be confirmed')
    if new_in_current_period:
        if previous_period_revenue is not None or previous_active_months is not None:
            raise ValueError('New enterprise cannot have a previous operating period')
        revenue, months = amount(current_period_actual_revenue), 12
    else:
        if current_period_actual_revenue is not None:
            raise ValueError('Existing enterprise uses previous-period revenue')
        if type(previous_active_months) is not int or not 1 <= previous_active_months <= 12:
            raise ValueError('Previous active months must be between 1 and 12')
        revenue, months = amount(previous_period_revenue), previous_active_months
    rate = Decimal('.20')
    with localcontext() as ctx:
        ctx.prec = 40
        if not related_enterprise_disqualified and not income_excluded_from_reduced_rates:
            if revenue * 12 <= Decimal('3000000000') * months:
                rate = Decimal('.15')
            elif revenue * 12 <= Decimal('50000000000') * months:
                rate = Decimal('.17')
    return dict(tax_year=tax_year, rate=rate, revenue=revenue, active_months=months,
                related_enterprise_disqualified=related_enterprise_disqualified,
                income_excluded_from_reduced_rates=income_excluded_from_reduced_rates)
