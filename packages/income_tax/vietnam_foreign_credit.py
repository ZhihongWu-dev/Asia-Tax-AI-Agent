"""Vietnam foreign-income credit arithmetic on separately established bases.

Decree320 Article12(2)(c) caps paragraph(b) credit plus allocated top-up credit.
This helper does not determine treaty entitlements, the top-up allocation itself,
or the relevant declaration/payment period. It preserves the established ordinary
credit and limits the additional top-up claim to remaining capacity. Callers must
not use it to pool unrelated projects or transfer credits between tax periods.
"""
from decimal import Decimal, localcontext

from .arithmetic import amount


def indonesia_deemed_credit(gross_income, *, income_type, vietnam_tax_limit,
                            paragraph2_and_treaty_entitlement_verified):
    """Vietnam resident credit on Indonesian income under treaty Article23(4).

    Requires Article10(2),11(2) or12(2) treatment, including beneficial ownership
    and any applicable MLI entitlement tests. Effectively connected PE income
    belongs to a different route. Deemed tax replaces the actual-paid measure;
    it is not an additional15% credit on top of withholding or underlying tax.
    The Vietnamese tax on the same income is established independently.
    """
    if income_type not in ('dividend', 'interest', 'royalty'):
        raise ValueError('Article23(4) covers dividend, interest or royalty income only')
    if paragraph2_and_treaty_entitlement_verified is not True:
        raise ValueError('Relevant paragraph2 treatment and treaty entitlement must be verified')
    gross, limit = map(amount, (gross_income, vietnam_tax_limit))
    if gross == 0 and limit != 0:
        raise ValueError('Zero income cannot have a positive same-income tax limit')
    with localcontext() as context:
        context.prec = 40
        deemed = gross * Decimal('0.15')
        credit = min(deemed, limit)
        return dict(policy_version='vn-id-deemed-credit-2026-11-18',
            residence_country='vn', source_country='id', income_type=income_type,
            gross_income=gross, deemed_paid_tax=deemed, vietnam_tax_limit=limit,
            allowed_tax_credit=credit, deemed_tax_exceeding_limit=deemed-credit,
            vietnam_tax_after_credit=limit-credit,
            stage='treaty_credit_before_assessment_rounding',
            sources=[dict(title='Indonesia–Vietnam treaty Article23(1)/(4)',
                url='https://pajak.go.id/en/p3b/vietnam'),
                dict(title='Official MLI synthesised text, Article23',
                url='https://www.pajak.go.id/sites/default/files/2025-06/Tax%20Treaty%20Vietnam%20%28Modified%20by%20MLI%29%20-%20EN.pdf',
                pages=[13])])


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
