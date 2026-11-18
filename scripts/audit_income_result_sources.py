"""Audit source provenance observed during income/report tests; run from repository root.

Usage: python scripts/audit_income_result_sources.py --output PATH
This proves only executed assessment outputs, not legal or business completeness.
"""
import argparse
import sys,json,hashlib
from pathlib import Path
import pytest
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
ROOT=Path(__file__).resolve().parents[1]
if Path.cwd().resolve()!=ROOT:parser.error('Run from repository root')
sys.path.insert(0,str(ROOT))
from packages.income_tax import assessment
original=assessment.calculate
records={};policies=set();calls=0
def walk(value,path,policy):
 if isinstance(value,dict):
  if 'url' in value and any(k in value for k in ('sha256','doc_id','title')):
   key=json.dumps(value,sort_keys=True,default=str)
   if key not in records:
    entry={'source':value,'paths':set(),'policies':set(),'problems':[]}
    file=value.get('file');digest=value.get('sha256')
    resolved=ROOT/file if file else None
    if file and file.startswith('raw/'):
     resolved=ROOT/'database'/file
    if not file:entry['problems'].append('missing_file')
    elif not resolved.is_file():entry['problems'].append('file_not_found')
    elif not digest:entry['problems'].append('missing_sha256')
    elif hashlib.sha256(resolved.read_bytes()).hexdigest()!=digest:entry['problems'].append('hash_mismatch')
    records[key]=entry
   records[key]['paths'].add(path);records[key]['policies'].add(policy)
  for k,v in value.items():walk(v,path+'.'+str(k),policy)
 elif isinstance(value,list):
  for v in value:walk(v,path+'[]',policy)
def wrapped(*args,**kwargs):
 global calls
 result=original(*args,**kwargs);calls+=1
 basis=args[1] if len(args)>1 else kwargs.get('basis')
 policy=getattr(basis,'policy',None) or (basis.get('policy') if isinstance(basis,dict) else 'unknown')
 policies.add(policy);walk(result,'result',policy);return result
assessment.calculate=wrapped
code=pytest.main(['tests/income_tax','tests/reporting','-q'])
for entry in records.values():
 entry['paths']=sorted(entry['paths']);entry['policies']=sorted(entry['policies'])
out={'pytest_exit':code,'successful_calls':calls,'policies':sorted(policies),'unique_source_records':len(records),'unresolved':[v for v in records.values() if v['problems']],'records':list(records.values())}
out['scope']='Only sources observed in successful assessment.calculate calls during these tests; not legal or complete business acceptance.'
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
print(json.dumps({k:v for k,v in out.items() if k not in ('records','unresolved')}));print('unresolved',len(out['unresolved']))
sys.exit(code or (1 if out['unresolved'] or not calls or not records else 0))
