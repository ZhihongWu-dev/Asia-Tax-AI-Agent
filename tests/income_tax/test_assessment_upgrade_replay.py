from copy import deepcopy
from hashlib import sha256
import json
import pytest
from packages.chat.income_tax import assessment_run, save_case
from packages.chat.store import ChatStore, CaseNotFound
from packages.chat.service import WorkflowError
from packages.contracts.income_tax import IncomeTaxCase
from tests.income_tax.test_assessment_workflow import ADAPTER, COMPANY, facts


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


@pytest.fixture
def historical_run(tmp_path):
    url = 'sqlite:///' + str(tmp_path/'cases.sqlite')
    store = ChatStore(url)
    case_id = store.create('alice')['id']
    save_case(store, 'alice', case_id, 0, 'facts', IncomeTaxCase(**facts()))
    run = assessment_run(store, 'alice', case_id, 1, 'calculate', ADAPTER.validate_python(COMPANY))
    # Persist the pre-upgrade representation, before two default fields existed.
    for key in ('non_taxable_income', 'exempt_income'):
        del run['basis'][key]
    run['result'].pop('basis_reconciliation')
    run['result']['policy_version'] = 'cn-2026-2026-11-16'
    run['request_hash'] = digest(dict(revision=1, basis=run['basis']))
    run['snapshot_hash'] = digest({k: run[k] for k in ('inputs', 'basis', 'result')})
    doc = store.get('alice', case_id)
    doc['income_tax_runs'] = [deepcopy(run)]
    doc['income_tax_result'] = deepcopy(run)
    store.save('alice', doc, 2)
    # An intervening edit must not prevent replay, or restore an obsolete result.
    changed = facts()
    changed['incomes'][0]['gross_amount'] = '2000000'
    save_case(store, 'alice', case_id, 3, 'edit', IncomeTaxCase(**changed))
    store.engine.dispose()
    reopened = ChatStore(url)
    yield reopened, case_id, run
    reopened.engine.dispose()


@pytest.mark.parametrize('explicit_defaults', [False, True])
def test_upgrade_replay_returns_exact_historical_result_without_recalculation(historical_run, monkeypatch, explicit_defaults):
    store, case_id, run = historical_run
    before = store.get('alice', case_id)
    basis = dict(COMPANY)
    if explicit_defaults:
        basis.update(non_taxable_income='0', exempt_income='0')
    def unexpected(*args, **kwargs):
        pytest.fail('Historical replay must not recalculate')
    monkeypatch.setattr('packages.income_tax.assessment.calculate', unexpected)
    assert assessment_run(store, 'alice', case_id, 1, 'calculate', ADAPTER.validate_python(basis)) == run
    assert store.get('alice', case_id) == before
    assert before.get('income_tax_result') is None


@pytest.mark.parametrize('change,revision', [({'non_taxable_income':'1'},1),
    ({'taxable_income':'2000000'},1), ({},4)])
def test_changed_request_still_conflicts_after_upgrade(historical_run, change, revision):
    store, case_id, _ = historical_run
    before = store.get('alice', case_id)
    with pytest.raises(WorkflowError, match='request_payload_conflict'):
        assessment_run(store, 'alice', case_id, revision, 'calculate', ADAPTER.validate_python({**COMPANY, **change}))
    assert store.get('alice', case_id) == before


def test_historical_replay_keeps_owner_boundary(historical_run):
    store, case_id, _ = historical_run
    with pytest.raises(CaseNotFound):
        assessment_run(store, 'bob', case_id, 1, 'calculate', ADAPTER.validate_python(COMPANY))


def test_compatibility_does_not_ignore_inconsistent_saved_request_hash(historical_run):
    store, case_id, _ = historical_run
    doc = store.get('alice', case_id)
    doc['income_tax_runs'][0]['request_hash'] = '0'*64
    store.save('alice', doc, doc['revision'])
    with pytest.raises(WorkflowError, match='request_payload_conflict'):
        assessment_run(store, 'alice', case_id, 1, 'calculate', ADAPTER.validate_python(COMPANY))

@pytest.mark.parametrize('explicit_transfers',[False,True])
@pytest.mark.parametrize('explicit_rentals',[False,True])
def test_personal_foreign_old_snapshot_replays_without_new_transfer_defaults_or_recalculation(tmp_path,monkeypatch,explicit_transfers,explicit_rentals):
    from tests.income_tax.test_china_personal_foreign_assessment import facts as personal_facts, basis as personal_basis
    from packages.reporting.income_tax import render
    url='sqlite:///'+str(tmp_path/'personal.sqlite')
    store=ChatStore(url);case_id=store.create('alice')['id']
    save_case(store,'alice',case_id,0,'facts',IncomeTaxCase(**personal_facts()))
    paper=personal_basis()
    saved=assessment_run(store,'alice',case_id,1,'calculate',ADAPTER.validate_python(paper))
    # Simulate the historical shape: neither optional category workpaper exists.
    saved['basis']['workpaper'].pop('transfers')
    saved['basis']['workpaper'].pop('rentals')
    for row in saved['result']['country_basis_reconciliation']:
        row.pop('rental_tax')
    saved['result'].pop('arithmetic')
    saved['result']['policy_version']='cn-personal-foreign-credit-limits-2026-11-19'
    saved['result']['allowed_credit']='3092.00'
    saved['request_hash']=digest(dict(revision=1,basis=saved['basis']))
    saved['snapshot_hash']=digest({k:saved[k] for k in ('inputs','basis','result')})
    doc=store.get('alice',case_id);doc['income_tax_runs']=[deepcopy(saved)];doc['income_tax_result']=deepcopy(saved)
    store.save('alice',doc,2)
    old_report=render(saved,'en')
    changed=personal_facts();changed['incomes'][0]['gross_amount']='2000000'
    save_case(store,'alice',case_id,3,'edit',IncomeTaxCase(**changed))
    store.engine.dispose();store=ChatStore(url)
    try:
        before=store.get('alice',case_id)
        if explicit_transfers:paper['workpaper']['transfers']=[]
        if explicit_rentals:paper['workpaper']['rentals']=[]
        def unexpected(*args,**kwargs):pytest.fail('Historical personal result must not recalculate')
        monkeypatch.setattr('packages.income_tax.assessment.calculate',unexpected)
        replay=assessment_run(store,'alice',case_id,1,'calculate',ADAPTER.validate_python(paper))
        assert replay==saved and render(replay,'en')==old_report
        assert store.get('alice',case_id)==before and before.get('income_tax_result') is None
        with pytest.raises(CaseNotFound):assessment_run(store,'bob',case_id,1,'calculate',ADAPTER.validate_python(paper))
        paper['workpaper']['comprehensive_deductions']='1'
        with pytest.raises(WorkflowError,match='request_payload_conflict'):
            assessment_run(store,'alice',case_id,1,'calculate',ADAPTER.validate_python(paper))
    finally:store.engine.dispose()


@pytest.mark.parametrize('with_tokyo', [False, True])
@pytest.mark.parametrize('explicit_osaka_default', [False, True])
def test_japan_pre_osaka_snapshot_replay_preserves_original(tmp_path, monkeypatch, with_tokyo, explicit_osaka_default):
    from tests.income_tax.test_japan_tokyo import facts as jp_facts, basis as jp_basis
    from tests.income_tax.test_japan_osaka_assessment import basis as osaka_basis
    from packages.reporting.income_tax import render
    url = 'sqlite:///' + str(tmp_path/'japan.sqlite')
    store = ChatStore(url); case_id = store.create('alice')['id']
    paper = jp_basis()
    if not with_tokyo: paper.pop('tokyo_local')
    save_case(store, 'alice', case_id, 0, 'facts', IncomeTaxCase(**jp_facts()))
    saved = assessment_run(store, 'alice', case_id, 1, 'calculate', ADAPTER.validate_python(paper))
    saved['basis'].pop('osaka_local')
    saved['request_hash'] = digest(dict(revision=1, basis=saved['basis']))
    saved['snapshot_hash'] = digest({k: saved[k] for k in ('inputs', 'basis', 'result')})
    doc = store.get('alice', case_id)
    doc['income_tax_runs'] = [deepcopy(saved)]; doc['income_tax_result'] = deepcopy(saved)
    store.save('alice', doc, 2)
    reports = {locale: render(saved, locale) for locale in ('zh', 'en')}
    changed = jp_facts(); changed['incomes'][0]['gross_amount'] = '20000000'
    save_case(store, 'alice', case_id, 3, 'edit', IncomeTaxCase(**changed))
    store.engine.dispose(); store = ChatStore(url)
    try:
        before = store.get('alice', case_id)
        if explicit_osaka_default: paper['osaka_local'] = None
        def unexpected(*args, **kwargs): pytest.fail('Historical Japanese assessment must not recalculate')
        monkeypatch.setattr('packages.income_tax.assessment.calculate', unexpected)
        replay = assessment_run(store, 'alice', case_id, 1, 'calculate', ADAPTER.validate_python(paper))
        assert replay == saved
        for locale in reports: assert render(replay, locale) == reports[locale]
        assert store.get('alice', case_id) == before and before.get('income_tax_result') is None
        with pytest.raises(CaseNotFound):
            assessment_run(store, 'bob', case_id, 1, 'calculate', ADAPTER.validate_python(paper))
        # A new local workpaper is a substantive request change, never a default.
        changed_paper = osaka_basis()
        with pytest.raises(WorkflowError, match='request_payload_conflict'):
            assessment_run(store, 'alice', case_id, 1, 'calculate', ADAPTER.validate_python(changed_paper))
        assert store.get('alice', case_id) == before
    finally:
        store.engine.dispose()
