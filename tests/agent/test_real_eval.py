"""Evaluation tooling checks (D). These are never reported as live-model passes."""
from copy import deepcopy
import json
from unittest.mock import patch

import pytest
from scripts import evaluate_b_workflow as evaluation
from packages.agent import dialogue
from packages.chat.service import ChatService
from packages.chat.store import ChatStore
from tests.agent.test_hybrid import send, parsed, edit, BASE


def test_frozen_corpus_has_provenance_and_meaningful_steps():
    data=evaluation.load_dataset()
    assert len(data['cases'])==62
    assert len(data['sources'])==11
    assert all(len(c['steps'])>=2 and any(s['expect'] for s in c['steps']) for c in data['cases'])
    assert sum(c['smoke'] for c in data['cases'])==15


def test_model_scope_aliases_keep_supported_queries_and_reject_other_regions():
    from packages.agent.task_contracts import TaskProposal
    from packages.agent.policy import scope
    for region in ('香港', 'Hong Kong', 'hk'):
        job = TaskProposal(kind='reference_lookup', jurisdiction=region, topic='股息').model_dump()
        assert scope('香港股息FSIE', job, {}, 'auto') == 'HK'
    job = TaskProposal(kind='reference_lookup', jurisdiction='SG', topic='dividend').model_dump()
    assert scope('新加坡股息', job, {}, 'auto') == 'unsupported'


def test_compact_prompt_keeps_every_field_and_extraction_constraint():
    from packages.chat.service import turn_prompt
    from packages.chat.facts import catalog
    system, _ = turn_prompt({'messages': [], 'facts': {}, 'state': 'collecting'}, '你好')
    fields = json.loads(system.split('\n事实字段词典：', 1)[1])
    assert len(fields) == len(catalog())
    for original, projected in zip(catalog(), fields):
        for key in ('field_name', 'data_type', 'enum_values', 'description_zh', 'unit', 'requires_final_judgment'):
            assert projected.get(key) == original.get(key)
        assert 'required_evidence_types' not in projected


def test_missing_free_key_is_blocked_not_a_pass(tmp_path, monkeypatch):
    monkeypatch.delenv('OPENROUTER_API_KEY',raising=False)
    target=tmp_path/'blocked.json'
    assert evaluation.main(['--env-file',str(tmp_path/'absent'), '--output',str(target)])==2
    result=json.loads(target.read_text())
    assert result['status']=='blocked' and result['model_calls']==[]
    assert result['summary']=={'passed':0,'failed':0,'blocked':15}


def test_meter_does_not_call_transport_after_budget_or_permission_failure():
    config=evaluation.ModelConfig('https://openrouter.ai/api/v1','fixture','qwen/fixture:free',max_retries=0)
    meter=evaluation.Meter(config,max_calls=1,interval=0)
    meter.original=lambda *_:{'usage':{},'choices':[]}
    client=evaluation.OpenAICompatibleClient(config)
    assert meter.call(client,'/chat/completions',{'model':config.model_name})['choices']==[]
    with pytest.raises(evaluation.ModelError): meter.call(client,'/chat/completions',{'model':config.model_name})
    assert len(meter.calls)==1 and meter.blocked
    meter=evaluation.Meter(config,max_calls=2,interval=0)
    with pytest.raises(evaluation.ModelError):
        meter.call(client,'/chat/completions',{'model':config.model_name,'messages':[evaluation.MARKER]})
    assert meter.leaked and not meter.calls


def test_evaluation_replays_actual_api_without_another_model_request(tmp_path):
    spec=next(c for c in evaluation.load_dataset()['cases'] if c['name']=='重复提交不重复调用')
    config=evaluation.ModelConfig('https://openrouter.ai/api/v1','fixture','qwen/fixture:free',max_retries=0)
    meter=evaluation.Meter(config,interval=0)
    response=parsed('chat',reply='你好')
    meter.original=lambda *_:{'choices':[{'message':{'content':json.dumps(response)}}]}
    with patch('packages.chat.service.current_model_config',return_value=config), patch.object(
        evaluation.OpenAICompatibleClient,'_post',lambda c,p,b:meter.call(c,p,b)):
        result=evaluation.run_case(spec,config,meter,str(tmp_path))
    assert result['status']=='passed' and len(meter.calls)==1
    broken=deepcopy(spec)
    broken['steps'][0]['expect']['facts']={'dividend_amount':999}
    with patch('packages.chat.service.current_model_config',return_value=config), patch.object(
        evaluation.OpenAICompatibleClient,'_post',lambda c,p,b:meter.call(c,p,b)):
        result=evaluation.run_case(broken,config,meter,str(tmp_path))
    assert result['status']=='failed' and 'dividend_amount' in result['steps'][0]['checks_failed'][0]


@pytest.mark.parametrize('quote,value,accepted', [
    ('金额刚才说错了，应为200万港币',2000000,True),
    ('金额刚才说错了，应为200万港币',200,False),
    ('金额更正为2,000,000港币',2000000,True),
    ('金额应为1.5亿元',150000000,True),
    ('correct amount to 2 million',2000000,True),
])
def test_amount_correction_units_are_checked(quote,value,accepted):
    turn=parsed(facts={'dividend_amount':value},corrections={'dividend_amount':quote})
    assert ('dividend_amount' in dialogue.correction_fields(turn,quote,{'facts':{}}))==accepted


def test_fact_summary_keeps_question_and_does_not_authorize_partial_analysis(tmp_path):
    store=ChatStore(f'sqlite:///{tmp_path}/summary.sqlite')
    service=ChatService(store,provider=evaluation.MockKnowledgeProvider(), orchestration='hybrid',turner=lambda *_:parsed())
    try:
        doc=edit(service,store.create('owner'),{**BASE,'dividend_amount':1000000,'holding_percentage_pct':3})
        doc=send(service,doc,text='请梳理案情')
        pending=deepcopy(doc['dialogue']['pending'])
        control=deepcopy(doc['orchestration']['active_task'])
        result=send(service,doc,text='先不要下结论，把我已经提供的信息列出来，并说还缺哪些关键资料')
        assert '1000000' in result['messages'][-1]['text'] and '待补' in result['messages'][-1]['text']
        assert result['dialogue']['pending']==pending
        assert result['orchestration']['active_task']==control
        assert not result['dialogue'].get('partial_consent') and result['confirmed_facts'] is None
        assert result['facts']==doc['facts'] and not result['analyses']
    finally:
        store.engine.dispose()


def test_negated_summary_does_not_trigger_read_only_action():
    assert not dialogue.explicit_summary_request('不要汇总已知事实，继续追问')


def test_historical_summary_before_first_dialogue_uses_actual_api(tmp_path):
    spec=next(c for c in evaluation.load_dataset()['cases'] if c['name']=='历史案情汇总报错回归')
    config=evaluation.ModelConfig('https://openrouter.ai/api/v1','fixture','qwen/fixture:free',max_retries=0)
    meter=evaluation.Meter(config,interval=0)
    meter.original=lambda *_:pytest.fail('Read-only explicit summary needs no model')
    with patch('packages.chat.service.current_model_config',return_value=config), patch.object(
        evaluation.OpenAICompatibleClient,'_post',lambda c,p,b:meter.call(c,p,b)):
        result=evaluation.run_case(spec,config,meter,str(tmp_path))
    assert result['status']=='passed' and not meter.calls
