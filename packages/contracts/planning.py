"""Persisted Li planning input boundary; source admission remains separate."""
from datetime import date
import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator
from packages.contracts.income_tax import Jurisdiction


class Party(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    jur: Jurisdiction
    subject: Literal['company', 'individual'] = 'company'
    facts: dict[str, JsonValue] = Field(default_factory=dict)


class PlanningInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    date: str
    mode: Literal['plan', 'record']
    amount: Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]
    currency: str = Field(pattern=r'^[A-Z]{3}$')
    payer: Party
    payee: Party
    payment: dict[str, JsonValue] = Field(default_factory=dict)
    entities: dict[str, dict[str, JsonValue]] = Field(default_factory=dict, max_length=22)
    valuation: dict[str, dict[str, JsonValue]] = Field(default_factory=dict)
    answers: dict[str, JsonValue] = Field(default_factory=dict)
    assume: list[str] = Field(default_factory=list)
    limits: dict[str, int] = Field(default_factory=dict)
    constraints: dict[str, JsonValue] = Field(default_factory=dict)
    destinations: list[str | list[str]] = Field(default_factory=list, max_length=22)
    as_of: str | None = None
    fx: dict[str, JsonValue] = Field(default_factory=dict)
    past_payments: list[dict[str, JsonValue]] = Field(default_factory=list, max_length=200)
    note: str = Field(default='', max_length=10000)

    @field_validator('date', 'as_of')
    @classmethod
    def iso_day(cls, value):
        if value is not None and date.fromisoformat(value).isoformat() != value:
            raise ValueError('planning_date_requires_iso_day')
        return value

    @model_validator(mode='after')
    def boundary(self):
        if self.payer.subject != 'company':
            raise ValueError('planning_dividend_payer_must_be_company')
        # All four keys are controls understood by Li; reject misspelled limits.
        if set(self.limits) - {'max_hops', 'max_moves', 'max_labels', 'max_fork_keys'}:
            raise ValueError('planning_unknown_limit')
        if any(value < 0 for value in self.limits.values()):
            raise ValueError('planning_negative_limit')
        encoded = json.dumps(self.model_dump(mode='json'), ensure_ascii=False, allow_nan=False)
        if len(encoded.encode('utf-8')) > 500_000:
            raise ValueError('planning_input_too_large')
        return self

    def engine_input(self):
        # Preserve absence, especially as_of: Li distinguishes absent from null.
        return self.model_dump(mode='json', exclude_unset=True, exclude_none=True)
