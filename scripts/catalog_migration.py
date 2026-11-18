"""Validate reviewed catalog operations without modifying a database.

The returned copy is a simulation, not evidence that a deployment is ready.
Callers must read all affected keys from one consistent database snapshot.
"""
from copy import deepcopy
from hashlib import sha256
import json


KEYS = {'doc': 'id', 'param': 'param_id', 'decision': 'id', 'clause': 'cite_id'}


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def validate_plan(plan):
    operations = plan['operations']
    if (not operations or plan['operation_count'] != len(operations)
            or plan['proposed_catalog_revision'] != digest(operations)):
        raise ValueError('migration_plan_digest_mismatch')
    seen = set()
    for op in operations:
        table, key = op['table'], op['key']
        if table not in KEYS or op['key_column'] != KEYS[table]:
            raise ValueError('migration_table_or_key_invalid')
        if not isinstance(key, str) or not key or (table, key) in seen:
            raise ValueError('migration_duplicate_or_invalid_key')
        seen.add((table, key))
        action, before, after = op['operation'], op['expected_before'], op['after']
        if action not in ('insert', 'update', 'delete'):
            raise ValueError('migration_action_invalid')
        if ((action == 'insert') != (before is None)
                or (action == 'delete') != (after is None)):
            raise ValueError('migration_row_shape_invalid')
        for row in (before, after):
            if row is not None and (not isinstance(row, dict) or row.get(KEYS[table]) != key):
                raise ValueError('migration_row_key_mismatch')
        for row, field in ((before, 'expected_before_sha256'), (after, 'after_sha256')):
            if field in op and (row is None or op[field] != digest(row)):
                raise ValueError('migration_row_digest_mismatch')
    return operations


def simulate(plan, catalogs, *, uploaded_at):
    """Apply exact before-state guards to a copy; never alter caller data."""
    operations = validate_plan(plan)
    if uploaded_at != plan['base_uploaded_at']:
        raise ValueError('migration_base_upload_changed')
    # Check every guard before constructing the simulated result.
    for op in operations:
        rows = catalogs[op['table']]
        key = op['key']
        if op['operation'] == 'insert':
            matches = key not in rows
        else:
            matches = key in rows and rows[key] == op['expected_before']
        if not matches:
            raise ValueError('migration_before_state_changed:' + op['table'] + ':' + key)
    result = deepcopy(catalogs)
    for op in operations:
        rows = result[op['table']]
        if op['operation'] == 'delete':
            del rows[op['key']]
        else:
            rows[op['key']] = deepcopy(op['after'])
    return result


def read_affected_catalogs(connection, plan, *, extra_keys=None, batch_size=50):
    """Read bounded key batches in the caller's existing read-only transaction.

    Missing rows remain absent so insert guards can distinguish them from
    existing records. Additional keys support source-overlay validation.
    """
    from sqlalchemy import text

    operations = validate_plan(plan)
    if type(batch_size) is not int or not 1 <= batch_size <= 100:
        raise ValueError('migration_batch_size_invalid')
    wanted = {table: set() for table in KEYS}
    for op in operations:
        wanted[op['table']].add(op['key'])
    for table, ids in (extra_keys or {}).items():
        if table not in KEYS or not isinstance(ids, (list, tuple, set)):
            raise ValueError('migration_extra_keys_invalid')
        if any(not isinstance(key, str) or not key for key in ids):
            raise ValueError('migration_extra_keys_invalid')
        wanted[table].update(ids)
    catalogs = {table: {} for table in KEYS}
    for table, key_column in KEYS.items():
        ids = sorted(wanted[table])
        for offset in range(0, len(ids), batch_size):
            batch = ids[offset:offset + batch_size]
            # Identifiers come exclusively from KEYS, values are bound.
            statement = text(f'SELECT * FROM database.{table} WHERE {key_column} = ANY(:ids)')
            with connection.execute(statement, {'ids': batch}) as result:
                for row in result.mappings():
                    key = row[key_column]
                    if key not in batch or key in catalogs[table]:
                        raise ValueError('migration_unexpected_or_duplicate_row')
                    catalogs[table][key] = dict(row)
    return catalogs
