"""Read-only cloud retrieval checks; no model calls or source writes."""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from packages.chat.knowledge import search


def evaluate(case):
    start = time.perf_counter()
    result = search(case['query'])
    passages = result['passages']
    missing = {}
    for expected, actual in [('expected_locators', 'locator'), ('expected_units', 'unit_id'), ('expected_sources', 'source_id')]:
        absent = sorted(set(case.get(expected, [])) - {p.get(actual) for p in passages})
        if absent:
            missing[expected] = absent
    passed = result['status'] != 'unavailable' and not missing
    if case.get('expect_empty'):
        passed = result['status'] == 'no_matching_units' and not passages
    unique = len({p['unit_id'] for p in passages}) == len(passages)
    return {'id': case['id'], 'query': case['query'], 'passed': passed and unique,
            'status': result['status'], 'seconds': round(time.perf_counter() - start, 3),
            'missing': missing, 'unique': unique,
            'units': [p['unit_id'] for p in passages], 'locators': [p['locator'] for p in passages]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    dataset = json.loads((ROOT / 'tests/chat/retrieval_cases.json').read_text(encoding='utf-8'))
    rows = []
    for case in dataset['cases']:
        row = evaluate(case)
        rows.append(row)
        print(row['id'], 'PASS' if row['passed'] else 'FAIL', row['status'], flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'at': datetime.now(timezone.utc).isoformat(),
        'scope': dataset['description'], 'passed': sum(r['passed'] for r in rows),
        'total': len(rows), 'results': rows}, ensure_ascii=False, indent=2), encoding='utf-8')
    sys.exit(0 if all(r['passed'] for r in rows) else 1)
