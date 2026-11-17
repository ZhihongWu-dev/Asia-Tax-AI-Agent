import json
from hashlib import sha256
import pytest
from packages.chat.library_overlay import load_candidates, admitted_rows, matching_rows
from packages.chat.library_overlay import validate_base_rows, blocked_citations


def replacement_fixture():
    commit, records, review = accepted_fixture()
    cite = review['cite_id']
    baseline = dict(uploaded_at='base', text_sha256=sha256(b'old extraction').hexdigest(),
                    document_sha256=review['document_sha256'])
    records[cite] = {**records[cite], 'replaces': baseline}
    review = {**review, 'difference': 'different_text', 'base_uploaded_at': 'base'}
    base = dict(cite_id=cite, doc_id=review['doc_id'], text='old extraction',
                document_sha256=review['document_sha256'])
    return commit, records, review, base


def test_replacement_requires_approval_and_exact_baseline():
    commit, records, review, base = replacement_fixture()
    assert admitted_rows(commit, records, [{**review, 'review_status': 'candidate'}]) == []
    assert blocked_citations([review], []) == {review['cite_id']}
    overlay = admitted_rows(commit, records, [review])
    validate_base_rows(overlay, records, [base])
    assert overlay[0]['origin'] == 'reviewed_main_replacement'
    assert blocked_citations([review], overlay) == set()
    for changed in ([], [{**base, 'text': 'changed'}],
                    [{**base, 'document_sha256': '0' * 64}], [{**base, 'doc_id': 'other'}]):
        with pytest.raises(ValueError, match='overlay_replacement_base_changed'):
            validate_base_rows(overlay, records, changed)


@pytest.mark.parametrize('baseline', [None, {}, {'uploaded_at': 'wrong'},
    {'uploaded_at': 'base', 'text_sha256': 'x' * 64, 'document_sha256': '0' * 64}])
def test_replacement_without_bound_baseline_is_not_admitted(baseline):
    commit, records, review, _ = replacement_fixture()
    records[review['cite_id']]['replaces'] = baseline or {}
    with pytest.raises(ValueError, match='overlay_replacement_baseline_missing'):
        admitted_rows(commit, records, [review])


def test_main_only_collision_still_fails():
    commit, records, review = accepted_fixture()
    overlay = admitted_rows(commit, records, [review])
    with pytest.raises(ValueError, match='overlay_base_collision'):
        validate_base_rows(overlay, records, [{'cite_id': review['cite_id']}])


def test_real_candidate_bundle_preserves_all_107_without_approving_them():
    commit,rows,digest=load_candidates()
    assert commit=='78a037f522d1636541c2e5fcdd1145e735f18124'
    assert len(rows)==107 and len(digest)==64
    assert admitted_rows(commit,rows,[])==[]
    reviews=[dict(cite_id=cite,difference='main_only',review_status='candidate') for cite in rows]
    assert admitted_rows(commit,rows,reviews)==[]


def accepted_fixture():
    commit,rows,_=load_candidates()
    cite='ae.fta.natural-persons-2023#all';doc=rows[cite]['document']
    review=dict(cite_id=cite,difference='main_only',review_status='accepted',reviewed_at='test timestamp',
                review_note='Test-only review; never sent to cloud',source_commit=commit,doc_id=doc['id'],
                document_sha256=doc['sha256'],document_url=doc['url'])
    return commit,rows,review


def test_explicit_matching_review_admits_original_text():
    commit,rows,review=accepted_fixture()
    admitted=admitted_rows(commit,rows,[review])
    assert admitted[0]['passage']==rows[review['cite_id']]['clause']['text'][:5000]
    assert admitted[0]['origin']=='reviewed_main_overlay'
    assert len(matching_rows(admitted,review['cite_id'],'ae',[],True))==1
    assert matching_rows(admitted,review['cite_id'],'cn',[],True)==[]


@pytest.mark.parametrize('change',[dict(reviewed_at=None),dict(review_note=''),dict(source_commit='other'),
    dict(document_sha256='0'*64),dict(document_url='https://example.invalid'),dict(doc_id='other')])
def test_incomplete_or_different_review_never_admits_text(change):
    commit,rows,review=accepted_fixture()
    with pytest.raises(ValueError): admitted_rows(commit,rows,[{**review,**change}])


def test_tampered_bundle_fails(tmp_path):
    from packages.chat.library_overlay import DEFAULT_BUNDLE
    payload=json.loads(DEFAULT_BUNDLE.read_text(encoding='utf-8'))
    payload['records'][0]['clause']['text']+='changed'
    path=tmp_path/'bundle.json';path.write_text(json.dumps(payload),encoding='utf-8')
    with pytest.raises(ValueError,match='invalid_overlay_record'): load_candidates(path)
