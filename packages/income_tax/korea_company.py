"""Korean annual national corporate assessment from established ordinary bases.

Local income tax and separately imposed taxes remain separate liabilities.
Base-changing incentives and installments require their respective workflows.
"""
from decimal import Decimal, localcontext

from .arithmetic import amount
from .korea import gross_taxes, company_minimum_reference
from .korea_reliefs import allocate_company_reliefs
from .korea_rounding import final_cash_balance


def national_company_settlement(taxable_base, *, tax_year, minimum_regime,
        article60_2_1_1_company, reliefs, annual_standard_schedule_confirmed,
        minimum_regime_verified, eligibility_caps_and_expiry_verified,
        no_base_changing_incentives, additions_and_payments_verified,
        penalty_tax, relief_recapture, interim_tax, occasional_assessment_tax,
        withheld_tax, installment):
    """Gross tax -> restricted/exempt reliefs -> additions -> paid taxes -> cash.

    Verified payment credits must exclude their penalties (CTA64). Additions
    are separately established and cannot be reduced by ordinary tax credits.
    This result is national corporate tax only, not a combined Korean tax bill.
    """
    if minimum_regime_verified is not True or additions_and_payments_verified is not True:
        raise ValueError('Minimum-tax classification, additions and payment credits must be verified')
    if no_base_changing_incentives is not True:
        raise ValueError('Base-changing incentives require restoration and recalculation')
    if installment is not False:
        raise ValueError('Installments require separate allocation')
    # This call validates the reviewed annual regime and company classification;
    # local base is deliberately absent from the national-only result below.
    gross = gross_taxes(taxable_base, 0, tax_year=tax_year, subject='company',
        article60_2_1_1_company=article60_2_1_1_company,
        annual_standard_schedule_confirmed=annual_standard_schedule_confirmed)
    base = gross['national_taxable_base']
    minimum = company_minimum_reference(base, tax_year=tax_year, regime=minimum_regime,
        annual_applicability_and_restoration_confirmed=True)
    allocated = allocate_company_reliefs(gross['national_gross_tax'],
        minimum['minimum_reference_tax'], reliefs, tax_year=tax_year,
        eligibility_caps_and_expiry_verified=eligibility_caps_and_expiry_verified,
        no_base_changing_incentives=True)
    penalty, recapture, interim, occasional, withheld = map(amount,
        (penalty_tax, relief_recapture, interim_tax, occasional_assessment_tax, withheld_tax))
    with localcontext() as context:
        context.prec = 40
        liability = allocated['tax_after_reliefs'] + penalty + recapture
        payments = interim + occasional + withheld
        cash = final_cash_balance(liability, payments, installment=False)
    sources = [s for s in gross['sources'] if not s['doc_id'].startswith('kr.local-tax')]
    for source in sources:
        if source['doc_id'].startswith('kr.corporate-tax-act'):
            source['provisions'].extend(['Article59', 'Article64'])
    sources.extend(s for s in minimum['sources'] if s['doc_id'] not in {s['doc_id'] for s in sources})
    return dict(policy_version='kr-national-company-2026-2026-11-18', tax_year=tax_year,
        currency='KRW', tax_scope='national_corporate_income_tax_only',
        taxable_base=base, gross_tax=gross['national_gross_tax'],
        gross_bands=gross['national_bands'], minimum_regime=minimum_regime,
        minimum_reference_tax=minimum['minimum_reference_tax'],
        relief_allocation=allocated['reliefs'], tax_after_reliefs=allocated['tax_after_reliefs'],
        penalty_tax=penalty, relief_recapture=recapture,
        liability_before_cash_rounding=liability, interim_tax=interim,
        occasional_assessment_tax=occasional, withheld_tax=withheld,
        payment_credits=payments, settlement=cash, sources=sources,
        stage='national_settlement_before_installment_allocation')
