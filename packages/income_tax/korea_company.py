"""Korean annual national corporate assessment from established ordinary bases.

Local income tax and separately imposed taxes remain separate liabilities.
Base-changing incentives and installments require their respective workflows.
"""
from decimal import Decimal, localcontext

from .arithmetic import amount
from .korea import gross_taxes, company_minimum_reference
from .korea_reliefs import allocate_company_reliefs
from .korea_rounding import final_cash_balance
from .korea_local import LocalFilingAdjustments, settle_local_return
from .korea_reliefs import CompanyRelief


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


def company_tax(national_taxable_base, local_taxable_base, *, national_inputs,
        local_inputs, ordinary_domestic_scope_confirmed):
    """Combine separately established 2026 ordinary national/local assessments.

    Scope confirmation covers ordinary domestic income and absence of separate
    rural-special, land-transfer, retained-income or other special tax liabilities.
    It does not turn missing local allocation evidence into a verified ratio.
    """
    if ordinary_domestic_scope_confirmed is not True:
        raise ValueError('Verify ordinary domestic scope and absence of separate special-tax liabilities')
    national_args, local_args = dict(national_inputs), dict(local_inputs)
    national_args['reliefs'] = [CompanyRelief(**row) for row in national_args['reliefs']]
    local_args['adjustments'] = {key: LocalFilingAdjustments(**row)
        for key, row in local_args['adjustments'].items()}
    national = national_company_settlement(national_taxable_base, tax_year=2026, **national_args)
    gross = gross_taxes(national_taxable_base, local_taxable_base, tax_year=2026,
        subject='company', article60_2_1_1_company=national_args['article60_2_1_1_company'],
        annual_standard_schedule_confirmed=national_args['annual_standard_schedule_confirmed'])
    local = settle_local_return(gross['local_gross_tax'], **local_args)
    sources = national['sources'] + [s for s in gross['sources']
        if s['doc_id'] not in {r['doc_id'] for r in national['sources']}]
    sources.append(dict(doc_id='kr.local-tax.form43.20260701',
        url='https://www.law.go.kr/LSW/flDownload.do?flSeq=164921007',
        file='database/raw/kr/kr.local-tax.form43.20260701.pdf',
        sha256='363ae8f389af98b9d48a5ae0d753cb2eda6beee83b8ff1db9f03d9278a4b3051',
        provisions=['Instructions19-27']))
    with localcontext() as context:
        context.prec = 40
        payable = national['settlement']['payable'] + local['total_payable']
        refundable = national['settlement']['refundable'] + local['total_refundable']
    return dict(policy_version='kr-company-ordinary-2026-2026-11-18', currency='KRW',
        tax_year=2026, tax_scope='ordinary_national_and_local_corporate_income_tax',
        national=national, local=local, local_taxable_base=gross['local_taxable_base'],
        total_payable=payable, total_refundable=refundable, sources=sources,
        stage='separate_authority_balances_before_installments')
