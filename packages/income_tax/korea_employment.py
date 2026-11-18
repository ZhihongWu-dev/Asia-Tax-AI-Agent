"""Article47/59 employment components, before return-level adjustments/rounding.

Aggregate ordinary gross salary across employers after exempt pay is removed.
Daily-worker income and special reductions use separate rules. These components
do not constitute a complete annual national or local personal assessment.
"""
from decimal import Decimal, localcontext

from .arithmetic import Band, amount, marginal_tax

_DEDUCTION = tuple(Band(None if cap is None else Decimal(cap), Decimal(rate))
    for cap, rate in [('5000000', '.70'), ('15000000', '.40'),
                      ('45000000', '.15'), ('100000000', '.05'), (None, '.02')])
SOURCE = dict(doc_id='kr.income-tax-act.20260701.ko',
    file='database/raw/kr/kr.income-tax-act.20260701.ko.pdf',
    url='https://www.law.go.kr/LSW/lsPdfPrint.do?ancYnChk=0&bylChaChk=N&efGubun=Y&efYd=20260701&joAllCheck=Y&joEfOutPutYn=on&lsiSeq=280405&mokChaChk=N',
    sha256='53a12749c4791386d4071f84b3adb4776566c50df561f35a0b8e88b4841b088a')


def _year(tax_year):
    if type(tax_year) is not int or tax_year != 2026:
        raise ValueError('Only 2026 employment components have been reviewed')


def employment_deduction(gross_salary, *, tax_year, aggregated_ordinary_salary_verified):
    """Aggregate all employers first; Article47 caps the deduction at KRW20m."""
    _year(tax_year)
    if aggregated_ordinary_salary_verified is not True:
        raise ValueError('Verify aggregated ordinary salary excluding exempt and daily-worker pay')
    gross = amount(gross_salary)
    raw, bands = marginal_tax(gross, _DEDUCTION)
    with localcontext() as context:
        context.prec = 40
        deduction = min(gross, raw, Decimal('20000000'))
        net = gross-deduction
    return dict(currency='KRW', tax_year=tax_year, gross_salary=gross,
        deduction_before_cap=raw, employment_deduction=deduction,
        employment_income=net, bands=bands,
        sources=[dict(SOURCE, provisions=['Article47(1),(3),(5)'])],
        stage='employment_income_before_personal_deductions_and_return_rounding')


def employment_credit_reference(gross_salary, employment_attributable_gross_tax, *,
        tax_year, ordinary_attribution_without_special_reductions_verified):
    """Article59 reference with salary cap, before other credits/return rounding.

The tax argument is the established tax attributable to employment, not total
mixed-income tax. Special employment reductions can change credit allocation
and must not silently use this ordinary reference as their final credit.
"""
    _year(tax_year)
    if ordinary_attribution_without_special_reductions_verified is not True:
        raise ValueError('Verify employment-attributable tax and absence of special reductions')
    gross, tax = amount(gross_salary), amount(employment_attributable_gross_tax)
    if not gross and tax:
        raise ValueError('Positive employment-attributable tax requires salary')
    with localcontext() as context:
        context.prec = 40
        raw = (tax*Decimal('.55') if tax <= 1300000 else
               Decimal('715000')+(tax-1300000)*Decimal('.30'))
        if gross <= 33000000:
            cap = Decimal('740000')
        elif gross <= 70000000:
            cap = max(Decimal('660000'), Decimal('740000')-(gross-33000000)*Decimal('.008'))
        elif gross <= 120000000:
            cap = max(Decimal('500000'), Decimal('660000')-(gross-70000000)/2)
        else:
            cap = max(Decimal('200000'), Decimal('500000')-(gross-120000000)/2)
        credit = min(raw, cap)
    return dict(currency='KRW', tax_year=tax_year, gross_salary=gross,
        employment_attributable_gross_tax=tax, credit_before_salary_cap=raw,
        salary_credit_cap=cap, employment_credit_reference=credit,
        sources=[dict(SOURCE, provisions=['Article59(1),(2)'])],
        stage='ordinary_employment_credit_before_other_credits_and_return_rounding')
