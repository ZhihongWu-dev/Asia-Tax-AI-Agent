"""Schedule6(3) historical capacity/excess matching before tax settlement.

Local levy-shortfall ledgers are separate. This component does not turn a
matched amount into a refund, amend prior returns or approve filing entitlement.
"""
from copy import deepcopy
from datetime import date,timedelta
from decimal import Decimal
from pydantic import BaseModel,ConfigDict,Field,StrictBool
from packages.contracts.income_tax import Money
from .japan import yen
from .japan_company import annual_period

LAYERS=('national','prefectural','municipal')
SOURCES=[
 dict(doc_id='jp.local-order.20261122',file='database/raw/jp/jp.local-order.20261122.json',
  url='https://laws.e-gov.go.jp/law/325CO0000000245/20261101_508CO0000000083',
  sha256='9bc03b230fb0ed1039e33a1544cd53772939ee25d6d4648a386400ea269dfb17',
  provisions=['Articles9-7(2),(5),48-13(2),(6): oldest period and national/prefectural/municipal ordering; separate levy-shortfall treatment excluded']),
 dict(doc_id='jp.cta',file='database/raw/jp/jp.cta.xml',
  url='https://laws.e-gov.go.jp/law/340AC0000000034',
  sha256='b3adc0eabf98a8210ec465d6ded837fb0fadf65d4cfcb3e3bc2b7e43ca27212a',
  provisions=['Article69(2)-(3): prior periods starting within three years; defence substitutions separately sourced']),
 dict(doc_id='jp.cta.order',file='database/raw/jp/jp.cta.order.xml',
  url='https://laws.e-gov.go.jp/law/340CO0000000097',
  sha256='e2654ef6523c2fb501331747c0ee2855bc7d4c942d061b1ea7caa26d5d86108a',
  provisions=['Articles144(1)-(5),145(1)-(3): oldest-year matching and no duplicate use']),
]


class Balances(BaseModel):
    model_config=ConfigDict(extra='forbid')
    national: Money
    prefectural: Money
    municipal: Money


class Lot(BaseModel):
    model_config=ConfigDict(extra='forbid')
    identifier: str=Field(min_length=1,max_length=120,pattern=r'^\S(?:.*\S)?$')
    period_start: date
    period_end: date
    unused_capacity: Balances
    excess_foreign_tax: Money


class History(BaseModel):
    model_config=ConfigDict(extra='forbid')
    periods: list[Lot]=Field(min_length=1,max_length=200)
    original_returns_entitlement_prior_usage_and_continuous_filings_verified: StrictBool
    no_foreign_tax_expense_elections_reductions_groups_or_reorganizations_verified: StrictBool
    no_local_levy_shortfall_balances_or_special_adjustments_verified: StrictBool


def match_history(current,history,*,period_start,period_end):
    """Consume verified opening balances; do not calculate final tax credits."""
    h=History.model_validate(history)
    if any(getattr(h,key) is not True for key in History.model_fields if key.endswith('_verified')):
        raise ValueError('Verify historical returns, exclusions and separate local shortfall ledgers')
    start,end=annual_period(period_start,period_end)
    # annual_period restricts current starts to2026, so these anniversary dates
    # have no February29 ambiguity. Historical origins may themselves be leap days.
    lower=start.replace(year=start.year-3)
    next_start=end+timedelta(days=1)
    next_lower=next_start.replace(year=next_start.year-3)
    if current.get('policy_version')!='jp-current-local-foreign-allocation-20261122':
        raise ValueError('Expected current national/local foreign allocation')
    original_capacity=Balances.model_validate(current['current_unused_capacity_before_history'])
    capacity={k:int(yen(getattr(original_capacity,k))) for k in LAYERS}
    excess=int(yen(current['foreign_tax_above_all_current_limits']))
    if excess and any(capacity.values()):
        raise ValueError('Current excess cannot coexist with unused statutory capacity')
    ordered=sorted(h.periods,key=lambda row:row.period_start)
    if len({r.identifier for r in ordered})!=len(ordered):
        raise ValueError('Historical identifiers must be unique')
    previous_end=None;rows=[]
    cap_used={k:0 for k in LAYERS};excess_used={k:0 for k in LAYERS}
    for lot in ordered:
        if lot.period_end<lot.period_start or lot.period_end>=start or (lot.period_end-lot.period_start).days>=366:
            raise ValueError('History must contain completed prior business periods')
        if previous_end is not None and lot.period_start<=previous_end:
            raise ValueError('Historical business periods cannot overlap or duplicate')
        previous_end=lot.period_end
        opening={k:int(yen(getattr(lot.unused_capacity,k))) for k in LAYERS}
        opening_excess=int(yen(lot.excess_foreign_tax))
        if opening_excess and any(opening.values()):
            raise ValueError('Historical excess and unused statutory capacity cannot coexist in one period')
        used_capacity={k:0 for k in LAYERS};used_excess={k:0 for k in LAYERS}
        expired=lot.period_start<lower
        remaining_capacity=dict(opening);remaining_excess=opening_excess
        if not expired:
            for layer in LAYERS:
                use=min(excess,remaining_capacity[layer])
                excess-=use;remaining_capacity[layer]-=use;used_capacity[layer]=use;cap_used[layer]+=use
            for layer in LAYERS:
                use=min(remaining_excess,capacity[layer])
                remaining_excess-=use;capacity[layer]-=use;used_excess[layer]=use;excess_used[layer]+=use
        expires_before_next=lot.period_start<next_lower
        def money(values):return {k:Decimal(v) for k,v in values.items()}
        rows.append(dict(identifier=lot.identifier,period_start=lot.period_start.isoformat(),
            period_end=lot.period_end.isoformat(),expired_before_current=expired,
            opening_capacity=money(opening),opening_excess=Decimal(opening_excess),
            capacity_matched_to_current_excess=money(used_capacity),
            excess_matched_to_current_capacity=money(used_excess),
            remaining_capacity_after_matching=money(remaining_capacity),remaining_excess_after_matching=Decimal(remaining_excess),
            expired_capacity=money(remaining_capacity if expires_before_next else {k:0 for k in LAYERS}),
            expired_excess=Decimal(remaining_excess if expires_before_next else 0),
            next_period_capacity=money({k:0 for k in LAYERS} if expires_before_next else remaining_capacity),
            next_period_excess=Decimal(0 if expires_before_next else remaining_excess)))
    return dict(policy_version='jp-foreign-history-matching-20261122',currency='JPY',
        current_period_start=start.isoformat(),current_period_end=end.isoformat(),
        earliest_eligible_origin_start=lower.isoformat(),next_period_start=next_start.isoformat(),
        periods=rows,historical_capacity_used_by_layer={k:Decimal(v) for k,v in cap_used.items()},
        historical_excess_used_by_layer={k:Decimal(v) for k,v in excess_used.items()},
        current_capacity_remaining={k:Decimal(v) for k,v in capacity.items()},current_excess_remaining=Decimal(excess),
        sources=deepcopy(current['sources'])+deepcopy(SOURCES),
        stage='historical_limit_matching_before_final_tax_and_local_shortfall_settlement')
