from decimal import Decimal as D
import hashlib,json
from pathlib import Path
import pytest
from packages.income_tax.hong_kong import salaries_tax, profits_tax


def salary(net,**kwargs):
    options=dict(assessment_year='2025/26',allowed_allowances='0',prepaid_final_tax='0',ordinary_separate_assessment_confirmed=True)
    options.update(kwargs)
    return salaries_tax(net,**options)


def profit(base,**kwargs):
    options=dict(assessment_year='2025/26',business_form='corporation',two_tier_eligible=True,ordinary_regime_confirmed=True,prepaid_final_tax='0')
    options.update(kwargs)
    return profits_tax(base,**options)


@pytest.mark.parametrize('base,cumulative',[('50000','1000'),('100000','4000'),('150000','9000'),('200000','16000'),('300000','33000')])
def test_progressive_schedule_cumulative_values(base,cumulative):
    assert salary(base)['progressive_tax']==D(cumulative)


def test_standard_rate_uses_net_income_before_allowances_and_two_tiers():
    result=salary('6000000',allowed_allowances='132000')
    assert result['net_chargeable_income']==D('5868000')
    assert result['standard_rate_tax']==D('910000')
    assert result['selected_basis']=='standard'
    assert result['final_tax']==D('907000')
    assert salary('5000001')['standard_rate_tax']-salary('5000000')['standard_rate_tax']==D('.16')


def test_allowance_does_not_reduce_standard_basis():
    result=salary('200000',allowed_allowances='132000')
    assert result['net_chargeable_income']==D('68000')
    assert result['standard_rate_tax']==D('30000')
    assert result['gross_tax']==D('2080')
    assert result['final_tax']==0


@pytest.mark.parametrize('form,expected',[('corporation','247500'),('sole_proprietor','225000')])
def test_two_tier_profits(form,expected):
    result=profit('2500000',business_form=form)
    assert result['gross_tax']==D(expected)
    assert result['final_tax']==D(expected)-3000


def test_connected_entity_ineligible_does_not_receive_lower_tier():
    assert profit('2000000',two_tier_eligible=False)['gross_tax']==D('330000')
    assert profit('2000000')['gross_tax']==D('165000')
    assert profit('2000001')['gross_tax']-profit('2000000')['gross_tax']==D('.165')


def test_reduction_is_capped_at_tax_and_refund_is_preserved():
    assert profit('10000')['final_tax']==0
    assert salary('0',prepaid_final_tax='100')['balance_due']==D('-100')
    assert profit('0',prepaid_final_tax='100')['balance_due']==D('-100')


@pytest.mark.parametrize('changes',[{'assessment_year':'2026/27'},{'ordinary_regime_confirmed':False},{'two_tier_eligible':None},{'two_tier_eligible':1},{'business_form':'partnership'}])
def test_unreviewed_regimes_and_years_rejected(changes):
    with pytest.raises(ValueError):profit('100',**changes)


def test_source_hashes():
    root=Path(__file__).resolve().parents[2]
    manifest=json.loads((root/'packages/income_tax/hk_2025_26_sources.json').read_text(encoding='utf-8'))
    for source in manifest['sources']:
        assert hashlib.sha256((root/source['file']).read_bytes()).hexdigest()==source['sha256']


@pytest.mark.parametrize('net,allowances,prepaid,gross,final,balance',[
    ('380000','132000','10000','24160','21160','11160'),
    ('440000','394000','800','920','0','-800'),
])
def test_ird_2026_budget_examples_final_2025_26_assessment(net,allowances,prepaid,gross,final,balance):
    # IRD example2627.pdf examples 1 and 2, final 2025/26 columns only.
    # Provisional 2026/27 tax uses different allowances and is not this result.
    result=salary(net,allowed_allowances=allowances,prepaid_final_tax=prepaid)
    assert result['gross_tax']==D(gross)
    assert result['final_tax']==D(final)
    assert result['balance_due']==D(balance)
