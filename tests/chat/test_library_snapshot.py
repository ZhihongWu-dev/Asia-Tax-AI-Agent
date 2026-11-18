from contextlib import nullcontext
from types import SimpleNamespace
from hashlib import sha256
import json
import pytest
from packages.chat import library_cloud, library_research
from packages.chat.library_overlay import candidate_digest
from packages.chat.service import WorkflowError

VERSION = {'uploaded_at':'2026-11-13T03:39:52Z','spec_version':'2026-11-10','tools_commit':'release'}
REVIEW = dict(cite_id='cn.test#1',difference='different_text',review_status='candidate',
              base_uploaded_at=VERSION['uploaded_at'],reviewed_at=None)


def test_search_replacement_checks_live_base_and_invalidates_old_pin(monkeypatch):
    body = 'corrected legal text'
    doc = dict(id='cn.test', title='law', url='https://example.invalid/law',
               sha256='a' * 64, lang='zh', jur='cn')
    candidate = dict(document=doc, clause=dict(cite_id='cn.test#1', doc_id='cn.test',
                     label='1', text=body), replaces=dict(uploaded_at=VERSION['uploaded_at'],
                     document_sha256='a' * 64, text_sha256=sha256(b'broken').hexdigest()))
    review = {**REVIEW, 'review_status': 'accepted', 'reviewed_at': 'date',
              'review_note': 'test only', 'source_commit': 'commit', 'doc_id': 'cn.test',
              'document_sha256': doc['sha256'], 'document_url': doc['url']}
    review['review_note'] = json.dumps(dict(reason='Test only', candidate_sha256=candidate_digest(candidate)))
    base = dict(cite_id='cn.test#1', doc_id='cn.test', text='broken', document_sha256='a' * 64)
    monkeypatch.setattr(library_cloud, 'load_candidates',
                        lambda: ('commit', {'cn.test#1': candidate}, 'bundle-hash'))
    class ReplacementConnection(Connection):
        def execute(self, statement, params=None):
            sql = str(statement)
            if 'SELECT * FROM database_integration' in sql:
                return Result([review])
            if 'FROM database.clause c JOIN' in sql:
                assert params == {'ids': ['cn.test#1']}
                return Result([base])
            return super().execute(statement, params)
    monkeypatch.setattr(library_cloud, '_engine',
                        lambda: SimpleNamespace(connect=ReplacementConnection))
    result = library_cloud.search_library('cn.test#1', 'cn')
    assert result['status'] == 'available' and result['blocked_citations'] == []
    assert len(result['passages']) == 1
    assert result['passages'][0]['passage'] == body
    assert result['passages'][0]['origin'] == 'reviewed_main_replacement'
    pin = result['library_version']
    review['review_note'] = json.dumps(dict(reason='changed decision', candidate_sha256=candidate_digest(candidate)))
    with pytest.raises(library_cloud.LibraryVersionChanged, match='library_version_changed'):
        library_cloud.search_library('cn.test#1', 'cn', expected_version=pin)
    base['text'] = 'unexpected upstream change'
    with pytest.raises(library_cloud.LibraryVersionChanged, match='overlay_replacement_base_changed'):
        library_cloud.search_library('cn.test#1', 'cn')


def test_pin_includes_review_contents_and_fails_on_base_change():
    expected = library_cloud._snapshot(VERSION,[REVIEW],None)
    assert len(expected['review_sha256'])==64
    assert library_cloud._snapshot(dict(VERSION),[dict(REVIEW)],expected)==expected
    for version, reviews in [({**VERSION,'uploaded_at':'new'},[REVIEW]),
                             (VERSION,[{**REVIEW,'review_note':'changed'}]),
                             ({},[]), (VERSION,[{**REVIEW,'base_uploaded_at':'old'}])]:
        with pytest.raises(library_cloud.LibraryVersionChanged):
            library_cloud._snapshot(version,reviews,expected)


class Result:
    def __init__(self, rows): self.rows=rows
    def mappings(self): return self
    def all(self): return self.rows


class Connection:
    def __init__(self): self.statements=[]
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def begin(self): return nullcontext()
    def execute(self, statement, params=None):
        sql=str(statement);self.statements.append((sql,params))
        if 'SELECT key, value' in sql: return Result(list(VERSION.items()))
        if 'SELECT * FROM database_integration' in sql: return Result([dict(REVIEW)])
        if 'FROM database.clause' in sql:
            # Candidate exclusion is executed in SQL, before LIMIT.
            assert 'NOT EXISTS' in sql and 'r.reviewed_at IS NOT NULL' in sql
            assert params['query']=='cn.test#1'
            return Result([])
        return Result([])


def test_conflict_is_explicit_and_transaction_is_read_only(monkeypatch):
    connection=Connection()
    monkeypatch.setattr(library_cloud,'_engine',lambda:SimpleNamespace(connect=lambda:connection))
    result=library_cloud.search_library('cn.test#1','cn')
    assert result['status']=='review_required'
    assert result['passages']==[] and result['blocked_citations']==['cn.test#1']
    assert connection.statements[0][0]=='SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'
    answer=library_research._answer('question',result,'en')
    assert answer['citations']==[] and 'unresolved' in answer['text']


@pytest.mark.parametrize('status', ['candidate', 'rejected'])
def test_main_only_source_stays_blocked_in_search(monkeypatch, status):
    review = {**REVIEW, 'difference': 'main_only', 'review_status': status,
              'reviewed_at': 'date' if status == 'rejected' else None}
    class MainOnlyConnection(Connection):
        def execute(self, statement, params=None):
            if 'SELECT * FROM database_integration' in str(statement):
                return Result([review])
            if 'FROM database.clause' in str(statement):
                # SQL excludes base fallthrough before LIMIT, including rejected imports.
                assert "r.difference = 'main_only' OR" in str(statement)
            return super().execute(statement, params)
    monkeypatch.setattr(library_cloud, '_engine', lambda: SimpleNamespace(connect=MainOnlyConnection))
    result = library_cloud.search_library('cn.test#1', 'cn')
    assert result['status'] == 'review_required'
    assert result['passages'] == [] and result['blocked_citations'] == ['cn.test#1']


def test_changed_pin_prevents_clause_query(monkeypatch):
    connection=Connection()
    monkeypatch.setattr(library_cloud,'_engine',lambda:SimpleNamespace(connect=lambda:connection))
    with pytest.raises(library_cloud.LibraryVersionChanged):
        library_cloud.search_library('cn.test#1','cn',expected_version={'uploaded_at':'old'})
    assert not any('FROM database.clause' in sql for sql,_ in connection.statements)


def test_standalone_snapshot_matches_search_and_is_fresh(monkeypatch):
    connection = Connection()
    monkeypatch.setattr(library_cloud, '_engine', lambda: SimpleNamespace(connect=lambda: connection))
    first = library_cloud.current_library_snapshot()
    assert connection.statements[0][0] == 'SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'
    assert not any('FROM database.clause' in sql for sql, _ in connection.statements)
    assert library_cloud.search_library('cn.test#1', 'cn')['library_version'] == first
    monkeypatch.setitem(VERSION, 'tools_commit', 'changed-runtime')
    assert library_cloud.current_library_snapshot() != first
    with pytest.raises(library_cloud.LibraryVersionChanged):
        library_cloud.current_library_snapshot(expected_version=first)


@pytest.mark.parametrize('pair', ['ae-jp', 'JP-AE'])
def test_treaty_pair_search_uses_canonical_bound_parameter(monkeypatch, pair):
    class TreatyConnection(Connection):
        def execute(self, statement, params=None):
            if 'FROM database.clause' in str(statement):
                self.statements.append((str(statement), params))
                assert params['jurisdiction'] == 'ae-jp'
                assert params['query'] == 'treaty.ae-jp.2013.mli.en#all'
                assert 'NOT EXISTS' in str(statement)
                return Result([])
            return super().execute(statement, params)
    connection = TreatyConnection()
    monkeypatch.setattr(library_cloud, '_engine', lambda: SimpleNamespace(connect=lambda: connection))
    result = library_cloud.search_library('treaty.ae-jp.2013.mli.en#all', pair)
    assert result['jurisdiction'] == 'ae-jp'
    assert any('FROM database.clause' in sql for sql, _ in connection.statements)


@pytest.mark.parametrize('jurisdiction', ['jp-jp', 'ae-jp-cn', 'ae--jp', 'ae-jp OR true', '中国', 'jp/ae'])
def test_invalid_treaty_pair_is_rejected_before_database(monkeypatch, jurisdiction):
    monkeypatch.setattr(library_cloud, '_engine', lambda: pytest.fail('must not access database'))
    with pytest.raises(ValueError, match='invalid_library_query'):
        library_cloud.search_library('treaty.ae-jp.2013.mli.en#all', jurisdiction)


def test_followup_keeps_pin_and_never_calls_model_after_version_change(monkeypatch):
    expected=library_cloud._snapshot(VERSION,[REVIEW],None)
    doc={'library_context':{'jurisdiction':'cn','anchor':'所得税','library_version':expected}}
    def changed(query,jurisdiction,**kwargs):
        assert kwargs['expected_version']==expected
        raise library_cloud.LibraryVersionChanged()
    monkeypatch.setattr(library_research,'search_library',changed)
    monkeypatch.setattr(library_research,'_answer',lambda *args:pytest.fail('must not generate an answer'))
    with pytest.raises(WorkflowError) as caught:
        library_research.prepare(doc,'税率','zh')
    assert caught.value.code=='knowledge_version_changed'


def test_first_research_turn_saves_the_library_pin(monkeypatch):
    snapshot=library_cloud._snapshot(VERSION,[REVIEW],None)
    research={'status':'no_matching_units','library_version':snapshot,'passages':[]}
    monkeypatch.setattr(library_research,'search_library',lambda *args,**kwargs:research)
    result=library_research.prepare({},'中国内地所得税','zh')
    assert result['library_context']['library_version']==snapshot
    assert result['workflow']['library_version']==snapshot


def test_version_failure_is_a_visible_service_error():
    from fastapi import HTTPException
    from apps.api.chat import call
    def fail(): raise WorkflowError('knowledge_version_changed')
    with pytest.raises(HTTPException) as caught: call(fail)
    assert caught.value.status_code==503
    assert caught.value.detail=='knowledge_version_changed'


def test_catalog_migration_invalidates_old_pin_without_rebinding_source_reviews(monkeypatch):
    metadata = dict(VERSION)

    class CatalogConnection(Connection):
        def execute(self, statement, params=None):
            sql = str(statement)
            if 'SELECT key, value' in sql:
                self.statements.append((sql, params))
                # Model the real WHERE IN selection: an unrequested revision
                # must not appear just because our fake metadata contains it.
                return Result([(k, v) for k, v in metadata.items() if "'" + k + "'" in sql])
            return super().execute(statement, params)

    connection = CatalogConnection()
    monkeypatch.setattr(library_cloud, '_engine', lambda: SimpleNamespace(connect=lambda: connection))
    before = library_cloud.current_library_snapshot()
    assert 'catalog_revision' not in before  # Existing unversioned upload is readable.
    metadata['catalog_revision'] = 'a' * 64
    after = library_cloud.current_library_snapshot()
    assert after['catalog_revision'] == 'a' * 64
    assert after['uploaded_at'] == before['uploaded_at'] == REVIEW['base_uploaded_at']
    assert after['review_sha256'] == before['review_sha256']
    connection.statements.clear()
    with pytest.raises(library_cloud.LibraryVersionChanged, match='library_version_changed'):
        library_cloud.search_library('cn.test#1', 'cn', expected_version=before)
    assert not any('FROM database.clause' in sql for sql, _ in connection.statements)
    assert library_cloud.current_library_snapshot(expected_version=after) == after
    metadata['catalog_revision'] = 'b' * 64
    with pytest.raises(library_cloud.LibraryVersionChanged, match='library_version_changed'):
        library_cloud.current_library_snapshot(expected_version=after)
