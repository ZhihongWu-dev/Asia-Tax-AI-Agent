from decimal import Decimal, localcontext
import hashlib
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from packages.contracts.income_assessment import Assessment
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.assessment import calculate

from packages.income_tax.india import annual_tax, round_rupees


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
