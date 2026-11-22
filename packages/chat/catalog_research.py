"""Read the branch's multi-jurisdiction catalog for chat source navigation."""
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from urllib.parse import urlsplit

from packages.domain_bridge.tax_atlas import NAME_ZH

DATABASE = Path(__file__).resolve().parents[2] / 'database' / 'database.sqlite'
NAMES = dict(zip(
    ('cn', 'hk', 'sg', 'my', 'id', 'th', 'vn', 'jp', 'kr', 'in', 'ae'),
    ('Mainland China', 'Hong Kong', 'Singapore', 'Malaysia', 'Indonesia',
     'Thailand', 'Vietnam', 'Japan', 'South Korea', 'India', 'United Arab Emirates'),
))
INVENTORY = re.compile(
    r'(哪些|几个|多少|覆盖|支持|收录|都有).{0,24}(国家|地区|法域)|'
    r'(国家|地区|法域).{0,16}(覆盖|清单)|\b(which|what|how many)\b.{0,35}'
    r'\b(countries|jurisdictions)\b', re.I)
CATALOG = re.compile(r'数据库|资料库|法规库|知识库|catalog|database|library', re.I)
LOOKUP = re.compile(r'查找|找一下|检索|列出|原文|来源|\b(find|source|look up|show me)\b', re.I)
TAX = re.compile(r'所得税|利得税|税额抵免|法人税|\b(income tax|profits tax|corporation tax|foreign tax credit)\b', re.I)
TERMS = {
    'income tax': ('income tax', 'corporation tax', 'profits tax', '所得税', '利得税', '法人税', '소득세', '법인세'),
    'credit': ('foreign tax credit', 'foreign tax relief', '境外税额', '外国税額控除', '외국납부세액'),
}


def request(text):
    if INVENTORY.search(text) and CATALOG.search(text):
        return 'inventory'
    if not (LOOKUP.search(text) and TAX.search(text)):
        return None
    codes = [code for code, name in NAMES.items()
             if (NAME_ZH.get(code) and NAME_ZH[code] in text)
             or re.search(r'\b' + re.escape(name) + r'\b', text, re.I)
             or (code == 'cn' and '内地' in text)
             or (code == 'hk' and '香港' in text)]
    return codes[0] if len(codes) == 1 else None


def prepare(doc, text, locale, selection):
    en = locale == 'en'
    try:
        with closing(sqlite3.connect(DATABASE.as_uri() + '?mode=ro', uri=True)) as conn:
            if selection == 'inventory':
                counts = dict(conn.execute('SELECT jur, count(*) FROM doc GROUP BY jur'))
                rows = [f'- {name if en else NAME_ZH.get(code, name)} ({counts[code]}'
                        + (' documents)' if en else ' 份资料)')
                        for code, name in NAMES.items() if counts.get(code)]
                if not rows:
                    raise ValueError('Empty catalog')
                heading = (f'The current legal catalog contains domestic sources for {len(rows)} jurisdictions.'
                           if en else f'当前法规库收录了 {len(rows)} 个国家和地区的本地资料。')
                reply = heading + '\n\n' + '\n'.join(rows)
            else:
                reply = source_links(conn, text, selection, en)
    except (sqlite3.Error, ValueError):
        reply = ('The legal catalog is unavailable in this instance.' if en else '当前实例暂时无法读取法规库。')
    return {
        'turn': {'intent': 'chat', 'facts': {}, 'query': text, 'reply': reply},
        'patch': {}, 'conflicts': {}, 'research': None, 'answer': None,
        'workflow': {'version': 'catalog-chat-1', 'status': 'draft_ready', 'reply_locale': locale},
        'dialogue': doc.get('dialogue', {}), 'question': None,
    }


def source_links(conn, text, code, en):
    credit = bool(re.search(r'抵免|foreign tax credit', text, re.I))
    terms = TERMS['credit' if credit else 'income tax']
    rows = conn.execute(
        'SELECT id, title, url FROM doc WHERE jur = ? AND url IS NOT NULL ORDER BY id', (code,),
    )
    links = []
    article = re.search(r'第\s*(\d+)\s*[条條]|\b(?:article|section)\s+(\d+)\b', text, re.I)
    number = next(filter(None, article.groups())) if article else None
    for source_id, title, url in rows:
        if not any(term in (title or '').lower() for term in terms):
            continue
        parsed = urlsplit(url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or re.search(r'[<>\s]', url):
            continue
        label = re.sub(r'[\[\]<>\r\n]', '', title)
        if number:
            clauses = conn.execute(
                'SELECT cite_id, label, text FROM clause WHERE doc_id = ? ORDER BY cite_id', (source_id,),
            )
            for cite_id, locator, passage in clauses:
                pattern = rf'^\s*(?:第\s*{number}\s*[条條](?!の\d)|(?:article|section)\s*{number}(?![\w-])|제\s*{number}\s*조(?!의\d))'
                if not passage or (cite_id != f'{source_id}#{number}'
                                   and not re.search(pattern, (locator or '') + ' ', re.I)):
                    continue
                excerpt = re.sub(r'\s+', ' ', passage).strip()[:480]
                links.append(f'- [{label}](<{url}>) · `{cite_id}`\n\n  > {excerpt}')
                break
        else:
            links.append(f'- [{label}](<{url}>) · `{source_id}`')
        if len(links) == 6:
            break
    if not links:
        return ('No matching source was found in the local catalog.' if en
                else '本地法规库未找到匹配的资料或条文。')
    heading = ('Matching archived sources. Check the applicable period in the original.'
               if en else '找到以下归档资料，适用期间请核对原文。')
    return heading + '\n\n' + '\n'.join(links)
