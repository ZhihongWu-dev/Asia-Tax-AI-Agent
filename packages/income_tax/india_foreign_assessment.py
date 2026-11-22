"""Saved Indian company FTC using verified source tax attribution workpapers."""
from decimal import Decimal, localcontext
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt
from packages.contracts.income_tax import Money
from . import india, india_company
from .india_foreign_credit import Source, calculate as credit_calculation


class Group(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source_id: str = Field(min_length=1, max_length=120, pattern=r'\S')
    income_indexes: list[StrictInt] = Field(min_length=1, max_length=200)
    allowable_expenses: Money
    foreign_credit: Source | None = None


class SavedWorkpaper(BaseModel):
    model_config = ConfigDict(extra='forbid')
    groups: list[Group] = Field(min_length=1, max_length=200)
    scheme: Literal['normal', 'section200']
    turnover_2024_25: Money | None = None
    mat_book_profit_before_rounding: Money | None = None
    domestic_company_regime_and_base_verified: StrictBool
    source_attribution_and_expenses_verified: StrictBool
    tax_year_fx_disputes_and_treaty_limits_verified: StrictBool
    required_filings_and_accountant_verification_confirmed: StrictBool
    no_prior_credit_refunds_special_regimes_or_losses_verified: StrictBool
    period_prepayments_verified: StrictBool
    no_legacy_mat_credit_or_other_reliefs_verified: StrictBool


def assess(case, workpaper, prepaid_tax):
    p = SavedWorkpaper.model_validate(workpaper)
    if not all((p.domestic_company_regime_and_base_verified, p.source_attribution_and_expenses_verified,
            p.tax_year_fx_disputes_and_treaty_limits_verified, p.required_filings_and_accountant_verification_confirmed,
            p.no_prior_credit_refunds_special_regimes_or_losses_verified, p.period_prepayments_verified,
            p.no_legacy_mat_credit_or_other_reliefs_verified)):
        raise ValueError('Verify company regime, source attribution, expenses, foreign tax evidence, filings and exclusions')
    if (case.subject != 'company' or case.jurisdiction != 'in' or case.residency != 'resident'
            or case.missing_for_calculation() or case.carried_losses):
        raise ValueError('Confirmed Indian resident company without carried losses required')
    if (case.period_start.isoformat(), case.period_end.isoformat()) != ('2026-04-01', '2027-03-31'):
        raise ValueError('Tax year2026-27 required')
    indexes = [n for g in p.groups for n in g.income_indexes]
    ids = [g.source_id.strip() for g in p.groups]
    if sorted(indexes) != list(range(len(case.incomes))) or len(set(ids)) != len(ids):
        raise ValueError('Unique sources must cover every saved income exactly once')
    foreign, rows = [], []
    with localcontext() as context:
        context.prec = 40
        if sum((g.allowable_expenses for g in p.groups), Decimal(0)) != case.claimed_deductions:
            raise ValueError('Source expenses must reconcile to saved deductions')
        total = Decimal(0)
        for g in p.groups:
            items = [case.incomes[n] for n in g.income_indexes]
            countries = {i.source_jurisdiction for i in items}
            categories = {i.category for i in items}
            if len(countries) != 1 or len(categories) != 1 or not categories <= {'business','interest','royalty','rental'}:
                raise ValueError('Each source requires one country and ordinary company income category')
            country = next(iter(countries))
            gross = sum((i.gross_amount for i in items), Decimal(0))
            net = gross-g.allowable_expenses
            if net < 0:
                raise ValueError('Source losses require separate allocation treatment')
            total += net
            if country == 'in':
                if g.foreign_credit is not None or any(i.foreign_tax_paid not in (None,0) for i in items):
                    raise ValueError('Domestic sources cannot claim foreign credits')
            else:
                c = g.foreign_credit
                if c is None or c.source_id.strip() != g.source_id.strip() or c.country != country:
                    raise ValueError('Foreign credit must identify the saved source and country')
                if any(i.foreign_tax_paid is None for i in items):
                    raise ValueError('Foreign tax paid must be recorded, including zero')
                paid = sum((i.foreign_tax_paid for i in items), Decimal(0))
                if c.foreign_tax_paid_inr != paid:
                    raise ValueError('Foreign tax must reconcile to saved payments')
                if not net and c.normal_indian_tax_attributable:
                    raise ValueError('Zero taxable source requires separate attribution review')
                foreign.append(c.model_dump())
            rows.append(dict(source_id=g.source_id.strip(), country=country, gross_income=gross,
                allowable_expenses=g.allowable_expenses, net_taxable_income=net))
    if not foreign:
        raise ValueError('At least one foreign source required')
    # Reuse established domestic-company rate engines, with foreign source and
    # relief reconciliation performed here rather than the domestic-only route.
    rate_args = dict(taxable_income_before_rounding=total, period_start='2026-04-01',
        period_end='2027-03-31', regime_and_base_verified=True, ordinary_domestic_scope_confirmed=True)
    if p.scheme == 'normal':
        if p.turnover_2024_25 is None or p.mat_book_profit_before_rounding is None:
            raise ValueError('Normal company requires historical turnover and verified MAT book profit')
        annual = india_company.normal_company_tax(**rate_args, turnover_2024_25=p.turnover_2024_25,
            mat_book_profit_before_rounding=p.mat_book_profit_before_rounding, turnover_and_mat_adjustments_verified=True)
        normal = annual['normal_tax_including_surcharge_cess']
        minimum = annual['mat_tax_including_surcharge_cess']
    else:
        if p.turnover_2024_25 is not None or p.mat_book_profit_before_rounding is not None:
            raise ValueError('Section200 excludes normal-regime turnover/MAT inputs')
        annual = india.annual_tax(**rate_args, regime='company_section200')
        normal, minimum = annual['annual_tax_before_rounding'], None
    credit = credit_calculation(dict(sources=foreign,
        indian_residency_and_tax_eligibility_verified=True, source_tax_year_fx_and_dispute_treatment_verified=True,
        attributable_tax_excludes_interest_fees_penalties_verified=True,
        required_statements_payment_evidence_and_verification_confirmed=True),
        normal_indian_tax=normal, section206_tax=minimum)
    used = credit['section206_foreign_tax_credit'] if annual.get('mat_applies') else credit['normal_foreign_tax_credit']
    with localcontext() as context:
        context.prec = 40
        before = annual['annual_tax_before_rounding']
        after = before-used
        prepaid = india.amount(prepaid_tax)
        balance = after-prepaid
        annual.update(policy_version='in-company-foreign-ty2026-27-20261122',
            tax_scope='india_company_foreign_ty2026_27',
            annual_tax_before_foreign_credit=before, allowed_foreign_tax_credit=used,
            annual_tax_before_rounding=after, final_tax=india.round_rupees(after), prepaid_tax=prepaid,
            balance_due=(-1 if balance < 0 else 1)*india.round_rupees(abs(balance)),
            source_reconciliation=rows, foreign_credit=credit,
            stage='company_foreign_credit_and_verified_prepayments_before_interest_fees',
            source_attribution='user_verified_statutory_source_tax_workpaper')
    known = {s['doc_id'] for s in annual['sources']}
    annual['sources'].extend(s for s in credit['sources'] if s['doc_id'] not in known)
    return annual
