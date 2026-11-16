"""Bounded PDF text extraction. Originals are never written to disk."""
from __future__ import annotations
import asyncio
import json
import re
import sys
from io import BytesIO
from pathlib import Path

MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 50
MAX_TEXT = 20000
MARKER = '\n\n[Taxrora PDF attachment]\n'


def extract_pdf(data: bytes) -> dict:
    from pypdf import PdfReader
    if len(data) > MAX_BYTES:
        raise ValueError('pdf_too_large')
    if not data.startswith(b'%PDF-'):
        raise ValueError('pdf_invalid')
    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted:
            raise ValueError('pdf_encrypted')
        if len(reader.pages) > MAX_PAGES:
            raise ValueError('pdf_too_many_pages')
        pages, empty, length = [], [], 0
        for number, page in enumerate(reader.pages, 1):
            content = re.sub(r'[\x00-\x08\x0b-\x1f]', '', page.extract_text() or '').strip()
            length += len(content)
            if length > MAX_TEXT:
                raise ValueError('pdf_too_much_text')
            if content:
                pages.append({'page': number, 'text': content})
            else:
                empty.append(number)
        if not pages:
            raise ValueError('pdf_no_text')
        return {'page_count': len(reader.pages), 'pages': pages, 'empty_pages': empty}
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('pdf_invalid') from exc


# A killable worker bounds CPU and expanded PDF data independently of the API.
async def read_pdf(data: bytes) -> dict:
    proc = await asyncio.create_subprocess_exec(
        sys.executable, '-X', 'utf8', '-m', 'packages.chat.pdf_attachments',
        cwd=str(Path(__file__).resolve().parents[2]),
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL)
    try:
        output, _ = await asyncio.wait_for(proc.communicate(data), 20)
        if proc.returncode:
            raise ValueError('pdf_invalid')
        result = json.loads(output)
        if 'error' in result:
            raise ValueError(result['error'])
        return result
    except asyncio.TimeoutError as exc:
        raise ValueError('pdf_timeout') from exc
    finally:
        if proc.returncode is None:
            from packages.chat.worker_limits import terminate_worker
            await terminate_worker(proc)


if __name__ == '__main__':
    from packages.chat.worker_limits import apply_worker_limits
    apply_worker_limits(15, 384)
    try:
        result = extract_pdf(sys.stdin.buffer.read(MAX_BYTES + 1))
    except Exception as exc:
        code = str(exc)
        result = {'error': code if code.startswith('pdf_') else 'pdf_invalid'}
    print(json.dumps(result, ensure_ascii=False))
