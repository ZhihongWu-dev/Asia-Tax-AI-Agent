from copy import deepcopy
import pytest
from packages.income_tax.india_foreign_credit import calculate


def fixture():
    return dict(sources=[dict(source_id='branch_a', country='sg', foreign_tax_paid_inr='300',
        disputed_tax_excluded_inr='0', treaty_applies=True, treaty_permitted_tax_inr='250',
        normal_indian_tax_attributable='200')],
        indian_residency_and_tax_eligibility_verified=True,
        source_tax_year_fx_and_dispute_treatment_verified=True,
        attributable_tax_excludes_interest_fees_penalties_verified=True,
        required_statements_payment_evidence_and_verification_confirmed=True)


def test_separate_sources_in_same_country_do_not_pool_limits():
    p = fixture()
    second = deepcopy(p['sources'][0])
    second.update(source_id='branch_b', foreign_tax_paid_inr='10', normal_indian_tax_attributable='500')
    p['sources'].append(second)
    result = calculate(p, normal_indian_tax='1000')
    assert result['normal_foreign_tax_credit'] == 210
    assert result['normal_tax_after_foreign_credit'] == 790


@pytest.mark.parametrize('disputed,ceiling,expected', [('150','250',150),('0','100',100),('0','0',0),('300','250',0)])
def test_disputed_and_treaty_limits(disputed, ceiling, expected):
    p = fixture()
    p['sources'][0].update(disputed_tax_excluded_inr=disputed, treaty_permitted_tax_inr=ceiling)
    assert calculate(p, normal_indian_tax='1000')['normal_foreign_tax_credit'] == expected


def test_normal_and_section206_limits_are_separate():
    p = fixture()
    p['sources'][0].update(normal_indian_tax_attributable='100', section206_tax_attributable='230')
    result = calculate(p, normal_indian_tax='500', section206_tax='600')
    assert result['normal_foreign_tax_credit'] == 100
    assert result['section206_foreign_tax_credit'] == 230
    assert result['section206_extra_credit_ignored_for_tax_credit_computation'] == 130
    assert result['section206_tax_after_foreign_credit'] == 370
    assert 'new_mat_credit' not in result


@pytest.mark.parametrize('country', ['cn','hk','sg','id','vn','my','th','ae','jp','kr'])
def test_treaty_ineligibility_does_not_enable_section160(country):
    p = fixture()
    p['sources'][0].update(country=country, treaty_applies=False, treaty_permitted_tax_inr=None,
        section160_relief_limit_inr='50')
    with pytest.raises(ValueError, match='Section160 requires no agreement'):
        calculate(p, normal_indian_tax='1000')


@pytest.mark.parametrize('change', ['duplicate','domestic','dispute','treaty','attribution','section206','evidence'])
def test_invalid_claim_rejected(change):
    p = fixture()
    s = p['sources'][0]
    if change == 'duplicate': p['sources'].append(deepcopy(s))
    elif change == 'domestic': s['country'] = 'in'
    elif change == 'dispute': s['disputed_tax_excluded_inr'] = '301'
    elif change == 'treaty': s['treaty_permitted_tax_inr'] = None
    elif change == 'attribution': s['normal_indian_tax_attributable'] = '1001'
    elif change == 'section206': s['section206_tax_attributable'] = '1'
    else: p['required_statements_payment_evidence_and_verification_confirmed'] = False
    with pytest.raises(ValueError): calculate(p, normal_indian_tax='1000')
