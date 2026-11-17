"""Li CLI module imports run in subprocess isolation."""
from pathlib import Path
import subprocess
import sys


def test_optimizer_uses_one_explicit_library_without_default_fallback():
    script = r'''
import sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'optimization/tools'))
import optimize as op
import rule_tool
import query
import eval as ev
from common import Library
class Pinned(Library):
    def __bool__(self):return False
    def version_metadata(self):return {'snapshot_sha256':'verified-test-snapshot'}
lib=Pinned(Path('database'))
def forbidden(*args,**kwargs):raise AssertionError('default library accessed')
rule_tool.Library=forbidden
ev.Library=forbidden
inp=op.jload('optimization/examples/case_jp_sg_individual.json')
opt=op.Optimizer(inp,lib=lib)
assert opt.lib is lib and opt.q.lib is lib and opt.tool.lib is lib and opt.rs.lib is lib
version=opt.q.version()['database']
assert version['snapshot_sha256']=='verified-test-snapshot'
assert 'doc_csv_sha256' not in version
lib.version_metadata=lambda: {}
try:opt.q.version()
except ValueError:pass
else:raise AssertionError('empty snapshot version accepted')
lib.version_metadata=None
try:opt.q.version()
except ValueError:pass
else:raise AssertionError('missing version provider accepted')
print('Explicit library identity and fail-closed version verified')
'''
    r=subprocess.run([sys.executable,'-X','utf8','-c',script],cwd=Path(__file__).resolve().parents[2],capture_output=True,text=True,timeout=60)
    assert r.returncode==0,r.stdout+r.stderr


def test_checker_preserves_injected_library(tmp_path):
    script = r'''
import sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'optimization/tools'))
import optimize as op
from check import Checker
from common import Library
import rule_tool
import eval as ev
class Pinned(Library):
    def version_metadata(self):return {'snapshot_sha256':'checker-test-snapshot'}
lib=Pinned(Path('database'))
def forbidden(*args,**kwargs):raise AssertionError('default library accessed')
rule_tool.Library=forbidden
ev.Library=forbidden
inp=op.jload('optimization/examples/case_jp_sg_individual.json')
inp['constraints']['consider']=['jp','sg']
out=Path(sys.argv[1])/'products'
op.Optimizer(inp,lib=lib).run(out)
checker=Checker(out,lib=lib)
assert checker.opt.lib is lib
checker.version_hash()
assert not checker.fails,checker.fails
lib.version_metadata=lambda: {'snapshot_sha256':'changed'}
checker.version_hash()
assert any('database_version' in failure for failure in checker.fails)
'''
    r=subprocess.run([sys.executable,'-X','utf8','-c',script,str(tmp_path)],
                     cwd=Path(__file__).resolve().parents[2],capture_output=True,text=True,timeout=180)
    assert r.returncode==0,r.stdout+r.stderr


def test_real_catalog_bundle_runs_optimizer_and_checker(tmp_path):
    # Local fixture proves interface compatibility, not cloud source admission.
    script = r'''
import sys
from pathlib import Path
from hashlib import sha256
sys.path.insert(0,str(Path.cwd()/'optimization/tools'))
import optimize as op
from check import Checker
from common import read_csv
from packages.domain_bridge.planning_library import PlanningLibrary,digest
import rule_tool
import eval as ev
tables={name:read_csv(Path('database')/(name+'.csv'))
        for name in ('jurisdiction','doc','param','treaty','decision')}
sources={r['cite_id']:{'cite_id':r['cite_id'],'passage':r['text'],'label':r['label'],
         'passage_sha256':sha256(r['text'].encode('utf-8')).hexdigest()}
         for r in read_csv('database/clause.csv')}
pin={'fixture':'local-catalog-compatibility-only'}
bundle={'library_version':pin,'tables':tables,'sources':sources,
        'table_sha256':{name:digest(rows) for name,rows in tables.items()}}
bundle['bundle_sha256']=digest(bundle)
lib=PlanningLibrary(bundle,expected_version=pin)
def forbidden(*args,**kwargs):raise AssertionError('default library accessed')
rule_tool.Library=forbidden
ev.Library=forbidden
inp=op.jload('optimization/examples/case_jp_sg_individual.json')
inp['constraints']['consider']=['jp','sg']
out=Path(sys.argv[1])/'products'
op.Optimizer(inp,lib=lib).run(out)
checker=Checker(out,lib=lib)
checker.version_hash()
assert not checker.fails,checker.fails
assert checker.version['database_version']['bundle_sha256']==bundle['bundle_sha256']
assert checker.version['database_version']['library_version']==pin
from packages.domain_bridge.planning_runner import run
result=run(inp,bundle,expected_version=pin,output=Path(sys.argv[1])/'runner-products')
assert result['checks']['status']=='passed'
assert result['artifacts']['tax.json']['bytes'] > 0
assert result['version']['database_version']['bundle_sha256']==bundle['bundle_sha256']
'''
    r=subprocess.run([sys.executable,'-X','utf8','-c',script,str(tmp_path)],
                     cwd=Path(__file__).resolve().parents[2],capture_output=True,text=True,timeout=180)
    assert r.returncode==0,r.stdout+r.stderr
