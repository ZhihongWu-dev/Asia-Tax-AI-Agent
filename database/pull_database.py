"""Read-only inspection and download of the configured Supabase database."""
from pathlib import Path, PurePosixPath
import argparse
import json
import os
import sys
import csv
import hashlib
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from urllib.parse import urlsplit, quote

ROOT = Path(__file__).resolve().parent


def config():
    source = ROOT / '.env'
    if not source.exists():
        source = ROOT / '(3).env'
    result = {}
    for line in source.read_text(encoding='utf-8-sig').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, sep, value = line.removeprefix('export ').partition('=')
        if sep:
            result[key.strip()] = value.strip().strip('"\'')
    return result


def storage_session(cfg):
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    base = cfg['FSIE_AUTH_SUPABASE_URL'].rstrip('/')
    if urlsplit(base).hostname != 'ujeppdjucpajhsdclgif.supabase.co':
        raise RuntimeError('Configured Supabase project differs from the requested project')
    key = cfg['FSIE_AUTH_PUBLISHABLE_KEY']
    session = requests.Session()
    session.headers['apikey'] = key
    if key.startswith('eyJ'):
        session.headers['Authorization'] = 'Bearer ' + key
    session.mount('https://', HTTPAdapter(max_retries=Retry(
        total=4, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=['GET', 'POST'])))
    return base, session


def list_objects(base, session, prefix=''):
    offset = 0
    while True:
        response = session.post(base + '/storage/v1/object/list/database', json={
            'prefix': prefix, 'limit': 1000, 'offset': offset,
            'sortBy': {'column': 'name', 'order': 'asc'}}, timeout=90)
        if response.status_code != 200:
            raise RuntimeError(f'Storage listing failed: HTTP {response.status_code}')
        rows = response.json()
        if not isinstance(rows, list):
            raise RuntimeError('Unexpected Storage listing response')
        for row in rows:
            name = '/'.join(x for x in [prefix, row['name']] if x)
            if row.get('id') is None and row.get('metadata') is None:
                yield from list_objects(base, session, name)
            else:
                yield {'name': name, 'size': (row.get('metadata') or {}).get('size'),
                       'updated_at': row.get('updated_at'), 'metadata': row.get('metadata')}
        if len(rows) < 1000:
            break
        offset += len(rows)


def connect(cfg):
    import psycopg
    url = cfg['FSIE_DATABASE_URL'].replace('postgresql+psycopg://', 'postgresql://', 1)
    conn = psycopg.connect(url, connect_timeout=20, sslmode='require')
    conn.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
    conn.read_only = True
    conn.execute("SET statement_timeout = '120s'")
    return conn


def inspect(cfg):
    from psycopg import sql
    print('Checking PostgreSQL schema database...', flush=True)
    with connect(cfg) as conn:
        version = conn.execute('SHOW server_version').fetchone()[0]
        exists = conn.execute("SELECT EXISTS(SELECT FROM pg_namespace WHERE nspname='database')").fetchone()[0]
        tables = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='database' AND table_type='BASE TABLE' ORDER BY table_name").fetchall()
        print(json.dumps({'postgres_version': version, 'schema_database_exists': exists}, ensure_ascii=False), flush=True)
        for (table,) in tables:
            count = conn.execute(sql.SQL('SELECT count(*) FROM {}.{}').format(sql.Identifier('database'), sql.Identifier(table))).fetchone()[0]
            cols = conn.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='database' AND table_name=%s ORDER BY ordinal_position", (table,)).fetchall()
            print(json.dumps({'table': table, 'rows': count, 'columns': cols}, ensure_ascii=False), flush=True)
    print('Checking Storage bucket database...', flush=True)
    base, session = storage_session(cfg)
    objects = list(list_objects(base, session))
    print(json.dumps({'bucket': 'database', 'files': len(objects), 'bytes': sum(int(x['size'] or 0) for x in objects), 'top_level': sorted({x['name'].split('/')[0] for x in objects}), 'docs': [x['name'] for x in objects if x['name'].startswith('docs/')]}, ensure_ascii=False), flush=True)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def publish_file(temporary, destination):
    if destination.exists():
        if digest(temporary) != digest(destination):
            raise RuntimeError(f'Local file already exists with different contents: {destination.relative_to(ROOT)}')
        temporary.unlink()
    else:
        temporary.replace(destination)


def pull(cfg):
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict
    target = ROOT / 'database'
    backup = ROOT / '_supabase_snapshot'
    target.mkdir(exist_ok=True)
    backup.mkdir(exist_ok=True)
    report = {'created_at': datetime.now(timezone.utc).isoformat(),
              'schema': 'database', 'bucket': 'database', 'tables': [], 'objects': []}
    with connect(cfg) as conn:
        tables = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='database' AND table_type='BASE TABLE' ORDER BY table_name").fetchall()
        if not tables:
            raise RuntimeError('No visible tables in schema database')
        report['postgres_version'] = conn.execute('SHOW server_version').fetchone()[0]
        exported_snapshot = conn.execute('SELECT pg_export_snapshot()').fetchone()[0]
        print(f'Exporting {len(tables)} database tables...', flush=True)
        for (table,) in tables:
            identifier = sql.SQL('{}.{}').format(sql.Identifier('database'), sql.Identifier(table))
            count = conn.execute(sql.SQL('SELECT count(*) FROM {}').format(identifier)).fetchone()[0]
            columns = conn.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='database' AND table_name=%s ORDER BY ordinal_position", (table,)).fetchall()
            destination = target / (table + '.csv')
            if destination.parent != target or '/' in table:
                raise RuntimeError('Unsafe table name')
            temporary = destination.with_suffix('.csv.part')
            with conn.cursor() as cur, temporary.open('wb') as output:
                with cur.copy(sql.SQL('COPY {} TO STDOUT WITH (FORMAT CSV, HEADER TRUE)').format(identifier)) as stream:
                    for block in stream:
                        output.write(block)
            csv.field_size_limit(sys.maxsize)
            with temporary.open(encoding='utf-8', newline='') as stream:
                reader = csv.reader(stream)
                next(reader)
                local_count = sum(1 for _ in reader)
            if local_count != count:
                raise RuntimeError(f'Row-count mismatch for {table}')
            publish_file(temporary, destination)
            report['tables'].append({'name': table, 'rows': count, 'columns': columns,
                                     'sha256': digest(destination), 'bytes': destination.stat().st_size})
            print(f'  {table}: {count} rows', flush=True)
        params = conninfo_to_dict(cfg['FSIE_DATABASE_URL'].replace('postgresql+psycopg://', 'postgresql://', 1))
        dump_env = os.environ.copy()
        for field, envkey in [('host', 'PGHOST'), ('port', 'PGPORT'), ('dbname', 'PGDATABASE'), ('user', 'PGUSER'), ('password', 'PGPASSWORD')]:
            if field in params:
                dump_env[envkey] = params[field]
        dump_env.update(PGSSLMODE='require', PGCONNECT_TIMEOUT='20', PGOPTIONS='-c default_transaction_read_only=on')
        dump_temp = backup / 'database.dump.part'
        result = subprocess.run(['/opt/homebrew/opt/libpq/bin/pg_dump', '--format=custom',
            '--schema=database', '--no-owner', '--no-privileges', '--snapshot=' + exported_snapshot,
            '--file=' + str(dump_temp)], env=dump_env, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError('pg_dump failed: ' + result.stderr.strip())
        publish_file(dump_temp, backup / 'database.dump')
        report['dump_sha256'] = digest(backup / 'database.dump')
    base, session = storage_session(cfg)
    objects = list(list_objects(base, session))
    total_bytes = sum(int(x['size'] or 0) for x in objects)
    print(f'Downloading Storage database: {len(objects)} objects, {total_bytes / 1048576:.1f} MiB...', flush=True)

    def download(obj):
        relative = PurePosixPath(obj['name'])
        if relative.is_absolute() or '..' in relative.parts:
            raise RuntimeError('Unsafe Storage object path')
        destination = target.joinpath(*relative.parts)
        if not destination.resolve().is_relative_to(target.resolve()):
            raise RuntimeError('Storage object escapes destination')
        destination.parent.mkdir(parents=True, exist_ok=True)
        _, local_session = storage_session(cfg)
        url = base + '/storage/v1/object/database/' + quote(obj['name'], safe='/')
        with local_session.get(url, stream=True, timeout=(20, 180), headers={'Accept-Encoding': 'identity'}) as response:
            if response.status_code != 200:
                raise RuntimeError(f"Download failed: {obj['name']} (HTTP {response.status_code})")
            with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=destination.name + '.', suffix='.part', delete=False) as output:
                temporary = Path(output.name)
                for block in response.iter_content(1024 * 1024):
                    output.write(block)
        if obj['size'] is not None and temporary.stat().st_size != int(obj['size']):
            raise RuntimeError('File-size mismatch: ' + obj['name'])
        obj['sha256'] = digest(temporary)
        publish_file(temporary, destination)
        return obj

    with ThreadPoolExecutor(max_workers=6) as pool:
        jobs = [pool.submit(download, obj) for obj in objects]
        for index, future in enumerate(as_completed(jobs), 1):
            report['objects'].append(future.result())
            if index % 25 == 0 or index == len(objects):
                print(f'  Storage: {index}/{len(objects)} objects downloaded and size-checked', flush=True)
    report['objects'].sort(key=lambda x: x['name'])
    # Check that listing metadata stayed stable during the download.
    after = list(list_objects(base, session))
    signature = lambda rows: sorted((x['name'], x['size'], x['updated_at']) for x in rows)
    report['storage_stable_during_download'] = signature(objects) == signature(after)
    if not report['storage_stable_during_download']:
        raise RuntimeError('Storage changed during download; inspect before treating snapshot as complete')
    indexed_files = []
    with (target / 'files.csv').open(encoding='utf-8', newline='') as stream:
        for row in csv.DictReader(stream):
            local_file = target / row['path']
            if not local_file.resolve().is_relative_to(target.resolve()):
                raise RuntimeError('Unsafe indexed path')
            if not local_file.is_file():
                raise RuntimeError('Indexed file missing: ' + row['path'])
            if local_file.stat().st_size != int(row['bytes']) or digest(local_file) != row['sha256']:
                raise RuntimeError('Indexed file hash or size differs: ' + row['path'])
            indexed_files.append(row['path'])
    report['indexed_files_verified'] = len(indexed_files)
    (backup / 'manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'complete': True, 'tables': len(report['tables']),
        'rows': sum(x['rows'] for x in report['tables']), 'objects': len(objects),
        'storage_bytes': total_bytes, 'target': str(target)}, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--inspect', action='store_true')
    parser.add_argument('--pull', action='store_true')
    args = parser.parse_args()
    if args.pull:
        pull(config())
    else:
        inspect(config())


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Never put connection strings, passwords or API keys into terminal output.
        print(f'Operation failed ({type(exc).__name__}).', file=sys.stderr)
        message = str(exc)
        for key, value in config().items():
            if value and any(word in key for word in ('KEY', 'DATABASE_URL')):
                message = message.replace(value, '<redacted>')
                if 'DATABASE_URL' in key:
                    password = urlsplit(value).password
                    if password:
                        message = message.replace(password, '<redacted>')
        print(message, file=sys.stderr)
        sys.exit(1)
