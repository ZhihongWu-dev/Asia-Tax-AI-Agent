from decimal import Decimal, localcontext
import pytest
from tests.income_tax.test_japan_tokyo import facts, basis as tokyo_basis, run


def basis():
    b = tokyo_basis()
    p = b.pop('tokyo_local')
    p.pop('inhabitant_interim_liability')
    p.pop('per_capita_interim_liability')
    for key in ('prefectural_inhabitant', 'city_inhabitant', 'prefectural_capitation', 'city_capitation'):
        p[key + '_interim_liability'] = '0'
    p['wards'] = [dict(ward_name='Kita', employees=50)]
    b['osaka_local'] = p
    return b


def test_annual_separate_components_and_sources():
    r = run(assertion=basis())
    assert r['national_final_tax'] == '1835300'
    local = r['osaka_local']
    assert local['local_tax_components'] == dict(enterprise='492000', special_enterprise='182000',
        prefectural_inhabitant='16600', city_inhabitant='99800', prefectural_capitation='20000', city_capitation='50000')
    assert r['final_tax'] == '2695700'
    assert len({s['doc_id'] for s in local['sources']}) == len(local['sources'])
    assert all('osaka' in s['doc_id'] for s in local['sources'])


def test_refunds_do_not_offset_other_components():
    b = basis()
    b['osaka_local']['enterprise_interim_liability'] = '600000'
    r = run(assertion=b)['osaka_local']
    assert r['local_balances']['enterprise'] == '-108000'
    assert r['local_refunds'] == '108000'
    assert r['local_amounts_payable'] == '368400'


def test_local_loss_reconciliation_is_independent():
    f = facts(); f['claimed_deductions'] = '12000000'
    b = basis(); b['taxable_income_before_rounding'] = '0'
    b['osaka_local'].update(enterprise_income_additions='3000000', eligible_enterprise_prior_losses='200000')
    r = run(f, b)
    assert r['national_final_tax'] == '0'
    assert r['osaka_local']['local_income_reconciliation']['enterprise_taxable_income'] == '800000'
    assert r['osaka_local']['local_final_tax'] == '108300'


def test_two_exclusive_local_scopes_rejected():
    b = basis(); b['tokyo_local'] = tokyo_basis()['tokyo_local']
    with pytest.raises(ValueError, match='cannot be combined'):
        run(assertion=b)


@pytest.mark.parametrize('change', ['unverified', 'fractional_interim', 'duplicate_ward'])
def test_invalid_osaka_paper(change):
    b = basis(); p = b['osaka_local']
    if change == 'unverified': p['ordinary_domestic_entity_verified'] = False
    elif change == 'fractional_interim': p['city_inhabitant_interim_liability'] = '1'
    else: p['wards'].append(dict(p['wards'][0]))
    with pytest.raises(ValueError): run(assertion=b)


def test_ambient_decimal_context_does_not_change_result():
    expected = run(assertion=basis())
    with localcontext() as ctx:
        ctx.prec = 6
        assert run(assertion=basis()) == expected
