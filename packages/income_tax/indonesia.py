"""Indonesia 2026 ordinary resident annual assessment in IDR.

Separate/final income (including PP55/2022 as amended by PP20/2026), listed
company rates, tax incentives, joint/spouse allocation and part-year residence
require their own policies. Net bases are established after lawful adjustments.
"""
from copy import deepcopy
from decimal import Decimal, localcontext
import json
from pathlib import Path
from .arithmetic import Band, ZERO, amount, marginal_tax

POLICY_VERSION = 'id-calendar2026-2026-11-16'
SOURCES = json.loads(Path(__file__).with_name('id_2026_sources.json').read_text(encoding='utf-8'))['sources']
THOUSAND = Decimal('1000')
RELIEF_GROSS = Decimal('4800000000')
RELIEF_LIMIT = Decimal('50000000000')
PERSONAL_BANDS = tuple(Band(None if cap is None else Decimal(cap), Decimal(rate))
    for cap,rate in [('60000000','.05'),('250000000','.15'),('500000000','.25'),
                     ('5000000000','.30'),(None,'.35')])
PTKP = {f'{status}/{dependents}': Decimal('54000000') + Decimal('4500000')*(dependents+married)
        for status,married in [('TK',0),('K',1)] for dependents in range(4)}


def check(tax_year, ordinary_annual_treatment_confirmed):
    if type(tax_year) is not int or tax_year != 2026:
        raise ValueError('This policy covers calendar 2026 only')
    if ordinary_annual_treatment_confirmed is not True:
        raise ValueError('Full-year ordinary treatment and final/special-regime exclusions must be confirmed')


def thousands(value):
    return (value // THOUSAND) * THOUSAND


def company_tax(taxable_income_before_rounding, *, tax_year, article31e_gross_receipts,
                ordinary_annual_treatment_confirmed, gross_receipts_scope_confirmed, prepaid_tax):
    """Article31E applies automatically to the confirmed ordinary resident base.

The gross-receipts denominator covers all statutory receipts, after returns and
sales/cash discounts, before expenses. The adapter currently accepts domestic
ordinary income only and requires confirmation that no other receipts exist.
Rounded eligible base is allocated first; the remainder conserves total PKP.
Prepaid tax includes verified domestic withholding and instalments, refundable
in principle if above liability; it is not capped as a foreign-tax credit.
"""
    check(tax_year,ordinary_annual_treatment_confirmed)
    if gross_receipts_scope_confirmed is not True:
        raise ValueError('Complete article31E gross-receipts scope must be confirmed')
    raw,turnover,prepaid=map(amount,(taxable_income_before_rounding,article31e_gross_receipts,prepaid_tax))
    if turnover==ZERO and raw>ZERO:
        raise ValueError('Positive taxable income cannot use a zero gross-receipts basis')
    with localcontext() as ctx:
        ctx.prec=40
        base=thousands(raw)
        eligible=ZERO
        if turnover<=RELIEF_GROSS:
            eligible=base
        elif turnover<=RELIEF_LIMIT:
            eligible=thousands((base*RELIEF_GROSS)//turnover)
        remaining=base-eligible
        reduced_tax=eligible*Decimal('.11')
        ordinary_tax=remaining*Decimal('.22')
        tax=reduced_tax+ordinary_tax
        return dict(policy_version=POLICY_VERSION,tax_year=tax_year,currency='IDR',
            taxable_income_before_rounding=raw,taxable_income=base,
            article31e_gross_receipts=turnover,article31e_eligible_base=eligible,
            article31e_other_base=remaining,article31e_reduced_tax=reduced_tax,
            ordinary_rate_tax=ordinary_tax,final_tax=tax,prepaid_tax=prepaid,balance_due=tax-prepaid,
            sources=deepcopy(SOURCES),stage='ordinary_resident_company_after_statutory_base_rounding')


def resident_individual_tax(net_income_before_ptkp, *, tax_year, ptkp_status,
                            ptkp_entitlement_confirmed, ordinary_annual_treatment_confirmed, prepaid_tax):
    """PTKP uses confirmed start-of-year entitlement, not marital label alone.

TK/K and 0..3 fully dependent qualifying relatives cover ordinary separate
assessment only. Combined spouse income, separate-property/spouse allocations,
part-year residence and special deductions must not be inferred from this code.
Net income is after established expenses, allowable losses and religious gifts.
"""
    check(tax_year,ordinary_annual_treatment_confirmed)
    if not isinstance(ptkp_status,str) or ptkp_status not in PTKP or ptkp_entitlement_confirmed is not True:
        raise ValueError('PTKP status and start-of-year entitlement must be verified')
    net,prepaid=map(amount,(net_income_before_ptkp,prepaid_tax))
    with localcontext() as ctx:
        ctx.prec=40
        allowance=PTKP[ptkp_status]
        raw=max(ZERO,net-allowance)
        base=thousands(raw)
        tax,bands=marginal_tax(base,PERSONAL_BANDS)
        return dict(policy_version=POLICY_VERSION,tax_year=tax_year,currency='IDR',
            net_income_before_ptkp=net,ptkp_status=ptkp_status,ptkp_allowance=allowance,
            taxable_income_before_rounding=raw,taxable_income=base,bands=bands,
            final_tax=tax,prepaid_tax=prepaid,balance_due=tax-prepaid,
            sources=deepcopy([SOURCES[i] for i in (0,1,2,4,5)]),
            stage='ordinary_resident_individual_after_statutory_base_rounding')
