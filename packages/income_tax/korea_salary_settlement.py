"""National salary year-end cash balance from an established decision amount.

This does not establish the rounded annual decision amount or local tax. Those
must not be inferred from a pre-rounding annual calculation without form review.
"""
from decimal import Decimal, localcontext, ROUND_DOWN

from .arithmetic import amount
from .korea_employment import SOURCE, _year
from .korea_rounding import final_cash_balance

LOCAL_SOURCE=dict(doc_id='kr.local-tax.salary-settlement.20260701',
    url='https://law.go.kr/lsLinkCommonInfo.do?lspttninfSeq=173607',
    sha256='527e8177958baa2eae6a272f60d3c02116e719fb08043b94e2e25b2a8651c053',
    provisions=['Article103-13','Article103-15','Article103-60'])


def local_salary_balance(national_decision_tax, current_employer_withheld,
        former_employer_settled_tax, *, tax_year, employer_special_collection_verified,
        installment):
    """Employer special collection, not a municipality-issued assessment notice.

Article103-15 uses national decision tax, not national cash due after credits
or small-balance noncollection. Article103-60's per-notice KRW2,000 threshold
is not applied to this employer's payroll collection. Local prior payments
come from their own receipts and are not inferred from national payments.
"""
    _year(tax_year)
    if employer_special_collection_verified is not True or installment is not False:
        raise ValueError('Verify employer year-end special collection and receipts; no installments')
    national,current,former=map(amount,(national_decision_tax,current_employer_withheld,former_employer_settled_tax))
    if any(value!=value.to_integral_value() for value in (national,current,former)):
        raise ValueError('Decision and local employer receipt amounts must be whole won')
    with localcontext() as context:
        context.prec=40
        decision=(national*Decimal('.1')).to_integral_value(rounding=ROUND_DOWN)
        paid=current+former
        cash=final_cash_balance(decision,paid,installment=False)
    return dict(currency='KRW',tax_year=tax_year,national_decision_tax=national,
        local_decision_tax=decision,current_employer_withheld=current,
        former_employer_settled_tax=former,total_payment_credits=paid,settlement=cash,
        sources=[dict(LOCAL_SOURCE),dict(doc_id='kr.local-tax-basic.article59.2026',
            url='https://www.law.go.kr/LSW/lsLinkProc.do?joLnkStr=%EC%A0%9C97%EC%A1%B0&lsNm=%EC%A7%80%EB%B0%A9%EC%84%B8%EA%B8%B0%EB%B3%B8%EB%B2%95&mode=11',
            sha256='1ed709aa892ade3bbc0950038efe2755046549aed809dc2332e89575051c0266',
            provisions=['Article59'])],
        stage='local_salary_employer_special_collection_before_installments')


def national_salary_balance(decision_tax, current_employer_withheld,
        former_employer_settled_tax, *, tax_year,
        decision_and_employer_records_verified, installment):
    """Articles86/137/137-2/138, ordinary first year-end settlement only.

Former-employer amounts are settled decision taxes from valid receipts, not
their pre-refund monthly gross withholdings. Verification also excludes amended
settlements, prior refunds not reflected in receipts, deferrals and penalties.
The below-KRW1,000 noncollection applies to positive withholding balances;
refunds do not disappear under that threshold.
"""
    _year(tax_year)
    if decision_and_employer_records_verified is not True or installment is not False:
        raise ValueError('Verify decision and reconciled employer receipts; installments need separate allocation')
    decision, current, former = map(amount,(decision_tax,current_employer_withheld,former_employer_settled_tax))
    if any(value!=value.to_integral_value() for value in (decision,current,former)):
        raise ValueError('Established decision and employer receipt amounts must be whole won')
    with localcontext() as context:
        context.prec=40
        paid=current+former
        balance=decision-paid
        waived=balance if 0 < balance < 1000 else Decimal(0)
        cash=final_cash_balance(decision,paid,installment=False)
        if waived:
            cash=final_cash_balance(0,0,installment=False)
    return dict(currency='KRW',tax_year=tax_year,decision_tax=decision,
        current_employer_withheld=current,former_employer_settled_tax=former,
        total_payment_credits=paid,balance_before_noncollection=balance,
        small_balance_not_collected=waived,settlement=cash,
        tax_scope='national_salary_year_end_cash_only',
        sources=[dict(SOURCE,provisions=['Article86(1)','Article137','Article137-2','Article138']),
            dict(doc_id='kr.national-treasury.article47.2026',
                url='https://www.law.go.kr/LSW/lsLinkCommonInfo.do?lsJoLnkSeq=1031453583',
                sha256='e219a858f303c94d114495ffc0105b5fef7e7622b85a7f064c5e5f9c35a6b665',
                provisions=['Article47'])],
        stage='national_salary_cash_from_established_decision_before_installments')
