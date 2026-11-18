from decimal import Decimal, localcontext
from hashlib import sha256
from pathlib import Path

import pytest

from packages.income_tax.china_personal_rental import monthly_expense_base
from packages.income_tax.china_personal_rental import repair_ledger


def repair_paper():
    return dict(opening_eligible_repairs='300',
        same_property_history_and_monthly_eligibility_verified=True,
        months=[dict(month=m, eligible_new_repairs='2000' if m==1 else '0',
                     established_repair_deduction='800' if m in (1,2) else '0') for m in range(1,13)])


def test_repair_chronology_conservation_and_year_end_balance():
    paper = repair_paper()
    result = repair_ledger(paper)
    assert result['closing_eligible_repairs'] == 700
    assert result['total_repair_deductions'] == 1600
    assert result['opening_eligible_repairs'] + result['total_new_repairs'] == result['total_repair_deductions'] + result['closing_eligible_repairs']
    assert result['months'][1]['opening_eligible_repairs'] == 1500
    paper['months'].reverse()
    assert repair_ledger(paper) == result
    with localcontext() as ctx:
        ctx.prec = 3
        assert repair_ledger(paper) == result
    for source in result['sources']:
        assert sha256(Path(source['file']).read_bytes()).hexdigest() == source['sha256']


@pytest.mark.parametrize('issue', ['missing', 'duplicate', 'cap', 'future', 'unverified'])
def test_invalid_repair_history_rejected(issue):
    paper = repair_paper()
    if issue == 'missing': paper['months'].pop()
    elif issue == 'duplicate': paper['months'][1]['month'] = 1
    elif issue == 'cap': paper['months'][0]['established_repair_deduction'] = '800.000001'
    elif issue == 'future':
        paper['months'][0]['eligible_new_repairs'] = '0'
        paper['months'][2]['eligible_new_repairs'] = '2000'
    else: paper['same_property_history_and_monthly_eligibility_verified'] = False
    with pytest.raises(ValueError): repair_ledger(paper)


def test_unused_repairs_preserved_in_inactive_months():
    paper = repair_paper()
    for row in paper['months']: row['established_repair_deduction'] = '0'
    assert repair_ledger(paper)['closing_eligible_repairs'] == 2300


@pytest.mark.parametrize('gross,deductions,base', [
    ('5000', '1200', '3000'),  # Gross exceeds4000, but the relevant balance does not.
    ('5000', '1000', '3200'),
    ('5000', '999.999999', '3200.0000008'),
    ('5000', '0', '4000'),
    ('800', '0', '0'),
    ('600', '0', '0'),
    ('800', '800', '0'),
    ('0', '0', '0'),
])
def test_monthly_threshold_after_preceding_deductions(gross, deductions, base):
    result = monthly_expense_base(gross, deductions)
    assert result['income_after_statutory_expense'] == Decimal(base)
    assert result['statutory_expense'] + result['income_after_statutory_expense'] == Decimal(gross) - Decimal(deductions)


def test_annual_aggregation_does_not_replace_monthly_calculation():
    monthly = sum(monthly_expense_base('1000', '0')['income_after_statutory_expense'] for _ in range(12))
    assert monthly == 2400
    assert monthly_expense_base('12000', '0')['income_after_statutory_expense'] == 9600


@pytest.mark.parametrize('gross,deductions', [('500', '501'), ('-1', '0'), ('1.0000001', '0'), (True, '0'), ('NaN', '0')])
def test_unestablished_negative_balance_and_invalid_money_rejected(gross, deductions):
    with pytest.raises(ValueError):
        monthly_expense_base(gross, deductions)


def test_context_independence_and_archived_sources():
    expected = monthly_expense_base('5000', '999.999999')
    with localcontext() as ctx:
        ctx.prec = 4
        assert monthly_expense_base('5000', '999.999999') == expected
    for source in expected['sources']:
        assert sha256(Path(source['file']).read_bytes()).hexdigest() == source['sha256']
