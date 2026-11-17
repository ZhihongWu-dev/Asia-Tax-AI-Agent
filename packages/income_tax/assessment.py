"""Route explicit bases against a confirmed immutable case snapshot."""
from decimal import Decimal, localcontext
from pydantic import TypeAdapter
from packages.contracts.income_tax import IncomeTaxCase
from . import china, singapore, hong_kong, united_arab_emirates, malaysia, thailand, indonesia
from . import vietnam, vietnam_employment, vietnam_transfer, japan, japan_company, india


def calculate(case: IncomeTaxCase, basis):
    if case.missing_for_calculation() or basis.basis_confirmed is not True:
        raise ValueError('Income facts and calculation basis require confirmation')
    policy = basis.policy
    jur = policy[:2]
    if jur != case.jurisdiction:
        raise ValueError('Policy jurisdiction differs from the saved case')
    # Japan company uses its explicit full-year period adapter; other policies
    # retain the reviewed calendar / stated year-of-assessment periods below.
    periods = {'cn': ('2026-01-01', '2026-12-31'), 'ae': ('2026-01-01', '2026-12-31'),
               'sg': ('2025-01-01', '2025-12-31'), 'hk': ('2025-04-01', '2026-03-31'),
               'my': ('2026-01-01', '2026-12-31'), 'th': ('2026-01-01', '2026-12-31'),
               'id': ('2026-01-01', '2026-12-31'), 'vn': ('2026-01-01', '2026-12-31'),
               'jp': ('2026-01-01', '2026-12-31'), 'in': ('2026-04-01', '2027-03-31')}
    if policy=='jp_company_starting_2026':
        japan_company.annual_period(case.period_start,case.period_end)
    elif (case.period_start.isoformat(), case.period_end.isoformat()) != periods[jur]:
        raise ValueError('Saved basis period is not supported by this policy')
    expected = {'cn_company_2026': 'company', 'cn_comprehensive_2026': 'individual',
                'sg_company_ya2026': 'company', 'sg_resident_ya2026': 'individual',
                'hk_salaries_2025_26': 'individual', 'my_company_2026': 'company',
                'my_individual_2026': 'individual', 'th_company_2026':'company', 'th_resident_2026':'individual',
                'vn_personal_transfer_2026': 'individual', 'vn_employment_2026': 'individual', 'vn_company_2026': 'company',
                'jp_resident_ordinary_2026': 'individual', 'jp_company_starting_2026':'company',
                'in_personal_new_ty2026_27':'individual', 'in_company_section200_ty2026_27':'company'}
    if policy == 'hk_profits_2025_26':
        expected[policy] = 'company' if basis.business_form == 'corporation' else 'individual'
    if policy in expected and case.subject != expected[policy]:
        raise ValueError('Policy subject differs from the saved case')
    if policy in ('id_company_2026','id_resident_2026') and case.subject != ('company' if policy=='id_company_2026' else 'individual'):
        raise ValueError('Policy subject differs from the saved case')
    if policy in ('cn_comprehensive_2026', 'sg_resident_ya2026', 'th_resident_2026','id_company_2026','id_resident_2026','vn_employment_2026','vn_company_2026','jp_resident_ordinary_2026') and case.residency != 'resident':
        raise ValueError('This policy requires resident status')
    args = basis.model_dump(exclude={'policy', 'basis_explanation', 'basis_confirmed'})
    if policy in ('in_personal_new_ty2026_27','in_company_section200_ty2026_27'):
        allowed={'business','employment','service_remuneration','author_remuneration','interest','rental','royalty'}
        if case.residency!='resident' or any(i.source_jurisdiction!='in' or
                i.foreign_tax_paid not in (None,0) or i.category not in allowed for i in case.incomes):
            raise ValueError('India ordinary domestic resident income required; special-rate and foreign income need separate treatment')
        with localcontext() as ctx:
            ctx.prec=40
            gross=sum((i.gross_amount for i in case.incomes),Decimal('0'))
            reconciled=max(Decimal('0'),gross-case.claimed_deductions-case.carried_losses)
        if basis.taxable_income_before_rounding!=reconciled:
            raise ValueError('India established taxable base must reconcile to saved income, deductions and eligible losses')
        result=india.annual_tax(period_start=case.period_start.isoformat(),period_end=case.period_end.isoformat(),
            regime='personal_new_resident' if case.subject=='individual' else 'company_section200',**args)
    elif policy=='jp_company_starting_2026':
        if case.residency!='resident' or any(i.source_jurisdiction!='jp' or
                i.foreign_tax_paid not in (None,0) or i.category not in ('business','rental','royalty','other') for i in case.incomes):
            raise ValueError('Ordinary Japanese resident domestic company income without withholding/foreign-credit adjustments required')
        result=japan_company.company_tax(period_start=case.period_start,period_end=case.period_end,**args)
    elif policy == 'cn_company_2026':
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
    elif policy in ('my_company_2026','my_individual_2026'):
        if any(i.category in ('dividend','capital_gain') for i in case.incomes):
            raise ValueError('Dividend and capital-gains treatment requires a separate workflow')
        if policy=='my_company_2026':
            if basis.scheme=='sme' and case.residency!='resident':
                raise ValueError('SME rates require Malaysian residence')
            result=malaysia.company_tax(assessment_year=2026,**args)
        else:
            result=malaysia.individual_tax(assessment_year=2026,residency=case.residency,**args)
    elif policy in ('id_company_2026','id_resident_2026'):
        allowed={'business','employment','service_remuneration','author_remuneration','royalty'}
        if any(i.source_jurisdiction!='id' or i.category not in allowed for i in case.incomes):
            raise ValueError('Foreign, final, exempt or special-rate income requires a separate Indonesian workflow')
        with localcontext() as ctx:
            ctx.prec=40
            gross=sum((i.gross_amount for i in case.incomes),Decimal('0'))
        if policy=='id_company_2026':
            result=indonesia.company_tax(tax_year=2026,article31e_gross_receipts=gross,**args)
        else:
            if basis.net_income_before_ptkp>gross:
                raise ValueError('Net income exceeds saved gross income')
            result=indonesia.resident_individual_tax(tax_year=2026,**args)
    elif policy=='jp_resident_ordinary_2026':
        if any(i.category not in ('employment','business') or i.source_jurisdiction != 'jp' or
               i.foreign_tax_paid not in (None,0) for i in case.incomes) or case.carried_losses != 0:
            raise ValueError('Japan ordinary policy requires domestic salary/business without foreign credits or carried losses')
        with localcontext() as ctx:
            ctx.prec = 40
            salary = sum((japan.yen(i.gross_amount) for i in case.incomes if i.category=='employment'),Decimal('0'))
            business = sum((japan.yen(i.gross_amount) for i in case.incomes if i.category=='business'),Decimal('0'))
            if basis.business_expenses + basis.other_income_deductions != case.claimed_deductions:
                raise ValueError('Saved deductions must reconcile to business expenses plus other income deductions; automatic salary/basic deductions are separate')
        result = japan.resident_ordinary_tax(salary,business,tax_year=2026,**args)
    elif policy=='vn_personal_transfer_2026':
        if any(i.category != 'capital_gain' or i.source_jurisdiction != 'vn' or
               i.foreign_tax_paid not in (None, 0) for i in case.incomes):
            raise ValueError('Transfer policy requires domestic transfer proceeds without foreign credits')
        if case.carried_losses != 0:
            raise ValueError('Per-transfer calculation cannot consume carried losses')
        indices = [line.income_index for line in basis.transfers]
        if sorted(indices) != list(range(len(case.incomes))):
            raise ValueError('Each saved transfer must have exactly one calculation basis')
        with localcontext() as ctx:
            ctx.prec = 40
            deductions = sum(((line.purchase_cost or Decimal('0')) +
                (line.transfer_costs or Decimal('0')) for line in basis.transfers), Decimal('0'))
            if deductions != case.claimed_deductions:
                raise ValueError('Transfer costs must reconcile to saved claimed deductions')
            results = []
            for line in sorted(basis.transfers, key=lambda x: x.income_index):
                values = line.model_dump(exclude={'income_index'})
                item = vietnam_transfer.personal_transfer_tax(
                    case.incomes[line.income_index].gross_amount,
                    resident=case.residency == 'resident', **values)
                item['income_index'] = line.income_index
                results.append(item)
            tax = sum((item['final_tax'] for item in results), Decimal('0'))
            prepaid = sum((item['prepaid_tax'] for item in results), Decimal('0'))
            result = dict(policy_version='vn-personal-transfer-case-2026-2026-11-17',
                currency='VND', transfers=results, final_tax=tax, prepaid_tax=prepaid,
                balance_due=tax-prepaid, sources=results[0]['sources'],
                calculation_stage='per_transaction_before_assessment_rounding')
    elif policy=='vn_company_2026':
        allowed = {'business', 'interest', 'rental', 'royalty', 'other'}
        if any(i.category not in allowed or i.source_jurisdiction != 'vn' for i in case.incomes):
            raise ValueError('Excluded or foreign income requires a separate Vietnam company workflow')
        if any(i.foreign_tax_paid not in (None, 0) for i in case.incomes):
            raise ValueError('Ordinary domestic policy cannot consume foreign tax credits')
        with localcontext() as ctx:
            ctx.prec = 40
            revenue = sum((i.gross_amount for i in case.incomes), Decimal('0'))
        result = vietnam.company_tax(tax_year=2026, current_period_statutory_revenue=revenue, **args)
    elif policy=='vn_employment_2026':
        if any(i.category != 'employment' or i.source_jurisdiction != 'vn' for i in case.incomes):
            raise ValueError('Other income and foreign employment require their separate Vietnam workflow')
        if case.carried_losses != 0 or any(i.foreign_tax_paid not in (None, 0) for i in case.incomes):
            raise ValueError('Employment policy cannot consume carried losses or foreign tax credits')
        with localcontext() as ctx:
            ctx.prec = 40
            gross = sum((i.gross_amount for i in case.incomes), Decimal('0'))
        if basis.chargeable_employment_income > gross:
            raise ValueError('Chargeable employment income exceeds saved gross income')
        result = vietnam_employment.resident_employment_tax(tax_year=2026, resident=True, **args)
    elif policy=='th_company_2026':
        result=thailand.company_tax(tax_year=2026,**args)
    elif policy=='th_resident_2026':
        if args.pop('assessable_income_classification_confirmed') is not True:
            raise ValueError('Section40 assessable income classification must be confirmed')
        allowed={'employment','business','service_remuneration','author_remuneration','royalty','rental'}
        if any(i.category not in allowed or i.source_jurisdiction!='th' for i in case.incomes):
            raise ValueError('Separate-rate or foreign-source income requires a separate workflow')
        with localcontext() as ctx:
            ctx.prec=40
            nonemployment=sum((i.gross_amount for i in case.incomes if i.category!='employment'),Decimal('0'))
            total=sum((i.gross_amount for i in case.incomes),Decimal('0'))
        if basis.net_taxable_income>total:
            raise ValueError('Net taxable income exceeds saved assessable gross income')
        result=thailand.resident_individual_tax(tax_year=2026,nonemployment_assessable_gross=nonemployment,**args)
    else:
        raise ValueError('Unsupported policy')
    # Pydantic preserves Decimal strings and nested band dataclasses in JSON.
    return TypeAdapter(dict).dump_python(result, mode='json')
