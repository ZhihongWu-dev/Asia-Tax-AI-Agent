import pytest
from pydantic import ValidationError
from packages.contracts.income_tax import IncomeTaxCase, CURRENCIES


def example(jur="cn"):
    return dict(subject="company", jurisdiction=jur, period_start="2026-01-01", period_end="2026-12-31", currency=CURRENCIES[jur], residency="resident", incomes=[dict(category="business", source_jurisdiction=jur, gross_amount="100000", description="Confirmed revenue")])


@pytest.mark.parametrize("jur", CURRENCIES)
@pytest.mark.parametrize("subject", ["company", "individual"])
def test_both_subjects_all_jurisdictions(jur, subject):
    data=example(jur); data["subject"]=subject
    case=IncomeTaxCase(**data)
    assert case.missing_for_calculation() == ["facts_confirmed", "claimed_deductions", "carried_losses"]


@pytest.mark.parametrize("amount", ["NaN", "Infinity", "-1"])
def test_invalid_amount_is_not_calculable(amount):
    data=example(); data["incomes"][0]["gross_amount"]=amount
    with pytest.raises(ValidationError): IncomeTaxCase(**data)


def test_foreign_tax_is_not_silently_zero():
    data=example(); data["incomes"][0]["source_jurisdiction"]="sg"
    assert "incomes.0.foreign_tax_paid" in IncomeTaxCase(**data).missing_for_calculation()


def test_reversed_period_and_wrong_currency_are_rejected():
    for field, value in [("period_end", "2025-12-31"), ("currency", "USD")]:
        data=example();data[field]=value
        with pytest.raises(ValidationError): IncomeTaxCase(**data)


@pytest.mark.parametrize('category', ['employment', 'service_remuneration', 'author_remuneration'])
def test_personal_income_categories_are_preserved_and_rejected_for_companies(category):
    data=example();data['subject']='individual';data['incomes'][0]['category']=category
    assert IncomeTaxCase(**data).incomes[0].category==category
    data['subject']='company'
    with pytest.raises(ValidationError): IncomeTaxCase(**data)


@pytest.mark.parametrize('value', [True, 1.2, '0.0000001', '1000000000000000001', 'Infinity', '-0.01'])
@pytest.mark.parametrize('field', ['gross_amount', 'foreign_tax_paid', 'claimed_deductions', 'carried_losses'])
def test_every_amount_uses_the_same_exact_calculation_contract(field,value):
    data=example()
    target=data['incomes'][0] if field in ('gross_amount','foreign_tax_paid') else data
    target[field]=value
    with pytest.raises(ValidationError): IncomeTaxCase(**data)


@pytest.mark.parametrize('value', ['true', 'false', 1, 0])
def test_confirmation_cannot_be_coerced(value):
    data=example();data['facts_confirmed']=value
    with pytest.raises(ValidationError): IncomeTaxCase(**data)


def test_decimal_strings_round_trip_without_float_conversion():
    data=example();data['incomes'][0]['gross_amount']='123456789012345678.123456'
    result=IncomeTaxCase(**data).model_dump(mode='json')
    assert result['incomes'][0]['gross_amount']=='123456789012345678.123456'
