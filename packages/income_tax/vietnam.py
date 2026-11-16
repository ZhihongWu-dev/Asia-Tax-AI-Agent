"""Vietnam calendar2026 ordinary domestic company calculation.

Combines verified eligibility helpers; API enablement and source indexing are
still pending. Inputs are established tax bases, not raw accounting profit.
Foreign income, excluded Article23(9) income, special rates, revenue methods
and non-calendar periods need separate calculations.
"""
from decimal import localcontext

from .arithmetic import amount, ZERO
from .vietnam_sources import sources_for
from .vietnam_reliefs import (company_small_revenue_exemption,
    company_ordinary_rate, company_2026_2027_reduction)


POLICY_VERSION = 'vn-company-calendar2026-2026-11-17'


def company_tax(taxable_income, *, tax_year, vietnam_established, new_in_current_period,
        previous_period_revenue, previous_active_months, current_period_statutory_revenue,
        exemption_related_enterprise_disqualified, reduced_rate_related_enterprise_disqualified,
        formed_by_split_after_resolution, all_split_entities_revenue,
        other_incentive_reduction, prepaid_tax, ordinary_domestic_income_confirmed,
        statutory_revenue_scope_confirmed, other_incentives_verified):
    """Apply exemption, ordinary rate, other incentives, then Decree398 relief.

    Current revenue determines the30% relief; prior revenue determines ordinary
    rates/exemption except for a new enterprise. The two relationship tests have
    different thresholds and must not be collapsed into one generic SME flag.
    Other incentives are a separately established reduction of tax, not a rate
    preference; preferential-rate income is outside this ordinary calculation.
    Prepayments affect the balance after tax relief, never the relief base.
    """
    if vietnam_established is not True:
        raise ValueError('This calculation requires a Vietnam-established enterprise')
    if ordinary_domestic_income_confirmed is not True or other_incentives_verified is not True:
        raise ValueError('Ordinary domestic scope and other incentive amount must be verified')
    base, current, incentive, prepaid = map(amount, (taxable_income,
        current_period_statutory_revenue, other_incentive_reduction, prepaid_tax))
    if current == ZERO and base > ZERO:
        raise ValueError('Positive ordinary income requires nonzero complete statutory revenue')
    # A disqualifying related enterprise for reduced rates necessarily also
    # fails the smaller exemption revenue threshold.
    if reduced_rate_related_enterprise_disqualified is True and exemption_related_enterprise_disqualified is False:
        raise ValueError('Inconsistent exemption and reduced-rate relationship facts')
    common = dict(tax_year=tax_year, new_in_current_period=new_in_current_period,
        previous_period_revenue=previous_period_revenue, previous_active_months=previous_active_months,
        current_period_actual_revenue=current if new_in_current_period is True else None,
        statutory_revenue_scope_confirmed=statutory_revenue_scope_confirmed)
    exemption = company_small_revenue_exemption(**common, vietnam_established=True,
        related_enterprise_disqualified=exemption_related_enterprise_disqualified,
        income_scope_eligible_confirmed=True)
    rate = company_ordinary_rate(**common,
        related_enterprise_disqualified=reduced_rate_related_enterprise_disqualified,
        income_excluded_from_reduced_rates=False, ordinary_rate_regime_confirmed=True)
    with localcontext() as ctx:
        ctx.prec = 40
        gross = base * rate['rate']
        exempt_tax = gross if exemption['eligible'] else ZERO
        after_exemption = gross - exempt_tax
        if incentive > after_exemption:
            raise ValueError('Other incentive reduction exceeds remaining tax')
        after_incentives = after_exemption - incentive
        relief = company_2026_2027_reduction(after_incentives, tax_year=tax_year,
            current_period_statutory_revenue=current, vietnam_established=True,
            formed_by_split_after_resolution=formed_by_split_after_resolution,
            all_split_entities_revenue=all_split_entities_revenue,
            statutory_revenue_and_period_confirmed=statutory_revenue_scope_confirmed,
            prior_incentives_applied=True)
        liability = relief['tax_after_reduction']
        return dict(policy_version=POLICY_VERSION, tax_year=tax_year, currency='VND',
            taxable_income=base, rate=rate['rate'], rate_eligibility=rate,
            exemption_eligibility=exemption, gross_tax=gross, exempt_tax=exempt_tax,
            other_incentive_reduction=incentive, annual_reduction=relief['reduction'],
            annual_reduction_eligibility=relief, final_tax=liability, prepaid_tax=prepaid,
            balance_due=liability-prepaid, sources=sources_for('company'),
            stage='ordinary_company_before_assessment_rounding')
