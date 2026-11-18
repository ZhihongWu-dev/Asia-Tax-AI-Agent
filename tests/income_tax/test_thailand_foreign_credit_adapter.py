from dataclasses import replace
from datetime import date

import pytest

from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.thailand_foreign_credit import ForeignIncomePool, prepare_case_foreign_tax
from packages.income_tax.thailand_remittances import RemittanceTranche


def case():
    return IncomeTaxCase(subject='individual', jurisdiction='th', period_start='2026-01-01',
        period_end='2026-12-31', currency='THB', residency='resident', claimed_deductions=0,
        carried_losses=0, facts_confirmed=True, incomes=[dict(category='dividend',
        source_jurisdiction='sg', gross_amount='1000', foreign_tax_paid='200',
        description='Original pool tax; current-year remitted income')])


def tranche(value=1000, earned=date(2024,1,1), days=180, index=0):
    return RemittanceTranche(index,value,earned,date(2026,6,1),days)


def pool(**changes):
    return replace(ForeignIncomePool('certificate-A',0,'2000','200','100','500',
                                   (tranche(),)), **changes)


def run(pools=None, **changes):
    return prepare_case_foreign_tax(case(), pools if pools is not None else [pool()],
        tracing_fx_and_entitlement_verified=changes.get('verified',True))


def test_saved_case_reconciles_original_tax_and_remitted_fraction():
    result=run()['pools'][0]
    assert result['attributable_paid_tax']==100
    assert result['eligible_attributable_tax']==50
    assert result['remaining_income']==500
    assert result['country']=='sg' and result['category']=='dividend'


def test_pre2024_pool_does_not_generate_credit():
    pools=[pool(pool_id='old',total_foreign_income=500,foreign_income_tax_paid=50,
                eligible_foreign_income_tax_paid=50,previously_remitted_income=0,
                remittances=(tranche(400,date(2023,12,31)),)),
           pool(pool_id='new',total_foreign_income=1000,foreign_income_tax_paid=150,
                eligible_foreign_income_tax_paid=100,previously_remitted_income=0,
                remittances=(tranche(600),))]
    result=run(pools)
    assert result['pools'][0]['attributable_paid_tax']==0
    assert result['pools'][1]['attributable_paid_tax']==90
    assert result['pools'][1]['eligible_attributable_tax']==60
    assert result['remittance_reconciliation']['excluded_from_section41_remittance']==400


def test_split_remittance_does_not_repeat_original_tax():
    result=run([pool(remittances=(tranche(400),tranche(600)))])
    assert result['pools'][0]['attributable_paid_tax']==100


def test_nonresident_income_year_does_not_generate_credit():
    assert run([pool(remittances=(tranche(days=179),))])['pools'][0]['eligible_attributable_tax']==0


@pytest.mark.parametrize('changes', [
    {'previously_remitted_income':1001}, {'total_foreign_income':0},
    {'eligible_foreign_income_tax_paid':201}, {'foreign_income_tax_paid':201},
    {'income_index':True}, {'income_index':1}, {'remittances':()},
    {'remittances':(tranche(999),)}, {'remittances':(tranche(1001),)},
    {'remittances':(tranche(500),tranche(500,date(2025,1,1)))},
    {'remittances':(tranche(500,days=179),tranche(500,days=180))},
    {'pool_id':''}, {'pool_id':' '*3},
])
def test_inconsistent_or_excess_claims_fail(changes):
    with pytest.raises(ValueError):run([pool(**changes)])


def test_duplicate_pool_fails_even_when_receipts_would_reconcile():
    line=pool(remittances=(tranche(500),),foreign_income_tax_paid=100)
    with pytest.raises(ValueError,match='unique'):run([line,line])


@pytest.mark.parametrize('verified',[False,1,None])
def test_unverified_basis_rejected(verified):
    with pytest.raises(ValueError):run(verified=verified)
