import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('collection_dbsource',
    Path(__file__).resolve().parents[2] / 'database/tools/dbsource.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
HEADER = b'id,jur,title,url,reason,alt_tried,logged_at\n'


def test_notes_only_changes_are_visible_without_upload_stamp(monkeypatch):
    remote = module.Remote()
    body = [HEADER + b'example,sg,Title,https://example.com,timeout,,2026-11-18\n']
    monkeypatch.setattr(remote, 'object', lambda name: body[0])
    first = remote.rows('blocked')
    assert first[0]['reason'] == 'timeout'
    first[0]['reason'] = 'changed locally'
    body[0] = HEADER + b'example,sg,Title,https://example.com,unavailable,,2026-11-18\n'
    assert remote.rows('blocked')[0]['reason'] == 'unavailable'
    assert 'blocked' not in remote.tables
    body[0] = HEADER
    assert remote.rows('blocked') == []


def test_unavailable_log_does_not_become_empty(monkeypatch):
    remote = module.Remote()
    def unavailable(name):
        raise RuntimeError('bucket unavailable')
    monkeypatch.setattr(remote, 'object', unavailable)
    with pytest.raises(RuntimeError):
        remote.rows('blocked')


@pytest.mark.parametrize('body', [b'', b'<html>error</html>', HEADER+b'x,sg\n',
                                  HEADER+b',sg,title,url,reason,,date\n',
                                  HEADER+b'x,sg,title,url,reason,,date,extra\n'])
def test_malformed_log_fails_instead_of_returning_partial_rows(monkeypatch, body):
    remote = module.Remote()
    monkeypatch.setattr(remote, 'object', lambda name: body)
    with pytest.raises(ValueError):
        remote.rows('blocked')


def test_mcp_refreshes_log_and_scopes_failure_to_log_query(monkeypatch):
    from types import SimpleNamespace
    mcp_spec = importlib.util.spec_from_file_location('collection_mcp',
        Path(__file__).resolve().parents[2] / 'database/tools/mcp_server.py')
    server = importlib.util.module_from_spec(mcp_spec)
    mcp_spec.loader.exec_module(server)
    body = [{'id': 'first'}]
    calls = []
    def rows(name):
        calls.append(name)
        return body if name == 'blocked' else []
    remote = SimpleNamespace(rows=rows, status=lambda: {'counts': {}},
        digest=lambda name: 'fixture', version=lambda: {}, count=lambda name: 0,
        clauses=lambda: [])
    monkeypatch.setattr(server.dbsource, 'online', lambda root: True)
    monkeypatch.setattr(server.dbsource, 'remote', lambda: remote)
    library = server.Library('supabase')
    assert 'blocked' not in calls
    assert library.ready.wait(2)
    library.stamp = lambda data: data
    assert library.blocked_docs()['blocked'] == [{'id': 'first'}]
    body[:] = [{'id': 'new-attempt'}]
    assert library.blocked_docs()['blocked'] == [{'id': 'new-attempt'}]
    def unavailable(name):
        raise RuntimeError('private storage details')
    library.remote.rows = unavailable
    assert library.blocked_docs() == {'error': 'collection_log_unavailable',
                                     'detail': 'The collection-failure log could not be read.'}
    library.remote = None
    library._blocked = [{'id': 'local'}]
    assert library.blocked_docs()['blocked'] == [{'id': 'local'}]
