#!/usr/bin/env python
"""Build of the minimal library (database/数据库规范.md): raw files -> text -> clauses, checks, sqlite, STATUS.md.

Conda env "tax" (Python 3.11); packages in database/requirements.txt.   python database/tools/build.py [--root DIR]

Filled by AI or by hand (one csv per table, in the root):
  jurisdiction.csv treaty.csv doc.csv param.csv decision.csv superseded.csv
Generated (never filled by hand):
  text/<doc_id>.txt, files.csv, clause.csv, database.sqlite, STATUS.md
Exit code 0 when the checks find no error, 1 otherwise; gaps are reported, not counted as errors.
--jur <code> checks one jurisdiction on its own rows and writes nothing: PASSED (exit 0) on zero errors and zero gaps
(数据库规范.md §5).

doc / rtf / xls / ppt are converted with LibreOffice (headless) in a temporary folder.
"""
import argparse
import csv
import hashlib
import io
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
from datetime import date
import xml.etree.ElementTree as ET
from pathlib import Path

import pymupdf as fitz           # PyMuPDF
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from xfa_text import is_xfa, xfa_text    # noqa: E402  dynamic (XFA) forms keep their text in an XML template
from fetch import is_official             # noqa: E402  the list of official hosts lives in fetch.py

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
csv.field_size_limit(10 ** 9)
ROOT = Path(__file__).resolve().parents[1]          # database/; --root points elsewhere (tests)
ENC = "utf-8-sig"
SOFFICE = r"C:\Program Files\LibreOffice\program\soffice.exe"

# ---------------------------------------------------------------- tables (数据库规范.md §3)
TABLES = {                                           # name -> columns; the order is the csv and sqlite column order
    "jurisdiction": ["code", "name", "currency", "company_in_scope", "individual_in_scope"],
    "treaty": ["pair", "doc_id", "in_force_from", "mli_doc_id", "note"],
    "doc": ["id", "jur", "type", "category", "title", "url", "file", "sha256", "lang", "effective_from", "effective_to", "note"],
    "clause": ["cite_id", "doc_id", "label", "text"],
    "param": ["param_id", "scope", "subject", "slot", "name", "value", "unit", "cite_id", "quote",
              "effective_from", "effective_to", "note", "changed_on", "superseded_by"],
    "files": ["path", "sha256", "bytes"],
    "decision": ["id", "jur", "category", "subject", "slot", "statement", "cite_id", "quote"],
}
FILLED = ["jurisdiction", "treaty", "doc", "param", "decision"]
SUPERSEDED = ["doc_id", "clause", "by", "since", "note", "phrase"]     # clauses replaced by a protocol or the MLI (§4.3)
SUBJECTS = ("company", "individual", "all")
SLOTS = ("outbound_wht", "inbound", "final", "residence", "cfc", "anti_abuse", "penalty", "restructure")
DOC_TYPES = ("law", "regulation", "guidance", "treaty", "form", "page", "attachment")
CATEGORIES = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "page_treaties", "page_rates", "page_deadlines")   # §2
COVERED_CATEGORIES = tuple(c for c in CATEGORIES if c != "11")   # 11 = interpretive sources: optional, never a parameter source
LEGAL_CATEGORIES = ("1", "2", "3", "4", "9")       # an absence record of these must cite the clause that sets the scope of the tax
UNITS = ("%", "days", "months", "years", "count", "bool", "text")   # plus the currency codes of jurisdiction.csv (数据库规范.md §4.4)
NUMERIC_UNITS = ("%", "days", "months", "years", "count")

# ---------------------------------------------------------------- helpers
CN_NUM = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def cn2int(s):
    total, cur = 0, 0
    for ch in s:
        if ch in CN_NUM:
            cur = CN_NUM[ch]
        elif ch == "十":
            total += (cur or 1) * 10
            cur = 0
        elif ch == "百":
            total += (cur or 1) * 100
            cur = 0
        else:
            return None
    return total + cur


def read_csv(path):
    """Rows of a csv; a byte order mark left inside the file by an appending program is ignored."""
    if not path.exists():
        return []
    with path.open(encoding=ENC, newline="") as f:
        return [{(k or "").replace("\ufeff", ""): (v or "").replace("\ufeff", "") if isinstance(v, str) else v for k, v in r.items()}
                for r in csv.DictReader(f)]


def write_csv(path, fields, rows):
    with path.open("w", encoding=ENC, newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def init_csvs():
    """First run on an empty root: write the header of every csv that is filled by AI or by hand."""
    for name in FILLED:
        p = ROOT / (name + ".csv")
        if not p.exists():
            write_csv(p, TABLES[name], [])
    p = ROOT / "superseded.csv"
    if not p.exists():
        write_csv(p, SUPERSEDED, [])

# ---------------------------------------------------------------- raw -> text: readers
def real_kind(path, ext):
    head = path.read_bytes()[:8]
    ext = ext.lower()
    if head.startswith(b"%PDF-"):
        return "pdf"
    if head.startswith(b"{\\rtf"):
        return "rtf"
    if head.startswith(b"\xd0\xcf\x11\xe0"):
        return "xls" if ext in ("xls", "et") else ("ppt" if ext in ("ppt", "pps") else "doc")
    if head.startswith(b"PK"):
        return "xlsx" if ext in ("xlsx", "xls") else ("pptx" if ext == "pptx" else "docx")
    return ext


def html_text(raw):
    soup = BeautifulSoup(raw, "lxml")
    for t in soup(["script", "style", "noscript", "header", "footer", "nav", "iframe"]):
        t.decompose()
    whole = len((soup.body or soup).get_text(strip=True))
    for t in soup("form"):                            # page chrome — unless the form is the document itself (the
        if len(t.get_text(strip=True)) < 0.9 * whole:  # Judiciary's LRS wraps a whole judgment in one <form>)
            t.decompose()
    body = soup.body or soup
    ps = body.find_all("p")
    total = sum(len(p.get_text(strip=True)) for p in ps)
    node = body
    if total > 400:                                   # descend to the smallest container holding most <p> text
        while True:
            best = None
            for child in node.find_all(recursive=False):
                if child.name == "p":
                    continue
                share = sum(len(p.get_text(strip=True)) for p in child.find_all("p"))
                if share >= 0.7 * total:
                    best = child
            if best is None:
                break
            node = best
    text = node.get_text("\n")
    lines = [re.sub(r"[ \t\u00a0\u3000]+", " ", ln).strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def pdf_pages(path):
    with fitz.open(path) as doc:
        return [page.get_text("text") for page in doc]


def docx_text(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    xml = re.sub(r"</w:p>", "\n", xml)
    return re.sub(r"<[^>]+>", "", xml)


def xlsx_text(path):
    import openpyxl
    wb = openpyxl.load_workbook(str(path), data_only=True)
    out = []
    for ws in wb.worksheets:
        out.append("## sheet: %s" % ws.title)
        for row in ws.iter_rows(values_only=True):
            cells = [str(c).strip() for c in row if c is not None and str(c).strip()]
            if cells:
                out.append(" | ".join(cells))
    return "\n".join(out)

# ---------------------------------------------------------------- raw -> text: conversion
def soffice_convert(jobs, conv):
    """jobs: [(src_path, kind, key)]. Writer formats -> txt, calc formats -> xlsx, slides -> pdf, into the folder conv."""
    tmp = conv / "in"
    for target, kinds in (("txt:Text (encoded):UTF8", ("doc", "rtf")), ("xlsx", ("xls",)), ("pdf", ("ppt", "pptx"))):
        todo = []
        for src, kind, key in jobs:
            if kind in kinds:
                tmp.mkdir(exist_ok=True)
                dst = tmp / ("%s.%s" % (key, kind))
                shutil.copyfile(str(src), str(dst))
                todo.append(str(dst))
        for i in range(0, len(todo), 8):
            profile = "file:///" + str(conv / "lo_profile").replace("\\", "/")
            subprocess.run([SOFFICE, "--headless", "--norestore", "-env:UserInstallation=" + profile,
                            "--convert-to", target, "--outdir", str(conv)] + todo[i:i + 8],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1800)
        if tmp.exists():
            shutil.rmtree(str(tmp), ignore_errors=True)


def to_text(row, kind, conv):
    """Returns (text, pages or None, status)."""
    path = ROOT / row["file"]
    key = row["sha256"][:16] or row["id"]
    try:
        if kind in ("html", "htm"):
            return html_text(path.read_bytes()), None, "ok"
        if kind == "pdf":
            pages = pdf_pages(path)
            text = "\n".join(pages)
            if len(text) < 3000 and ("Please wait" in text or is_xfa(path)):
                t = xfa_text(path)
                return (t, None, "xfa_template") if t else (text, pages, "xfa_form_no_text")
            return text, pages, "ok" if len(text.strip()) > 200 else "scanned_or_empty"
        if kind == "docx":
            return docx_text(path), None, "ok"
        if kind == "xlsx":
            return xlsx_text(path), None, "ok"
        if kind in ("doc", "rtf"):
            f = conv / (key + ".txt")
            return (f.read_text(encoding="utf-8-sig", errors="replace"), None, "ok") if f.exists() \
                else ("", None, "convert_failed")
        if kind == "xls":
            f = conv / (key + ".xlsx")
            return (xlsx_text(f), None, "ok") if f.exists() else ("", None, "convert_failed")
        if kind in ("ppt", "pptx"):
            f = conv / (key + ".pdf")
            if not f.exists():
                return "", None, "convert_failed"
            pages = pdf_pages(f)
            return "\n".join(pages), pages, "ok"
        if kind in ("md", "txt", "json"):
            return path.read_text(encoding="utf-8", errors="replace"), None, "ok"
        if kind == "xml":
            return xml_text(row), None, "ok"
        return "", None, "unsupported:" + kind
    except Exception as e:                            # noqa: BLE001
        return "", None, "error:%s" % type(e).__name__

# ---------------------------------------------------------------- slicers
RE_CN_ART = re.compile(r"^第([一二三四五六七八九十百零〇两]+)[条條]\s*(.*)$")
RE_CN_ITEM = re.compile(r"^([一二三四五六七八九十]+)、\s*(.*)$")
RE_EN_ART = re.compile(r"^ARTICLE\s+(\d+)\b\s*(.*)$", re.I)
RE_EN_ART_HEAD = re.compile(r"^ARTICLE\s+(\d+)\b(?!\s*[(,.;:]|\s+(?:of|and|to|in|shall|is|are|as|the|or|which|with)\b)\s*(.*)$", re.I)   # not "Article 1 of the Agreement shall be replaced"
RE_EN_PARA = re.compile(r"^(\d{1,2})\.(?:\s+(\S.*))?$")      # "1." may sit alone on a line in PDF text
RE_PAGENO = re.compile(r"^-?\s*\d{1,3}\s*-?$")
RE_CHAPTER = re.compile(r"^第[一二三四五六七八九十百]+[章节節]\s*\S{0,20}(\s\S{0,6}){0,6}$")
RE_SPLIT_HEAD = re.compile(r"^第[一二三四五六七八九十百零〇两]*$")
RE_SPLIT_TAIL = re.compile(r"^[一二三四五六七八九十百零〇两]*[条條]")


def clean_lines(text):
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not RE_PAGENO.match(ln.strip())]
    lines = [ln for ln in lines if not RE_CHAPTER.match(ln)]
    out, i = [], 0
    while i < len(lines):                              # "第" + "二十三条 ..." were split by an inline tag
        if i + 1 < len(lines) and RE_SPLIT_HEAD.match(lines[i]) and RE_SPLIT_TAIL.match(lines[i + 1]):
            out.append(lines[i] + lines[i + 1])
            i += 2
        else:
            out.append(lines[i])
            i += 1
    return out


def split_paras(block, matcher, number):
    """Split an article body into consecutively numbered paragraphs."""
    paras, cur, buf = [], None, []
    for ln in block:
        m = matcher.match(ln)
        if m and number(m.group(1)) == (cur or 0) + 1:
            if cur is not None:
                paras.append((cur, buf))
            cur, buf = number(m.group(1)), [ln]
        elif cur is not None:
            buf.append(ln)
    if cur is not None:
        paras.append((cur, buf))
    return paras


def pick_run(lines, regex, number):
    """Headings must be numbered consecutively; a jump is accepted only for a short title-like line.
    A restart at 1 opens a new run (table of contents first, or a second instrument in an annex).
    Returns the first run whose blocks are real text, as [(line_index, number)], plus the end line."""
    runs, cur, last = [], [], 0
    for i, ln in enumerate(lines):
        m = regex.match(ln)
        if not m:
            continue
        no = number(m.group(1))
        if no is None:
            continue
        title_like = len(ln) <= 24 and not re.search(r"[，。；：,;]", ln)
        if no == 1 and last >= 2:
            runs.append(cur)
            cur, last = [], 0
        if no == last + 1 or (no > last + 1 and title_like):
            cur.append((i, no))
            last = no
    runs.append(cur)
    runs = [r for r in runs if r]
    if not runs:
        return [], len(lines)
    bounds = [r[0][0] for r in runs] + [len(lines)]
    best = None
    for k, r in enumerate(runs):
        chars = sum(len(x) for x in lines[r[0][0]:bounds[k + 1]])
        if chars >= 150 * len(r) and len(r) >= 3:
            best = k
            break
    if best is None:
        best = max(range(len(runs)), key=lambda k: len(runs[k]))
    return runs[best], bounds[best + 1]


RE_PROTOCOL = re.compile(r"^.{0,30}(议\s*定\s*书|議\s*定\s*書)$|^PROTOCOL$"
                         r"|^(?:Paragraphs\s+\d+\s+to\s+\d+\s+of\s+the\s+)?Protocol\s+to\s+the\s+Agreement\b", re.I)   # last: Hong Kong s.49 orders
RE_SCHEDULE = re.compile(r"^Schedule\s+(\d+)\s*$", re.I)
RE_ANNEX_HEAD = re.compile(r"^(ANNEX|Annex|SCHEDULE|Schedule)\s+([A-Z]|\d{1,2})\s*$")


RE_EN_ART_ROMAN = re.compile(r"^ARTICLE\s+([IVXLC]+)\b(?!\s*[(,.;:]|\s+(?:of|and|to|in|shall|is|are|as|the|or|which|with)\b)\s*(.*)$")
ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def roman_int(r):
    n = 0
    for a, b in zip(r, r[1:] + " "):
        n += -ROMAN[a] if ROMAN.get(b, 0) > ROMAN[a] else ROMAN[a]
    return n


def annex_article_no(line):
    """Article number of an annex heading line: 'ARTICLE 3' or, in protocols, 'ARTICLE IV' (-> 4); else None."""
    m = RE_EN_ART_HEAD.match(line)
    if m:
        return int(m.group(1))
    m = RE_EN_ART_ROMAN.match(line)
    return roman_int(m.group(1)) if m else None


def annex_clauses(doc_id, lines):
    """lines begin at the first 'ANNEX A' / 'Schedule 2' heading after the treaty's last article. Each heading opens a
    block named annex<X> or sch<N>. A block whose articles restart at Article 1 (a protocol, an earlier convention)
    slices by article (Roman numerals counted as numbers, ARTICLE IV -> 4): <doc>#annexB.1, paragraphs <doc>#annexB.1.2. Any other block (e.g. Singapore's Annex A listing
    the MLI amendments) is one clause <doc>#annexA with its numbered items <doc>#annexA.2."""
    heads = [j for j, ln in enumerate(lines) if RE_ANNEX_HEAD.match(ln)]
    out = []
    for k, h in enumerate(heads):
        kind_word, tag = RE_ANNEX_HEAD.match(lines[h]).groups()
        name = ("sch" if kind_word.lower() == "schedule" else "annex") + tag
        block = lines[h:heads[k + 1] if k + 1 < len(heads) else len(lines)]
        grp, last = [], 0
        for i, ln in enumerate(block):
            no = annex_article_no(ln)
            if no is None:
                continue
            if no == last + 1:
                grp.append((i, no))
                last = no
            elif no == 1 and grp:
                break
        if grp:
            for kk, (i, no) in enumerate(grp):
                part = block[i:grp[kk + 1][0] if kk + 1 < len(grp) else len(block)]
                cid = "%s#%s.%s" % (doc_id, name, no)
                out.append({"cite_id": cid, "doc_id": doc_id, "kind": "article", "label": "%s, Article %s" % (name, no),
                            "parent": "", "text": "\n".join(part)})
                for n, buf in split_paras(part[1:], RE_EN_PARA, int):
                    out.append({"cite_id": "%s.%s" % (cid, n), "doc_id": doc_id, "kind": "paragraph",
                                "label": "%s, Article %s(%s)" % (name, no, n), "parent": cid, "text": "\n".join(buf)})
            continue
        cid = "%s#%s" % (doc_id, name)
        out.append({"cite_id": cid, "doc_id": doc_id, "kind": "annex", "label": name, "parent": "", "text": "\n".join(block)})
        for n, buf in split_paras(block[1:], RE_EN_PARA, int):
            out.append({"cite_id": "%s.%s" % (cid, n), "doc_id": doc_id, "kind": "item", "label": "%s(%s)" % (name, n),
                        "parent": cid, "text": "\n".join(buf)})
    return out


def slice_articles(doc_id, text, regex, number, para_regex, para_number, fmt_art, fmt_para, mode):
    lines = clean_lines(text)
    run, end = pick_run(lines, regex, number)
    out = []
    if len(run) < 3:
        return out, "none"
    for k, (i, no) in enumerate(run):
        stop = run[k + 1][0] if k + 1 < len(run) else end
        block = lines[i:stop]
        if k + 1 == len(run):                          # a protocol may follow the last article
            for j, ln in enumerate(block[1:], 1):
                if RE_PROTOCOL.match(ln):
                    out.append({"cite_id": doc_id + "#protocol", "doc_id": doc_id, "kind": "protocol",
                                "label": "议定书", "parent": "", "text": "\n".join(block[j:])})
                    for n, buf in split_paras(block[j + 1:], para_regex, para_number):
                        out.append({"cite_id": "%s#protocol.%s" % (doc_id, n), "doc_id": doc_id,
                                    "kind": "paragraph", "label": "议定书第%s条" % n,
                                    "parent": doc_id + "#protocol", "text": "\n".join(buf)})
                    block = block[:j]
                    break
        cid = "%s#%s" % (doc_id, no)
        out.append({"cite_id": cid, "doc_id": doc_id, "kind": "article", "label": fmt_art % no, "parent": "",
                    "text": "\n".join(block)})
        for n, buf in split_paras(block[1:], para_regex, para_number):
            out.append({"cite_id": "%s.%s" % (cid, n), "doc_id": doc_id, "kind": "paragraph",
                        "label": fmt_para % (no, n), "parent": cid, "text": "\n".join(buf)})
    return out, mode


def slice_cn(doc_id, text):
    """Chinese legal text. Article mode (第X条) if present, else top-level item mode (一、二、)."""
    out, mode = slice_articles(doc_id, text, RE_CN_ART, cn2int, RE_CN_ITEM, cn2int,
                               "第%s条", "第%s条第%s款", "cn_article")
    if out:
        return out, mode
    for n, buf in split_paras(clean_lines(text), RE_CN_ITEM, cn2int):
        out.append({"cite_id": "%s#i%s" % (doc_id, n), "doc_id": doc_id, "kind": "item", "label": "第%s项" % n,
                    "parent": "", "text": "\n".join(buf)})
    return out, "cn_item" if out else "none"


RE_MLI_BOX = re.compile(r"\bArticle\s+(\d+)\s+of\s+the\s+MLI\b.*\b(applies|apply|supersede|supersedes|replace|replaces|modif|"
                        r"is\s+added|are\s+added|shall\s+apply)", re.I)


RE_MLI_HEAD = re.compile(r"^\s*The following\b", re.I)


def mli_box_starts(lines):
    """(line index, MLI article) where a boxed MLI provision begins. The header may break over two lines
    ('The following paragraph 1 of Article 4 and subparagraph e) of paragraph 3 of Article' / '4 of the MLI replace
    paragraph 3 of Article 4 of this Agreement:'); the box then starts at its first line."""
    out = []
    for k in range(1, len(lines)):
        m = RE_MLI_BOX.search(lines[k])
        if not m and RE_MLI_HEAD.match(lines[k]) and k + 1 < len(lines):
            m = RE_MLI_BOX.search(lines[k] + " " + lines[k + 1])
        if m and not (out and out[-1][0] == k - 1 and RE_MLI_HEAD.match(lines[k - 1])):
            out.append((k, m.group(1)))
    return out


def later_instruments(doc_id, text):
    """Articles of a later instrument printed after the treaty in the same file, e.g. a Hong Kong s.49 order whose
    Schedule 2 holds the Second Protocol ('Article 1' to 'Article 3' after the treaty's last article). Each restart at
    Article 1 opens a group, named after the nearest 'Schedule N' line above it (else 'annex<k>'):
    <doc>#sch2.1, paragraphs <doc>#sch2.1.1."""
    lines = clean_lines(text)
    run, end = pick_run(lines, RE_EN_ART_HEAD, int)
    if len(run) < 3:
        return []
    groups, cur, last = [], [], 0
    for i in range(end, len(lines)):
        m = RE_EN_ART_HEAD.match(lines[i])
        if not m:
            continue
        no = int(m.group(1))
        if no == 1:
            if cur:
                groups.append(cur)
            cur, last = [(i, no)], 1
        elif cur and no == last + 1:
            cur.append((i, no))
            last = no
    if cur:
        groups.append(cur)
    out = []
    for g, grp in enumerate(groups, 1):
        name = "annex%d" % g
        for j in range(grp[0][0] - 1, run[-1][0], -1):
            m = RE_SCHEDULE.match(lines[j])
            if m:
                name = "sch" + m.group(1)
                break
        nxt = groups[g][0][0] if g < len(groups) else len(lines)
        for k, (i, no) in enumerate(grp):
            stop = grp[k + 1][0] if k + 1 < len(grp) else nxt
            block = lines[i:stop]
            cid = "%s#%s.%s" % (doc_id, name, no)
            out.append({"cite_id": cid, "doc_id": doc_id, "kind": "article", "label": "%s, Article %s" % (name, no),
                        "parent": "", "text": "\n".join(block)})
            for n, buf in split_paras(block[1:], RE_EN_PARA, int):
                out.append({"cite_id": "%s.%s" % (cid, n), "doc_id": doc_id, "kind": "paragraph",
                            "label": "%s, Article %s(%s)" % (name, no, n), "parent": cid, "text": "\n".join(buf)})
    return out


def slice_en_treaty(doc_id, text):
    """English treaties by Article, paragraphs '1.'. In a synthesised text (treaty as modified by the MLI) each boxed
    MLI provision opens with a line such as 'The following paragraph 1 of Article 7 of the MLI applies to the
    Agreement:'; from there to the next such line or the end of the article it is its own clause <doc>#<art>.mli<N>
    (N = the MLI article), and the article's own paragraphs are counted outside the boxes only. Checked on the Japanese
    Ministry of Finance texts (2026-10-23): India and Indonesia treaties (29 and 30 articles), synthesised texts with
    Malaysia and Thailand (28 and 27 articles)."""
    lines = clean_lines(text)
    run, _ = pick_run(lines, RE_EN_ART_HEAD, int)
    cut = None
    if len(run) >= 3:                                     # the treaty ends at the first annex or schedule heading after its last article
        cut = next((j for j in range(run[-1][0] + 1, len(lines)) if RE_ANNEX_HEAD.match(lines[j])), None)
    main = "\n".join(lines[:cut]) if cut is not None else text
    out, mode = slice_articles(doc_id, main, RE_EN_ART_HEAD, int, RE_EN_PARA, int, "Article %s", "Article %s(%s)", "en_article")
    if not out:
        return out, mode
    out += annex_clauses(doc_id, lines[cut:]) if cut is not None else later_instruments(doc_id, text)
    result = out
    final = []
    i = 0
    while i < len(result):
        c = result[i]
        i += 1
        if c["kind"] != "article":
            final.append(c)
            continue
        lines = c["text"].split("\n")
        boxes = mli_box_starts(lines)
        starts = [k for k, _ in boxes]
        if not starts:
            final.append(c)
            continue
        cid = c["cite_id"]
        while i < len(result) and result[i]["kind"] == "paragraph" and result[i]["parent"] == cid:
            i += 1                                        # the paragraphs were counted across the boxes: count again
        final.append(c)
        body = lines[:starts[0]]
        no = cid.split("#", 1)[1]
        for n, buf in split_paras(body[1:], RE_EN_PARA, int):
            final.append({"cite_id": "%s.%s" % (cid, n), "doc_id": doc_id, "kind": "paragraph",
                          "label": "Article %s(%s)" % (no, n), "parent": cid, "text": "\n".join(buf)})
        seen = {}
        for k, a in enumerate(starts):
            b = starts[k + 1] if k + 1 < len(starts) else len(lines)
            mli = boxes[k][1]
            seen[mli] = seen.get(mli, 0) + 1
            key = "mli%s" % mli + ("" if seen[mli] == 1 else "-%d" % seen[mli])
            final.append({"cite_id": "%s.%s" % (cid, key), "doc_id": doc_id, "kind": "mli_box",
                          "label": "Article %s, box: MLI Article %s" % (no, mli), "parent": cid, "text": "\n".join(lines[a:b])})
    return final, mode


RE_HK_SEC = re.compile(r"^(\d+)([A-Z]{0,6})\.\t(\S.*)$")
RE_HK_SCH = re.compile(r"^(?:(Schedule|附表)\s*(\d+[A-Z]*)|(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth) Schedule)$")
ORDINAL = {"First": "1", "Second": "2", "Third": "3", "Fourth": "4", "Fifth": "5", "Sixth": "6", "Seventh": "7", "Eighth": "8", "Ninth": "9", "Tenth": "10"}


def hk_sch_no(line):
    m = RE_HK_SCH.match(line.strip())
    return (m.group(2) or ORDINAL[m.group(3)]) if m else None


def slice_hk_ordinance(doc_id, text):
    """e-Legislation RTF text: '14.<TAB>Charge of profits tax'. Section numbers never decrease in the body;
    numbered lines inside Schedules are not sections, so the body ends at the first Schedule heading."""
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    sch = [i for i, ln in enumerate(lines) if RE_HK_SCH.match(ln.strip())]
    body_end = sch[0] if sch else len(lines)
    heads, last = [], 0
    for i, ln in enumerate(lines[:body_end]):
        m = RE_HK_SEC.match(ln)
        if not m:
            continue
        n, title = int(m.group(1)), m.group(3).rstrip()
        if last <= n <= last + 3 and (title.endswith("etc.") or not title.endswith((".", ";", "—", ":", "。", "；"))):
            heads.append((i, m.group(1) + m.group(2)))
            last = n
    out, seen = [], set()
    for k, (i, no) in enumerate(heads):
        if no in seen:
            continue
        seen.add(no)
        stop = heads[k + 1][0] if k + 1 < len(heads) else body_end
        out.append({"cite_id": "%s#s%s" % (doc_id, no), "doc_id": doc_id, "kind": "section", "label": "s %s" % no,
                    "parent": "", "text": "\n".join(x.strip() for x in lines[i:stop])})
    seen_sch = set()
    for k, i in enumerate(sch):
        no = hk_sch_no(lines[i])
        if no in seen_sch:
            continue
        seen_sch.add(no)
        stop = sch[k + 1] if k + 1 < len(sch) else len(lines)
        out.append({"cite_id": "%s#sch%s" % (doc_id, no), "doc_id": doc_id, "kind": "schedule",
                    "label": "Schedule %s" % no, "parent": "", "text": "\n".join(x.strip() for x in lines[i:stop])})
    return out, "hk_section" if len(out) >= 20 else "none"


RE_NUM_PARA = re.compile(r"^(\d{1,3})\.(?:\s+\S.*)?$")
RE_DOT_PARA = re.compile(r"^(\d{1,2})\.(\d{1,3})(?:\s+\S.*)?$")        # 5.100 and on (IRAS TP Guidelines)
H_MARK = "@@H@@"


def best_run(lines, hits):
    """hits: [(line_index, key, restart)]. Split into runs at restarts; return the run with the most text."""
    runs, cur = [], []
    for h in hits:
        if h[2] and cur:
            runs.append(cur)
            cur = []
        cur.append(h)
    if cur:
        runs.append(cur)
    if not runs:
        return []

    def size(r):
        k = runs.index(r)
        end = runs[k + 1][0][0] if k + 1 < len(runs) else len(lines)
        return sum(len(x) for x in lines[r[0][0]:end])
    return max(runs, key=size)


def dotted_run(lines):
    """'5.3 text' paragraphs (e-Tax guide style, and judgments numbered by section): the run with the most text."""
    hits, last = [], (0, 0)
    for i, ln in enumerate(lines):
        m = RE_DOT_PARA.match(ln)
        if not m:
            continue
        key = (int(m.group(1)), int(m.group(2)))
        if key == (1, 1) and last > (1, 1):
            hits.append((i, "1.1", True))
            last = key
        elif (key[0] == last[0] and key[1] == last[1] + 1) or (key[0] > last[0] and key[0] <= last[0] + 2 and key[1] == 1):
            hits.append((i, "%d.%d" % key, last == (0, 0)))
            last = key
    return best_run(lines, hits)


def slice_numbered_paras(doc_id, text):
    """Guidance PDFs. Either '12. text' numbered consecutively (DIPN style) or '5.3 text' (e-Tax guide style)."""
    lines = clean_lines(text)
    hits, last = [], 0
    for i, ln in enumerate(lines):
        m = RE_NUM_PARA.match(ln)
        if not m:
            continue
        n = int(m.group(1))
        if n == 1 and last >= 3:
            hits.append((i, "1", True))
            last = 1
        elif n == last + 1 or (last == 0 and n == 2):
            hits.append((i, str(n), last == 0))
            last = n
    plain = best_run(lines, hits)
    dotted = dotted_run(lines)
    run = dotted if len(dotted) >= max(8, len(plain) // 2) else plain
    if len(run) < 8:
        return [], "none"
    out = []
    if run[0][0] > 0:
        out.append({"cite_id": doc_id + "#front", "doc_id": doc_id, "kind": "front", "label": "front matter",
                    "parent": "", "text": "\n".join(lines[:run[0][0]])})
    for k, (i, key, _) in enumerate(run):
        stop = run[k + 1][0] if k + 1 < len(run) else len(lines)
        out.append({"cite_id": "%s#para%s" % (doc_id, key), "doc_id": doc_id, "kind": "paragraph",
                    "label": "para %s" % key, "parent": "", "text": "\n".join(lines[i:stop])})
    return out, "numbered_para"


def slice_html_sections(doc_id, raw):
    """Web pages: one clause per heading (h1-h4) inside the main container."""
    soup = BeautifulSoup(raw, "lxml")
    for t in soup(["script", "style", "noscript", "header", "footer", "nav", "form", "iframe"]):
        t.decompose()
    body = soup.body or soup

    def flat(node):
        return " ".join(node.get_text(" ").split())
    faq = body.find_all(class_=re.compile("question_container"))
    if len(faq) >= 3:
        out = []
        for n, q in enumerate(faq, 1):
            t = q.find(class_=re.compile("faq_title"))
            body_lines = [" ".join(x.split()) for x in q.get_text("\n").splitlines() if x.strip()]
            out.append({"cite_id": "%s#q%d" % (doc_id, n), "doc_id": doc_id, "kind": "qa",
                        "label": (flat(t) if t else "Q%d" % n)[:80], "parent": "", "text": "\n".join(body_lines)})
        return out, "html_faq"
    for h in body.find_all(["h1", "h2", "h3", "h4"]):
        h.insert_before("\n%s " % H_MARK)
    for para in body.find_all("p"):
        st = para.find("strong")
        if st and 3 < len(flat(para)) < 120 and flat(para) == flat(st):
            para.insert_before("\n%s " % H_MARK)
    lines = [re.sub(r"[ \t 　]+", " ", ln).strip() for ln in body.get_text("\n").splitlines()]
    lines = [ln for ln in lines if ln]
    sections, title, buf = [], None, []
    i = 0
    while i < len(lines):
        if lines[i].startswith(H_MARK):
            if title is not None and buf:
                sections.append((title, buf))
            rest = lines[i][len(H_MARK):].strip()
            if not rest and i + 1 < len(lines):
                i += 1
                rest = lines[i]
            title, buf = rest, [rest]
        elif title is not None:
            buf.append(lines[i])
        i += 1
    if title is not None and buf:
        sections.append((title, buf))
    sections = [(t, b) for t, b in sections if sum(len(x) for x in b) > len(t) + 40]   # drop empty menu headings
    if len(sections) < 3:
        return [], "none"
    out = []
    for n, (t, b) in enumerate(sections, 1):
        out.append({"cite_id": "%s#h%d" % (doc_id, n), "doc_id": doc_id, "kind": "section", "label": t[:80],
                    "parent": "", "text": "\n".join(b)})
    return out, "html_section"


SSO_ANCHOR = re.compile(r"^(pr[0-9]+[A-Z]*-|Sc[0-9]+[A-Z]*-)$")
SSO_REPEALED = re.compile(r"^\d+[A-Z]*\.\s*\[\s*Repealed by [^\]]*\]\s*$", re.S)
SSO_DROPPED = []                     # (cite_id, text): repealed-provision stubs left out of the clause layer (SSO, e-Legislation)
SSO_IMAGE = re.compile(r"/Image/([0-9a-f-]{36})\.gif")
FORMULAS = {}                        # image id -> transcribed formula; the library keeps no formula table, so it stays empty
UNTRANSCRIBED = []                   # (doc_id, image id): formula images marked in the text, listed in STATUS.md


def sso_formulas(doc_id, soup):
    """Each formula image becomes its reading, marked as such; an image nobody has read stays visible as a gap."""
    for img in soup.find_all("img", src=SSO_IMAGE):
        uid = SSO_IMAGE.search(img["src"]).group(1)
        if uid in FORMULAS:
            img.replace_with(" [formula: %s] " % FORMULAS[uid])
        else:
            UNTRANSCRIBED.append((doc_id, uid))
            img.replace_with(" [formula image %s: not transcribed] " % uid)


HK_REPEALED = re.compile(r"^(?:\d+[A-Z]*\.|Schedule \d+[A-Z]*)\s*\((?:Repealed|Omitted)[^)]*\)\s*$|"
                         r"^(?:\d+[A-Z]*\.|附表\d+[A-Z]*)\s*\(由[^)]*(?:廢除|刪除|删除)\)\s*$")


def sso_segments(soup):
    """Text from each SSO anchor to the next one, in document order: the fallback when a provision has no box of
    its own (the nearest enclosing div would otherwise be the whole Act)."""
    from bs4 import NavigableString, Tag
    seg, cur = {}, None
    for el in soup.descendants:
        if isinstance(el, Tag):
            if el.get("id") and SSO_ANCHOR.match(el["id"]):
                cur = el["id"]
                seg.setdefault(cur, [])
        elif isinstance(el, NavigableString) and cur and el.parent.name not in ("script", "style"):
            seg[cur].append(str(el))
    return {k: "\n".join(x.strip() for x in "\n".join(v).splitlines() if x.strip()) for k, v in seg.items()}


def slice_sso(doc_id, raw):
    """Singapore Statutes Online HTML: one clause per section, anchored by id='pr<no>-'. A provision's text is its
    own prov1 box when that box holds no other anchor, else the anchor-to-anchor segment. Repealed-section stubs
    ('18A. [Repealed by Act 21 of 2003]') are not current law and stay out of the clause layer."""
    soup = BeautifulSoup(raw, "lxml")
    sso_formulas(doc_id, soup)
    segments = None
    out, seen = [], set()
    for pattern, key, kind, label, box_class in ((r"^pr[0-9]+[A-Z]*-$", "s", "section", "s %s", "prov1"),
                                                 (r"^Sc[0-9]+[A-Z]*-$", "sch", "schedule", "Schedule %s", None)):
        for hdr in soup.find_all(id=re.compile(pattern)):
            no = hdr["id"][2:-1]
            if (key, no) in seen:
                continue
            seen.add((key, no))
            box = hdr.find_parent("div", class_=re.compile(box_class)) if box_class else hdr.find_parent("div")
            if box is None or len(box.find_all(id=SSO_ANCHOR)) > 1:
                if segments is None:
                    segments = sso_segments(soup)
                text = segments.get(hdr["id"], "")
            else:
                text = "\n".join(s.strip() for s in box.get_text("\n").splitlines() if s.strip())
            cite = "%s#%s%s" % (doc_id, key, no)
            if SSO_REPEALED.match(text.replace("\n", " ")):
                SSO_DROPPED.append((cite, text.replace("\n", " ")))
                continue
            out.append({"cite_id": cite, "doc_id": doc_id, "kind": kind, "label": label % no, "parent": "", "text": text})
    return out, "sso_section" if out else "none"


def slice_xfa(doc_id, text):
    """One clause per top-level subform of a dynamic form, e.g. #Page1_E; header, footer and buttons are skipped."""
    groups, order = {}, []
    for ln in text.splitlines():
        path = ln.split(" | ", 1)[0]
        parts = path.split("/")
        key = parts[1] if len(parts) > 1 else "root"
        if key.lower().startswith(("subform_header", "subform_footer", "landingpage")) or key == "root":
            continue
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(ln)
    out = [{"cite_id": "%s#%s" % (doc_id, k), "doc_id": doc_id, "kind": "subform", "label": k, "parent": "",
            "text": "\n".join(groups[k])} for k in order]
    return out, "xfa_subform" if out else "none"


RE_SEC_EN = re.compile(r"^[*]?(?:Section\s+)?(\d{1,4})([A-Z]{0,3})\.\s*(\S.*)?$")           # Malaysian acts: "109. ..." / "109B. ..." / "*43. ..." (the reprint's note mark, "*" or the Symbol-font glyph U+F02A)
RE_SEC_TH = re.compile(r"^(?:Section|มาตรา)\s+([0-9๐-๙]{1,4})\s*(bis|ter|quater|quarter|quinquies|quinque|sexies|sex|septies|octies|nonies|decies|"
                       r"ทวิ|ตรี|จัตวา|เบญจ|ฉ|สัตต|อัฏฐ|นว|ทศ)?(?![\w๐-๙])\s*(.*)$", re.I)   # Thai Revenue Code: "Section 70 Bis", "Section 57 Quarter", "มาตรา ๗๐ ทวิ"
RE_ART_AE = re.compile(r"^Article\s*(?:\(\s*(\d{1,4})\s*\)|(\d{1,4})\s*[-–—:])\s*(\S.*)?$", re.I)   # UAE decree-laws: "Article (45) ..." / "Article 45 – Title"; "Article 47 of this Decree-Law" (a reference) is not a heading
RE_SUBSEC = re.compile(r"^\((\d{1,2}|[a-z])\)\s*(\S.*)?$")                                             # "(1) ..." inside a section
RE_SUBSEC_AE = re.compile(r"^(\d{1,2})\.\s+(\S.*)$")                                                     # "1. ..." inside a UAE article
TH_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "0123456789" * 3)    # Thai, Arabic-Indic and Persian digits
RE_ART_AR = re.compile(r"^المادة\s*\(\s*([0-9٠-٩۰-۹]{1,3})\s*\)()\s*(.*)$")              # UAE decree-laws in Arabic: "المادة (45) الضريبة المقتطعة من المنبع"
RE_AR_DROP = re.compile(r"^(الفصل\s|النصوص السابقة$)")                                     # chapter headings; the portal's "previous texts" link
RE_TH_KHO = re.compile(r"^ข้อ\s*([0-9๐-๙]{1,3})()\s*(.*)$")                                   # Thai ministerial regulations and notifications: "ข้อ 2"
RE_TH_SUFFIX_LINE = re.compile(r"^(bis|ter|quater|quarter|quinquies|quinque|sexies|sex|septies|octies|nonies|decies|"
                               r"ทวิ|ตรี|จัตวา|เบญจ|ฉ|สัตต|อัฏฐ|นว|ทศ)$", re.I)
TH_SUFFIX = {"ทวิ": "bis", "ตรี": "ter", "จัตวา": "quater", "เบญจ": "quinquies", "ฉ": "sexies", "สัตต": "septies", "อัฏฐ": "octies",
             "นว": "nonies", "ทศ": "decies"}
LATIN_SUFFIX = {"bis": 1, "ter": 2, "quater": 3, "quarter": 3, "quinquies": 4, "quinque": 4, "sexies": 5, "sex": 5, "septies": 6,
                "octies": 7, "nonies": 8, "decies": 9}                                              # 'quarter', 'quinque', 'sex': spellings of rd.go.th
LATIN_CANON = {1: "bis", 2: "ter", 3: "quater", 4: "quinquies", 5: "sexies", 6: "septies", 7: "octies", 8: "nonies", 9: "decies"}


def section_suffix(raw):
    """(display, order) of a section suffix: Latin ordinals canonical and ordered by rank (bis < ter < quater ...),
    letters upper case and ordered as written (A < AA < B)."""
    raw = TH_SUFFIX.get(raw, raw or "")
    n = LATIN_SUFFIX.get(raw.lower())
    if n:
        return LATIN_CANON[n], "%02d" % n
    return raw.upper(), raw.upper()


def slice_sections(doc_id, text, regex, prefix, label_fmt, mode, sub_regex=RE_SUBSEC, max_jump=None):
    """English or Thai acts numbered "109.", "109B.", "Section 70 bis", "Article (45)": headings at the start of a line,
    numbers non-decreasing (a letter or bis/ter suffix after the same number), a drop in the number opening a new run
    (a table of contents comes first). The first run of at least three headings whose blocks hold real text is taken.
    Sub-sections "(1)", "(2)" become paragraphs. Checked on real texts (2026-10-23): Revenue Code ch. 3 (rd.go.th),
    Federal Decree-Law 47/2022 (mof.gov.ae)."""
    lines = clean_lines(text)
    heads = []                                               # (line index, base number, suffix order, display number, rest)
    for i, ln in enumerate(lines):
        m = regex.match(ln)
        if not m:
            continue
        g = m.groups()                                       # (number, suffix, rest); UAE: (number in brackets, number, rest)
        base = int(next(x for x in g if x).translate(TH_DIGITS))
        suffix, order = section_suffix(g[1] if regex is not RE_ART_AE else "")
        rest = g[-1] or ""
        if regex is RE_SEC_EN and (not rest or rest[0].islower()):   # "3. the Act" inside a paragraph is a list item, not a section
            continue
        heads.append((i, base, order, "%d%s" % (base, suffix), rest))
    runs, cur, last, skipped = [], [], (0, ""), []
    for h in heads:
        key = (h[1], h[2])
        if key < last and h[1] < last[0]:
            if h[1] == 1 or len(cur) <= 2:                   # numbering starts again (the body after a table of contents), or
                runs.append(cur)                             # one or two stray headings came first (a number in a preamble)
                cur = []
            else:
                skipped.append((h[0], h[1]))                 # a stray low number inside the body (a table row)
                continue
        if cur and key <= last:
            continue
        if cur and max_jump and h[1] > last[0] + max_jump:
            continue                                         # a stray high number (a table row)
        cur.append(h)
        last = key
    runs.append(cur)
    runs = [r for r in runs if len(r) >= 3]
    if not runs:
        return [], "none"
    ends = [r[0][0] for r in runs[1:]] + [len(lines)]
    pick = None
    for k, r in enumerate(runs):
        if sum(len(x) for x in lines[r[0][0]:ends[k]]) >= 150 * len(r):
            pick = k
            break
    if pick is None:
        pick = max(range(len(runs)), key=lambda k: len(runs[k]))
    run, end = runs[pick], ends[pick]
    again = [i for i, base in skipped if i > run[-1][0] and base == run[0][1]]
    if again:                                                # the same numbering starts over (a page that prints the part twice)
        end = min(end, again[0])
    out = []
    for k, (i, base, suffix, no, rest) in enumerate(run):
        stop = run[k + 1][0] if k + 1 < len(run) else end
        block = lines[i:stop]
        if sub_regex.match(rest or ""):                        # "109. (1) Where ..." : the first sub-section sits on the heading line
            block = [block[0][:len(block[0]) - len(rest)].rstrip(), rest] + block[1:]
        cid = "%s#%s%s" % (doc_id, prefix, no)
        out.append({"cite_id": cid, "doc_id": doc_id, "kind": "section", "label": label_fmt % no, "parent": "", "text": "\n".join(block)})
        sub, buf, seen = None, [], set()
        for ln in block[1:]:
            m = sub_regex.match(ln)
            if m and re.fullmatch(r"\d{1,2}[A-Za-z]?", m.group(1)) and m.group(1) not in seen:
                if sub is not None:
                    out.append({"cite_id": "%s(%s)" % (cid, sub), "doc_id": doc_id, "kind": "paragraph", "label": "%s(%s)" % (label_fmt % no, sub), "parent": cid, "text": "\n".join(buf)})
                sub, buf = m.group(1), [ln]
                seen.add(sub)
            elif sub is not None:
                buf.append(ln)
        if sub is not None:
            out.append({"cite_id": "%s(%s)" % (cid, sub), "doc_id": doc_id, "kind": "paragraph", "label": "%s(%s)" % (label_fmt % no, sub), "parent": cid, "text": "\n".join(buf)})
    return out, mode


def arabic_garbled(text):
    """True when an Arabic text layer has the ligatures reversed ('املادة' for 'المادة'); such PDFs also lose letters,
    so no quote copied by a reader can match them."""
    return text.count("امل") > 20 and text.count("الم") < text.count("امل") // 10


def slice_act(doc_id, text, jur):
    """Malaysian, Thai and UAE acts, each by its own heading style only: trying every style on every act lets a line
    such as 'section 154 ...' in a Malaysian act pass for a Thai heading. UAE acts in Arabic use the Arabic heading
    'المادة (45)', in English 'Article 45 – Title'; both give <doc>#a45. A Thai suffix on the line after 'มาตรา 49' is
    joined to it. Checked on real texts (2026-10-23): Income Tax Act 1967 (LOM reprint as at 1 January 2019, 249
    sections 1-156), Revenue Code ch. 3 (rd.go.th, Thai 42 + 30 sections, English 44 + 24), Federal Decree-Law 47/2022
    (uaelegislation.gov.ae Arabic HTML and mof.gov.ae English PDF, 70 articles each)."""
    if jur == "th":
        lines, out = text.splitlines(), []
        for ln in lines:
            if out and RE_TH_SUFFIX_LINE.match(ln.strip()) and RE_SEC_TH.match(out[-1].strip()) \
                    and re.fullmatch(r"(?:Section|มาตรา)\s+[0-9๐-๙]{1,4}", out[-1].strip(), re.I):
                out[-1] = out[-1].rstrip() + " " + ln.strip()
            else:
                out.append(ln)
        text = "\n".join(out)
    if jur == "ae" and "المادة" in text:
        text = "\n".join(ln for ln in text.splitlines() if not RE_AR_DROP.match(ln.strip()))
        return slice_sections(doc_id, text, RE_ART_AR, "a", "Article %s", "ae_article_ar", RE_SUBSEC_AE)
    if jur == "th":
        out, mode = slice_sections(doc_id, text, RE_SEC_TH, "s", "Section %s", "th_section", RE_SUBSEC)
        if out:
            return out, mode
        return slice_sections(doc_id, text, RE_TH_KHO, "c", "ข้อ %s", "th_clause", RE_SUBSEC)   # regulations without มาตรา
    regex, prefix, fmt, mode, sub = {"my": (RE_SEC_EN, "s", "Section %s", "my_section", RE_SUBSEC),
                                     "th": (RE_SEC_TH, "s", "Section %s", "th_section", RE_SUBSEC),
                                     "ae": (RE_ART_AE, "a", "Article %s", "ae_article", RE_SUBSEC_AE)}[jur]
    return slice_sections(doc_id, text, regex, prefix, fmt, mode, sub)


RE_SEC_ID = re.compile(r"^Pasal\s+(\d{1,3})([A-Z]{0,2})()$")       # Indonesian acts: "Pasal 26" alone on a line; "Pasal 26 ayat (1)" inside a sentence is a reference
RE_SUBSEC_ID = re.compile(r"^\((\d{1,2}[a-z]?)\)\s*(\S.*)?$")        # ayat "(1)", "(1a)"
RE_SEC_IN = re.compile(r"^(?:\d{1,2}\[)?(\d{1,3})([A-Z]{0,3})\.\s+([A-Z\u201c].*)$")            # 1961 Act (India Code): "195. Other sums.—(1) ...", "3[80RR. Deduction ..." (footnote marker + bracket before an inserted section)
RE_SEC_IN_TAB = re.compile(r"^(?:\d{1,2}\[)?(\d{1,3})([A-Z]{0,3})\.(?:[ ]*\t[\t ]*|\s+(?=\(\d))(.*)$")   # 2025 Act: "393.<TAB>(1) Where ...", "137. <TAB>An assessee", "45. (1)(a) A deduction ..."; table rows "1. Commission ..." do not match
RE_IN_TAB_STYLE = re.compile(r"^(?:\d{1,2}\[)?\d{1,3}[A-Z]{0,3}\.[ ]*\t")
RE_IN_WEAK = re.compile(r"^(?:\d{1,2}(?=\d{3}[A-Z]{0,3}\.))?(\d{1,3})([A-Z]{0,3})\.\s*(\S.*)$")   # "184. For the purposes ...", "5207.<TAB>(1) ..." (a footnote mark glued before the number)
RE_SUBSEC_IN = re.compile(r"^(?:\d{1,2}\[)?\((\d{1,2}[A-Za-z]?)\)\s*(\S.*)?$")                          # "(1)", "1[(1A)"
RE_IN_FOOTNOTE = re.compile(r"w\.e\.f\.|\bby Act\b|\bby s\.|\bibid\b|^\d{1,2}\.\s+(Subs|Ins|Omitted|Inserted|Substituted|Renumbered|Added|"
                            r"The (words|brackets|figures|letters|proviso|Explanation|expression|portion)|Certain words|Words|Earlier|Prior|Original|"
                            r"Explanation|Proviso|Second proviso|Sub-section|Sub-clause|Clause|Section|Item|Paragraph|Figures|Brackets|Letters|Marginal)\b")   # page-foot amendment notes


def slice_id(doc_id, text):
    """Indonesian acts: 'Pasal 26' alone on a line opens an article, '(1)' / '(1a)' alone on a line opens an ayat.
    An amending act (UU 36/2008) quotes each replaced article in full under 'Pasal I', so the same slicer yields the
    new wording; 'Pasal I' / 'Pasal II' (the amending frame, roman) and in-sentence references do not match.
    Written on UU 36/2008 (jdih.kemenkeu.go.id HTML, 2026-10-23): 25 articles, Pasal 2 to Pasal 35, 122 ayat."""
    return slice_sections(doc_id, text, RE_SEC_ID, "", "Pasal %s", "id_pasal", RE_SUBSEC_ID)


RE_VN_ART = re.compile(r"^Điều\s+(\d{1,3})\s*\.\s*(.*)$")                                # Vietnamese laws and decrees: "Điều 4. Thu nhập được miễn thuế"
RE_VN_HEAD = re.compile(r"^(Chương|Mục)\s+([IVXLC]+|\d+)\s*$")                                  # chapter / section headings between articles
RE_VN_END = re.compile(r"^(Luật này được Quốc hội|Nơi nhận\s*:)")                                # the closing formula: signatures follow


def slice_vn(doc_id, text):
    """Vietnamese laws and decrees: 'Điều 4. Title' opens an article, '1.' a clause (khoản), cite_id <doc>#4.1. Chapter
    headings ('Chương II' and the upper-case title on the next line) and everything from the closing formula on are
    dropped; a table of contents before the body restarts the numbering and is passed over. A reference such as
    'Điều 3 của Luật này' alone on a line has no dot after the number and is not a heading.
    Written on Luật Thuế thu nhập doanh nghiệp 67/2025/QH15 (2026-10-23): 20 articles."""
    kept, title_next = [], False
    for ln in text.splitlines():
        s = ln.strip()
        if RE_VN_END.match(s):
            break
        if RE_VN_HEAD.match(s):
            title_next = True
            continue
        if title_next and s and s == s.upper() and not RE_VN_ART.match(s):
            title_next = False
            continue
        title_next = False
        kept.append(ln)
    return slice_articles(doc_id, "\n".join(kept), RE_VN_ART, int, RE_EN_PARA, int, "Điều %s", "Điều %s khoản %s", "vn_article")


def promote_in_headings(lines):
    """2025 typesetting: a line written '184. For the purposes ...' (space, no tab) or '5207.<TAB>...' (a footnote mark
    glued before the number) is a heading only when its number is the one expected next (the last heading + 1) and lower
    than the next certain heading; table rows such as '1. Commission or brokerage' never are. Such lines are rewritten
    to the tab form."""
    strong = [None] * len(lines)
    for i, ln in enumerate(lines):
        m = RE_SEC_IN_TAB.match(ln)
        strong[i] = int(m.group(1)) if m else None
    nxt, after = [10 ** 6] * len(lines), 10 ** 6
    for i in range(len(lines) - 1, -1, -1):
        nxt[i] = after
        if strong[i] is not None:
            after = strong[i]
    out, last = [], 0
    for i, ln in enumerate(lines):
        if strong[i] is not None:
            if last < strong[i] <= last + 30:
                last = strong[i]
            out.append(ln)
            continue
        m = RE_IN_WEAK.match(ln)
        if m and int(m.group(1)) == last + 1 and int(m.group(1)) < nxt[i]:
            last = int(m.group(1))
            out.append("%s%s.\t%s" % (m.group(1), m.group(2), m.group(3)))
            continue
        out.append(ln)
    return out


def slice_in(doc_id, text):
    """Indian acts (India Code / Gazette typesetting): '195. Other sums.—(1) Any person ...', '115A. ...', inserted sections
    '3[80RR. ...'. The page-foot amendment notes ('1. Subs. by Act 4 of 1988, s. 3 (w.e.f. 1-4-1989)') look like sections
    1, 2, 3 and would split the run, so every numbered line that reads like one is dropped first; the first sub-section,
    which sits on the heading line after the title ('.—(1)'), is moved to its own line so that it is sliced like the others.
    The arrangement of sections (a table of contents) and the Schedules restart the numbering and fall into other runs.
    Checked (2026-10-23) on the Income-tax Act 1961 (India Code PDF, 880 pages): 688 sections, 1 to 298, and on the
    Income-tax Act 2025 as amended by the Finance Act 2026 (incometaxindia.gov.in PDF, 686 pages), where the section
    number is followed by a tab and the title stands on the line before."""
    lines = [ln.replace("\xad", "") for ln in text.splitlines() if not RE_IN_FOOTNOTE.search(ln.strip())]   # soft hyphens out
    lines = [re.sub(r"(\.\s*[\u2013\u2014])\s*((?:\d{1,2}\[)?\(\d{1,2}[A-Za-z]?\))", r"\1\n\2", ln, count=1) for ln in lines]
    regex = RE_SEC_IN_TAB if sum(1 for ln in lines if RE_IN_TAB_STYLE.match(ln)) > 50 else RE_SEC_IN   # the 2025 typesetting
    if regex is RE_SEC_IN_TAB:
        lines = promote_in_headings(lines)
    return slice_sections(doc_id, "\n".join(lines), regex, "s", "Section %s", "in_section", RE_SUBSEC_IN, max_jump=30)


JP_BLOCKS = {"Paragraph", "Item", "Subitem1", "Subitem2", "Subitem3", "TableRow", "ListSentence", "Sublist1Sentence", "Sublist2Sentence"}
JP_LABELS = {"ParagraphNum", "ItemTitle", "Subitem1Title", "Subitem2Title", "Subitem3Title"}


def jp_lines(e, depth=0, lines=None):
    """Text lines of an e-Gov XML element in document order: one line per paragraph, item, sub-item, list and table row;
    the number label first, columns joined by an ideographic space, table cells by a tab."""
    if lines is None:
        lines = []
    if e.tag in JP_BLOCKS:
        lines.append("　" * depth)
        depth += 1
    if e.tag == "Sentence":
        t = "".join(e.itertext()).strip()
        if lines:
            lines[-1] += t
        else:
            lines.append(t)
        return lines
    if e.tag in JP_LABELS:
        t = (e.text or "").strip()
        if t:
            lines[-1] += t + "　"
        return lines
    if e.tag in ("Column", "TableColumn") and lines and lines[-1].strip():
        lines[-1] += "\t" if e.tag == "TableColumn" else "　"
    for ch in e:
        jp_lines(ch, depth, lines)
    return lines


def jp_articles(raw):
    """[(num, title, caption, [(para_num, lines)])] for the main provisions of an e-Gov law XML (API v1 or v2)."""
    root = ET.fromstring(raw)
    main = next(iter(root.iter("MainProvision")), None)
    if main is None:
        return []
    out = []
    for art in main.iter("Article"):
        num = (art.get("Num") or "").replace("_", "-")
        title = (art.findtext("ArticleTitle") or "").strip()
        caption = (art.findtext("ArticleCaption") or "").strip()
        paras = []
        for p in art.findall("Paragraph"):
            paras.append(((p.get("Num") or "").strip(), [ln for ln in jp_lines(p) if ln.strip()]))
        out.append((num, title, caption, paras))
    return out


def jp_text(raw):
    blocks = []
    for num, title, caption, paras in jp_articles(raw):
        lines = ([caption] if caption else [])
        for k, (pn, pl) in enumerate(paras):
            if k == 0 and pl:
                pl = [title + "　" + pl[0].lstrip("　")] + pl[1:]
            lines += pl
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def slice_jp(doc_id, raw):
    """Japanese acts from e-Gov (XML): one clause per Article of the main provisions (第四条の二 → #4-2), one paragraph
    per 項 when the article has more than one (#4-2.2). Supplementary provisions (附則) are not sliced; '削除' stubs are dropped.
    Written on 法人税法 (340AC0000000034, API v1, 2026-10-23)."""
    out = []
    try:
        arts = jp_articles(raw)
    except ET.ParseError:
        return [], "xml_error"
    for num, title, caption, paras in arts:
        if not paras or (len(paras) == 1 and "".join(paras[0][1]).strip() in ("削除", "")):
            continue
        cid = "%s#%s" % (doc_id, num)
        lines = ([caption] if caption else [])
        for k, (pn, pl) in enumerate(paras):
            if k == 0 and pl:
                pl = [title + "　" + pl[0].lstrip("　")] + pl[1:]
            lines += pl
        out.append({"cite_id": cid, "doc_id": doc_id, "kind": "article", "label": title, "parent": "", "text": "\n".join(lines)})
        if len(paras) > 1:
            for k, (pn, pl) in enumerate(paras):
                if not pn:
                    continue
                out.append({"cite_id": "%s.%s" % (cid, pn), "doc_id": doc_id, "kind": "paragraph", "label": "%s第%s項" % (title, pn),
                            "parent": cid, "text": "\n".join(pl)})
    return out, "jp_article" if out else "none"


RE_JP_ITEM = re.compile(r"^(\d{1,2}(?:の\d+)?(?:[\u2212\uff0d\u2010-]\d{1,3}(?:の\d+)?){1,3})\s*$")   # NTA circulars: "3−3−1", "2−1−1の8" alone on a line


def slice_jp_tsutatsu(doc_id, text):
    """Japanese NTA circulars (法令解釈通達, HTML): an item number such as '3−3−1' alone on a line opens an item; the
    caption in brackets on the line before belongs to it. cite_id <doc>#3-3-1 ('の' becomes '_': 2-1-1_8).
    Checked on 法人税基本通達 第2章第1節第6款 and 第3章第3節 (nta.go.jp, 2026-10-23)."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    heads = [i for i, ln in enumerate(lines) if RE_JP_ITEM.match(ln)]
    if len(heads) < 2:
        return [], "none"
    out = []
    for k, i in enumerate(heads):
        start = i - 1 if i > 0 and lines[i - 1].startswith("（") and lines[i - 1].endswith("）") else i
        stop = heads[k + 1] if k + 1 < len(heads) else len(lines)
        if k + 1 < len(heads) and lines[stop - 1].startswith("（") and lines[stop - 1].endswith("）"):
            stop -= 1                                            # the next item's caption
        no = re.sub(r"[\u2212\uff0d\u2010]", "-", lines[i]).replace("の", "_")
        out.append({"cite_id": "%s#%s" % (doc_id, no), "doc_id": doc_id, "kind": "item", "label": lines[i], "parent": "",
                    "text": "\n".join(lines[start:stop])})
    return out, "jp_tsutatsu"


def kr_admrul_articles(raw):
    """[(key, label, lines)] of a law.go.kr administrative rule (AdmRulService XML): each 조문내용 block that starts with
    '제N조' (or '제N조의M'); chapter and section headings are skipped."""
    root = ET.fromstring(raw)
    out = []
    for e in root.iter("조문내용"):
        t = (e.text or "").strip()
        m = re.match(r"^제(\d+)조(?:의(\d+))?\s*\(", t)
        if not m:
            continue
        key = m.group(1) + ("-" + m.group(2) if m.group(2) else "")
        label = "제%s조" % m.group(1) + ("의%s" % m.group(2) if m.group(2) else "")
        out.append((key, label, [ln.rstrip() for ln in t.splitlines() if ln.strip()]))
    return out


def slice_kr_admrul(doc_id, raw):
    """Korean administrative rules from law.go.kr (훈령, 예규, 고시: AdmRulService XML): one clause per 조, one paragraph
    per circled number (① -> .1) when there are several. Checked on 국제조세사무처리규정 (2026-10-23)."""
    out = []
    for key, label, lines in kr_admrul_articles(raw):
        if re.match(r"^제\d+조(의\d+)?\s*삭제", lines[0]):
            continue
        cid = "%s#%s" % (doc_id, key)
        out.append({"cite_id": cid, "doc_id": doc_id, "kind": "article", "label": label, "parent": "", "text": "\n".join(lines)})
        paras, cur = [], None
        for ln in lines:
            m = re.match(r"^\s*([%s])" % KR_CIRCLED, ln)
            if m:
                cur = [KR_CIRCLED.index(m.group(1)) + 1, [ln.strip()]]
                paras.append(cur)
            elif cur:
                cur[1].append(ln.strip())
        if len(paras) > 1:
            for n, pl in paras:
                out.append({"cite_id": "%s.%d" % (cid, n), "doc_id": doc_id, "kind": "paragraph", "label": "%s제%d항" % (label, n),
                            "parent": cid, "text": "\n".join(pl)})
    return out, "kr_admrul" if out else "none"


KR_CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚"


def kr_articles(raw):
    """[(key, label, [lines], [(para_no, lines)])] for the 조문 units of a law.go.kr XML (DRF lawService, type=XML)."""
    root = ET.fromstring(raw)
    out = []
    for u in root.iter("조문단위"):
        if (u.findtext("조문여부") or "").strip() != "조문":
            continue                                          # 전문 rows are chapter headings
        no = (u.findtext("조문번호") or "").strip()
        branch = (u.findtext("조문가지번호") or "").strip()
        key = no + ("-" + branch if branch else "")
        label = "제%s조" % no + ("의%s" % branch if branch else "")
        lines = [(u.findtext("조문내용") or "").strip()]
        paras = []
        for h in u.findall("항"):
            hn = (h.findtext("항번호") or "").strip()
            pl = [(h.findtext("항내용") or "").strip()]
            for ho in h.findall("호"):
                pl.append("　" + (ho.findtext("호내용") or "").strip())
                for mok in ho.findall("목"):
                    pl.append("　　" + (mok.findtext("목내용") or "").strip())
            pl = [x for x in pl if x.strip()]
            lines += pl
            if hn and hn[0] in KR_CIRCLED:
                paras.append((KR_CIRCLED.index(hn[0]) + 1, pl))
        out.append((key, label, [x for x in lines if x.strip()], paras))
    return out


def kr_text(raw):
    if b"<AdmRulService" in raw[:2000]:
        return "\n\n".join("\n".join(lines) for _, _, lines in kr_admrul_articles(raw))
    return "\n\n".join("\n".join(lines) for _, _, lines, _ in kr_articles(raw))


def slice_kr(doc_id, raw):
    if b"<AdmRulService" in raw[:2000]:
        return slice_kr_admrul(doc_id, raw)
    """Korean acts from law.go.kr (XML): one clause per 조문 (제98조의2 → #98-2), one paragraph per numbered 항 (①
    → #98-2.1) when the article has more than one. Addenda (부칙) are not sliced; '삭제' stubs are dropped.
    Written on 법인세법 (법령ID 001563, 2026-10-23)."""
    try:
        arts = kr_articles(raw)
    except ET.ParseError:
        return [], "xml_error"
    out = []
    for key, label, lines, paras in arts:
        if not lines or re.match(r"^제\d+조(의\d+)?\s*삭제", lines[0]):
            continue
        cid = "%s#%s" % (doc_id, key)
        out.append({"cite_id": cid, "doc_id": doc_id, "kind": "article", "label": label, "parent": "", "text": "\n".join(lines)})
        if len(paras) > 1:
            for n, pl in paras:
                out.append({"cite_id": "%s.%d" % (cid, n), "doc_id": doc_id, "kind": "paragraph", "label": "%s제%d항" % (label, n),
                            "parent": cid, "text": "\n".join(pl)})
    return out, "kr_article" if out else "none"


def xml_text(row):
    """Text layer of an XML document: the sliced article text for e-Gov (jp.) and law.go.kr (kr.) files, all text otherwise."""
    raw = (ROOT / row["file"]).read_bytes()
    if row["id"].startswith("jp."):
        return jp_text(raw)
    if row["id"].startswith("kr."):
        return kr_text(raw)
    return "\n".join(t.strip() for t in ET.fromstring(raw).itertext() if t.strip())


def slice_pages(doc_id, pages):
    return [{"cite_id": "%s#p%d" % (doc_id, i + 1), "doc_id": doc_id, "kind": "page", "label": "p.%d" % (i + 1),
             "parent": "", "text": t.strip()} for i, t in enumerate(pages) if t.strip()], "page"

# ---------------------------------------------------------------- superseded clauses and quotes
def norm(s):
    return re.sub(r"[\s\xad]+", "", s or "")


def drop_superseded(clauses, only=None):
    """superseded.csv: doc_id, clause ('13.4'; '24*' for an article with its paragraphs, i.e. '24' and '24.<n>'; '*' for all;
    '13.5@4-' / '13.5@4-6' / '13.5@2' for lines of a clause; or a clause plus an exact phrase), by, since.
    Those clauses, lines or phrases are not kept. What leaves a paragraph also leaves the article (its parent),
    so the replaced wording cannot be cited through the article either.
    only: the documents of this run (--jur); rows of other documents are skipped."""
    rules = [r for r in read_csv(ROOT / "superseded.csv") if only is None or r["doc_id"] in only]
    if not rules:
        return clauses, 0
    cut = {}                                           # "i8@2" or "13.5@4-": remove those lines of the clause
    for r in rules:
        if "@" in r["clause"]:
            name, span = r["clause"].split("@")
            a, _, b = span.partition("-")
            cut.setdefault(r["doc_id"] + "#" + name, []).append((int(a), int(b) if b else (10 ** 6 if "-" in span else int(a))))
    phrases = [r for r in rules if r.get("phrase")]     # remove an exact phrase from one clause
    rules = [r for r in rules if "@" not in r["clause"] and not r.get("phrase")]
    exact = {r["doc_id"] + "#" + r["clause"] for r in rules if not r["clause"].endswith("*")}
    prefix = [r["doc_id"] + "#" + r["clause"][:-1] for r in rules if r["clause"].endswith("*")]

    def gone(cid):                                    # '24*' = 24 and 24.<n>; '*' alone = the whole document
        return cid in exact or any(cid.startswith(x) if x.endswith("#") else (cid == x or cid.startswith(x + "."))
                                   for x in prefix)

    kept = [c for c in clauses if not gone(c["cite_id"])]
    by_id = {c["cite_id"]: c for c in kept}

    def strip(c, piece):
        """Remove a piece of text (lines of a child, or a phrase) from a clause; blank lines left behind are dropped."""
        if c is not None and piece and piece in c["text"]:
            c["text"] = "\n".join(ln for ln in c["text"].replace(piece, "", 1).splitlines() if ln.strip())
            c["chars"] = len(c["text"])

    for c in clauses:                                  # a removed paragraph also leaves its article
        if gone(c["cite_id"]) and c.get("parent") and not gone(c["parent"]):
            strip(by_id.get(c["parent"]), c["text"])
    n_cut = 0
    for c in kept:
        if c["cite_id"] in cut:
            spans = cut[c["cite_id"]]
            lines = c["text"].splitlines()
            drop = [i for i in range(1, len(lines) + 1) if any(a <= i <= b for a, b in spans)]
            blocks, cur = [], []                       # consecutive removed lines, removed from the parent as one block
            for i in drop:
                if cur and i != cur[-1] + 1:
                    blocks.append(cur)
                    cur = []
                cur.append(i)
            if cur:
                blocks.append(cur)
            for blk in blocks:
                strip(by_id.get(c.get("parent") or ""), "\n".join(lines[i - 1] for i in blk))
            c["text"] = "\n".join(ln for i, ln in enumerate(lines, 1) if i not in drop)
            c["chars"] = len(c["text"])
            n_cut += 1
    for r in phrases:
        c = by_id.get(r["doc_id"] + "#" + r["clause"])
        targets = [c] if c is not None else []
        if c is None and r["clause"] == "all":            # the document is sliced now: cut the phrase where it sits
            targets = [x for x in kept if x["doc_id"] == r["doc_id"] and r["phrase"] in x["text"]]
        if not targets or any(r["phrase"] not in x["text"] for x in targets):
            raise SystemExit("superseded.csv: phrase not found in %s#%s: %s" % (r["doc_id"], r["clause"], r["phrase"][:30]))
        for x in targets:
            strip(by_id.get(x.get("parent") or ""), r["phrase"])
            x["text"] = "\n".join(ln for ln in x["text"].replace(r["phrase"], "").splitlines() if ln.strip())
            x["chars"] = len(x["text"])
            n_cut += 1
    return kept, len(clauses) - len(kept) + n_cut


# ---------------------------------------------------------------- which slicer
RE_SSO_PAGE = re.compile(rb'id="(?:pr|Sc)[0-9]+[A-Z]*-"')       # section or schedule anchors


def slice_doc(row, text, pages):
    """Pick the slicer by jurisdiction, type and format; the first one that cuts the text wins."""
    doc_id, typ, jur, kind = row["id"], row["type"], row["jur"], row["real_kind"]
    raw = (ROOT / row["file"]).read_bytes() if kind in ("html", "htm", "xml") else b""
    if row.get("text_status") == "xfa_template":
        return slice_xfa(doc_id, text)
    if kind in ("html", "htm") and RE_SSO_PAGE.search(raw):                           # Singapore Statutes Online
        out, mode = slice_sso(doc_id, raw)
        if out:
            return out, mode
    is_treaty = doc_id.startswith("treaty.") or (doc_id.startswith("intl.") and typ == "treaty")   # bilateral treaties by id (§4.2) and the MLI text; positions files fall back to pages
    statute = typ in ("law", "regulation") and not is_treaty
    if jur == "hk" and statute:                                                        # e-Legislation chapters
        out, mode = slice_hk_ordinance(doc_id, text)
        if out and mode != "none":
            return out, mode
    if jur in ("my", "th", "ae") and (statute or (jur == "th" and typ == "guidance")):   # Malaysian, Thai, UAE acts; Thai notifications
        out, mode = slice_act(doc_id, text, jur)
        if out:
            return out, mode
    if jur == "jp" and kind == "xml":                                                  # e-Gov law XML
        out, mode = slice_jp(doc_id, raw)
        if out:
            return out, mode
    if jur == "kr" and kind == "xml":                                                  # law.go.kr law XML
        out, mode = slice_kr(doc_id, raw)
        if out:
            return out, mode
    if jur == "jp" and kind in ("html", "htm"):                                        # NTA circulars
        out, mode = slice_jp_tsutatsu(doc_id, text)
        if out:
            return out, mode
    if jur == "id" and statute:                                                        # Indonesian acts by Pasal
        out, mode = slice_id(doc_id, text)
        if out:
            return out, mode
    if jur == "vn" and statute:                                                        # Vietnamese laws and decrees by Điều
        out, mode = slice_vn(doc_id, text)
        if out:
            return out, mode
    if jur == "in" and statute:                                                        # Indian acts by section
        out, mode = slice_in(doc_id, text)
        if out:
            return out, mode
    sample = text[:20000]
    cn = len(re.findall(r"[\u4e00-\u9fff]", sample)) > 0.2 * max(1, len(sample))
    attached_text = typ == "attachment" and re.search(r"办法|规定|指南|细则|条例|准则|公约|协定", row["title"] or "") and "表" not in (row["title"] or "")
    legal = typ in ("law", "regulation", "guidance") or is_treaty or bool(attached_text)   # an attached 办法 slices like its parent
    if cn and legal:
        out, mode = slice_cn(doc_id, text)
        if len(out) >= 3:
            return out, mode
    if not cn and is_treaty:
        out, mode = slice_en_treaty(doc_id, text)
        if len(out) >= 3:
            return out, mode
    if pages and typ in ("guidance", "page") and not cn:
        out, mode = slice_numbered_paras(doc_id, text)
        if out:
            return out, mode
    if pages:
        return slice_pages(doc_id, pages)
    if kind in ("html", "htm"):
        out, mode = slice_html_sections(doc_id, raw)
        if out:
            return out, mode
    return [{"cite_id": doc_id + "#all", "doc_id": doc_id, "kind": "whole", "label": "全文", "parent": "",
             "text": text}], "whole"


# ---------------------------------------------------------------- checks (数据库规范.md §5)
def split_list(s):
    return [x.strip() for x in re.split(r"[;,\s]+", s or "") if x.strip()]


def pairs_of(codes):
    codes = sorted(codes)
    return ["%s-%s" % (a, b) for k, a in enumerate(codes) for b in codes[k + 1:]]


def valid_pair(pair, codes):
    a, _, b = (pair or "").partition("-")
    return a in codes and b in codes and a != b


def bad_date(v):
    """True unless v is empty or a real date written YYYY-MM-DD."""
    v = (v or "").strip()
    if not v:
        return False
    try:
        return date.fromisoformat(v).isoformat() != v
    except ValueError:
        return True


def check_dates(kind, key, row, cols, errors):
    for c in cols:
        if bad_date(row.get(c)):
            errors.append("%s %s: %s %r must be a date written YYYY-MM-DD" % (kind, key, c, row.get(c)))


def id_prefix(jur, codes):
    """The prefix every id of this jurisdiction starts with, so that folders of several collectors merge without clashes."""
    if jur == "intl":
        return "intl."
    if valid_pair(jur, codes):
        return "treaty.%s." % jur
    return jur + "."


def check_docs(docs, codes, errors, warnings):
    seen, by_hash = set(), {}
    for r in docs:
        rid = r["id"]
        if rid in seen:
            errors.append("doc %s: duplicate id" % rid)
        seen.add(rid)
        if not re.fullmatch(r"[A-Za-z0-9._\-]+", rid):
            errors.append("doc %s: id may only hold ASCII letters, digits, . _ - (it becomes a file name and a storage key)" % rid)
        if r["jur"] not in codes and r["jur"] != "intl" and not valid_pair(r["jur"], codes):
            errors.append("doc %s: jur %r is not a jurisdiction code, a pair or intl" % (rid, r["jur"]))
        if r["type"] not in DOC_TYPES:
            warnings.append("doc %s: type %r is not one of %s" % (rid, r["type"], "/".join(DOC_TYPES)))
        if r["type"] == "treaty" and r["jur"] != "intl" and not valid_pair(r["jur"], codes):
            errors.append("doc %s: a treaty document's jur must be its pair (such as cn-hk) or intl" % rid)
        elif (r["jur"] in codes or r["jur"] == "intl" or valid_pair(r["jur"], codes)) and not rid.startswith(id_prefix(r["jur"], codes)):
            errors.append("doc %s: id must start with %s" % (rid, id_prefix(r["jur"], codes)))
        if not (r.get("url") or "").strip():
            errors.append("doc %s: url empty" % rid)
        elif not is_official(r["url"]):
            errors.append("doc %s: url %s is not on an official host (fetch.py OFFICIAL); register the official address "
                          "and say in note where the copy came from" % (rid, r["url"]))
        if not (r.get("lang") or "").strip():
            errors.append("doc %s: lang empty (the language code of the file, such as zh, en, th)" % rid)
        check_dates("doc", rid, r, ("effective_from", "effective_to"), errors)
        cats = split_list(r.get("category"))
        bad = [c for c in cats if c not in CATEGORIES]
        if bad:
            errors.append("doc %s: category %s not in %s" % (rid, ";".join(bad), "/".join(CATEGORIES)))
        if not cats and r["jur"] in codes and r["type"] != "treaty":
            errors.append("doc %s: category empty (one or more of %s, separated by ;)" % (rid, "/".join(CATEGORIES)))
        f = ROOT / (r["file"] or "-")
        if not r["file"] or not f.is_file():
            errors.append("doc %s: file missing: %s" % (rid, r["file"]))
            r["_missing"] = True
            continue
        sha = hashlib.sha256(f.read_bytes()).hexdigest()
        if r["sha256"] and r["sha256"] != sha:
            errors.append("doc %s: sha256 differs from the file (file changed after registration)" % rid)
        if not r["sha256"]:
            warnings.append("doc %s: sha256 empty (fetch.py fills it)" % rid)
            r["sha256"] = sha
        if sha in by_hash:
            warnings.append("doc %s: same bytes as %s; sliced once" % (rid, by_hash[sha]))
            r["_alias"] = by_hash[sha]
        else:
            by_hash[sha] = rid


def check_quotes(kind, rows, id_key, clause_text, errors):
    for p in rows:
        cid = p.get("cite_id", "")
        if cid not in clause_text:
            errors.append("%s %s: cite_id not found: %s" % (kind, p.get(id_key), cid))
        elif not (p.get("quote") or "").strip():
            errors.append("%s %s: quote empty" % (kind, p.get(id_key)))
        elif norm(p["quote"]) not in norm(clause_text[cid]):
            errors.append("%s %s: quote not found verbatim in %s" % (kind, p.get(id_key), cid))


def check_params(params, codes, currencies, clause_text, errors, docs=()):
    seen = set()
    interpretive = {r["id"] for r in docs if set(split_list(r.get("category"))) == {"11"}}
    ids = {p["param_id"] for p in params}
    for p in params:
        pid = p["param_id"]
        if pid in seen:
            errors.append("param %s: duplicate param_id" % pid)
        seen.add(pid)
        if (p.get("cite_id") or "").split("#")[0] in interpretive:
            errors.append("param %s: cite_id %s is in an interpretive source (category 11); parameters come from primary sources only" % (pid, p["cite_id"]))
        sup = (p.get("superseded_by") or "").strip()
        if sup and sup not in ids:
            errors.append("param %s: superseded_by %s is not a param_id" % (pid, sup))
        if p["scope"] not in codes and not valid_pair(p["scope"], codes):
            errors.append("param %s: scope %r is not a jurisdiction code or a pair a-b" % (pid, p["scope"]))
        if p["subject"] not in SUBJECTS:
            errors.append("param %s: subject %r not in %s" % (pid, p["subject"], "/".join(SUBJECTS)))
        if p["slot"] not in SLOTS:
            errors.append("param %s: slot %r not in %s" % (pid, p["slot"], "/".join(SLOTS)))
        name = p.get("name") or ""
        if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
            errors.append("param %s: name %r must be lowercase letters, digits and _" % (pid, name))
        stem = "%s.%s.%s" % (p["scope"], p["slot"], name)
        if pid != stem and not pid.startswith(stem + "."):
            errors.append("param %s: param_id must be %s, or %s.<suffix> when several rows share it" % (pid, stem, stem))
        check_dates("param", pid, p, ("effective_from", "effective_to", "changed_on"), errors)
        unit, value = p.get("unit") or "", (p.get("value") or "").strip()
        if unit not in UNITS and unit not in currencies:
            errors.append("param %s: unit %r not in %s or a currency of jurisdiction.csv" % (pid, unit, "/".join(UNITS)))
        elif unit in NUMERIC_UNITS or unit in currencies:
            if not re.fullmatch(r"\d+(\.\d+)?", value):
                errors.append("param %s: value %r must be a plain number for unit %s (5 for 5%%, not 0.05)" % (pid, value, unit))
        elif unit == "bool" and value not in ("yes", "no"):
            errors.append("param %s: value %r must be yes or no for unit bool" % (pid, value))
        elif unit == "text" and not value:
            errors.append("param %s: value empty" % pid)
    check_quotes("param", params, "param_id", clause_text, errors)


def check_treaties(treaties, codes, doc_ids, errors):
    seen = set()
    for t in treaties:
        pair = t["pair"]
        if not valid_pair(pair, codes):
            errors.append("treaty %s: not a pair of jurisdiction codes a-b" % pair)
        elif pair.split("-") != sorted(pair.split("-")):
            errors.append("treaty %s: write the pair in alphabetical order (%s)" % (pair, "-".join(sorted(pair.split("-")))))
        if pair in seen:
            errors.append("treaty %s: duplicate pair" % pair)
        check_dates("treaty", pair, t, ("in_force_from",), errors)
        seen.add(pair)
        for col in ("doc_id", "mli_doc_id"):
            if t[col] and t[col] not in doc_ids:
                errors.append("treaty %s: %s %s not in doc" % (pair, col, t[col]))


def check_decisions(decisions, codes, clause_text, errors):
    """Every decision row is an absence record of one cell: a category (that jurisdiction has no document of it) or a
    subject and slot (its law has no rule there). Categories 1-4 and 9 and every slot must cite the clause that sets the
    scope of the tax; for categories 5-8 and the pages the citation is optional (an authority not publishing something
    has no clause), and the statement says where it was searched."""
    cited, seen = [], set()
    for d in decisions:
        jur, cat = (d.get("jur") or "").strip(), (d.get("category") or "").strip()
        subj, slot = (d.get("subject") or "").strip(), (d.get("slot") or "").strip()
        if d["id"] in seen:
            errors.append("decision %s: duplicate id" % d["id"])
        seen.add(d["id"])
        if jur in codes and not d["id"].startswith(jur + "."):
            errors.append("decision %s: id must start with %s." % (d["id"], jur))
        if not jur or bool(cat) == bool(slot) or bool(slot) != bool(subj):
            errors.append("decision %s: an absence record needs jur and either category, or subject and slot" % d["id"])
            continue
        if jur not in codes:
            errors.append("decision %s: jur %r is not a jurisdiction code" % (d["id"], jur))
        if cat and cat not in CATEGORIES:
            errors.append("decision %s: category %r not in %s" % (d["id"], cat, "/".join(CATEGORIES)))
        if slot and slot not in SLOTS:
            errors.append("decision %s: slot %r not in %s" % (d["id"], slot, "/".join(SLOTS)))
        if subj and subj not in SUBJECTS:
            errors.append("decision %s: subject %r not in %s" % (d["id"], subj, "/".join(SUBJECTS)))
        if not (d.get("statement") or "").strip():
            errors.append("decision %s: statement empty (say what is absent and where it was searched)" % d["id"])
        legal = slot or cat in LEGAL_CATEGORIES
        if legal and not (d.get("cite_id") or "").strip():
            errors.append("decision %s: an absence record of %s must cite the clause that sets the scope of the tax"
                          % (d["id"], ("slot " + slot) if slot else ("category " + cat)))
        elif (d.get("cite_id") or "").strip():
            cited.append(d)
    check_quotes("decision", cited, "id", clause_text, errors)


def coverage_slots(params, decisions, juris):
    """Cells jurisdiction | subject | slot with neither a parameter of the jurisdiction's own law (scope = its code;
    subject all covers both) nor an absence record."""
    have = set()
    for p in params:
        for s in (("company", "individual") if p["subject"] == "all" else (p["subject"],)):
            have.add((p["scope"], s, p["slot"]))
    for d in decisions:
        subj = (d.get("subject") or "").strip()
        for s in (("company", "individual") if subj == "all" else (subj,)):
            have.add(((d.get("jur") or "").strip(), s, (d.get("slot") or "").strip()))
    gaps = []
    for j in juris:
        for s, col in (("company", "company_in_scope"), ("individual", "individual_in_scope")):
            if (j.get(col) or "yes").lower() not in ("yes", "y", "1", "true"):
                continue
            gaps += ["%s|%s|%s" % (j["code"], s, slot) for slot in SLOTS if (j["code"], s, slot) not in have]
    return gaps


def coverage_categories(docs, decisions, juris):
    """Cells jurisdiction | category with neither a document nor an absence record."""
    have = set()
    for r in docs:
        for c in split_list(r.get("category")):
            have.add((r["jur"], c))
    for d in decisions:
        if d.get("jur") and d.get("category"):
            have.add((d["jur"].strip(), d["category"].strip()))
    return ["%s|%s" % (j["code"], c) for j in juris for c in COVERED_CATEGORIES if (j["code"], c) not in have]


def missing_pairs_of(treaties, juris):
    """Pairs of jurisdictions without a treaty row (a row with empty doc_id records "no treaty")."""
    have = {t["pair"] for t in treaties}
    return [p for p in pairs_of([j["code"] for j in juris]) if p not in have]


# ---------------------------------------------------------------- one jurisdiction (§5)
def jurs_of(value, codes):
    """'cn' -> {'cn'}; 'cn-hk' -> {'cn', 'hk'}; anything else (intl, unknown) -> empty."""
    if value in codes:
        return {value}
    a, _, b = (value or "").partition("-")
    return {a, b} if a in codes and b in codes else set()


def subset(t, jur, codes):
    """The rows one jurisdiction answers for: its documents, those of its pairs (treaties) and the intl documents (the
    MLI text); parameters of it and of its pairs; its absence records; the treaty rows of its pairs."""
    def mine(v):
        return jur in jurs_of(v, codes)
    out = dict(t)
    out["jurisdiction"] = [j for j in t["jurisdiction"] if j["code"] == jur]
    out["doc"] = [r for r in t["doc"] if mine(r["jur"]) or r["jur"] == "intl"]
    out["param"] = [r for r in t["param"] if mine(r["scope"])]
    out["decision"] = [r for r in t["decision"] if (r.get("jur") or "").strip() == jur]
    out["treaty"] = [r for r in t["treaty"] if mine(r["pair"])]
    return out


def unresolved_blocked(doc_ids, jur, codes):
    """blocked.csv rows whose id never made it into doc.csv; with jur, only that jurisdiction's and its pairs'."""
    rows = [b for b in read_csv(ROOT / "blocked.csv") if b["id"] not in doc_ids]
    if jur:
        rows = [b for b in rows if jur in jurs_of(b["jur"], codes)]
    return ["%s (%s)" % (b["id"], b["reason"]) for b in rows]


def slice_all(docs, errors, warnings, write_text):
    """Text and clauses of the documents; with write_text the text/ folder is rewritten for exactly these documents."""
    text_dir = ROOT / "text"
    clauses, conv = [], Path(tempfile.mkdtemp(prefix="build_conv_"))
    if write_text:
        text_dir.mkdir(exist_ok=True)
    try:
        live = [r for r in docs if not r.get("_missing")]
        for r in live:
            r["real_kind"] = real_kind(ROOT / r["file"], Path(r["file"]).suffix.lstrip("."))
        soffice_convert([(ROOT / r["file"], r["real_kind"], r["sha256"][:16] or r["id"]) for r in live
                         if r["real_kind"] in ("doc", "rtf", "xls", "ppt", "pptx")], conv)
        for r in live:
            text, pages, status = to_text(r, r["real_kind"], conv)
            r["text_status"] = status
            if status not in ("ok", "xfa_template"):
                errors.append("doc %s: no text (%s)" % (r["id"], status))
            if text and arabic_garbled(text):
                errors.append("doc %s: Arabic text layer garbled (letters reversed or missing); register the page of "
                              "uaelegislation.gov.ae or another source whose text copies correctly" % r["id"])
            if text and write_text:
                (text_dir / (r["id"] + ".txt")).write_text(text, encoding="utf-8")
            if r.get("_alias"):
                r["slice_mode"], r["n_clauses"] = "alias of " + r["_alias"], 0
                continue
            cl, mode = slice_doc(r, text, pages) if text else ([], "none")
            r["slice_mode"], r["n_clauses"] = mode, len(cl)
            clauses.extend(cl)
    finally:
        shutil.rmtree(str(conv), ignore_errors=True)
    if write_text:
        with_text = {r["id"] for r in docs if (text_dir / (r["id"] + ".txt")).exists() and not r.get("_missing")}
        for f in text_dir.glob("*.txt"):               # text of a document no longer registered
            if f.stem not in with_text:
                f.unlink()

    kept = []
    for c in clauses:                                  # repealed-provision placeholders are not current law
        head = re.split(r"_{5,}", c["text"])[0].replace("\n", " ").replace("\t", " ").strip()
        if HK_REPEALED.match(head) and c["doc_id"].startswith("hk."):
            SSO_DROPPED.append((c["cite_id"], head))
        else:
            kept.append(c)
    seen, uniq = set(), []
    for c in kept:
        if c["cite_id"] in seen:
            warnings.append("clause %s: duplicate cite_id, later one dropped" % c["cite_id"])
            continue
        seen.add(c["cite_id"])
        uniq.append(c)
    try:
        return drop_superseded(uniq, None if write_text else {r["id"] for r in docs})
    except SystemExit as e:                            # a phrase of superseded.csv not found
        errors.append(str(e))
        return uniq, 0


# ---------------------------------------------------------------- main
def main():
    global ROOT
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="", help="library folder (default: database/)")
    ap.add_argument("--jur", default="", help="check one jurisdiction only (§5): PASSED on zero errors and zero gaps; writes nothing")
    args = ap.parse_args()
    if args.root:
        ROOT = Path(args.root).resolve()
    init_csvs()
    errors, warnings = [], []
    t = {name: read_csv(ROOT / (name + ".csv")) for name in FILLED}
    for name in FILLED:
        with (ROOT / (name + ".csv")).open(encoding=ENC, newline="") as f:
            header = next(csv.reader(f), [])
        missing = [c for c in TABLES[name] if c not in header]
        if missing:
            errors.append("%s.csv: columns missing: %s" % (name, ", ".join(missing)))
    all_juris = t["jurisdiction"]
    codes = {j["code"] for j in all_juris}
    all_doc_ids = {r["id"] for r in t["doc"]}
    if args.jur:
        if args.jur not in codes:
            print("! --jur %s: not a code of jurisdiction.csv" % args.jur)
            return 1
        t = subset(t, args.jur, codes)
    docs = t["doc"]
    check_docs(docs, codes, errors, warnings)
    clauses, n_superseded = slice_all(docs, errors, warnings, write_text=not args.jur)
    run_ids = {r["id"] for r in docs}
    for r in read_csv(ROOT / "superseded.csv"):
        if r["doc_id"] in run_ids:
            check_dates("superseded.csv", "%s#%s" % (r["doc_id"], r["clause"]), r, ("since",), errors)
    clause_text = {c["cite_id"]: c["text"] for c in clauses}
    check_params(t["param"], codes, {j["currency"] for j in all_juris if j.get("currency")}, clause_text, errors, t["doc"])
    check_decisions(t["decision"], codes, clause_text, errors)
    check_treaties(t["treaty"], codes, all_doc_ids, errors)
    cat_gaps = coverage_categories(docs, t["decision"], t["jurisdiction"])
    slot_gaps = coverage_slots(t["param"], t["decision"], t["jurisdiction"])
    missing_pairs = [p for p in missing_pairs_of(t["treaty"], all_juris)
                     if not args.jur or p.split("-")[0] == args.jur]   # a pair is registered by its alphabetically first side
    blocked = unresolved_blocked(all_doc_ids, args.jur, codes)

    if args.jur:
        gaps = (["category %s" % g for g in cat_gaps] + ["slot %s without a parameter" % g for g in slot_gaps]
                + ["pair %s without a treaty row" % p for p in missing_pairs]
                + ["download not resolved: %s" % b for b in blocked])
        print("acceptance %s: %s (errors=%d gaps=%d)" % (args.jur, "NOT PASSED" if errors or gaps else "PASSED",
                                                         len(errors), len(gaps)))
        for x in errors:
            print("  ! error: " + x)
        for x in gaps:
            print("  ! gap: " + x)
        return 1 if errors or gaps else 0

    write_csv(ROOT / "clause.csv", TABLES["clause"], clauses)
    files = []
    for folder in ("raw", "text"):
        for f in sorted((ROOT / folder).rglob("*")) if (ROOT / folder).exists() else []:
            if f.is_file():
                b = f.read_bytes()
                files.append({"path": f.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)})
    write_csv(ROOT / "files.csv", TABLES["files"], files)

    db = ROOT / "database.sqlite"
    if db.exists():
        db.unlink()
    con = sqlite3.connect(str(db))
    rows = dict(t, clause=clauses, files=files)
    for name, cols in TABLES.items():
        con.execute("CREATE TABLE %s (%s)" % (name, ", ".join('"%s" TEXT' % c for c in cols)))
        con.executemany("INSERT INTO %s VALUES (%s)" % (name, ",".join("?" * len(cols))),
                        [[str(r.get(c, "")) for c in cols] for r in rows.get(name, [])])
    for idx in ("clause(cite_id)", "clause(doc_id)", "param(param_id)", "doc(id)"):
        con.execute("CREATE INDEX ix_%s ON %s" % (re.sub(r"\W", "_", idx), idx))
    con.commit()
    con.close()

    write_status(docs, clauses, n_superseded, t, errors, warnings, missing_pairs, cat_gaps, blocked, slot_gaps)
    print("docs=%d clauses=%d params=%d absence_records=%d errors=%d warnings=%d category_gaps=%d slot_gaps=%d missing_pairs=%d unresolved_blocked=%d" % (
        len(docs), len(clauses), len(t["param"]), len(t["decision"]), len(errors), len(warnings), len(cat_gaps),
        len(slot_gaps), len(missing_pairs), len(blocked)))
    for x in errors:
        print("  ! " + x)
    return 1 if errors else 0


def write_status(docs, clauses, n_superseded, t, errors, warnings, missing_pairs, cat_gaps, blocked, slot_gaps):
    L = ["# STATUS", "", "Written by `tools/build.py` at every build; do not edit. The acceptance of one jurisdiction is "
         "`python database/tools/build.py --jur <code>` (数据库规范.md §5).", "",
         "| What | Count |", "|---|---|",
         "| Documents | %d |" % len(docs),
         "| Clauses | %d |" % len(clauses),
         "| Clauses left out (superseded.csv) | %d |" % n_superseded,
         "| Repealed-provision stubs left out | %d |" % len(SSO_DROPPED),
         "| Parameters | %d |" % len(t["param"]),
         "| Treaty rows | %d |" % len(t["treaty"]),
         "| Absence records | %d |" % len(t["decision"]),
         "| Errors / warnings | %d / %d |" % (len(errors), len(warnings)),
         "| Gaps: (jurisdiction, category) / (jurisdiction, subject, slot) / pairs without a treaty row / unresolved downloads | %d / %d / %d / %d |" % (
             len(cat_gaps), len(slot_gaps), len(missing_pairs), len(blocked)),
         "", "## Documents", "",
         "| id | jur | type | category | format | text | slicing | clauses | title |", "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(docs, key=lambda x: x["id"]):
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["id"], r["jur"], r["type"], r.get("category", ""), r.get("real_kind", ""), r.get("text_status", "missing"),
            r.get("slice_mode", ""), r.get("n_clauses", 0), (r["title"] or "").replace("|", "/")[:60]))
    L += ["", "## Errors", ""] + (["- " + x for x in errors] or ["None."])
    L += ["", "## Warnings", ""] + (["- " + x for x in warnings] or ["None."])
    L += ["", "## Gaps", "", "Cells of jurisdiction | category with neither a document nor an absence record:", ""]
    L += ["- " + g for g in cat_gaps] or ["None."]
    L += ["", "Cells of jurisdiction | subject | slot with neither a parameter nor an absence record:", ""]
    L += ["- " + g for g in slot_gaps] or ["None."]
    L += ["", "Pairs without a treaty row (a row with empty doc_id records \"no treaty\"):", ""]
    L += ["- " + p for p in missing_pairs] or ["None."]
    L += ["", "Downloads in blocked.csv not yet in doc.csv:", ""]
    L += ["- " + b for b in blocked] or ["None."]
    if SSO_DROPPED:
        L += ["", "## Repealed-provision stubs left out", ""] + ["- `%s`: %s" % (c, x[:80]) for c, x in SSO_DROPPED]
    if UNTRANSCRIBED:
        L += ["", "## Formula images in the text", "",
              "Singapore Statutes Online prints some formulas as images; the text shows a marker where each one stood.", ""]
        L += ["- `%s`: %s" % (d, u) for d, u in sorted(set(UNTRANSCRIBED))]
    (ROOT / "STATUS.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
