import json
from pathlib import Path
import shutil
import subprocess
import sys
import pytest
from agent.tools import make_agents

ROOT=Path(__file__).resolve().parents[2]


def checkout(tmp_path):
    folder=tmp_path/'agent'
    folder.mkdir()
    shutil.copyfile(ROOT/'agent/mcp_servers.json',folder/'mcp_servers.json')
    for spec in make_agents.SPECS.values():
        shutil.copyfile(ROOT/'agent'/spec,folder/spec)
    return tmp_path


def test_fresh_checkout_generates_role_bound_portable_configs(tmp_path):
    project=checkout(tmp_path)
    bundle=make_agents.generate(project)
    assert set(bundle)=={'front','analysis','review'}
    for role in bundle:
        servers=json.loads((project/'.claude/mcp'/f'{role}.json').read_text())['mcpServers']
        assert set(servers)==set(make_agents.SERVERS[role])
        assert all(s['command']=='python' for s in servers.values())
        for kind in ('case','read'):
            args=servers[f'tax-{kind}-{role}']['args']
            assert args[args.index('--agent')+1]==role
        if role!='front':
            args=servers['tax-opt-calc']['args']
            assert args[args.index('--role')+1]=='reader'
            assert args[args.index('--only')+1]=='evaluate,fx'
            assert 'Bash' not in bundle[role]['tools']


def test_missing_override_server_fails_before_overwriting_generated_files(tmp_path):
    project=checkout(tmp_path)
    make_agents.generate(project)
    files=list((project/'.claude').rglob('*'))
    before={f:f.read_bytes() for f in files if f.is_file()}
    (project/'.mcp.json').write_text(json.dumps({'mcpServers':{}}))
    with pytest.raises(ValueError,match='Missing required role servers'):
        make_agents.generate(project)
    assert all(f.read_bytes()==data for f,data in before.items())


def test_local_command_override_is_explicit_and_manifest_stays_portable(tmp_path):
    project=checkout(tmp_path)
    original=(project/'agent/mcp_servers.json').read_bytes()
    make_agents.generate(project,python_command=sys.executable)
    servers=json.loads((project/'.claude/mcp/analysis.json').read_text())['mcpServers']
    assert all(s['command']==sys.executable for s in servers.values())
    assert (project/'agent/mcp_servers.json').read_bytes()==original


def test_committed_role_files_match_current_specs_and_manifest(tmp_path):
    project=checkout(tmp_path)
    make_agents.generate(project)
    for path in (project/'.claude').rglob('*'):
        if path.is_file():
            assert path.read_text(encoding='utf8')==(ROOT/path.relative_to(project)).read_text(encoding='utf8')


def test_calculation_server_really_registers_only_calculation_tools(tmp_path):
    script='''import asyncio,json,sys
from pathlib import Path
root=Path.cwd()
sys.path.insert(0,str(root/'optimization/tools'))
import mcp_server
server,_=mcp_server.build_server(root/'optimization',root/'rule',root/'database',Path(sys.argv[1]),'reader',['evaluate','fx'])
print(json.dumps(sorted(t.name for t in asyncio.run(server.list_tools()))))
'''
    result=subprocess.run([sys.executable,'-X','utf8','-c',script,str(tmp_path)],cwd=ROOT,
                          capture_output=True,text=True,timeout=45)
    assert result.returncode==0,result.stderr[-2000:]
    assert json.loads(result.stdout)==['evaluate','fx']
