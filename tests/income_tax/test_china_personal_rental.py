from decimal import Decimal, localcontext
from hashlib import sha256
from pathlib import Path

import pytest

from packages.income_tax.china_personal_rental import monthly_expense_base
from packages.income_tax.china_personal_rental import repair_ledger
from packages.income_tax.china_personal_rental import calculate
from packages.contracts.income_tax import IncomeTaxCase
from tests.income_tax.test_china_personal_foreign_assessment import facts


def rental_case_and_papers():
    data = facts()
    data['incomes'] = [dict(category='rental', source_jurisdiction='sg', gross_amount='60000', foreign_tax_paid='0', description='One ordinary non-housing property')]
    months = [dict(month=m, gross_income='5000', eligible_taxes_and_fees='200', eligible_sublease_rent='200',
                   eligible_new_repairs='2000' if m==1 else '0', established_repair_deduction='800' if m in (1,2) else '0',
                   allowed_donation='0', allowed_tax_reduction='0') for m in range(1,13)]
    paper = dict(income_index=0, property_id='sg-property-1', opening_eligible_repairs='300', months=months,
        ordinary_rate_source_and_monthly_allocation_verified=True,
        property_aggregation_deductions_and_history_verified=True)
    return IncomeTaxCase(**data), [paper]


def test_annual_rental_reconciles_monthly_tax_and_repair_use():
    case, papers = rental_case_and_papers()
    result = calculate(case, papers)
    prop = result['properties'][0]
    assert prop['months'][0]['taxable_income'] == 3000
    assert prop['months'][2]['taxable_income'] == 3680
    assert result['tax_after_reduction'] == 8560
    assert result['established_deductions'] == 6400  # Only repairs used, not repairs paid.
    assert prop['repair_ledger']['closing_eligible_repairs'] == 700
    for source in result['sources']:
        assert sha256(Path(source['file']).read_bytes()).hexdigest() == source['sha256']
    with localcontext() as ctx:
        ctx.prec = 3
        assert calculate(case, papers) == result


@pytest.mark.parametrize('issue', ['annual_sum', 'missing_paper', 'duplicate_paper', 'missing_month', 'donation', 'reduction', 'negative_balance', 'unverified'])
def test_annual_rental_invalid_workpapers_rejected(issue):
    case, papers = rental_case_and_papers()
    if issue == 'annual_sum': papers[0]['months'][0]['gross_income'] = '4999'
    elif issue == 'missing_paper': papers.clear()
    elif issue == 'duplicate_paper': papers.append(papers[0])
    elif issue == 'missing_month': papers[0]['months'].pop()
    elif issue == 'donation': papers[0]['months'][0]['allowed_donation'] = '3001'
    elif issue == 'reduction': papers[0]['months'][0]['allowed_tax_reduction'] = '601'
    elif issue == 'negative_balance': papers[0]['months'][0]['eligible_taxes_and_fees'] = '5001'
    else: papers[0]['ordinary_rate_source_and_monthly_allocation_verified'] = False
    with pytest.raises(ValueError): calculate(case, papers)


def test_rental_tax_enters_saved_case_country_credit_limit():
    from tests.income_tax.test_china_personal_foreign_assessment import basis, run
    case, papers = rental_case_and_papers()
    data = case.model_dump(mode='json')
    data['claimed_deductions'] = '6400'
    data['incomes'][0]['foreign_tax_paid'] = '10000'
    paper = basis()
    paper['prepaid_tax'] = '0'
    paper['workpaper']['rentals'] = papers
    paper['workpaper']['countries'] = [dict(country='sg', business_deductions='0', business_prior_losses='0', eligible_foreign_tax_paid='10000', prior_excess=[])]
    result = run(data, paper)
    assert Decimal(result['tax_before_foreign_credit']) == 8560
    assert Decimal(result['allowed_credit']) == 8560
    assert Decimal(result['final_tax']) == 0
    assert Decimal(result['country_limits'][0]['credit_limit']) == 8560
    assert result['property_rentals']['properties'][0]['property_id'] == 'sg-property-1'
    data['claimed_deductions'] = '6800'  # Repairs incurred are not the deduction used.
    with pytest.raises(ValueError): run(data, paper)


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
