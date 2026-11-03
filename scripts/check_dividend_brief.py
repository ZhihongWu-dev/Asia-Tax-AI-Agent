"""Opt-in live smoke check using synthetic facts and an isolated local case database.

No cloud cases are created. Calls the configured model only with --live-model.
"""
import argparse
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live-model', action='store_true')
    args = parser.parse_args()
    if not args.live_model:
        parser.error('This check calls the configured model; pass --live-model to opt in.')
    os.environ['FSIE_AGENT_LOG_DIR'] = 'off'
    from packages.runtime import application_runtime
    from packages.agent.providers import configured_provider
    from packages.chat.store import ChatStore
    from packages.chat.service import WorkflowError
    from packages.consultation.workflow import message
    text = ('以下全部是合成研究资料。分红公司税务居民地中国内地，计划2026-12-01分红100万CNY。'
            '直接股东是香港A公司，持股100%，2020-01-01取得股份。没有其他中间控股公司。'
            '最终受益人是税务居民地中国内地的自然人张某，目标是长期将资金留在公司投资，暂不分配到个人。'
            '请先整理基础信息，再判断需要哪些工具和动态补问。')
    try:
        with TemporaryDirectory(prefix='taxrora-brief-live-') as directory, application_runtime():
            store = ChatStore(f'sqlite:///{directory}/case.sqlite')
            doc = store.create('synthetic:smoke')
            try:
                result = message(store, configured_provider(), 'synthetic:smoke', doc['id'], 0, str(uuid4()), text, True,
                                 emit=lambda stage: print(json.dumps({'progress': stage}, ensure_ascii=False), flush=True))
                brief = result['consultation']
                print(json.dumps({'status':'ok', 'stage':brief['stage'], 'fact_count':len(brief['facts']),
                    'tools':[{k:t.get(k) for k in ('tool','status','gaps')} for t in brief['tools']],
                    'reply':result['messages'][-1]['text']}, ensure_ascii=False), flush=True)
            finally: store.engine.dispose()
    except WorkflowError as exc:
        print(json.dumps({'status':'failed','code':exc.code}), flush=True)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
