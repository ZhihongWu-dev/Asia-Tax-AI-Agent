"""India TY 2026-27 ordinary-income annual liability on an established base.

The individual default regime and domestic-company section 200 option are
separate elections. This is before payment credits, interest and penalties;
special-rate income and agricultural aggregation require other adapters.
"""
from copy import deepcopy
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP, localcontext
import json
from pathlib import Path

from .arithmetic import Band, amount, marginal_tax

_SOURCES = json.loads(Path(__file__).with_name('in_2026_sources.json').read_text(encoding='utf-8'))
_PERSONAL = tuple(Band(None if cap is None else Decimal(cap), Decimal(rate))
    for cap, rate in [('400000','0'),('800000','.05'),('1200000','.10'),
                     ('1600000','.15'),('2000000','.20'),('2400000','.25'),(None,'.30')])


def settle(annual_result, *, tds_tcs_credit, advance_tax_paid, self_assessment_paid,
           total_interest_due, total_fee_due, settlement_verified):
    """Aggregate ordinary return balance under ss266, 431 and 516.

Credits must belong to this taxpayer/period and be reconciled to evidence.
Interest and fees are cumulative assessed amounts, not remaining balances;
their date-dependent computation and the s266(3) payment allocation must
already have been verified. Prior refunds, updated returns, ESOP deferral,
penalties and additional demands are not part of this ordinary settlement.
No refund interest or cross-year offsets are calculated.
"""
    if settlement_verified is not True:
        raise ValueError('Verify period credits, cumulative interest/fees, payment allocation and settlement exclusions')
    if annual_result.get('tax_scope') != 'india_ordinary_annual_ty2026_27':
        raise ValueError('India ordinary annual calculation required')
    tds, advance, self_paid, interest, fee = map(amount, (
        tds_tcs_credit, advance_tax_paid, self_assessment_paid, total_interest_due, total_fee_due))
    with localcontext() as context:
        context.prec = 40
        paid = tds + advance + self_paid
        # Use the unrounded annual reference; round the actual net payable or
        # refundable once. Rounding annual liability first creates boundary errors.
        total = annual_result['annual_tax_before_rounding'] + interest + fee
        net = total - paid
        magnitude = round_rupees(abs(net))
        rounded = -magnitude if net < 0 and magnitude else magnitude
        result = deepcopy(annual_result)
        result.update(tax_scope='india_ordinary_settlement_ty2026_27',
            stage='ordinary_return_balance_with_verified_interest_fees_and_payments',
            tds_tcs_credit=tds, advance_tax_paid=advance, self_assessment_paid=self_paid,
            total_interest_due=interest, total_fee_due=fee, total_payments=paid,
            total_liability_before_rounding=total, balance_before_rounding=net,
            balance_due=rounded, tax_payable=max(rounded, Decimal('0')),
            refund_due=max(-rounded, Decimal('0')), refund_interest_calculated=False)
        return result


def round_rupees(value):
    """Section 516: discard paise, then round to nearest ten rupees."""
    value = amount(value)
    with localcontext() as context:
        context.prec = 40
        whole = value.to_integral_value(rounding=ROUND_DOWN)
        return (whole / 10).to_integral_value(rounding=ROUND_HALF_UP) * 10


def annual_tax(taxable_income_before_rounding, *, period_start, period_end,
               regime, regime_and_base_verified, ordinary_domestic_scope_confirmed,
               resident_age_band=None, amt_not_applicable_verified=None):
    """Compute annual liability; caller must establish elections and tax base.

personal_new_resident requires a resident individual taxed under s202, without
opting out. personal_old_resident requires a valid s202(4) election, the highest
age band attained during the tax year, no s206(2) AMT and no carried AMT credit.
company_section200 requires a valid timely domestic-company option
and compliance with s200's deduction/loss restrictions. Neither flag is inferred
from income size. No special-rate income, agricultural income, foreign relief,
IFSC concessions, other credits or adjustments may be included in this scope.
"""
    if period_start != '2026-04-01' or period_end != '2027-03-31':
        raise ValueError('Only Tax Year 2026-27 (not Assessment Year 2026-27) is reviewed')
    if regime_and_base_verified is not True or ordinary_domestic_scope_confirmed is not True:
        raise ValueError('Verify regime eligibility, established base and ordinary domestic scope')
    if regime not in ('personal_new_resident', 'personal_old_resident', 'company_section200'):
        raise ValueError('Unsupported India regime')
    old = regime == 'personal_old_resident'
    if old:
        if resident_age_band not in ('under60','60_to79','80_plus') or amt_not_applicable_verified is not True:
            raise ValueError('Old regime requires verified tax-year age band and AMT non-applicability')
        exemption = {'under60':250000,'60_to79':300000,'80_plus':500000}[resident_age_band]
        schedule = (Band(Decimal(exemption),Decimal('0')),)
        if exemption < 500000:
            schedule += (Band(Decimal('500000'),Decimal('.05')),)
        schedule += (Band(Decimal('1000000'),Decimal('.20')),Band(None,Decimal('.30')))
    else:
        if resident_age_band is not None or amt_not_applicable_verified is not None:
            raise ValueError('Age classification and AMT exclusion apply only to the old personal regime')
        schedule = _PERSONAL
    income = amount(taxable_income_before_rounding)
    with localcontext() as context:
        context.prec = 40
        base = round_rupees(income)
        rebate = relief = Decimal('0')
        if regime in ('personal_new_resident','personal_old_resident'):
            gross, bands = marginal_tax(base, schedule)
            if old:
                rebate = min(gross, Decimal('12500')) if base <= 500000 else Decimal('0')
            elif base <= 1200000:
                rebate = min(gross, Decimal('60000'))
            else:
                rebate = max(Decimal('0'), gross - (base - 1200000))
            tax = gross - rebate
            threshold, previous_rate, rate = (
                (50000000, Decimal('.25'), Decimal('.37')) if old and base > 50000000 else
                (20000000, Decimal('.15'), Decimal('.25')) if base > 20000000 else
                (10000000, Decimal('.10'), Decimal('.15')) if base > 10000000 else
                (5000000, Decimal('0'), Decimal('.10')) if base > 5000000 else
                (0, Decimal('0'), Decimal('0')))
            surcharge = tax * rate
            if threshold:
                threshold_tax, _ = marginal_tax(threshold, schedule)
                ceiling = threshold_tax * (1 + previous_rate) + base - threshold
                relief = max(Decimal('0'), tax + surcharge - ceiling)
        else:
            gross = tax = base * Decimal('.22')
            bands = ()
            rate = Decimal('.10')
            surcharge = tax * rate
        net_surcharge = surcharge - relief
        cess = (tax + net_surcharge) * Decimal('.04')
        unrounded = tax + net_surcharge + cess
        return dict(policy_version='in-ordinary-ty2026-27-2026-11-18', currency='INR',
            period_start=period_start, period_end=period_end, tax_year='2026-27',
            regime=regime, resident_age_band=resident_age_band,
            tax_scope='india_ordinary_annual_ty2026_27', taxable_income_before_rounding=income, taxable_income=base,
            gross_income_tax=gross, bands=bands, resident_rebate=rebate,
            income_tax_after_rebate=tax, surcharge_rate=rate, gross_surcharge=surcharge,
            surcharge_marginal_relief=relief, surcharge=net_surcharge,
            health_education_cess=cess, annual_tax_before_rounding=unrounded,
            final_tax=round_rupees(unrounded),
            stage='annual_liability_before_payment_credits_interest_penalties',
            sources=deepcopy(_SOURCES['sources']))
