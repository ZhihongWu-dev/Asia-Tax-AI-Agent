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
