"""Compare optimized and legacy absence selection through the real optimizer."""
from pathlib import Path
import subprocess
import sys


def test_optimizer_absence_lookup_matches_legacy_order_and_fallback():
    script = r'''
import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path.cwd()/'optimization/tools'))
import optimize as op
from packages.domain_bridge.planning_library import PlanningLibrary,digest
from hashlib import sha256
from itertools import permutations,product
rows=[dict(id='all',jur='cn',subject='all',slot='cfc',cite_id='cn.law#1',statement='all first'),
      dict(id='company',jur='cn',subject='company',slot='cfc',cite_id='cn.law#1',statement='company first'),
      dict(id='other',jur='sg',subject='individual',slot='exit',cite_id='cn.law#1',statement='other')]
for order in permutations(rows):
    tables={'jurisdiction':[{'code':'cn'},{'code':'sg'}],'doc':[],'param':[],'treaty':[],'decision':list(order)}
    pin={'uploaded_at':'test'}
    bundle={'library_version':pin,'tables':tables,'table_sha256':{k:digest(v) for k,v in tables.items()},
            'sources':{'cn.law#1':{'cite_id':'cn.law#1','passage':'law','passage_sha256':sha256(b'law').hexdigest()}}}
    bundle['bundle_sha256']=digest(bundle)
    lib=PlanningLibrary(bundle,expected_version=pin)
    fast=op.Optimizer.__new__(op.Optimizer);fast.lib=lib
    legacy=op.Optimizer.__new__(op.Optimizer);legacy.lib=SimpleNamespace(absences=list(order))
    for query in product(['cn','sg','missing'],['company','individual','all'],['cfc','exit','missing']):
        expected=legacy.absence(*query)
        assert fast.absence(*query)==expected,(order,query)
        if expected is not None:
            changed=fast.absence(*query);changed['statement']='caller mutation'
            assert fast.absence(*query)==expected
'''
    result = subprocess.run([sys.executable, '-X', 'utf8', '-c', script],
        cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
