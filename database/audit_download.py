"""Preliminary checks of the downloaded snapshot; not the prescribed build acceptance.

This never edits the database directory or connects to a remote service.
"""
import csv
import hashlib
import itertools
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'database'
REPORTS = ROOT / '_extension_audit'
TABLES = ('jurisdiction', 'doc', 'files', 'clause', 'param', 'decision', 'treaty')
CATEGORIES = [str(n) for n in range(1, 10)] + ['page_treaties', 'page_rates', 'page_deadlines']
SLOTS = ('outbound_wht', 'inbound', 'final', 'residence', 'cfc', 'anti_abuse')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    csv.field_size_limit(sys.maxsize)
    tables = {}
    for name in TABLES:
        with (DATA / (name + '.csv')).open(encoding='utf-8-sig', newline='') as stream:
            tables[name] = list(csv.DictReader(stream))
    findings = []
    def issue(kind, target, detail):
        findings.append({'kind': kind, 'target': target, 'detail': detail})
    clauses = {r['cite_id']: r for r in tables['clause']}
    docs = {r['id']: r for r in tables['doc']}
    verified = 0
    for row in tables['files']:
        path = DATA / row['path']
        if not path.resolve().is_relative_to(DATA.resolve()):
            issue('unsafe_path', row['path'], 'Path escapes database directory')
        elif not path.is_file():
            issue('file_missing', row['path'], 'Indexed file is missing')
        elif path.stat().st_size != int(row['bytes']) or digest(path) != row['sha256']:
            issue('file_changed', row['path'], 'Size or SHA-256 mismatch')
        else:
            verified += 1
    for row in tables['doc']:
        path = DATA / row['file']
        if not path.resolve().is_relative_to(DATA.resolve()):
            issue('unsafe_path', row['id'], 'Document path escapes database directory')
        elif not path.is_file() or digest(path) != row['sha256']:
            issue('document_changed', row['id'], 'Original missing or SHA-256 mismatch')
    for name, key in [('param', 'param_id'), ('decision', 'id')]:
        for row in tables[name]:
            cite = row['cite_id']
            if cite and cite not in clauses:
                issue('citation_missing', row[key], cite)
            elif cite and row['quote'] not in clauses[cite]['text']:
                normalize = lambda s: re.sub(r'\s+', '', s)
                kind = ('quote_whitespace_difference' if normalize(row['quote']) in normalize(clauses[cite]['text'])
                        else 'quote_content_difference')
                issue(kind, row[key], cite)
            elif name == 'param' and not cite:
                issue('citation_missing', row[key], 'Parameter has no cite_id')
    pairs = {r['pair']: r for r in tables['treaty']}
    for row in tables['treaty']:
        for key in ('doc_id', 'mli_doc_id'):
            if row[key] and row[key] not in docs:
                issue('treaty_document_missing', row['pair'], row[key])
    coverage = []
    codes = sorted(r['code'] for r in tables['jurisdiction'])
    for jur in tables['jurisdiction']:
        code = jur['code']
        present = {c for r in tables['doc'] if r['jur'] == code for c in r['category'].split(';')}
        present.update(r['category'] for r in tables['decision'] if r['jur'] == code and r['category'])
        missing_slots = []
        for subject in ('company', 'individual'):
            if jur[subject + '_in_scope'] != 'yes':
                continue
            for slot in SLOTS:
                has_param = any(r['scope'] == code and r['subject'] in (subject, 'all') and r['slot'] == slot for r in tables['param'])
                has_absence = any(r['jur'] == code and not r['category'] and r['subject'] in (subject, 'all') and r['slot'] == slot for r in tables['decision'])
                if not has_param and not has_absence:
                    missing_slots.append(subject + '|' + slot)
        coverage.append({'jur': code, 'documents': sum(r['jur'] == code for r in tables['doc']),
                         'parameters': sum(r['scope'] == code for r in tables['param']),
                         'missing_categories': [c for c in CATEGORIES if c not in present],
                         'missing_slots': missing_slots,
                         'missing_owned_pairs': [code + '-' + other for other in codes if other > code and code + '-' + other not in pairs]})
    expected_pairs = ['-'.join(p) for p in itertools.combinations(codes, 2)]
    required = ['tools/build.py', 'tools/fetch.py', 'tools/find.py', 'tools/clause_diff.py',
                'tools/upload.py', 'samples/slicers-2026-10-23/run_slicers.py', 'superseded.csv']
    missing_tools = [p for p in required if not (DATA / p).is_file()]
    report = {'created_at': datetime.now(timezone.utc).isoformat(),
              'acceptance': 'NOT RUN: original prescribed tools are missing',
              'scope': 'Preliminary snapshot integrity and coverage checks only; not legal validation or build.py acceptance.',
              'table_rows': {k: len(v) for k, v in tables.items()},
              'indexed_files_verified': verified, 'findings': findings,
              'missing_required_files': missing_tools, 'coverage': coverage,
              'expected_pairs': len(expected_pairs), 'registered_pairs': len(pairs),
              'missing_pairs': [p for p in expected_pairs if p not in pairs]}
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / 'baseline.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = ['# Preliminary extension baseline', '',
             'Acceptance: NOT RUN. The original prescribed collection/build tools and superseded.csv are missing.', '',
             'These checks are supplementary and do not replace the checks in spec.zh.md sections 4.9 and 5.', '',
             '## Existing data', '',
             *[f'- {name}: {len(rows)} rows' for name, rows in tables.items()],
             f'- Indexed files verified: {verified}/{len(tables["files"])}',
             f'- Findings: {len(findings)}', '', '## Coverage gaps', '',
             '| Region | Documents | Domestic parameters | Missing categories | Missing subject/slot cells | Missing owned pairs |',
             '|---|---:|---:|---|---:|---:|']
    for r in coverage:
        lines.append(f'| {r["jur"]} | {r["documents"]} | {r["parameters"]} | {", ".join(r["missing_categories"]) or "none"} | {len(r["missing_slots"])} | {len(r["missing_owned_pairs"])} |')
    lines.extend(['', '## Required source files', '', *['- database/' + p for p in missing_tools], '',
                  '## Original-tool discovery', '',
                  'All 11 visible branches of ZhihongWu-dev/Asia-Tax-AI-Agent were checked. None contains database/, clause_diff.py, or the required slicer sample runner.',
                  'Local official/tools/build.py belongs to a different data package and has not been substituted.', '',
                  '## Next action', '',
                  'Obtain the matching source database/ package, including tools/, samples/, superseded.csv, blocked.csv and session_log.md if present. Preserve the existing downloaded rows when merging. Run the original baseline build and per-region acceptance before collecting missing data.', '',
                  'No business data or remote data was changed. See baseline.json for each missing slot and pair.', ''])
    (REPORTS / 'BASELINE.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('table_rows', 'indexed_files_verified', 'registered_pairs', 'expected_pairs', 'missing_required_files')}, ensure_ascii=False))
    print('Findings:', json.dumps(dict(Counter(r['kind'] for r in findings))))
    for r in coverage:
        print(r['jur'], 'missing categories:', len(r['missing_categories']), 'slots:', len(r['missing_slots']), 'pairs:', len(r['missing_owned_pairs']))


if __name__ == '__main__':
    main()
