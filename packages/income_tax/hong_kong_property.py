"""Separate property assessment for solely owned Hong Kong rental properties."""
from copy import deepcopy
from decimal import Decimal, localcontext
from .arithmetic import ZERO, amount
from .hong_kong import SOURCES, check_year


def property_tax(case, *, assessment_year, properties,
                 sole_ownership_and_separate_assessment_verified,
                 consideration_and_deductions_verified, prepaid_final_tax):
    check_year(assessment_year)
    if (sole_ownership_and_separate_assessment_verified is not True or
            consideration_and_deductions_verified is not True):
        raise ValueError('Property ownership, separate assessment, consideration and deductions require verification')
    if case.subject != 'individual' or case.carried_losses != 0 or any(
            i.category != 'rental' or i.source_jurisdiction != 'hk' or
            i.foreign_tax_paid not in (None, 0) for i in case.incomes):
        raise ValueError('Separate Hong Kong individual rental income without business losses or foreign credits required')
    indices = [p['income_index'] for p in properties]
    if sorted(indices) != list(range(len(case.incomes))):
        raise ValueError('Each saved rental property must have exactly one deduction row')
    prepaid = amount(prepaid_final_tax)
    with localcontext() as ctx:
        ctx.prec = 40
        rows = []
        for p in sorted(properties, key=lambda p: p['income_index']):
            item = case.incomes[p['income_index']]
            bad, rates = map(amount, (p['irrecoverable_rent'], p['owner_rates_paid']))
            if bad + rates > item.gross_amount:
                raise ValueError('Deductions exceed current property consideration; prior-year irrecoverable-rent relief requires separate assessment')
            adjusted = item.gross_amount - bad - rates
            allowance = adjusted * Decimal('.20')
            nav = adjusted - allowance
            rows.append(dict(income_index=p['income_index'], gross_consideration=item.gross_amount,
                irrecoverable_rent=bad, owner_rates_paid=rates, statutory_allowance=allowance,
                net_assessable_value=nav, property_tax=nav * Decimal('.15')))
        claimed = sum((r['irrecoverable_rent'] + r['owner_rates_paid'] for r in rows), ZERO)
        if case.claimed_deductions != claimed:
            raise ValueError('Saved deductions must equal irrecoverable rent plus owner rates; exclude the automatic 20% allowance')
        liability = sum((r['property_tax'] for r in rows), ZERO)
        return dict(policy_version='hk-property-2025-26-20261119', assessment_year=assessment_year,
            currency='HKD', properties=rows,
            net_assessable_value=sum((r['net_assessable_value'] for r in rows), ZERO),
            statutory_allowance=sum((r['statutory_allowance'] for r in rows), ZERO),
            final_tax=liability, prepaid_final_tax=prepaid, balance_due=liability-prepaid,
            sources=deepcopy([s for s in SOURCES if s['doc_id']=='hk.ird.property-notes-20261119']),
            stage='separate_property_before_assessment_rounding')
