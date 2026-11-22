from copy import deepcopy
import pytest
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.hong_kong_foreign_reconciliation import reconcile
from tests.income_tax.test_hong_kong_foreign_credit import fixture as credit_fixture


def fixture():
    case=IncomeTaxCase.model_validate(dict(subject='company',jurisdiction='hk',currency='HKD',
        period_start='2025-04-01',period_end='2026-03-31',residency='resident',
        facts_confirmed=True,claimed_deductions='100',carried_losses='0',incomes=[
            dict(category='business',source_jurisdiction='hk',gross_amount='1000',description='Domestic trade'),
            dict(category='dividend',source_jurisdiction='sg',gross_amount='500',foreign_tax_paid='100',description='Taxable FSIE dividend')]))
    p=dict(groups=[dict(source_id='domestic',income_indexes=[0],allowable_expenses='100',
        taxable_additions='0',excluded_income='0',underlying_tax_gross_up='0'),
        dict(source_id='receipt_a',income_indexes=[1],allowable_expenses='0',taxable_additions='0',
        excluded_income='0',underlying_tax_gross_up='200',foreign_credit=credit_fixture()['sources'][0])],
        receipt_year_source_exemptions_and_expenses_verified=True,
        gross_up_and_no_foreign_tax_in_expenses_verified=True,no_source_losses_or_special_regimes_verified=True)
    return case,p


def test_saved_receipts_expenses_and_underlying_tax_reconcile():
    case,p=fixture();result=reconcile(case,p)
    assert result['total_basis_before_excess_foreign_tax_deduction']==1600
    assert result['source_reconciliation'][1]['source_basis_before_excess_foreign_tax_deduction']==700
    assert result['foreign_credit_sources'][0]['direct_foreign_tax_paid']==100
    assert result['foreign_credit_sources'][0]['underlying_tax_paid']==200
    assert 'final_tax' not in result


def test_split_saved_receipts_have_same_source_basis():
    case,p=fixture();data=case.model_dump()
    data['incomes'][1]['gross_amount']='300';data['incomes'][1]['foreign_tax_paid']='60'
    extra=deepcopy(data['incomes'][1]);extra.update(gross_amount='200',foreign_tax_paid='40')
    data['incomes'].append(extra);p['groups'][1]['income_indexes']=[1,2]
    assert reconcile(IncomeTaxCase.model_validate(data),p)['total_basis_before_excess_foreign_tax_deduction']==1600


def test_exempt_foreign_receipt_is_preserved_without_credit():
    case,p=fixture();data=case.model_dump()
    data['incomes'].append(dict(category='interest',source_jurisdiction='cn',gross_amount='300',foreign_tax_paid='30',description='Verified exemption'))
    p['groups'].append(dict(source_id='exempt',income_indexes=[2],allowable_expenses='0',
        taxable_additions='0',excluded_income='300',underlying_tax_gross_up='0'))
    result=reconcile(IncomeTaxCase.model_validate(data),p)
    assert result['total_basis_before_excess_foreign_tax_deduction']==1600
    assert len(result['foreign_credit_sources'])==1


@pytest.mark.parametrize('change',['duplicate','omitted','negative_index','expenses','paid','country','category',
    'gross_up','excluded','zero_income','missing_credit','domestic_credit','evidence'])
def test_inconsistent_workpapers_rejected(change):
    case,p=fixture();g=p['groups'][1]
    if change=='duplicate':g['income_indexes']=[0,1]
    elif change=='omitted':p['groups']=p['groups'][1:]
    elif change=='negative_index':g['income_indexes']=[-1]
    elif change=='expenses':g['allowable_expenses']='1'
    elif change=='paid':g['foreign_credit']['direct_foreign_tax_paid']='101'
    elif change=='country':g['foreign_credit']['country']='cn'
    elif change=='category':g['foreign_credit']['income_type']='interest'
    elif change=='gross_up':g['underlying_tax_gross_up']='201'
    elif change=='excluded':g['excluded_income']='701'
    elif change=='zero_income':g['excluded_income']='700'
    elif change=='missing_credit':g['foreign_credit']=None
    elif change=='domestic_credit':p['groups'][0]['foreign_credit']=g['foreign_credit']
    else:p['gross_up_and_no_foreign_tax_in_expenses_verified']=False
    with pytest.raises(ValueError):reconcile(case,p)
