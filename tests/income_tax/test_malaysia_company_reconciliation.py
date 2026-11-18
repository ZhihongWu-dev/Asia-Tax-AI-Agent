from decimal import Decimal
import pytest
from packages.contracts.income_tax import IncomeTaxCase
from packages.contracts.income_assessment import Assessment
from packages.income_tax.malaysia_reconciliation import CompanyWorkpaper,reconcile_company
from packages.income_tax.assessment import calculate
from pydantic import TypeAdapter
from tests.income_tax.test_assessment_workflow import COMMON


def paper(count=1):
    return dict(sources=[dict(income_index=n,additions='0',deductions='0',statutory_charges='0',statutory_allowances='0',explanation='Verified ordinary domestic source adjustments') for n in range(count)],eligible_prior_business_losses='0',schedule4_additions='0',allowed_total_income_deductions=[],eligibility_verified=True,standalone_ordinary_verified=True)


def inputs():
    case=dict(subject='company',jurisdiction='my',period_start='2026-01-01',period_end='2026-12-31',currency='MYR',residency='resident',claimed_deductions='32000',carried_losses='100000',facts_confirmed=True,incomes=[dict(category='business',source_jurisdiction='my',gross_amount='100000',description='Business receipts'),dict(category='interest',source_jurisdiction='my',gross_amount='20000',description='Nonbusiness domestic interest')])
    work=paper(2);work['sources'][0]['statutory_allowances']='30000';work['eligible_prior_business_losses']='100000';work['allowed_total_income_deductions']=['2000']
    basis=dict(policy='my_company_2026',chargeable_income='18000',scheme='ordinary',sme_eligibility_confirmed=False,ordinary_treatment_confirmed=True,allowed_rebates='0',allowed_tax_credits='0',prepaid_tax='0',workpaper=work,**COMMON)
    return case,basis


def test_prior_business_loss_cannot_offset_nonbusiness_interest():
    case,basis=inputs();result=calculate(IncomeTaxCase(**case),TypeAdapter(Assessment).validate_python(basis))
    rec=result['reconciliation']
    assert Decimal(rec['prior_losses_used'])==70000
    assert Decimal(rec['prior_losses_unused'])==30000
    assert Decimal(rec['chargeable_income'])==18000
    assert Decimal(result['final_tax'])==4320


def test_current_business_loss_can_offset_other_income_after_aggregation():
    case,basis=inputs();case.update(claimed_deductions='120000',carried_losses='100000')
    work=basis['workpaper'];work['sources'][0].update(deductions='120000',statutory_allowances='0');work['allowed_total_income_deductions']=[]
    rec=reconcile_company(IncomeTaxCase(**case),CompanyWorkpaper(**work))
    assert rec['prior_losses_used']==0
    assert rec['current_losses_used']==20000
    assert rec['chargeable_income']==0


def test_unused_capital_allowance_does_not_become_current_business_loss():
    case,basis=inputs();case['claimed_deductions']='202000';basis['workpaper']['sources'][0]['statutory_allowances']='200000'
    rec=reconcile_company(IncomeTaxCase(**case),CompanyWorkpaper(**basis['workpaper']))
    assert rec['sources'][0]['unused_allowances']==100000
    assert rec['current_losses_used']==0
    assert rec['chargeable_income']==18000


@pytest.mark.parametrize('change',['missing','base','deductions','duplicate','unverified'])
def test_incomplete_or_inconsistent_company_workpaper_is_rejected(change):
    case,basis=inputs()
    if change=='missing':basis.pop('workpaper')
    if change=='base':basis['chargeable_income']='120000'
    if change=='deductions':case['claimed_deductions']='0'
    if change=='duplicate':basis['workpaper']['sources'][1]['income_index']=0
    if change=='unverified':basis['workpaper']['standalone_ordinary_verified']=False
    with pytest.raises(ValueError):calculate(IncomeTaxCase(**case),TypeAdapter(Assessment).validate_python(basis))
