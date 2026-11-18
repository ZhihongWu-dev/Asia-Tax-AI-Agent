"""Explicit tax-basis assertions for supported calculation policies.

These are user attestations, not an assertion of professional review by Taxrora.
The saved income facts remain separate from the established calculation basis.
"""
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt
from .income_tax import Money
from packages.income_tax.hong_kong_salary_reconciliation import SalaryWorkpaper
from packages.income_tax.malaysia_reconciliation import IndividualWorkpaper, CompanyWorkpaper


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
    non_taxable_income: Money = Decimal('0')
    exempt_income: Money = Decimal('0')


class CNSmallCompany(Basis):
    policy: Literal['cn_small_company_2026']
    taxable_income: Money
    annual_average_employees: Money
    annual_average_assets: Money
    unrestricted_industry_confirmed: StrictBool
    statutory_averages_and_eligibility_verified: StrictBool
    allowed_tax_credits: Money
    prepaid_tax: Money
    non_taxable_income: Money = Decimal('0')
    exempt_income: Money = Decimal('0')


class CNIndividual(Basis):
    policy: Literal['cn_comprehensive_2026']
    allowed_special_deductions: Money
    allowed_additional_deductions: Money
    allowed_other_deductions: Money
    allowed_donations: Money
    allowed_tax_reductions: Money
    prepaid_tax: Money
    domestic_normal_treatment_confirmed: StrictBool


class CNBusiness(Basis):
    policy: Literal['cn_business_2026']
    taxable_income: Money
    business_form: Literal['individual_operator', 'other_business']
    allowed_other_tax_reductions: Money
    prepaid_tax: Money
    annual_aggregation_and_classification_verified: StrictBool
    deductions_losses_and_no_double_claim_verified: StrictBool


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


class SGEmployment(Basis):
    policy: Literal['sg_employment_ya2026']
    birth_date: date
    disability_relief_eligible: StrictBool
    allowed_employment_expenses: Money
    allowed_donation_deduction: Money
    allowed_cpf_relief: Money
    allowed_other_personal_reliefs: Money
    available_parenthood_rebate: Money
    prepaid_tax: Money
    eligibility_and_allocations_verified: StrictBool


class HKProfits(Basis):
    policy: Literal['hk_profits_2025_26']
    # Legacy field name: the tax-rate base after loss relief.
    assessable_profits: Money
    taxable_additions: Money = Decimal('0')
    excluded_income: Money = Decimal('0')
    business_form: Literal['corporation', 'sole_proprietor']
    two_tier_eligible: StrictBool
    ordinary_regime_confirmed: StrictBool
    prepaid_final_tax: Money


class HKSalaries(Basis):
    workpaper: SalaryWorkpaper | None = None
    policy: Literal['hk_salaries_2025_26']
    net_income: Money
    allowed_allowances: Money
    prepaid_final_tax: Money
    ordinary_separate_assessment_confirmed: StrictBool


class HKPropertyLine(BaseModel):
    model_config = ConfigDict(extra='forbid')
    income_index: Annotated[StrictInt, Field(ge=0)]
    irrecoverable_rent: Money
    owner_rates_paid: Money


class HKProperty(Basis):
    policy: Literal['hk_property_2025_26']
    properties: list[HKPropertyLine] = Field(min_length=1, max_length=200)
    sole_ownership_and_separate_assessment_verified: StrictBool
    consideration_and_deductions_verified: StrictBool
    prepaid_final_tax: Money


class AEOrdinary(Basis):
    policy: Literal['ae_ordinary_2026']
    taxable_income: Money
    taxable_additions: Money = Decimal('0')
    exempt_income: Money = Decimal('0')
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
    workpaper: CompanyWorkpaper | None = None
    policy: Literal['my_company_2026']
    scheme: Literal['ordinary', 'sme']
    sme_eligibility_confirmed: StrictBool


class MYIndividual(MYBasis):
    workpaper: IndividualWorkpaper | None = None
    policy: Literal['my_individual_2026']


class MYDividends(Basis):
    policy: Literal['my_dividend_2026']
    dividend_statutory_before_threshold: Money
    ordinary_statutory_income: Money
    chargeable_income: Money
    allowed_rebates: Money
    allowed_tax_credits: Money
    prepaid_tax: Money
    separate_domestic_assessment_verified: StrictBool
    dividend_scope_verified: StrictBool
    bases_verified: StrictBool
    settlement_inputs_verified: StrictBool


class THBasis(Basis):
    ordinary_treatment_confirmed: StrictBool
    allowed_tax_credits: Money
    prepaid_tax: Money


class THCompany(THBasis):
    policy: Literal['th_company_2026']
    net_taxable_profit: Money
    exempt_income: Money = Decimal('0')
    scheme: Literal['ordinary','sme']
    sme_eligibility_confirmed: StrictBool


class THIndividual(THBasis):
    policy: Literal['th_resident_2026']
    net_taxable_income: Money
    assessable_income_classification_confirmed: StrictBool


class THRemittanceLine(BaseModel):
    model_config = ConfigDict(extra='forbid')
    income_index: Annotated[int, Field(strict=True, ge=0, le=199)]
    remitted_income: Money
    income_date: date
    remittance_date: date
    days_in_thailand_in_income_year: Annotated[int, Field(strict=True, ge=0, le=366)]


class THForeignPool(BaseModel):
    model_config = ConfigDict(extra='forbid')
    pool_id: str = Field(min_length=1, max_length=200)
    income_index: Annotated[int, Field(strict=True, ge=0, le=199)]
    total_foreign_income: Money
    foreign_income_tax_paid: Money
    eligible_foreign_income_tax_paid: Money
    previously_remitted_income: Money
    remittances: list[THRemittanceLine] = Field(min_length=1, max_length=1000)
    entitlement_and_fx_explanation: str = Field(min_length=20, max_length=4000)


class THForeignIncome(Basis):
    policy: Literal['th_foreign_income_2026']
    pools: list[THForeignPool] = Field(min_length=1, max_length=1000)
    net_taxable_income: Money
    prepaid_tax: Money
    ordinary_treatment_confirmed: StrictBool
    assessable_income_classification_confirmed: StrictBool
    tracing_fx_and_entitlement_verified: StrictBool
    saved_tax_represents_original_pool_tax: StrictBool


class THDividendLine(BaseModel):
    model_config = ConfigDict(extra='forbid')
    income_index: Annotated[int, Field(strict=True, ge=0, le=199)]
    gross_dividend: Money
    corporate_rate_percent: Money | None
    withholding_tax: Money
    credit_eligible: StrictBool


class THDividends(Basis):
    policy: Literal['th_dividend_2026']
    election: Literal['aggregate', 'final_withholding']
    tranches: list[THDividendLine] = Field(min_length=1, max_length=1000)
    allowed_expenses_and_allowances: Money
    other_prepaid_tax: Money
    certificates_verified: StrictBool
    recipient_eligibility_verified: StrictBool
    election_scope_verified: StrictBool
    ordinary_income_classification_verified: StrictBool


class VNCompany(Basis):
    policy: Literal['vn_company_2026']
    taxable_income: Money
    exempt_income: Money = Decimal('0')
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


class VNBusinessActivity(BaseModel):
    model_config = ConfigDict(extra='forbid')
    income_index: Annotated[int, Field(strict=True, ge=0, le=199)]
    category: Literal['goods', 'services_without_materials',
        'asset_rental_or_specified_agency', 'production_transport_with_materials',
        'digital_content', 'other_business']
    allocated_revenue_deduction: Money


class VNBusiness(Basis):
    policy: Literal['vn_business_2026']
    method: Literal['revenue', 'profit']
    activities: list[VNBusinessActivity] = Field(min_length=1, max_length=100)
    deductible_expenses: Money | None
    prepaid_tax: Money
    ordinary_domestic_business_verified: StrictBool
    revenue_and_expense_evidence_verified: StrictBool
    method_election_and_continuity_verified: StrictBool
    revenue_method_started_within_limit: StrictBool


class VNRentalContract(BaseModel):
    model_config = ConfigDict(extra='forbid')
    income_index: Annotated[int, Field(strict=True, ge=0, le=199)]
    contract_id: str = Field(min_length=1, max_length=120)
    allocated_revenue_deduction: Money
    prepaid_tax: Money
    tenant_files: StrictBool
    filing_and_allocation_verified: StrictBool


class VNRental(Basis):
    policy: Literal['vn_property_rental_2026']
    contracts: list[VNRentalContract] = Field(min_length=1, max_length=100)
    rental_only_scope_verified: StrictBool
    annual_recognition_and_all_contracts_verified: StrictBool


class VNEmployment(Basis):
    policy: Literal['vn_employment_2026']
    exempt_employment_income: Money = Decimal('0')
    chargeable_employment_income: Money
    full_calendar_year_confirmed: StrictBool
    dependent_months: list[Annotated[int, Field(strict=True, ge=0, le=12)]] = Field(max_length=200)
    deductible_insurance: Money
    article11_deductions: Money
    prepaid_tax: Money
    income_and_deductions_verified: StrictBool


class VNTransferLine(BaseModel):
    model_config = ConfigDict(extra='forbid')
    income_index: Annotated[int, Field(strict=True, ge=0, le=199)]
    recognition_date: date
    asset_kind: Literal['capital_interest', 'security']
    purchase_cost: Money | None
    transfer_costs: Money | None
    cost_basis_established: StrictBool
    ordinary_sale_confirmed: StrictBool
    classification_valuation_and_scope_verified: StrictBool
    prepaid_tax: Money


class VNPersonalTransfer(Basis):
    policy: Literal['vn_personal_transfer_2026']
    transfers: list[VNTransferLine] = Field(min_length=1, max_length=200)


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


class JPIndividual(Basis):
    policy: Literal['jp_resident_ordinary_2026']
    business_expenses: Money
    other_income_deductions: Money
    income_tax_credits: Money
    salary_adjustment_eligible: StrictBool
    withheld_tax: Money
    estimated_tax: Money
    annual_domestic_ordinary_scope_confirmed: StrictBool
    deductions_and_credits_verified: StrictBool


class JPCompany(Basis):
    policy: Literal['jp_company_starting_2026']
    taxable_income_before_rounding: Money
    rate_regime: Literal['ordinary','sme_reduced','sme_excluded']
    rate_classification_verified: StrictBool
    ordinary_no_adjustments_confirmed: StrictBool
    corporation_interim_liability: Money
    local_corporation_interim_liability: Money


class INBasis(Basis):
    taxable_income_before_rounding: Money
    regime_and_base_verified: StrictBool
    ordinary_domestic_scope_confirmed: StrictBool
    settlement_requested: StrictBool = False
    tds_tcs_credit: Money | None = None
    advance_tax_paid: Money | None = None
    self_assessment_paid: Money | None = None
    total_interest_due: Money | None = None
    total_fee_due: Money | None = None
    settlement_verified: StrictBool = False


class INIndividual(INBasis):
    policy: Literal['in_personal_new_ty2026_27']


class INOldIndividual(INBasis):
    policy: Literal['in_personal_old_ty2026_27']
    resident_age_band: Literal['under60','60_to79','80_plus']
    amt_not_applicable_verified: StrictBool


class INCompany(INBasis):
    policy: Literal['in_company_section200_ty2026_27']


class INNormalCompany(INBasis):
    policy: Literal['in_company_normal_ty2026_27']
    turnover_2024_25: Money
    mat_book_profit_before_rounding: Money
    turnover_and_mat_adjustments_verified: StrictBool


class KRRelief(BaseModel):
    model_config = ConfigDict(extra='forbid')
    identifier: str = Field(min_length=1, max_length=120)
    value: Money
    category: Literal['reduction', 'noncarry_credit', 'carry_credit', 'article58_3_credit']
    origin_year: StrictInt = Field(ge=1900, le=2026)
    minimum_tax_subject: StrictBool


class KRNationalInputs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    minimum_regime: Literal['general', 'sme', 'graduated_first_three_years', 'graduated_next_two_years']
    article60_2_1_1_company: StrictBool
    reliefs: list[KRRelief] = Field(max_length=1000)
    annual_standard_schedule_confirmed: StrictBool
    minimum_regime_verified: StrictBool
    eligibility_caps_and_expiry_verified: StrictBool
    no_base_changing_incentives: StrictBool
    additions_and_payments_verified: StrictBool
    penalty_tax: Money
    relief_recapture: Money
    interim_tax: Money
    occasional_assessment_tax: Money
    withheld_tax: Money
    installment: StrictBool


class KRLocalAdjustment(BaseModel):
    model_config = ConfigDict(extra='forbid')
    relief: Money
    penalty: Money
    additional_tax: Money
    other_payments: Money
    rate_adjustment_increase: Money
    rate_adjustment_decrease: Money


class KRLocalInputs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    total_withheld: Money
    filing_ratios: dict[str, Annotated[str, Field(pattern=r'^(?:0(?:\.\d{1,8})?|1(?:\.0{1,8})?)$')]] = Field(min_length=1, max_length=1000)
    adjustments: dict[str, KRLocalAdjustment] = Field(min_length=1, max_length=1000)
    head_office: str = Field(min_length=1, max_length=120)
    initial_return_and_filing_groups_verified: StrictBool
    relief_caps_rate_adjustments_and_payments_verified: StrictBool
    installment: StrictBool


class KRCompany(Basis):
    policy: Literal['kr_company_ordinary_2026']
    national_taxable_base: Money
    local_taxable_base: Money
    national_inputs: KRNationalInputs
    local_inputs: KRLocalInputs
    ordinary_domestic_scope_confirmed: StrictBool


class KRPersonalDeductionPerson(BaseModel):
    model_config = ConfigDict(extra='forbid')
    identifier: str = Field(min_length=1,max_length=120)
    relationship: Literal['self','spouse','ascendant','descendant','adopted_child','sibling',
        'welfare_recipient','foster_child','disabled_descendant_spouse']
    basic_eligible: StrictBool
    senior_70_at_statutory_date: StrictBool
    statutory_disability: StrictBool


class KRChildCreditFacts(BaseModel):
    model_config = ConfigDict(extra='forbid')
    identifier: str = Field(min_length=1,max_length=120)
    birth_date: date = Field(le=date(2026,12,31))
    relationship: Literal['child','adopted_child','foster_child','grandchild']
    basic_deduction_eligible: StrictBool
    current_year_birth_adoption_order: StrictInt | None = Field(default=None,ge=1,le=1000)


class KRSalary(Basis):
    policy: Literal['kr_salary_standard_payroll_2026']
    people: list[KRPersonalDeductionPerson] = Field(min_length=1,max_length=1000)
    children: list[KRChildCreditFacts] = Field(max_length=1000)
    female_taxpayer: StrictBool
    has_spouse: StrictBool
    household_head: StrictBool
    public_pension_paid: Money
    ordinary_salary_and_standard_credit_verified: StrictBool
    family_eligibility_and_allocation_verified: StrictBool
    pension_eligibility_verified: StrictBool
    current_employer_withheld: Money
    former_employer_settled_tax: Money
    decision_and_employer_records_verified: StrictBool
    local_current_employer_withheld: Money
    local_former_employer_settled_tax: Money
    employer_special_collection_verified: StrictBool
    installment: StrictBool


Assessment = Annotated[CNCompany | CNSmallCompany | CNIndividual | CNBusiness | SGCompany | SGIndividual | SGEmployment | JPIndividual | JPCompany | INIndividual | INOldIndividual | INCompany | INNormalCompany | KRCompany | KRSalary |
                       HKProfits | HKSalaries | HKProperty | AEOrdinary | MYCompany | MYIndividual | MYDividends | THCompany | THIndividual | THForeignIncome | THDividends | IDCompany | IDIndividual | VNEmployment | VNCompany | VNPersonalTransfer | VNBusiness | VNRental,
                       Field(discriminator='policy')]
