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
TAX = re.compile(r'所得税|利得税|税额抵免|境外抵免|法人税|\b(income tax|profits tax|corporation tax|foreign tax credit)\b', re.I)
TERMS = {
    'income tax': ('income tax', 'corporation tax', 'profits tax', '所得税', '利得税', '法人税', '소득세', '법인세'),
    'credit': ('foreign tax credit', 'foreign tax relief', '境外税额', '外国税額控除', '외국납부세액'),
}


def jurisdictions(text):
    return [code for code, name in NAMES.items()
            if (NAME_ZH.get(code) and NAME_ZH[code] in text)
            or re.search(r'\b' + re.escape(name) + r'\b', text, re.I)
            or any(alias in text for alias in {'cn': ('内地', '中国大陆'), 'hk': ('香港',),
                   'kr': ('韩国',), 'ae': ('阿联酋',), 'my': ('马来西亚',)}.get(code, ()))]


def request(text):
    if INVENTORY.search(text) and CATALOG.search(text):
        return 'inventory'
    if not (LOOKUP.search(text) and TAX.search(text)):
        return None
    codes = jurisdictions(text)
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


# Answer only topics for which the catalog can retrieve question-specific clauses.
ANSWER_TOPICS = (
    (re.compile(r'境外.{0,10}抵免|外国.{0,10}抵免|foreign tax credit|double taxation relief', re.I),
     ('foreign tax credit', 'foreign tax paid', '外国税額', '外国法人税', '외국납부세액',
      '외국 납부 세액', '境外所得税', '境外已缴纳', '雙重課稅寬免')),
    (re.compile(r'税率|tax rates?|how much.*tax', re.I),
     ('corporate income tax rate', 'individual income tax rate', 'resident tax rates',
      '法人税率', '税率', '세율', 'tax rate', 'rate of tax')),
)
OFFICIAL_DOMAINS = {
    'cn': ('gov.cn',), 'hk': ('ird.gov.hk', 'elegislation.gov.hk'),
    'sg': ('iras.gov.sg', 'sso.agc.gov.sg'), 'jp': ('nta.go.jp', 'e-gov.go.jp'),
    'kr': ('law.go.kr', 'nts.go.kr'), 'in': ('incometax.gov.in', 'incometaxindia.gov.in'),
    'id': ('pajak.go.id', 'kemenkeu.go.id'), 'my': ('hasil.gov.my', 'agc.gov.my'),
    'th': ('rd.go.th', 'ratchakitcha.soc.go.th'), 'vn': ('gov.vn',),
    'ae': ('tax.gov.ae', 'mof.gov.ae', 'uaelegislation.gov.ae'),
}
PRIMARY_CREDIT_CLAUSES = {
    'jp': {'jp.cta#69'},
    'kr': {'kr.corporate-tax-act.20260701.ko#57'},
}


def answer_request(text):
    if not TAX.search(text):
        return None
    codes = jurisdictions(text)
    terms = next((terms for pattern, terms in ANSWER_TOPICS if pattern.search(text)), ())
    if len(codes) == 1 and terms:
        return codes[0], terms
    return None


def answer_question(doc, text, locale, selection):
    from packages.chat.library_research import _answer

    code, terms = selection
    def official(url):
        parsed = urlsplit(url)
        host = parsed.hostname or ''
        return parsed.scheme == 'https' and any(
            host == domain or host.endswith('.' + domain) for domain in OFFICIAL_DOMAINS[code])

    passages = []
    en = locale == 'en'
    year = re.search(r'(?<!\d)(20\d{2})(?!\d)', text)
    subject = ('personal' if re.search(r'个人|individual|personal', text, re.I) else
               'company' if re.search(r'企业|公司|法人|corporat|company', text, re.I) else None)
    rate_question = terms == ANSWER_TOPICS[1][1]
    if rate_question and (year is None or subject is None):
        reply = ('Which tax year, and is this for a company or an individual?' if en
                 else '请问是哪个课税年度，主体是企业还是个人？')
        response = {'text': reply, 'citations': [], 'answer_status': 'insufficient_evidence'}
    else:
        with closing(sqlite3.connect(DATABASE.as_uri() + '?mode=ro', uri=True)) as conn:
            rows = conn.execute(
                'SELECT c.cite_id, d.id, d.title, c.label, d.url, c.text, d.effective_from, d.effective_to '
                'FROM clause c JOIN doc d ON d.id = c.doc_id WHERE d.jur = ? ORDER BY c.cite_id', (code,))
            scored = []
            for cite, source, title, label, url, passage, start, end in rows:
                if not passage or not url or not official(url):
                    continue
                title_text = (title or '').lower()
                company_title = bool(re.search(r'corporat|company|法人税|법인세|企业所得税', title_text))
                personal_title = bool(re.search(r'individual|personal|个人所得税|(?<!법인)소득세법', title_text))
                if (subject == 'company' and personal_title and not company_title
                        or subject == 'personal' and company_title and not personal_title):
                    continue
                if year and ((start and start[:4] > year[1]) or (end and end[:4] < year[1])):
                    continue
                haystack = ((label or '') + ' ' + passage).lower()
                score = sum(term in haystack for term in terms)
                if score:
                    if not rate_question and cite in PRIMARY_CREDIT_CLAUSES.get(code, ()):
                        score += 10
                    if subject == 'company' and company_title:
                        score += 3
                    if subject == 'personal' and personal_title:
                        score += 3
                    if year and year[1] in title_text:
                        score += 2
                    scored.append((score, cite, dict(cite_id=cite, document_id=source, title=title,
                                  label=label, url=url, passage=passage[:3500],
                                  effective_from=start, effective_to=end)))
            per_doc = {}
            for _, _, item in sorted(scored, key=lambda row: (-row[0], row[1])):
                source = item['document_id']
                if per_doc.get(source, 0) >= 2:
                    continue
                passages.append(item)
                per_doc[source] = per_doc.get(source, 0) + 1
                if len(passages) == 8:
                    break
        research = {'library_version': 'branch-legal-catalog', 'passages': passages}
        response = _answer(text, research, locale, official=official, scope=f'{NAMES[code]} income tax')
    return {
        'turn': {'intent': 'research', 'facts': {}, 'query': text, 'reply': response['text']},
        'patch': {}, 'conflicts': {}, 'answer': response,
        'research': {'status': 'ok' if passages else 'no_match', 'passages': passages},
        'workflow': {'version': 'catalog-chat-1', 'reply_locale': locale,
                     'status': 'draft_ready' if passages else 'paused_gap'},
        'dialogue': doc.get('dialogue', {}), 'question': None,
    }
