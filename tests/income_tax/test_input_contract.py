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
