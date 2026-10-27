"""Validate the CSV database package against docs/spec.zh.md.

The downloaded package already contains generated text/, files.csv and
clause.csv. This implementation validates those generated artifacts instead
of overwriting them. Re-slicing from every original format will be added only
with per-format fixtures; this prevents a generic parser from corrupting
verified legal citations.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import html
import subprocess
import sys
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from itertools import combinations
from pathlib import Path

from common import (CATEGORIES, DATA, SLOTS, SUBJECTS, TABLES, TYPES, UNITS,
                    is_date, is_pair, official_host, rows, sha256, write_rows,
                    whitespace_normalized)


def materialize_new_documents():
    """Create conservative #all clauses only for newly fetched documents.

    Existing reviewed clauses are never re-sliced. A later format-specific
    slicer can replace a #all clause after its fixture passes.
    """
    docs, clauses, file_rows = rows('doc'), rows('clause'), rows('files')
    known_docs = {r['doc_id'] for r in clauses}
    indexed = {r['path'] for r in file_rows}
    changed = False
    for doc in docs:
        raw = DATA / doc['file']
        raw_hash = sha256(raw)
        raw_row = next((row for row in file_rows if row['path'] == doc['file']), None)
        source_changed = raw_row is not None and (
            raw_row['sha256'] != raw_hash or raw_row['bytes'] != str(raw.stat().st_size)
        )
        if raw_row is None:
            file_rows.append({'path': doc['file'], 'sha256': sha256(raw), 'bytes': str(raw.stat().st_size)})
            indexed.add(doc['file']); changed = True
        elif source_changed:
            # fetch.py --force intentionally replaces an original.  Rebuild
            # only that document's generated view and conservative #all
            # clause, so its checksums and citations cannot refer to stale
            # content.  Normal reviewed documents remain untouched.
            raw_row.update({'sha256': raw_hash, 'bytes': str(raw.stat().st_size)})
            clauses[:] = [clause for clause in clauses if clause['doc_id'] != doc['id']]
            known_docs.discard(doc['id'])
            changed = True
        if doc['id'] in known_docs:
            continue
        suffix = raw.suffix.lower()
        if suffix in {'.html', '.htm', '.xml'}:
            from bs4 import BeautifulSoup
            text = BeautifulSoup(raw.read_bytes(), 'lxml').get_text('\n')
        elif suffix == '.pdf':
            import fitz
            text = '\n'.join(page.get_text() for page in fitz.open(raw))
            # Use OCR only for an image-only PDF. The original object is
            # preserved; the generated text remains subject to all ordinary
            # hash, citation and coverage checks.
            if not text.strip():
                with tempfile.TemporaryDirectory(prefix='database-ocr-') as temporary:
                    prefix = Path(temporary) / 'page'
                    rendered = subprocess.run(
                        ['pdftoppm', '-r', '200', '-png', str(raw), str(prefix)],
                        text=True, capture_output=True,
                    )
                    if rendered.returncode:
                        raise ValueError(f'doc {doc["id"]}: PDF rendering for OCR failed: {rendered.stderr.strip()}')
                    images = sorted(Path(temporary).glob('page-*.png'))
                    if not images:
                        raise ValueError(f'doc {doc["id"]}: PDF rendering for OCR produced no pages')
                    def ocr(image):
                        recognised = subprocess.run(
                            ['tesseract', str(image), 'stdout', '-l', 'eng'],
                            text=True, capture_output=True,
                        )
                        if recognised.returncode:
                            raise ValueError(f'doc {doc["id"]}: OCR failed for {image.name}: {recognised.stderr.strip()}')
                        return recognised.stdout
                    with ThreadPoolExecutor(max_workers=4) as workers:
                        pages = list(workers.map(ocr, images))
                    text = '\n\f\n'.join(pages)
        else:
            text = raw.read_text(encoding='utf-8', errors='replace')
            if suffix == '.rtf': text = re.sub(r'\\[a-z]+-?\d* ?', ' ', text).replace('{', ' ').replace('}', ' ')
        text = html.unescape(text).strip()
        if not text: raise ValueError(f'doc {doc["id"]}: no extractable text')
        text_path = DATA / 'text' / (doc['id'] + '.txt')
        relative = str(text_path.relative_to(DATA))
        text_row = next((row for row in file_rows if row['path'] == relative), None)
        if text_row is None or source_changed:
            text_path.parent.mkdir(parents=True, exist_ok=True)
            text_path.write_text(text + '\n', encoding='utf-8')
            metadata = {'path': relative, 'sha256': sha256(text_path), 'bytes': str(text_path.stat().st_size)}
            if text_row is None:
                file_rows.append(metadata)
                indexed.add(relative)
            else:
                text_row.update(metadata)
        clauses.append({'cite_id': doc['id'] + '#all', 'doc_id': doc['id'], 'label': 'Whole document', 'text': text})
        known_docs.add(doc['id']); changed = True
    if changed:
        write_rows('files', file_rows)
        write_rows('clause', clauses)


def audit(jur: str | None = None):
    data = {name: rows(name) for name in TABLES}
    codes = {r['code'] for r in data['jurisdiction']}
    errors, gaps, warnings = [], [], []
    def error(message): errors.append(message)
    selected = set(codes) if jur is None else {jur}
    if not selected <= codes:
        return [f'error: unknown jurisdiction {jur}'], [], []
    doc_ids = set()
    for r in data['doc']:
        if r['id'] in doc_ids: error(f'doc {r["id"]}: duplicate id')
        doc_ids.add(r['id'])
        if r['type'] not in TYPES: error(f'doc {r["id"]}: type {r["type"]!r} invalid')
        if not r['lang']: error(f'doc {r["id"]}: lang empty')
        if not is_date(r['effective_from']) or not is_date(r['effective_to']): error(f'doc {r["id"]}: date invalid')
        if not official_host(r['url']): error(f'doc {r["id"]}: URL is not an approved official host')
        if r['type'] == 'treaty':
            if r['jur'] == 'intl':
                if not r['id'].startswith('intl.'):
                    error(f'doc {r["id"]}: international treaty id must start intl.')
            else:
                if not is_pair(r['jur'], codes): error(f'doc {r["id"]}: treaty jur must be an alphabetical pair')
                if not r['id'].startswith('treaty.'):
                    error(f'doc {r["id"]}: treaty id must start treaty.')
        elif r['jur'] != 'intl' and r['jur'] not in codes: error(f'doc {r["id"]}: unknown jur')
        for category in filter(None, r['category'].split(';')):
            if category not in CATEGORIES: error(f'doc {r["id"]}: invalid category {category}')
        path = DATA / r['file']
        if not path.is_file(): error(f'doc {r["id"]}: file missing')
        elif sha256(path) != r['sha256']: error(f'doc {r["id"]}: sha256 differs')
    file_paths = set()
    for r in data['files']:
        path = DATA / r['path']
        if r['path'] in file_paths: error(f'files {r["path"]}: duplicate path')
        file_paths.add(r['path'])
        if not path.is_file(): error(f'files {r["path"]}: file missing')
        elif path.stat().st_size != int(r['bytes']) or sha256(path) != r['sha256']: error(f'files {r["path"]}: checksum differs')
    clauses = {}
    for r in data['clause']:
        if r['cite_id'] in clauses: error(f'clause {r["cite_id"]}: duplicate cite_id')
        clauses[r['cite_id']] = r
        if r['doc_id'] not in doc_ids: error(f'clause {r["cite_id"]}: doc_id missing')
        if not r['cite_id'].startswith(r['doc_id'] + '#'): error(f'clause {r["cite_id"]}: cite_id/doc mismatch')
    currencies = {r['currency'] for r in data['jurisdiction']}
    for table, key in [('param', 'param_id'), ('decision', 'id')]:
        seen = set()
        for r in data[table]:
            if r[key] in seen: error(f'{table} {r[key]}: duplicate id')
            seen.add(r[key])
            cite, quote = r['cite_id'], r['quote']
            if cite:
                if cite not in clauses: error(f'{table} {r[key]}: cite_id not found')
                elif whitespace_normalized(quote) not in whitespace_normalized(clauses[cite]['text']): error(f'{table} {r[key]}: quote not found verbatim')
                elif quote not in clauses[cite]['text']: warnings.append(f'{table} {r[key]}: quote differs only by whitespace')
            if table == 'param':
                if r['scope'] not in codes and not is_pair(r['scope'], codes): error(f'param {r[key]}: invalid scope')
                if r['subject'] not in SUBJECTS or r['slot'] not in SLOTS: error(f'param {r[key]}: invalid subject or slot')
                if r['unit'] not in UNITS | currencies: error(f'param {r[key]}: invalid unit')
                if not re.fullmatch(r'[a-z0-9_.-]+', r['param_id']): error(f'param {r[key]}: param_id invalid')
                if not is_date(r['effective_from']) or not is_date(r['effective_to']): error(f'param {r[key]}: date invalid')
                if not cite: error(f'param {r[key]}: cite_id required')
            else:
                cat, subject, slot = r['category'], r['subject'], r['slot']
                if r['jur'] not in codes: error(f'decision {r[key]}: jur invalid')
                if bool(cat) == bool(subject or slot): error(f'decision {r[key]}: choose category or subject+slot')
                if cat and cat not in CATEGORIES: error(f'decision {r[key]}: category invalid')
                if (subject not in SUBJECTS or slot not in SLOTS) and not cat: error(f'decision {r[key]}: subject/slot invalid')
                if (cat in {'1','2','3','4','9'} or slot) and not cite: error(f'decision {r[key]}: cited evidence required')
    pairs = set()
    for r in data['treaty']:
        if r['pair'] in pairs: error(f'treaty {r["pair"]}: duplicate pair')
        pairs.add(r['pair'])
        if not is_pair(r['pair'], codes): error(f'treaty {r["pair"]}: pair not alphabetical')
        for field in ('doc_id', 'mli_doc_id'):
            if r[field] and r[field] not in doc_ids: error(f'treaty {r["pair"]}: {field} does not exist')
        if not is_date(r['in_force_from']): error(f'treaty {r["pair"]}: date invalid')
    for code in sorted(selected):
        categories = {c for r in data['doc'] if r['jur'] == code for c in r['category'].split(';') if c}
        categories |= {r['category'] for r in data['decision'] if r['jur'] == code and r['category']}
        for category in sorted(CATEGORIES - categories): gaps.append(f'gap: category {code}|{category}')
        scope_params = [r for r in data['param'] if r['scope'] == code]
        for jr in data['jurisdiction']:
            if jr['code'] != code: continue
            for subject in ('company', 'individual'):
                if jr[subject + '_in_scope'] != 'yes': continue
                for slot in sorted(SLOTS):
                    has_param = any(r['subject'] in {subject, 'all'} and r['slot'] == slot for r in scope_params)
                    absent = any(r['jur'] == code and not r['category'] and r['subject'] in {subject, 'all'} and r['slot'] == slot for r in data['decision'])
                    if not has_param and not absent: gaps.append(f'gap: slot {code}|{subject}|{slot} without a parameter or absence record')
        for other in sorted(codes):
            pair = '-'.join(sorted((code, other)))
            if code < other and pair not in pairs: gaps.append(f'gap: pair {pair} without a treaty row')
    return errors, gaps, warnings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--jur')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    if not args.jur:
        materialize_new_documents()
    errors, gaps, warnings = audit(args.jur)
    report = {'jurisdiction': args.jur or 'all', 'errors': errors, 'gaps': gaps, 'warnings': warnings}
    if not args.jur:
        codes = {r['code'] for r in rows('jurisdiction')}
        # The source package did not include the original slicers. Preserve the
        # downloaded, hash-verified generated CSVs and materialise a queryable
        # SQLite view of them. Validation is still performed from CSV sources.
        db_path = DATA / 'database.sqlite'
        connection = sqlite3.connect(db_path)
        try:
            for table, fields in TABLES.items():
                connection.execute(f'DROP TABLE IF EXISTS "{table}"')
                connection.execute('CREATE TABLE "' + table + '" (' + ', '.join('"' + field + '" TEXT' for field in fields) + ')')
                values = [[r[field] for field in fields] for r in rows(table)]
                connection.executemany('INSERT INTO "' + table + '" VALUES (' + ', '.join('?' for _ in fields) + ')', values)
            connection.commit()
        finally:
            connection.close()
        by_jur = {code: {'categories': 0, 'slots': 0, 'pairs': 0} for code in codes}
        for gap in gaps:
            kind, target = gap.split(': ', 1)[1].split(' ', 1)
            code = target.split('-', 1)[0] if kind == 'pair' else target.split('|', 1)[0]
            if code in by_jur:
                by_jur[code][{'category': 'categories', 'slot': 'slots', 'pair': 'pairs'}[kind]] += 1
        status = ['# Database build status', '',
                  f'- Errors: {len(errors)}', f'- Coverage gaps: {len(gaps)}', f'- Warnings: {len(warnings)}',
                  f'- SQLite snapshot: {db_path.name}', '',
                  '| Region | Category gaps | Slot gaps | Owned-pair gaps |', '|---|---:|---:|---:|']
        status.extend(f'| {code} | {counts["categories"]} | {counts["slots"]} | {counts["pairs"]} |' for code, counts in sorted(by_jur.items()))
        status.extend(['', '## Errors', '', *(errors or ['none']), '', '## Gaps', '', *(gaps or ['none']), '', '## Warnings', '', *(warnings or ['none']), ''])
        (DATA / 'STATUS.md').write_text('\n'.join(status), encoding='utf-8')
    if args.json: print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for line in errors + gaps + warnings: print(line)
        print('PASSED' if not errors and not gaps else f'NOT PASSED: {len(errors)} errors, {len(gaps)} gaps')
    raise SystemExit(0 if not errors and not gaps else 1)


if __name__ == '__main__': main()
