"""National salary year-end cash balance from an established decision amount.

This does not establish the rounded annual decision amount or local tax. Those
must not be inferred from a pre-rounding annual calculation without form review.
"""
from decimal import Decimal, localcontext

from .arithmetic import amount
from .korea_employment import SOURCE, _year
from .korea_rounding import final_cash_balance


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
