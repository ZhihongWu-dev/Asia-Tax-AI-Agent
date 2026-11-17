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


class MYBasis(Basis):
    chargeable_income: Money
    ordinary_treatment_confirmed: StrictBool
    allowed_rebates: Money
    allowed_tax_credits: Money
    prepaid_tax: Money


class MYCompany(MYBasis):
    policy: Literal['my_company_2026']
    scheme: Literal['ordinary', 'sme']
    sme_eligibility_confirmed: StrictBool


class MYIndividual(MYBasis):
    policy: Literal['my_individual_2026']


class THBasis(Basis):
    ordinary_treatment_confirmed: StrictBool
    allowed_tax_credits: Money
    prepaid_tax: Money


class THCompany(THBasis):
    policy: Literal['th_company_2026']
    net_taxable_profit: Money
    scheme: Literal['ordinary','sme']
    sme_eligibility_confirmed: StrictBool


class THIndividual(THBasis):
    policy: Literal['th_resident_2026']
    net_taxable_income: Money
    assessable_income_classification_confirmed: StrictBool


class VNCompany(Basis):
    policy: Literal['vn_company_2026']
    taxable_income: Money
    vietnam_established: StrictBool
    new_in_current_period: StrictBool
    previous_period_revenue: Money | None
    previous_active_months: Annotated[int, Field(strict=True, ge=1, le=12)] | None
    exemption_related_enterprise_disqualified: StrictBool
    reduced_rate_related_enterprise_disqualified: StrictBool
    formed_by_split_after_resolution: StrictBool
    all_split_entities_revenue: Money | None
    other_incentive_reduction: Money
    prepaid_tax: Money
    ordinary_domestic_income_confirmed: StrictBool
    statutory_revenue_scope_confirmed: StrictBool
    other_incentives_verified: StrictBool


class VNEmployment(Basis):
    policy: Literal['vn_employment_2026']
    chargeable_employment_income: Money
    full_calendar_year_confirmed: StrictBool
    dependent_months: list[Annotated[int, Field(strict=True, ge=0, le=12)]] = Field(max_length=200)
    deductible_insurance: Money
    article11_deductions: Money
    prepaid_tax: Money
    income_and_deductions_verified: StrictBool


class IDBasis(Basis):
    ordinary_annual_treatment_confirmed: StrictBool
    prepaid_tax: Money


class IDCompany(IDBasis):
    policy: Literal['id_company_2026']
    taxable_income_before_rounding: Money
    gross_receipts_scope_confirmed: StrictBool


class IDIndividual(IDBasis):
    policy: Literal['id_resident_2026']
    net_income_before_ptkp: Money
    ptkp_status: Literal['TK/0','TK/1','TK/2','TK/3','K/0','K/1','K/2','K/3']
    ptkp_entitlement_confirmed: StrictBool


Assessment = Annotated[CNCompany | CNIndividual | SGCompany | SGIndividual |
                       HKProfits | HKSalaries | AEOrdinary | MYCompany | MYIndividual | THCompany | THIndividual | IDCompany | IDIndividual | VNEmployment | VNCompany,
                       Field(discriminator='policy')]
