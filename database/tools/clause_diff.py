"""Track clause identifiers before and after a slicer change."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from common import DATA, rows

parser = argparse.ArgumentParser()
parser.add_argument('--save', action='store_true')
args = parser.parse_args()
snapshot = DATA / '.clause_ids.before.json'
current = sorted(r['cite_id'] for r in rows('clause'))
if args.save:
    snapshot.write_text(json.dumps(current, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Saved {len(current)} clause identifiers.')
elif not snapshot.exists():
    parser.error('run with --save before changing a slicer')
else:
    before = set(json.loads(snapshot.read_text(encoding='utf-8')))
    after = set(current)
    print('Removed:', *sorted(before - after), sep='\n')
    print('Added:', *sorted(after - before), sep='\n')
    cited = {r['cite_id'] for t in ('param', 'decision') for r in rows(t) if r['cite_id']}
    lost = sorted(cited & (before - after))
    if lost:
        print('ERROR: records still cite removed identifiers:', *lost, sep='\n')
        raise SystemExit(1)
