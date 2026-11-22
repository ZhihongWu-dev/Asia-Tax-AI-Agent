"""Section50(5) source income reconciliation using an established credit rate.

The caller must establish the Section50(3)/(6) rate separately. In particular,
this function must not infer an annual average rate from net income after the
very deduction it calculates. This is not an annual profits-tax assessment.
"""
from decimal import Decimal, localcontext
from fractions import Fraction
from .arithmetic import amount


def _reconcile_source_caps(*, domestic_income, sources, bands, reduction, allocations=None):
    """Join established source limits to the aggregate-cap arithmetic.

    Internal exact arithmetic only: the caller establishes each source's rate,
    eligible tax and deduction entitlement, plus the annual schedule. A binding
    total cap can leave multiple feasible source allocations. Return their
    intervals instead of inventing a statutory priority or pro-rata election.
    Explicit allocations must cover every source and reconcile exactly.
    """
    if type(domestic_income) is not Fraction or domestic_income < 0:
        raise ValueError('Domestic income must be a nonnegative exact fraction')
    sources = tuple(sources)
    if not 1 <= len(sources) <= 200:
        raise ValueError('Between one and 200 established sources required')
    rows = []
    ids = set()
    for source in sources:
        if set(source) != {'source_id', 'income', 'foreign_tax', 'rate'}:
            raise ValueError('Source requires identity, income, eligible tax and established rate')
        identifier = source['source_id']
        if not isinstance(identifier, str) or not identifier.strip() or len(identifier) > 120:
            raise ValueError('Source identity must be nonempty and at most120characters')
        identifier = identifier.strip()
        if identifier in ids:
            raise ValueError('Sources require unique identities')
        ids.add(identifier)
        income, foreign, rate = (source[key] for key in ('income', 'foreign_tax', 'rate'))
        if any(type(value) is not Fraction or value < 0 for value in (income, foreign, rate)):
            raise ValueError('Source amounts and rate must be nonnegative exact fractions')
        if foreign > income or rate >= 1:
            raise ValueError('Source tax cannot exceed income and rate must be below one')
        ceiling = min(foreign, rate*(income-foreign)/(1-rate))
        rows.append(dict(source_id=identifier, income=income, foreign_tax=foreign,
                         rate=rate, source_credit_ceiling=ceiling))
    total_ceiling = sum((row['source_credit_ceiling'] for row in rows), Fraction(0))
    aggregate = _reconcile_aggregate_cap(
        income=domestic_income+sum((row['income'] for row in rows), Fraction(0)),
        foreign_tax=sum((row['foreign_tax'] for row in rows), Fraction(0)),
        source_ceiling=total_ceiling, bands=bands, reduction=reduction)
    credit = aggregate['foreign_tax_credit']
    ranges = [dict(source_id=row['source_id'], source_credit_ceiling=row['source_credit_ceiling'],
        minimum_credit=max(Fraction(0), credit-(total_ceiling-row['source_credit_ceiling'])),
        maximum_credit=min(credit, row['source_credit_ceiling'])) for row in rows]
    unique = all(row['minimum_credit'] == row['maximum_credit'] for row in ranges)
    if allocations is None and unique:
        allocations = {row['source_id']: row['minimum_credit'] for row in ranges}
    reconciled = None
    if allocations is not None:
        if not isinstance(allocations, dict) or set(allocations) != ids:
            raise ValueError('Allocations must cover exactly the reconciled source identities')
        if any(type(value) is not Fraction or value < 0 for value in allocations.values()):
            raise ValueError('Allocated credits must be nonnegative exact fractions')
        if sum(allocations.values(), Fraction(0)) != credit:
            raise ValueError('Allocated credits must equal the reconciled aggregate credit')
        reconciled = []
        for row, limits in zip(rows, ranges):
            allocated = allocations[row['source_id']]
            if not limits['minimum_credit'] <= allocated <= limits['maximum_credit']:
                raise ValueError('Allocated credit exceeds the feasible source interval')
            deduction = row['foreign_tax']-allocated
            base = row['income']-deduction
            reconciled.append(dict(source_id=row['source_id'], foreign_tax_credit=allocated,
                excess_foreign_tax_deduction=deduction,
                source_income_after_foreign_tax_deduction=base,
                tax_on_reconciled_source=base*row['rate']))
    return dict(aggregate=aggregate, source_credit_ranges=ranges,
                source_reconciliation=reconciled, allocation_required=reconciled is None,
                allocation_is_unique=unique,
                stage='established_source_and_aggregate_constraints_before_policy_and_rounding')


def _reconcile_aggregate_cap(*, income, foreign_tax, source_ceiling, bands, reduction):
    """Exact arithmetic for an independently established annual tax schedule.

    Internal integration primitive, NOT an HK policy or a rate determination.
    All scalars and band endpoints/rates must be exact Fractions. For credit C,
    deduction is F-C and tax base is I-F+C. Find the largest C in [0, ceiling]
    for which C <= max(0, schedule(I-F+C)-reduction). Each marginal rate must
    be less than one, so tax minus credit is strictly decreasing while taxable.
    No per-source allocation, assessment rounding or refund is inferred here.
    """
    scalars = (income, foreign_tax, source_ceiling, reduction)
    if any(type(value) is not Fraction or value < 0 for value in scalars):
        raise ValueError('Aggregate reconciliation requires nonnegative exact fractions')
    if foreign_tax > income or source_ceiling > foreign_tax:
        raise ValueError('Foreign tax must not exceed income and source ceiling must not exceed foreign tax')
    bands = tuple(bands)
    lower = Fraction(0)
    if not bands or bands[-1][0] is not None:
        raise ValueError('Tax schedule must end in an unbounded band')
    for index, (upper, rate) in enumerate(bands):
        if type(rate) is not Fraction or not 0 <= rate < 1:
            raise ValueError('Marginal rates must be exact fractions below one')
        if upper is None:
            if index != len(bands)-1:
                raise ValueError('Only the final band may be unbounded')
        elif type(upper) is not Fraction or upper <= lower:
            raise ValueError('Band limits must be strictly increasing exact fractions')
        if upper is not None:
            lower = upper

    def annual_tax(base):
        lower = total = Fraction(0)
        for upper, rate in bands:
            total += max(Fraction(0), (base if upper is None else min(base, upper))-lower)*rate
            if upper is not None:
                lower = upper
        return max(Fraction(0), total-reduction)

    base_without_credit = income-foreign_tax
    credit = source_ceiling
    if annual_tax(base_without_credit+credit) < credit:
        credit = Fraction(0)
        if annual_tax(base_without_credit) > 0:
            lower = tax_at_lower = Fraction(0)
            for upper, rate in bands:
                # In this band: T(I-F+C) = rate*(I-F+C-lower)
                # + tax_at_lower - reduction. Solve T = C exactly.
                root = (rate*(base_without_credit-lower)+tax_at_lower-reduction)/(1-rate)
                candidate_base = base_without_credit+root
                if (0 <= root <= source_ceiling and lower <= candidate_base
                        and (upper is None or candidate_base <= upper)):
                    credit = root
                    break
                if upper is not None:
                    tax_at_lower += (upper-lower)*rate
                    lower = upper
            else:
                raise ArithmeticError('No aggregate cap root in validated tax schedule')
    deduction = foreign_tax-credit
    base = income-deduction
    tax = annual_tax(base)
    return dict(foreign_tax_credit=credit, excess_foreign_tax_deduction=deduction,
                income_after_foreign_tax_deduction=base, tax_before_credit=tax,
                tax_after_credit=tax-credit, source_credit_reduction=source_ceiling-credit)


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
