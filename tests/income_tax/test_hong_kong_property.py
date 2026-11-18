from copy import deepcopy
from decimal import Decimal
import pytest
from pydantic import ValidationError
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.assessment import calculate
from tests.income_tax.test_assessment_workflow import ADAPTER, COMMON, facts


def inputs():
    data = facts('hk', 'individual')
    data['incomes'] = [dict(category='rental', source_jurisdiction='hk',
        gross_amount='300000', description='Solely owned rental property, full consideration')]
    data['claimed_deductions'] = '30000'
    basis = dict(policy='hk_property_2025_26',
        properties=[dict(income_index=0, irrecoverable_rent='20000', owner_rates_paid='10000')],
        sole_ownership_and_separate_assessment_verified=True,
        consideration_and_deductions_verified=True, prepaid_final_tax='35000', **COMMON)
    return data, basis


def run(data, basis):
    return calculate(IncomeTaxCase(**data), ADAPTER.validate_python(basis))


def test_property_allowance_follows_actual_deductions_without_profits_reduction():
    result = run(*inputs())
    assert Decimal(result['statutory_allowance']) == 54000
    assert Decimal(result['net_assessable_value']) == 216000
    assert Decimal(result['final_tax']) == 32400
    assert Decimal(result['balance_due']) == -2600
    assert result['sources'][0]['doc_id'] == 'hk.ird.property-notes-20261119'


def test_multiple_properties_have_independent_rows_and_exact_total():
    data, basis = inputs()
    data['incomes'].append({**data['incomes'][0], 'gross_amount': '100000'})
    basis['properties'].insert(0, dict(income_index=1, irrecoverable_rent='0', owner_rates_paid='0'))
    result = run(data, basis)
    assert [r['income_index'] for r in result['properties']] == [0, 1]
    assert Decimal(result['properties'][1]['property_tax']) == 12000
    assert Decimal(result['final_tax']) == 44400


@pytest.mark.parametrize('change', [dict(carried_losses='1'), dict(claimed_deductions='84000'),
    dict(subject='company'), dict(period_end='2026-12-31')])
def test_incompatible_saved_case_rejected(change):
    data, basis = inputs()
    data.update(change)
    with pytest.raises(ValueError):
        run(data, basis)


@pytest.mark.parametrize('change', [dict(category='employment'), dict(source_jurisdiction='cn'),
    dict(foreign_tax_paid='1')])
def test_other_income_or_foreign_credit_not_absorbed(change):
    data, basis = inputs()
    data['incomes'][0].update(change)
    with pytest.raises(ValueError):
        run(data, basis)


@pytest.mark.parametrize('field', ['sole_ownership_and_separate_assessment_verified',
    'consideration_and_deductions_verified'])
def test_scope_requires_explicit_verification(field):
    data, basis = inputs()
    basis[field] = False
    with pytest.raises(ValueError):
        run(data, basis)


def test_excess_bad_debt_needs_prior_year_review_not_cross_property_offset():
    data, basis = inputs()
    data['incomes'].append({**data['incomes'][0], 'gross_amount': '1000000'})
    basis['properties'].append(dict(income_index=1, irrecoverable_rent='0', owner_rates_paid='0'))
    basis['properties'][0]['irrecoverable_rent'] = '400000'
    data['claimed_deductions'] = '410000'
    with pytest.raises(ValueError, match='prior-year'):
        run(data, basis)


def test_property_mapping_cannot_duplicate_or_omit_saved_income():
    data, basis = inputs()
    basis['properties'].append(deepcopy(basis['properties'][0]))
    with pytest.raises(ValueError, match='exactly one'):
        run(data, basis)
    basis['properties'] = []
    with pytest.raises(ValidationError):
        run(data, basis)


def test_individual_rental_is_not_ordinary_profits_without_business_classification():
    data, _ = inputs()
    with pytest.raises(ValueError, match='property assessment'):
        run(data, dict(policy='hk_profits_2025_26', assessable_profits='270000',
            business_form='sole_proprietor', two_tier_eligible=True,
            ordinary_regime_confirmed=True, prepaid_final_tax='0', **COMMON))
