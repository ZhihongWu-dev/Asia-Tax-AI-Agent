"""Dictionary validation and bilingual questions; no model controls workflow state."""
from __future__ import annotations

import math
from datetime import date
from typing import Any

from packages.intake.prompting import field_catalog

EN_LABELS = {
    "entity_hk_business_status": "Does the recipient carry on business in Hong Kong?",
    "mne_group_status": "Is the recipient part of a multinational enterprise group?",
    "regulated_financial_entity_status": "Regulated financial entity status",
    "pure_equity_holding_entity_status": "Pure equity holding entity status",
    "entity_tax_residency": "Entity tax residency",
    "income_type": "What type of income is involved?",
    "income_legal_character": "Legal character of the income",
    "payer_entity": "Payer entity", "dividend_amount": "Dividend amount",
    "dividend_currency": "Dividend currency", "accrual_date": "Accrual date",
    "underlying_profit_period": "Underlying profit period", "source_analysis": "Source of the income",
    "receipt_location": "Where was the income received?",
    "receipt_date": "Receipt date", "bank_or_account_path": "Bank account and payment path",
    "set_off_or_clearing_arrangement": "Set-off or clearing arrangements",
    "cash_pool_arrangement": "Cash pooling arrangements", "payment_on_behalf_arrangement": "Payment on behalf arrangements",
    "direct_or_indirect_holding": "Direct or indirect holding", "investee_entity": "Investee entity",
    "holding_percentage_pct": "What percentage of the investee is held (0–100)?",
    "continuous_holding_period_months": "How many continuous months was the investment held?",
    "acquisition_date": "Acquisition date", "beneficial_owner_status": "Beneficial owner status",
    "foreign_tax_on_dividend_or_underlying_profit": "Foreign tax on the dividend or underlying profits",
    "foreign_nominal_tax_rate_pct": "Foreign nominal tax rate (%)", "foreign_tax_jurisdiction": "Foreign tax jurisdiction",
    "underlying_tax_deductible_status": "Underlying tax deductibility", "foreign_tax_credit_available": "Foreign tax credit availability",
    "entity_activity_profile": "Entity business activities", "hk_adequate_employees": "Hong Kong employee adequacy",
    "hk_adequate_premises": "Hong Kong premises adequacy", "hk_operating_expenditure_amount": "Hong Kong operating expenditure",
    "hk_operating_expenditure_currency": "Operating expenditure currency",
    "strategic_decision_making_location": "Strategic decision-making location",
    "outsourcing_and_supervision": "Outsourcing and supervision", "hybrid_mismatch_arrangement": "Hybrid mismatch arrangements",
    "main_purpose_tax_benefit_flag": "Tax benefit as a main purpose",
    "restructuring_near_income_date": "Restructuring near the income date", "commercial_rationale": "Commercial rationale",
    "evidence_inventory": "Evidence inventory",
}


def catalog() -> list[dict]:
    return [{**f, "label_en": EN_LABELS[f["field_name"]]} for f in field_catalog() if f["field_name"] != "expert_decision_status"]


def validate_patch(patch: dict[str, Any]) -> dict:
    fields = {f["field_name"]: f for f in catalog()}
    accepted = {}
    for name, value in patch.items():
        if name not in fields:
            raise ValueError("Unknown or protected fact field")
        spec = fields[name]
        if value is None or value == "":
            accepted[name] = None
            continue
        if isinstance(value, str) and value in ("unknown", "conflict"):
            accepted[name] = value
            continue
        dtype = spec["data_type"]
        if dtype == "enum":
            if not isinstance(value, str) or value not in spec["enum_values"]:
                raise ValueError("Invalid fact option")
        elif dtype in ("integer", "decimal"):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError("Expected a finite non-negative number")
            if dtype == "integer" and int(value) != value:
                raise ValueError("Expected whole months")
            if name.endswith("_pct") and value > 100:
                raise ValueError("Percentage exceeds 100")
        elif dtype == "list":
            if not isinstance(value, list) or len(value) > 50 or any(not isinstance(v, str) or len(v) > 200 for v in value):
                raise ValueError("Expected a short list of strings")
        else:
            if not isinstance(value, str) or len(value) > 1000:
                raise ValueError("Expected short text")
            if dtype == "date":
                date.fromisoformat(value)
            if dtype == "currency_code" and (len(value) != 3 or not value.isascii() or not value.isalpha()):
                raise ValueError("Expected a three-letter currency")
        accepted[name] = value
    return accepted


def raw_facts(doc: dict) -> dict:
    return {k: v["value"] for k, v in doc["facts"].items()}


def questions(doc: dict) -> list[str]:
    facts = raw_facts(doc)
    conflicts = [k for k, v in facts.items() if v == "conflict"]
    if conflicts:
        return conflicts[:1]
    core = ["income_type", "entity_hk_business_status", "mne_group_status", "source_analysis", "accrual_date", "receipt_location"]
    if facts.get("income_type") not in (None, "dividend", "unknown") or facts.get("entity_hk_business_status") == "no" or facts.get("mne_group_status") == "no":
        return []
    if facts.get("receipt_location") in ("received_in_hk", "deemed_received_in_hk"):
        core += ["holding_percentage_pct", "continuous_holding_period_months", "hk_adequate_employees"]
    return [k for k in core if k not in facts][:1]


def state_for(doc: dict) -> str:
    if any(v["value"] == "conflict" for v in doc["facts"].values()):
        return "needs_resolution"
    return "collecting" if questions(doc) else "awaiting_confirmation"
