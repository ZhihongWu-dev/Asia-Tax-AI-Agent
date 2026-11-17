"""Section47bis certified dividend components for the annual assessment.

This prepares income and credits, not a tax liability or an election recommendation.
The caller must establish aggregation-election scope and reconcile every tranche
with saved income and withholding certificates before annual settlement.
"""
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal, localcontext

from .arithmetic import ZERO, amount
from .thailand import SOURCES


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
