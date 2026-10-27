"""Fetch one official source, write its raw original and register doc.csv."""
from __future__ import annotations
import argparse, mimetypes, re, subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests
from common import CATEGORIES, DATA, OFFICIAL, TYPES, rows, sha256, write_rows

parser = argparse.ArgumentParser()
parser.add_argument('--id', required=True)
parser.add_argument('--jur', required=True)
parser.add_argument('--type', choices=TYPES, required=True)
parser.add_argument('--category', default='')
parser.add_argument('--title', required=True)
parser.add_argument('--url', required=True)
parser.add_argument('--lang', required=True)
parser.add_argument('--effective', default='')
parser.add_argument('--effective-to', default='')
parser.add_argument('--note', default='')
parser.add_argument('--force', action='store_true')
parser.add_argument('--engine', choices=('requests', 'curl'), default='requests')
args = parser.parse_args()
if not re.fullmatch(r'[A-Za-z0-9_.-]+', args.id): parser.error('id may only contain ASCII letters, digits, dot, underscore and hyphen')
if urlsplit(args.url).hostname not in OFFICIAL: parser.error('URL is not an approved official host; add an official host in common.py only after verification')
if any(c not in CATEGORIES for c in filter(None, args.category.split(';'))): parser.error('category is invalid')
all_docs = rows('doc')
previous = next((r for r in all_docs if r['id'] == args.id), None)
if previous and not args.force: parser.error('id already exists; use --force only to replace its source')
if args.engine == 'curl':
    temporary_download = DATA / '.fetch-download.tmp'
    completed = subprocess.run(['curl', '--fail', '--location', '--retry', '3', '--retry-all-errors',
                                '--connect-timeout', '20', args.url, '--output', str(temporary_download)],
                               text=True, capture_output=True)
    if completed.returncode:
        raise RuntimeError(f'curl download failed: {completed.stderr.strip()}')
    content = temporary_download.read_bytes()
    temporary_download.unlink()
    final_url, content_type = args.url, ''
else:
    response = requests.get(args.url, timeout=(20, 180), headers={'User-Agent': 'database-collector/1.0'})
    response.raise_for_status()
    content, final_url, content_type = response.content, response.url, response.headers.get('Content-Type', '')
suffix = Path(urlsplit(final_url).path).suffix.lower() or mimetypes.guess_extension(content_type.split(';')[0]) or '.html'
destination = DATA / 'raw' / args.jur / (args.id + suffix)
destination.parent.mkdir(parents=True, exist_ok=True)
temporary = destination.with_suffix(destination.suffix + '.new')
temporary.write_bytes(content)
temporary.replace(destination)
row = {'id': args.id, 'jur': args.jur, 'type': args.type, 'category': args.category, 'title': args.title,
       'url': args.url, 'file': str(destination.relative_to(DATA)), 'sha256': sha256(destination), 'lang': args.lang,
       'effective_from': args.effective, 'effective_to': args.effective_to,
       'note': (args.note + ' ' if args.note else '') + 'downloaded with requests ' + datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}
all_docs = [r for r in all_docs if r['id'] != args.id] + [row]
write_rows('doc', all_docs)
print(f'Registered {args.id}: {destination.relative_to(DATA)}')
