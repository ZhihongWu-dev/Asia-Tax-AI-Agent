"""Three Japanese national company taxes for ordinary annual 2026 starts.

This adapter covers a verified taxable base without tax credits/additions,
group taxation, retained-profit surtax, special entities or Pillar Two. Municipal
and prefectural taxes need separate calculation. Interim amounts are liabilities
from interim returns, not cash payments; balances are separate for each tax.
"""
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal, ROUND_DOWN, localcontext
import json
from pathlib import Path

from .japan import yen

_SOURCES = json.loads(Path(__file__).with_name('jp_company_2026_sources.json').read_text(encoding='utf-8'))


def annual_period(period_start, period_end):
    def day(value):
        if type(value) is date:
            return value
        if type(value) is str:
            parsed=date.fromisoformat(value)
            if parsed.isoformat()==value:
                return parsed
        raise ValueError('Exact ISO calendar dates required')
    start,end=day(period_start),day(period_end)
    if start.year!=2026 or end!=date(2027,start.month,start.day)-timedelta(days=1):
        raise ValueError('Requires a full twelve-month period starting in 2026')
    return start,end


def company_tax(taxable_income_before_rounding, *, period_start, period_end,
        rate_regime, rate_classification_verified, ordinary_no_adjustments_confirmed,
        corporation_interim_liability, local_corporation_interim_liability):
    start,end=annual_period(period_start,period_end)
    if rate_classification_verified is not True or ordinary_no_adjustments_confirmed is not True:
        raise ValueError('Verify company classification, tax basis and all excluded adjustments')
    if rate_regime not in ('ordinary','sme_reduced','sme_excluded'):
        raise ValueError('Unknown statutory rate classification')
    income,interim,local_interim=map(yen,[taxable_income_before_rounding,
        corporation_interim_liability,local_corporation_interim_liability])
    with localcontext() as context:
        context.prec=40
        if interim%100 or local_interim%100:
            raise ValueError('Interim return liabilities must be in whole hundreds of yen')
        def down(value,unit):
            return (value/unit).to_integral_value(rounding=ROUND_DOWN)*unit
        base=down(income,1000)
        # The reviewed sources do not resolve whether this eligibility test uses
        # income before or after Article118 truncation. Do not guess where the
        # two interpretations give different rates.
        if rate_regime=='sme_reduced' and income>1000000000 and base==1000000000:
            raise ValueError('SME income threshold rounding requires manual review (JPY1,000,000,001–1,000,000,999)')
        lower_rate=(Decimal('.19') if rate_regime=='sme_excluded' else
                    Decimal('.17') if income>1000000000 else Decimal('.15'))
        lower_base=min(base,Decimal('8000000')) if rate_regime!='ordinary' else Decimal('0')
        # References for the two additional national taxes are computed before
        # the final corporation-tax amount is truncated to hundreds of yen.
        reference=lower_base*lower_rate+(base-lower_base)*Decimal('.232')
        corporation=down(reference,100)
        local_base=down(reference,1000)
        local_tax=down(local_base*Decimal('.103'),100)
        defence_applies=start>=date(2026,4,1)
        defence_base=down(max(Decimal('0'),reference-5000000),1000) if defence_applies else Decimal('0')
        defence_tax=down(defence_base*Decimal('.04'),100)
        return dict(policy_version='jp-company-national-2026-2026-11-17',currency='JPY',
            period_start=start.isoformat(),period_end=end.isoformat(),rate_regime=rate_regime,
            tax_scope='japan_three_national_company_taxes_only',
            taxable_income_before_rounding=income,taxable_income=base,
            lower_tier_base=lower_base,lower_tier_rate=lower_rate if lower_base else None,
            corporation_tax_reference=reference,corporation_tax=corporation,
            local_corporation_tax_base=local_base,local_corporation_tax=local_tax,
            defence_return_required=defence_applies,defence_tax_base=defence_base,defence_tax=defence_tax,
            final_tax=corporation+local_tax+defence_tax,
            corporation_interim_liability=interim,local_corporation_interim_liability=local_interim,
            corporation_balance_due=corporation-interim,
            local_corporation_balance_due=local_tax-local_interim,
            local_taxes_calculated=False,sources=deepcopy(_SOURCES['sources']))
