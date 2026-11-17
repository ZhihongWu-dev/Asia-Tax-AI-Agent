"""YA2026 individual dividend base allocation, before settlement and rounding.

Act 53 Schedule 1 Part XXII; P.U.(A)148/2025 rule 2. Inputs are established
statutory/aggregate/chargeable income, not raw cash receipts. Exempt dividends,
foreign income, expenses and relief eligibility must be resolved upstream.
"""
from copy import deepcopy
from decimal import Decimal, localcontext

from .arithmetic import ZERO, amount
from .malaysia import SOURCES

THRESHOLD = Decimal('100000')
RATE = Decimal('.02')
POLICY_VERSION = 'my-dividend-ya2026-2026-11-18'
DIVIDEND_SOURCES = [*SOURCES, {
    'doc_id': 'my.pua148.2025.dividend-income',
    'url': 'https://www.parlimen.gov.my/ipms/eps/2025-08-28/ST.140.2025%20-%20ST140.2025.pdf',
    'sha256': 'fd85095d1bb8b841997447558c8af7ca09a1a6695b6a2e3c44f7fca4e334059a',
    'locator': 'Rule 2(1)-(5)',
}, {
    'doc_id': 'my.hasil.be2025.explanatory',
    'url': 'https://ef.hasil.gov.my/eBE2026/Pdf/Nota_BE_e.pdf',
    'sha256': '587421c806cb9b62ba9789627dadf7c85cc9b314ea99971935cb4e105c347222',
    'locator': 'B2 threshold example; B15-B19 allocation and tax',
    'note': 'YA2025 example supports threshold interpretation; statute and rules continue into YA2026.',
}]


def dividend_statutory_income(before_threshold, *, scope_verified):
    """Apply the annual threshold once to qualifying Malaysian-source income.

The caller establishes statutory income before this threshold, including
expense and exemption treatment, across all qualifying payers for one person.
This is not a per-voucher or per-payer allowance.
"""
    if scope_verified is not True:
        raise ValueError('Dividend scope, statutory income and annual aggregation must be verified')
    return max(ZERO, amount(before_threshold) - THRESHOLD)


def allocate_dividend_income(*, assessment_year, residency,
                             dividend_statutory_income, aggregate_income,
                             chargeable_income, bases_verified):
    """Allocate verified A/B*C, using A after the annual RM100,000 threshold.

For joint assessment the caller must supply the combined statutory dividend
income and aggregate/chargeable bases after each spouse's assessment rules.
This function does not compute individual reliefs or joint-assessment inputs.
The ordinary remainder still needs the resident/nonresident Part I schedule.
"""
    if type(assessment_year) is not int or assessment_year != 2026:
        raise ValueError('This policy is verified only for YA2026')
    if residency not in ('resident', 'nonresident'):
        raise ValueError('Residency must be established')
    if bases_verified is not True:
        raise ValueError('Statutory, aggregate and chargeable bases must be verified')
    a, b, c = map(amount, (dividend_statutory_income, aggregate_income, chargeable_income))
    if a > b or c > b:
        raise ValueError('Dividend statutory and chargeable income cannot exceed aggregate income')
    with localcontext() as context:
        context.prec = 40
        dividend_base = ZERO if b == ZERO else a * c / b
        return dict(policy_version=POLICY_VERSION, assessment_year=assessment_year,
                    residency=residency, currency='MYR', dividend_statutory_income=a,
                    aggregate_income=b, chargeable_income=c,
                    dividend_chargeable_income=dividend_base,
                    ordinary_chargeable_income=c-dividend_base,
                    dividend_tax=dividend_base*RATE, dividend_rate=RATE,
                    sources=deepcopy(DIVIDEND_SOURCES),
                    stage='dividend_allocation_before_ordinary_tax_settlement_and_rounding')
