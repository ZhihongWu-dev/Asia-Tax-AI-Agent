"""Retrieve, authorize and project evidence before any answer is constructed."""
from __future__ import annotations
from hashlib import sha256
from time import monotonic
from urllib.parse import urlsplit

from packages.agent.contracts import SearchRequest, SearchResult, TrustedContext
from packages.agent.providers import failure
from packages.agent.budget import BudgetExceeded


def applicable(evidence, request):
    if request.jurisdiction and evidence.jurisdiction != request.jurisdiction:
        return False
    if request.topic and evidence.topic != request.topic:
        return False
    when = request.applicable_date
    if when and ((evidence.effective_from and when < evidence.effective_from) or
                 (evidence.effective_to and when > evidence.effective_to)):
        return False
    return True


def retrieve(provider, request: SearchRequest, context: TrustedContext):
    if hasattr(provider, "for_request"):
        provider = provider.for_request()
    started = monotonic()
    calls = 0
    while True:
        calls += 1
        remaining = request.deadline_ms - int((monotonic() - started) * 1000)
        try:
            result = provider.search_evidence(request.model_copy(update={'deadline_ms': max(1, remaining)}), context)
            result = SearchResult.model_validate(result)
            if result.request_id != request.request_id or result.trace_id != request.trace_id:
                raise ValueError('Retrieval response identity mismatch')
        except BudgetExceeded:
            raise
        except Exception:
            result = failure(request, 'c', 'INVALID_RESPONSE')
        if result.status != 'error' or not result.error.retryable or result.error.code not in ('TIMEOUT', 'UNAVAILABLE', 'HTTP_ERROR') or calls >= 2 or remaining <= 1:
            break
        if (monotonic() - started) * 1000 >= request.deadline_ms:
            break
    evidence_for_model, passages, gaps = [], [], list(result.coverage.missing_requirements)
    verified_ids = []
    rejected = False
    for evidence in result.evidence[:request.limit if not request.locators else 50]:
        if not applicable(evidence, request):
            gaps.append('资料法域、主题或适用日期不匹配：' + evidence.evidence_id)
            rejected = True
            continue
        display = None
        if evidence.display_use == 'allowed' and evidence.display_ref:
            if (monotonic() - started) * 1000 >= request.deadline_ms:
                gaps.append('读取原文预算已用尽')
                break
            try:
                display = provider.get_evidence(evidence.display_ref, 'display', context)
            except BudgetExceeded:
                raise
            except Exception:
                display = None
            if (display is None or display.status != 'ok' or display.reference != evidence.reference() or
                display.content_hash != evidence.content_hash or
                sha256((display.text or '').encode()).hexdigest() != evidence.content_hash):
                display = None
                gaps.append('原文版本不可用或校验失败：' + evidence.evidence_id)
        if display is not None:
            if (evidence.verification_status == 'verified' and not evidence.is_synthetic and not result.is_synthetic
                and not evidence.drift and evidence.effective_from and request.applicable_date):
                verified_ids.append(evidence.evidence_id)
            url = evidence.url
            if url and urlsplit(url).scheme not in ('https', 'http'):
                url = None
            passages.append({'unit_id': evidence.unit_id, 'source_id': evidence.source_id,
                'evidence_id': evidence.evidence_id, 'source_version_id': evidence.source_version_id,
                'locator': evidence.locator, 'text': display.text, 'title': evidence.title, 'url': url,
                'text_sha256': evidence.content_hash, 'is_synthetic': evidence.is_synthetic or result.is_synthetic,
                'model_use': evidence.model_use, 'policy_version': evidence.policy_version,
                'drift': evidence.drift, 'heading': evidence.heading, 'retrieved_at': evidence.retrieved_at,
                'snapshot_sha256': evidence.snapshot_sha256, 'coverage_cutoff': evidence.coverage_cutoff})
        # Permission to model alone is NOT permission to disclose a derived answer.
        if evidence.model_use == 'allowed' and evidence.display_use == 'allowed' and display is not None and evidence.model_text:
            if sha256(evidence.model_text.encode()).hexdigest() != evidence.content_hash:
                gaps.append('入模文本校验失败：' + evidence.evidence_id)
                continue
            evidence_for_model.append({'evidence_id': evidence.evidence_id,
                'text': evidence.model_text[:4000], 'source_version_id': evidence.source_version_id,
                'locator': evidence.locator, 'content_hash': evidence.content_hash,
                'display_allowed': evidence.display_use == 'allowed'})
    if result.status == 'error':
        reason = 'retrieval_failed'
    elif result.status == 'no_match':
        reason = 'no_match'
    elif rejected or gaps or result.status == 'partial' or result.coverage.truncated:
        reason = 'evidence_insufficient'
    elif not evidence_for_model:
        reason = 'evidence_restricted'
    else:
        reason = 'evidence_available'
    return {
        'status': 'unavailable' if result.status == 'error' else 'available' if passages else 'no_matching_units',
        'method': 'knowledge_provider_v0.1', 'query': request.query, 'provider': result.provider,
        'is_synthetic': result.is_synthetic, 'corpus_version': result.corpus_version,
        'retrieval_id': result.retrieval_id, 'reason_code': reason, 'passages': passages,
        'error': {'code': result.error.code, 'retryable': result.error.retryable} if result.error else None,
        'coverage': result.coverage.model_dump(), 'gaps': gaps, 'verified_evidence_ids': verified_ids,
        'model_evidence': evidence_for_model, 'retrieval_calls': calls,
        'timings_ms': {**result.timings_ms.model_dump(), 'total': round((monotonic() - started) * 1000, 2)},
    }


def display_result(bundle):
    """Separate frontend wire payload from the model-only projection."""
    return {k: v for k, v in bundle.items() if k != 'model_evidence'}


def compose_answer(bundle):
    reason = bundle['reason_code']
    summaries = {
        'no_match': '本次查询未找到匹配依据，不能据此认定相关规定不存在，也不能形成税务结论。',
        'evidence_restricted': '资料未获准用于模型分析。已获展示许可的原文列在下方，供核对；当前不生成税务判断。',
        'evidence_insufficient': '依据覆盖不完整，以下仅列出可核对的资料，缺失条件暂不判断。',
        'retrieval_failed': '资料服务暂时不可用，请稍后重试。',
        'evidence_available': '已找到可用资料。以下为依据摘录及适用条件提示，具体案件仍需最终复核。',
    }
    answer = {'summary': summaries[reason], 'conditions': ['仅适用于本次查询范围；日期、主体及具体事实仍须核对。'],
              'claims': [], 'limitations': bundle['gaps'][:], 'review_status': 'pending_final_review'}
    context = bundle.get('query_context', {})
    if reason == 'no_match':
        answer['limitations'].append('未匹配的查询：' + bundle['query'])
        if context.get('applicable_date'):
            answer['limitations'].append('需核对适用期间的依据：' + str(context['applicable_date']))
        elif context.get('uses_case'):
            answer['limitations'].append('尚未确认累算日期及其实际/计划状态，不能核实个案适用的规则版本。')
        answer['limitations'].append('可补充条文/案例编号或调整检索关键词；已知事实无需重新填写。')
    if bundle['is_synthetic']:
        answer['summary'] = '【模拟联调资料，不是真实税务依据】' + answer['summary']
        answer['limitations'].append('模拟资料仅验证流程，不能用于实际税务结论。')
    # Extractive first release: mechanically auditable, no invented claims or URLs.
    for evidence in bundle['model_evidence'][:7]:
        if not evidence.get('display_allowed', True):
            continue
        answer['claims'].append({'text': evidence['text'][:500], 'evidence_ids': [evidence['evidence_id']], 'kind': 'excerpt'})
    lines = [answer['summary'], '\n适用条件：' + '；'.join(answer['conditions'])]
    for claim in answer['claims']:
        lines.append('\n依据摘录 [' + claim['evidence_ids'][0] + ']：\n' + claim['text'])
    if answer['limitations']:
        lines.append('\n缺口：' + '；'.join(answer['limitations']))
    answer['text'] = '\n'.join(lines)
    return answer


def validate_answer(answer, bundle):
    permitted = {e['evidence_id']: e for e in bundle['model_evidence']}
    for claim in answer['claims']:
        if not claim['evidence_ids'] or any(ref not in permitted for ref in claim['evidence_ids']):
            raise ValueError('Unknown or unauthorized citation')
        if claim.get('kind') != 'excerpt' or not any(claim['text'] in permitted[ref]['text'] for ref in claim['evidence_ids']):
            raise ValueError('Unsupported claim')
    if answer['review_status'] != 'pending_final_review':
        raise ValueError('Agent cannot approve')
