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
