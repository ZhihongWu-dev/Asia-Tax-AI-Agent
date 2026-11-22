"""Section50(5) source income reconciliation using an established credit rate.

The caller must establish the Section50(3)/(6) rate separately. In particular,
this function must not infer an annual average rate from net income after the
very deduction it calculates. This is not an annual profits-tax assessment.
"""
from decimal import Decimal, localcontext
from fractions import Fraction
from .arithmetic import amount


def reconcile_excess_tax(*, source_income_before_foreign_tax_deduction,
                         eligible_foreign_tax, established_credit_rate,
                         statutory_rate_and_deduction_eligibility_verified):
    if statutory_rate_and_deduction_eligibility_verified is not True:
        raise ValueError('Statutory credit rate and excess-tax deduction eligibility require verification')
    income, foreign, rate = map(amount, (source_income_before_foreign_tax_deduction,
        eligible_foreign_tax, established_credit_rate))
    if rate >= 1:
        raise ValueError('Established credit rate must be less than one')
    if foreign > income:
        raise ValueError('Foreign tax exceeding source income requires separate loss and eligibility review')
    # C = min(F, r * (I - (F - C))). Solve exactly; iterative rounded
    # calculations can create false residual taxes or non-convergence.
    i, f, r = map(Fraction, (income, foreign, rate))
    credit = min(f, r * (i-f) / (1-r))
    deduction = f-credit
    basis = i-deduction
    values = dict(foreign_tax_credit=credit, excess_foreign_tax_deduction=deduction,
                  source_income_after_foreign_tax_deduction=basis,
                  tax_on_reconciled_source=basis*r,
                  source_tax_after_credit=basis*r-credit)
    with localcontext() as context:
        context.prec = 40
        result = {key: Decimal(value.numerator)/Decimal(value.denominator)
                  for key,value in values.items()}
    result.update(exact_amounts={key:dict(numerator=str(value.numerator),
        denominator=str(value.denominator)) for key,value in values.items()},
        stage='section50_source_basis_before_annual_settlement_and_rounding',
        policy_version='hk-section50-excess-tax-component-20261122',
        sources=[dict(doc_id='hk.dipn.44',title='IRD DIPN44: Example5, notes1 and2',
            url='https://www.ird.gov.hk/eng/pdf/dipn44.pdf',
            file='database/raw/hk/hk.dipn.44.pdf',
            sha256='b894ef31bbeb34e597b0c5d12004dde45718638e5e841c14b1510d02bb705c43',
            locator='Paragraph131, Example5: historical flat-rate illustration')])
    return result
