"""Vietnam ordinary personal transfer calculations; deferred events are separate."""
from datetime import date
from decimal import Decimal, localcontext
from .arithmetic import amount, ZERO
from .vietnam_sources import sources_for


def personal_transfer_tax(transfer_value, *, recognition_date, resident, asset_kind,
        purchase_cost, transfer_costs, cost_basis_established, ordinary_sale_confirmed,
        classification_valuation_and_scope_verified, prepaid_tax):
    """Verified statutory value excludes installment interest and reflects valuation rules.

    Joint-stock shares remain securities even if unlisted. Whole-business sales
    linked to property, deferred contributions/realisations, derivatives, treaty
    relief and exemptions require their own assessment and cannot use this entry.
    A nonresident's capital interest must be within statutory Vietnamese scope.
    """
    if type(recognition_date) is not date or not date(2026,7,1) <= recognition_date <= date(2026,12,31):
        raise ValueError('Requires a verified recognition date in July-December 2026')
    if type(resident) is not bool or type(cost_basis_established) is not bool:
        raise ValueError('Residence and cost-basis status must be explicit')
    if ordinary_sale_confirmed is not True or classification_valuation_and_scope_verified is not True:
        raise ValueError('Ordinary taxable sale, classification, valuation and scope must be verified')
    if asset_kind not in ('capital_interest','security'):
        raise ValueError('Unsupported transfer classification')
    proceeds, prepaid = amount(transfer_value), amount(prepaid_tax)
    with localcontext() as ctx:
        ctx.prec = 40
        if asset_kind == 'security':
            if purchase_cost is not None or transfer_costs is not None or cost_basis_established:
                raise ValueError('Securities use gross proceeds; cost deductions are inapplicable')
            base, rate, method = proceeds, Decimal('.001'), 'securities_proceeds'
        elif cost_basis_established:
            cost, expenses = amount(purchase_cost), amount(transfer_costs)
            base, rate, method = max(ZERO,proceeds-cost-expenses), Decimal('.20'), 'capital_gain'
        else:
            if purchase_cost is not None or transfer_costs is not None:
                raise ValueError('Unknown-cost method cannot accept partial or assumed deductions')
            base, rate, method = proceeds, Decimal('.02'), 'capital_proceeds_unknown_cost'
        tax = base*rate
        return dict(policy_version='vn-personal-transfer-2026-2026-11-17',currency='VND',
            recognition_date=recognition_date.isoformat(),resident=resident,asset_kind=asset_kind,
            transfer_value=proceeds,taxable_base=base,rate=rate,method=method,
            final_tax=tax,prepaid_tax=prepaid,balance_due=tax-prepaid,
            calculation_stage='before_assessment_rounding',sources=sources_for('personal_transfer'),
            legal_basis=('vn.law.pit2026.vi#'+('13' if resident else '23'),
                         'vn.decree253.2026.vi#10','vn.decree253.2026.vi#53','vn.decree253.2026.vi#54'))
