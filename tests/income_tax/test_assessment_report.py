from types import SimpleNamespace
from uuid import uuid4
import json
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from apps.api import auth, chat
from packages.chat.store import ChatStore
from packages.reporting.income_tax import render, _json
from tests.chat.auth_support import fixture_user
from tests.income_tax.test_assessment_workflow import COMPANY, HEADERS, facts


def test_report_preserves_saved_snapshot_after_edit_restart_and_owner_boundaries(tmp_path):
    url = 'sqlite:///' + str(tmp_path/'cases.sqlite')
    service = SimpleNamespace(store=ChatStore(url))
    app = FastAPI(); app.include_router(auth.router); app.include_router(chat.router)
    app.dependency_overrides[auth.optional_user] = fixture_user
    app.dependency_overrides[chat.get_service] = lambda: service
    with TestClient(app) as alice, TestClient(app) as bob, TestClient(app) as anon:
        alice.get('/api/auth/session'); bob.get('/api/auth/session')
        case_id = alice.post('/api/cases', headers=HEADERS).json()['id']
        path = f'/api/cases/{case_id}/income-tax'
        data = facts()
        data['incomes'][0]['description'] = '业务收入 ```\n<script>alert(1)</script>'
        assert alice.put(path,headers=HEADERS,json=dict(revision=0,request_id=str(uuid4()),inputs=data)).status_code==200
        response = alice.post(path+'/runs',headers=HEADERS,json=dict(revision=1,request_id=str(uuid4()),basis=COMPANY))
        assert response.status_code==200,response.text
        run = response.json()
        report_path = path+'/runs/'+run['id']+'/report'
        report = alice.get(report_path+'?locale=en')
        assert report.status_code==200,report.text
        assert report.headers['cache-control']=='private, no-store'
        result = report.json()
        assert result['snapshot_hash']==run['snapshot_hash']
        assert result['markdown'].startswith('# Income-tax calculation record')
        assert '249000' in result['markdown']
        assert run['result']['sources'][0]['url'] in result['markdown']
        assert run['result']['sources'][0]['sha256'] in result['markdown']
        assert run['snapshot_hash'] in result['markdown']
        assert 'basis_reconciliation' in result['markdown']
        assert alice.get(report_path).json()['markdown'].startswith('# 所得税计算记录')
        assert alice.get(report_path+'?locale=de').status_code==422
        assert bob.get(report_path).status_code==404
        assert anon.get(report_path).status_code==401
        assert alice.get(path+'/runs/'+str(uuid4())+'/report').status_code==404
        changed = facts(); changed['incomes'][0]['gross_amount']='2000000'
        assert alice.put(path,headers=HEADERS,json=dict(revision=2,request_id=str(uuid4()),inputs=changed)).status_code==200
        service.store.engine.dispose();service.store=ChatStore(url)
        assert alice.get(report_path+'?locale=en').json()==result
        current = alice.get(path).json()
        assert current['income_tax_result'] is None
        assert current['revision']==3
    service.store.engine.dispose()


def test_snapshot_mismatch_rejected():
    with pytest.raises(ValueError,match='snapshot_mismatch'):
        render(dict(inputs={},basis={},result={},snapshot_hash='0'*64))


@pytest.mark.parametrize('policy,manifest,count', [
    ('th', 'th_foreign_2026_sources.json', 4),
    ('cn', 'cn_business_2026_sources.json', 3),
    ('sg', 'sg_employment_2026_sources.json', 3),
    ('cn_small', 'cn_2026_sources.json', 2),
    ('th_dividend', 'th_2026_sources.json', 1),
    ('th_company', 'th_2026_sources.json', 2),
    ('jp_company', 'jp_company_2026_sources.json', 8),
    ('id_company', 'id_2026_sources.json', 6),
])
def test_source_versions_survive_storage_restart_and_report(tmp_path, policy, manifest, count):
    from hashlib import file_digest
    from pathlib import Path
    from tests.income_tax.test_thailand_foreign_assessment import inputs
    from tests.income_tax.test_china_business import saved_inputs
    from tests.income_tax.test_singapore_employment import saved_case_and_basis
    from tests.income_tax.test_china_small_company import saved_inputs as small_company_inputs
    from tests.income_tax.test_thailand_dividend_adapter import inputs as dividend_inputs
    from tests.income_tax.test_japan_company import facts as japan_facts, basis as japan_basis
    from tests.income_tax.test_indonesia_company_reconciliation import inputs as indonesia_inputs

    root = Path(__file__).resolve().parents[2]
    sources = json.loads((root/'packages/income_tax'/manifest).read_text(
        encoding='utf-8'))['sources']
    if policy == 'cn_small':
        sources = [s for s in sources if s['doc_id'] in ('cn.law.eit', 'cn.mof.sta.2023-12')]
    elif policy == 'th_dividend':
        sources = [s for s in sources if s['doc_id'] == 'th.rd.p119-2545']
    elif policy == 'th_company':
        sources = [sources[0], sources[4]]
    assert len(sources) == count
    for source in sources:
        with (root/source['file']).open('rb') as original:
            assert file_digest(original, 'sha256').hexdigest() == source['sha256']
    url = 'sqlite:///' + str(tmp_path/'thai.sqlite')
    service = SimpleNamespace(store=ChatStore(url))
    app = FastAPI(); app.include_router(auth.router); app.include_router(chat.router)
    app.dependency_overrides[auth.optional_user] = fixture_user
    app.dependency_overrides[chat.get_service] = lambda: service
    with TestClient(app) as client:
        client.get('/api/auth/session')
        case_id = client.post('/api/cases', headers=HEADERS).json()['id']
        path = f'/api/cases/{case_id}/income-tax'
        if policy == 'sg':
            case_model, basis_model = saved_case_and_basis()
            data, basis = case_model.model_dump(mode='json'), basis_model.model_dump(mode='json')
        elif policy == 'cn_small':
            data, basis = small_company_inputs()
        elif policy == 'th_dividend':
            data, basis = dividend_inputs()
        elif policy == 'jp_company':
            data, basis = japan_facts(), japan_basis()
        elif policy == 'id_company':
            data, basis = indonesia_inputs()
        elif policy == 'th_company':
            data = facts()
            data.update(jurisdiction='th', currency='THB')
            data['incomes'][0]['source_jurisdiction'] = 'th'
            basis = dict(policy='th_company_2026', net_taxable_profit='1000000',
                scheme='ordinary', sme_eligibility_confirmed=False,
                ordinary_treatment_confirmed=True, allowed_tax_credits='0', prepaid_tax='0',
                basis_confirmed=True, basis_explanation='Verified ordinary Thai company profit basis.')
        else:
            data, basis = inputs() if policy == 'th' else saved_inputs()
        saved = client.put(path, headers=HEADERS, json=dict(
            revision=0, request_id=str(uuid4()), inputs=data))
        assert saved.status_code == 200, saved.text
        if policy in ('th_company', 'jp_company', 'id_company'):
            key = 'net_taxable_profit' if policy == 'th_company' else 'taxable_income_before_rounding'
            rejected = client.post(path+'/runs', headers=HEADERS, json=dict(
                revision=1, request_id=str(uuid4()),
                basis={**basis, key: '1000001'}))
            assert rejected.status_code == 422, rejected.text
            unchanged = client.get(path).json()
            assert unchanged['revision'] == 1
            assert unchanged['income_tax_result'] is None
        response = client.post(path+'/runs', headers=HEADERS, json=dict(
            revision=1, request_id=str(uuid4()), basis=basis))
        assert response.status_code == 200, response.text
        run = response.json()
        for source in sources:
            assert source in run['result']['sources']
        service.store.engine.dispose(); service.store = ChatStore(url)
        report = client.get(path+'/runs/'+run['id']+'/report?locale=en')
        assert report.status_code == 200, report.text
        assert report.json()['snapshot_hash'] == run['snapshot_hash']
        for source in sources:
            assert source['sha256'] in report.json()['markdown']
            assert source['file'] in report.json()['markdown']
    service.store.engine.dispose()


def test_json_fence_preserves_arbitrary_notes_and_exact_decimal_strings():
    data = {'note':'``````\n# replace report\n<script>alert(1)</script>', 'amount':'1000000000000000.123456'}
    lines = _json(data).splitlines()
    assert lines[0]=='```````json' and lines[-1]=='```````'
    assert json.loads('\n'.join(lines[1:-1]))==data


def test_report_invalid_locale_rejected():
    with pytest.raises(ValueError,match='locale'):
        render({}, 'de')


def test_korean_report_keeps_payments_and_refunds_separate():
    from hashlib import sha256
    from tests.income_tax.test_korea_assessment_workflow import inputs, basis, run
    snapshot = dict(inputs=inputs(),basis=basis(),result=run())
    digest = sha256(json.dumps(snapshot,sort_keys=True,separators=(',', ':')).encode()).hexdigest()
    saved = dict(**snapshot,id='example',case_id='example',input_revision=1,
        created_at='2026-11-19T00:00:00Z',status='calculated_basis',snapshot_hash=digest)
    report = render(saved, 'en')
    assert 'Total payable' in report and '2000000' in report
    assert 'Total refundable' in report and '1000000' in report
    assert 'not netted against' in report
    assert 'national' in report and 'local' in report
