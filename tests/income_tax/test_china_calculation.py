from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import pytest
from packages.income_tax.china import resident_comprehensive_tax, normal_company_tax


def personal(**changes):
    values = dict(tax_year=2026, wages='0', service_remuneration='0', author_remuneration='0',
                  royalties='0', allowed_special_deductions='0', allowed_additional_deductions='0',
                  allowed_other_deductions='0', allowed_donations='0', allowed_tax_reductions='0',
                  prepaid_tax='0', domestic_normal_treatment_confirmed=True)
    values.update(changes)
    return resident_comprehensive_tax(**values)


@pytest.mark.parametrize('base,rate,quick', [
    ('36000','.03','0'), ('144000','.10','2520'), ('300000','.20','16920'),
    ('420000','.25','31920'), ('660000','.30','52920'), ('960000','.35','85920'),
    ('1200000','.45','181920')])
def test_annual_schedule_matches_official_quick_deduction_table(base, rate, quick):
    result = personal(wages=D(base)+D('60000'))
    assert result['gross_tax'] == D(base)*D(rate)-D(quick)


@pytest.mark.parametrize('boundary,next_rate', [('36000','.10'),('144000','.20'),('300000','.25'),
    ('420000','.30'),('660000','.35'),('960000','.45')])
def test_one_yuan_above_threshold_has_only_next_marginal_rate(boundary,next_rate):
    wages=D(boundary)+D('60000')
    assert personal(wages=wages+1)['gross_tax']-personal(wages=wages)['gross_tax']==D(next_rate)


def test_income_categories_expense_reductions_and_refund():
    result=personal(wages='120000', service_remuneration='10000', author_remuneration='10000',
                    royalties='10000', allowed_special_deductions='12000', allowed_additional_deductions='24000',
                    prepaid_tax='2000')
    assert result['assessable_comprehensive_income']==D('141600')
    assert result['taxable_income']==D('45600')
    assert result['gross_tax']==D('2040')
    assert result['balance_due']==D('40')
    assert personal(wages='50000',prepaid_tax='500')['balance_due']==D('-500')


def test_normal_company_credits_and_prepayments_are_separate():
    result=normal_company_tax('1000000',tax_year=2026,normal_rate_confirmed=True,
                              allowed_tax_credits='20000',prepaid_tax='240000')
    assert result['gross_tax']==D('250000')
    assert result['annual_liability']==D('230000')
    assert result['balance_due']==D('-10000')


@pytest.mark.parametrize('changes', [dict(tax_year=2025),dict(tax_year=True),
    dict(domestic_normal_treatment_confirmed=False),dict(domestic_normal_treatment_confirmed=1),
    dict(wages=1.2),dict(wages='NaN'),dict(allowed_tax_reductions='1'),dict(allowed_donations='1')])
def test_invalid_or_unconfirmed_personal_inputs_fail(changes):
    with pytest.raises(ValueError): personal(**changes)


def test_company_cannot_default_to_standard_rate_or_overclaim_credit():
    with pytest.raises(ValueError):
        normal_company_tax('100',tax_year=2026,normal_rate_confirmed=False,allowed_tax_credits='0',prepaid_tax='0')
    with pytest.raises(ValueError):
        normal_company_tax('100',tax_year=2026,normal_rate_confirmed=True,allowed_tax_credits='26',prepaid_tax='0')


def test_sources_match_immutable_manifest():
    root=Path(__file__).resolve().parents[2]
    manifest=json.loads((root/'packages/income_tax/cn_2026_sources.json').read_text(encoding='utf-8'))
    for source in manifest['sources']:
        assert hashlib.sha256((root/source['file']).read_bytes()).hexdigest()==source['sha256']
