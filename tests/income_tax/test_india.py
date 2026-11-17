from decimal import Decimal, localcontext
import hashlib
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from packages.contracts.income_assessment import Assessment
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.assessment import calculate

from packages.income_tax.india import annual_tax, round_rupees, settle


def assess(base, **changes):
    args = dict(period_start='2026-04-01', period_end='2027-03-31',
                regime='personal_new_resident', regime_and_base_verified=True,
                ordinary_domestic_scope_confirmed=True)
    args.update(changes)
    return annual_tax(base, **args)


@pytest.mark.parametrize('base,expected', [
    ('0',0), ('400000',0), ('1200000',0), ('1200004.99',0),
    ('1200005',10), ('1210000',10400), ('1270000',72800),
    ('1600000',124800), ('2000000',208000), ('2400000',312000),
    ('5000000',1123200), ('10000000',2951520), ('20000000',6673680)])
def test_new_regime_annual_liability(base, expected):
    assert assess(base)['final_tax'] == expected


@pytest.mark.parametrize('base,prior_tax', [
    ('5000010',1080000), ('10000010',2838000), ('20000010',6417000)])
def test_surcharge_marginal_relief_before_cess(base, prior_tax):
    result = assess(base)
    # At each discontinuity, combined tax/surcharge grows by only INR 10;
    # cess is then imposed on the relieved amount, not on gross surcharge.
    assert result['income_tax_after_rebate'] + result['surcharge'] == prior_tax + 10
    assert result['health_education_cess'] == Decimal(prior_tax + 10) * Decimal('.04')
    assert result['surcharge_marginal_relief'] > 0


@pytest.mark.parametrize('base,expected', [('0',0),('1000000',251680),('10000000',2516800)])
def test_company_fixed_surcharge_and_no_resident_rebate(base, expected):
    result = assess(base, regime='company_section200')
    assert result['final_tax'] == expected
    assert result['resident_rebate'] == 0
    assert result['surcharge_marginal_relief'] == 0


@pytest.mark.parametrize('value,expected', [('14.99',10),('15',20),('4.99',0),('5',10)])
def test_statutory_rounding(value, expected):
    assert round_rupees(value) == expected


@pytest.mark.parametrize('changes', [
    {'period_start':'2025-04-01'}, {'period_end':'2026-03-31'},
    {'regime':'personal_old'}, {'regime':'company_normal'},
    {'regime_and_base_verified':1}, {'ordinary_domestic_scope_confirmed':'true'}])
def test_reject_unreviewed_period_or_unverified_election(changes):
    with pytest.raises(ValueError):
        assess('1000000', **changes)


@pytest.mark.parametrize('base', [True, 1.5, '-1', 'NaN', 'Infinity', '1e19'])
def test_invalid_amount(base):
    with pytest.raises(ValueError):
        assess(base)


def test_precision_is_independent_of_ambient_context():
    expected = assess('20000010.99')
    with localcontext() as context:
        context.prec = 6
        assert assess('20000010.99') == expected


def test_sources_match_original_files_and_results_are_not_shared():
    root = Path(__file__).resolve().parents[2]
    result = assess('1600000')
    for source in result['sources']:
        assert hashlib.sha256((root / source['file']).read_bytes()).hexdigest() == source['sha256']
    result['sources'].clear()
    assert len(assess('1600000')['sources']) == 2


def workflow(subject='individual', **changes):
    facts = dict(subject=subject, jurisdiction='in', currency='INR', residency='resident',
        period_start='2026-04-01', period_end='2027-03-31', facts_confirmed=True,
        incomes=[dict(category='business',source_jurisdiction='in',gross_amount='1700000',description='Domestic ordinary business')],
        claimed_deductions='100000',carried_losses='0')
    facts.update(changes)
    basis = dict(policy='in_personal_new_ty2026_27' if subject=='individual' else 'in_company_section200_ty2026_27',
        taxable_income_before_rounding='1600000', regime_and_base_verified=True,
        ordinary_domestic_scope_confirmed=True, basis_confirmed=True,
        basis_explanation='Ordinary domestic base reconciled; regime election and permitted deductions verified.')
    return IncomeTaxCase(**facts), TypeAdapter(Assessment).validate_python(basis)


@pytest.mark.parametrize('subject,expected',[('individual',124800),('company',402690)])
def test_saved_workflow(subject,expected):
    result=calculate(*workflow(subject))
    assert Decimal(result['final_tax']) == expected
    assert result['tax_year']=='2026-27'


@pytest.mark.parametrize('changes',[
    {'residency':'nonresident'}, {'period_start':'2025-04-01','period_end':'2026-03-31'},
    {'claimed_deductions':'99999'}, {'carried_losses':'1'},
    {'incomes':[dict(category='capital_gain',source_jurisdiction='in',gross_amount='1700000',description='Special rate')]},
    {'incomes':[dict(category='business',source_jurisdiction='sg',gross_amount='1700000',foreign_tax_paid='0',description='Foreign source')]}
])
def test_saved_workflow_rejects_mismatches(changes):
    with pytest.raises(ValueError):
        calculate(*workflow(**changes))


def payments(**changes):
    values=dict(tds_tcs_credit='0', advance_tax_paid='0', self_assessment_paid='0',
                total_interest_due='0', total_fee_due='0', settlement_verified=True)
    values.update(changes)
    return values


@pytest.mark.parametrize('credit,net', [('6',124800),('124806',0),('124807',0),('124808',-10)])
def test_settlement_rounds_net_not_previously_rounded_annual_tax(credit,net):
    annual=assess('1600010')
    assert annual['annual_tax_before_rounding']==Decimal('124802.080')
    result=settle(annual,**payments(tds_tcs_credit=credit))
    assert result['balance_due']==net
    assert result['tax_payable']==max(net,0)
    assert result['refund_due']==max(-net,0)
    assert 'balance_due' not in annual


def test_settlement_includes_all_payments_and_cumulative_interest_fees():
    result=settle(assess('1600000'),**payments(tds_tcs_credit='100000',
        advance_tax_paid='20000',self_assessment_paid='1000',total_interest_due='1200',total_fee_due='5000'))
    assert result['total_payments']==121000
    assert result['balance_due']==10000
    assert result['refund_interest_calculated'] is False


@pytest.mark.parametrize('changes',[{'settlement_verified':1},{'tds_tcs_credit':None},
    {'advance_tax_paid':-1},{'total_interest_due':'NaN'},{'self_assessment_paid':True}])
def test_settlement_rejects_unknown_unverified_and_invalid(changes):
    with pytest.raises(ValueError):
        settle(assess('1600000'),**payments(**changes))


def test_saved_settlement_explicit_and_backward_compatible():
    case,basis=workflow()
    assert 'balance_due' not in calculate(case,basis)
    values=basis.model_dump()
    values.update(payments(tds_tcs_credit='130000'),settlement_requested=True)
    result=calculate(case,TypeAdapter(Assessment).validate_python(values))
    assert Decimal(result['balance_due'])==-5200
    values['settlement_requested']=False
    with pytest.raises(ValueError,match='explicit settlement'):
        calculate(case,TypeAdapter(Assessment).validate_python(values))


def test_missing_payment_is_not_assumed_zero():
    case,basis=workflow()
    values=basis.model_dump()
    values.update(payments(),settlement_requested=True)
    del values['advance_tax_paid']
    with pytest.raises(ValueError):
        calculate(case,TypeAdapter(Assessment).validate_python(values))


def old(base, age='under60', **changes):
    args=dict(regime='personal_old_resident',resident_age_band=age,amt_not_applicable_verified=True)
    args.update(changes)
    return assess(base,**args)


@pytest.mark.parametrize('age,base,tax',[
    ('under60','500000',0),('60_to79','500000',0),('80_plus','500000',0),
    ('under60','500010',13000),('60_to79','500010',10400),('80_plus','500010',0),
    ('under60','1000000',117000),('60_to79','1000000',114400),('80_plus','1000000',104000),
    ('under60','1600000',304200),('60_to79','1600000',301600),('80_plus','1600000',291200),
    # (112500 + 59000000 * .30) * 1.37 * 1.04 = 25379250.
    ('under60','60000000',25379250)])
def test_old_resident_bands_and_no_rebate_marginal_relief(age,base,tax):
    result=old(base,age)
    assert result['final_tax']==tax
    if Decimal(base)>500000:
        assert result['resident_rebate']==0


@pytest.mark.parametrize('base,previous_combined',[
    ('5000010','1312500'),('10000010','3093750'),
    ('20000010','6684375'),('50000010','18515625')])
def test_old_surcharge_four_discontinuities(base,previous_combined):
    result=old(base)
    assert result['income_tax_after_rebate']+result['surcharge']==Decimal(previous_combined)+10
    assert result['surcharge_marginal_relief']>0


@pytest.mark.parametrize('changes',[{'resident_age_band':None},{'resident_age_band':'80'},
    {'amt_not_applicable_verified':False},{'amt_not_applicable_verified':1}])
def test_old_age_and_amt_must_be_explicit(changes):
    with pytest.raises(ValueError):old('1600000',**changes)


def test_old_workflow_settlement_and_subject_validation():
    case,basis=workflow()
    values=basis.model_dump()
    values.update(policy='in_personal_old_ty2026_27',resident_age_band='60_to79',amt_not_applicable_verified=True,
                  settlement_requested=True,**payments(tds_tcs_credit='310000'))
    validated=TypeAdapter(Assessment).validate_python(values)
    result=calculate(case,validated)
    assert Decimal(result['final_tax'])==301600
    assert Decimal(result['balance_due'])==-8400
    case.subject='company'
    with pytest.raises(ValueError,match='subject'):
        calculate(case,validated)
