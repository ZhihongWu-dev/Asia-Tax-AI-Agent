"""Exercise actual optimizer output, in isolation from CLI module imports."""
from pathlib import Path
import subprocess
import sys


def test_zero_amount_is_preserved_and_invalid_amounts_rejected(tmp_path):
    script = r'''
import copy,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'optimization/tools'))
import optimize as op
from check import Checker
inp=op.jload('optimization/examples/case_jp_sg_individual.json')
inp['constraints']['consider']=['jp','sg']
for invalid in (None,False,True,'0','100',-1,float('nan'),float('inf'),-float('inf'),10**400):
    case=copy.deepcopy(inp)
    case['amount']=invalid
    try: op.Optimizer(case)
    except ValueError as exc: assert 'amount' in str(exc)
    else: raise AssertionError('invalid amount accepted: '+repr(invalid))
missing=copy.deepcopy(inp)
missing.pop('amount')
assert op.Optimizer(missing).amount==100
inp['amount']=0
opt=op.Optimizer(inp)
assert opt.amount==0
out=Path(sys.argv[1])/'zero-products'
opt.run(out)
tax=op.jload(out/'tax.json')
assert tax['amount']==0
assert tax['taxes']
for item in tax['taxes']:
    assert all(value is None or value==0 for value in item['amount'].values()),item
checker=Checker(out)
assert not checker.run_all(),checker.fails
'''
    result=subprocess.run([sys.executable,'-X','utf8','-c',script,str(tmp_path)],
                          cwd=Path(__file__).resolve().parents[2],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+result.stderr
