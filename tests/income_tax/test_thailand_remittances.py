from datetime import date, datetime
from decimal import Decimal

import pytest

from packages.income_tax.thailand_remittances import classify_remittance


def run(**changes):
    args = dict(income_date=date(2024,1,1), remittance_date=date(2026,1,1),
                days_in_thailand_in_income_year=180, tax_year=2026,
                foreign_income_and_tracing_verified=True)
    args.update(changes)
    return classify_remittance('123456.78', **args)


@pytest.mark.parametrize('earned,days,expected', [
    (date(2023,12,31),365,'0'), (date(2024,1,1),179,'0'),
    (date(2024,1,1),180,'123456.78'), (date(2024,12,31),366,'123456.78'),
    (date(2026,1,1),180,'123456.78')])
def test_income_year_and_residency_boundaries(earned,days,expected):
    result=run(income_date=earned,days_in_thailand_in_income_year=days)
    assert result['included_before_relief']==Decimal(expected)
    assert result['included_before_relief']+result['excluded_from_section41_remittance']==Decimal('123456.78')


@pytest.mark.parametrize('changes', [
    {'income_date':date(2026,1,2)}, {'remittance_date':date(2025,12,31)},
    {'income_date':'2024-01-01'}, {'income_date':datetime(2024,1,1)},
    {'days_in_thailand_in_income_year':True}, {'days_in_thailand_in_income_year':180.0},
    {'days_in_thailand_in_income_year':-1}, {'days_in_thailand_in_income_year':367},
    {'income_date':date(2025,1,1),'days_in_thailand_in_income_year':366},
    {'tax_year':2025}, {'tax_year':2026.0},
    {'foreign_income_and_tracing_verified':False}, {'foreign_income_and_tracing_verified':1}])
def test_invalid_or_unverified_inputs_fail(changes):
    with pytest.raises(ValueError):run(**changes)
