"""Ordinary Indian domestic companies outside sections 200/201, TY2026-27.

The statutory book-profit adjustments and ordinary taxable base are separately
established. No IFSC, insurance/shipping regime, foreign income, special rates
or other tax credits/adjustments are included here.
"""
from copy import deepcopy
from decimal import Decimal, localcontext

from .arithmetic import amount
from .india import _SOURCES, round_rupees


def _charge(base, rate):
    gross = base * rate
    threshold, prior_rate, surcharge_rate = (
        (100000000, Decimal('.07'), Decimal('.12')) if base > 100000000 else
        (10000000, Decimal('0'), Decimal('.07')) if base > 10000000 else
        (0, Decimal('0'), Decimal('0')))
    surcharge = gross * surcharge_rate
    relief = Decimal('0')
    if threshold:
        ceiling = Decimal(threshold) * rate * (1 + prior_rate) + base - threshold
        relief = max(Decimal('0'), gross + surcharge - ceiling)
    net_surcharge = surcharge - relief
    cess = (gross + net_surcharge) * Decimal('.04')
    return dict(gross_income_tax=gross, surcharge_rate=surcharge_rate,
        gross_surcharge=surcharge, surcharge_marginal_relief=relief,
        surcharge=net_surcharge, health_education_cess=cess,
        annual_tax_before_rounding=gross + net_surcharge + cess)


def normal_company_tax(taxable_income_before_rounding, *, period_start, period_end,
        turnover_2024_25, mat_book_profit_before_rounding,
        regime_and_base_verified, ordinary_domestic_scope_confirmed,
        turnover_and_mat_adjustments_verified):
    if period_start != '2026-04-01' or period_end != '2027-03-31':
        raise ValueError('Only Tax Year 2026-27 is reviewed')
    if any(value is not True for value in (regime_and_base_verified,
            ordinary_domestic_scope_confirmed, turnover_and_mat_adjustments_verified)):
        raise ValueError('Verify ordinary domestic regime, historical turnover, taxable base and statutory MAT book-profit adjustments')
    income, turnover, book = map(amount, (taxable_income_before_rounding,
        turnover_2024_25, mat_book_profit_before_rounding))
    with localcontext() as context:
        context.prec = 40
        base, book_base = round_rupees(income), round_rupees(book)
        rate = Decimal('.25') if turnover <= 4000000000 else Decimal('.30')
        normal, mat = _charge(base, rate), _charge(book_base, Decimal('.14'))
        mat_applies = mat['annual_tax_before_rounding'] > normal['annual_tax_before_rounding']
        selected = mat if mat_applies else normal
        return dict(policy_version='in-company-normal-ty2026-27-2026-11-18',
            currency='INR', period_start=period_start, period_end=period_end,
            tax_year='2026-27', regime='company_normal',
            tax_scope='india_ordinary_annual_ty2026_27',
            stage='annual_liability_before_payment_credits_interest_penalties',
            taxable_income_before_rounding=income, taxable_income=base,
            turnover_2024_25=turnover, normal_company_rate=rate,
            mat_book_profit_before_rounding=book, mat_book_profit=book_base,
            normal_tax_including_surcharge_cess=normal['annual_tax_before_rounding'],
            mat_tax_including_surcharge_cess=mat['annual_tax_before_rounding'],
            mat_applies=mat_applies, normal_components=normal, mat_components=mat,
            legacy_mat_credit_used=Decimal('0'), new_mat_credit=Decimal('0'),
            final_tax=round_rupees(selected['annual_tax_before_rounding']),
            sources=deepcopy(_SOURCES['sources']), **selected)
