"""Route explicit bases against a confirmed immutable case snapshot."""
from decimal import Decimal, localcontext
from pydantic import TypeAdapter
from packages.contracts.income_tax import IncomeTaxCase
from . import china, singapore, hong_kong, united_arab_emirates


def calculate(case: IncomeTaxCase, basis):
    if case.missing_for_calculation() or basis.basis_confirmed is not True:
        raise ValueError('Income facts and calculation basis require confirmation')
    policy = basis.policy
    jur = policy[:2]
    if jur != case.jurisdiction:
        raise ValueError('Policy jurisdiction differs from the saved case')
    # Current policies are annual calendar bases, except HK's stated year of assessment.
    # Non-calendar company basis periods need their own period adapter.
    periods = {'cn': ('2026-01-01', '2026-12-31'), 'ae': ('2026-01-01', '2026-12-31'),
               'sg': ('2025-01-01', '2025-12-31'), 'hk': ('2025-04-01', '2026-03-31')}
    if (case.period_start.isoformat(), case.period_end.isoformat()) != periods[jur]:
        raise ValueError('Saved basis period is not supported by this policy')
    expected = {'cn_company_2026': 'company', 'cn_comprehensive_2026': 'individual',
                'sg_company_ya2026': 'company', 'sg_resident_ya2026': 'individual',
                'hk_salaries_2025_26': 'individual'}
    if policy == 'hk_profits_2025_26':
        expected[policy] = 'company' if basis.business_form == 'corporation' else 'individual'
    if policy in expected and case.subject != expected[policy]:
        raise ValueError('Policy subject differs from the saved case')
    if policy in ('cn_comprehensive_2026', 'sg_resident_ya2026') and case.residency != 'resident':
        raise ValueError('This policy requires resident status')
    args = basis.model_dump(exclude={'policy', 'basis_explanation', 'basis_confirmed'})
    if policy == 'cn_company_2026':
        if any(i.source_jurisdiction != 'cn' for i in case.incomes):
            raise ValueError('Foreign-source corporate workflow is not verified by this policy')
        result = china.normal_company_tax(tax_year=2026, **args)
    elif policy == 'cn_comprehensive_2026':
        categories = {'employment': 'wages', 'service_remuneration': 'service_remuneration',
                      'author_remuneration': 'author_remuneration', 'royalty': 'royalties'}
        totals = dict.fromkeys(categories.values(), Decimal('0'))
        with localcontext() as ctx:
            ctx.prec = 40
            for item in case.incomes:
                if item.category not in categories or item.source_jurisdiction != 'cn':
                    raise ValueError('Only domestic comprehensive income is supported')
                totals[categories[item.category]] += item.gross_amount
        result = china.resident_comprehensive_tax(tax_year=2026, **totals, **args)
    elif policy == 'sg_company_ya2026':
        if args.pop('ordinary_regime_confirmed') is not True:
            raise ValueError('Ordinary Singapore regime must be confirmed')
        result = singapore.company_tax(assessment_year=2026, **args)
    elif policy == 'sg_resident_ya2026':
        result = singapore.resident_individual_tax(assessment_year=2026, **args)
    elif policy == 'hk_profits_2025_26':
        result = hong_kong.profits_tax(assessment_year='2025/26', **args)
    elif policy == 'hk_salaries_2025_26':
        if any(i.category != 'employment' for i in case.incomes):
            raise ValueError('Salaries policy cannot cover other saved income categories')
        result = hong_kong.salaries_tax(assessment_year='2025/26', **args)
    elif policy == 'ae_ordinary_2026':
        classified = args.pop('natural_person_activity_classification_confirmed')
        if case.subject == 'individual':
            if classified is not True:
                raise ValueError('Natural-person statutory activity classification must be confirmed')
            with localcontext() as ctx:
                ctx.prec = 40
                turnover = sum((i.gross_amount for i in case.incomes if i.category == 'business'), Decimal('0'))
            if turnover != args['natural_person_business_turnover']:
                raise ValueError('Business turnover must reconcile to saved business income')
        result = united_arab_emirates.ordinary_corporate_tax(tax_year=2026, subject_type=case.subject, **args)
    else:
        raise ValueError('Unsupported policy')
    # Pydantic preserves Decimal strings and nested band dataclasses in JSON.
    return TypeAdapter(dict).dump_python(result, mode='json')
