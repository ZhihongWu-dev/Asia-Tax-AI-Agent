"""Annual domestic business income on an established, aggregated taxable base."""
from decimal import Decimal, localcontext

from .arithmetic import Band, ZERO, amount, marginal_tax
from .china import check_year

BANDS = tuple(Band(None if cap is None else Decimal(cap), Decimal(rate))
    for cap, rate in [('30000', '.05'), ('90000', '.10'), ('300000', '.20'),
                      ('500000', '.30'), (None, '.35')])
SOURCES = (
    ('cn.iit.business.schedule', 'https://guangxi.chinatax.gov.cn/zcwj/zxwj/201809/t20180914_254766.html'),
    ('cn.sta.2023-12.business-relief', 'https://fgk.chinatax.gov.cn/zcfgk/c100012/c5213596/content.html'),
    ('cn.sta.2023-12.business-examples', 'https://fgk.chinatax.gov.cn/zcfgk/c100015/c5213612/content.html'),
)


def annual_business_tax(taxable_income, *, tax_year, business_form,
                        allowed_other_tax_reductions, prepaid_tax,
                        annual_aggregation_and_classification_verified,
                        deductions_losses_and_no_double_claim_verified):
    """No automatic personal deductions: the established base already includes them.

    All businesses must be aggregated, with allocation/deductibility established.
    The individual_operator classification requires all included business income
    to qualify for that status. Mixed eligible/ineligible business pools require
    a separate allocation workflow. This is annual arithmetic before form rounding.
    """
    check_year(tax_year)
    if business_form not in ('individual_operator', 'other_business'):
        raise ValueError('Verified individual-operator or other-business classification required')
    if annual_aggregation_and_classification_verified is not True:
        raise ValueError('Annual business aggregation and classification must be verified')
    if deductions_losses_and_no_double_claim_verified is not True:
        raise ValueError('Deduction eligibility, loss use and no duplicate personal deductions must be verified')
    base, other, prepaid = map(amount, (taxable_income, allowed_other_tax_reductions, prepaid_tax))
    with localcontext() as context:
        context.prec = 40
        gross, bands = marginal_tax(base, BANDS)
        if other > gross:
            raise ValueError('Other reductions exceed gross business tax')
        eligible_base = min(base, Decimal('2000000')) if business_form == 'individual_operator' else ZERO
        eligible_tax = marginal_tax(eligible_base, BANDS)[0]
        allocated_other = other * eligible_base / base if base else ZERO
        # Do not fabricate a negative reduction when supplied relief allocations
        # fall outside the reviewed statutory examples.
        if allocated_other > eligible_tax:
            raise ValueError('Other relief allocation exceeds eligible-band tax; establish the applicable allocation separately')
        half_reduction = (eligible_tax - allocated_other) * Decimal('.5')
        liability = gross - other - half_reduction
        if liability < ZERO:
            raise ValueError('Combined relief exceeds gross business tax')
        balance = liability - prepaid
        return dict(policy_version='cn-business-2026-2026-11-18', tax_year=tax_year,
            currency='CNY', business_form=business_form, taxable_income=base,
            bands=bands, gross_tax=gross, allowed_other_tax_reductions=other,
            half_relief_eligible_base=eligible_base, half_relief_eligible_tax=eligible_tax,
            other_relief_allocated_to_eligible_base=allocated_other,
            individual_operator_half_reduction=half_reduction,
            annual_liability=liability, prepaid_tax=prepaid, balance_due=balance,
            payable=max(ZERO, balance), refundable=max(ZERO, -balance),
            stage='annual_aggregated_business_before_assessment_rounding',
            sources=[dict(doc_id=doc_id, url=url) for doc_id, url in SOURCES])
