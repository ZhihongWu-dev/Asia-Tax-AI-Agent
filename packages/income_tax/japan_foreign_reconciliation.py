"""Reconcile saved ordinary Japanese corporate receipts to credit inputs.

Source qualification, expense attribution and foreign tax eligibility are
verified workpaper facts. This does not infer treaty rates, high-tax exclusions,
foreign PE adjustments, dividend exemptions or annual return liability.
"""
from decimal import Decimal, localcontext
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt
from packages.contracts.income_tax import Money
from .japan import yen
from .japan_company import annual_period
from .japan_company import company_tax
from .japan_foreign_credit import current_national_credits,current_national_return_credits


class Group(BaseModel):
    model_config=ConfigDict(extra='forbid')
    source_id: str=Field(min_length=1,max_length=120,pattern=r'\S')
    income_indexes: list[StrictInt]=Field(min_length=1,max_length=200)
    allowable_expenses: Money
    foreign_income_exempt_from_foreign_tax: Money
    eligible_foreign_corporate_tax: Money


class SavedWorkpaper(BaseModel):
    model_config=ConfigDict(extra='forbid')
    groups: list[Group]=Field(min_length=1,max_length=200)
    japanese_source_income_and_expense_allocation_verified: StrictBool
    foreign_tax_eligibility_high_tax_exclusions_treaty_fx_and_period_verified: StrictBool
    foreign_tax_exempt_income_and_no_double_deduction_verified: StrictBool
    no_losses_dividend_exemptions_pe_adjustments_groups_or_special_regimes_verified: StrictBool


def reconcile(case,workpaper):
    p=SavedWorkpaper.model_validate(workpaper)
    if not all((p.japanese_source_income_and_expense_allocation_verified,
            p.foreign_tax_eligibility_high_tax_exclusions_treaty_fx_and_period_verified,
            p.foreign_tax_exempt_income_and_no_double_deduction_verified,
            p.no_losses_dividend_exemptions_pe_adjustments_groups_or_special_regimes_verified)):
        raise ValueError('Verify source attribution, foreign tax eligibility and ordinary scope')
    if (case.subject!='company' or case.jurisdiction!='jp' or case.residency!='resident'
            or case.missing_for_calculation() or case.carried_losses):
        raise ValueError('Confirmed resident Japanese company without carried losses required')
    start,end=annual_period(case.period_start,case.period_end)
    indexes=[i for g in p.groups for i in g.income_indexes]
    ids=[g.source_id.strip() for g in p.groups]
    if sorted(indexes)!=list(range(len(case.incomes))) or len(ids)!=len(set(ids)):
        raise ValueError('Unique source groups must cover each saved income exactly once')
    rows=[];foreign_count=0
    with localcontext() as context:
        context.prec=40
        if sum((g.allowable_expenses for g in p.groups),Decimal(0))!=case.claimed_deductions:
            raise ValueError('Source expenses must reconcile to saved deductions')
        world=foreign=exempt=eligible=Decimal(0)
        for g in p.groups:
            items=[case.incomes[i] for i in g.income_indexes]
            countries={i.source_jurisdiction for i in items};categories={i.category for i in items}
            if len(countries)!=1 or len(categories)!=1 or not categories<={'business','interest','rental','royalty'}:
                raise ValueError('Each group requires one country and ordinary income category')
            country=next(iter(countries));category=next(iter(categories))
            gross=sum((yen(i.gross_amount) for i in items),Decimal(0))
            expenses=yen(g.allowable_expenses);net=gross-expenses
            source_exempt=yen(g.foreign_income_exempt_from_foreign_tax)
            source_eligible=yen(g.eligible_foreign_corporate_tax)
            if net<0:
                raise ValueError('Source losses require separate statutory allocation')
            world+=net
            paid=sum((yen(i.foreign_tax_paid or 0) for i in items),Decimal(0))
            if country=='jp':
                if paid or source_exempt or source_eligible:
                    raise ValueError('Domestic source cannot claim foreign tax or foreign exemption')
            else:
                foreign_count+=1
                if source_exempt>net:
                    raise ValueError('Foreign-tax-exempt income exceeds source net income')
                if source_eligible>paid:
                    raise ValueError('Eligible foreign tax exceeds saved actual foreign payments')
                foreign+=net;exempt+=source_exempt;eligible+=source_eligible
            rows.append(dict(source_id=g.source_id.strip(),country=country,category=category,
                gross_income=gross,allowable_expenses=expenses,net_income=net,
                foreign_tax_paid=paid,foreign_income_exempt_from_foreign_tax=source_exempt,
                eligible_foreign_corporate_tax=source_eligible))
        if not foreign_count or world<=0:
            raise ValueError('Positive worldwide income and at least one foreign source required')
        return dict(period_start=start.isoformat(),period_end=end.isoformat(),
            statutory_worldwide_income=world,taxable_income_before_rounding=world,
            foreign_income_before_exempt=foreign,foreign_income_exempt_from_foreign_tax=exempt,
            eligible_foreign_corporate_tax=eligible,sources_reconciled=rows,
            stage='saved_ordinary_source_reconciliation_not_annual_assessment')


def current_credit_workpaper(case,workpaper,*,rate_regime,rate_classification_verified,
        no_other_tax_credits_additions_or_history_verified):
    """Derive ordinary references from saved facts; not a final tax return.

    Reuse the existing ordinary rate/base engine only for pre-credit references.
    Its rounded final tax and interim settlement outputs are deliberately not
    exposed here. Schedule6(2) references precede final JPY100 tax truncation.
    """
    if no_other_tax_credits_additions_or_history_verified is not True:
        raise ValueError('Other credits, additions and historical balances need separate treatment')
    reconciled=reconcile(case,workpaper)
    ordinary=company_tax(reconciled['taxable_income_before_rounding'],
        period_start=case.period_start,period_end=case.period_end,rate_regime=rate_regime,
        rate_classification_verified=rate_classification_verified,
        ordinary_no_adjustments_confirmed=True,corporation_interim_liability=0,
        local_corporation_interim_liability=0)
    with localcontext() as context:
        context.prec=40
        references=dict(corporation_tax_reference=ordinary['corporation_tax_reference'],
            local_corporation_tax_reference=ordinary['local_corporation_tax_base']*Decimal('.103'),
            defence_tax_reference=ordinary['defence_tax_base']*Decimal('.04'),
            defence_applicable=ordinary['defence_return_required'])
    credit=current_national_credits(**{key:reconciled[key] for key in (
        'statutory_worldwide_income','foreign_income_before_exempt',
        'foreign_income_exempt_from_foreign_tax','eligible_foreign_corporate_tax')},
        **references,statutory_reference_amounts_and_current_tax_eligibility_verified=True,
        no_history_group_or_special_credit_adjustments_verified=True)
    return dict(policy_version='jp-saved-current-credit-workpaper-20261122',currency='JPY',
        reconciliation=reconciled,reference_taxes=references,
        corporation_taxable_base=ordinary['taxable_income'],
        local_corporation_tax_base=ordinary['local_corporation_tax_base'],
        defence_tax_base=ordinary['defence_tax_base'],rate_regime=rate_regime,
        current_national_credit=credit,sources=ordinary['sources']+credit['sources'],
        stage='saved_current_credit_workpaper_before_filing_rounding_and_local_history_settlement')


def current_national_settlement(case,workpaper,*,corporation_interim_liability,
        local_corporation_interim_liability,**reference_options):
    """Settle the three national taxes only; local/history support is separate."""
    current=current_credit_workpaper(case,workpaper,**reference_options)
    reconciled=current['reconciliation'];references=current['reference_taxes']
    credits=current_national_return_credits(**{key:reconciled[key] for key in (
        'statutory_worldwide_income','foreign_income_before_exempt',
        'foreign_income_exempt_from_foreign_tax','eligible_foreign_corporate_tax')},
        **references,statutory_reference_amounts_and_current_tax_eligibility_verified=True,
        no_history_group_or_special_credit_adjustments_verified=True)
    interim=[yen(corporation_interim_liability),yen(local_corporation_interim_liability),Decimal(0)]
    if any(value%100 for value in interim):
        raise ValueError('Interim return liabilities must be in whole hundreds of yen')
    settlements={}
    with localcontext() as context:
        context.prec=40
        for name,prepaid in zip(('corporation','local_corporation','defence'),interim):
            reference=references[name+'_tax_reference'];credit=credits[name+'_credit']
            after=reference-credit
            liability=(after//100)*100
            balance=liability-prepaid
            settlements[name]=dict(reference_tax=reference,current_foreign_credit=credit,
                after_credit_before_final_rounding=after,annual_liability=liability,
                interim_return_liability=prepaid,balance_due=balance,
                payable=max(Decimal(0),balance),refundable=max(Decimal(0),-balance))
        return dict(policy_version='jp-current-national-foreign-settlement-20261122',currency='JPY',
            tax_scope='japan_three_national_company_taxes_only',
            source_reconciliation=reconciled,reference_taxes=references,
            current_foreign_credit=credits,settlements=settlements,
            total_payable=sum((v['payable'] for v in settlements.values()),Decimal(0)),
            total_refundable=sum((v['refundable'] for v in settlements.values()),Decimal(0)),
            sources=current['sources']+[credits['sources'][-1]],
            stage='current_national_settlement_local_and_history_not_calculated')


def current_standard_local_workpaper(case,workpaper,local_workpaper,**reference_options):
    """Saved facts drive national references and standard local credit limits.

    Local available levies and employee weights remain verified inputs. This
    does not settle enterprise taxes, capitation, history or interim payments.
    """
    from .japan_local_foreign_credit import allocate_standard_current
    current=current_credit_workpaper(case,workpaper,**reference_options)
    reconciled=current['reconciliation']
    inputs={key:reconciled[key] for key in (
        'statutory_worldwide_income','foreign_income_before_exempt',
        'foreign_income_exempt_from_foreign_tax','eligible_foreign_corporate_tax')}
    inputs.update(current['reference_taxes'],
        statutory_reference_amounts_and_current_tax_eligibility_verified=True,
        no_history_group_or_special_credit_adjustments_verified=True)
    allocation=allocate_standard_current(inputs,local_workpaper)
    sources={s['doc_id']:s for s in current['sources']+
        allocation['national_credit']['sources']+allocation['sources']}
    return dict(policy_version='jp-saved-standard-local-credit-workpaper-20261122',currency='JPY',
        source_reconciliation=reconciled,reference_taxes=current['reference_taxes'],
        current_foreign_credit=allocation,sources=list(sources.values()),
        stage='saved_current_credit_allocation_local_settlement_and_history_pending')
