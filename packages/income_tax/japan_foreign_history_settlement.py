"""National annual settlement from current allocation and verified history.

This internal workpaper settles the three national taxes. Local history remains
in the matching ledger until the separate local levy-shortfall calculation.
It is not a saved assessment policy and does not override no-history attestations.
"""
from copy import deepcopy
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
from packages.contracts.income_tax import Money
from .japan import yen
from .japan_foreign_history import match_history
from .japan_foreign_credit import ROUNDING_SOURCE


class References(BaseModel):
    model_config = ConfigDict(extra='forbid')
    corporation_tax_reference: Money
    local_corporation_tax_reference: Money
    defence_tax_reference: Money


FORM_SOURCE = dict(doc_id='jp.nta.form1.2026',
    file='database/raw/jp/jp.nta.form1.2026.pdf',
    url='https://www.nta.go.jp/taxes/tetsuzuki/shinsei/annai/hojin/shinkoku/itiran2026/pdf/01-01-a.pdf',
    sha256='f72212f6ea52b81566a81cc5af510897e38d5a45002d26ff539aaef7ad3b8b63',
    provisions=['Corporation fields12-24: applied credit, unused credit refund and interim refund separately'])


def settle_national_history(current_allocation, history, *, reference_taxes,
        period_start, period_end, corporation_interim_liability,
        local_corporation_interim_liability,
        ordinary_final_return_without_other_credits_or_additions_verified):
    """Consume a current-only *component* plus independently verified history.

    Corporation eligible credit includes Schedule6(2)18+19+20. A refund of
    eligible credit exceeding corporation tax is distinct from unmatched tax
    above statutory limits (CTA74(1)(3),78) and interim refunds (CTA79).
    Local-corporation and defence amounts remain their current-year credits.
    """
    if ordinary_final_return_without_other_credits_or_additions_verified is not True:
        raise ValueError('Verify ordinary final-return references and absence of other credits/additions')
    references = References.model_validate(reference_taxes)
    matched = match_history(current_allocation, history,
        period_start=period_start, period_end=period_end)
    if matched['current_period_start'] < '2026-04-01' and references.defence_tax_reference:
        raise ValueError('Defence tax requires a business period beginning on or after2026-04-01')
    national = current_allocation['national_credit']
    if national.get('policy_version') != 'jp-current-national-return-credits-20261122':
        raise ValueError('Expected rounded current national credit fields')
    interim = [int(yen(corporation_interim_liability)),
               int(yen(local_corporation_interim_liability)), 0]
    if any(value % 100 for value in interim):
        raise ValueError('Interim return liabilities must be whole hundreds of yen')
    capacity_credit = int(yen(matched['historical_capacity_used_by_layer']['national']))
    excess_credit = int(yen(matched['historical_excess_used_by_layer']['national']))
    settlements = {}
    for name, prepaid in zip(('corporation', 'local_corporation', 'defence'), interim):
        reference = int(yen(getattr(references, name + '_tax_reference')))
        current_credit = int(yen(national[name + '_credit']))
        limit = int(yen(national[name + '_credit_limit']))
        if not current_credit <= limit <= reference:
            raise ValueError('Current national credit, limit and reference must reconcile')
        old_capacity = capacity_credit if name == 'corporation' else 0
        old_excess = excess_credit if name == 'corporation' else 0
        eligible = current_credit + old_capacity + old_excess
        applied = min(reference, eligible)
        # Never truncate a negative liability or hide a credit refund in it.
        after = reference - applied
        liability = after // 100 * 100
        credit_refund = eligible - applied
        interim_refund = max(0, prepaid - liability)
        payable = max(0, liability - prepaid)
        settlements[name] = {key: Decimal(value) for key, value in dict(
            reference_tax=reference, current_foreign_credit=current_credit,
            historical_capacity_credit=old_capacity, historical_excess_credit=old_excess,
            eligible_foreign_credit=eligible, foreign_credit_applied_to_tax=applied,
            foreign_credit_refund=credit_refund,
            after_credit_before_final_rounding=after, annual_liability=liability,
            interim_return_liability=prepaid, interim_refund=interim_refund,
            balance_due=liability-prepaid, payable=payable,
            refundable=credit_refund+interim_refund).items()}
    sources = {source['doc_id']: deepcopy(source) for source in
        matched['sources'] + national['sources'] + [ROUNDING_SOURCE, FORM_SOURCE]}
    sources['jp.cta']['provisions'] += [
        'Articles74(1)(3),78: refund of eligible credit not deducted; Article79: separate interim refund']
    # Integer totals stay exact even when the caller has a low Decimal precision.
    totals = {key: Decimal(sum(int(row[field]) for row in settlements.values()))
        for key, field in [('total_annual_liability', 'annual_liability'),
                           ('total_payable', 'payable'), ('total_refundable', 'refundable'),
                           ('total_foreign_credit_refund', 'foreign_credit_refund'),
                           ('total_interim_refund', 'interim_refund')]}
    return dict(policy_version='jp-national-history-settlement-20261122', currency='JPY',
        history_matching=matched, settlements=settlements, **totals,
        sources=list(sources.values()),
        stage='national_annual_history_settlement_local_history_not_settled')
