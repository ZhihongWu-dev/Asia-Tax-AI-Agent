"""Check durable planning storage in a unique disposable PostgreSQL schema.

Only SQLAlchemy-generated table SQL is used, mapped to the new schema.
No migrations, production table initialization, model calls or real cases.
"""
import argparse
import json
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from dotenv import dotenv_values
    from sqlalchemy import MetaData, create_engine, event
    from sqlalchemy.schema import CreateSchema, DropSchema
    from packages.chat.store import ChatStore, CaseNotFound, conversations, creations
    from packages.domain_bridge.planning_store import PlanningStore, LeaseLost, runs

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    config = dotenv_values(args.env_file)
    url = config.get('FSIE_WEB_DATABASE_URL') or config.get('FSIE_DATABASE_URL')
    if not url or not url.startswith(('postgresql://', 'postgresql+psycopg://')):
        raise SystemExit('PostgreSQL configuration required')
    url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
    schema = 'fsie_planning_check_' + uuid4().hex
    admin = create_engine(url, connect_args={'connect_timeout': 10})
    metadata = MetaData()
    for table in (conversations, creations, runs):
        table.to_metadata(metadata)
    engines = []
    created = False
    report = {'schema': schema, 'checks': {}, 'production_tables_mutated': False,
              'scope': 'real PostgreSQL store operations across connection recreation; not hosted API/auth acceptance'}

    def isolated_engine():
        engine = create_engine(url, connect_args={'connect_timeout': 10},
                               execution_options={'schema_translate_map': {None: schema}})
        # Fail closed if any table-bearing SQL escapes explicit qualification.
        @event.listens_for(engine, 'before_cursor_execute')
        def guard(connection, cursor, statement, parameters, context, executemany):
            for name in ('chat_cases', 'chat_case_creations', 'planning_runs'):
                if name in statement and schema + '.' + name not in statement:
                    raise RuntimeError('unqualified_test_table_sql')
            if 'public.' in statement:
                raise RuntimeError('production_schema_sql_rejected')
        engines.append(engine)
        return engine

    try:
        with admin.begin() as connection:
            connection.execute(CreateSchema(schema))
        created = True
        engine = isolated_engine()
        metadata.create_all(engine, checkfirst=False)
        chat = object.__new__(ChatStore)
        chat.engine = engine
        jobs = PlanningStore(engine)
        creation_request = str(uuid4())
        case = chat.create('synthetic-owner-a', creation_request)
        assert chat.create('synthetic-owner-a', creation_request) == case
        report['checks']['idempotent_case_creation'] = 'passed'
        run = jobs.enqueue('synthetic-owner-a', case['id'], 0, 'request-one',
                           {'amount': 100}, {'version': 'synthetic'})
        assert jobs.enqueue('synthetic-owner-a', case['id'], 0, 'request-one',
                            {'amount': 100}, {'version': 'synthetic'})['id'] == run['id']
        report['checks']['idempotent_enqueue'] = 'passed'
        try:
            jobs.get('synthetic-owner-b', run['id'])
        except CaseNotFound:
            report['checks']['owner_filter'] = 'passed'
        else:
            raise AssertionError('owner_filter_failed')
        claim = jobs.claim()
        assert claim and jobs.claim() is None
        jobs.heartbeat(run['id'], claim['lease_token'])
        engine.dispose()
        fresh = isolated_engine()
        recovered = PlanningStore(fresh)
        assert recovered.get('synthetic-owner-a', run['id'])['status'] == 'running'
        assert recovered.claim() is None
        report['checks']['reconnect_preserves_active_lease'] = 'passed'
        with fresh.begin() as connection:
            connection.execute(runs.update().where(runs.c.id == run['id']).values(lease_until=0))
        replacement = recovered.claim()
        assert replacement and replacement['attempts'] == 2
        try:
            recovered.finish(run['id'], claim['lease_token'], result={'stale': True})
        except LeaseLost:
            report['checks']['stale_worker_fenced'] = 'passed'
        else:
            raise AssertionError('lease_fence_failed')
        recovered.finish(run['id'], replacement['lease_token'], result={'synthetic_verified': True})
        fresh.dispose()
        final = isolated_engine()
        assert PlanningStore(final).get('synthetic-owner-a', run['id'])['result'] == {'synthetic_verified': True}
        report['checks']['completed_result_survives_reconnect'] = 'passed'
        final_chat = object.__new__(ChatStore)
        final_chat.engine = final
        assert final_chat.create('synthetic-owner-a', creation_request) == case
        report['checks']['creation_receipt_survives_reconnect'] = 'passed'
        final_chat.delete('synthetic-owner-a', case['id'], case['revision'])
        assert PlanningStore(final).list_case('synthetic-owner-a', case['id'])['items'] == []
        try:
            final_chat.create('synthetic-owner-a', creation_request)
        except CaseNotFound:
            report['checks']['deleted_case_not_recreated'] = 'passed'
        else:
            raise AssertionError('deleted_case_recreated')
        report['status'] = 'passed'
    except Exception as exc:
        # Never emit driver exception text, which can contain credentials.
        report.update(status='failed', error=type(exc).__name__)
    finally:
        if created:
            try:
                cleanup = isolated_engine()
                metadata.drop_all(cleanup, checkfirst=True)
                with admin.begin() as connection:
                    connection.execute(DropSchema(schema))
                report['cleaned_up'] = True
            except Exception as exc:
                report.update(status='failed', cleaned_up=False, cleanup_error=type(exc).__name__)
        for engine in engines:
            engine.dispose()
        admin.dispose()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(report))
    return 0 if report.get('status') == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
