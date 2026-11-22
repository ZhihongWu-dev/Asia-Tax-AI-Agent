"""FSIE credit limits on verified taxable income and same-income Hong Kong tax.

Not an annual assessment or an automatic source, exemption, treaty, ownership,
gross-up, expense, exchange-rate or tax-reduction determination.
"""
from decimal import Decimal, localcontext
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from packages.contracts.income_tax import Jurisdiction, Money
from .arithmetic import computed_amount


class SourceFacts(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source_id: str = Field(min_length=1, max_length=120, pattern=r'\S')
    country: Jurisdiction
    income_type: Literal['interest', 'dividend', 'disposal_gain', 'ip_income']
    direct_foreign_tax_paid: Money
    cdta_applies: StrictBool
    bilateral_credit_eligible_tax: Money | None = None
    underlying_tax_paid: Money
    underlying_tax_in_bilateral_claim: Money
    underlying_unilateral_eligible_tax: Money = Decimal(0)
    underlying_attribution_and_no_treaty_provision_verified: StrictBool = False
    equity_fraction_at_distribution: Money | None = None
    voting_fraction_at_distribution: Money | None = None
    equity_chain_at_distribution: list[Money] | None = Field(default=None,min_length=1,max_length=200)
    voting_chain_at_distribution: list[Money] | None = Field(default=None,min_length=1,max_length=200)
    taxable_fsie_receipt_and_similar_tax_verified: StrictBool
    treaty_ownership_and_no_duplicate_tax_verified: StrictBool


class Source(SourceFacts):
    hong_kong_tax_on_same_income: Money


class EligibilityWorkpaper(BaseModel):
    model_config = ConfigDict(extra='forbid')
    sources: list[SourceFacts] = Field(min_length=1, max_length=200)
    hong_kong_resident_mne_verified: StrictBool
    source_tax_attribution_and_gross_up_verified: StrictBool
    payment_fx_and_claim_evidence_verified: StrictBool


class Workpaper(EligibilityWorkpaper):
    sources: list[Source] = Field(min_length=1, max_length=200)


def _interest(declared, chain):
    """One verified path: direct holding or at most four interposed persons.

    Multiple paths and voting rights attributed by agreement still require a
    separately verified aggregate; overlapping paths must not be added here.
    """
    if chain is None:
        return declared or Decimal(0)
    if any(part > 1 for part in chain):
        raise ValueError('Every ownership-chain fraction must be between zero and one')
    effective=Decimal(1)
    if len(chain)>5:
        effective=Decimal(0)  # Section50AAAC(4): five or more interposed persons excluded.
    else:
        for part in chain:
            effective*=part
    if declared is not None and declared!=effective:
        raise ValueError('Declared interest differs from the verified statutory ownership chain')
    return effective


def calculate_eligibility(workpaper):
    """Establish eligible tax without requiring a not-yet-derived HK limit."""
    p = EligibilityWorkpaper.model_validate(workpaper)
    if not all((p.hong_kong_resident_mne_verified,
                p.source_tax_attribution_and_gross_up_verified,
                p.payment_fx_and_claim_evidence_verified)):
        raise ValueError('Resident MNE, attributed tax, gross-up, FX and claim evidence must be verified')
    ids = [s.source_id.strip() for s in p.sources]
    if len(ids) != len(set(ids)):
        raise ValueError('Separate sources require unique identifiers')
    rows = []
    with localcontext() as context:
        context.prec = 40
        for s in p.sources:
            if s.country == 'hk':
                raise ValueError('FSIE foreign credit requires an overseas source')
            if not (s.taxable_fsie_receipt_and_similar_tax_verified and
                    s.treaty_ownership_and_no_duplicate_tax_verified):
                raise ValueError('Taxable receipt, similar tax, treaty, ownership and distinct tax evidence must be verified')
            if s.cdta_applies != (s.bilateral_credit_eligible_tax is not None):
                raise ValueError('CDTA claims require an explicit bilateral eligible amount, including zero')
            if s.income_type != 'dividend' and (s.underlying_tax_paid or
                    s.underlying_tax_in_bilateral_claim or s.underlying_unilateral_eligible_tax or
                    s.equity_fraction_at_distribution is not None or s.voting_fraction_at_distribution is not None or
                    s.equity_chain_at_distribution is not None or s.voting_chain_at_distribution is not None):
                raise ValueError('Underlying profit tax and equity inputs apply only to dividends')
            if s.equity_fraction_at_distribution is not None and s.equity_fraction_at_distribution > 1:
                raise ValueError('Equity ownership must be a fraction between zero and one')
            if s.voting_fraction_at_distribution is not None and s.voting_fraction_at_distribution > 1:
                raise ValueError('Voting rights must be a fraction between zero and one')
            equity=_interest(s.equity_fraction_at_distribution,s.equity_chain_at_distribution)
            voting=_interest(s.voting_fraction_at_distribution,s.voting_chain_at_distribution)
            if s.underlying_tax_in_bilateral_claim > s.underlying_tax_paid:
                raise ValueError('Underlying bilateral tax exceeds underlying paid tax')
            if not s.cdta_applies and s.underlying_tax_in_bilateral_claim:
                raise ValueError('A non-CDTA source cannot include a bilateral claim')
            bilateral = s.bilateral_credit_eligible_tax or Decimal(0)
            if s.cdta_applies and not (s.underlying_tax_in_bilateral_claim <= bilateral <=
                    s.direct_foreign_tax_paid + s.underlying_tax_in_bilateral_claim):
                raise ValueError('Bilateral eligible tax must reconcile direct and underlying paid tax')
            underlying_remainder = s.underlying_tax_paid - s.underlying_tax_in_bilateral_claim
            # Underlying tax not covered by a CDTA can qualify unilaterally;
            # it must never be counted in both parts of the claim.
            underlying_unilateral = s.underlying_unilateral_eligible_tax
            if underlying_unilateral > underlying_remainder:
                raise ValueError('Unilateral underlying claim duplicates bilateral tax or exceeds paid tax')
            if underlying_unilateral and (not s.underlying_attribution_and_no_treaty_provision_verified or
                    max(equity,voting) < Decimal('.10')):
                raise ValueError('Underlying unilateral credit requires adequate interest and verified attributed tax with no applicable treaty credit provision')
            direct_unilateral = Decimal(0) if s.cdta_applies else s.direct_foreign_tax_paid
            eligible = bilateral + direct_unilateral + underlying_unilateral
            rows.append(dict(source_id=s.source_id.strip(), country=s.country,
                effective_equity_fraction=equity,effective_voting_fraction=voting,
                income_type=s.income_type, bilateral_eligible_tax=bilateral,
                unilateral_direct_tax=direct_unilateral,
                unilateral_underlying_tax=underlying_unilateral,
                underlying_tax_not_eligible=underlying_remainder-underlying_unilateral,
                total_eligible_tax=eligible))
    return dict(policy_version='hk-fsie-eligibility-component-20261122', currency='HKD',
        source_eligibility=rows,
        stage='verified_fsie_eligibility_before_source_limits_and_annual_settlement',
        sources=[dict(doc_id='hk.fsie.credit.20261122',
            title='IRD Foreign-sourced Income Exemption: Double Taxation Relief',
            url='https://www.ird.gov.hk/eng/tax/bus_fsie.htm',
            file='database/raw/hk/hk.fsie.credit.20261122.html',
            sha256='17759e053e59472f50bb2bcf94b97d03be6a50032acce725df6eda73547e7edb',
            locator='Double Taxation Relief: CDTA and unilateral credits'),
            dict(doc_id='hk.cap112', title='Inland Revenue Ordinance',
                url='https://www.elegislation.gov.hk/hk/cap112',
                file='database/raw/hk/hk.cap112.rtf',
                sha256='e28849ff385862416718714208c9fa05d27b022ca475b687c6f1c4591a100134',
                locator='Sections50AAAB(2)-(9),50AAAC: underlying tax and adequate interest')])


def calculate(workpaper, *, total_hong_kong_tax):
    p = Workpaper.model_validate(workpaper)
    facts = p.model_dump()
    for source in facts['sources']:
        del source['hong_kong_tax_on_same_income']
    eligibility = calculate_eligibility(facts)
    total = computed_amount(total_hong_kong_tax)
    rows = []
    with localcontext() as context:
        context.prec = 40
        if sum((s.hong_kong_tax_on_same_income for s in p.sources), Decimal(0)) > total:
            raise ValueError('Distinct-source Hong Kong tax attribution exceeds total tax')
        for source, row in zip(p.sources, eligibility['source_eligibility']):
            eligible = row['total_eligible_tax']
            credit = min(eligible, source.hong_kong_tax_on_same_income)
            rows.append(dict(row, same_income_hong_kong_limit=source.hong_kong_tax_on_same_income,
                foreign_tax_credit=credit, eligible_tax_above_limit=eligible-credit))
        credit = sum((row['foreign_tax_credit'] for row in rows), Decimal(0))
        after_credit = total-credit
    return dict(policy_version='hk-fsie-credit-component-20261122', currency='HKD',
        source_credits=rows, foreign_tax_credit=credit,
        tax_after_credit_before_other_adjustments=after_credit,
        stage='verified_fsie_source_limits_before_annual_settlement',
        sources=eligibility['sources'])
