"""Run rule builder in isolation because its CLI uses top-level module imports."""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]


def test_failed_rule_write_and_replace_preserve_published_database(tmp_path):
    script = r'''
import runpy,sys,sqlite3
from pathlib import Path
from unittest.mock import patch
b=runpy.run_path('rule/tools/build.py')
root=Path(sys.argv[1]);tables={name:[] for name in b['TABLES']}
write=b['write_sqlite'];write(root,tables)
before=(root/'rule.sqlite').read_bytes()
class Invalid:
    def __str__(self): raise ValueError('invalid cell')
broken={**tables,'rule':[{'rule_id':Invalid()}]}
try: write(root,broken)
except ValueError: pass
else: raise AssertionError('expected write failure')
assert (root/'rule.sqlite').read_bytes()==before
with patch('os.replace',side_effect=PermissionError('in use')):
    try: write(root,tables)
    except PermissionError: pass
    else: raise AssertionError('expected replacement failure')
assert (root/'rule.sqlite').read_bytes()==before
assert not list(root.glob('.rule-*'))
with sqlite3.connect(root/'rule.sqlite') as c:
    assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
'''
    result=subprocess.run([sys.executable,'-X','utf8','-c',script,str(tmp_path)],cwd=ROOT,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr


def test_invalid_rule_build_writes_diagnostics_but_keeps_old_database(tmp_path):
    import csv
    import shutil
    for path in (ROOT/'rule').glob('*.csv'):
        shutil.copyfile(path,tmp_path/path.name)
    path=tmp_path/'rule.csv'
    with path.open(encoding='utf-8-sig',newline='') as stream: rows=list(csv.DictReader(stream))
    rows[0]['condition']='THIS IS NOT A VALID CONDITION !!!'
    with path.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
    target=tmp_path/'rule.sqlite';target.write_bytes(b'previous published artifact')
    result=subprocess.run([sys.executable,'-X','utf8','rule/tools/build.py','--root',str(tmp_path),'--db',str(ROOT/'database')],
                          cwd=ROOT,capture_output=True,text=True,timeout=60)
    assert result.returncode==1,result.stdout+result.stderr
    assert target.read_bytes()==b'previous published artifact'
    assert (tmp_path/'STATUS.md').exists()
