import ast
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def actual_function(relative, name):
    tree = ast.parse((ROOT / relative).read_text(encoding='utf-8-sig'))
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
    namespace = {}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), relative, 'exec'), namespace)
    return namespace[name]


@pytest.mark.parametrize('day, expected', [('2014-12-23',False),('2014-12-24',True),
    ('2024-12-31',True),('2025-01-01',False),('2026-11-18',False)])
def test_historical_source_and_parameter_share_business_boundary(day, expected):
    candidates = json.loads((ROOT / 'config/library/main-only-candidates.json').read_text(encoding='utf-8'))
    doc = next(r['document'] for r in candidates['records'] if r['cite_id']=='id.pmk242-2014#2(7)')
    audit = json.loads((ROOT / 'docs/project/data-reconciliation/indonesia-historical-payment-source-20261118.json').read_text(encoding='utf-8'))
    param = audit['after_parameter']
    law_keep = actual_function('agent/tools/read_core.py','law_keep')
    in_window = actual_function('rule/tools/common.py','in_window')
    metadata = dict(jur=doc['jur'],doc_id=doc['id'],lang=doc['lang'],
                    valid_from=doc['effective_from'],valid_to=doc['effective_to'])
    assert law_keep(None, metadata, {'as_of':day}) is expected
    assert in_window(day,param['effective_from'],param['effective_to']) is expected
