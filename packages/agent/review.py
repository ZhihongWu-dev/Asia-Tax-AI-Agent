"""Final review of a frozen internal report; no intermediate advisor execution."""
from hashlib import sha256
import json
from packages.chat.store import now


def report_hash(report):
    payload = {k: v for k, v in report.items() if k not in ('report_hash', 'review', 'stale')}
    return sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def freeze(report):
    report['review'] = {'status': 'pending_final_review', 'history': []}
    report['report_hash'] = report_hash(report)
    return report


def review_report(report, expected_hash, reviewer, decision, note):
    from packages.chat.service import WorkflowError
    if report.get('stale') or report.get('report_hash') != expected_hash or report_hash(report) != expected_hash:
        raise WorkflowError('review_snapshot_changed')
    if decision not in ('approved', 'changes_requested', 'unable_to_conclude'):
        raise WorkflowError('invalid_review_decision')
    if not note.strip():
        raise WorkflowError('review_note_required')
    if decision == 'approved' and (report.get('is_synthetic') or report.get('missing_nodes') or
        report.get('blockers') or report.get('missing_locators') or
        report.get('evidence_gate') != 'sufficient_for_task'):
        raise WorkflowError('review_incomplete')
    if report['review']['status'] != 'pending_final_review':
        raise WorkflowError('review_already_decided')
    report['review']['history'].append({'reviewer': reviewer, 'decision': decision,
                                      'note': note.strip(), 'report_hash': expected_hash, 'at': now()})
    report['review']['status'] = decision
