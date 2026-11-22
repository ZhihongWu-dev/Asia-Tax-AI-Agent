"""Route explicit bases against a confirmed immutable case snapshot."""
from copy import deepcopy
from decimal import Decimal, localcontext
from pydantic import TypeAdapter
from packages.contracts.income_tax import IncomeTaxCase
from . import china, singapore, hong_kong, united_arab_emirates, malaysia, thailand, indonesia
from . import vietnam, vietnam_employment, vietnam_transfer, japan, japan_company, india, india_company
from . import korea_company
from . import vietnam_business, vietnam_rental
from . import korea_salary
from . import china_business
from . import hong_kong_property
from . import singapore_employment
from . import thailand_dividends
from . import malaysia_dividends
from . import thailand_foreign_credit
from .korea_children import ChildCreditFacts
from .korea_personal_deductions import PersonalDeductionPerson


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
               'jp': ('2026-01-01', '2026-12-31'), 'kr': ('2026-01-01', '2026-12-31'), 'in': ('2026-04-01', '2027-03-31')}
    if policy=='jp_company_starting_2026':
        japan_company.annual_period(case.period_start,case.period_end)
    elif (case.period_start.isoformat(), case.period_end.isoformat()) != periods[jur]:
        raise ValueError('Saved basis period is not supported by this policy')
    expected = {'cn_company_2026': 'company', 'cn_small_company_2026': 'company', 'cn_comprehensive_2026': 'individual', 'cn_business_2026': 'individual',
                'ae_company_foreign_direct_2026': 'company', 'sg_company_ya2026': 'company', 'sg_company_foreign_direct_ya2026': 'company', 'sg_resident_ya2026': 'individual',
                'hk_salaries_2025_26': 'individual', 'my_company_2026': 'company',
                'my_individual_2026': 'individual', 'my_dividend_2026': 'individual', 'th_company_2026':'company', 'th_resident_2026':'individual', 'th_dividend_2026':'individual', 'th_foreign_income_2026':'individual',
                'vn_personal_transfer_2026': 'individual', 'vn_employment_2026': 'individual', 'vn_company_2026': 'company', 'vn_business_2026': 'individual', 'vn_property_rental_2026': 'individual',
                'jp_resident_ordinary_2026': 'individual', 'jp_company_starting_2026':'company',
                'in_personal_new_ty2026_27':'individual', 'in_personal_old_ty2026_27':'individual', 'in_company_section200_ty2026_27':'company',
                'in_company_normal_ty2026_27':'company', 'kr_company_ordinary_2026':'company',
                'kr_salary_standard_payroll_2026':'individual'}
    if policy == 'hk_profits_2025_26':
        expected[policy] = 'company' if basis.business_form == 'corporation' else 'individual'
    if policy in expected and case.subject != expected[policy]:
        raise ValueError('Policy subject differs from the saved case')
    if policy in ('id_company_2026','id_resident_2026') and case.subject != ('company' if policy=='id_company_2026' else 'individual'):
        raise ValueError('Policy subject differs from the saved case')
    if policy in ('cn_comprehensive_2026', 'sg_resident_ya2026', 'th_resident_2026','th_dividend_2026','th_foreign_income_2026','id_company_2026','id_resident_2026','vn_employment_2026','vn_company_2026','jp_resident_ordinary_2026') and case.residency != 'resident':
        raise ValueError('This policy requires resident status')
    args = basis.model_dump(exclude={'policy', 'basis_explanation', 'basis_confirmed'})
    cn_reconciliation = None
    if policy in ('cn_company_2026', 'cn_small_company_2026'):
        cn_reconciliation = china.reconcile_company_basis(case,
            taxable_income=basis.taxable_income,
            non_taxable_income=args.pop('non_taxable_income'), exempt_income=args.pop('exempt_income'))
    if policy=='cn_personal_foreign_2026':
        from .china_personal_foreign_assessment import assess
        result=assess(case,basis.workpaper,basis.prepaid_tax)
    elif policy=='cn_company_foreign_direct_2026':
        from .china_foreign_assessment import assess
        result=assess(case,basis.workpaper,basis.prepaid_tax)
    elif policy == 'in_company_foreign_ty2026_27':
        from .india_foreign_assessment import assess
        result = assess(case, basis.workpaper, basis.prepaid_tax)
    elif policy in ('in_personal_new_ty2026_27','in_personal_old_ty2026_27','in_company_section200_ty2026_27','in_company_normal_ty2026_27'):
        settlement_requested=args.pop('settlement_requested')
        settlement={key:args.pop(key) for key in ('tds_tcs_credit','advance_tax_paid',
            'self_assessment_paid','total_interest_due','total_fee_due','settlement_verified')}
        if not settlement_requested and (settlement['settlement_verified'] or
                any(value is not None for key,value in settlement.items() if key!='settlement_verified')):
            raise ValueError('Settlement values require an explicit settlement request')
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
        if policy=='in_company_normal_ty2026_27':
            result=india_company.normal_company_tax(period_start=case.period_start.isoformat(),period_end=case.period_end.isoformat(),**args)
        else:
            result=india.annual_tax(period_start=case.period_start.isoformat(),period_end=case.period_end.isoformat(),
                regime={'in_personal_new_ty2026_27':'personal_new_resident',
                        'in_personal_old_ty2026_27':'personal_old_resident',
                        'in_company_section200_ty2026_27':'company_section200'}[policy],**args)
        if settlement_requested:
            result=india.settle(result,**settlement)
    elif policy=='kr_salary_standard_payroll_2026':
        if case.residency!='resident' or case.carried_losses!=0 or any(
                i.source_jurisdiction!='kr' or i.category!='employment' or
                i.foreign_tax_paid not in (None,0) for i in case.incomes):
            raise ValueError('Korean payroll policy requires resident domestic ordinary salary without carried losses or foreign credits')
        if case.claimed_deductions!=basis.public_pension_paid:
            raise ValueError('Saved deductions must equal verified public pension contributions; automatic salary and family deductions are separate')
        with localcontext() as context:
            context.prec=40
            salary=sum((i.gross_amount for i in case.incomes),Decimal(0))
        args['people']=[PersonalDeductionPerson(**row) for row in args['people']]
        args['children']=[ChildCreditFacts(**row) for row in args['children']]
        result=korea_salary.standard_salary_return(salary,tax_year=2026,**args)
    elif policy=='kr_company_foreign_history_2026':
        from .korea_foreign_assessment import assess_with_history
        result = assess_with_history(case, **args)
    elif policy=='kr_company_foreign_direct_2026':
        from .korea_foreign_assessment import assess
        result = assess(case, **args)
    elif policy=='kr_company_ordinary_2026':
        if case.residency != 'resident' or any(i.source_jurisdiction != 'kr' or
                i.foreign_tax_paid not in (None, 0) or i.category not in ('business', 'interest', 'rental', 'royalty')
                for i in case.incomes):
            raise ValueError('Korean ordinary domestic resident company income required; special and foreign income need separate treatment')
        with localcontext() as context:
            context.prec = 40
            base = max(Decimal('0'), sum((i.gross_amount for i in case.incomes), Decimal('0'))
                - case.claimed_deductions - case.carried_losses)
        if basis.national_taxable_base != base:
            raise ValueError('Korean national base must reconcile to saved income, deductions and eligible losses')
        result = korea_company.company_tax(**args)
    elif policy=='jp_company_starting_2026':
        if case.residency!='resident' or any(i.source_jurisdiction!='jp' or
                i.foreign_tax_paid not in (None,0) or i.category not in ('business','rental','royalty','other') for i in case.incomes):
            raise ValueError('Ordinary Japanese resident domestic company income without withholding/foreign-credit adjustments required')
        reconciliation = japan_company.reconcile_company_basis(case,
            taxable_income_before_rounding=basis.taxable_income_before_rounding)
        tokyo_paper = args.pop('tokyo_local')
        osaka_paper = args.pop('osaka_local')
        if tokyo_paper is not None and osaka_paper is not None:
            raise ValueError('Tokyo-only and Osaka-only local workpapers cannot be combined')
        result=japan_company.company_tax(period_start=case.period_start,period_end=case.period_end,**args)
        result['basis_reconciliation'] = reconciliation
        result['policy_version'] += '-reconciled-20261119'
        if tokyo_paper is not None:
            from .japan_tokyo import assess as assess_tokyo, WORKPAPER_SOURCES
            from .japan_local import SOURCES as tokyo_sources
            local = assess_tokyo(result,reconciliation,basis.tokyo_local)
            result['tokyo_local'] = local
            result['national_final_tax'] = result['final_tax']
            with localcontext() as ctx:
                ctx.prec = 40
                result['final_tax'] += local['local_final_tax']
            result['tax_scope'] = 'japan_national_and_ordinary_tokyo_23_wards_full_year'
            result['local_taxes_calculated'] = True
            result['policy_version'] += '-tokyo-local-20261119'
            result['sources'].extend(deepcopy([*tokyo_sources, *WORKPAPER_SOURCES]))
        if osaka_paper is not None:
            from .japan_osaka import assess as assess_osaka
            local = assess_osaka(result, reconciliation, basis.osaka_local)
            result['osaka_local'] = local
            result['national_final_tax'] = result['final_tax']
            with localcontext() as ctx:
                ctx.prec = 40
                result['final_tax'] += local['local_final_tax']
            result['tax_scope'] = 'japan_national_and_ordinary_osaka_city_full_year'
            result['local_taxes_calculated'] = True
            result['policy_version'] += '-osaka-local-20261119'
            result['sources'].extend(deepcopy(local['sources']))
    elif policy == 'cn_small_company_2026':
        if case.residency != 'resident' or any(item.source_jurisdiction != 'cn' or
                item.foreign_tax_paid not in (None, 0) for item in case.incomes):
            raise ValueError('Small-company workflow requires domestic resident income without foreign tax credits')
        result = china.small_low_profit_company_tax(tax_year=2026, **args)
    elif policy == 'cn_company_2026':
        if any(i.source_jurisdiction != 'cn' for i in case.incomes):
            raise ValueError('Foreign-source corporate workflow is not verified by this policy')
        result = china.normal_company_tax(tax_year=2026, **args)
    elif policy == 'cn_business_2026':
        if case.residency != 'resident' or any(item.category != 'business' or
                item.source_jurisdiction != 'cn' or item.foreign_tax_paid not in (None, 0)
                for item in case.incomes):
            raise ValueError('China business workflow requires resident domestic business income without foreign tax credits')
        with localcontext() as ctx:
            ctx.prec = 40
            base = max(Decimal('0'), sum((item.gross_amount for item in case.incomes), Decimal('0'))
                - case.claimed_deductions - case.carried_losses)
        if basis.taxable_income != base:
            raise ValueError('Business taxable base must reconcile to saved income, established deductions and eligible losses')
        result = china_business.annual_business_tax(tax_year=2026, **args)
    elif policy == 'cn_comprehensive_2026':
        if case.carried_losses != 0:
            raise ValueError('Comprehensive income cannot consume carried losses')
        if any(item.foreign_tax_paid not in (None, 0) for item in case.incomes):
            raise ValueError('Domestic comprehensive policy cannot consume foreign tax credits')
        with localcontext() as ctx:
            ctx.prec = 40
            manual_deductions = sum((basis.allowed_special_deductions,
                basis.allowed_additional_deductions, basis.allowed_other_deductions,
                basis.allowed_donations), Decimal('0'))
        if case.claimed_deductions != manual_deductions:
            raise ValueError('Saved deductions must reconcile to special, additional, other and donation deductions; automatic basic and income-category deductions are separate')
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
    elif policy == 'sg_employment_ya2026':
        if case.subject != 'individual' or case.residency != 'resident' or case.carried_losses != 0 or any(
                i.category != 'employment' or i.source_jurisdiction != 'sg' or
                i.foreign_tax_paid not in (None, 0) for i in case.incomes):
            raise ValueError('Singapore employment workflow requires resident domestic employment without losses or foreign credits')
        with localcontext() as ctx:
            ctx.prec = 40
            gross = sum((i.gross_amount for i in case.incomes), Decimal('0'))
            manual = sum((basis.allowed_employment_expenses, basis.allowed_donation_deduction,
                          basis.allowed_cpf_relief, basis.allowed_other_personal_reliefs), Decimal('0'))
        if case.claimed_deductions != manual:
            raise ValueError('Saved deductions must equal expenses, donation deduction, CPF and other relief claims before the overall cap; exclude automatic earned income relief')
        result = singapore_employment.resident_employment_tax(gross, assessment_year=2026, **args)
    elif policy == 'sg_company_foreign_direct_ya2026':
        from .singapore_foreign_assessment import assess
        result = assess(case, **args)
    elif policy == 'id_company_foreign_direct_2026':
        from .indonesia_foreign_assessment import assess
        result = assess(case, **args)
    elif policy == 'my_company_foreign_direct_ya2026':
        from .malaysia_foreign_assessment import assess
        result = assess(case, **args)
    elif policy == 'ae_company_foreign_direct_2026':
        from .uae_foreign_assessment import assess
        result = assess(case, **args)
    elif policy == 'sg_company_ya2026':
        if args.pop('ordinary_regime_confirmed') is not True:
            raise ValueError('Ordinary Singapore regime must be confirmed')
        reconciliation = singapore.reconcile_company_basis(case,
            normal_chargeable_income=basis.normal_chargeable_income)
        result = singapore.company_tax(assessment_year=2026, **args)
        result['singapore_basis_reconciliation'] = reconciliation
        result['policy_version'] += '-reconciled-20261119'
        result['sources'] = [result['source'], *[dict(s) for s in singapore.COMPANY_BASIS_SOURCES]]
    elif policy == 'sg_resident_ya2026':
        result = singapore.resident_individual_tax(assessment_year=2026, **args)
    elif policy == 'hk_profits_2025_26':
        if any(i.category == 'employment' for i in case.incomes):
            raise ValueError('Profits policy cannot cover saved employment income; separate the tax schedules')
        if case.subject == 'individual' and any(i.category == 'rental' for i in case.incomes):
            raise ValueError('Individual rental income requires property assessment or verified business classification')
        from .hong_kong_reconciliation import reconcile
        reconciliation = reconcile(case, additions=args.pop('taxable_additions'),
            excluded_income=args.pop('excluded_income'))
        if basis.assessable_profits != reconciliation['net_taxable_profits']:
            raise ValueError('Hong Kong net taxable profits must reconcile to saved income, tax adjustments, deductions and prior losses')
        result = hong_kong.profits_tax(assessment_year='2025/26', **args)
        result['hong_kong_profits_reconciliation'] = reconciliation
        result['policy_version'] += '-reconciled-20261119'
        result['sources'].extend(deepcopy(hong_kong.PROFITS_BASIS_SOURCES))
    elif policy == 'hk_property_2025_26':
        result = hong_kong_property.property_tax(case, assessment_year='2025/26', **args)
    elif policy == 'hk_salaries_2025_26':
        if any(i.category != 'employment' for i in case.incomes):
            raise ValueError('Salaries policy cannot cover other saved income categories')
        if args.pop('workpaper') is None:
            raise ValueError('Salaries calculation requires a reconciled workpaper')
        from .hong_kong_salary_reconciliation import reconcile
        reconciliation = reconcile(case,basis.workpaper)
        if basis.net_income != reconciliation['net_income_before_allowances']:
            raise ValueError('Salaries net income must reconcile to the saved income and deduction workpaper')
        result = hong_kong.salaries_tax(assessment_year='2025/26', **args)
        result['salary_reconciliation'] = reconciliation
        result['policy_version'] += '-reconciled-20261119'
        result['sources'].extend(deepcopy(hong_kong.SALARY_BASIS_SOURCES))
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
        from .uae_reconciliation import reconcile
        reconciliation = reconcile(case, taxable_income=basis.taxable_income,
            additions=args.pop('taxable_additions'), exempt_income=args.pop('exempt_income'))
        result = united_arab_emirates.ordinary_corporate_tax(tax_year=2026, subject_type=case.subject, **args)
        result['uae_basis_reconciliation'] = reconciliation
        result['policy_version'] += '-reconciled-20261119'
        result['sources'].extend(deepcopy(united_arab_emirates.BASIS_SOURCES))
    elif policy == 'my_dividend_2026':
        if args.pop('separate_domestic_assessment_verified') is not True:
            raise ValueError('Separate domestic ordinary and dividend assessment must be verified')
        allowed = {'dividend', 'employment', 'business', 'rental', 'interest',
                   'royalty', 'service_remuneration', 'author_remuneration'}
        if case.carried_losses != 0 or any(i.category not in allowed or
                i.source_jurisdiction != 'my' or i.foreign_tax_paid not in (None, 0)
                for i in case.incomes):
            raise ValueError('Foreign, special-rate income and carried losses need a separate Malaysia workflow')
        if not any(i.category == 'dividend' for i in case.incomes):
            raise ValueError('Dividend assessment requires saved dividend income')
        before = args.pop('dividend_statutory_before_threshold')
        ordinary = args.pop('ordinary_statutory_income')
        dividend = malaysia_dividends.dividend_statutory_income(before,
            scope_verified=args.pop('dividend_scope_verified'))
        with localcontext() as ctx:
            ctx.prec = 40
            gross_dividends = sum((i.gross_amount for i in case.incomes if i.category == 'dividend'), Decimal('0'))
            gross_ordinary = sum((i.gross_amount for i in case.incomes if i.category != 'dividend'), Decimal('0'))
            if before > gross_dividends or ordinary > gross_ordinary:
                raise ValueError('Established statutory income exceeds the corresponding saved gross income')
            aggregate = dividend + ordinary
            if basis.chargeable_income > aggregate:
                raise ValueError('Chargeable income exceeds aggregate income after the dividend threshold')
            # Saved deductions include verified expenses, exclusions and reliefs,
            # but exclude the automatic annual dividend threshold.
            deductions = gross_dividends-before + gross_ordinary-ordinary + aggregate-basis.chargeable_income
            if case.claimed_deductions != deductions:
                raise ValueError('Malaysia dividend bases must reconcile to saved income and deductions, excluding the automatic threshold')
        result = malaysia_dividends.annual_dividend_assessment(assessment_year=2026,
            residency=case.residency, dividend_statutory_income=dividend,
            aggregate_income=aggregate, **args)
        result.update(dividend_statutory_before_threshold=before,
                      dividend_threshold_used=before-dividend,
                      ordinary_statutory_income=ordinary, reconciled_deductions=deductions)
    elif policy in ('my_company_2026','my_individual_2026'):
        if any(i.category in ('dividend','capital_gain') for i in case.incomes):
            raise ValueError('Dividend and capital-gains treatment requires a separate workflow')
        if policy=='my_company_2026':
            if basis.scheme=='sme' and case.residency!='resident':
                raise ValueError('SME rates require Malaysian residence')
            if args.pop('workpaper') is None:
                raise ValueError('Company calculation requires a reconciled workpaper')
            from .malaysia_reconciliation import reconcile_company
            reconciliation = reconcile_company(case, basis.workpaper)
            if basis.chargeable_income != reconciliation['chargeable_income']:
                raise ValueError('Company chargeable income differs from the reconciled workpaper')
            result=malaysia.company_tax(assessment_year=2026,**args)
            result['reconciliation'] = reconciliation
            result['policy_version'] += '-reconciled-20261119'
            result['sources'].extend(deepcopy(malaysia.COMPANY_BASIS_SOURCES))
        else:
            paper = args.pop('workpaper')
            if paper is None:
                raise ValueError('Individual calculation requires a reconciled workpaper')
            from .malaysia_reconciliation import reconcile
            reconciliation = reconcile(case, basis.workpaper)
            if basis.chargeable_income != reconciliation['chargeable_income']:
                raise ValueError('Chargeable income differs from the reconciled workpaper')
            result=malaysia.individual_tax(assessment_year=2026,residency=case.residency,**args)
            if reconciliation is not None:
                result['reconciliation'] = reconciliation
                result['policy_version'] += '-reconciled-20261122'
                for source in result['sources']:
                    source['locator'] += '; sections 42-45 (basis reconciliation)'
    elif policy in ('id_company_2026','id_resident_2026'):
        allowed={'business','employment','service_remuneration','author_remuneration','royalty'}
        if any(i.source_jurisdiction!='id' or i.category not in allowed for i in case.incomes):
            raise ValueError('Foreign, final, exempt or special-rate income requires a separate Indonesian workflow')
        with localcontext() as ctx:
            ctx.prec=40
            gross=sum((i.gross_amount for i in case.incomes),Decimal('0'))
        if policy=='id_company_2026':
            reconciliation = indonesia.reconcile_company_basis(case,
                taxable_income_before_rounding=basis.taxable_income_before_rounding)
            result=indonesia.company_tax(tax_year=2026,article31e_gross_receipts=gross,**args)
            result['basis_reconciliation'] = reconciliation
            result['policy_version'] += '-reconciled-20261119'
        else:
            with localcontext() as ctx:
                ctx.prec = 40
                after_deductions = gross - case.claimed_deductions
                available = max(Decimal('0'), after_deductions)
                used_losses = min(available, case.carried_losses)
                reconciled = available - used_losses
            if basis.net_income_before_ptkp != reconciled:
                raise ValueError('Indonesian personal net income must reconcile to saved income, verified deductions and eligible prior losses before PTKP')
            result=indonesia.resident_individual_tax(tax_year=2026,**args)
            result['personal_basis_reconciliation'] = dict(saved_gross_income=gross,
                verified_deductions=case.claimed_deductions,
                income_after_deductions=after_deductions, eligible_prior_losses=case.carried_losses,
                prior_losses_used=used_losses, prior_losses_unused=case.carried_losses-used_losses,
                net_income_before_ptkp=reconciled,
                scope='Established fiscal amounts only; no automatic deduction eligibility or future loss carryforward entitlement')
            result['policy_version'] += '-reconciled-20261119'
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
    elif policy=='vn_property_rental_2026':
        if case.residency != 'resident' or case.carried_losses != 0 or any(
                i.category != 'rental' or i.source_jurisdiction != 'vn' or
                i.foreign_tax_paid not in (None, 0) for i in case.incomes):
            raise ValueError('Requires resident domestic property rental only, without carried losses or foreign credits')
        contract_basis = args.pop('contracts')
        if sorted(c['income_index'] for c in contract_basis) != list(range(len(case.incomes))):
            raise ValueError('Each saved rental income must have exactly one contract basis')
        with localcontext() as ctx:
            ctx.prec = 40
            if sum((c['allocated_revenue_deduction'] for c in contract_basis), Decimal('0')) != case.claimed_deductions:
                raise ValueError('Rental deductions must reconcile to saved deductions')
            contracts = []
            for contract in sorted(contract_basis, key=lambda c: c['income_index']):
                contract = dict(contract)
                index = contract.pop('income_index')
                contract['revenue'] = case.incomes[index].gross_amount
                contracts.append(contract)
            annual = sum((i.gross_amount for i in case.incomes), Decimal('0'))
        result = vietnam_rental.resident_property_rental_tax(tax_year=2026,
            resident=True, contracts=contracts, all_annual_rental_revenue=annual, **args)
        for index, contract in enumerate(result['contracts']):
            contract['income_index'] = index
    elif policy=='vn_business_2026':
        if case.residency != 'resident' or any(
                i.category != 'business' or i.source_jurisdiction != 'vn' or
                i.foreign_tax_paid not in (None, 0) for i in case.incomes):
            raise ValueError('Resident domestic business income is required; other income needs separate treatment')
        if case.carried_losses != 0:
            raise ValueError('Business policy does not establish carried-loss eligibility')
        activity_basis = args.pop('activities')
        if sorted(a['income_index'] for a in activity_basis) != list(range(len(case.incomes))):
            raise ValueError('Each saved income must have exactly one business classification')
        with localcontext() as ctx:
            ctx.prec = 40
            deductions = (sum((a['allocated_revenue_deduction'] for a in activity_basis), Decimal('0'))
                if basis.method == 'revenue' else basis.deductible_expenses)
            if deductions != case.claimed_deductions:
                raise ValueError('Business deductions must reconcile to the saved case')
            activities = [dict(category=a['category'],
                revenue=case.incomes[a['income_index']].gross_amount,
                allocated_revenue_deduction=a['allocated_revenue_deduction'])
                for a in sorted(activity_basis, key=lambda row: row['income_index'])]
            annual = sum((i.gross_amount for i in case.incomes), Decimal('0'))
        result = vietnam_business.resident_business_tax(tax_year=2026, resident=True,
            activities=activities, all_annual_business_revenue=annual, **args)
        for index, activity in enumerate(result['activities']):
            activity['income_index'] = index
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
        reconciliation = vietnam.reconcile_company_basis(case,
            taxable_income=basis.taxable_income, exempt_income=args.pop('exempt_income'))
        result = vietnam.company_tax(tax_year=2026, current_period_statutory_revenue=revenue, **args)
        result['basis_reconciliation'] = reconciliation
        result['policy_version'] += '-reconciled-20261119'
    elif policy=='vn_employment_2026':
        if any(i.category != 'employment' or i.source_jurisdiction != 'vn' for i in case.incomes):
            raise ValueError('Other income and foreign employment require their separate Vietnam workflow')
        if case.carried_losses != 0 or any(i.foreign_tax_paid not in (None, 0) for i in case.incomes):
            raise ValueError('Employment policy cannot consume carried losses or foreign tax credits')
        with localcontext() as ctx:
            ctx.prec = 40
            gross = sum((i.gross_amount for i in case.incomes), Decimal('0'))
        exempt = args.pop('exempt_employment_income')
        with localcontext() as ctx:
            ctx.prec = 40
            expected_pay = gross - exempt
        if exempt > gross or basis.chargeable_employment_income != expected_pay:
            raise ValueError('Chargeable employment income must equal saved gross income less verified exempt employment income')
        result = vietnam_employment.resident_employment_tax(tax_year=2026, resident=True, **args)
        if case.claimed_deductions != result['total_deductions']:
            raise ValueError('Employment deductions differ from the saved case; include personal, dependent, insurance and article 11 deductions exactly once')
        result['employment_reconciliation'] = dict(saved_gross_income=gross,
            exempt_employment_income=exempt, chargeable_employment_income=expected_pay,
            saved_claimed_deductions=case.claimed_deductions,
            reconciled_total_deductions=result['total_deductions'],
            taxable_income=result['taxable_income'])
        result['policy_version'] += '-reconciled-20261119'
    elif policy=='th_dividend_2026':
        if args.pop('ordinary_income_classification_verified') is not True:
            raise ValueError('Ordinary domestic income classification must be verified')
        allowed = {'dividend', 'employment', 'business', 'service_remuneration',
                   'author_remuneration', 'royalty', 'rental'}
        if any(i.category not in allowed or i.source_jurisdiction != 'th' for i in case.incomes):
            raise ValueError('Foreign or separate-regime income requires a separate workflow')
        if case.carried_losses != 0 or any(i.foreign_tax_paid not in (None, 0) for i in case.incomes):
            raise ValueError('Dividend workflow cannot consume carried losses or foreign tax credits')
        if case.claimed_deductions != basis.allowed_expenses_and_allowances:
            raise ValueError('Dividend workflow deductions differ from the saved case')
        lines = args.pop('tranches')
        totals = {}
        tranches = []
        with localcontext() as ctx:
            ctx.prec = 40
            for line in lines:
                index = line.pop('income_index')
                if index >= len(case.incomes) or case.incomes[index].category != 'dividend':
                    raise ValueError('Dividend certificate must reference a saved dividend income')
                totals[index] = totals.get(index, Decimal('0')) + line['gross_dividend']
                tranches.append(thailand_dividends.DividendTranche(**line))
            expected_dividends = {n:i.gross_amount for n,i in enumerate(case.incomes) if i.category == 'dividend'}
            if not expected_dividends or totals != expected_dividends:
                raise ValueError('Certified tranches must reconcile every saved dividend exactly')
            employment = sum((i.gross_amount for i in case.incomes if i.category == 'employment'), Decimal('0'))
            other = sum((i.gross_amount for i in case.incomes if i.category not in ('employment', 'dividend')), Decimal('0'))
        result = thailand_dividends.annual_dividend_assessment(tranches, tax_year=2026,
            employment_gross=employment, other_nonemployment_gross=other, **args)
        for output, saved in zip(result['dividend_components']['tranches'], basis.tranches):
            output['income_index'] = saved.income_index
    elif policy=='th_foreign_income_2026':
        result=thailand_foreign_credit.assess_saved_case(case, **args)
    elif policy=='th_company_2026':
        from .thailand_company_foreign_reconciliation import reconcile as reconcile_thai_foreign
        foreign_workpaper = args.pop('rd300_workpaper')
        foreign_reconciliation = None
        if foreign_workpaper is not None:
            foreign_reconciliation = reconcile_thai_foreign(case, foreign_workpaper,
                scheme=basis.scheme, exempt_income=basis.exempt_income,
                allowed_tax_credits=basis.allowed_tax_credits)
        reconciliation = thailand.reconcile_company_basis(case,
            net_taxable_profit=basis.net_taxable_profit, exempt_income=args.pop('exempt_income'))
        result=thailand.company_tax(tax_year=2026,**args)
        result['basis_reconciliation'] = reconciliation
        result['policy_version'] += '-reconciled-20261119'
        result['sources'] += [s.copy() for s in thailand.SOURCES if s['doc_id'] == 'th.rc3b.th']
        if foreign_reconciliation is not None:
            from .thailand_company_foreign_reconciliation import SOURCES as TH_FOREIGN_SOURCES
            result['foreign_credit_reconciliation'] = foreign_reconciliation
            result['sources'] += [s.copy() for s in TH_FOREIGN_SOURCES]
            result['policy_version'] += '-rd300-20261122'
    elif policy=='th_resident_2026':
        if args.pop('assessable_income_classification_confirmed') is not True:
            raise ValueError('Section40 assessable income classification must be confirmed')
        allowed={'employment','business','service_remuneration','author_remuneration','royalty','rental'}
        if any(i.category not in allowed or i.source_jurisdiction!='th' or
               i.foreign_tax_paid not in (None,0) for i in case.incomes):
            raise ValueError('Separate-rate or foreign-source income requires a separate workflow')
        if case.carried_losses != 0:
            raise ValueError('Thai ordinary personal policy does not establish carried-loss eligibility')
        with localcontext() as ctx:
            ctx.prec=40
            nonemployment=sum((i.gross_amount for i in case.incomes if i.category!='employment'),Decimal('0'))
            total=sum((i.gross_amount for i in case.incomes),Decimal('0'))
            reconciled=max(Decimal('0'),total-case.claimed_deductions)
        if basis.net_taxable_income!=reconciled:
            raise ValueError('Thai net taxable income must reconcile to saved income and verified deductions')
        result=thailand.resident_individual_tax(tax_year=2026,nonemployment_assessable_gross=nonemployment,**args)
    else:
        raise ValueError('Unsupported policy')
    if cn_reconciliation is not None:
        result['basis_reconciliation'] = cn_reconciliation
        result['policy_version'] += '-reconciled-20261119'
    # Pydantic preserves Decimal strings and nested band dataclasses in JSON.
    return TypeAdapter(dict).dump_python(result, mode='json')
