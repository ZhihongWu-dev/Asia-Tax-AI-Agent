"""Search the validated clause catalogue without modifying it."""
from __future__ import annotations
import argparse
from common import rows

parser = argparse.ArgumentParser()
parser.add_argument('terms', nargs='*')
parser.add_argument('--jur')
parser.add_argument('--cite')
args = parser.parse_args()
docs = {r['id']: r for r in rows('doc')}
clauses = rows('clause')
if args.cite:
    found = [r for r in clauses if r['cite_id'] == args.cite]
    if not found: parser.error('cite_id not found')
    print(found[0]['text'])
elif not args.terms:
    parser.error('provide terms or --cite')
else:
    for clause in clauses:
        document = docs.get(clause['doc_id'], {})
        if args.jur and document.get('jur') != args.jur: continue
        text = clause['text']
        if all(term.casefold() in text.casefold() for term in args.terms):
            print(f'{clause["cite_id"]}\t{clause["label"]}\t{text}')
