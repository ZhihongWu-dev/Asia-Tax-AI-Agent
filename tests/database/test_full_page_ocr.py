import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('library_build_ocr', ROOT/'database/tools/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def fixture(tmp_path,monkeypatch):
    monkeypatch.setattr(build,'ROOT',tmp_path)
    source=tmp_path/'original.pdf'
    with build.fitz.open() as pdf:
        page=pdf.new_page()
        page.insert_text((50,50),'Signature metadata only '*4)
        pdf.save(source)
    sha=hashlib.sha256(source.read_bytes()).hexdigest()
    row=dict(id='test',file='original.pdf',sha256=sha)
    text='Article 1. Complete scanned legal text, including the operative provision.'
    folder=tmp_path/'ocr';folder.mkdir()
    (folder/'test.txt').write_text(f'#ocr sha256={sha} model=test\n{text}',encoding='utf-8')
    config=dict(clip_top=0,skip_pages=[],scope='All pages',language='vie',rotation=0,dpi=300)
    models={'vie':'pinned-model'}
    profile=hashlib.sha256(json.dumps(dict(source=sha,config=config,models=models),sort_keys=True,separators=(',',':')).encode()).hexdigest()
    metadata=dict(source_sha256=sha,profile=profile,config=config,model_sha256=models,
        pages=[dict(page=1,status='ocr_pending_review',sha256=hashlib.sha256(text.encode()).hexdigest())])
    (folder/'test.json').write_text(json.dumps(metadata),encoding='utf-8')
    return row,text,metadata


def test_full_page_transcription_overrides_signature_layer(tmp_path,monkeypatch):
    row,text,_=fixture(tmp_path,monkeypatch)
    assert len(build.pdf_pages(tmp_path/'original.pdf')[0])>build.OCR_PAGE_MIN
    actual,pages,status=build.to_text(row,'pdf',tmp_path)
    assert actual==text and pages==[text] and status=='ocr'


def test_legacy_ocr_keeps_native_layer(tmp_path,monkeypatch):
    row,_,_=fixture(tmp_path,monkeypatch)
    (tmp_path/'ocr/test.json').unlink()
    actual,_,_=build.to_text(row,'pdf',tmp_path)
    assert 'Signature metadata' in actual


@pytest.mark.parametrize('field,value',[('source_sha256','wrong'),('profile','wrong'),('pages',[])])
def test_bad_provenance_cannot_override(tmp_path,monkeypatch,field,value):
    row,text,metadata=fixture(tmp_path,monkeypatch)
    metadata[field]=value
    (tmp_path/'ocr/test.json').write_text(json.dumps(metadata))
    with pytest.raises(ValueError):build.full_page_ocr(row,[text])


def test_modified_transcription_rejected(tmp_path,monkeypatch):
    row,text,_=fixture(tmp_path,monkeypatch)
    with pytest.raises(ValueError):build.full_page_ocr(row,[text+'changed'])


@pytest.mark.parametrize('config',[dict(clip_top=.1),dict(skip_pages=[1])])
def test_partial_scope_cannot_override_whole_native_page(tmp_path,monkeypatch,config):
    row,text,metadata=fixture(tmp_path,monkeypatch)
    metadata['config'].update(config)
    (tmp_path/'ocr/test.json').write_text(json.dumps(metadata))
    assert build.full_page_ocr(row,[text]) is False
