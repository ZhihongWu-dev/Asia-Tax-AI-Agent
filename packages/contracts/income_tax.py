"""Confirmed income-tax inputs, separate from dividend-planning facts."""
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StrictBool, model_validator
from packages.income_tax.arithmetic import amount

Jurisdiction = Literal["cn", "hk", "sg", "id", "vn", "my", "th", "ae", "jp", "kr", "in"]
CURRENCIES = {"cn": "CNY", "hk": "HKD", "sg": "SGD", "id": "IDR", "vn": "VND", "my": "MYR", "th": "THB", "ae": "AED", "jp": "JPY", "kr": "KRW", "in": "INR"}


Money = Annotated[Decimal, BeforeValidator(amount)]


class IncomeItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: Literal["business", "employment", "service_remuneration", "author_remuneration", "dividend", "interest", "rental", "royalty", "capital_gain", "other"]
    source_jurisdiction: Jurisdiction
    gross_amount: Money
    foreign_tax_paid: Money | None = None
    description: str = Field(min_length=1, max_length=1000)


class IncomeTaxCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario: Literal["income_tax"] = "income_tax"
    subject: Literal["company", "individual"]
    jurisdiction: Jurisdiction
    period_start: date
    period_end: date
    currency: str
    residency: Literal["resident", "nonresident", "undetermined"]
    incomes: list[IncomeItem] = Field(min_length=1, max_length=200)
    claimed_deductions: Money | None = None
    carried_losses: Money | None = None
    facts_confirmed: StrictBool = False

    @model_validator(mode="after")
    def validate_period_and_currency(self):
        if self.period_end < self.period_start:
            raise ValueError("period_end must not precede period_start")
        if self.currency != CURRENCIES[self.jurisdiction]:
            raise ValueError("Convert amounts to the jurisdiction currency using a documented applicable FX basis")
        if self.subject == "company" and any(item.category in ("employment", "service_remuneration", "author_remuneration") for item in self.incomes):
            raise ValueError("Personal employment, service remuneration and author remuneration belong to an individual; company service revenue is business income")
        return self

    def missing_for_calculation(self) -> list[str]:
        missing = []
        if not self.facts_confirmed:
            missing.append("facts_confirmed")
        if self.residency == "undetermined":
            missing.append("residency")
        if self.claimed_deductions is None:
            missing.append("claimed_deductions")
        if self.carried_losses is None:
            missing.append("carried_losses")
        for index, item in enumerate(self.incomes):
            if item.source_jurisdiction != self.jurisdiction and item.foreign_tax_paid is None:
                missing.append(f"incomes.{index}.foreign_tax_paid")
        return missing
