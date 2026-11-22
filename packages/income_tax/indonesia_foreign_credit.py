"""PMK192/2018 Articles6-9 credit component, before return rounding.

Inputs are taxable net income after exclusions; foreign losses never enter
these nonnegative country/type buckets. The annual assessment derives PKP/tax.
"""
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from packages.contracts.income_tax import Money, Jurisdiction
from .arithmetic import computed_amount


class ForeignIncome(BaseModel):
    model_config = ConfigDict(extra='forbid')
    country: Jurisdiction
    category: Literal['business', 'interest', 'royalty', 'rental', 'dividend', 'capital_gain']
    net_taxable_income: Money
    foreign_tax: Money
    treaty_applies: StrictBool
    treaty_permitted_tax: Money | None = None


class Workpaper(BaseModel):
    model_config = ConfigDict(extra='forbid')
    taxable_income: Money
    foreign_incomes: list[ForeignIncome] = Field(min_length=1, max_length=200)
    prior_credit_reduction_or_refund: Money
    taxable_scope_source_period_and_fx_verified: StrictBool
    treaty_entitlement_and_tax_evidence_verified: StrictBool
    recapture_of_previously_credited_tax_verified: StrictBool


def calculate(workpaper, *, indonesian_tax_before_credit):
    p = Workpaper.model_validate(workpaper)
    if not all((p.taxable_scope_source_period_and_fx_verified,
                p.treaty_entitlement_and_tax_evidence_verified,
                p.recapture_of_previously_credited_tax_verified)):
        raise ValueError('Taxable scope, source, period, FX, treaty and recapture evidence require verification')
    total = Fraction(p.taxable_income)
    tax = Fraction(computed_amount(indonesian_tax_before_credit))
    if not total and tax:
        raise ValueError('Positive Indonesian tax requires positive taxable income')
    keys = [(s.country, s.category) for s in p.foreign_incomes]
    if len(set(keys)) != len(keys):
        raise ValueError('Aggregate each country and income type exactly once')
    rows = []
    for source in p.foreign_incomes:
        if source.country == 'id':
            raise ValueError('Foreign credit requires foreign-source income')
        if source.treaty_applies != (source.treaty_permitted_tax is not None):
            raise ValueError('Provide an explicit permitted tax, including zero, exactly when a treaty applies')
        net, paid = Fraction(source.net_taxable_income), Fraction(source.foreign_tax)
        cap = min(tax, tax * net / total) if total else Fraction(0)
        allowed = min(paid, cap)
        treaty = None if source.treaty_permitted_tax is None else Fraction(source.treaty_permitted_tax)
        if treaty is not None:
            allowed = min(allowed, treaty)
        rows.append(dict(country=source.country, category=source.category, net_taxable_income=net,
            foreign_tax=paid, treaty_permitted_tax=treaty, indonesian_tax_limit=cap,
            credit_before_overall_cap=allowed))
    provisional = sum((r['credit_before_overall_cap'] for r in rows), Fraction(0))
    used = min(tax, provisional)
    recapture = Fraction(p.prior_credit_reduction_or_refund)
    def convert(value):
        if isinstance(value, Fraction):
            with localcontext() as ctx:
                ctx.prec = 40
                return Decimal(value.numerator) / Decimal(value.denominator)
        if isinstance(value, list): return [convert(v) for v in value]
        if isinstance(value, dict): return {k: convert(v) for k, v in value.items()}
        return value
    return convert(dict(policy_version='id-article24-credit-20261122', currency='IDR',
        taxable_income=total, indonesian_tax_before_credit=tax, source_credits=rows,
        allowed_foreign_tax_credit=used, overall_cap_reduction=provisional-used,
        unrelieved_foreign_tax=sum((r['foreign_tax'] for r in rows), Fraction(0))-used,
        tax_after_credit=tax-used, prior_credit_recapture=recapture,
        liability_after_recapture=tax-used+recapture,
        sources=[dict(doc_id='id.pmk192.2018.foreign-credit',
            title='PMK192/PMK.03/2018 foreign income tax credits',
            url='https://www.pajak.go.id/id/pelaksanaan-pengkreditan-pajak-atas-penghasilan-dari-luar-negeri',
            file='database/raw/id/id.pmk192.2018.foreign-credit.20261122.html',
            sha256='b9f8268bb972c1b46170ed934fdf95229493de6eec32a4c1fbf62aa2712be338',
            locator='Articles4,6-10')], stage='verified_credit_component_before_filing_rounding'))
