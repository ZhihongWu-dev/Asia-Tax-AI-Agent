"""Staged Malaysian individual and company workpapers, not eligibility adjudication.

Act 53 sections 42-45. Callers must establish source adjustments, allowable
amounts, loss vintages and relief eligibility before using this workpaper.
The workpaper is persisted with the assessment; eligibility remains verified input.
"""
from decimal import Decimal, localcontext
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt
from packages.contracts.income_tax import IncomeTaxCase, Money


class SourceAdjustment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    income_index: StrictInt = Field(ge=0)
    additions: Money
    deductions: Money
    statutory_charges: Money
    statutory_allowances: Money
    explanation: str = Field(min_length=20, max_length=4000)


class IndividualWorkpaper(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sources: list[SourceAdjustment] = Field(min_length=1, max_length=200)
    eligible_prior_business_losses: Money
    schedule4_additions: Money
    allowed_total_income_deductions: list[Money] = Field(max_length=8)
    allowed_personal_reliefs: Money
    eligibility_verified: StrictBool
    separate_assessment_verified: StrictBool


class CompanyWorkpaper(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sources: list[SourceAdjustment] = Field(min_length=1, max_length=200)
    eligible_prior_business_losses: Money
    schedule4_additions: Money
    allowed_total_income_deductions: list[Money] = Field(max_length=8)
    eligibility_verified: StrictBool
    standalone_ordinary_verified: StrictBool


def reconcile(case: IncomeTaxCase, paper: IndividualWorkpaper):
    """Reconcile every saved source; never offset old business losses against wages."""
    if (case.jurisdiction != "my" or case.subject != "individual"
            or case.residency != "resident" or case.missing_for_calculation()):
        raise ValueError("Confirmed Malaysian resident individual facts required")
    if not paper.eligibility_verified or not paper.separate_assessment_verified:
        raise ValueError("Workpaper eligibility and separate assessment require verification")
    return _reconcile_sources(case, paper, paper.allowed_personal_reliefs)


def reconcile_company(case: IncomeTaxCase, paper: CompanyWorkpaper):
    if (case.jurisdiction != "my" or case.subject != "company" or case.missing_for_calculation()):
        raise ValueError("Confirmed Malaysian company facts required")
    if not paper.eligibility_verified or not paper.standalone_ordinary_verified:
        raise ValueError("Company workpaper eligibility and standalone ordinary scope require verification")
    return _reconcile_sources(case, paper, Decimal(0))


def _reconcile_sources(case, paper, personal_reliefs):
    if sorted(s.income_index for s in paper.sources) != list(range(len(case.incomes))):
        raise ValueError("Each saved income must appear exactly once in the workpaper")
    if any(i.source_jurisdiction != "my" or i.foreign_tax_paid not in (None, 0)
           or i.category in ("dividend", "capital_gain", "other") for i in case.incomes):
        raise ValueError("Foreign and separate-regime income needs its own reconciliation")
    if paper.eligible_prior_business_losses != case.carried_losses:
        raise ValueError("Prior business losses must reconcile to saved eligible losses")
    with localcontext() as ctx:
        ctx.prec = 40
        claimed = (sum((s.deductions + s.statutory_allowances for s in paper.sources), Decimal(0))
                   + sum(paper.allowed_total_income_deductions, Decimal(0))
                   + personal_reliefs)
        if claimed != case.claimed_deductions:
            raise ValueError('Saved claimed deductions differ from the workpaper deduction amounts')
        business = other = current_losses = Decimal(0)
        rows = []
        for s in sorted(paper.sources, key=lambda s: s.income_index):
            item = case.incomes[s.income_index]
            adjusted = item.gross_amount + s.additions - s.deductions
            is_business = item.category == "business"
            if not is_business and (adjusted < 0 or s.statutory_charges or s.statutory_allowances):
                raise ValueError("Nonbusiness source cannot create a business loss or capital allowance")
            loss = max(Decimal(0), -adjusted) if is_business else Decimal(0)
            available = max(Decimal(0), adjusted) + s.statutory_charges
            used_allowances = min(available, s.statutory_allowances)
            statutory = available - used_allowances
            if is_business:
                business += statutory
                current_losses += loss
            else:
                other += statutory
            rows.append(dict(income_index=s.income_index, gross=item.gross_amount,
                adjusted=adjusted, current_business_loss=loss, statutory=statutory,
                unused_allowances=s.statutory_allowances-used_allowances))
        prior_used = min(business, paper.eligible_prior_business_losses)
        aggregate = business - prior_used + other + paper.schedule4_additions
        current_used = min(aggregate, current_losses)
        total = aggregate - current_used
        deduction_steps = []
        for deduction in paper.allowed_total_income_deductions:
            if deduction > total:
                raise ValueError("Allowed total-income deduction exceeds remaining income")
            total -= deduction
            deduction_steps.append(dict(deduction=deduction, remaining=total))
        chargeable = max(Decimal(0), total-personal_reliefs)
        return dict(sources=rows, business_statutory_income=business,
            reconciled_claimed_deductions=claimed,
            other_statutory_income=other, prior_losses_used=prior_used,
            prior_losses_unused=paper.eligible_prior_business_losses-prior_used,
            aggregate_income=aggregate, current_losses_used=current_used,
            current_losses_unused=current_losses-current_used,
            deduction_steps=deduction_steps, total_income=total,
            chargeable_income=chargeable,
            scope="Verified-amount workpaper; no automatic deduction eligibility or return approval")
