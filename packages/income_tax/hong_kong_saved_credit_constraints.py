"""Saved receipts -> eligible foreign tax -> source/aggregate constraints.

This workpaper integration does not choose a statutory annual rate, tax
schedule, allocation method, rounding rule or assessment policy. Those are
independently established inputs. An unresolved allocation stays unresolved;
the result must not be presented as a final annual assessment.
"""
from decimal import Decimal, localcontext
from fractions import Fraction
from pydantic import StrictBool
from packages.contracts.income_tax import IncomeTaxCase
from .hong_kong_foreign_reconciliation import FactsWorkpaper, reconcile_facts
from .hong_kong_foreign_credit import calculate_eligibility
from .hong_kong_credit_basis import _reconcile_source_caps


class Workpaper(FactsWorkpaper):
    hong_kong_resident_mne_verified: StrictBool
    source_tax_attribution_and_gross_up_verified: StrictBool
    payment_fx_and_claim_evidence_verified: StrictBool


def _render(value, *, exact):
    if isinstance(value, Fraction):
        if exact:
            return dict(numerator=str(value.numerator),denominator=str(value.denominator))
        return Decimal(value.numerator)/Decimal(value.denominator)
    if isinstance(value, dict):
        return {key:_render(item,exact=exact) for key,item in value.items()}
    if isinstance(value, list):
        return [_render(item,exact=exact) for item in value]
    return value


def reconcile_constraints(case, workpaper, *, established_credit_rate, tax_bands,
                          tax_reduction, annual_rate_schedule_and_deduction_eligibility_verified,
                          allocations=None):
    if annual_rate_schedule_and_deduction_eligibility_verified is not True:
        raise ValueError('Annual rate, tax schedule and excess-tax deduction treatment require verification')
    if type(established_credit_rate) is not Fraction or not 0 <= established_credit_rate < 1:
        raise ValueError('Established statutory rate requires an exact fraction below one')
    case = IncomeTaxCase.model_validate(case)
    p = Workpaper.model_validate(workpaper)
    saved = reconcile_facts(case, {key:getattr(p,key) for key in FactsWorkpaper.model_fields})
    eligibility = calculate_eligibility(dict(sources=saved['foreign_credit_sources'],
        hong_kong_resident_mne_verified=p.hong_kong_resident_mne_verified,
        source_tax_attribution_and_gross_up_verified=p.source_tax_attribution_and_gross_up_verified,
        payment_fx_and_claim_evidence_verified=p.payment_fx_and_claim_evidence_verified))
    eligible_by_id = {row['source_id']:row for row in eligibility['source_eligibility']}
    claims_by_id = {group.source_id.strip():group.foreign_credit for group in p.groups}
    domestic = Fraction(0)
    sources = []
    for row in saved['source_reconciliation']:
        identifier = row['source_id']
        income = Fraction(row['source_basis_before_excess_foreign_tax_deduction'])
        if row['country'] == 'hk':
            domestic += income
        elif identifier in eligible_by_id:
            claim = claims_by_id[identifier]
            # Eligibility already distinguishes attributed underlying tax from
            # direct payments and prevents bilateral/unilateral duplication.
            underlying = (Fraction(claim.underlying_tax_in_bilateral_claim)
                          + Fraction(claim.underlying_unilateral_eligible_tax))
            if Fraction(row['underlying_tax_gross_up']) != underlying:
                raise ValueError('Underlying income gross-up must reconcile tax taken into account in the claim')
            sources.append(dict(source_id=identifier, income=income,
                foreign_tax=Fraction(eligible_by_id[identifier]['total_eligible_tax']),
                rate=established_credit_rate))
        elif income:
            raise ValueError('Unclaimed foreign source must be wholly excluded')
    constraints = _reconcile_source_caps(domestic_income=domestic,sources=sources,
        bands=tax_bands,reduction=tax_reduction,allocations=allocations)
    # Keep exact ratios alongside display decimals; consumers must not feed
    # rounded display amounts back into source allocations or tax bases.
    with localcontext() as context:
        context.prec = 40
        return dict(policy_version='hk-saved-credit-constraints-20261122',currency='HKD',
            saved_receipt_reconciliation=saved['source_reconciliation'],
            source_eligibility=eligibility['source_eligibility'],
            established_credit_rate=_render(established_credit_rate,exact=True),
            constraints=_render(constraints,exact=False),
            exact_constraints=_render(constraints,exact=True),
            sources=eligibility['sources'],
            stage='saved_fsie_constraints_before_annual_policy_allocation_and_rounding')
