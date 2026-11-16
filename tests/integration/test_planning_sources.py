from contextlib import nullcontext
from hashlib import sha256
from types import SimpleNamespace

import pytest

from packages.domain_bridge import planning_sources as sources


PIN = {'uploaded_at': 'pinned', 'review_sha256': 'review'}


def fixture_reader(monkeypatch, *, rows=(), reviews=(), overlay=()):
    statements = []
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def begin(self): return nullcontext()
        def execute(self, statement, params=None):
            statements.append((str(statement), params))
            return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: rows))
    monkeypatch.setattr(sources.library_cloud, '_engine',
                        lambda: SimpleNamespace(connect=Connection))
    def state(connection, expected):
        assert expected == PIN
        assert statements[0][0] == 'SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'
        return dict(PIN), reviews, overlay
    monkeypatch.setattr(sources.library_cloud, '_read_library_state', state)
    return statements


def test_complete_base_and_overlay_passages_and_hashes(monkeypatch):
    body = '完整法条' * 2000
    overlay_body = 'overlay full text' * 1000
    statements = fixture_reader(monkeypatch,
        rows=[{'cite_id': 'cn.law#1', 'passage': body, 'document_sha256': 'original'}],
        overlay=[{'cite_id': 'cn.other#2', 'passage': overlay_body[:5000],
                  '_search_text': overlay_body, 'origin': 'reviewed_main_overlay'}])
    result = sources.read_sources(['cn.other#2', 'cn.law#1', 'cn.law#1'], expected_version=PIN)
    assert result['library_version'] == PIN
    assert result['sources']['cn.law#1']['passage'] == body
    assert result['sources']['cn.law#1']['document_sha256'] == 'original'
    assert result['sources']['cn.other#2']['passage'] == overlay_body
    assert result['sources']['cn.other#2']['passage_sha256'] == sha256(overlay_body.encode()).hexdigest()
    assert '_search_text' not in result['sources']['cn.other#2']
    assert statements[-1][1] == {'ids': ['cn.law#1', 'cn.other#2']}
    assert 'left(' not in statements[-1][0].lower()


@pytest.mark.parametrize('difference,status,reviewed', [
    ('different_text', 'candidate', None), ('different_text', 'accepted', 'date'),
    ('different_text', 'rejected', None), ('main_only', 'candidate', None)])
def test_blocked_dependency_stops_before_reading_text(monkeypatch, difference, status, reviewed):
    statements = fixture_reader(monkeypatch, reviews=[dict(cite_id='cn.law#1',
        difference=difference, review_status=status, reviewed_at=reviewed)])
    with pytest.raises(sources.PlanningSourcesUnavailable) as exc:
        sources.read_sources(['cn.law#1'], expected_version=PIN)
    assert exc.value.blocked == ('cn.law#1',)
    assert len(statements) == 1


def test_missing_dependency_never_returns_partial_success(monkeypatch):
    fixture_reader(monkeypatch, rows=[{'cite_id': 'cn.law#1', 'passage': 'text'}])
    with pytest.raises(sources.PlanningSourcesUnavailable) as exc:
        sources.read_sources(['cn.law#1', 'cn.missing#2'], expected_version=PIN)
    assert exc.value.missing == ('cn.missing#2',)


def test_changed_pin_prevents_source_read(monkeypatch):
    statements = fixture_reader(monkeypatch)
    def changed(*args): raise sources.library_cloud.LibraryVersionChanged()
    monkeypatch.setattr(sources.library_cloud, '_read_library_state', changed)
    with pytest.raises(sources.library_cloud.LibraryVersionChanged):
        sources.read_sources(['cn.law#1'], expected_version=PIN)
    assert len(statements) == 1


@pytest.mark.parametrize('citations,pin', [([], PIN), (['bad'], PIN),
    (['cn.law#1'] * 1001, PIN), (['cn.law#1'], {}), (['cn.law#1'], None)])
def test_invalid_request_never_accesses_database(monkeypatch, citations, pin):
    monkeypatch.setattr(sources.library_cloud, '_engine', lambda: pytest.fail('unexpected DB'))
    with pytest.raises(ValueError): sources.read_sources(citations, expected_version=pin)
