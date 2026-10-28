"""Shared, conservative helpers for the database collection tools.

The data package is intentionally CSV-first.  These helpers never silently
repair source rows: callers report a precise error and leave data unchanged.
"""
from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path
from urllib.parse import urlsplit

DATA = Path(__file__).resolve().parents[1]
csv.field_size_limit(2**31 - 1)

TABLES = {
    'jurisdiction': ['code', 'name', 'currency', 'company_in_scope', 'individual_in_scope'],
    'doc': ['id', 'jur', 'type', 'category', 'title', 'url', 'file', 'sha256', 'lang', 'effective_from', 'effective_to', 'note'],
    'files': ['path', 'sha256', 'bytes'],
    'clause': ['cite_id', 'doc_id', 'label', 'text'],
    'param': ['param_id', 'scope', 'subject', 'slot', 'name', 'value', 'unit', 'cite_id', 'quote', 'effective_from', 'effective_to', 'note'],
    'decision': ['id', 'jur', 'category', 'subject', 'slot', 'statement', 'cite_id', 'quote'],
    'treaty': ['pair', 'doc_id', 'in_force_from', 'mli_doc_id', 'note'],
}
TYPES = {'law', 'regulation', 'guidance', 'treaty', 'form', 'page', 'attachment'}
CATEGORIES = {str(i) for i in range(1, 10)} | {'page_treaties', 'page_rates', 'page_deadlines'}
SLOTS = {'outbound_wht', 'inbound', 'final', 'residence', 'cfc', 'anti_abuse'}
SUBJECTS = {'company', 'individual', 'all'}
UNITS = {'%', 'days', 'months', 'years', 'count', 'bool', 'text'}
OFFICIAL = {
    'fgk.chinatax.gov.cn', 'www.chinatax.gov.cn', 'szs.mof.gov.cn', 'www.npc.gov.cn', 'www.mofa.go.jp', 'www.mof.go.jp',
    'www.elegislation.gov.hk', 'www.ird.gov.hk', 'sso.agc.gov.sg', 'www.iras.gov.sg',
    'www.oecd.org', 'laws.e-gov.go.jp', 'www.law.go.kr', 'www.nts.go.kr', 'taxlaw.nts.go.kr', 'www.nta.go.jp', 'uaelegislation.gov.ae',
    'tax.gov.ae', 'www.tax.gov.ae', 'mof.gov.ae',
    'www.incometax.gov.in', 'incometaxindia.gov.in',
    'en.baochinhphu.vn', 'chinhphu.vn', 'www.hasil.gov.my', 'phl.hasil.gov.my', 'www.rd.go.th', 'www.pajak.go.id', 'pajak.go.id', 'stats.pajak.go.id', 'wmstatic-prd.incometaxindia.gov.in',
}


def rows(table: str) -> list[dict[str, str]]:
    path = DATA / f'{table}.csv'
    with path.open(encoding='utf-8-sig', newline='') as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != TABLES[table]:
            raise ValueError(f'{table}.csv headers differ from the data contract')
        return list(reader)


def write_rows(table: str, records: list[dict[str, str]]) -> None:
    path = DATA / f'{table}.csv'
    temporary = path.with_suffix('.csv.new')
    with temporary.open('w', encoding='utf-8', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=TABLES[table])
        writer.writeheader()
        writer.writerows(records)
    temporary.replace(path)


def sha256(path: Path) -> str:
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def whitespace_normalized(value: str) -> str:
    # Text extraction changes line wrapping. This preserves every non-space
    # character while making line-wrap-only differences visible as equivalent.
    return re.sub(r'\s+', '', value)


def is_date(value: str) -> bool:
    return not value or bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', value))


def is_pair(value: str, codes: set[str]) -> bool:
    left, sep, right = value.partition('-')
    return bool(sep and left in codes and right in codes and left < right)


def official_host(url: str) -> bool:
    return urlsplit(url).hostname in OFFICIAL
