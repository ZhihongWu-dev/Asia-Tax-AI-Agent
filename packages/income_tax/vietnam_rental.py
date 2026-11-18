"""Annual 2026 resident domestic property rental, excluding accommodation."""
from decimal import Decimal, localcontext

from .arithmetic import amount, ZERO
from .vietnam_sources import sources_for


def resident_property_rental_tax(*, tax_year, resident, contracts,
        all_annual_rental_revenue, rental_only_scope_verified,
        annual_recognition_and_all_contracts_verified):
    if type(tax_year) is not int or tax_year != 2026 or resident is not True:
        raise ValueError('Only resident calendar-year 2026 rental is supported')
    if rental_only_scope_verified is not True or annual_recognition_and_all_contracts_verified is not True:
        raise ValueError('Verify all annual domestic property rent, excluding accommodation and other business')
    if not isinstance(contracts, (list, tuple)) or not 1 <= len(contracts) <= 100:
        raise ValueError('Supply one to 100 rental contracts')
    annual = amount(all_annual_rental_revenue)
    with localcontext() as ctx:
        ctx.prec = 40
        rows = []
        identifiers = set()
        for contract in contracts:
            if not isinstance(contract, dict) or set(contract) != {
                    'contract_id', 'revenue', 'allocated_revenue_deduction',
                    'prepaid_tax', 'tenant_files', 'filing_and_allocation_verified'}:
                raise ValueError('Each contract requires its complete filing and allocation basis')
            identifier = contract['contract_id']
            if not isinstance(identifier, str) or not identifier.strip() or len(identifier) > 120:
                raise ValueError('Each contract requires an identifier')
            identifier = identifier.strip()
            if identifier in identifiers:
                raise ValueError('Contract identifiers must be unique')
            identifiers.add(identifier)
            if type(contract['tenant_files']) is not bool or contract['filing_and_allocation_verified'] is not True:
                raise ValueError('Verify filing responsibility, contractual allocation and actual payments')
            revenue = amount(contract['revenue'])
            deduction = amount(contract['allocated_revenue_deduction'])
            paid = amount(contract['prepaid_tax'])
            if deduction > revenue:
                raise ValueError('Contract deduction cannot exceed its annual revenue')
            rows.append(dict(contract_id=identifier, revenue=revenue,
                allocated_revenue_deduction=deduction, prepaid_tax=paid,
                tenant_files=contract['tenant_files']))
        if sum((r['revenue'] for r in rows), ZERO) != annual:
            raise ValueError('Contracts must reconcile to all annual rental revenue')
        allocated = sum((r['allocated_revenue_deduction'] for r in rows), ZERO)
        allowance = min(annual, Decimal('1000000000'))
        if allocated > allowance:
            raise ValueError('Contracts share one VND 1bn annual rental deduction')
        relief_rate = Decimal('.30') if annual <= Decimal('10000000000') else ZERO
        for row in rows:
            base = ZERO if annual <= Decimal('1000000000') else row['revenue'] - row['allocated_revenue_deduction']
            before = base * Decimal('.05')
            reduction = before * relief_rate
            row.update(taxable_revenue=base, tax_before_relief=before,
                annual_reduction=reduction, final_tax=before-reduction,
                balance_due=before-reduction-row['prepaid_tax'])
        total = lambda key: sum((r[key] for r in rows), ZERO)
        return dict(policy_version='vn-resident-property-rental-2026-2026-11-18',
            currency='VND', tax_year=tax_year, contracts=rows,
            annual_rental_revenue=annual, allocated_revenue_deduction=allocated,
            unused_revenue_deduction=allowance-allocated, rate=Decimal('.05'),
            reduction_rate=relief_rate, tax_before_relief=total('tax_before_relief'),
            annual_reduction=total('annual_reduction'), final_tax=total('final_tax'),
            prepaid_tax=total('prepaid_tax'), balance_due=total('balance_due'),
            calculation_stage='before_assessment_rounding',
            scope='resident_domestic_property_rental_only_excluding_accommodation_and_VAT',
            sources=sources_for('property_rental'))
