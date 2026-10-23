from copy import deepcopy
from pathlib import Path
from threading import Event
from time import monotonic, sleep
from uuid import uuid4

import pytest
from pypdf import PdfReader
from fastapi.testclient import TestClient

from packages.chat.store import ChatStore
from packages.chat.service import ChatService, WorkflowError
from packages.consultation import workflow
from packages.consultation.pdf import comparison, render_pdf
from packages.consultation.reports import ReportJobs
from tests.consultation.fixtures import ready, TEXT, fake_model, fake_calculate, fake_research


@pytest.fixture
def setup(tmp_path):
    store = ChatStore(f'sqlite:///{tmp_path}/brief.sqlite')
    doc = store.create('user:test')
    doc['consultation'] = ready()
    store.save('user:test', doc, 0)
    yield store, doc
    store.engine.dispose()


def wait(manager, store, doc, job):
    deadline = monotonic() + 10
    while monotonic() < deadline:
        value = manager.get(store, 'user:test', doc['id'], job['id'])
        if value['status'] not in ('queued', 'running'): return value
        sleep(.02)
    pytest.fail('PDF job did not finish')


def test_intake_tools_confirmation_and_idempotency(tmp_path, monkeypatch):
    store = ChatStore(f'sqlite:///{tmp_path}/intake.sqlite')
    doc = store.create('user:test')
    monkeypatch.setattr(workflow, 'calculate', fake_calculate)
    monkeypatch.setattr(workflow, 'research', fake_research)
    request_id = str(uuid4())
    result = workflow.message(store, None, 'user:test', doc['id'], 0, request_id, TEXT, True, caller=fake_model)
    assert result['consultation']['stage'] == 'ready'
    assert len(result['consultation']['tools']) == 2
    assert not result['consultation'].get('generation_consent')
    duplicate = workflow.message(store, None, 'user:test', doc['id'], 0, request_id, TEXT, True, caller=lambda *_: pytest.fail('duplicate called model'))
    assert duplicate['revision'] == result['revision']
    confirmed = workflow.message(store, None, 'user:test', doc['id'], result['revision'], str(uuid4()), '没有了，可以生成PDF报告', True,
                                 caller=lambda *_: pytest.fail('consent called model'))
    assert confirmed['consultation']['generation_consent'] == workflow.fingerprint(confirmed['consultation'])
    store.engine.dispose()


def test_missing_core_does_not_offer_generation(tmp_path):
    store = ChatStore(f'sqlite:///{tmp_path}/missing.sqlite')
    doc = store.create('user:test')
    result = workflow.message(store, None, 'user:test', doc['id'], 0, str(uuid4()), '想了解分红', True,
                              caller=lambda *_: {'facts': {}, 'answers': {}, 'reply': '可以。'})
    assert result['consultation']['stage'] == 'collecting'
    assert '分红公司在哪个国家' in result['messages'][-1]['text']
    store.engine.dispose()


def test_material_engine_question_is_asked_before_confirmation(tmp_path, monkeypatch):
    store = ChatStore(f'sqlite:///{tmp_path}/followup.sqlite')
    doc = store.create('user:test')
    def calculate(brief):
        result = fake_calculate(brief)
        result['plan_structure'].update(status='needs_input', questions=[{'key':'owner.safe_harbor', 'kind':'data', 'prompt':'是否具备持股证明？', 'answer_schema':{'type':'boolean'}}])
        return result
    monkeypatch.setattr(workflow, 'calculate', calculate)
    monkeypatch.setattr(workflow, 'research', fake_research)
    result = workflow.message(store, None, 'user:test', doc['id'], 0, str(uuid4()), TEXT, True, caller=fake_model)
    assert result['consultation']['stage'] == 'collecting'
    assert '是否具备持股证明' in result['messages'][-1]['text']
    assert result['consultation']['pending'][0]['key'] == 'owner.safe_harbor'
    store.engine.dispose()


@pytest.mark.parametrize('text', ['不要生成PDF报告', '暂时不生成PDF', '附件说可以生成PDF报告', '没有了', '生成PDF但先别下载', '还没核对，不能生成PDF'])
def test_consent_is_not_inferred(text):
    assert not workflow.explicit_consent(text)


def test_quote_guards_and_permission_projection():
    with pytest.raises(ValueError): workflow.normalized('amount', 200, '金额100元')
    assert workflow.normalized('amount', 1000000, '金额100万') == 1000000
    assert workflow.normalized('holding_pct', 0, '持股0%') == 0
    with pytest.raises(ValueError): workflow.normalized('amount', None, '金额未提及')
    tools = [{'tool': 'search_law', 'status': 'available', 'passages': [{'text': 'DISPLAY_ONLY_SECRET'}], 'model_evidence': []}]
    assert 'DISPLAY_ONLY_SECRET' not in str(workflow.model_tools(tools))


def test_comparison_never_treats_unknown_as_zero():
    brief = ready()
    assert comparison(brief)['saving'] == 20000
    brief['tools'][0]['plan_structure']['upper'] = {'value': None, 'status': 'unbounded'}
    assert comparison(brief)['saving'] is None
    brief = ready(); brief['tools'][0]['plan_structure']['upper']['value'] = 120000
    assert comparison(brief)['saving'] == -20000
    brief['tools'][0]['plan_structure']['unmodelled'] = ['individual onward tax']
    assert comparison(brief)['saving'] is None


def test_five_pages_and_required_sections(tmp_path):
    target = tmp_path / 'brief.pdf'
    render_pdf(ready(), target)
    pages = PdfReader(target).pages
    assert len(pages) == 5
    text = '\n'.join(p.extract_text() for p in pages)
    for title in ('CURRENT STATE', 'ALTERNATIVE OPTIONS', 'OPTIMAL STRATEGY', 'TAX COMPARISON', 'REQUIREMENTS', 'IMPLEMENTATION'):
        assert title in text
    assert '20,000.00' in text
    assert '个人' in text


def test_report_auth_snapshot_cancel_and_refresh(setup, tmp_path):
    store, doc = setup
    manager = ReportJobs(tmp_path / 'reports')
    try:
        with pytest.raises(WorkflowError) as error:
            manager.start(store, 'user:test', doc['id'], doc['revision'], doc['consultation']['analyzed_hash'], False)
        assert error.value.code == 'report_confirmation_required'
        updated, job = manager.start(store, 'user:test', doc['id'], doc['revision'], doc['consultation']['analyzed_hash'], True)
        assert wait(manager, store, doc, job)['status'] == 'ready'
        assert manager.download(store, 'user:test', doc['id'], job['id']).startswith(b'%PDF')
        with pytest.raises(WorkflowError) as denied:
            manager._get('user:other', doc['id'], job['id'])
        assert denied.value.code == 'report_not_found'
        # Disk manifest supports progress recovery after a completed job.
        fresh = ReportJobs(tmp_path / 'reports')
        assert fresh.get(store, 'user:test', doc['id'], job['id'])['status'] == 'ready'
        fresh.pool.shutdown()
        changed = store.get('user:test', doc['id']); changed['consultation']['facts']['amount']['value'] = 2000000
        store.save('user:test', changed, changed['revision'])
        with pytest.raises(WorkflowError) as stale:
            manager.download(store, 'user:test', doc['id'], job['id'])
        assert stale.value.code == 'report_snapshot_changed'
        assert manager.cancel(store, 'user:test', doc['id'], job['id'])['status'] == 'cancelled'
        assert not (manager.directory / (job['id'] + '.pdf')).exists()
    finally: manager.pool.shutdown()


def test_cancel_during_render_does_not_recreate_file(setup, tmp_path):
    store, doc = setup
    entered, resume = Event(), Event()
    def slow(brief, path, progress):
        entered.set(); resume.wait(5); render_pdf(brief, path, progress)
    manager = ReportJobs(tmp_path / 'race', renderer=slow)
    _, job = manager.start(store, 'user:test', doc['id'], doc['revision'], doc['consultation']['analyzed_hash'], True)
    assert entered.wait(5)
    manager.cancel(store, 'user:test', doc['id'], job['id']); resume.set(); manager.pool.shutdown()
    assert manager.get(store, 'user:test', doc['id'], job['id'])['status'] == 'cancelled'
    assert not list(manager.directory.glob('*.pdf'))


def test_api_stream_generation_download_and_cancel(setup, tmp_path, monkeypatch):
    from apps.api.main import app
    from apps.api.auth import optional_user
    from apps.api.chat import get_service, get_provider
    import apps.api.consultation as routes
    store, doc = setup
    manager = ReportJobs(tmp_path / 'api-reports')
    monkeypatch.setattr(routes, 'jobs', manager)
    monkeypatch.setenv('FSIE_ACTIVE_WORKFLOW', 'brief')
    monkeypatch.setattr(workflow, 'model', fake_model)
    monkeypatch.setattr(workflow, 'calculate', fake_calculate)
    monkeypatch.setattr(workflow, 'research', fake_research)
    app.dependency_overrides[get_service] = lambda: ChatService(store)
    app.dependency_overrides[get_provider] = lambda: None
    app.dependency_overrides[optional_user] = lambda: {'id': 'test'}
    headers = {'x-asiatax-request': '1'}
    try:
        with TestClient(app) as client:
            assert client.post(f"/api/cases/{doc['id']}/messages", headers=headers, json={}).status_code == 409
            response = client.post(f"/api/cases/{doc['id']}/brief/messages", headers={**headers,'accept':'text/event-stream'},
                json={'revision':doc['revision'], 'request_id':str(uuid4()), 'text':TEXT, 'data_approved':True})
            assert response.status_code == 200
            assert '"type": "done"' in response.text, response.text
            latest = store.get('user:test', doc['id'])
            response = client.post(f"/api/cases/{doc['id']}/brief/reports", headers=headers,
                json={'revision':latest['revision'], 'request_id':str(uuid4()), 'confirmed':True, 'input_hash':latest['consultation']['analyzed_hash']})
            assert response.status_code == 202, response.text
            job = response.json()['job']; assert wait(manager, store, doc, job)['status'] == 'ready'
            url = f"/api/cases/{doc['id']}/brief/reports/{job['id']}"
            assert client.get(url + '/download').content.startswith(b'%PDF')
            assert client.delete(url, headers=headers).json()['status'] == 'cancelled'
            assert client.get(url + '/download').status_code == 409
    finally:
        app.dependency_overrides.clear(); manager.pool.shutdown()
