"""Immutable main source candidates, gated by the private review table."""
from hashlib import sha256
import json
from pathlib import Path

DEFAULT_BUNDLE = Path(__file__).resolve().parents[2] / 'config/library/main-only-candidates.json'


def candidate_digest(row):
    """Bind the approval to text, applicability, provenance and expected base."""
    return sha256(json.dumps(row, sort_keys=True, separators=(',', ':'),
                             ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()


def load_candidates(path=DEFAULT_BUNDLE):
    raw = path.read_bytes()
    payload = json.loads(raw)
    if payload.get('format_version') != 1 or payload.get('publication_status') != 'candidate_not_approved':
        raise ValueError('invalid_overlay_bundle')
    records = {}
    for row in payload['records']:
        cite = row['cite_id']
        if (cite in records or row['clause']['cite_id'] != cite
                or row['clause']['doc_id'] != row['document']['id']
                or sha256(row['clause']['text'].encode()).hexdigest() != row['text_sha256']):
            raise ValueError('invalid_overlay_record')
        if 'source_commit' in row and (not isinstance(row['source_commit'], str)
                or len(row['source_commit']) != 40
                or any(c not in '0123456789abcdef' for c in row['source_commit'])):
            raise ValueError('invalid_overlay_record')
        records[cite] = row
    return payload['source_commit'], records, sha256(raw).hexdigest()


def admitted_rows(source_commit, records, reviews):
    """No review status is inferred from an exact text match or a source hash."""
    admitted = []
    for review in reviews:
        if review['difference'] not in ('main_only', 'different_text') or review['review_status'] != 'accepted':
            continue
        row = records.get(review['cite_id'])
        if row is None or not review['reviewed_at'] or not (review.get('review_note') or '').strip():
            raise ValueError('overlay_review_incomplete')
        doc, clause = row['document'], row['clause']
        replacement = review['difference'] == 'different_text'
        if replacement:
            baseline = row.get('replaces', {})
            if (not isinstance(baseline, dict) or not baseline.get('uploaded_at')
                    or baseline['uploaded_at'] != review.get('base_uploaded_at')
                    or any(not isinstance(baseline.get(key), str) or len(baseline[key]) != 64
                           or any(c not in '0123456789abcdef' for c in baseline[key])
                           for key in ('text_sha256', 'document_sha256'))):
                raise ValueError('overlay_replacement_baseline_missing')
            try:
                approval = json.loads(review['review_note'])
            except (TypeError, ValueError) as exc:
                raise ValueError('overlay_replacement_approval_missing') from exc
            if (not isinstance(approval, dict) or not isinstance(approval.get('reason'), str)
                    or not approval['reason'].strip()
                    or approval.get('candidate_sha256') != candidate_digest(row)):
                raise ValueError('overlay_replacement_approval_mismatch')
        elif row.get('replaces'):
            raise ValueError('overlay_review_difference_mismatch')
        if (review['source_commit'] != row.get('source_commit', source_commit) or review['doc_id'] != doc['id']
                or review['document_sha256'] != doc['sha256']
                or review['document_url'] != doc['url']):
            raise ValueError('overlay_review_source_mismatch')
        admitted.append(dict(cite_id=clause['cite_id'],label=clause['label'],passage=clause['text'][:5000],
            document_id=doc['id'],title=doc['title'],url=doc['url'],document_sha256=doc['sha256'],
            lang=doc['lang'],effective_from=doc.get('effective_from',''),effective_to=doc.get('effective_to',''),
            jurisdiction=doc['jur'],origin='reviewed_main_replacement' if replacement else 'reviewed_main_overlay',
            _search_text=clause['text']))
    return admitted


def validate_base_rows(overlay, candidates, base_rows):
    """A replacement is valid only for the exact reviewed base extraction."""
    bases = {r['cite_id']: r for r in base_rows}
    if len(bases) != len(base_rows):
        raise ValueError('overlay_base_collision')
    for row in overlay:
        base = bases.get(row['cite_id'])
        if row['origin'] != 'reviewed_main_replacement':
            if base is not None:
                raise ValueError('overlay_base_collision')
            continue
        expected = candidates[row['cite_id']]['replaces']
        if (base is None or base['doc_id'] != row['document_id']
                or base['document_sha256'] != expected['document_sha256']
                or sha256(base['text'].encode('utf-8')).hexdigest() != expected['text_sha256']):
            raise ValueError('overlay_replacement_base_changed')


def blocked_citations(reviews, overlay):
    admitted = {r['cite_id'] for r in overlay}
    replacements = {r['cite_id'] for r in overlay if r['origin'] == 'reviewed_main_replacement'}
    blocked = {r['cite_id'] for r in reviews if r['difference'] == 'different_text'
               and not (r['review_status'] == 'rejected' and r['reviewed_at'] is not None)
               and r['cite_id'] not in replacements}
    blocked.update(r['cite_id'] for r in reviews
                   if r['difference'] == 'main_only' and r['cite_id'] not in admitted)
    for review in reviews:
        note = review.get('review_note') or ''
        if review['review_status'] != 'rejected' or not note.lstrip().startswith('{'):
            continue
        decision = json.loads(note)
        aliases = decision.get('excluded_citations', [])
        if (not isinstance(aliases, list) or any(not isinstance(c, str)
                or not c.startswith((review.get('doc_id') or '') + '#')
                or len(c) > 240 for c in aliases)):
            raise ValueError('invalid_review_excluded_citations')
        blocked.update(aliases)
    return blocked


def matching_rows(rows, query, jurisdiction, terms, exact):
    return [row for row in rows if row['jurisdiction']==jurisdiction and
        (row['cite_id']==query or (not exact and any(
            terms[0].lower() in row[key].lower() for key in ('_search_text','title'))))]
