"""2025/26 ordinary corporate FSIE workpaper before assessment completion.

Section50(6) rate income excludes underlying gross-up and the excess-tax
deduction. Applying Section100's reduction to tax on that rate income is a
statutory interpretation corroborated by historical teaching examples, not
a current IRD ruling on these cases. Require explicit verification of the
annual basis and ordering. The saved API result is a workpaper, not a final
assessment, including when source allocation is unique or supplied.
"""
from copy import deepcopy
from datetime import date, timedelta
from decimal import localcontext
from fractions import Fraction as F
from packages.contracts.income_tax import IncomeTaxCase
from .hong_kong import SOURCES, PROFITS_BASIS_SOURCES
from .hong_kong_foreign_reconciliation import FactsWorkpaper, reconcile_facts
from .hong_kong_saved_credit_constraints import Workpaper, reconcile_constraints, _render


def prepare(case, workpaper, *, two_tier_eligible,
            ordinary_annual_basis_and_reduction_ordering_verified,
            ongoing_business_unchanged_accounting_year_verified, allocations=None):
    if (type(two_tier_eligible) is not bool
            or ordinary_annual_basis_and_reduction_ordering_verified is not True):
        raise ValueError('Ordinary annual basis, reduction ordering and two-tier eligibility require verification')
    case = IncomeTaxCase.model_validate(case)
    if ongoing_business_unchanged_accounting_year_verified is not True:
        raise ValueError('Ongoing business and unchanged annual accounting period require verification')
    if not date(2025,4,1) <= case.period_end <= date(2026,3,31):
        raise ValueError('Annual accounts must end within assessment year2025/26')
    # Neither possible end year is leap, so replacing its year cannot produce
    # an invalid29February. Commencement/cessation/changed-year periods remain
    # subject to separate statutory basis-period treatment.
    expected_start=case.period_end.replace(year=case.period_end.year-1)+timedelta(days=1)
    if case.period_start != expected_start:
        raise ValueError('Ordinary annual accounts require a full year ending in the assessment year')
    p = Workpaper.model_validate(workpaper)
    saved = reconcile_facts(case,{key:getattr(p,key) for key in FactsWorkpaper.model_fields})
    rate_income = F(0)
    underlying = F(0)
    for row in saved['source_reconciliation']:
        gross_up = F(row['underlying_tax_gross_up'])
        before = F(row['source_basis_before_excess_foreign_tax_deduction'])
        if before < gross_up:
            raise ValueError('Source loss before underlying gross-up needs separate rate-basis review')
        underlying += gross_up
        rate_income += before-gross_up
    lower = min(rate_income,F(2000000)) if two_tier_eligible else F(0)
    gross_tax = lower*F(825,10000)+(rate_income-lower)*F(165,1000)
    reduction = min(gross_tax,F(3000))
    numerator = gross_tax-reduction
    # With zero rate income there is no tax on that income. Do not divide by
    # zero or use underlying gross-up as a replacement denominator.
    rate = numerator/rate_income if rate_income else F(0)
    bands = [(F(2000000),F(825,10000)),(None,F(165,1000))] if two_tier_eligible else [(None,F(165,1000))]
    result = reconcile_constraints(case,p,established_credit_rate=rate,tax_bands=bands,
        tax_reduction=F(3000),annual_rate_schedule_and_deduction_eligibility_verified=True,
        allocations=allocations)
    basis = dict(income_before_excess_tax_deduction=F(saved['total_basis_before_excess_foreign_tax_deduction']),
        underlying_tax_gross_up_excluded=underlying,rate_denominator=rate_income,
        gross_tax_on_rate_basis=gross_tax,tax_reduction_on_rate_basis=reduction,
        tax_before_credit_on_rate_basis=numerator,average_credit_rate=rate)
    with localcontext() as context:
        context.prec=40
        result['annual_rate_basis']=_render(basis,exact=False)
        result['exact_annual_rate_basis']=_render(basis,exact=True)
    result['assessment_year']='2025/26'
    result['basis_period']=dict(start=case.period_start.isoformat(),end=case.period_end.isoformat(),
        ongoing_business_unchanged_accounting_year_verified=True)
    result['two_tier_eligible']=two_tier_eligible
    result['policy_version']='hk-ordinary-fsie-workpaper-2025-26-20261122'
    result['result_kind']='workpaper'
    result['review_status']=('source_allocation_required' if result['constraints']['allocation_required']
                             else 'assessment_review_required')
    result['assessment_rounding_applied']=False
    result['stage']='ordinary_2025_26_fsie_workpaper_before_allocation_review_and_assessment_rounding'
    result['sources'].extend(deepcopy([SOURCES[1],SOURCES[2],PROFITS_BASIS_SOURCES[0]]))
    for source in result['sources']:
        if source['doc_id']=='hk.cap112':
            source['locator'] += '; Sections50(3)-(6),100: rate basis, source/total caps, excess deduction and reduction'
        elif source['doc_id']=='hk.ird.corporation-notes.20261119':
            source['locator']='B(5): return amounts exclude cents; C2(1)-(4): ordinary annual accounts and special basis periods'
    return result
