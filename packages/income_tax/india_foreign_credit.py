"""Rule76 source-by-source FTC component using established INR tax bases.

This is not an annual assessment. The caller establishes attributable Indian
tax (including surcharge/cess), foreign tax eligibility, period, FX and filings.
"""
from decimal import Decimal, localcontext
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from packages.contracts.income_tax import Jurisdiction, Money
from .arithmetic import computed_amount


class Source(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source_id: str = Field(min_length=1, max_length=120, pattern=r'\S')
    country: Jurisdiction
    foreign_tax_paid_inr: Money
    disputed_tax_excluded_inr: Money
    treaty_applies: StrictBool
    treaty_permitted_tax_inr: Money | None = None
    section160_relief_limit_inr: Money | None = None
    normal_indian_tax_attributable: Money
    section206_tax_attributable: Money | None = None


class Workpaper(BaseModel):
    model_config = ConfigDict(extra='forbid')
    sources: list[Source] = Field(min_length=1, max_length=200)
    indian_residency_and_tax_eligibility_verified: StrictBool
    source_tax_year_fx_and_dispute_treatment_verified: StrictBool
    attributable_tax_excludes_interest_fees_penalties_verified: StrictBool
    required_statements_payment_evidence_and_verification_confirmed: StrictBool


def calculate(workpaper, *, normal_indian_tax, section206_tax=None):
    p = Workpaper.model_validate(workpaper)
    if not all((p.indian_residency_and_tax_eligibility_verified,
                p.source_tax_year_fx_and_dispute_treatment_verified,
                p.attributable_tax_excludes_interest_fees_penalties_verified,
                p.required_statements_payment_evidence_and_verification_confirmed)):
        raise ValueError('Residency, eligible tax, period, FX, disputes, attributable tax and filing evidence require verification')
    ids = [s.source_id.strip() for s in p.sources]
    if len(ids) != len(set(ids)):
        raise ValueError('Each separate income source requires a unique identifier')
    normal = computed_amount(normal_indian_tax)
    minimum = None if section206_tax is None else computed_amount(section206_tax)
    rows = []
    with localcontext() as context:
        context.prec = 40
        for s in p.sources:
            if s.country == 'in':
                raise ValueError('Foreign credits require an overseas country')
            if s.disputed_tax_excluded_inr > s.foreign_tax_paid_inr:
                raise ValueError('Excluded disputed tax exceeds foreign paid tax')
            if s.treaty_applies != (s.treaty_permitted_tax_inr is not None):
                raise ValueError('Treaty cases require an explicit permitted tax, including zero')
            if (not s.treaty_applies) != (s.section160_relief_limit_inr is not None):
                raise ValueError('Non-treaty cases require an established Section160 average-rate relief limit')
            if (minimum is None) != (s.section206_tax_attributable is None):
                raise ValueError('Section206 attribution must be supplied for every source exactly when applicable')
            eligible = s.foreign_tax_paid_inr-s.disputed_tax_excluded_inr
            if s.treaty_applies:
                eligible = min(eligible, s.treaty_permitted_tax_inr)
            else:
                eligible = min(eligible, s.section160_relief_limit_inr)
            rows.append(dict(source_id=s.source_id.strip(), country=s.country,
                foreign_tax_paid_inr=s.foreign_tax_paid_inr, disputed_tax_excluded_inr=s.disputed_tax_excluded_inr,
                treaty_applies=s.treaty_applies, treaty_permitted_tax_inr=s.treaty_permitted_tax_inr,
                section160_relief_limit_inr=s.section160_relief_limit_inr,
                eligible_foreign_tax_before_indian_limit=eligible,
                normal_indian_tax_attributable=s.normal_indian_tax_attributable,
                section206_tax_attributable=s.section206_tax_attributable,
                normal_credit=min(eligible, s.normal_indian_tax_attributable),
                section206_credit=None if minimum is None else min(eligible, s.section206_tax_attributable)))
        if sum((s.normal_indian_tax_attributable for s in p.sources), Decimal(0)) > normal:
            raise ValueError('Distinct-source normal tax attribution exceeds total Indian tax')
        if minimum is not None and sum((s.section206_tax_attributable for s in p.sources), Decimal(0)) > minimum:
            raise ValueError('Distinct-source Section206 attribution exceeds total Section206 tax')
        credit = sum((r['normal_credit'] for r in rows), Decimal(0))
        minimum_credit = None if minimum is None else sum((r['section206_credit'] for r in rows), Decimal(0))
        excess = None if minimum_credit is None else max(Decimal(0), minimum_credit-credit)
    return dict(policy_version='in-rule76-credit-component-20261122', currency='INR',
        source_credits=rows, normal_foreign_tax_credit=credit, section206_foreign_tax_credit=minimum_credit,
        section206_extra_credit_ignored_for_tax_credit_computation=excess,
        normal_tax_after_foreign_credit=normal-credit,
        section206_tax_after_foreign_credit=None if minimum is None else minimum-minimum_credit,
        stage='verified_source_credit_component_before_annual_settlement',
        sources=[dict(doc_id='in.rules2026', title='Income-tax Rules2026: foreign tax credit',
            url='https://www.incometax.gov.in/iec/foportal/sites/default/files/2026-03/En-Notified-IT-Rules-2026-20-03-2026.pdf',
            file='database/raw/in/in.rules2026.pdf', sha256='30bc85bf9d3ff23f378d5ddd2ca1d2e3d223134471fc8163aa5e2feecacb7e51',
            locator='Rule76(1)-(18)'),
            dict(doc_id='in.law.ita2025.fa2026.en', title='Income-tax Act2025 as amended by Finance Act2026',
                url='https://www.incometaxindia.gov.in/documents/d/guest/income_tax_act_2025_as_amended_by_fa_act_2026-pdf',
                file='database/raw/in/in.law.ita2025.fa2026.en.pdf',
                sha256='d54a0ed6a91673d1a4fbcef9b5e472c3efe441139fae38f85a5a0c5b2cfc998b', locator='Section160')])
