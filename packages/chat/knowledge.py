"""Deterministic retrieval of approved catalog sources. No model receives originals."""
from __future__ import annotations

import json
import re
from collections import Counter
from functools import lru_cache
from urllib.parse import urlsplit

from sqlalchemy import create_engine, select, or_, case, func

from packages.knowledge_loader.parser import FSIE_DIR
from packages.persistence.config import get_settings
from packages.persistence.models import LegalUnit, Source

TOPICS = {
    '股息': 'dividend', '经济实质': 'economic substance', '經濟實質': 'economic substance',
    '参与豁免': 'participation exemption', '參與豁免': 'participation exemption',
    '持股': 'equity holding', '雇员': 'employees', '僱員': 'employees',
    '外包': 'outsourcing', '境外纳税': 'foreign tax', '境外納稅': 'foreign tax',
    '反混合': 'hybrid mismatch', '主要目的': 'main purpose', '抵免': 'tax credit',
    '收取': 'received', '申报': 'notification reporting', '申報': 'notification reporting',
    '金融实体': 'financial entity', '金融實體': 'financial entity',
    '裁定': 'ruling', '案例': 'ruling', '实物': 'in-kind', '實物': 'in-kind',
    '官方资料': 'dividend exemption', '官方資料': 'dividend exemption',
}
STOP = set('a an the what which how why is are was were do does can could should please explain tell me about of for to in on with and or my our this that have has i we you it case cases ruling rulings section fsie'.split())
STOP.update('there any show list available official source sources some us find look up detail details provide'.split())


def catalog() -> dict:
    return json.loads((FSIE_DIR / 'source_manifest.json').read_text(encoding='utf-8'))


@lru_cache(maxsize=1)
def knowledge_engine():
    return create_engine(get_settings().database_url, connect_args={
        'connect_timeout': 5, 'options': '-c statement_timeout=10000',
    }, pool_pre_ping=True, pool_size=3, max_overflow=2)


def references(query: str):
    locator = re.search(r'(?:s\.?\s*|section\s+|第\s*)(15[a-z])\s*(\(\d+\))?', query, re.I)
    ruling = re.search(r'(?:ruling|case|裁定|案例)\s*(?:no\.?|第|编号|編號)?\s*(\d+)(?!\d)', query, re.I)
    return locator, ruling


def read_documents(query: str = '', kind: str = 'all', locators: list[str] | None = None) -> list[dict]:
    manifest = catalog()
    entries = {s['source_id']: s for s in manifest['sources'] if s.get('l0_in_scope', True)
               and urlsplit(s['url']).hostname in manifest['allowed_source_domains']}
    conditions = [Source.source_id.in_(entries), Source.l0_in_scope.is_(True), Source.parse_status == 'parsed']
    token_matches = []
    if kind == 'ruling':
        conditions.append(LegalUnit.unit_type == 'ruling_block')
    elif kind == 'law':
        conditions.append(LegalUnit.statute_locator.is_not(None))
    elif kind == 'guidance':
        conditions.extend([LegalUnit.statute_locator.is_(None), LegalUnit.unit_type != 'ruling_block'])
    if locators is not None:
        conditions.append(LegalUnit.statute_locator.in_(locators))
    if query:
        locator, ruling = references(query)
        if ruling:
            conditions.append(Source.source_id == 'hk_ird_advance_' + ruling.group(1))
        elif locator:
            ref = 's.' + locator.group(1).upper() + (locator.group(2) or '')
            conditions.append(LegalUnit.statute_locator == ref if locator.group(2) else or_(
                LegalUnit.statute_locator == ref, LegalUnit.statute_locator.startswith(ref + '(')))
        else:
            tokens = terms(query)
            if not tokens:
                if re.search(r'\b(?:cases?|rulings?)\b|案例|裁定', query, re.I):
                    conditions.extend([LegalUnit.unit_type == 'ruling_block', LegalUnit.ordinal == 4])
                else:
                    return []
            else:
                token_matches = [LegalUnit.text.icontains(token, autoescape=True) for token in tokens]
                conditions.append(or_(*token_matches))
    with knowledge_engine().connect() as connection:
        statement = select(
                LegalUnit.unit_ref, LegalUnit.statute_locator, LegalUnit.heading,
                LegalUnit.text, LegalUnit.text_sha256, LegalUnit.unit_type, LegalUnit.ordinal,
                Source.source_id, Source.actual_sha256, Source.manifest_sha256, Source.retrieved_at,
            ).join(Source, LegalUnit.source_db_id == Source.id).where(*conditions)
        if token_matches:
            # Bounded lexical candidate stage keeps full-page HTML tables off the wire.
            score = sum(case((condition, 1), else_=0) for condition in token_matches)
            statement = statement.order_by(score.desc(), func.length(LegalUnit.text), LegalUnit.unit_ref).limit(120)
        else:
            statement = statement.order_by(Source.source_id, LegalUnit.ordinal)
        rows = connection.execute(statement).all()
    return [{
            'unit_id': r.unit_ref, 'locator': r.statute_locator, 'heading': r.heading,
            'text': r.text, 'text_sha256': r.text_sha256, 'unit_type': r.unit_type,
            'ordinal': r.ordinal, 'source_id': r.source_id,
            'title': entries[r.source_id]['title'], 'url': entries[r.source_id]['url'],
            'snapshot_sha256': r.actual_sha256, 'manifest_sha256': r.manifest_sha256,
            'retrieved_at': r.retrieved_at.isoformat() if r.retrieved_at else None,
            'drift': bool(r.actual_sha256 and r.manifest_sha256 and r.actual_sha256 != r.manifest_sha256),
            'professional_validation_status': 'unverified',
            'coverage_cutoff': manifest['legal_coverage_cutoff'],
        } for r in rows]


def terms(query: str) -> list[str]:
    expanded = query.lower()
    for zh, en in TOPICS.items():
        if zh in query:
            expanded += ' ' + en
    tokens = list(dict.fromkeys(w for w in re.findall(r'[a-z][a-z-]+', expanded) if w not in STOP))[:16]
    if not tokens and re.search(r'\bfsie\b', query, re.I):
        return ['foreign-sourced', 'income', 'exemption']
    return tokens


def rank_documents(documents: list[dict], query: str, kind: str = 'all', limit: int = 6) -> list[dict]:
    candidates = [d for d in documents if kind == 'all' or
                  (kind == 'ruling' and d['unit_type'] == 'ruling_block') or
                  (kind == 'law' and d['locator']) or
                  (kind == 'guidance' and not d['locator'] and d['unit_type'] != 'ruling_block')]
    locator, ruling = references(query)
    if ruling:
        sid = 'hk_ird_advance_' + ruling.group(1)
        return [d for d in candidates if d['source_id'] == sid][:min(limit, 7)]
    if locator:
        ref = 's.' + locator.group(1).upper() + (locator.group(2) or '')
        return [d for d in candidates if d['locator'] == ref or
                (not locator.group(2) and (d['locator'] or '').startswith(ref + '('))][:limit]
    tokens = terms(query)
    if not tokens:
        if re.search(r'\b(?:cases?|rulings?)\b|案例|裁定', query, re.I):
            return [d for d in candidates if d['unit_type'] == 'ruling_block' and d['ordinal'] == 4][:limit]
        return []
    scored = []
    for d in candidates:
        words = set(re.findall(r'[a-z][a-z-]+', (d['text'] + ' ' + (d['heading'] or '')).lower()))
        hits = sum(any(w == t or w == t + 's' for w in words) for t in tokens)
        if not hits:
            continue
        # Avoid returning an entire long page ahead of a focused paragraph.
        score = hits / len(tokens) + hits / (1 + len(d['text']) / 800)
        scored.append((score, d))
    scored.sort(key=lambda pair: (-pair[0], pair[1]['unit_id']))
    counts: Counter = Counter()
    result = []
    for _, doc in scored:
        if counts[doc['source_id']] >= 2:
            continue
        counts[doc['source_id']] += 1
        result.append(doc)
        if len(result) >= limit:
            break
    return result


def search(query: str, kind: str = 'all', limit: int = 7) -> dict:
    try:
        results = rank_documents(read_documents(query=query, kind=kind), query, kind, limit)
        return {'status': 'available' if results else 'no_matching_units', 'passages': results,
                'method': 'catalog_keyword_and_locator', 'query': query}
    except Exception:
        # Connection details, filesystem paths and raw DB errors stay on the server.
        return {'status': 'unavailable', 'passages': [], 'method': 'catalog_keyword_and_locator', 'query': query}
