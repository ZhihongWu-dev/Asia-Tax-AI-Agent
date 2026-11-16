import hashlib
import zipfile
from scripts.audit_main_only_citations import audit, blob_id, table
import pytest


def test_archive_original_and_current_source_must_both_match(tmp_path):
    original=b'original source'; digest=hashlib.sha256(original).hexdigest()
    (tmp_path/'raw').mkdir(); (tmp_path/'text').mkdir()
    (tmp_path/'raw/law.pdf').write_bytes(original)
    (tmp_path/'text/law.txt').write_text('Header\nTax rate is 25 percent.\nFooter')
    doc=dict(id='law',file='raw/law.pdf',sha256=digest)
    clause=dict(cite_id='law#all',doc_id='law',text='Tax rate is 25 percent.')
    path=tmp_path/'source.zip'
    with zipfile.ZipFile(path,'w') as archive: archive.writestr('repo/database/raw/law.pdf',original)
    with zipfile.ZipFile(path) as archive:
        rows=audit({'law#all':clause},{},{'law':doc},{'law':doc},tmp_path,archive)
        assert rows[0]['classification']=='exact_text_same_source'
        assert rows[0]['publication_status']=='candidate_not_approved'
        (tmp_path/'raw/law.pdf').write_bytes(b'changed')
        rows=audit({'law#all':clause},{},{'law':doc},{'law':doc},tmp_path,archive)
        assert rows[0]['classification']=='text_or_source_review_required'
        (tmp_path/'raw/law.pdf').write_bytes(original)
        (tmp_path/'text/law.txt').write_text('Tax rate is 20 percent.')
        assert not audit({'law#all':clause},{},{'law':doc},{'law':doc},tmp_path,archive)[0]['entire_main_text_contained_ignoring_whitespace']


def test_blob_hash_matches_git_empty_blob_and_duplicate_ids_fail():
    assert blob_id(b'')=='e69de29bb2d1d6434b8b29ae775ad8c2e48c5391'
    with pytest.raises(ValueError,match='Duplicate'):
        table(b'id,text\na,one\na,two\n','id')
