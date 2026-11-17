from datetime import date,datetime
from decimal import Decimal,localcontext
import hashlib
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from packages.income_tax.japan_company import company_tax,annual_period
from packages.contracts.income_assessment import Assessment
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.assessment import calculate


def inputs(**changes):
    args=dict(taxable_income_before_rounding='100000000',period_start='2026-04-01',period_end='2027-03-31',
        rate_regime='ordinary',rate_classification_verified=True,ordinary_no_adjustments_confirmed=True,
        corporation_interim_liability='0',local_corporation_interim_liability='0')
    args.update(changes);return args


def test_three_separate_national_components():
    r=company_tax(**inputs())
    assert r['corporation_tax']==23200000
    assert r['local_corporation_tax']==2389600
    assert r['defence_tax_base']==18200000
    assert r['defence_tax']==728000
    assert r['final_tax']==26317600
    assert r['local_taxes_calculated'] is False
    assert 'balance_due' not in r  # No automatic cross-tax offset.


def test_commencement_uses_period_start_not_end_or_calendar_year():
    before=company_tax(**inputs(period_start='2026-03-31',period_end='2027-03-30'))
    assert before['defence_tax']==0
    assert before['defence_return_required'] is False
    assert company_tax(**inputs())['defence_return_required'] is True
    assert company_tax(**inputs(taxable_income_before_rounding='0'))['defence_return_required'] is True


@pytest.mark.parametrize('regime,income,rate,corporation',[
    ('sme_reduced','8000000','.15',1200000),
    ('sme_reduced','10000000','.15',1664000),
    ('sme_excluded','10000000','.19',1984000),
    # JPY232m ordinary tax less the first-tier discount on JPY8m:
    # 656000 / 496000 / 336000 for 15% / 17% / 19% respectively.
    ('sme_reduced','1000000000','.15',231344000),
    ('sme_reduced','1000001000','.17',231504200),
    ('sme_excluded','1000000001','.19',231664000)])
def test_sme_first_tier_and_current_income_exclusion_boundaries(regime,income,rate,corporation):
    r=company_tax(**inputs(rate_regime=regime,taxable_income_before_rounding=income))
    assert r['lower_tier_rate']==Decimal(rate)
    assert r['corporation_tax']==corporation


def test_tax_bases_and_final_amounts_have_distinct_rounding():
    r=company_tax(**inputs(taxable_income_before_rounding='10001999'))
    assert r['taxable_income']==10001000
    assert r['corporation_tax_reference']==2320232
    assert r['corporation_tax']==2320200
    assert r['local_corporation_tax_base']==2320000
    assert r['local_corporation_tax']==238900
    assert r['defence_tax']==0


@pytest.mark.parametrize('income',['1000000001','1000000500','1000000999'])
def test_unresolved_sme_threshold_rounding_requires_review(income):
    with pytest.raises(ValueError,match='threshold rounding requires manual review'):
        company_tax(**inputs(rate_regime='sme_reduced',taxable_income_before_rounding=income))


def test_interim_notified_liability_is_deducted_per_tax_without_cross_offset():
    r=company_tax(**inputs(corporation_interim_liability='24000000',local_corporation_interim_liability='1000000'))
    assert r['corporation_balance_due']==-800000
    assert r['local_corporation_balance_due']==1389600
    assert r['defence_tax']==728000


@pytest.mark.parametrize('changes',[dict(rate_regime='sme'),dict(rate_classification_verified=1),
    dict(ordinary_no_adjustments_confirmed=False),dict(taxable_income_before_rounding='0.1'),
    dict(corporation_interim_liability='1'),dict(local_corporation_interim_liability=True),
    dict(period_start='2025-04-01',period_end='2026-03-31'),dict(period_end='2026-12-31'),
    dict(period_end='9999-12-31'),dict(period_start=datetime(2026,4,1)),dict(period_start='20260401')])
def test_unknown_facts_and_unreviewed_periods_fail(changes):
    with pytest.raises(ValueError):company_tax(**inputs(**changes))


def test_precision_source_hashes_and_mutation_isolation():
    with localcontext() as context:
        context.prec=6
        result=company_tax(**inputs())
        assert result['final_tax']==26317600
    root=Path(__file__).resolve().parents[2]
    for s in result['sources']:
        assert hashlib.sha256((root/s['file']).read_bytes()).hexdigest()==s['sha256']
    result['sources'][0]['sha256']='changed'
    assert company_tax(**inputs())['sources'][0]['sha256']!='changed'
    assert annual_period(date(2026,1,1),date(2026,12,31))==(date(2026,1,1),date(2026,12,31))


def facts():
    return dict(subject='company',jurisdiction='jp',currency='JPY',residency='resident',
        period_start='2026-04-01',period_end='2027-03-31',facts_confirmed=True,
        incomes=[dict(category='business',source_jurisdiction='jp',gross_amount='200000000',description='Annual domestic business revenue')],
        claimed_deductions='100000000',carried_losses='0')


def basis():
    value=inputs();value.pop('period_start');value.pop('period_end')
    return dict(policy='jp_company_starting_2026',basis_confirmed=True,
        basis_explanation='Ordinary domestic company annual base and rate classification checked; no credits or additions.',**value)


def test_saved_case_allows_reviewed_non_calendar_period():
    r=calculate(IncomeTaxCase(**facts()),TypeAdapter(Assessment).validate_python(basis()))
    assert Decimal(r['final_tax'])==26317600
    assert r['period_start']=='2026-04-01'


@pytest.mark.parametrize('changes',[dict(subject='individual'),dict(residency='nonresident'),
    dict(jurisdiction='sg',currency='SGD'),dict(period_end='2027-03-30')])
def test_saved_case_scope_rejected(changes):
    data=facts();data.update(changes)
    with pytest.raises(ValueError):calculate(IncomeTaxCase(**data),TypeAdapter(Assessment).validate_python(basis()))
