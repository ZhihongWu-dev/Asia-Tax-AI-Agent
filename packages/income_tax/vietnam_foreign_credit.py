"""Vietnam foreign-income credit arithmetic on separately established bases.

Decree320 Article12(2)(c) caps paragraph(b) credit plus allocated top-up credit.
This helper does not determine treaty entitlements, the top-up allocation itself,
or the relevant declaration/payment period. It preserves the established ordinary
credit and limits the additional top-up claim to remaining capacity. Callers must
not use it to pool unrelated projects or transfer credits between tax periods.
"""
from decimal import localcontext

from .arithmetic import amount


def additional_top_up_credit(*, vietnam_tax_limit, established_ordinary_credit,
                             allocated_paid_top_up_tax,
                             same_income_and_period_verified):
    """Apply a shared cap to an additional eligible allocated paid top-up claim.

    Ordinary credit is an already established amount, not raw foreign tax paid.
    Allocated paid top-up is likewise a legally established amount for this
    offset period, not a group's total top-up liability or an unpaid provision.
    Neither input is inferred from a generic20% domestic rate.
    """
    if same_income_and_period_verified is not True:
        raise ValueError('Shared income basis, credit eligibility and offset period must be verified')
    limit, ordinary, top_up = map(amount, (
        vietnam_tax_limit, established_ordinary_credit, allocated_paid_top_up_tax))
    if ordinary > limit:
        raise ValueError('Established ordinary credit exceeds the shared Vietnam tax limit')
    with localcontext() as context:
        context.prec = 40
        remaining = limit - ordinary
        additional = min(top_up, remaining)
        total = ordinary + additional
        return {
            'policy_version': 'vn-additional-top-up-cap-2026-11-18',
            'currency': 'VND',
            'vietnam_tax_limit': limit,
            'established_ordinary_credit': ordinary,
            'remaining_limit_before_top_up': remaining,
            'allocated_paid_top_up_tax': top_up,
            'additional_top_up_credit': additional,
            'combined_credit': total,
            'top_up_exceeding_limit': top_up - additional,
            'vietnam_tax_after_combined_credit': limit - total,
            'stage': 'established_basis_cap_before_assessment_rounding',
            'sources': [{
                'title': 'Decree320/2025/ND-CP Article12(2)(c)',
                'url': 'https://congbao.cdnchinhphu.vn/CongBaoCP/CongBao/2025/12/46840/60373-1-1737-1738.pdf',
                'sha256': '0f5db5c51b79643276e5d5eb03fd636fbdac8ea043018f79cf50ba9d8d6d8de6',
                'pages': [48],
            }, {
                'title': 'Circular89/2026/TT-BTC annex03-4/TNDN sectionsA/B',
                'url': 'https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/7/89-btc.signed.pdf',
                'sha256': '952c45ffc0f10bfc176bd9ae6b3d204fd3a034294ee270278957b9c11e1471dc',
                'pages': [284, 285],
            }],
        }
