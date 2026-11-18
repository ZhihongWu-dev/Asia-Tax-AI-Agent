import csv
import importlib.util
import io
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize('mode', ['notes', 'full', 'dry'])
def test_notes_survive_upload_without_notes_mode_replacing_catalog(tmp_path, monkeypatch, mode):
    path = Path(__file__).resolve().parents[2] / 'database/tools/upload.py'
    spec = importlib.util.spec_from_file_location('tested_notes_upload', path)
    upload = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(upload)
    for name in upload.NOTES:
        (tmp_path / name).write_text('notes', encoding='utf-8')
    monkeypatch.setattr(upload, 'ROOT', tmp_path)
    monkeypatch.setattr(upload.build, 'ROOT', tmp_path)
    monkeypatch.setattr(upload.fetch, 'ROOT', tmp_path)
    monkeypatch.setattr(upload.subprocess, 'run', lambda *a, **k: None)
    monkeypatch.setattr(upload, 'accepted', lambda *a: (True, 'accepted cn'))
    monkeypatch.setattr(upload, 'plan_rows', lambda *a: ({'doc': {}}, []))
    monkeypatch.setattr(upload, 'tools_meta', lambda *a: {})
    monkeypatch.setattr(upload.build, 'read_csv', lambda p: [{'code': 'cn'}] if p.name == 'jurisdiction.csv' else [])
    monkeypatch.setattr(upload.fetch, 'secret', lambda *a: 'test-only')
    monkeypatch.setattr(upload, 'remote_meta', lambda *a: {})
    writes, deletes, replacements = {}, [], []

    class Connection:
        def commit(self): pass
        def close(self): pass
        def cursor(self): return self
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, *a):
            assert mode == 'full', 'notes-only must not inspect or delete other objects'
        def fetchall(self):
            return [(n,) for n in ('blocked.csv', 'STATUS.md', 'session_log.md', 'stale.txt')]

    class Bucket:
        def __init__(self, *a): pass
        def ensure(self): pass
        def put(self, name, data, *a): writes[name] = data
        def delete(self, names): deletes.extend(names)

    monkeypatch.setitem(sys.modules, 'psycopg', SimpleNamespace(connect=lambda *a, **k: Connection()))
    monkeypatch.setattr(upload, 'Bucket', Bucket)
    monkeypatch.setattr(upload, 'replace_tables', lambda *a: replacements.append(True))
    args = ['upload.py'] + (['--notes-only'] if mode != 'full' else [])
    if mode == 'dry': args.append('--dry-run')
    monkeypatch.setattr(sys, 'argv', args)
    assert upload.main() == 0
    if mode == 'dry':
        assert not writes and not deletes and not replacements
    else:
        reader = csv.DictReader(io.StringIO(writes['blocked.csv'].decode('utf-8-sig')))
        assert set(reader.fieldnames) == {'id', 'jur', 'title', 'url', 'reason', 'alt_tried', 'logged_at'}
        assert list(reader) == []
        assert all(name in writes for name in upload.NOTES)
        assert deletes == (['stale.txt'] if mode == 'full' else [])
        assert replacements == ([True] if mode == 'full' else [])
