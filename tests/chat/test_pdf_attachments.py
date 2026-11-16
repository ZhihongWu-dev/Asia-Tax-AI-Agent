import asyncio
from io import BytesIO
import json
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
from apps.api.main import app
from apps.api.auth import optional_user
from apps.api.chat import get_service
from packages.chat.service import ChatService, turn_prompt
from packages.chat.store import ChatStore
from packages.chat.pdf_attachments import extract_pdf, read_pdf, MAX_BYTES, MARKER


def pdf(text='Dividend amount CNY 2000000', blank=False, encrypted=False, count=1):
    writer = PdfWriter()
    for _ in range(count):
        page = writer.add_blank_page(600, 800)
        if not blank:
            font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
            page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
            stream = DecodedStreamObject()
            stream.set_data(('BT /F1 12 Tf 50 700 Td (' + text + ') Tj ET').encode())
            page[NameObject('/Contents')] = writer._add_object(stream)
    if encrypted:
        writer.encrypt('fixture')
    output = BytesIO(); writer.write(output)
    return output.getvalue()


def test_extract_and_worker_keep_page_references():
    result = asyncio.run(read_pdf(pdf(count=2)))
    assert [p['page'] for p in result['pages']] == [1, 2]
    assert '2000000' in result['pages'][1]['text']
    assert result['empty_pages'] == []


@pytest.mark.parametrize('data,error', [
    (b'not a pdf', 'pdf_invalid'), (b'%PDF-' + b'x' * MAX_BYTES, 'pdf_too_large'),
    (pdf(blank=True), 'pdf_no_text'), (pdf(encrypted=True), 'pdf_encrypted'),
    (pdf(count=51), 'pdf_too_many_pages'), (pdf(text='A' * 20001), 'pdf_too_much_text'),
], ids=['invalid', 'oversized', 'blank', 'encrypted', 'too-many-pages', 'too-much-text'])
def test_rejects_unreadable_or_excessive_documents(data, error):
    with pytest.raises(ValueError, match=error): extract_pdf(data)


def test_mixed_pdf_reports_unread_pages():
    writer = PdfWriter(BytesIO(pdf()))
    writer.add_blank_page(600, 800)
    out = BytesIO(); writer.write(out)
    assert extract_pdf(out.getvalue())['empty_pages'] == [2]


def test_authenticated_upload_and_chat_context(tmp_path):
    store = ChatStore(f'sqlite:///{tmp_path}/pdf.sqlite')
    seen = []
    def turn(doc, text):
        seen.append(text)
        return {'intent': 'chat', 'facts': {}, 'query': '', 'reply': 'Read the PDF.'}
    service = ChatService(store, turner=turn)
    app.dependency_overrides[get_service] = lambda: service
    app.dependency_overrides[optional_user] = lambda: {'id': 'pdf-test-user'}
    headers = {'x-asiatax-request': '1'}
    try:
        with TestClient(app) as client:
            result = client.post('/api/attachments/pdf?filename=case.pdf', content=pdf('A' * 5000 + ' END_OF_DOCUMENT'), headers=headers)
            assert result.status_code == 200
            file = result.json()
            text = 'Please summarize.' + MARKER + json.dumps(file)
            doc = client.post('/api/cases', headers=headers).json()
            response = client.post(f"/api/cases/{doc['id']}/messages", headers=headers, json={
                'text': text, 'revision': doc['revision'], 'request_id': str(uuid4()), 'data_approved': True})
            assert response.status_code == 200, response.text
            assert 'END_OF_DOCUMENT' in seen[0]
            saved = store.get('user:pdf-test-user', doc['id'])
            _, prompt = turn_prompt(saved, 'What is in the file?')
            assert 'END_OF_DOCUMENT' in prompt
            assert MARKER in saved['messages'][0]['text']
            assert client.post('/api/attachments/pdf?filename=case.txt', content=pdf(), headers=headers).status_code == 422
            app.dependency_overrides[optional_user] = lambda: None
            assert client.post('/api/attachments/pdf?filename=case.pdf', content=pdf(), headers=headers).status_code == 401
    finally:
        app.dependency_overrides.clear()
        store.engine.dispose()
