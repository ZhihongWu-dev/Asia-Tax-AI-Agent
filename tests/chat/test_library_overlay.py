import json
import pytest
from packages.chat.library_overlay import load_candidates, admitted_rows, matching_rows


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
