from decimal import Decimal
import pytest
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.china_personal_transfers import calculate
from tests.income_tax.test_china_personal_foreign_assessment import facts


def data():
    d=facts();d['incomes']=[dict(category='capital_gain',source_jurisdiction='sg',gross_amount=v,foreign_tax_paid='0',description='One ordinary sale; amount is gross proceeds') for v in ['1000','1000']]
    return IncomeTaxCase(**d)


def papers():
    return [dict(income_index=n,original_cost=c,reasonable_transfer_expenses='100',allowed_donation='0',allowed_tax_reduction='0',single_transaction_source_and_ordinary_rate_verified=True,original_cost_expenses_and_reliefs_verified=True) for n,c in [(0,'400'),(1,'2000')]]


def test_profit_and_loss_transactions_are_not_netted():
    r=calculate(data(),papers())
    assert r['tax_after_reduction']==100
    assert r['transactions'][0]['taxable_income']==500
    assert r['transactions'][1]['unoffset_loss']==1100
    assert r['transactions'][1]['tax_after_reduction']==0


def test_donation_then_tax_reduction():
    p=papers();p[0].update(allowed_donation='100',allowed_tax_reduction='20')
    assert calculate(data(),p)['tax_after_reduction']==60


@pytest.mark.parametrize('issue',['missing','duplicate','wrong_index','unverified','cost_unverified','donation','reduction'])
def test_unreconciled_transactions_rejected(issue):
    p=papers()
    if issue=='missing':p.pop()
    elif issue=='duplicate':p[1]['income_index']=0
    elif issue=='wrong_index':p[1]['income_index']=3
    elif issue=='unverified':p[0]['single_transaction_source_and_ordinary_rate_verified']=False
    elif issue=='cost_unverified':p[0]['original_cost_expenses_and_reliefs_verified']=False
    elif issue=='donation':p[0]['allowed_donation']='501'
    else:p[0]['allowed_tax_reduction']='101'
    with pytest.raises(ValueError):calculate(data(),p)


def test_source_hashes_and_decimal_context():
    from decimal import localcontext
    from pathlib import Path
    from hashlib import sha256
    expected=calculate(data(),papers())
    with localcontext() as ctx:
        ctx.prec=4
        assert calculate(data(),papers())==expected
    for s in expected['sources']:assert sha256(Path(s['file']).read_bytes()).hexdigest()==s['sha256']
