"""Thai foreign-tax attribution before treaty entitlement and credit limits.

RD November2025 manual, Part1 item1.2 (PDF page19): attribute tax paid on
one foreign income pool to the portion remitted. Inputs are consistently
converted THB amounts for the same country, income type and earnings pool.
This arithmetic does not establish that the resulting tax is creditable.
"""
from decimal import Decimal, localcontext
from dataclasses import dataclass
import re

from .arithmetic import amount


SOURCE = 'https://www.rd.go.th/fileadmin/user_upload/porphor/GuideTaxFromAbroad_EN.pdf'


@dataclass(frozen=True)
class ForeignIncomePool:
    pool_id: str
    income_index: int
    total_foreign_income: Decimal | str | int
    foreign_income_tax_paid: Decimal | str | int
    eligible_foreign_income_tax_paid: Decimal | str | int
    previously_remitted_income: Decimal | str | int
    remittances: tuple


def prepare_case_foreign_tax(case, pools, *, tracing_fx_and_entitlement_verified):
    """Reconcile original earnings/tax pools with saved2026 remitted receipts.

    For this adapter the saved foreign_tax_paid is total tax paid on the
    original pools, not the remitted fraction. All amounts within each pool
    must use the same documented THB valuation basis. Pool IDs identify
    disjoint source income/tax records; prior remittances consume the balance.
    Each pool has one income date and residence-day count. No eligibility is
    inferred: eligible tax is separately reviewed, bounded by actual tax paid.
    """
    from .thailand_remittances import RemittanceTranche, prepare_case_remittances
    if tracing_fx_and_entitlement_verified is not True:
        raise ValueError('Verify disjoint income pools, FX, tracing and treaty entitlement')
    if not isinstance(pools, (list, tuple)) or not 1 <= len(pools) <= 1000:
        raise ValueError('Provide traced foreign-income pools')
    ids, all_tranches, pool_data = set(), [], []
    for pool in pools:
        if not isinstance(pool, ForeignIncomePool):
            raise ValueError('Invalid foreign-income pool')
        if (not isinstance(pool.pool_id, str) or not pool.pool_id.strip()
                or len(pool.pool_id) > 200 or pool.pool_id in ids):
            raise ValueError('Income pool identifiers must be unique')
        ids.add(pool.pool_id)
        if type(pool.income_index) is not int:
            raise ValueError('Income pool must reference a saved income index')
        if not isinstance(pool.remittances, (list, tuple)) or not pool.remittances:
            raise ValueError('Income pool requires traced current-year remittances')
        if any(not isinstance(r, RemittanceTranche) or r.income_index != pool.income_index
               for r in pool.remittances):
            raise ValueError('Remittances must reference their income pool item')
        if len({(r.income_date, r.days_in_thailand_in_income_year) for r in pool.remittances}) != 1:
            raise ValueError('Each income pool must have a single earnings date and residence basis')
        original, paid, eligible, previous = map(amount, (pool.total_foreign_income,
            pool.foreign_income_tax_paid, pool.eligible_foreign_income_tax_paid, pool.previously_remitted_income))
        if original == 0 or eligible > paid:
            raise ValueError('Pool earnings must be positive and eligible tax cannot exceed paid tax')
        with localcontext() as context:
            context.prec = 40
            remitted = sum((amount(r.remitted_income) for r in pool.remittances), amount(0))
            if previous + remitted > original:
                raise ValueError('Prior and current remittances exceed original income pool')
        all_tranches.extend(pool.remittances)
        pool_data.append((pool, original, paid, eligible, previous, remitted))
    reconciliation = prepare_case_remittances(case, all_tranches,
        foreign_income_and_tracing_verified=True)
    paid_by_item, outputs = {}, []
    offset = 0
    with localcontext() as context:
        context.prec = 40
        for pool, original, paid, eligible, previous, remitted in pool_data:
            portions = reconciliation['portions'][offset:offset + len(pool.remittances)]
            offset += len(pool.remittances)
            included = sum((r['included_before_relief'] for r in portions), amount(0))
            paid_by_item[pool.income_index] = paid_by_item.get(pool.income_index, amount(0)) + paid
            item = case.incomes[pool.income_index]
            outputs.append(dict(pool_id=pool.pool_id, income_index=pool.income_index,
                country=item.source_jurisdiction, category=item.category,
                original_foreign_income=original, original_foreign_tax_paid=paid,
                previously_remitted_income=previous, current_remitted_income=remitted,
                included_assessable_income=included, remaining_income=original-previous-remitted,
                attributable_paid_tax=included*paid/original,
                eligible_attributable_tax=included*eligible/original))
        expected = {i: item.foreign_tax_paid for i, item in enumerate(case.incomes)
                    if item.source_jurisdiction != 'th'}
        if paid_by_item != expected:
            raise ValueError('Original pool tax payments must reconcile every saved foreign tax amount')
    return dict(pools=outputs, remittance_reconciliation=reconciliation,
                stage='saved_case_foreign_tax_reconciled_before_country_limits', sources=[SOURCE])


def attribute_remitted_tax(*, total_foreign_income, foreign_income_tax_paid,
                           remitted_income, tax_year, source_and_fx_verified):
    """Return Part1 G/H, without pooling countries or deciding final credit.

    Tax paid must exclude penalties and non-income taxes. The caller must
    establish source, earnings-pool tracing, tax-payment evidence and a
    consistent permitted remittance-date exchange rate. A saved remitted
    income amount alone is not a valid substitute for total foreign earnings.
    """
    if type(tax_year) is not int or tax_year != 2026:
        raise ValueError('This policy covers tax year2026 only')
    if source_and_fx_verified is not True:
        raise ValueError('Verify income pool, paid income tax, remittance tracing and FX basis')
    income, paid, remitted = map(amount, (total_foreign_income, foreign_income_tax_paid, remitted_income))
    if income == 0 or remitted > income:
        raise ValueError('Foreign earnings must be positive and cover the remitted income')
    with localcontext() as context:
        context.prec = 40
        # Multiply first to avoid rounding the remittance fraction prematurely.
        attributable = remitted * paid / income
        return dict(tax_year=tax_year, currency='THB',
                    total_foreign_income=income, foreign_income_tax_paid=paid,
                    remitted_income=remitted,
                    remitted_percentage=remitted * 100 / income,
                    foreign_tax_attributable_to_remittance=attributable,
                    stage='foreign_tax_attribution_before_entitlement_and_credit_limit',
                    sources=[SOURCE])


def country_credit_limits(countries, *, domestic_assessable_income,
                          thai_tax_before_foreign_credit, tax_year,
                          entitlement_and_basis_verified):
    """Apply Part3 limits to already reviewed country totals, before rounding.

    Every foreign assessable receipt belongs in a country's remitted income,
    including receipts without credit entitlement. eligible_attributable_tax
    must already exclude tax beyond treaty taxing rights, non-income taxes,
    penalties and tax on excluded income. This function does not infer that
    eligibility or calculate taxable income/expenses from gross receipts.
    """
    if type(tax_year) is not int or tax_year != 2026:
        raise ValueError('This policy covers tax year2026 only')
    if entitlement_and_basis_verified is not True:
        raise ValueError('Verify treaty entitlement, source tax caps and complete assessable income')
    if not isinstance(countries, (list, tuple)) or not 1 <= len(countries) <= 250:
        raise ValueError('Provide complete foreign-country totals')
    domestic, thai_tax = map(amount, (domestic_assessable_income, thai_tax_before_foreign_credit))
    seen, inputs = set(), []
    for row in countries:
        if not isinstance(row, dict) or set(row) != {'country', 'remitted_assessable_income', 'eligible_attributable_tax'}:
            raise ValueError('Each country requires remitted assessable income and eligible attributable tax')
        country = row['country']
        if not isinstance(country, str) or not re.fullmatch('[a-z]{2}', country) or country == 'th' or country in seen:
            raise ValueError('Use distinct foreign-country codes')
        seen.add(country)
        income, paid = map(amount, (row['remitted_assessable_income'], row['eligible_attributable_tax']))
        if income == 0 and paid != 0:
            raise ValueError('Credit requires attributable assessable income')
        inputs.append((country, income, paid))
    with localcontext() as context:
        context.prec = 40
        total = domestic + sum((income for _, income, _ in inputs), amount(0))
        if total == 0 and thai_tax != 0:
            raise ValueError('Tax cannot be allocated without assessable income')
        output = []
        for country, income, paid in sorted(inputs):
            limit = income * thai_tax / total if total else amount(0)
            allowed = min(paid, limit)
            output.append(dict(country=country, remitted_assessable_income=income,
                               eligible_attributable_tax=paid, credit_limit=limit,
                               allowable_foreign_credit=allowed, unused_foreign_tax=paid-allowed))
        return dict(tax_year=tax_year, currency='THB', countries=output,
                    total_assessable_income=total, domestic_assessable_income=domestic,
                    thai_tax_before_foreign_credit=thai_tax,
                    allowable_foreign_credit=sum((r['allowable_foreign_credit'] for r in output), amount(0)),
                    stage='reviewed_country_credit_limits_before_rounding_and_settlement',
                    sources=[SOURCE, 'https://www.rd.go.th/fileadmin/user_upload/porphor/GuideTaxFromAbroad_TH.pdf'])
