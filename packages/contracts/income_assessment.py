"""Explicit tax-basis assertions for supported calculation policies.

These are user attestations, not an assertion of professional review by Taxrora.
The saved income facts remain separate from the established calculation basis.
"""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from .income_tax import Money


class Basis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    basis_explanation: str = Field(min_length=20, max_length=4000)
    basis_confirmed: StrictBool


class CNCompany(Basis):
    policy: Literal['cn_company_2026']
    taxable_income: Money
    normal_rate_confirmed: StrictBool
    allowed_tax_credits: Money
    prepaid_tax: Money


class CNIndividual(Basis):
    policy: Literal['cn_comprehensive_2026']
    allowed_special_deductions: Money
    allowed_additional_deductions: Money
    allowed_other_deductions: Money
    allowed_donations: Money
    allowed_tax_reductions: Money
    prepaid_tax: Money
    domestic_normal_treatment_confirmed: StrictBool


class SGCompany(Basis):
    policy: Literal['sg_company_ya2026']
    normal_chargeable_income: Money
    exemption_scheme: Literal['partial', 'startup', 'none']
    startup_eligibility_confirmed: StrictBool
    cash_grant_eligible: StrictBool
    allowed_tax_setoff: Money
    ordinary_regime_confirmed: StrictBool


class SGIndividual(Basis):
    policy: Literal['sg_resident_ya2026']
    chargeable_income: Money


class HKProfits(Basis):
    policy: Literal['hk_profits_2025_26']
    assessable_profits: Money
    business_form: Literal['corporation', 'sole_proprietor']
    two_tier_eligible: StrictBool
    ordinary_regime_confirmed: StrictBool
    prepaid_final_tax: Money


class HKSalaries(Basis):
    policy: Literal['hk_salaries_2025_26']
    net_income: Money
    allowed_allowances: Money
    prepaid_final_tax: Money
    ordinary_separate_assessment_confirmed: StrictBool


class AEOrdinary(Basis):
    policy: Literal['ae_ordinary_2026']
    taxable_income: Money
    ordinary_regime_confirmed: StrictBool
    no_relief_elected_confirmed: StrictBool
    allowed_foreign_tax_credit: Money
    prepaid_tax: Money
    natural_person_business_turnover: Money | None = None
    natural_person_activity_classification_confirmed: StrictBool = False


Assessment = Annotated[CNCompany | CNIndividual | SGCompany | SGIndividual |
                       HKProfits | HKSalaries | AEOrdinary, Field(discriminator='policy')]
