"""C provider wire service for pinned, replayable official text."""
from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache
from hashlib import sha256
import importlib
import os
from pathlib import Path
import re
import sys
from threading import local
from typing import Literal
from types import SimpleNamespace

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from packages.agent.contracts import (Coverage, Evidence, EvidenceResult, Reference, SearchRequest,
                                      SearchResult, TrustedContext)
from packages.domain_bridge.bridge import PINNED_DB_SHA256, DomainError, release_path, verify_release
from packages.agent.source_policy import public_hk_official, canonical_source_id, source_kind, FSIE_GUIDANCE_PATHS

app = FastAPI(title='Official tax library read-only API', version='0.1.0')
_thread = local()


class SearchWire(BaseModel):
    request: SearchRequest
    trusted_context: TrustedContext


class EvidenceWire(BaseModel):
    reference: Reference
    purpose: Literal['display', 'model']
    trusted_context: TrustedContext


def _authorise(request: Request):
    from packages.agent.providers import ProviderSettings
    token = ProviderSettings().c_token
    if token:
        if request.headers.get('authorization') != 'Bearer ' + token:
            raise HTTPException(401, 'access_denied')
    elif request.client is None or request.client.host not in ('127.0.0.1', '::1', 'testclient'):
        raise HTTPException(403, 'loopback_only')


@lru_cache(maxsize=1)
def _release():
    try:
        root = release_path()
        verify_release(root)
        return root
    except DomainError:
        raise HTTPException(503, 'release_unavailable') from None


def _library():
    root = _release()
    if not getattr(_thread, 'library', None):
        sys.path.insert(0, str(root / 'official/tools'))
        module = importlib.import_module('search')
        lib = module.Library(root / 'official/official.sqlite')
        lib.con.execute('PRAGMA query_only = ON')
        _thread.library = lib
    return _thread.library


def _reference(cite: str, start: int, end: int) -> Reference:
    unit = 'law|' + cite + '|' + str(start) + '|' + str(end)
    return Reference(evidence_id=unit, source_version_id=PINNED_DB_SHA256, unit_id=unit)


def _span(reference: Reference):
    if reference.source_version_id != PINNED_DB_SHA256 or reference.evidence_id != reference.unit_id:
        raise HTTPException(409, 'version_unavailable')
    parts = reference.unit_id.rsplit('|', 2)
    if len(parts) != 3 or not parts[0].startswith(('law|', 'li|')):
        raise HTTPException(422, 'invalid_reference')
    try:
        start, end = int(parts[1]), int(parts[2])
    except ValueError:
        raise HTTPException(422, 'invalid_reference') from None
    if start < 0 or end <= start or end - start > 30000:
        raise HTTPException(422, 'invalid_reference')
    return parts[0].split('|', 1)[1], start, end


def _locator_hits(lib, locators):
    """Group verified subsection spans under one replayable parent section."""
    groups = {}
    for locator in locators:
        match = re.fullmatch(r's\.(15[A-Z])(?:\((\d+)\))?', locator)
        if match:
            section, subsection = match.groups()
            cite = 'hk.cap112.en#s' + section
        else:
            cite, subsection = locator, None
        row = lib.con.execute('SELECT text FROM clause WHERE cite_id = ?', (cite,)).fetchone()
        if not row:
            continue
        text = row[0]
        if len(text) > 30000:
            continue
        spans = [(m.group(1), m.start()) for m in re.finditer(r'(?m)^\((\d+)\)\s*', text)]
        if subsection:
            matches = [i for i, (number, _) in enumerate(spans) if number == subsection]
            if len(matches) != 1:
                continue
            index = matches[0]
            start = spans[index][1]
            end = spans[index + 1][1] if index + 1 < len(spans) else len(text)
        else:
            start, end = 0, len(text)
        if cite not in groups:
            groups[cite] = SimpleNamespace(cite_id=cite, span=(0, len(text)), snippet=text,
                requested_locator='s.' + section if match else cite, locator_spans=[],
                valid_from=lib.meta[cite]['valid_from'], valid_to=lib.meta[cite]['valid_to'],
                title=lib.meta[cite]['title'], lang=lib.meta[cite]['lang'])
        requested = [{'locator': locator, 'start': start, 'end': end}]
        if match and not subsection:
            requested.extend({'locator': f's.{section}({number})', 'start': offset,
                              'end': spans[index + 1][1] if index + 1 < len(spans) else len(text)}
                             for index, (number, offset) in enumerate(spans))
        existing = {span['locator'] for span in groups[cite].locator_spans}
        for span in requested:
            if span['locator'] not in existing:
                span['content_hash'] = sha256(text[span['start']:span['end']].encode()).hexdigest()
                groups[cite].locator_spans.append(span)
                existing.add(span['locator'])
    return list(groups.values())


@app.get('/health')
def health():
    _release()
    return {'knowledge_ready': True, 'corpus_version': PINNED_DB_SHA256, 'channels': ['exact', 'bm25']}


@app.post('/search', response_model=SearchResult)
def search(body: SearchWire, request: Request):
    _authorise(request)
    lib = _library()
    r = body.request
    if r.kind == 'ruling':
        return SearchResult(request_id=r.request_id, trace_id=r.trace_id, retrieval_id=r.request_id,
                            provider='c', is_synthetic=False, corpus_version=PINNED_DB_SHA256,
                            status='no_match', coverage=Coverage(status='partial', scope='Official law library',
                                                                missing_requirements=['本资料库不包含独立税务裁定案例']))
    navigation = list(r.locators)
    if not navigation and r.jurisdiction == 'HK' and r.kind != 'guidance':
        from packages.chat.knowledge import outside_scope, references, topic_locators
        explicit, cases = references(r.query)
        navigation = explicit or ([] if cases or outside_scope(r.query) else topic_locators(r.query))
    hits = lib.search(r.query, k=min(50, r.limit * 6) if r.kind != 'all' else r.limit, jur=r.jurisdiction.lower() if r.jurisdiction else None, as_of=r.applicable_date.isoformat() if r.applicable_date else None,
                      channels=('exact', 'bm25'), today=date.today().isoformat())
    retrieval_gap = None
    if not isinstance(hits, list):
        retrieval_gap = hits.reason
        hits = []
    direct = _locator_hits(lib, navigation) if navigation else []
    if r.applicable_date:
        when = r.applicable_date.isoformat()
        direct = [hit for hit in direct if (not hit.valid_from or hit.valid_from <= when) and
                  (not hit.valid_to or when < hit.valid_to)]
    selected = []
    seen = set()
    # Explicit navigation must not substitute keyword hits for absent or expired clauses.
    for hit in direct if navigation else hits:
        key = (hit.cite_id, *hit.span)
        if key not in seen:
            selected.append(hit)
            seen.add(key)
    # Read seven parent sections once, then project all verified child spans.
    # The shared remaining reads also serve PostgreSQL guidance and ruling sources.
    if r.kind != 'all':
        # Filter by doc metadata before truncation; a statutory locator is not guidance.
        selected = [hit for hit in selected if source_kind((lib.con.execute(
            'SELECT type FROM doc WHERE id = ?', (lib.meta[hit.cite_id]['expr_id'],)
        ).fetchone() or {'type': None})['type']) == r.kind]
    max_evidence = 7 if navigation else r.limit
    truncated = len(selected) > max_evidence
    selected = selected[:max_evidence]
    evidence = []
    for hit in selected:
        row = lib.con.execute('SELECT text FROM clause WHERE cite_id = ?', (hit.cite_id,)).fetchone()
        if not row:
            continue
        full = row[0]
        start, end = hit.span
        if start < 0 or end > len(full) or full[start:end] != hit.snippet:
            start = full.find(hit.snippet) if hit.snippet else -1
            if start < 0 or full.find(hit.snippet, start + 1) >= 0:
                continue
            end = start + len(hit.snippet)
        excerpt = full[start:end]
        if not excerpt or len(excerpt) > 30000:
            continue
        meta = lib.meta[hit.cite_id]
        doc = lib.con.execute('SELECT url, type FROM doc WHERE id = ?', (meta['expr_id'],)).fetchone()
        reference = _reference(hit.cite_id, start, end)
        cutoff = date.fromisoformat(hit.valid_to) - timedelta(days=1) if hit.valid_to else None
        source_id = 'hk_hkel_iro_cap112' if meta['expr_id'] == 'hk.cap112.en' else meta['expr_id']
        source_id = canonical_source_id(source_id, doc['url'] if doc else None)
        is_fsie = source_id in FSIE_GUIDANCE_PATHS or source_id == 'hk_hkel_iro_cap112' and re.search(r'#s15(?:H|I|J|K|L|M|N|O|P|Q|R|S)$', hit.cite_id)
        official_for_model = public_hk_official(source_id, doc['url'] if doc else None)
        evidence.append(Evidence(**reference.model_dump(), source_id=source_id, content_hash=sha256(excerpt.encode()).hexdigest(),
                                 title=hit.title or hit.cite_id, source_type=doc['type'] if doc else 'official',
                                 url=doc['url'] if doc else None, locator=getattr(hit, 'requested_locator', hit.cite_id),
                                 heading='Legal source: ' + hit.cite_id, jurisdiction=meta['jur'].upper() if meta['jur'] else None,
                                 topic='dividend' if is_fsie else None, language=hit.lang or '',
                                 effective_from=date.fromisoformat(hit.valid_from) if hit.valid_from else None,
                                 effective_to=cutoff, verification_status='unverified',
                                 model_use='allowed' if official_for_model else 'denied',
                                 model_text=excerpt if official_for_model else None,
                                 display_use='allowed', policy_version='public-hk-official-v1' if official_for_model else 'official-display-only-v1', display_ref=reference,
                                 locator_spans=getattr(hit, 'locator_spans', []), mapping_version='law-locator-2026-10-11'))
    missing = [retrieval_gap] if retrieval_gap and not direct else []
    if truncated:
        missing.append(f'本次只返回前 {max_evidence} 段原文；其余定位条款需另行检索')
    if r.locators:
        resolved = {span.locator for e in evidence for span in e.locator_spans} | {e.locator for e in evidence}
        missing.extend('未定位条款：' + locator for locator in r.locators if locator not in resolved)
    return SearchResult(request_id=r.request_id, trace_id=r.trace_id, retrieval_id=r.request_id,
                        provider='c', is_synthetic=False, corpus_version=PINNED_DB_SHA256,
                        status='partial' if evidence and missing else 'ok' if evidence else 'no_match', evidence=evidence,
                        coverage=Coverage(status='partial' if missing else 'unchecked',
                                          scope='Official law library; applicability and professional review pending',
                                          missing_requirements=missing, truncated=truncated))


@app.post('/evidence', response_model=EvidenceResult)
def evidence(body: EvidenceWire, request: Request):
    _authorise(request)
    ref = body.reference
    try:
        cite, start, end = _span(ref)
    except HTTPException as exc:
        return EvidenceResult(status='version_unavailable' if exc.status_code == 409 else 'not_found', reference=ref)
    lib = _library()
    if body.purpose == 'model':
        meta = lib.meta.get(cite)
        doc = lib.con.execute('SELECT url FROM doc WHERE id = ?', (meta['expr_id'],)).fetchone() if meta else None
        source_id = 'hk_hkel_iro_cap112' if meta and meta['expr_id'] == 'hk.cap112.en' else meta['expr_id'] if meta else ''
        if not public_hk_official(source_id, doc['url'] if doc else None):
            return EvidenceResult(status='restricted', reference=ref)
    row = lib.con.execute('SELECT text FROM clause WHERE cite_id = ?', (cite,)).fetchone()
    if not row or end > len(row[0]):
        return EvidenceResult(status='not_found', reference=ref)
    text = row[0][start:end]
    return EvidenceResult(status='ok', reference=ref, text=text, content_hash=sha256(text.encode()).hexdigest())
