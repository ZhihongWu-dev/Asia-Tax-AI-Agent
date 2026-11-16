"""Small immutable main-only source bundle, gated by the private review table."""
from hashlib import sha256
import json
from pathlib import Path

DEFAULT_BUNDLE = Path(__file__).resolve().parents[2] / 'config/library/main-only-candidates.json'


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
        records[cite] = row
    return payload['source_commit'], records, sha256(raw).hexdigest()


def admitted_rows(source_commit, records, reviews):
    """No review status is inferred from an exact text match or a source hash."""
    admitted = []
    for review in reviews:
        if review['difference'] != 'main_only' or review['review_status'] != 'accepted':
            continue
        row = records.get(review['cite_id'])
        if row is None or not review['reviewed_at'] or not (review.get('review_note') or '').strip():
            raise ValueError('overlay_review_incomplete')
        doc, clause = row['document'], row['clause']
        if (review['source_commit'] != source_commit or review['doc_id'] != doc['id']
                or review['document_sha256'] != doc['sha256']
                or review['document_url'] != doc['url']):
            raise ValueError('overlay_review_source_mismatch')
        admitted.append(dict(cite_id=clause['cite_id'],label=clause['label'],passage=clause['text'][:5000],
            document_id=doc['id'],title=doc['title'],url=doc['url'],document_sha256=doc['sha256'],
            lang=doc['lang'],effective_from=doc.get('effective_from',''),effective_to=doc.get('effective_to',''),
            jurisdiction=doc['jur'],origin='reviewed_main_overlay',_search_text=clause['text']))
    return admitted


def matching_rows(rows, query, jurisdiction, terms, exact):
    return [row for row in rows if row['jurisdiction']==jurisdiction and
        (row['cite_id']==query or (not exact and any(
            terms[0].lower() in row[key].lower() for key in ('_search_text','title'))))]
