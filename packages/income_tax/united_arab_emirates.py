"""UAE calendar-2026 ordinary CT arithmetic on an established taxable base.

Natural-person business scope is separate from tax-base calculation. Free-zone,
exempt-person, tax-group, minimum-tax and relief elections require other policies.
"""
from copy import deepcopy
from decimal import Decimal, localcontext
import json
from pathlib import Path
from .arithmetic import ZERO, amount

POLICY_VERSION = 'ae-calendar-2026-2026-11-16'
SOURCES = json.loads(Path(__file__).with_name('ae_2026_sources.json').read_text(encoding='utf-8'))['sources']

BASIS_SOURCES = json.loads(Path(__file__).with_name('ae_basis_sources.json').read_text(encoding='utf-8'))['sources']

def _period(tax_year):
    if type(tax_year) is not int or tax_year != 2026:
        raise ValueError('This policy covers calendar 2026 only')


def natural_person_scope(business_turnover, *, tax_year, excluded_wages,
                         excluded_personal_investment, excluded_real_estate_investment,
                         activity_classification_confirmed):
    """Aggregate all in-scope UAE businesses, including attributable foreign sales.

Excluded categories must satisfy the statutory definitions, not merely an input
label. This result determines CT scope only; it is not a computed tax liability.
"""
    _period(tax_year)
    if activity_classification_confirmed is not True:
        raise ValueError('UAE activity scope and statutory exclusions must be confirmed')
    turnover, wages, investments, real_estate = map(amount, (
        business_turnover, excluded_wages, excluded_personal_investment,
        excluded_real_estate_investment))
    return {'policy_version': POLICY_VERSION, 'tax_year': tax_year, 'currency': 'AED',
            'business_turnover': turnover, 'excluded_wages': wages,
            'excluded_personal_investment': investments,
            'excluded_real_estate_investment': real_estate,
            'within_corporate_tax_scope': turnover > Decimal('1000000'),
            'sources': deepcopy(SOURCES[1:3]), 'stage': 'natural_person_scope_only'}


def ordinary_corporate_tax(taxable_income, *, tax_year, subject_type,
                          ordinary_regime_confirmed, no_relief_elected_confirmed,
                          allowed_foreign_tax_credit, prepaid_tax,
                          natural_person_business_turnover=None):
    """Taxable income is after verified adjustments/loss relief, never turnover.

Confirmation requires an ordinary standalone taxable person outside exempt,
qualifying-free-zone and domestic-minimum-top-up regimes. No small-business
relief election is inferred. Foreign credit must already be limited per source.
Natural persons must separately verify business classification and aggregation.
Returns exact amounts before assessment rounding.
"""
    _period(tax_year)
    if subject_type not in ('company', 'individual'):
        raise ValueError('Unsupported subject type')
    if ordinary_regime_confirmed is not True or no_relief_elected_confirmed is not True:
        raise ValueError('Ordinary regime and absence of relief election must be confirmed')
    if subject_type == 'individual':
        if natural_person_business_turnover is None or amount(natural_person_business_turnover) <= Decimal('1000000'):
            raise ValueError('Natural person must have confirmed in-scope business turnover above AED 1 million')
    elif natural_person_business_turnover is not None:
        raise ValueError('Natural-person turnover is not applicable to a company')
    base, credit, prepaid = map(amount, (taxable_income, allowed_foreign_tax_credit, prepaid_tax))
    with localcontext() as ctx:
        ctx.prec = 40
        taxed = max(ZERO, base - Decimal('375000'))
        gross = taxed * Decimal('.09')
        if credit > gross:
            raise ValueError('Allowed foreign tax credit cannot exceed gross CT')
        liability = gross - credit
        return {'policy_version': POLICY_VERSION, 'tax_year': tax_year, 'currency': 'AED',
                'subject_type': subject_type, 'taxable_income': base,
                'zero_rate_income': min(base, Decimal('375000')), 'standard_rate_income': taxed,
                'gross_tax': gross, 'allowed_foreign_tax_credit': credit,
                'final_tax': liability, 'prepaid_tax': prepaid, 'balance_due': liability - prepaid,
                'sources': deepcopy(SOURCES), 'stage': 'ordinary_ct_before_assessment_rounding'}
