from types import SimpleNamespace

import pytest

from packages.chat import library_cloud
from packages.persistence.config import Settings


def test_reader_url_is_normalized_separately_from_writer():
    config = Settings(_env_file=None, database_url='postgresql://writer@host/db',
        library_database_url='postgresql://reader@host/db')
    assert config.database_url == 'postgresql+psycopg://writer@host/db'
    assert config.library_database_url == 'postgresql+psycopg://reader@host/db'


def test_missing_reader_never_falls_back_to_writer(monkeypatch):
    library_cloud._engine.cache_clear()
    monkeypatch.setattr(library_cloud, 'get_settings', lambda: SimpleNamespace(
        database_url='postgresql://writer@host/db', library_database_url=''))
    monkeypatch.setattr(library_cloud, 'create_engine', lambda *a, **k: pytest.fail('Writer connection attempted'))
    with pytest.raises(ValueError, match='FSIE_LIBRARY_DATABASE_URL'):
        library_cloud._engine()


def test_library_engine_uses_reader_only_with_bounded_pool_and_timeout(monkeypatch):
    library_cloud._engine.cache_clear()
    monkeypatch.setattr(library_cloud, 'get_settings', lambda: SimpleNamespace(
        database_url='postgresql://writer@host/db', library_database_url='postgresql://reader@host/db'))
    seen = []
    def create(url, **kwargs):
        seen.append((url, kwargs))
        return object()
    monkeypatch.setattr(library_cloud, 'create_engine', create)
    try:
        first = library_cloud._engine()
        assert library_cloud._engine() is first
        assert seen[0][0] == 'postgresql://reader@host/db'
        assert seen[0][1]['max_overflow'] == 0
        assert seen[0][1]['connect_args']['connect_timeout'] == 3
    finally:
        library_cloud._engine.cache_clear()
