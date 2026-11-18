"""Thai calendar-2026 ordinary annual rates and section 48(2) comparison."""
from copy import deepcopy
from decimal import Decimal, localcontext
import json
from pathlib import Path
from .arithmetic import Band, ZERO, amount, marginal_tax

POLICY_VERSION='th-calendar2026-2026-11-16'
SOURCES=json.loads(Path(__file__).with_name('th_2026_sources.json').read_text(encoding='utf-8'))['sources']
PERSONAL_BANDS=tuple(Band(None if cap is None else Decimal(cap),Decimal(rate)) for cap,rate in
    [('150000','0'),('300000','.05'),('500000','.10'),('750000','.15'),('1000000','.20'),
     ('2000000','.25'),('5000000','.30'),(None,'.35')])
SME_BANDS=(Band(Decimal('300000'),ZERO),Band(Decimal('3000000'),Decimal('.15')),Band(None,Decimal('.20')))


def check(tax_year,ordinary_treatment_confirmed):
    if type(tax_year) is not int or tax_year!=2026:
        raise ValueError('This policy covers tax year 2026 only')
    if ordinary_treatment_confirmed is not True:
        raise ValueError('Ordinary annual treatment and separate-regime exclusions must be confirmed')


def settle(gross,allowed_tax_credits,prepaid_tax):
    credit,prepaid=map(amount,(allowed_tax_credits,prepaid_tax))
    if credit>gross:
        raise ValueError('Allowed credits exceed computed tax')
    final=gross-credit
    return dict(gross_tax=gross,allowed_tax_credits=credit,final_tax=final,
                prepaid_tax=prepaid,balance_due=final-prepaid)


def reconcile_company_basis(case, *, net_taxable_profit, exempt_income):
    """Reconcile established Section65 amounts; do not infer loss eligibility.

    Saved income includes statutory valuation adjustments. Deductions contain
    only allowed expenses; losses are the separately verified usable prior-year
    amount. Exempt income must not also be counted in deductions.
    """
    exempt, base = map(amount, (exempt_income, net_taxable_profit))
    with localcontext() as context:
        context.prec = 40
        total = sum((item.gross_amount for item in case.incomes), ZERO)
        if exempt > total:
            raise ValueError('Exempt income cannot exceed saved total income')
        before_losses = total - exempt - case.claimed_deductions
        available = max(ZERO, before_losses)
        used = min(available, case.carried_losses)
        reconciled = available - used
        if base != reconciled:
            raise ValueError('Thai company net profit must reconcile to saved income, exemption, deductions and eligible losses')
        return dict(total_income=total, non_taxable_income=ZERO, exempt_income=exempt,
            allowed_deductions=case.claimed_deductions, income_before_loss_relief=before_losses,
            current_period_loss=max(ZERO, -before_losses), prior_losses_used=used,
            prior_losses_unused=case.carried_losses-used, taxable_income=reconciled,
            scope='Established Section65/65bis/65ter amounts; eligibility, loss vintages and future carryforward not inferred')


def company_tax(net_taxable_profit,*,tax_year,scheme,sme_eligibility_confirmed,
                ordinary_treatment_confirmed,allowed_tax_credits,prepaid_tax):
    """SME eligibility includes capital/revenue tests and continuous qualification.

Paid-up capital at period end <=THB5m and goods/service revenue <=THB30m;
Royal Decree530's continuing-period conditions must also be checked. Excludes
BOI/incentive, petroleum, gross-receipt and top-up tax regimes.
"""
    check(tax_year,ordinary_treatment_confirmed)
    if scheme not in ('ordinary','sme') or type(sme_eligibility_confirmed) is not bool:
        raise ValueError('Company scheme and eligibility must be explicit')
    if scheme=='sme' and not sme_eligibility_confirmed:
        raise ValueError('SME eligibility must be confirmed')
    base=amount(net_taxable_profit)
    with localcontext() as ctx:
        ctx.prec=40
        gross,bands=marginal_tax(base,SME_BANDS if scheme=='sme' else (Band(None,Decimal('.20')),))
        return dict(policy_version=POLICY_VERSION,tax_year=tax_year,currency='THB',
            net_taxable_profit=base,scheme=scheme,bands=bands,
            **settle(gross,allowed_tax_credits,prepaid_tax),sources=deepcopy([SOURCES[0],SOURCES[4]]),
            stage='ordinary_company_before_assessment_rounding')


def resident_individual_tax(net_taxable_income,*,tax_year,nonemployment_assessable_gross,
                            ordinary_treatment_confirmed,allowed_tax_credits,prepaid_tax):
    """Net basis after verified expenses/allowances; gross basis before those.

Section48(2) excludes section40(1) employment. Decree480 exempts that method
when its tax is <=THB5,000, without exempting section48(1) progressive tax.
Special final-tax elections, lump-sum termination, property disposal and joint
assessment need separate policies. Returns exact values before rounding.
"""
    check(tax_year,ordinary_treatment_confirmed)
    net,gross_nonemployment=map(amount,(net_taxable_income,nonemployment_assessable_gross))
    with localcontext() as ctx:
        ctx.prec=40
        progressive,bands=marginal_tax(net,PERSONAL_BANDS)
        minimum_raw=gross_nonemployment*Decimal('.005') if gross_nonemployment>=Decimal('120000') else ZERO
        exempt=minimum_raw<=Decimal('5000')
        minimum=ZERO if exempt else minimum_raw
        selected=max(progressive,minimum)
        return dict(policy_version=POLICY_VERSION,tax_year=tax_year,currency='THB',
            net_taxable_income=net,nonemployment_assessable_gross=gross_nonemployment,
            progressive_tax=progressive,minimum_tax_before_exemption=minimum_raw,
            minimum_tax_exempt=exempt,minimum_tax=minimum,bands=bands,
            selected_basis='progressive' if progressive>=minimum else 'minimum_gross_income',
            **settle(selected,allowed_tax_credits,prepaid_tax),sources=deepcopy(SOURCES[:4]),
            stage='resident_annual_comparison_before_assessment_rounding')
