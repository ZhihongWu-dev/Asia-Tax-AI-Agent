"""LTA103-19 current foreign-tax deductions from the corporate local base.

No national-credit limit is reused as a local deduction. Legacy local balances
need a separate15-year ledger; this component covers current amounts only.
"""
from decimal import Decimal, localcontext
from .arithmetic import amount


def reconcile_local_base(*, national_taxable_base, expired_foreign_tax_deducted_nationally,
        article57_foreign_tax, article57_2_eligible_fund_credit,
        local_eligibility_addback_and_no_duplicate_amounts_verified,
        no_prior_local_foreign_tax_deductions_verified):
    if local_eligibility_addback_and_no_duplicate_amounts_verified is not True or no_prior_local_foreign_tax_deductions_verified is not True:
        raise ValueError('Verify local eligibility, national expiry addback, distinct amounts and absence of prior local deductions')
    base,addback,direct,fund=map(amount,(national_taxable_base,
        expired_foreign_tax_deducted_nationally,article57_foreign_tax,article57_2_eligible_fund_credit))
    with localcontext() as context:
        context.prec=40
        adjusted=base+addback
        available=direct+fund
        used=min(adjusted,available)
        excess=available-used
        return dict(policy_version='kr-local-foreign-base-component-20261122',currency='KRW',
            national_taxable_base=base,expired_national_foreign_tax_addback=addback,
            local_base_before_foreign_tax_deduction=adjusted,
            article57_foreign_tax=direct,article57_2_eligible_fund_credit=fund,
            current_local_foreign_tax_deduction=used,local_taxable_base=adjusted-used,
            excess_current_local_deduction=excess,local_carryforward_years=15,
            stage='local_taxable_base_before_rate_rounding_municipality_allocation_and_payments',
            sources=[dict(doc_id='kr.local-tax.article103-19.20260701',
                url='https://www.law.go.kr/lsLinkCommonInfo.do?chrClsCd=010202&lsJoLnkSeq=1031177413',
                file='database/raw/kr/kr.local-tax.article103-19.20260701.html',
                sha256='3e84354b8c3e82a9b8d79982a2787092022bf3c8ab6361eed94c115204b25272',
                provisions=['Article103-19(2)-(4)']),
                dict(doc_id='kr.local-decree.article100-10.20261001',
                    url='https://law.go.kr/LSW/lsLinkCommonInfo.do?chrClsCd=010202&lspttninfSeq=164397',
                    file='database/raw/kr/kr.local-decree.article100-10.20261001.html',
                    sha256='a58f8e42f8b93c5bb45c60d3f901bc9784589e29f4b0d7669d5383fc21d32b22',
                    provisions=['Article100-10(1)-(7)'])])
