"""Annual direct-credit settlement from reconciled saved Korean company facts."""
from decimal import Decimal, localcontext
from .korea_foreign_reconciliation import reconcile
from .korea_foreign_credit import calculate as calculate_credit
from .korea_foreign_local_basis import reconcile_local_base
from .korea_company import national_company_settlement
from .korea import gross_taxes
from .korea_local import LocalFilingAdjustments, settle_local_return
from .korea_rounding import _cash_result


def assess(case, workpaper, national_inputs, local_inputs, *,
           current_direct_credit_and_local_deduction_eligibility_verified,
           no_prior_foreign_balances_other_reliefs_or_separate_taxes_verified):
    if (current_direct_credit_and_local_deduction_eligibility_verified is not True
            or no_prior_foreign_balances_other_reliefs_or_separate_taxes_verified is not True):
        raise ValueError('Verify current direct-credit/local deduction eligibility and absence of prior balances, competing reliefs and separate taxes')
    # Reuse the established public-input contracts without introducing an
    # import cycle when the assessment policy registry imports this module.
    from packages.contracts.income_assessment import KRNationalInputs, KRLocalInputs
    national_args = KRNationalInputs.model_validate(national_inputs).model_dump()
    local_args = KRLocalInputs.model_validate(local_inputs).model_dump()
    if national_args['reliefs']:
        raise ValueError('Competing national reliefs require joint allocation; never enter the foreign credit again as a manual relief')
    reconciled = reconcile(case, workpaper)
    base = reconciled['national_taxable_base']
    national = national_company_settlement(base, tax_year=2026, **national_args)
    credit = calculate_credit(dict(countries=reconciled['countries'],
        resident_company_and_direct_tax_scope_verified=True,
        country_income_expenses_and_relief_allocations_verified=True,
        treaty_caps_payment_fx_and_filing_evidence_verified=True,
        no_prior_credits_other_reliefs_or_source_losses_verified=True),
        national_tax_before_credit=national['gross_tax'], national_taxable_base=national['taxable_base'])
    with localcontext() as context:
        context.prec = 40
        used = credit['current_foreign_tax_credit']
        national['tax_after_reliefs'] -= used
        national['allowed_foreign_tax_credit'] = used
        national['liability_before_cash_rounding'] -= used
        national['settlement'] = _cash_result(national['liability_before_cash_rounding'] - national['payment_credits'])
        national['policy_version'] = 'kr-national-company-direct-foreign-20261122'
        eligible = sum((c['eligible_direct_foreign_tax'] for c in reconciled['countries']), Decimal(0))
        local_basis = reconcile_local_base(national_taxable_base=national['taxable_base'],
            expired_foreign_tax_deducted_nationally=0, article57_foreign_tax=eligible,
            article57_2_eligible_fund_credit=0,
            local_eligibility_addback_and_no_duplicate_amounts_verified=True,
            no_prior_local_foreign_tax_deductions_verified=True)
        gross = gross_taxes(base, local_basis['local_taxable_base'], tax_year=2026, subject='company',
            article60_2_1_1_company=national_args['article60_2_1_1_company'],
            annual_standard_schedule_confirmed=national_args['annual_standard_schedule_confirmed'])
        local_args['adjustments'] = {key: LocalFilingAdjustments(**row)
            for key, row in local_args['adjustments'].items()}
        local = settle_local_return(gross['local_gross_tax'], **local_args)
        payable = national['settlement']['payable'] + local['total_payable']
        refundable = national['settlement']['refundable'] + local['total_refundable']
    sources = []
    for source in national['sources'] + gross['sources'] + credit['sources'] + local_basis['sources']:
        existing = next((s for s in sources if s['doc_id'] == source['doc_id']), None)
        if existing is None:
            sources.append(dict(source, provisions=list(source.get('provisions', []))))
        else:
            existing['provisions'] = list(dict.fromkeys(existing['provisions'] + source.get('provisions', [])))
    sources.append(dict(doc_id='kr.local-tax.form43.20260701',
        url='https://www.law.go.kr/LSW/flDownload.do?flSeq=164921007',
        file='database/raw/kr/kr.local-tax.form43.20260701.pdf',
        sha256='363ae8f389af98b9d48a5ae0d753cb2eda6beee83b8ff1db9f03d9278a4b3051',
        provisions=['Instructions19-27']))
    return dict(policy_version='kr-company-direct-foreign-2026-20261122', currency='KRW', tax_year=2026,
        tax_scope='current_direct_foreign_credit_national_and_local_corporate_income_tax',
        national=national, local=local, foreign_credit=credit, local_basis=local_basis,
        source_reconciliation=reconciled['source_reconciliation'], local_taxable_base=gross['local_taxable_base'],
        total_payable=payable, total_refundable=refundable, sources=sources,
        stage='separate_authority_balances_before_installments')
