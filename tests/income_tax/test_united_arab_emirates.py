from decimal import Decimal
import hashlib
from pathlib import Path
import pytest
from packages.income_tax.united_arab_emirates import (
    SOURCES, natural_person_scope, ordinary_corporate_tax,
)


def tax(base, **kwargs):
    args = dict(tax_year=2026, subject_type='company', ordinary_regime_confirmed=True,
                no_relief_elected_confirmed=True, allowed_foreign_tax_credit='0', prepaid_tax='0')
    args.update(kwargs)
    return ordinary_corporate_tax(base, **args)


def scope(turnover, **kwargs):
    args = dict(tax_year=2026, excluded_wages='0', excluded_personal_investment='0',
                excluded_real_estate_investment='0', activity_classification_confirmed=True)
    args.update(kwargs)
    return natural_person_scope(turnover, **args)


@pytest.mark.parametrize('base,expected', [('0','0'),('375000','0'),('375000.01','.0009'),
                                         ('1000000','56250')])
def test_ordinary_threshold_and_fta_example(base, expected):
    assert tax(base)['final_tax'] == Decimal(expected)


def test_fta_natural_person_example_17():
    # CTGTNP1 pp25-26: freelance 1.6m + shop domestic 1.2m + foreign 0.8m.
    # Wage 200k is excluded. Verified deductible expenses 400k + 1.4m.
    result = scope('3600000', excluded_wages='200000')
    assert result['within_corporate_tax_scope'] is True
    assert tax('1800000', subject_type='individual',
               natural_person_business_turnover='3600000')['final_tax'] == Decimal('128250')


@pytest.mark.parametrize('turnover,expected', [('0',False),('1000000',False),('1000000.01',True)])
def test_turnover_threshold_excludes_statutory_personal_income(turnover, expected):
    result = scope(turnover, excluded_wages='2000000', excluded_personal_investment='4000000',
                   excluded_real_estate_investment='5000000')
    assert result['within_corporate_tax_scope'] is expected
    assert 'final_tax' not in result


@pytest.mark.parametrize('kwargs', [dict(tax_year=2025),dict(tax_year=True),
    dict(subject_type='partnership'),dict(ordinary_regime_confirmed=1),
    dict(no_relief_elected_confirmed=False),dict(subject_type='individual'),
    dict(subject_type='individual',natural_person_business_turnover='1000000'),
    dict(natural_person_business_turnover='2000000'),dict(allowed_foreign_tax_credit='56251')])
def test_unsupported_or_unconfirmed_inputs_fail(kwargs):
    with pytest.raises(ValueError):
        tax('1000000', **kwargs)


@pytest.mark.parametrize('bad', [None,True,1.2,'NaN','-1','0.0000001'])
def test_invalid_money_fails(bad):
    with pytest.raises(ValueError):
        tax(bad)


def test_credit_and_prepaid_are_separate():
    result = tax('1000000', allowed_foreign_tax_credit='6250', prepaid_tax='60000')
    assert result['final_tax'] == Decimal('50000')
    assert result['balance_due'] == Decimal('-10000')


def test_classification_required_and_sources_are_immutable():
    with pytest.raises(ValueError):
        scope('2000000', activity_classification_confirmed=1)
    tax('0')['sources'][0]['sha256'] = 'changed'
    root = Path(__file__).resolve().parents[2]
    for source in SOURCES:
        assert hashlib.sha256((root/source['file']).read_bytes()).hexdigest() == source['sha256']
