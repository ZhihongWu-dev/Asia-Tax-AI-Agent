"""Text helpers shared by the retrieval indexes (agent/retrieval_spec.en.md §4.1): language, retrieval units, FTS tokens,
verbatim anchoring. Ported from the archived knowledge layer (archive/old-model-2026-10-31/official/tools/graph.py), where
they were evaluated (round-I synthesis §4, §6)."""
import re

CJK = re.compile(r"[㐀-鿿豈-﫿぀-ヿ]")       # Han, plus kana: Japanese is cut like Chinese
MAX_CJK, MAX_LAT = 260, 700          # about 100 words of English; similar reading load in Chinese
BLOCK = re.compile(r"(?m)^(?=(?:—)?\(\d+[A-Z]*\)|\([a-z]{1,4}\)\s|\([ivx]{1,6}\)\s|（[一二三四五六七八九十]+）|"
                   r"[一二三四五六七八九十]+、|第[一二三四五六七八九十百零〇\d]+[条款项]|\d+(?:\.\d+)*\s|[a-z]\)\s|Article \d+)")
SENT = re.compile(r"(?<=[。；;！？!?])|(?<=\.)\s+(?=[A-Z(“\"])|(?<=:)\n")
CN_DIGIT = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def lang_of(text):
    sample = text[:2000]
    n = len(sample) or 1
    if len(re.findall(r"[぀-ヿ]", sample)) / n > 0.02:
        return "ja"
    if len(re.findall(r"[฀-๿]", sample)) / n > 0.2:
        return "th"
    return "zh" if len(CJK.findall(sample)) / n > 0.2 else "en"


def cjk_like(lang):
    return lang in ("zh", "ja", "th")


def split_units(text, lang):
    """Verbatim spans [start, end) covering the text without gaps: structural markers first, then sentence ends,
    small neighbours merged up to the cap, what is still too long cut hard."""
    cap = MAX_CJK if cjk_like(lang) else MAX_LAT
    n = len(text)
    if n <= cap * 1.4:
        return [(0, n)]
    cuts = sorted({0, n} | {m.start() for m in BLOCK.finditer(text)})
    blocks = [(a, b) for a, b in zip(cuts, cuts[1:]) if b > a]
    pieces = []
    for a, b in blocks:
        if b - a <= cap:
            pieces.append((a, b))
            continue
        sc = sorted({a, b} | {a + m.end() for m in SENT.finditer(text[a:b])})
        pieces += [(x, y) for x, y in zip(sc, sc[1:]) if y > x]
    out, cur_a, cur_b = [], None, None
    for a, b in pieces:
        if cur_a is None:
            cur_a, cur_b = a, b
        elif b - cur_a <= cap:
            cur_b = b
        else:
            out.append((cur_a, cur_b))
            cur_a, cur_b = a, b
    if cur_a is not None:
        out.append((cur_a, cur_b))
    final = []
    for a, b in out:
        while b - a > cap * 1.5:
            final.append((a, a + cap))
            a += cap
        final.append((a, b))
    return [(a, b) for a, b in final if text[a:b].strip()]


def fts_tokens(text):
    """CJK and Thai runs as overlapping character bigrams (single characters stay), everything else as lower-case words."""
    out = []
    for run in re.findall(r"[㐀-鿿豈-﫿぀-ヿ฀-๿]+|[A-Za-z0-9À-ɏḀ-ỿ]+", text or ""):
        if CJK.match(run) or "฀" <= run[0] <= "๿":
            out += [run] if len(run) == 1 else [run[i:i + 2] for i in range(len(run) - 1)]
        else:
            out.append(run.lower())
    for m in re.finditer(r"(?<![\d,.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?![\d,])", text or ""):    # a figure also in its plain form:
        plain = m.group(1).replace(",", "")                                                       # 14,000,000.00 and 700000.0 -> 14000000, 700000
        if plain != m.group(0):
            out.append(plain)
    return " ".join(out)


def fts_query(text, min_len=2):
    """An FTS5 MATCH expression: every token quoted, joined by OR (BM25 ranks by how many and how rare)."""
    toks = [t for t in fts_tokens(text).split() if len(t) >= min_len or CJK.match(t)]
    toks = list(dict.fromkeys(toks))[:64]
    return " OR ".join('"%s"' % t.replace('"', "") for t in toks)


def anchor(text, quote):
    """Exact span of quote in text, whitespace ignored -> (start, end, occurrences)."""
    keep = [i for i, ch in enumerate(text) if not ch.isspace()]
    flat = "".join(text[i] for i in keep)
    q = re.sub(r"\s+", "", quote or "")
    if not q:
        return None, None, 0
    pos = [m.start() for m in re.finditer(re.escape(q), flat)]
    if not pos:
        return None, None, 0
    return keep[pos[0]], keep[pos[0] + len(q) - 1] + 1, len(pos)


def approx_anchor(text, quote, min_ratio=0.8):
    """Best approximate span of quote in text (OCR text): (start, end, ratio) or (None, None, best ratio)."""
    import difflib
    q = re.sub(r"\s+", "", quote or "")
    keep = [i for i, ch in enumerate(text) if not ch.isspace()]
    flat = "".join(text[i] for i in keep)
    if not q or not flat:
        return None, None, 0.0
    best = (0.0, 0)
    step = max(1, len(q) // 4)
    for s in range(0, max(1, len(flat) - len(q) + 1), step):
        r = difflib.SequenceMatcher(None, q, flat[s:s + len(q)], autojunk=False).ratio()
        if r > best[0]:
            best = (r, s)
    r, s = best
    if r < min_ratio:
        return None, None, round(r, 2)
    e = min(len(flat), s + len(q)) - 1
    return keep[s], keep[e] + 1, round(r, 2)


def cn2int(s):
    """Chinese numerals (up to the hundreds) or digits -> int; None when unreadable."""
    s = str(s or "").strip()
    if s.isdigit():
        return int(s)
    total, cur = 0, 0
    for ch in s:
        if ch in CN_DIGIT:
            cur = CN_DIGIT[ch]
        elif ch == "十":
            total += (cur or 1) * 10
            cur = 0
        elif ch == "百":
            total += (cur or 1) * 100
            cur = 0
        else:
            return None
    return total + cur


NUM = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?(?![\w])")


def numbers(text):
    """Every figure written in a text, as floats (thousands separators removed)."""
    out = set()
    for m in NUM.finditer(text or ""):
        try:
            out.add(float(m.group(1).replace(",", "") + ("." + m.group(2) if m.group(2) else "")))
        except ValueError:
            pass
    return out


def json_numbers(obj, out=None):
    """Every number in a JSON value."""
    out = set() if out is None else out
    if isinstance(obj, bool):
        return out
    if isinstance(obj, (int, float)):
        out.add(float(obj))
    elif isinstance(obj, str):
        out |= numbers(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            json_numbers(v, out)
    elif isinstance(obj, list):
        for v in obj:
            json_numbers(v, out)
    return out
