"""Frozen domain research reports, with auditable evidence and Markdown export."""
from copy import deepcopy
from datetime import date
from uuid import uuid4

from packages.agent.budget import RunBudget, BudgetedProvider, current_budget
from packages.agent.contracts import SearchRequest, TrustedContext
from packages.agent.knowledge import retrieve, display_result
from packages.agent.review import freeze
from packages.chat.store import now
from packages.domain_bridge import state


def build_report(doc, owner, provider, partial):
    outcome = deepcopy(doc['domain_outcome'])
    budget = current_budget.get() or RunBudget(evidence_limit=35, search_limit=10)
    token = current_budget.set(budget)
    try:
        scoped_provider = BudgetedProvider(provider, budget, outcome['facts_hash'])
        legacy_report = None
        if outcome['mode'] != 'plan_structure' and doc.get('legacy_bindings'):
            from packages.chat.analysis import analyze
            legacy_report = analyze(doc['id'], {k: r['value'] for k, r in doc['facts'].items()},
                                    doc['domain_confirmation']['revision'], provider=scoped_provider,
                                    context=TrustedContext(owner=owner, case_id=doc['id']))
        references = outcome.get('citations', [])
        # An explicitly requested report has one 45 s budget for at most
        # seven FSIE parents, seven ruling blocks, and 21 domain references.
        # Larger bibliographies retain explicit gaps instead of unbounded reads.
        # Exact domain citations can name treaties or administrative guidance as
        # well as legislation. Keep them in the pinned library, without a type filter.
        bundle = None
        for start in range(0, min(len(references), 21), 7):
            part = retrieve(scoped_provider, SearchRequest(
                schema_version='0.2.0', request_id=str(uuid4()), trace_id=str(uuid4()),
                query='结构计算所引用的官方依据', jurisdiction=None, topic=None,
                deadline_ms=10000,
                applicable_date=date.fromisoformat(doc['domain_case']['event']['on']),
                date_status='planned' if outcome['mode'] == 'plan_structure' else 'actual',
                locators=references[start:start + 7], kind='all'), TrustedContext(owner=owner, case_id=doc['id']))
            if bundle is None:
                bundle = part
            else:
                bundle['passages'].extend(part['passages'])
                bundle['gaps'].extend(part['gaps'])
                if part['status'] == 'available':
                    bundle['status'] = 'available'
        if legacy_report:
            bundle = bundle or {'passages': [], 'gaps': [], 'status': legacy_report['retrieval_status']}
            passages = {p['unit_id']: p for p in legacy_report['passages'] + bundle['passages']}
            bundle['passages'] = list(passages.values())
            bundle['gaps'] += legacy_report.get('evidence_gaps', [])
        covered = {p['locator'] for p in (bundle or {}).get('passages', [])}
        # Native parent references are recorded as read only when their exact
        # parent reference was replayed and its full hash retained by B.
        native = {p['reference']['unit_id'].split('|')[1] for p in (bundle or {}).get('passages', [])
                  if p.get('reference', {}).get('unit_id', '').startswith(('law|', 'li|'))}
        missing = sorted(set(references) - covered - native)
        if bundle:
            bundle['gaps'].extend('领域引用未在本稿回读：' + cite for cite in missing)
    finally:
        current_budget.reset(token)
    questions = outcome.get('questions', [])
    report = {'id': str(uuid4()), 'created_at': now(), 'report_kind': 'structure_plan' if outcome['mode'] == 'plan_structure' else 'current_structure',
              'confirmed_revision': doc['domain_confirmation']['revision'], 'facts_snapshot': state.project_case(doc),
              'canonical_snapshot': deepcopy(doc['canonical_fact_records']), 'facts_hash': outcome['facts_hash'],
              'rule_version': outcome['release'], 'outcome': outcome, 'partial_output_authorized': partial,
              'professional_validation_status': 'unverified', 'stale': False, 'is_synthetic': True,
              'blockers': [q['key'] for q in questions], 'missing_nodes': [],
              'missing_locators': missing,
              'domain_citation_coverage': {'read': sorted(set(references) - set(missing)), 'missing': missing},
              'passages': (bundle or {}).get('passages', []), 'sources': [],
              'evidence_gaps': (bundle or {}).get('gaps', []) + ([] if references else ['领域计算尚未返回可定位的条文引用']),
              'evidence_gate': 'insufficient', 'retrieval_status': (bundle or {}).get('status', 'no_matching_units'),
              'coverage_cutoff': 'release:' + outcome['release'][:8], 'nodes': [],
              'review_tasks': [{'node': 'professional', 'status': 'pending_final_judgment', 'fact_keys': [q['key']],
                               'missing_facts': [q['key']]} for q in questions if q['kind'] in ('ruling', 'library')],
              'fsie_assessment': legacy_report, 'fsie_bridge_status': 'same_canonical_facts' if legacy_report else 'not_mapped',
              'integration_run_id': doc['integration_runs'][-1]['run_id'], 'map_version': state.MAP_VERSION,
              'budget_limits': {'seconds': 45, 'search': 10, 'evidence': 35}, 'budget': budget.snapshot()}
    report['markdown'] = render(report)
    return freeze(report)


def render(report):
    o = report['outcome']
    def bound(key):
        value = o.get(key, {})
        return str(value.get('value')) if value.get('status') == 'finite' else '未界定'
    lines = ['# 合并编排研究稿', '', '合成案情内部研究稿 · 待专业复核', '',
             f"模式：{o['mode']}；输入版本：{report['confirmed_revision']}；计算币种：{o.get('currency', '未确认')}",
             f"引擎发布：{o['release']}；映射版本：{report['map_version']}",
             f"事实哈希：{report['facts_hash']}；输入哈希：{o['input_hash']}", '',
             f"计算状态：{o['status']}；候选数量：{o['candidate_count']}",
             f"模型范围内税额：下界 {bound('lower')}，上界 {bound('upper')}", '', '## 结构', '']
    for row in o.get('structure', {}).get('entities', []):
        lines.append(f'- {row[0]} / {row[1]} / {row[2]}')
    for row in o.get('structure', {}).get('holds', []):
        lines.append(f'- {row[0]} → {row[1]}：{row[2]}%（{row[3]}）')
    lines.extend(['', '## 待补问题与条件', ''])
    for q in o.get('questions', []):
        lines.append(f"- [{q['kind']}] {q['key']}：{q['prompt']}")
    for region in o.get('regions', []):
        lines.append('\n地区：' + ' / '.join(region['jurisdictions']))
        for tax in region.get('guaranteed', []):
            lines.append(f'- 上界情景：{tax[0]} / {tax[1]} / {tax[2]} / {tax[3]} / {tax[4]}；依据：' + ', '.join(tax[5]))
        for condition in region.get('conditions', []):
            lines.append('- 未决条件：' + str(condition))
        for deadline in region.get('deadlines', []):
            lines.append('- 期限：' + str(deadline))
    lines.extend(['', '## 依据及缺口', ''])
    for passage in report['passages']:
        lines.append(f"- {passage.get('locator')} · SHA-256 {passage['text_sha256']} · {passage.get('url') or ''}")
    lines.extend('- ' + gap for gap in report['evidence_gaps'])
    if report.get('fsie_assessment'):
        lines.extend(['', '## 香港 FSIE 规则核对（同一案情）', ''])
        for node in report['fsie_assessment']['nodes']:
            lines.append('- ' + node['node'] + '：' + node['output'])
        lines.extend('- 待补：' + gap for gap in report['fsie_assessment'].get('blockers', []))
    else:
        lines.extend(['', '尚未确认聊天事实与公司、股权的对应关系，未附加香港 FSIE 规则核对。'])
    lines.extend(['', '## 限制', '', '工程校验不代表税务专业核验；模型上界依赖列明事实、行动及规则范围。'])
    lines.extend('- ' + str(item) for item in o.get('unmodelled', []))
    lines.extend('- ' + str(item) for item in o.get('notes', []))
    return '\n'.join(lines) + '\n'
