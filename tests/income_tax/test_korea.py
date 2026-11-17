from decimal import Decimal

import pytest

from packages.income_tax.korea import gross_taxes, company_minimum_reference


def compute(base,local=None,**changes):
    facts=dict(tax_year=2026,subject='company',article60_2_1_1_company=False,
        annual_standard_schedule_confirmed=True)
    facts.update(changes)
    return gross_taxes(base,base if local is None else local,**facts)


@pytest.mark.parametrize('base,tax',[(0,0),(200000000,20000000),
    (20000000000,3980000000),(300000000000,65580000000),
    (300000000001,Decimal('65580000000.25'))])
def test_ordinary_company_statutory_boundaries(base,tax):
    result=compute(base)
    assert result['national_gross_tax']==tax
    assert result['local_gross_tax']==Decimal(tax)/10


def test_specified_company_does_not_receive_first_band():
    r=compute(200000000,article60_2_1_1_company=True)
    assert r['national_gross_tax']==40000000
    assert r['local_gross_tax']==4000000
    r=compute(300000000000,article60_2_1_1_company=True)
    assert r['national_gross_tax']==65600000000
    assert r['local_gross_tax']==6560000000


@pytest.mark.parametrize('base,tax',[(14000000,840000),(50000000,6240000),
    (88000000,15360000),(150000000,37060000),(300000000,94060000),
    (500000000,174060000),(1000000000,384060000),(1000000001,Decimal('384060000.45'))])
def test_personal_statutory_boundaries(base,tax):
    r=compute(base,subject='individual',article60_2_1_1_company=None)
    assert r['national_gross_tax']==tax
    assert r['local_gross_tax']==Decimal(tax)/10


def test_local_base_is_independent():
    r=compute('1000000000',local='200000000')
    assert r['national_gross_tax']==180000000
    assert r['local_gross_tax']==2000000
    assert 'final_tax' not in r


def test_provenance_preserves_commencement_and_original_table_versions():
    sources=compute('1')['sources']
    assert any(s['doc_id']=='kr.local-tax.amendment21308.2025' for s in sources)
    assert any(s['sha256']=='4856297a4fc5feaba4cd39a2c84e40edfb8016a98d60f7cf2d1e8393549b8363' for s in sources)
    sources[0]['provisions'].clear()
    assert compute('1')['sources'][0]['provisions']
    personal=compute('1',subject='individual',article60_2_1_1_company=None)['sources']
    assert not any('corporate' in s['doc_id'] for s in personal)
    assert any(s['doc_id']=='kr.local-tax.table.personal' for s in personal)


@pytest.mark.parametrize('changes',[dict(tax_year=2025),dict(tax_year=True),
    dict(subject='other'),dict(article60_2_1_1_company=1),
    dict(article60_2_1_1_company=None),dict(annual_standard_schedule_confirmed=False),
    dict(subject='individual')])
def test_unverified_schedule_rejected(changes):
    with pytest.raises(ValueError):compute('1',**changes)


@pytest.mark.parametrize('value',[True,1.1,'NaN','-1','1.0000001'])
def test_invalid_bases_rejected_independently(value):
    with pytest.raises(ValueError):compute(value)
    with pytest.raises(ValueError):compute('1',local=value)


@pytest.mark.parametrize('base,regime,expected',[(0,'general',0),
    (10000000000,'general',1000000000),
    (100000000000,'general',11800000000),
    (100000000001,'general',Decimal('11800000000.17')),
    (10000000000,'sme',700000000),
    (10000000000,'graduated_first_three_years',800000000),
    (10000000000,'graduated_next_two_years',900000000)])
def test_minimum_reference_regimes_and_boundaries(base,regime,expected):
    r=company_minimum_reference(base,tax_year=2026,regime=regime,
        annual_applicability_and_restoration_confirmed=True)
    assert r['minimum_reference_tax']==expected
    assert r['sources'][0]['doc_id']=='kr.special-tax-treatment.article132.2026'
    assert 'final_tax' not in r


@pytest.mark.parametrize('change',[dict(tax_year=2025),dict(tax_year=True),
    dict(regime='unknown'),dict(regime=None),dict(regime=[]),
    dict(annual_applicability_and_restoration_confirmed=False)])
def test_minimum_reference_requires_explicit_eligibility(change):
    facts=dict(tax_year=2026,regime='general',annual_applicability_and_restoration_confirmed=True)
    facts.update(change)
    with pytest.raises(ValueError):company_minimum_reference('1',**facts)
