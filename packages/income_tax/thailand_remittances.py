"""Section41/P161/P162 applicability for individually traced foreign income.

This component determines inclusion before exemptions, deductions, treaty relief
or foreign tax credits. It must not be presented as a final tax assessment.
"""
from calendar import isleap
from datetime import date
from dataclasses import dataclass
from decimal import Decimal, localcontext

from .arithmetic import ZERO, amount


def classify_remittance(remitted_income, *, income_date, remittance_date,
                        days_in_thailand_in_income_year, tax_year,
                        foreign_income_and_tracing_verified):
    """Classify a traced income portion remitted in calendar2026, in THB.

The amount is the income portion, not an unclassified bank transfer (which may
contain capital). Residency is tested in the income year. No special exemption
or treaty entitlement is inferred from an excluded/included classification.
"""
    if type(tax_year) is not int or tax_year != 2026:
        raise ValueError('This policy covers remittances in tax year2026 only')
    if type(income_date) is not date or type(remittance_date) is not date:
        raise ValueError('Provide exact income and remittance dates')
    if remittance_date.year != tax_year or income_date > remittance_date:
        raise ValueError('Remittance must be in the assessment year and follow income')
    days = days_in_thailand_in_income_year
    if type(days) is not int or not 0 <= days <= 365 + int(isleap(income_date.year)):
        raise ValueError('Income-year presence must be a valid whole-day count')
    if foreign_income_and_tracing_verified is not True:
        raise ValueError('Verify foreign source, income character and remittance tracing')
    value = amount(remitted_income)
    if income_date < date(2024, 1, 1):
        reason = 'pre_2024_income_excluded_from_p161'
        included = ZERO
    elif days < 180:
        reason = 'not_resident_in_income_year'
        included = ZERO
    else:
        reason = 'resident_income_remitted_in_assessment_year'
        included = value
    return dict(tax_year=tax_year, currency='THB', income_date=income_date,
                remittance_date=remittance_date, income_year=income_date.year,
                income_year_presence_days=days, remitted_income=value,
                included_before_relief=included, excluded_from_section41_remittance=value-included,
                reason=reason, stage='remittance_inclusion_before_reliefs_and_tax',
                sources=[
                    'https://www.rd.go.th/5937.html',
                    'https://www.rd.go.th/fileadmin/user_upload/kormor/newlaw/dn161A.pdf',
                    'https://www.rd.go.th/fileadmin/user_upload/kormor/newlaw/dn162A.pdf'])


@dataclass(frozen=True)
class RemittanceTranche:
    income_index: int
    remitted_income: Decimal | str | int
    income_date: date
    remittance_date: date
    days_in_thailand_in_income_year: int


def prepare_case_remittances(case, tranches, *, foreign_income_and_tracing_verified):
    """Reconcile every saved foreign-income receipt with traced remitted portions.

Saved foreign gross amounts represent income remitted in the assessment year,
not the full original earnings or capital transfers. Multiple portions may map
to one income item; no foreign item may be omitted. Domestic items are outside
this classifier. This does not calculate tax, deductions or credit entitlement.
"""
    from packages.contracts.income_tax import IncomeTaxCase
    if not isinstance(case, IncomeTaxCase) or case.missing_for_calculation():
        raise ValueError('A complete confirmed saved income case is required')
    if (case.jurisdiction != 'th' or case.subject != 'individual' or
            case.period_start != date(2026,1,1) or case.period_end != date(2026,12,31)):
        raise ValueError('Thai individual calendar2026 case required')
    if not isinstance(tranches, (list,tuple)) or not 1 <= len(tranches) <= 1000:
        raise ValueError('Provide between one and1000 traced remittance portions')
    expected={n:i.gross_amount for n,i in enumerate(case.incomes) if i.source_jurisdiction!='th'}
    totals, presence, results = {}, {}, []
    with localcontext() as context:
        context.prec=40
        for line in tranches:
            if (not isinstance(line,RemittanceTranche) or type(line.income_index) is not int
                    or line.income_index not in expected):
                raise ValueError('Each portion must reference a saved foreign-income item')
            result=classify_remittance(line.remitted_income, income_date=line.income_date,
                remittance_date=line.remittance_date,
                days_in_thailand_in_income_year=line.days_in_thailand_in_income_year,
                tax_year=2026, foreign_income_and_tracing_verified=foreign_income_and_tracing_verified)
            year=result['income_year'];days=line.days_in_thailand_in_income_year
            if year in presence and presence[year]!=days:
                raise ValueError('Presence days must be consistent for the same income year')
            presence[year]=days
            totals[line.income_index]=totals.get(line.income_index,ZERO)+result['remitted_income']
            result.update(income_index=line.income_index,
                          category=case.incomes[line.income_index].category,
                          source_jurisdiction=case.incomes[line.income_index].source_jurisdiction)
            results.append(result)
        if not expected or totals!=expected:
            raise ValueError('Traced portions must reconcile every saved foreign-income amount exactly')
        return dict(portions=results,
            remitted_income=sum((r['remitted_income'] for r in results),ZERO),
            included_before_relief=sum((r['included_before_relief'] for r in results),ZERO),
            excluded_from_section41_remittance=sum((r['excluded_from_section41_remittance'] for r in results),ZERO),
            stage='saved_case_remittance_reconciliation_before_reliefs_and_tax')
