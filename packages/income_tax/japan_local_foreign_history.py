"""Local annual foreign credits with separate statutory and levy ledgers.

Single unchanged prefecture/municipality, ordinary final returns. Multi-office
redistribution, amended-return adjustments and reorganizations need their own
calculations; they are not silently treated as a single local filing.
"""
from copy import deepcopy
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from packages.contracts.income_tax import Money
from .japan import yen
from .japan_foreign_history import LimitHistory, match_limit_history
from .japan_foreign_credit import ROUNDING_SOURCE
from .japan_osaka import SOURCES as PREFECTURAL_SOURCES, CITY_SOURCES

LAYERS = ('prefectural', 'municipal')
GUIDE = dict(doc_id='jp.kyoto.foreign-credit-guide.202604',
    file='database/raw/jp/jp.kyoto.foreign-credit-guide.202604.pdf',
    url='https://www.city.kyoto.lg.jp/gyozai/cmsfiles/contents/0000034/34624/gaikokuzeikoujoTebiki_R0804.pdf',
    sha256='371fa7babfd16ce196c0dfa52c2a112e90e5258b434a7e1d0b248b1b25d4e9ec',
    provisions=['Pages1-2: separate local levy-shortfall balances; oldest origin first, before current credit'])


class LocalLot(BaseModel):
    model_config = ConfigDict(extra='forbid')
    identifier: str = Field(min_length=1,max_length=120,pattern=r'^\S(?:.*\S)?$')
    period_start: date
    period_end: date
    prefectural: Money
    municipal: Money


class LevyHistory(BaseModel):
    model_config = ConfigDict(extra='forbid')
    periods: list[LocalLot] = Field(max_length=200)
    prefectural_filing_id: str = Field(min_length=1,max_length=120,pattern=r'^\S(?:.*\S)?$')
    municipal_filing_id: str = Field(min_length=1,max_length=120,pattern=r'^\S(?:.*\S)?$')
    original_local_returns_prior_usage_and_continuous_filings_verified: StrictBool
    single_unchanged_prefecture_and_municipality_verified: StrictBool
    no_amended_return_credit_adjustments_groups_or_reorganizations_verified: StrictBool


def settle_local_history(current_allocation, limit_history, levy_history, *,
        period_start, period_end, prefectural_interim_liability,
        municipal_interim_liability):
    limits = LimitHistory.model_validate(limit_history)
    local = LevyHistory.model_validate(levy_history)
    if any(getattr(local,key) is not True for key in LevyHistory.model_fields if key.endswith('_verified')):
        raise ValueError('Verify local historical returns, unchanged filing scope and exclusions')
    matched = match_limit_history(current_allocation,limits,period_start=period_start,period_end=period_end)
    start = date.fromisoformat(matched['current_period_start'])
    lower = date.fromisoformat(matched['earliest_eligible_origin_start'])
    next_start = date.fromisoformat(matched['next_period_start'])
    next_lower = next_start.replace(year=next_start.year-3)
    ordered = sorted(local.periods,key=lambda row:row.period_start)
    if len({r.identifier for r in ordered}) != len(ordered):
        raise ValueError('Local historical identifiers must be unique')
    previous_end = None
    for row in ordered:
        if row.period_end < row.period_start or row.period_end >= start or (row.period_end-row.period_start).days >= 366:
            raise ValueError('Local history must contain completed prior business periods')
        if previous_end is not None and row.period_start <= previous_end:
            raise ValueError('Local historical business periods cannot overlap')
        previous_end = row.period_end
    # Both ledgers belong to the same entity and must describe the same fiscal
    # calendar when periods overlap; absence from either ledger is allowed.
    timeline = sorted(set((r.period_start,r.period_end) for r in [*limits.periods,*ordered]))
    if any(b[0] <= a[1] for a,b in zip(timeline,timeline[1:])):
        raise ValueError('Statutory and local levy ledgers must use a consistent fiscal calendar')
    rows = [dict(identifier=r.identifier,period_start=r.period_start.isoformat(),
        period_end=r.period_end.isoformat(),expired_before_current=r.period_start < lower,
        opening={},used={},remaining_after_use={},expired={},next_period={}) for r in ordered]
    settlements = {}; new_shortfall = {}; expired = {}; next_balances = {}
    for layer, interim_value in zip(LAYERS,(prefectural_interim_liability,municipal_interim_liability)):
        component = current_allocation[layer]
        filings = component['filings']
        if len(filings) != 1 or filings[0]['filing_id'] != getattr(local,layer+'_filing_id'):
            raise ValueError('Local history requires one matching unchanged filing per tax layer')
        filing = filings[0]
        if filing['employee_weight'] <= 0:
            raise ValueError('Positive employee weight required for each local filing')
        levy = int(yen(filing['available_levy']))
        prepaid = int(yen(interim_value))
        if prepaid % 100:
            raise ValueError('Local interim liabilities must be whole hundreds of yen')
        remaining_levy = levy; prior_used = 0; expiring = 0; carried = 0
        for origin, result in zip(ordered,rows):
            opening = int(yen(getattr(origin,layer)))
            used = min(opening,remaining_levy) if origin.period_start >= lower else 0
            remaining_levy -= used; prior_used += used
            residual = opening-used
            expires = residual if origin.period_start < next_lower else 0
            forward = residual-expires
            expiring += expires; carried += forward
            for key,value in [('opening',opening),('used',used),('remaining_after_use',residual),
                              ('expired',expires),('next_period',forward)]:
                result[key][layer] = Decimal(value)
        current_pool = int(yen(component['credit_pool']))
        historical_limit_credit = sum(int(yen(matched[key][layer])) for key in
            ('historical_capacity_used_by_layer','historical_excess_used_by_layer'))
        eligible = current_pool+historical_limit_credit
        current_used = min(remaining_levy,eligible)
        shortfall = eligible-current_used
        after = remaining_levy-current_used
        liability = after//100*100
        balance = liability-prepaid
        settlements[layer] = {key:Decimal(value) for key,value in dict(
            reference_tax=levy,current_credit_pool=current_pool,
            historical_limit_credit=historical_limit_credit,
            current_period_eligible_credit=eligible,prior_levy_credit_applied=prior_used,
            current_period_credit_applied=current_used,total_foreign_credit_applied=prior_used+current_used,
            after_credit_before_final_rounding=after,annual_liability=liability,
            interim_return_liability=prepaid,balance_due=balance,payable=max(0,balance),
            interim_refund=max(0,-balance),refundable=max(0,-balance),
            current_levy_shortfall=shortfall).items()}
        new_shortfall[layer] = Decimal(shortfall)
        expired[layer] = Decimal(expiring)
        next_balances[layer] = Decimal(carried+shortfall)
    return_sources = [s for s in PREFECTURAL_SOURCES+CITY_SOURCES if s['doc_id'] in
        ('jp.osaka-prefecture-return-instructions.202607','jp.osaka-city-return-instructions')]
    sources = {s['doc_id']:deepcopy(s) for s in matched['sources']+[GUIDE,ROUNDING_SOURCE]+return_sources}
    sources['jp.local-order.20261122']['provisions'] += [
        'Articles9-7(17),(27),48-13(18): separate unrelieved local levy amounts and filing entitlement']
    return dict(policy_version='jp-single-local-history-settlement-20261122',currency='JPY',
        history_matching=matched,local_levy_history=rows,settlements=settlements,
        current_period_levy_shortfall=dict(period_start=start.isoformat(),
            period_end=matched['current_period_end'],balances=new_shortfall),
        expired_levy_shortfall=expired,next_period_levy_shortfall=next_balances,
        total_payable=Decimal(sum(int(r['payable']) for r in settlements.values())),
        total_refundable=Decimal(sum(int(r['refundable']) for r in settlements.values())),
        sources=list(sources.values()),
        stage='single_prefecture_municipality_history_settlement_national_and_other_taxes_separate')
