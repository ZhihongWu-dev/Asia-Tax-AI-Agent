"""Regression checks run in isolation because Li's CLI imports generic module names."""
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def test_input_identity_and_stale_product_detection(tmp_path):
    script = r'''
import copy, json, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()/'optimization/tools'))
import optimize as op
from check import Checker
inp = op.jload('optimization/examples/case_jp_sg_individual.json')
# This regression concerns identity and artifact validation. Keep its real
# cross-border search bounded; the complete CSV golden suite runs separately.
inp['constraints']['consider'] = ['jp', 'sg']
opt = op.Optimizer(copy.deepcopy(inp))
base = opt.version()
assert len(base['inputs_sha256']) == 64
assert base['version_schema'] == 2
for key, value in [('amount', inp['amount']+1), ('currency', 'USD'),
                   ('past_payments', [{'date':'2025-12-25','payee_share':1000,'withheld':100}])]:
    changed = copy.deepcopy(inp)
    changed[key] = value
    assert op.Optimizer(changed).version()['inputs_sha256'] != base['inputs_sha256'], key
assert op.Optimizer(dict(reversed(list(inp.items())))).version()['inputs_sha256'] == base['inputs_sha256']
out = Path(sys.argv[1])/'products'
opt.run(out)
checker = Checker(out)
checker.version_hash()
assert not checker.fails, checker.fails
for field in ('version_schema', 'rule_version', 'database_version', 'engine_sha256'):
    checker = Checker(out)
    checker.version[field] = 'stale'
    checker.version_hash()
    assert any(field in failure for failure in checker.fails), field
saved = op.jload(out/'input.json')
saved['amount'] += 1
op.jdump(saved, out/'input.json')
checker = Checker(out)
checker.version_hash()
assert any('version hash' in failure for failure in checker.fails), checker.fails
print('input identity and stale artifacts verified')
'''
    result = subprocess.run([sys.executable, '-X', 'utf8', '-c', script, str(tmp_path)],
                            cwd=ROOT, capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
