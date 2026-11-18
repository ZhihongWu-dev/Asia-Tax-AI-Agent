from decimal import Decimal, localcontext
import hashlib
from pathlib import Path
import pytest

from packages.income_tax.japan_local import ordinary_enterprise_levies, SOURCES


def compute(income, **changes):
    args = dict(fiscal_start_year=2026, months=12, reduced_bands_eligible=True,
        tokyo_surcharge_applies=False, ordinary_income_based_scope_verified=True)
    args.update(changes)
    return ordinary_enterprise_levies(income, **args)


def test_official_four_month_example_allocates_before_rounding():
    # Tokyo return instructions page15 gives these three independently rounded bases.
    result = compute('2856420', months=4)
    assert [r['taxable_base'] for r in result['bands']] == [1333000,1333000,189000]
    assert [r['allocated_before_rounding'] for r in result['bands']] == [1333333,1333333,189754]
    assert [r['tax'] for r in result['bands']] == [46600,70600,13200]
    assert result['enterprise_tax_before_credits'] == 130400
    assert result['special_enterprise_tax_before_credits'] == 48200


def test_surcharge_does_not_inflate_special_enterprise_tax():
    standard = compute('5000000')
    surcharge = compute('5000000', tokyo_surcharge_applies=True)
    assert standard['enterprise_tax_before_credits'] == 193000
    assert surcharge['enterprise_tax_before_credits'] == 206600
    assert surcharge['standard_rate_enterprise_tax'] == 193000
    assert standard['special_enterprise_tax_before_credits'] == surcharge['special_enterprise_tax_before_credits'] == 71400


def test_no_reduced_bands_taxes_entire_base_at_upper_rate():
    result = compute('5000000', reduced_bands_eligible=False, tokyo_surcharge_applies=True)
    assert len(result['bands']) == 1
    assert result['enterprise_tax_before_credits'] == 374000
    assert result['standard_rate_enterprise_tax'] == 350000
    assert result['special_enterprise_tax_before_credits'] == 129500


@pytest.mark.parametrize('income,enterprise,special',[
    ('0',0,0),('999',0,0),('2999',0,0),('3000',100,0),
    ('3999999',139900,51700),('4000000',140000,51800),
    ('4001999',140000,51800),('4002000',140100,51800),
    ('8000000',352000,130200),
])
def test_band_and_two_rounding_boundaries(income,enterprise,special):
    result = compute(income)
    assert result['enterprise_tax_before_credits'] == enterprise
    assert result['special_enterprise_tax_before_credits'] == special


@pytest.mark.parametrize('changes',[
    dict(months=0),dict(months=13),dict(months=True),dict(months='4'),
    dict(fiscal_start_year=2025),dict(fiscal_start_year=True),
    dict(reduced_bands_eligible=1),dict(tokyo_surcharge_applies=0),
    dict(ordinary_income_based_scope_verified=False),dict(ordinary_income_based_scope_verified=1),
])
def test_scope_and_eligibility_are_not_coerced(changes):
    with pytest.raises(ValueError): compute('1000000',**changes)


@pytest.mark.parametrize('income',['-1','0.1','NaN',True,1.1])
def test_whole_yen_inputs_only(income):
    with pytest.raises(ValueError): compute(income)


def test_precision_and_source_snapshot_isolation():
    with localcontext() as ctx:
        ctx.prec = 6
        result = compute('1000000000000000000')
        assert result['enterprise_tax_before_credits'] == Decimal('69999999999792000')
    result['sources'][0]['url'] = 'changed'
    assert compute('0')['sources'][0]['url'].startswith('https://www.tax.metro.tokyo.lg.jp/')
    root=Path(__file__).resolve().parents[2]
    assert len(SOURCES)==3
    for source in SOURCES:
        assert hashlib.sha256((root/source['file']).read_bytes()).hexdigest()==source['sha256']


from packages.income_tax.japan_local import ordinary_per_capita_component


def per_capita(capital='10000000', **changes):
    args=dict(fiscal_start_year=2026,employees_in_ward=50,office_months=12,
        component='wards_only_principal',ordinary_capital_scope_verified=True)
    args.update(changes)
    return ordinary_per_capita_component(capital,**args)


@pytest.mark.parametrize('capital,employees,expected',[
    ('10000000',50,70000),('10000000',51,140000),
    ('10000001',50,180000),('100000000',51,200000),
    ('100000001',50,290000),('1000000000',51,530000),
    ('1000000001',50,950000),('5000000000',51,2290000),
    ('5000000001',50,1210000),('5000000001',51,3800000),
])
def test_official_ordinary_capital_and_employee_table(capital,employees,expected):
    result=per_capita(capital,employees_in_ward=employees)
    assert result['annual_component_amount']==expected
    assert result['per_capita_tax_before_prepayments']==expected


def test_one_month_principal_ward_must_not_round_separate_components():
    assert per_capita(office_months=1)['per_capita_tax_before_prepayments']==5800
    ward=per_capita(office_months=1,component='ward_only')
    prefecture=per_capita(office_months=1,component='prefectural_only')
    assert ward['per_capita_tax_before_prepayments']==4100
    assert prefecture['per_capita_tax_before_prepayments']==1600
    assert ward['annual_component_amount']==50000
    assert prefecture['annual_component_amount']==20000


def test_annual_extra_ward_adds_no_second_prefecture():
    main=per_capita()
    extra=per_capita(component='ward_only',employees_in_ward=51)
    assert main['per_capita_tax_before_prepayments']+extra['per_capita_tax_before_prepayments']==190000


def test_prefectural_amount_ignores_ward_employee_threshold():
    assert per_capita(component='prefectural_only',employees_in_ward=0)['annual_component_amount']==20000
    assert per_capita(component='prefectural_only',employees_in_ward=1000)['annual_component_amount']==20000


@pytest.mark.parametrize('changes',[
    dict(employees_in_ward=True),dict(employees_in_ward=-1),dict(employees_in_ward=50.0),
    dict(office_months=0),dict(office_months=13),dict(office_months=True),
    dict(component='municipal'),dict(ordinary_capital_scope_verified=False),
    dict(ordinary_capital_scope_verified=1),dict(fiscal_start_year=True),dict(fiscal_start_year=2025),
])
def test_per_capita_scope_and_counts_are_strict(changes):
    with pytest.raises(ValueError):per_capita(**changes)


def test_no_profit_exemption_in_per_capita_component():
    # No income parameter: ordinary zero-profit companies can still owe this levy.
    assert per_capita('0',employees_in_ward=0)['per_capita_tax_before_prepayments']==70000
    with pytest.raises(ValueError):per_capita('0.1')


from packages.income_tax.japan_local import ordinary_inhabitant_levy


def inhabitant(national='10000000',**changes):
    args=dict(fiscal_start_year=2026,months=12,registered_capital='100000000',
        ward_allocated_base=national,municipality_allocated_base='0',ordinary_domestic_scope_verified=True)
    args.update(changes)
    return ordinary_inhabitant_levy(national,**args)


@pytest.mark.parametrize('national,capital,months,surcharge,tax',[
    ('10000000','100000000',12,False,700000),
    ('10000999','100000000',12,False,700000),
    ('10001000','100000000',12,True,1040100),
    ('10000000','100000001',12,True,1040000),
    ('3333999','100000000',4,False,233300),
    ('3334000','100000000',4,True,346700),
])
def test_rate_threshold_uses_rounded_nationwide_base_and_short_year(national,capital,months,surcharge,tax):
    result=inhabitant(national,registered_capital=capital,months=months)
    assert result['surcharge_applies'] is surcharge
    assert result['final_levy']==tax


def test_small_local_allocation_does_not_qualify_large_nationwide_base():
    result=inhabitant('15000000',ward_allocated_base='1000000',municipality_allocated_base='2000000')
    assert result['surcharge_applies'] is True
    assert result['ward_levy_before_credits']==104000
    assert result['municipality_prefectural_levy_before_credits']==40000
    assert result['final_levy']==144000


def test_combine_ward_and_prefectural_parts_before_hundred_floor():
    result=inhabitant('4000',ward_allocated_base='1000',municipality_allocated_base='3000')
    assert result['ward_levy_before_credits']==70
    assert result['municipality_prefectural_levy_before_credits']==30
    assert result['final_levy']==100


def test_credit_precedes_final_rounding_and_prepayment_can_produce_refund():
    result=inhabitant('2000',allowed_credits=30,prepaid_levy=200)
    assert result['levy_before_credits']==140
    assert result['net_levy_before_rounding']==110
    assert result['final_levy']==100
    assert result['balance_due']==-100
    assert inhabitant('0',tax_credit_additions=200,allowed_credits=101)['final_levy']==0


@pytest.mark.parametrize('changes',[
    dict(ward_allocated_base='10000001'),dict(allowed_credits='700001'),
    dict(months=0),dict(months=13),dict(months=True),dict(months=12.0),
    dict(fiscal_start_year=2025),dict(fiscal_start_year=True),
    dict(ordinary_domestic_scope_verified=False),dict(ordinary_domestic_scope_verified=1),
    dict(registered_capital='0.1'),dict(prepaid_levy=True),
])
def test_inhabitant_rejects_unverified_or_unreconciled_inputs(changes):
    with pytest.raises(ValueError):inhabitant(**changes)
