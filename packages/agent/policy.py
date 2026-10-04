"""Auditable scope and rule decisions shared by fixed and automatic dispatch."""
import re
from packages.agent import dialogue, task_state

REASONS = {
    'fact_conflict': 'BR-11', 'fact_collection': 'BR-12', 'intent_unclear': 'BR-04',
    'out_of_scope': 'BR-05', 'no_match': 'BR-17', 'evidence_insufficient': 'BR-17',
    'evidence_restricted': 'BR-17', 'retrieval_failed': 'BR-31', 'partial_requested': 'BR-28',
    'ordinary_chat': 'HY-02', 'budget_exhausted': 'HY-05', 'confirmation_required': 'BR-13',
    'partial_confirmation_required': 'BR-23', 'analysis_ready': 'BR-34',
}


def concrete_tax_claim(text):
    return bool(re.search(
        r'(?:税率|预提税|withholding tax)[^\n]{0,12}\d+(?:\.\d+)?\s*%|'
        r'(?:符合|满足|享受|可以|确定|已经).{0,8}免税|'
        r'(?:免税|应税).{0,8}(?:成立|确认|确定)|(?:tax.exempt).{0,8}(?:eligible|confirmed)',
        text, re.I))


def scope(query, job, facts, hint):
    lower = query.casefold()
    if job.get('jurisdiction') and job['jurisdiction'] != 'HK':
        return 'unsupported'
    if job.get('topic') and job['topic'] not in ('dividend', 'fsie'):
        return 'unsupported'
    if any(x in lower for x in ('利息', 'interest', '特许权', 'royalt', '增值税', 'vat')):
        return 'unsupported'
    hk = '香港' in query or 'hong kong' in lower or 'fsie' in lower
    if not hk and any(x in lower for x in ('新加坡税', '新加坡的税', 'singapore tax', '中国税', '内地税', 'mainland tax', '美国税', 'us tax')):
        return 'unsupported'
    if job.get('uses_case'):
        if not dialogue.supported(facts):
            return 'unsupported'
        if facts.get('analysis_jurisdiction') != 'HK':
            return 'need_scope'
        return 'HK'
    if hk or re.search(r'\bcase\s*\d+\b', lower) or hint in task_state.HINT_TASK:
        return 'HK'
    return 'need_scope'


def rewrite_preserves_scope(original, rewritten):
    # Unicode word boundaries do not delimit Chinese dates; preserve all explicit
    # years, full dates and locators, including a refusal to introduce new years.
    years = r'(?<!\d)(?:19|20)\d{2}(?!\d)'
    anchors = r'(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)|\d{4}年\d{1,2}月(?:\d{1,2}日)?|(?<![A-Za-z0-9])case\s*\d+(?!\d)|s\.\d+[A-Za-z]*'
    if set(re.findall(years, original)) != set(re.findall(years, rewritten)):
        return False
    numbers = r'(?<!\d)\d+(?:\.\d+)?(?!\d)'
    if set(re.findall(numbers, original)) != set(re.findall(numbers, rewritten)):
        return False
    return all(a.casefold() in rewritten.casefold() for a in re.findall(anchors, original, re.I))


def decisions(meta, turn):
    result = [{'rule_id': 'HY-01', 'decision': 'entry_is_hint'},
              {'rule_id': 'HY-05', 'decision': 'shared_budget'},
              {'rule_id': 'HY-07', 'decision': 'proposal_before_commit'}]
    reason = meta.get('reason_code')
    if reason in REASONS:
        result.append({'rule_id': REASONS[reason], 'decision': reason})
    if turn.get('uses_case') is False:
        result.append({'rule_id': 'HY-03', 'decision': 'reference_without_case'})
    return result
