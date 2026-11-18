"""Vietnam foreign-income credit arithmetic on separately established bases.

Decree320 Article12(2)(c) caps paragraph(b) credit plus allocated top-up credit.
This helper does not determine treaty entitlements, the top-up allocation itself,
or the relevant declaration/payment period. It preserves the established ordinary
credit and limits the additional top-up claim to remaining capacity. Callers must
not use it to pool unrelated projects or transfer credits between tax periods.
"""
from decimal import Decimal, localcontext

from .arithmetic import amount


def dividend_underlying_credit(*, source_country, qualifying_holding_percent,
        dividend_before_withholding, distributing_profit_after_tax,
        corporate_tax_paid_on_profit, vietnam_tax_limit,
        corporate_recipient_and_pool_verified, treaty_and_vietnam_basis_verified):
    """Cap the attributed underlying component without rounding it first.

    The limit must refer to the Vietnamese tax attributable to this dividend
    and its legally established inclusion basis. No gross-up is inferred here.
    This returns only underlying credit; it does not independently grant a second
    cap to any other credit claimed on the same income.
    """
    if treaty_and_vietnam_basis_verified is not True:
        raise ValueError('Treaty entitlement and Vietnam same-income tax basis must be verified')
    limit = amount(vietnam_tax_limit)
    attribution = dividend_underlying_tax(source_country=source_country,
        qualifying_holding_percent=qualifying_holding_percent,
        dividend_before_withholding=dividend_before_withholding,
        distributing_profit_after_tax=distributing_profit_after_tax,
        corporate_tax_paid_on_profit=corporate_tax_paid_on_profit,
        corporate_recipient_and_pool_verified=corporate_recipient_and_pool_verified)
    if attribution['dividend_before_withholding'] == 0 and limit != 0:
        raise ValueError('Zero dividend cannot have a positive same-income tax limit')
    # Attribution is already validated Decimal arithmetic. Do not pass this
    # internal repeating fraction through the six-place external-input parser.
    with localcontext() as context:
        context.prec = 40
        underlying = attribution['attributable_underlying_tax']
        allowed = min(underlying, limit)
        return dict(attribution,
            policy_version='vn-dividend-underlying-credit-2026-11-18',
            vietnam_tax_limit=limit, allowed_underlying_credit=allowed,
            underlying_tax_exceeding_limit=underlying-allowed,
            remaining_same_income_credit_limit=limit-allowed,
            stage='underlying_credit_before_assessment_rounding')


def dividend_underlying_tax(*, source_country, qualifying_holding_percent,
        dividend_before_withholding, distributing_profit_after_tax,
        corporate_tax_paid_on_profit, corporate_recipient_and_pool_verified):
    """Attribute a documented homogeneous profit pool's tax to one dividend.

    Hong Kong Article22(3) tests control of shares; Singapore Article24(2)(a)
    tests share-capital ownership, directly or indirectly. The supplied holding
    must use the applicable treaty measure, not automatically voting power.
    Dividend is before shareholder withholding but after distributing-company
    tax. The pool must exclude capital distributions and unrelated years/taxes.
    Different-rate pools must be attributed separately. This is the underlying
    tax component, still subject to treaty eligibility and the Vietnamese cap.
    """
    if source_country not in ('hk', 'sg'):
        raise ValueError('Reviewed underlying-dividend routes are Hong Kong and Singapore')
    if corporate_recipient_and_pool_verified is not True:
        raise ValueError('Corporate recipient, treaty holding measure and matched profit pool must be verified')
    holding, dividend, profit, tax = map(amount, (qualifying_holding_percent,
        dividend_before_withholding, distributing_profit_after_tax, corporate_tax_paid_on_profit))
    if holding < 10 or holding > 100:
        raise ValueError('Treaty qualifying holding must be between10 and100 percent')
    if profit == 0 or dividend > profit:
        raise ValueError('Dividend must belong to a positive after-tax profit pool and not exceed it')
    with localcontext() as context:
        context.prec = 40
        attributed = dividend * tax / profit
        return dict(policy_version='vn-dividend-underlying-attribution-2026-11-18',
            source_country=source_country, residence_country='vn',
            qualifying_holding_percent=holding, dividend_before_withholding=dividend,
            distributing_profit_after_tax=profit, corporate_tax_paid_on_profit=tax,
            attributable_underlying_tax=attributed,
            stage='underlying_component_before_vietnam_credit_cap',
            sources=[dict(title=('Hong Kong–Vietnam treaty Article22(3)' if source_country=='hk'
                                else 'Singapore–Vietnam treaty Article24(2)(a)'),
                url=('https://www.elegislation.gov.hk/hk/cap112BE!en.rtf' if source_country=='hk'
                     else 'https://www.iras.gov.sg/media/docs/default-source/dtas/singapore-vietnam-dta-(ratified)(mli)(01092023).pdf'))])


def singapore_interest_royalty_credit(gross_income, *, income_type,
        eligible_singapore_tax_paid, vietnam_tax_limit,
        article11_or12_and_treaty_entitlement_verified):
    """Article24(4)(a) minimum deemed-tax measure for a Vietnam resident.

    Applies only to Singapore-source Article11/12 income, not dividends. The
    supplied tax must be independently eligible under Article24(2)(a), including
    treaty source-tax limits. This does not determine Article24(2)(b) incentive
    sparing or add a separate10% amount to paid tax.
    """
    if income_type not in ('interest', 'royalty'):
        raise ValueError('Singapore Article24(4)(a) covers interest or royalty income only')
    if article11_or12_and_treaty_entitlement_verified is not True:
        raise ValueError('Article11/12 classification and treaty entitlement must be verified')
    gross, paid, limit = map(amount, (gross_income, eligible_singapore_tax_paid, vietnam_tax_limit))
    if gross == 0 and (paid != 0 or limit != 0):
        raise ValueError('Zero income cannot have positive related tax or a tax limit')
    with localcontext() as context:
        context.prec = 40
        deemed_floor = gross * Decimal('0.10')
        credit_basis = max(paid, deemed_floor)
        allowed = min(credit_basis, limit)
        return dict(policy_version='vn-sg-interest-royalty-credit-2026-11-18',
            residence_country='vn', source_country='sg', income_type=income_type,
            gross_income=gross, eligible_singapore_tax_paid=paid,
            deemed_tax_floor=deemed_floor, deemed_floor_applied=paid < deemed_floor,
            credit_basis=credit_basis, vietnam_tax_limit=limit,
            allowed_tax_credit=allowed, credit_basis_exceeding_limit=credit_basis-allowed,
            vietnam_tax_after_credit=limit-allowed,
            stage='treaty_credit_before_assessment_rounding',
            sources=[dict(title='Singapore–Vietnam treaty Article24(2)(a)/(4)(a)',
                url='https://www.iras.gov.sg/media/docs/default-source/dtas/singapore-vietnam-dta-(ratified)(mli)(01092023).pdf',
                pages=[13, 14],
                sha256='948b2597f2996af06d048be2eb1a74ca1772e7d110b31a969985fa3dbdeca503')])


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
                'file': 'database/raw/vn/vn.gazette1737-1738.2025.vi.pdf',
                'url': 'https://congbao.cdnchinhphu.vn/CongBaoCP/CongBao/2025/12/46840/60373-1-1737-1738.pdf',
                'sha256': '0f5db5c51b79643276e5d5eb03fd636fbdac8ea043018f79cf50ba9d8d6d8de6',
                'pages': [48],
            }, {
                'title': 'Circular89/2026/TT-BTC annex03-4/TNDN sectionsA/B',
                'file': 'database/raw/vn/vn.circular89.2026.vi.pdf',
                'url': 'https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/7/89-btc.signed.pdf',
                'sha256': '952c45ffc0f10bfc176bd9ae6b3d204fd3a034294ee270278957b9c11e1471dc',
                'pages': [284, 285],
            }],
        }
