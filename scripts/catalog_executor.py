"""Explicit, transaction-owned catalog execution; no CLI or automatic deployment.

Callers must supply deployment/source-review validators that raise or return
True. PostgreSQL acceptance is required before using this against a live catalog.
SQLite support exists for local transaction/rollback tests only.
"""
from copy import deepcopy

from sqlalchemy import MetaData, Table, select, text

from scripts.catalog_migration import KEYS, simulate, validate_plan, verify_target


def execute_reviewed_plan(engine, plan, *, expected_catalog_revision,
                          validate_before, validate_after):
    plan = deepcopy(plan)
    operations = validate_plan(plan)
    if not callable(validate_before) or not callable(validate_after):
        raise ValueError('migration_validators_required')
    if engine.dialect.name not in ('postgresql', 'sqlite'):
        raise ValueError('migration_database_unsupported')
    with engine.connect().execution_options(isolation_level='SERIALIZABLE') as connection:
        with connection.begin():
            if engine.dialect.name == 'postgresql':
                connection.execute(text("SET LOCAL lock_timeout = '10s'"))
                connection.execute(text("SET LOCAL statement_timeout = '60s'"))
                connection.execute(text('LOCK TABLE database.meta, database.doc, database.param, '
                    'database.decision, database.clause, database_integration.source_review '
                    'IN SHARE ROW EXCLUSIVE MODE'))
            else:
                connection.exec_driver_sql('BEGIN IMMEDIATE')
            metadata = MetaData()
            tables = {name: Table(name, metadata, schema='database', autoload_with=connection)
                      for name in set(op['table'] for op in operations)}
            meta = Table('meta', metadata, schema='database', autoload_with=connection)
            version = dict(connection.execute(select(meta.c.key, meta.c.value)).all())
            if version.get('catalog_revision') != expected_catalog_revision:
                raise ValueError('migration_catalog_revision_changed')

            def read_targets():
                result = {name: {} for name in tables}
                for name, table in tables.items():
                    keys = sorted(op['key'] for op in operations if op['table'] == name)
                    for start in range(0, len(keys), 50):
                        for row in connection.execute(select(table).where(
                                table.c[KEYS[name]].in_(keys[start:start+50]))).mappings():
                            result[name][row[KEYS[name]]] = dict(row)
                return result

            simulate(plan, read_targets(), uploaded_at=version.get('uploaded_at'))
            if validate_before(connection) is not True:
                raise ValueError('migration_preflight_rejected')
            for op in operations:
                table = tables[op['table']]
                key = table.c[op['key_column']]
                after = op['after']
                if after is not None and set(after) != set(table.c.keys()):
                    raise ValueError('migration_target_columns_incomplete')
                if op['operation'] == 'insert':
                    connection.execute(table.insert().values(**after))
                else:
                    statement = table.delete() if after is None else table.update().values(**after)
                    changed = connection.execute(statement.where(key == op['key']))
                    if changed.rowcount != 1:
                        raise ValueError('migration_write_count_mismatch')
            result = verify_target(plan, read_targets())
            revision = plan['proposed_catalog_revision']
            if 'catalog_revision' in version:
                connection.execute(meta.update().where(meta.c.key == 'catalog_revision').values(value=revision))
            else:
                connection.execute(meta.insert().values(key='catalog_revision', value=revision))
            if validate_after(connection) is not True:
                raise ValueError('migration_postflight_rejected')
        return {**result, 'status': 'committed'}
