from copy import deepcopy
import os

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import OperationalError
from sqlalchemy.engine import make_url

from scripts.catalog_executor import execute_reviewed_plan
from scripts.catalog_migration import digest


@pytest.fixture(params=['sqlite', pytest.param('postgresql', marks=pytest.mark.integration)])
def catalog(tmp_path, request):
    postgres = request.param == 'postgresql'
    if postgres:
        url = os.environ.get('CATALOG_EXECUTOR_TEST_DATABASE_URL')
        if not url:
            pytest.skip('Dedicated PostgreSQL catalog test database is not configured')
        parsed = make_url(url)
        if (parsed.get_backend_name() != 'postgresql' or parsed.host not in ('localhost','127.0.0.1')
                or parsed.database != 'catalog_executor_test'):
            pytest.fail('Catalog tests require a dedicated local catalog_executor_test database')
        engine = create_engine(url)
    else:
        engine = create_engine('sqlite://')
        @event.listens_for(engine, 'connect')
        def attach(connection, _):
            connection.execute('ATTACH DATABASE ? AS database', (str(tmp_path/'catalog.sqlite'),))
    with engine.begin() as connection:
        if postgres:
            # No IF NOT EXISTS: never reuse or clear an existing catalog schema.
            connection.exec_driver_sql('CREATE SCHEMA database')
            connection.exec_driver_sql('CREATE SCHEMA database_integration')
            for name in ('param','decision','clause'):
                connection.exec_driver_sql(f'CREATE TABLE database.{name} (id TEXT PRIMARY KEY)')
            connection.exec_driver_sql('CREATE TABLE database_integration.source_review (id TEXT PRIMARY KEY)')
        connection.exec_driver_sql('CREATE TABLE database.meta (key TEXT PRIMARY KEY, value TEXT)')
        connection.exec_driver_sql('CREATE TABLE database.doc (id TEXT PRIMARY KEY, title TEXT NOT NULL)')
        connection.exec_driver_sql("INSERT INTO database.meta VALUES ('uploaded_at', 'upload'), ('unrelated', 'preserve')")
        connection.exec_driver_sql("INSERT INTO database.doc VALUES ('law', 'old'), ('other', 'untouched')")
    ops = [dict(table='doc',key_column='id',key='law',operation='update',
        expected_before={'id':'law','title':'old'},after={'id':'law','title':'new'}),
        dict(table='doc',key_column='id',key='inserted',operation='insert',
        expected_before=None,after={'id':'inserted','title':'new source'})]
    plan = dict(operations=ops,operation_count=2,proposed_catalog_revision=digest(ops),base_uploaded_at='upload')
    try:
        yield engine, plan
    finally:
        if postgres:
            with engine.begin() as connection:
                connection.exec_driver_sql('DROP SCHEMA database CASCADE')
                connection.exec_driver_sql('DROP SCHEMA database_integration CASCADE')
        engine.dispose()


def snapshot(engine):
    with engine.connect() as connection:
        return {name: connection.exec_driver_sql(f'SELECT * FROM database.{name} ORDER BY 1').all()
                for name in ('doc','meta')}


def test_commits_rows_and_revision_together(catalog):
    engine, plan = catalog
    original = deepcopy(plan)
    def after(connection):
        assert connection.exec_driver_sql("SELECT title FROM database.doc WHERE id='law'").scalar() == 'new'
        assert connection.exec_driver_sql("SELECT value FROM database.meta WHERE key='catalog_revision'").scalar() == plan['proposed_catalog_revision']
        return True
    result = execute_reviewed_plan(engine,plan,expected_catalog_revision=None,
        validate_before=lambda c: True,validate_after=after)
    assert result['status'] == 'committed'
    assert plan == original
    data = snapshot(engine)
    assert ('other','untouched') in data['doc']
    assert ('uploaded_at','upload') in data['meta']
    assert ('unrelated','preserve') in data['meta']


@pytest.mark.parametrize('failure', ['stale_row','stale_revision','preflight','constraint','postflight'])
def test_any_failure_leaves_all_rows_and_revision_unchanged(catalog, failure):
    engine, plan = catalog
    before = snapshot(engine)
    if failure == 'stale_row': plan['operations'][0]['expected_before']['title']='wrong'
    if failure == 'constraint': plan['operations'][1]['after']['title']=None
    plan['proposed_catalog_revision']=digest(plan['operations'])
    with pytest.raises((ValueError, IntegrityError)):
        execute_reviewed_plan(engine,plan,
            expected_catalog_revision='wrong' if failure=='stale_revision' else None,
            validate_before=lambda c: failure!='preflight',
            validate_after=lambda c: failure!='postflight')
    assert snapshot(engine) == before


def test_postgres_excludes_concurrent_catalog_writer(catalog):
    engine, plan = catalog
    if engine.dialect.name != 'postgresql':
        pytest.skip('PostgreSQL lock semantics require PostgreSQL')
    def before(connection):
        with pytest.raises(OperationalError) as error:
            with engine.begin() as competing:
                competing.exec_driver_sql("SET LOCAL lock_timeout = '100ms'")
                competing.exec_driver_sql("UPDATE database.doc SET title='concurrent' WHERE id='law'")
        assert error.value.orig.sqlstate == '55P03'
        return True
    result = execute_reviewed_plan(engine,plan,expected_catalog_revision=None,
        validate_before=before,validate_after=lambda c: True)
    assert result['status'] == 'committed'


@pytest.mark.parametrize('missing_dependency', [False, True])
def test_postgres_source_validation_reads_uncommitted_changes_without_committing(catalog, missing_dependency):
    from packages.chat.library_cloud import _read_library_state
    from packages.domain_bridge.planning_sources import (
        PlanningSourcesUnavailable, read_planning_bundle_in_transaction)
    engine, _ = catalog
    if engine.dialect.name != 'postgresql':
        pytest.skip('Uncommitted source validation requires PostgreSQL')
    with engine.begin() as connection:
        connection.exec_driver_sql('ALTER TABLE database_integration.source_review RENAME COLUMN id TO cite_id')
        connection.exec_driver_sql('ALTER TABLE database.clause RENAME COLUMN id TO cite_id')
        for name in ('doc_id', 'label', 'text'):
            connection.exec_driver_sql(f'ALTER TABLE database.clause ADD COLUMN {name} TEXT')
        for name in ('url', 'sha256', 'lang', 'jur', 'effective_from', 'effective_to'):
            connection.exec_driver_sql(f'ALTER TABLE database.doc ADD COLUMN {name} TEXT')
        connection.exec_driver_sql('ALTER TABLE database.param RENAME COLUMN id TO param_id')
        connection.exec_driver_sql('ALTER TABLE database.param ADD COLUMN cite_id TEXT')
        connection.exec_driver_sql('CREATE TABLE database.jurisdiction (code TEXT PRIMARY KEY)')
        connection.exec_driver_sql('CREATE TABLE database.treaty (pair TEXT PRIMARY KEY)')
    class RollbackProbe(Exception):
        pass
    expected_error = PlanningSourcesUnavailable if missing_dependency else RollbackProbe
    with pytest.raises(expected_error):
        with engine.connect().execution_options(isolation_level='SERIALIZABLE') as connection:
            with connection.begin():
                connection.exec_driver_sql("INSERT INTO database.clause VALUES ('cn.law#1','law','Article 1','Uncommitted complete source')")
                if missing_dependency:
                    connection.exec_driver_sql("INSERT INTO database.param VALUES ('rate','cn.missing#2')")
                version, _, _ = _read_library_state(connection)
                bundle = read_planning_bundle_in_transaction(connection, ['cn.law#1'], expected_version=version)
                assert bundle['sources']['cn.law#1']['passage'] == 'Uncommitted complete source'
                assert connection.in_transaction()
                # Another connection cannot see the uncommitted source.
                with engine.connect() as observer:
                    assert observer.exec_driver_sql('SELECT count(*) FROM database.clause').scalar() == 0
                raise RollbackProbe()
    with engine.connect() as connection:
        assert connection.exec_driver_sql('SELECT count(*) FROM database.clause').scalar() == 0
        assert connection.exec_driver_sql('SELECT count(*) FROM database.param').scalar() == 0
