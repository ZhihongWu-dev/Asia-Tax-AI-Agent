"""Synchronise the local database package to Supabase.

Only the ``database`` schema and the Storage bucket of the same name are in
scope. Tables load into a same-structure staging schema and swap in one
PostgreSQL transaction, so a failed table load leaves the old schema intact.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote

import psycopg
import requests
from psycopg import sql

from build import audit
from common import DATA, TABLES, rows

DOCS = ('docs/spec.zh.md', 'docs/spec.en.md', 'docs/task_sheet.zh.md', 'docs/task_sheet.en.md')
REMOTE_SCHEMA = 'database'
BUCKET = 'database'
STAGING_SCHEMA = 'database_upload_stage'
COPY_BATCH_ROWS = 250
PRIMARY_KEYS = {
    'jurisdiction': 'code', 'doc': 'id', 'files': 'path', 'clause': 'cite_id',
    'param': 'param_id', 'decision': 'id', 'treaty': 'pair',
}


def env_values() -> dict[str, str]:
    """Read local configuration without displaying secret values."""
    values: dict[str, str] = {}
    for location in (DATA.parent / '.env', DATA / '.env'):
        if not location.exists():
            continue
        for line in location.read_text(encoding='utf-8').splitlines():
            key, separator, value = line.partition('=')
            if separator and key.strip() and not key.lstrip().startswith('#'):
                values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def configured(values: dict[str, str], *names: str) -> str:
    for name in names:
        if values.get(name):
            return values[name]
        if os.environ.get(name):
            return os.environ[name]
    return ''


def configuration() -> tuple[str, str, str]:
    values = env_values()
    database_url = configured(values, 'database_url', 'DATABASE_URL', 'FSIE_DATABASE_URL')
    supabase_url = configured(values, 'supabase_url', 'SUPABASE_URL', 'FSIE_AUTH_SUPABASE_URL')
    supabase_key = configured(values, 'supabase_key', 'SUPABASE_KEY', 'FSIE_AUTH_PUBLISHABLE_KEY')
    missing = [label for label, value in (
        ('database URL', database_url), ('Supabase URL', supabase_url), ('Supabase key', supabase_key),
    ) if not value]
    if missing:
        raise ValueError('Missing ' + ', '.join(missing) + ' in .env')
    # SQLAlchemy URLs are common in application .env files but psycopg takes
    # a PostgreSQL URI. Some prior local configuration also used a bare
    # ``?sslmode`` flag; make its intended secure value explicit.
    if database_url.startswith('postgresql+psycopg://'):
        database_url = 'postgresql://' + database_url.removeprefix('postgresql+psycopg://')
    if database_url.endswith('?sslmode'):
        database_url += '=require'
    elif '&sslmode' in database_url and ('&sslmode=' not in database_url):
        database_url = database_url.replace('&sslmode', '&sslmode=require')
    return database_url, supabase_url.rstrip('/'), supabase_key


def local_objects() -> list[str]:
    names = [item['path'] for item in rows('files')] + list(DOCS)
    missing = [name for name in names if not (DATA / name).is_file()]
    if missing:
        raise ValueError('Local upload object is missing: ' + ', '.join(missing))
    return sorted(set(names))


def storage_headers(key: str) -> dict[str, str]:
    return {'apikey': key, 'Authorization': f'Bearer {key}'}


def curl_storage_list(url: str, key: str, prefix: str) -> list[dict]:
    """List Storage objects with curl only after requests has a TLS transport error.

    The Supabase key is written to a 0600 temporary curl configuration file,
    never passed in command arguments or printed in diagnostics.
    """
    request_body = json.dumps({'prefix': prefix, 'limit': 1000, 'offset': 0,
                               'sortBy': {'column': 'name', 'order': 'asc'}})
    def quoted(value: str) -> str:
        return value.replace('\\', '\\\\').replace('"', '\\"')
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', prefix='database-storage-', delete=False) as config:
        config.write(f'header = "apikey: {quoted(key)}"\n')
        config.write(f'header = "Authorization: Bearer {quoted(key)}"\n')
        config.write('header = "Content-Type: application/json"\n')
        config.write(f'data = "{quoted(request_body)}"\n')
        config_path = Path(config.name)
    try:
        config_path.chmod(0o600)
        completed = subprocess.run(
            ['curl', '--silent', '--show-error', '--fail', '--connect-timeout', '10', '--max-time', '20',
             '--config', str(config_path),
             f'{url}/storage/v1/object/list/{BUCKET}'], text=True, capture_output=True,
        )
        if completed.returncode:
            raise ValueError(f'Storage list curl fallback failed: {completed.stderr.strip()}')
        payload = json.loads(completed.stdout)
        if not isinstance(payload, list):
            raise ValueError('Storage list curl fallback returned a non-list response')
        return payload
    finally:
        config_path.unlink(missing_ok=True)


def remote_objects_http(url: str, key: str, prefix: str = '') -> set[str]:
    """Recursively list objects in exactly the selected bucket.

    The Supabase Storage list endpoint is reliable through curl in this
    environment, while the Python TLS transport can stall before it reports a
    retryable error. Prefer the supported curl path and retain requests as a
    fallback for installations where curl itself is unavailable.
    """
    try:
        entries = curl_storage_list(url, key, prefix)
    except ValueError:
        response = requests.post(
            f'{url}/storage/v1/object/list/{BUCKET}', headers=storage_headers(key),
            json={'prefix': prefix, 'limit': 1000, 'offset': 0, 'sortBy': {'column': 'name', 'order': 'asc'}},
            timeout=15,
        )
        response.raise_for_status()
        entries = response.json()
    result: set[str] = set()
    for entry in entries:
        name = entry.get('name', '')
        if not name:
            continue
        relative = f'{prefix}/{name}'.strip('/')
        if entry.get('id') is None and entry.get('metadata') is None:
            result |= remote_objects_http(url, key, relative)
        else:
            result.add(relative)
    return result


def remote_objects(database_url: str, supabase_url: str, supabase_key: str) -> set[str]:
    """List exactly the target bucket's object names without recursive HTTP calls.

    The configured PostgreSQL connection is already required for the atomic
    schema replacement.  Querying `storage.objects` through that same channel
    avoids one Storage REST request per folder during preflight and verification.
    Retain the REST implementation as a fallback for deployments whose database
    role cannot read the Storage metadata table.
    """
    try:
        with psycopg.connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT name FROM storage.objects WHERE bucket_id = %s', (BUCKET,))
                return {row[0] for row in cursor.fetchall()}
    except psycopg.Error:
        return remote_objects_http(supabase_url, supabase_key)


def upload_object(url: str, key: str, name: str) -> None:
    try:
        with (DATA / name).open('rb') as payload:
            response = requests.post(
                f'{url}/storage/v1/object/{BUCKET}/{quote(name, safe="/")}',
                headers={**storage_headers(key), 'x-upsert': 'true', 'Content-Type': 'application/octet-stream'},
                data=payload, timeout=300,
            )
    except requests.RequestException as error:
        raise ValueError(f'Storage upload request failed for {name}: {type(error).__name__}') from error
    if not response.ok:
        raise ValueError(f'Storage upload failed for {name}: HTTP {response.status_code}')


def delete_object(url: str, key: str, name: str) -> None:
    response = requests.delete(
        f'{url}/storage/v1/object/{BUCKET}/{quote(name, safe="/")}',
        headers=storage_headers(key), timeout=60,
    )
    if not response.ok:
        raise ValueError(f'Storage deletion failed for {name}: HTTP {response.status_code}')


def replace_tables(database_url: str) -> None:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            print('Table sync: checking target schema.', flush=True)
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = %s AND table_type = 'BASE TABLE'", (REMOTE_SCHEMA,))
            present = {row[0] for row in cursor.fetchall()}
            absent = set(TABLES) - present
            if absent:
                raise ValueError('Remote schema is missing expected tables: ' + ', '.join(sorted(absent)))
            print('Table sync: creating staging schema.', flush=True)
            cursor.execute(f'DROP SCHEMA IF EXISTS {STAGING_SCHEMA} CASCADE')
            cursor.execute(f'CREATE SCHEMA {STAGING_SCHEMA}')
            for table, fields in TABLES.items():
                try:
                    print(f'Table sync: staging {table} ({len(rows(table))} rows).', flush=True)
                    cursor.execute(f'CREATE TABLE {STAGING_SCHEMA}.{table} (LIKE {REMOTE_SCHEMA}.{table} INCLUDING ALL)')
                    if rows(table):
                        # A whole clause.csv COPY can exceed the managed
                        # database's statement timeout.  Keep all batches in
                        # this one transaction and staging schema, while
                        # making each COPY independently short enough to
                        # complete.  Any failed batch still rolls back the
                        # entire transaction before the schema swap.
                        with (DATA / f'{table}.csv').open('r', encoding='utf-8-sig', newline='') as source:
                            reader = csv.DictReader(source)
                            while batch := [next(reader, None) for _ in range(COPY_BATCH_ROWS)]:
                                batch = [record for record in batch if record is not None]
                                if not batch:
                                    break
                                payload = io.StringIO(newline='')
                                writer = csv.DictWriter(payload, fieldnames=fields)
                                writer.writeheader()
                                writer.writerows(batch)
                                with cursor.copy(f'COPY {STAGING_SCHEMA}.{table} ({", ".join(fields)}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE)') as copy:
                                    copy.write(payload.getvalue())
                except psycopg.Error as error:
                    # COPY errors identify a bad local value, not credentials.
                    # Keep the database URI out of diagnostics while preserving
                    # enough context to repair a failed staged upload.
                    state = getattr(error, 'sqlstate', None)
                    detail = str(error).splitlines()[0]
                    suffix = f' [{state}]' if state else ''
                    raise ValueError(f'Unable to stage table {table}{suffix}: {detail}') from error
            print('Table sync: replacing target schema.', flush=True)
            cursor.execute(f'DROP SCHEMA {REMOTE_SCHEMA} CASCADE')
            cursor.execute(f'ALTER SCHEMA {STAGING_SCHEMA} RENAME TO {REMOTE_SCHEMA}')
        print('Table sync: committing replacement.', flush=True)
        connection.commit()


def reconcile_missing_rows(database_url: str) -> None:
    """Insert only local rows absent by primary key, within one transaction.

    This is deliberately narrower than a schema replacement.  It is valid only
    when the remote set is a strict subset of local data: a remote-only key is
    an unexpected divergence and stops the operation before any write.
    """
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            for table, fields in TABLES.items():
                key = PRIMARY_KEYS[table]
                local = {record[key]: record for record in rows(table)}
                cursor.execute(
                    sql.SQL('SELECT {} FROM {}.{}').format(
                        sql.Identifier(key), sql.Identifier(REMOTE_SCHEMA), sql.Identifier(table)
                    )
                )
                remote_keys = {record[0] for record in cursor.fetchall()}
                unexpected = remote_keys - set(local)
                if unexpected:
                    raise ValueError(
                        f'Reconciliation refused for {table}: remote-only primary keys are present.'
                    )
                missing = [local[record_key] for record_key in sorted(set(local) - remote_keys)]
                if not missing:
                    print(f'Table reconciliation: {table} already matches.', flush=True)
                    continue
                print(f'Table reconciliation: inserting {len(missing)} missing {table} rows.', flush=True)
                statement = sql.SQL('INSERT INTO {}.{} ({}) VALUES ({})').format(
                    sql.Identifier(REMOTE_SCHEMA),
                    sql.Identifier(table),
                    sql.SQL(', ').join(sql.Identifier(field) for field in fields),
                    sql.SQL(', ').join(sql.Placeholder() for _ in fields),
                )
                cursor.executemany(
                    statement,
                    [tuple(record[field] or None for field in fields) for record in missing],
                )
        print('Table reconciliation: committing additive changes.', flush=True)
        connection.commit()


def preflight_remote(database_url: str, supabase_url: str, supabase_key: str) -> int:
    """Confirm the intended schema and bucket are reachable without mutation."""
    remote = remote_objects(database_url, supabase_url, supabase_key)
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = %s AND table_type = 'BASE TABLE'", (REMOTE_SCHEMA,))
            present = {row[0] for row in cursor.fetchall()}
    absent = set(TABLES) - present
    if absent:
        raise ValueError('Remote schema is missing expected tables: ' + ', '.join(sorted(absent)))
    return len(remote)


def verify_remote(database_url: str, supabase_url: str, supabase_key: str, objects: list[str]) -> None:
    """Compare remote object names and table row counts without mutation."""
    remote = remote_objects(database_url, supabase_url, supabase_key)
    wanted = set(objects)
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            for table in TABLES:
                cursor.execute(f'SELECT count(*) FROM {REMOTE_SCHEMA}.{table}')
                actual = cursor.fetchone()[0]
                expected = len(rows(table))
                if actual != expected:
                    raise ValueError(f'Remote row count differs for {table}: expected {expected}, found {actual}')
    if remote != wanted:
        raise ValueError('Remote Storage object names differ from the local upload set')
    print(f'Remote verification passed: {len(wanted)} objects and {len(TABLES)} table row counts match local data.', flush=True)


def remote_status(database_url: str, supabase_url: str, supabase_key: str, objects: list[str]) -> None:
    """Display counts and object-set differences without mutating remote state."""
    remote = remote_objects(database_url, supabase_url, supabase_key)
    wanted = set(objects)
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            for table in TABLES:
                cursor.execute(f'SELECT count(*) FROM {REMOTE_SCHEMA}.{table}')
                print(f'  remote {table}: {cursor.fetchone()[0]} rows')
    print(f'Remote objects: {len(remote)}; local-only: {len(wanted - remote)}; remote-only: {len(remote - wanted)}', flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--preflight', action='store_true', help='read-only check of the target schema and bucket')
    parser.add_argument('--verify', action='store_true', help='read-only comparison of remote rows and object names')
    parser.add_argument('--status', action='store_true', help='read-only remote row and object-count report')
    parser.add_argument('--resume', action='store_true', help='upload only local objects absent from the selected bucket')
    parser.add_argument('--partial', action='store_true', help='allow coverage gaps when explicitly authorised')
    parser.add_argument('--reconcile', action='store_true', help='insert only local rows missing by primary key; refuse remote-only rows')
    args = parser.parse_args()
    errors, gaps, warnings = audit()
    if errors:
        raise SystemExit(f'Upload blocked: {len(errors)} data errors.')
    if gaps and not args.partial:
        raise SystemExit(f'Upload blocked: {len(gaps)} coverage gaps. Use --partial only with explicit approval.')
    objects = local_objects()
    print(f'Validation: {len(errors)} errors, {len(gaps)} gaps, {len(warnings)} warnings.', flush=True)
    print(f'Objects: {len(objects)} (including {len(DOCS)} documentation files)', flush=True)
    for table in TABLES:
        print(f'  {table}: {len(rows(table))} rows', flush=True)
    if args.dry_run:
        print('Dry run only. No credential was used and no remote write was performed.', flush=True)
        return
    database_url, supabase_url, supabase_key = configuration()
    if args.preflight:
        print(f'Remote preflight passed: {preflight_remote(database_url, supabase_url, supabase_key)} existing bucket objects; expected schema tables are present.', flush=True)
        return
    if args.verify:
        verify_remote(database_url, supabase_url, supabase_key, objects)
        return
    if args.status:
        remote_status(database_url, supabase_url, supabase_key, objects)
        return
    remote = remote_objects(database_url, supabase_url, supabase_key)
    wanted = set(objects)
    upload_names = sorted(wanted - remote) if args.resume else objects
    print(f'Uploading {len(upload_names)} objects; deleting {len(remote - wanted)} obsolete bucket objects.', flush=True)
    for name in upload_names:
        upload_object(supabase_url, supabase_key, name)
    for name in sorted(remote - wanted):
        delete_object(supabase_url, supabase_key, name)
    if args.reconcile:
        reconcile_missing_rows(database_url)
        print('Upload complete: Storage bucket and missing database rows were reconciled.', flush=True)
    else:
        replace_tables(database_url)
        print('Upload complete: Storage bucket and database schema were replaced.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (psycopg.Error, requests.RequestException) as error:
        # Connection exceptions can contain a full URI. Keep diagnostics useful
        # without exposing configured database URLs or credentials.
        status = getattr(getattr(error, 'response', None), 'status_code', None)
        detail = f' HTTP {status}' if status is not None else ''
        print(f'Upload failed during a remote operation ({type(error).__name__}{detail}); no database schema replacement was committed.', flush=True)
        raise SystemExit(1)
    except ValueError as error:
        print(f'Upload validation failed: {error}', flush=True)
        raise SystemExit(1)
