from copy import deepcopy
from decimal import Decimal
import pytest
from pydantic import TypeAdapter
from packages.contracts.income_assessment import Assessment
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.assessment import calculate
from tests.income_tax.test_vietnam_workflow import test_api_persists_vietnam_provenance_and_result_after_restart as persist


def facts():
    return dict(subject='individual',jurisdiction='vn',currency='VND',period_start='2026-01-01',
        period_end='2026-12-31',residency='resident',facts_confirmed=True,carried_losses='0',
        claimed_deductions='600000000',incomes=[dict(category='capital_gain',source_jurisdiction='vn',
        gross_amount='1000000000',description='Verified ordinary transfer proceeds')])


def basis():
    return dict(policy='vn_personal_transfer_2026',basis_confirmed=True,
        basis_explanation='Verified transaction classification and statutory price and documented costs.',
        transfers=[dict(income_index=0,recognition_date='2026-07-01',asset_kind='capital_interest',
            purchase_cost='600000000',transfer_costs='0',cost_basis_established=True,
            ordinary_sale_confirmed=True,classification_valuation_and_scope_verified=True,prepaid_tax='0')])


def run(f,b):return calculate(IncomeTaxCase(**f),TypeAdapter(Assessment).validate_python(b))


def test_saved_proceeds_used_and_each_transaction_loss_kept_separate():
    f,b=facts(),basis()
    assert Decimal(run(f,b)['final_tax'])==80000000
    f['incomes'].append(dict(f['incomes'][0],gross_amount='100000000'))
    f['claimed_deductions']='1200000000'
    b['transfers'].append(dict(b['transfers'][0],income_index=1))
    r=run(f,b)
    assert Decimal(r['final_tax'])==80000000
    assert Decimal(r['transfers'][1]['final_tax'])==0
    f['incomes'][0]['gross_amount']='1100000000'
    assert Decimal(run(f,b)['final_tax'])==100000000


@pytest.mark.parametrize('indices',[[0,0],[],[1],[True]])
def test_missing_duplicate_or_coerced_binding_rejected(indices):
    f,b=facts(),basis();line=b['transfers'][0]
    b['transfers']=[dict(line,income_index=i) for i in indices]
    with pytest.raises(ValueError):run(f,b)


@pytest.mark.parametrize('field,value',[('subject','company'),('carried_losses','1'),
    ('claimed_deductions','1'),('residency','undetermined')])
def test_case_scope_rejected(field,value):
    f=facts();f[field]=value
    with pytest.raises(ValueError):run(f,basis())


@pytest.mark.parametrize('change',[dict(category='dividend'),dict(foreign_tax_paid='1'),
    dict(source_jurisdiction='sg',foreign_tax_paid='0')])
def test_other_income_rejected(change):
    f=facts();f['incomes'][0].update(change)
    with pytest.raises(ValueError):run(f,basis())


def test_nonresident_reference_and_api_restart(tmp_path):
    f=facts();f['residency']='nonresident'
    assert run(f,basis())['transfers'][0]['legal_basis'][0].endswith('#23')
    persist(tmp_path,facts,basis,80000000,'6b4803e79a068a7ed5727cfe174e337bbb8b1dbb1b1e48f72119b5f5825e9685')
