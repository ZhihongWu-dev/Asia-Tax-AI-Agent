"""Deterministic retrieval of catalog sources; approved public excerpts may be summarized."""
from __future__ import annotations

import json
import re
from collections import Counter
from functools import lru_cache
from urllib.parse import urlsplit

from sqlalchemy import create_engine, select, or_, and_, case, func

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

# Navigation hints to existing source units, not tax determinations.
TOPIC_LOCATORS = [
    (r'外包|outsourc', ['s.15K(3)', 's.15K(2)']),
    (r'经济实质|經濟實質|economic substance|纯股权|純股權|pure equity', ['s.15K(1)', 's.15K(2)', 's.15K(3)']),
    (r'参[与股]豁免|參[與股]豁免|participation|持股比例|持有期|holding period', ['s.15M(1)', 's.15M(2)', 's.15N(2)', 's.15N(6)', 's.15N(7)', 's.15N(3)', 's.15N(4)']),
    (r'收取|汇回|匯回|境外银行|received|remit', ['s.15H(5)', 's.15H(6)', 's.15H(7)']),
    (r'抵免|重复征税|双重征税|交过税|credit|double tax', ['s.15N(5)', 's.15K(1)']),
    (r'反混合|hybrid', ['s.15N(3)']),
    (r'主要目的|main purpose', ['s.15N(4)']),
    (r'申报|申報|reporting|notification', ['s.15J']),
    (r'什么是|是什么|范围|適用|适用|what is|scope', ['s.15H(1)', 's.15I(1)', 's.15I(3)']),
]


def topic_locators(query: str) -> list[str]:
    return list(dict.fromkeys(ref for pattern, refs in TOPIC_LOCATORS
                             if re.search(pattern, query, re.I) for ref in refs))


def outside_scope(query: str) -> bool:
    outside = re.search(r'新加坡|美国|日本|内地|大陆|singapore|united states|japan|mainland|个人所得税|预提所得税', query, re.I)
    hk = re.search(r'香港|hong kong|\bHK\b|\bFSIE\b', query, re.I)
    return bool(outside and not hk and not any(references(query)))


def catalog() -> dict:
    return json.loads((FSIE_DIR / 'source_manifest.json').read_text(encoding='utf-8'))


@lru_cache(maxsize=1)
def knowledge_engine():
    return create_engine(get_settings().database_url, connect_args={
        'connect_timeout': 2, 'options': '-c statement_timeout=1000',
    }, pool_pre_ping=True, pool_size=3, max_overflow=2)


def references(query: str):
    # The corpus stores numeric subsections, so (2)(a) returns its full (2)
    # parent, never an invented paragraph-level citation. Accept full-width input.
    query = query.translate(str.maketrans('（）', '()'))
    locators = [
        's.' + match.group(1).upper() + (re.sub(r'\s+', '', match.group(2)) if match.group(2) else '')
        for match in re.finditer(r'(?<![a-z0-9])(?:s\.?\s*|sections?\s+)?(15[a-z]{1,2})(?![a-z0-9])\s*(\(\s*\d+\s*\))?', query, re.I)
    ]
    rulings = ['hk_ird_advance_' + match.group(1) for match in re.finditer(
        r'(?:ruling|case|裁定|案例)\s*(?:no\.?|第|编号|編號)?\s*(\d+)(?!\d)', query, re.I)]
    return list(dict.fromkeys(locators)), list(dict.fromkeys(rulings))


def locator_matches(locator: str | None, ref: str) -> bool:
    return locator == ref or ('(' not in ref and (locator or '').startswith(ref + '('))


def read_documents(query: str = '', kind: str = 'all', locators: list[str] | None = None,
                   context_ranges: list[tuple[str, int, int]] | None = None, unit_id: str | None = None) -> list[dict]:
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
    if unit_id is not None:
        conditions.append(LegalUnit.unit_ref == unit_id)
    if locators is not None:
        conditions.append(LegalUnit.statute_locator.in_(locators))
    if context_ranges is not None:
        if not context_ranges:
            return []
        conditions.append(or_(*(and_(Source.source_id == sid, LegalUnit.ordinal.between(lo, hi))
                                for sid, lo, hi in context_ranges)))
    if query:
        refs, rulings = references(query)
        if refs or rulings:
            matches = [LegalUnit.statute_locator == ref if '(' in ref else or_(
                LegalUnit.statute_locator == ref, LegalUnit.statute_locator.startswith(ref + '(')) for ref in refs]
            if rulings:
                matches.append(Source.source_id.in_(rulings))
            conditions.append(or_(*matches))
        else:
            tokens = terms(query)
            if not tokens:
                if topic_locators(query):
                    conditions.append(LegalUnit.statute_locator.in_(topic_locators(query)))
                elif re.search(r'\b(?:cases?|rulings?)\b|案例|裁定', query, re.I):
                    conditions.extend([LegalUnit.unit_type == 'ruling_block', LegalUnit.ordinal == 4])
                else:
                    return []
            else:
                token_matches = [LegalUnit.text.icontains(token, autoescape=True) for token in tokens]
                conditions.append(or_(*token_matches, LegalUnit.statute_locator.in_(topic_locators(query))))
    with knowledge_engine().connect() as connection:
        statement = select(
                LegalUnit.unit_ref, LegalUnit.statute_locator, LegalUnit.heading,
                LegalUnit.text, LegalUnit.text_sha256, LegalUnit.unit_type, LegalUnit.ordinal,
                Source.source_id, Source.actual_sha256, Source.manifest_sha256, Source.retrieved_at,
            ).join(Source, LegalUnit.source_db_id == Source.id).where(*conditions)
        if token_matches:
            # Bounded lexical candidate stage keeps full-page HTML tables off the wire.
            score = sum(case((condition, 1), else_=0) for condition in token_matches)
            priority = case((LegalUnit.statute_locator.in_(topic_locators(query)), 1), else_=0)
            statement = statement.order_by(priority.desc(), score.desc(), func.length(LegalUnit.text), LegalUnit.unit_ref).limit(120)
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
    if limit <= 0:
        return []
    candidates = [d for d in documents if kind == 'all' or
                  (kind == 'ruling' and d['unit_type'] == 'ruling_block') or
                  (kind == 'law' and d['locator']) or
                  (kind == 'guidance' and not d['locator'] and d['unit_type'] != 'ruling_block')]
    refs, rulings = references(query)
    if refs or rulings:
        ordered = sorted(candidates, key=lambda d: (d['source_id'], d['ordinal'], d['unit_id']))
        groups = [[d for d in ordered if locator_matches(d['locator'], ref)] for ref in refs]
        groups += [[d for d in ordered if d['source_id'] == sid][:7] for sid in rulings]
        result, seen = [], set()
        # Round-robin prevents one broad section consuming every available slot.
        while any(groups) and len(result) < limit:
            for group in groups:
                while group and group[0]['unit_id'] in seen:
                    group.pop(0)
                if group and len(result) < limit:
                    doc = group.pop(0)
                    seen.add(doc['unit_id'])
                    result.append(doc)
        return result
    tokens = terms(query)
    preferred = topic_locators(query)
    preferred_docs = [d for ref in preferred for d in candidates if d['locator'] == ref]
    if not tokens:
        if preferred_docs:
            return preferred_docs[:limit]
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
        coverage = hits / len(tokens)
        if len(tokens) >= 3 and coverage < 0.3:
            continue
        # One-line fragments should not outrank complete explanations.
        score = coverage + min(len(d['text']) / 250, 1) * 0.35
        scored.append((score, d))
    scored.sort(key=lambda pair: (-pair[0], pair[1]['unit_id']))
    counts: Counter = Counter()
    result = preferred_docs[:limit]
    seen = {d['unit_id'] for d in result}
    for _, doc in scored:
        if len(result) >= limit:
            break
        if doc['unit_id'] in seen:
            continue
        if counts[doc['source_id']] >= 2:
            continue
        counts[doc['source_id']] += 1
        result.append(doc)
        seen.add(doc['unit_id'])
        if len(result) >= limit:
            break
    return result


def search(query: str, kind: str = 'all', limit: int = 7) -> dict:
    try:
        if outside_scope(query):
            return {'status': 'no_matching_units', 'passages': [], 'reason': 'outside_scope',
                    'method': 'catalog_keyword_and_locator', 'query': query}
        results = rank_documents(read_documents(query=query, kind=kind), query, kind, limit)
        # Batch adjacent blocks once. Preserve every unit's ID and original hash.
        short = [d for d in results if not d['locator'] and d['unit_type'] != 'ruling_block' and len(d['text']) < 500]
        if short:
            neighbors = read_documents(context_ranges=[(d['source_id'], max(0, d['ordinal'] - 1), d['ordinal'] + 2) for d in short])
            for d in short:
                d['context'] = [p for p in neighbors if p['source_id'] == d['source_id']
                                and max(0, d['ordinal'] - 1) <= p['ordinal'] <= d['ordinal'] + 2
                                and p['unit_id'] != d['unit_id'] and p['snapshot_sha256'] == d['snapshot_sha256']][:3]
        return {'status': 'available' if results else 'no_matching_units', 'passages': results,
                'method': 'catalog_keyword_and_locator', 'query': query}
    except Exception:
        # Connection details, filesystem paths and raw DB errors stay on the server.
        return {'status': 'unavailable', 'passages': [], 'method': 'catalog_keyword_and_locator', 'query': query}
