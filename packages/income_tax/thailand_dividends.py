"""Section47bis certified dividend components for the annual assessment.

This prepares income and credits, not a tax liability or an election recommendation.
The caller must establish aggregation-election scope and reconcile every tranche
with saved income and withholding certificates before annual settlement.
"""
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal, localcontext

from .arithmetic import ZERO, amount
from .thailand import SOURCES, PERSONAL_BANDS


@dataclass(frozen=True)
class DividendTranche:
    # Dividend before shareholder withholding, not the net bank receipt.
    gross_dividend: Decimal | str | int
    corporate_rate_percent: Decimal | str | int | None
    withholding_tax: Decimal | str | int
    credit_eligible: bool


def prepare_aggregated_dividends(tranches, *, certificates_verified,
                                 recipient_eligibility_verified):
    """Gross up only eligible Thai-company dividend tranches at their own rate.

Non-creditable dividends must have rate=None; zero-rate eligible tranches may
explicitly carry rate=0. No default corporate rate or credit fraction is inferred.
Shareholder withholding is reported separately and is not part of gross-up.
Repeating divisions use40-digit Decimal precision before assessment rounding.
"""
    if certificates_verified is not True or recipient_eligibility_verified is not True:
        raise ValueError('Dividend certificates and recipient eligibility must be verified')
    if not isinstance(tranches, (list, tuple)) or not 1 <= len(tranches) <= 1000:
        raise ValueError('Provide between one and1000 certified dividend tranches')
    rows = []
    with localcontext() as ctx:
        ctx.prec = 40
        for tranche in tranches:
            if not isinstance(tranche, DividendTranche) or type(tranche.credit_eligible) is not bool:
                raise ValueError('Each dividend tranche requires explicit credit eligibility')
            gross, withheld = amount(tranche.gross_dividend), amount(tranche.withholding_tax)
            if withheld > gross:
                raise ValueError('Withholding exceeds the dividend before withholding')
            if tranche.credit_eligible:
                rate = amount(tranche.corporate_rate_percent)
                if rate >= 100:
                    raise ValueError('Certified corporate rate must be below100 percent')
                credit = gross * rate / (Decimal('100') - rate)
            else:
                if tranche.corporate_rate_percent is not None:
                    raise ValueError('Non-creditable dividends must not carry a credit rate')
                rate, credit = None, ZERO
            rows.append(dict(gross_dividend=gross, corporate_rate_percent=rate,
                             credit_eligible=tranche.credit_eligible, dividend_credit=credit,
                             assessable_dividend=gross + credit, withholding_tax=withheld,
                             net_cash_received=gross - withheld))
        return dict(tranches=rows,
                    gross_dividends=sum((r['gross_dividend'] for r in rows), ZERO),
                    dividend_credit=sum((r['dividend_credit'] for r in rows), ZERO),
                    assessable_dividends=sum((r['assessable_dividend'] for r in rows), ZERO),
                    withholding_tax=sum((r['withholding_tax'] for r in rows), ZERO),
                    sources=deepcopy([SOURCES[1]]),
                    stage='dividend_components_before_annual_assessment_and_rounding')


def annual_dividend_assessment(tranches, *, tax_year, election,
                               employment_gross, other_nonemployment_gross,
                               allowed_expenses_and_allowances, other_prepaid_tax,
                               certificates_verified, recipient_eligibility_verified,
                               election_scope_verified):
    """Domestic resident annual aggregation or section48(3) final10% election.

All amounts other than dividends are independently established ordinary annual
income/deductions. Scope verification includes all creditable payers under
OrderP119/2545 clause19, and excludes exempt/foreign/special-regime dividends.
No additional foreign or other tax credits are accepted by this calculation.
"""
    if type(tax_year) is not int or tax_year != 2026:
        raise ValueError('This policy covers tax year2026 only')
    if election not in ('aggregate', 'final_withholding') or election_scope_verified is not True:
        raise ValueError('Verify the complete dividend election scope')
    components = prepare_aggregated_dividends(tranches,
        certificates_verified=certificates_verified,
        recipient_eligibility_verified=recipient_eligibility_verified)
    employment, other, deductions, prepaid = map(amount, (
        employment_gross, other_nonemployment_gross,
        allowed_expenses_and_allowances, other_prepaid_tax))
    with localcontext() as ctx:
        ctx.prec = 40
        aggregated = election == 'aggregate'
        included = components['assessable_dividends'] if aggregated else ZERO
        credit = components['dividend_credit'] if aggregated else ZERO
        nonemployment = other + included
        gross = employment + nonemployment
        net = max(ZERO, gross - deductions)
        # Internal gross-up can repeat beyond six decimals. Retain precision
        # through band arithmetic; do not pass it through the input-money parser.
        progressive, lower = ZERO, ZERO
        for band in PERSONAL_BANDS:
            taxable = max(ZERO, (net if band.upper is None else min(net, band.upper)) - lower)
            progressive += taxable * band.rate
            if band.upper is not None:
                lower = band.upper
        minimum_raw = nonemployment * Decimal('.005') if nonemployment >= 120000 else ZERO
        minimum = minimum_raw if minimum_raw > 5000 else ZERO
        selected = max(progressive, minimum)
        net_assessed = selected - credit
        dividend_final = ZERO if aggregated else components['gross_dividends'] * Decimal('.10')
        # The final election cannot turn dividend withholding into a refundable
        # annual credit. Require the fully withheld10% before treating it as final.
        if not aggregated and any(r['withholding_tax'] != r['gross_dividend'] * Decimal('.10')
                                  for r in components['tranches']):
            raise ValueError('Final election requires verified10 percent withholding on every tranche')
        annual_prepaid = prepaid + (components['withholding_tax'] if aggregated else ZERO)
        balance = net_assessed - annual_prepaid
        return dict(policy_version='th-dividend-annual-2026-2026-11-18', tax_year=tax_year,
                    currency='THB', election=election, dividend_components=components,
                    annual_assessable_income=gross, net_taxable_income=net,
                    progressive_tax=progressive, minimum_tax_before_exemption=minimum_raw,
                    minimum_tax=minimum, gross_tax=selected, dividend_credit=credit,
                    net_assessed_tax=net_assessed, final_tax=max(ZERO, net_assessed),
                    refundable_dividend_credit=max(ZERO, -net_assessed),
                    separate_final_dividend_tax=dividend_final, prepaid_tax=annual_prepaid,
                    balance_due=balance, amount_payable=max(ZERO, balance),
                    refund_due=max(ZERO, -balance),
                    sources=deepcopy(SOURCES[:4]) + [{'url':'https://www.rd.go.th/11162.html',
                        'title':'Revenue Department OrderP119/2545, clause19'}],
                    stage='resident_dividend_annual_before_assessment_rounding')
