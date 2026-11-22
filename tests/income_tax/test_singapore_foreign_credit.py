from decimal import Decimal
import pytest
from packages.income_tax.singapore_foreign_credit import calculate


def paper(pooled=False):
    def row(country,gross,tax):
        return dict(country=country,gross=gross,eligible_foreign_tax=tax,
            pool_elected=pooled and country!='sg',headline_rate_percent='20',
            credit_entitlement_verified=True)
    return dict(groups=[dict(source_id='services',kind='trade',deductions='15000',
        sources=[row('sg','300000','0'),row('my','50000','10000')]),
        dict(source_id='interest',kind='passive',deductions='100',
        sources=[row('jp','20000','1000')])],singapore_tax_before_credit='42738',
        resident_same_income_and_allocation_verified=True)


@pytest.mark.parametrize('pooled,expected',[(False,'6763.08'),(True,'8159.49')])
def test_iras_official_example(pooled,expected):
    result=calculate(paper(pooled))
    assert result['allowed_foreign_tax_credit'].quantize(Decimal('.01'))==Decimal(expected)
    assert result['total_statutory_income']==354900


@pytest.mark.parametrize('change',['duplicate','passive_mix','loss','domestic_credit','low_rate','unpaid_pool','unverified'])
def test_invalid_allocations(change):
    p=paper(True)
    if change=='duplicate': p['groups'].append(p['groups'][0])
    if change=='passive_mix': p['groups'][1]['sources'].append(p['groups'][0]['sources'][0])
    if change=='loss': p['groups'][1]['deductions']='20001'
    if change=='domestic_credit': p['groups'][0]['sources'][0]['eligible_foreign_tax']='1'
    if change=='low_rate': p['groups'][1]['sources'][0]['headline_rate_percent']='14.99'
    if change=='unpaid_pool': p['groups'][1]['sources'][0]['eligible_foreign_tax']='0'
    if change=='unverified': p['resident_same_income_and_allocation_verified']=False
    with pytest.raises(ValueError): calculate(p)


def test_partial_pool_preserves_unpooled_source_limit():
    p=paper(True)
    p['groups'][1]['sources'][0]['pool_elected']=False
    assert calculate(p)['allowed_foreign_tax_credit']==calculate(paper(False))['allowed_foreign_tax_credit']
