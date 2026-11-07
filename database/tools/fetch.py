#!/usr/bin/env python
"""Download one official document into the minimal library, keep the raw bytes untouched, and register it in doc.csv.

Conda env "tax" (Python 3.11); packages in database/requirements.txt.
  python database/tools/fetch.py --id my.ita1967 --jur my --type law --category "1;3;4" --title "Income Tax Act 1967" --url https://... \
      [--effective YYYY-MM-DD] [--effective-to YYYY-MM-DD] [--lang en] [--note "..."] [--with-attachments] [--engine curl]
  python database/tools/fetch.py --register-file PATH --id ... --jur ... --type ... --title ... --url <where it came from>
  python database/tools/fetch.py --blocked --id ... --jur ... --title ... --url ... --reason "..." [--alt-tried "..."]
  law.go.kr: write OC=<OC> in --url; the id comes from LAW_GO_KR_OC (environment or .env) and doc.csv keeps <OC>.
  add --root DIR to work on another library folder (tests).

One call = 1 attempt + 2 retries. The file goes to raw/<jur>/<id>.<ext>; the row (数据库规范.md §3, doc) goes to doc.csv,
with the retrieval facts in note. An id already in doc.csv is skipped; --force replaces its row and file.
Exit code 0 on success, 2 on failure.
"""
import argparse
import csv
import hashlib
import io
import json
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]                     # database/; --root points elsewhere (tests)
ENC = "utf-8-sig"
DOC_FIELDS = ["id", "jur", "type", "category", "title", "url", "file", "sha256", "lang", "effective_from", "effective_to", "note"]
BLOCKED_FIELDS = ["id", "jur", "title", "url", "reason", "alt_tried", "logged_at"]
DOC_TYPES = ("law", "regulation", "guidance", "treaty", "form", "page", "attachment")
CATEGORIES = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "page_treaties", "page_rates", "page_deadlines")   # 数据库规范.md §2
OFFICIAL = ("gov.cn", "gov.hk", "gov.sg", "go.id", "gov.vn", "gov.my", "go.th", "gov.ae", "go.jp", "go.kr",
            "chinhphu.vn", "vbpl.vn", "quochoi.vn",   # Vietnam: Government portal and gazette, legal database, National Assembly
            "baochinhphu.vn",        # Vietnam: the Government's online newspaper (Government Office); its English law pages are translations
            "klri.re.kr",            # Korea Legislation Research Institute: the official English translations of Korean acts
            "gov.in", "nic.in",      # incometaxindia.gov.in, egazette.gov.in, indiacode.nic.in
            "oecd.org")              # MLI texts and positions

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
ATT_EXT = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".rar", ".ofd", ".wps", ".et", ".rtf")
CT_EXT = {"application/pdf": "pdf", "text/html": "html", "application/msword": "doc",
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
          "application/vnd.ms-excel": "xls",
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
          "text/plain": "txt", "application/rtf": "rtf", "application/zip": "zip",
          "application/xml": "xml", "text/xml": "xml"}


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_official(url):
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in OFFICIAL)


ENGINE = "requests"


def curl_get(url, cookie=""):
    """One curl request. The chinatax CDN sometimes answers with a ~400-byte script that sets a cookie
    (document.cookie="C3VK=...") and reloads; in that case the request is repeated once with that cookie."""
    from urllib.parse import quote
    out = Path(tempfile.mkdtemp()) / "body"
    cmd = ["curl", "-s", "-L", "-m", "180", "-A", UA, "-o", str(out), "-w", "%{http_code} %{content_type}"]
    if cookie:
        cmd += ["-b", cookie]
    r = subprocess.run(cmd + [quote(url, safe=":/?&=%#")], capture_output=True, text=True)
    code, _, ctype = (r.stdout or "").partition(" ")
    if r.returncode != 0 or code != "200" or not out.exists():
        raise RuntimeError("curl HTTP %s rc=%s" % (code or "?", r.returncode))
    body = out.read_bytes()
    if not cookie and len(body) < 1000:
        m = re.search(rb'cookie="([A-Za-z0-9_]+=[A-Za-z0-9_]+);', body)
        if m:
            return curl_get(url, m.group(1).decode())
    return body, ctype.split(";")[0].strip().lower(), url


def get(url, insecure=False, min_bytes=800):
    """1 attempt + 2 retries. Returns (bytes, content_type, final_url) or raises RuntimeError."""
    last = ""
    for i, wait in enumerate((0, 4, 10)):
        if wait:
            time.sleep(wait)
        if ENGINE == "curl":
            try:
                content, ctype, final = curl_get(url)
                if len(content) < min_bytes:
                    last = "too small: %d bytes" % len(content)
                    continue
                return content, ctype, final
            except RuntimeError as e:
                last = str(e)
                continue
        try:
            r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
                             timeout=(20, 120), allow_redirects=True, verify=not insecure)
            if r.status_code != 200:
                last = "HTTP %s" % r.status_code
                continue
            if len(r.content) < min_bytes:
                last = "too small: %d bytes" % len(r.content)
                continue
            return r.content, r.headers.get("Content-Type", "").split(";")[0].strip().lower(), r.url
        except Exception as e:                                   # noqa: BLE001
            last = "%s: %s" % (type(e).__name__, str(e)[:200])
    raise RuntimeError("failed after 3 attempts (%s)" % last)


RE_SSO_PART = re.compile(rb'<div class="dms" data-field="seriesId" data-term="([0-9a-f-]{36})"></div>')
RE_SSO_TOC = re.compile(rb'"tocSysId":"([0-9a-f-]{36})"')


def get_once(url, insecure=False, min_bytes=200):
    """One request with the current engine, no retry. Returns (bytes, content_type, final_url) or raises RuntimeError."""
    if ENGINE == "curl":
        content, ctype, final = curl_get(url)
    else:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=(20, 120), allow_redirects=True, verify=not insecure)
        if r.status_code != 200:
            raise RuntimeError("HTTP %s" % r.status_code)
        content, ctype, final = r.content, r.headers.get("Content-Type", "").split(";")[0].strip().lower(), r.url
    if len(content) < min_bytes:
        raise RuntimeError("too small: %d bytes" % len(content))
    return content, ctype, final


def fill_sso_parts(content, url, insecure=False, pace=10.0, cooldown=240, tries=10):
    """Singapore Statutes Online sends a whole Act (?WholeDoc=1) with only its first parts filled in; every other part is
    an empty placeholder <div class="dms" data-field="seriesId" data-term="<id>"> that the browser loads later from
    /Details/GetLazyLoadContent. Each placeholder is replaced by its part, in page order, so the saved file holds the
    whole Act. The site lets a client without a browser make only a few requests in a row and then answers with an
    AWS WAF challenge (HTTP 202). The challenge is not solved or bypassed: the loader waits `cooldown` seconds and asks
    for the same part again, up to `tries` times, `pace` seconds between parts. A whole Act takes about an hour.
    Progress goes to stderr. Returns (content, number of parts filled); a part that still fails ends the download."""
    host = (urlparse(url).hostname or "").lower()
    ids = RE_SSO_PART.findall(content)
    toc = RE_SSO_TOC.search(content)
    if not host.endswith("sso.agc.gov.sg") or not ids or not toc:
        return content, 0
    base = "https://sso.agc.gov.sg/Details/GetLazyLoadContent?TocSysId=%s&SeriesId=" % toc.group(1).decode()
    for k, sid in enumerate(ids):
        time.sleep(pace)
        for attempt in range(1, tries + 1):
            try:
                part, _, _ = get_once(base + sid.decode(), insecure)
                break
            except RuntimeError as e:
                if attempt == tries:
                    raise RuntimeError("part %d of %d of the page (SeriesId %s): %s after %d tries; HTTP 202 is the site's "
                                       "AWS WAF challenge: retry later, or download in a browser (数据库规范.md 4.7)"
                                       % (k + 1, len(ids), sid.decode(), e, tries))
                print("part %d/%d: %s, waiting %d s" % (k + 1, len(ids), e, cooldown), file=sys.stderr, flush=True)
                time.sleep(cooldown)
        print("part %d/%d loaded" % (k + 1, len(ids)), file=sys.stderr, flush=True)
        placeholder = b'<div class="dms" data-field="seriesId" data-term="' + sid + b'"></div>'
        content = content.replace(placeholder, part, 1)
    return content, len(ids)


def guess_ext(content, ctype, url):
    if content[:5] == b"%PDF-":
        return "pdf"
    if ctype in CT_EXT:
        return CT_EXT[ctype]
    suffix = Path(urlparse(url).path).suffix.lower().lstrip(".")
    return suffix if 1 <= len(suffix) <= 5 else "bin"



def read_rows(path):
    if not path.exists():
        return []
    with path.open(encoding=ENC, newline="") as f:
        return list(csv.DictReader(f))


def write_rows(path, fields, rows):
    with path.open("w", encoding=ENC, newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def append_row(path, fields, row):
    new = not path.exists()
    with path.open("a", encoding=ENC, newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in fields})


def valid_jur(jur):
    """A jurisdiction code of jurisdiction.csv, a pair a-b of two codes, or intl (MLI, OECD)."""
    codes = {r["code"] for r in read_rows(ROOT / "jurisdiction.csv")}
    a, _, b = jur.partition("-")
    return jur == "intl" or jur in codes or (a in codes and b in codes and a != b)


SECRET_PARAMS = re.compile(r"((?:^|[?&])OC=)[^&#]+")       # law.go.kr: the OC id of the applicant never goes into doc.csv


def secret(name):
    """A key such as LAW_GO_KR_OC from the environment, or from a .env file next to or above the library folder."""
    import os
    for k, v in os.environ.items():
        if k.lower() == name.lower() and v.strip():
            return v.strip()
    for env in (ROOT / ".env", ROOT.parent / ".env"):
        if env.exists():
            for ln in env.read_text(encoding="utf-8", errors="replace").splitlines():
                m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", ln)
                if m and m.group(1).lower() == name.lower() and m.group(2).strip():
                    return m.group(2).strip().strip('"').strip("'")
    return ""


def mask(url):
    return SECRET_PARAMS.sub(lambda m: m.group(1) + "<OC>", url)


def save(args, doc_id, content, ext, url, title, doc_type, how, parent=""):
    """Write raw/<jur>/<id>.<ext> and the doc.csv row; with --force an existing row (and its file) is replaced."""
    out_dir = ROOT / "raw" / args.jur
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / ("%s.%s" % (doc_id, ext))
    rel = out.relative_to(ROOT).as_posix()
    rows = read_rows(ROOT / "doc.csv")
    old = [r for r in rows if r["id"] == doc_id]
    for r in old:                                        # --force: the earlier file of this id goes with its row
        f = ROOT / r["file"]
        if r["file"] != rel and r["file"].startswith("raw/") and f.is_file():
            f.unlink()
    out.write_bytes(content)
    host = (urlparse(url).hostname or "").lower()
    facts = [args.note] if args.note else []
    if parent:
        facts.append("parent=%s" % parent)
    facts.append("%s %s" % (how, now()))
    if not is_official(url):
        facts.append("host %s is not on the official list" % host)
    url = mask(url)
    row = {"id": doc_id, "jur": args.jur, "type": doc_type, "category": args.category, "title": title, "url": url, "file": rel,
           "sha256": hashlib.sha256(content).hexdigest(), "lang": args.lang,
           "effective_from": args.effective, "effective_to": args.effective_to, "note": "; ".join(facts)}
    if old:
        write_rows(ROOT / "doc.csv", DOC_FIELDS, [row if r["id"] == doc_id else r for r in rows])
    else:
        append_row(ROOT / "doc.csv", DOC_FIELDS, row)
    print(json.dumps({"saved": doc_id, "file": rel, "bytes": len(content), "ext": ext,
                      "official_domain": is_official(url), "replaced": bool(old)}, ensure_ascii=False))
    return row


def main():
    global ROOT, ENGINE
    p = argparse.ArgumentParser()
    p.add_argument("--id", required=True)
    p.add_argument("--jur", required=True, help="code of jurisdiction.csv, a pair such as cn-hk, or intl")
    p.add_argument("--type", default="", help="|".join(DOC_TYPES))
    p.add_argument("--category", default="", help="one or more of %s, separated by ; (attachments inherit it)" % "/".join(CATEGORIES))
    p.add_argument("--title", required=True)
    p.add_argument("--url", required=True)
    p.add_argument("--effective", default="")
    p.add_argument("--effective-to", default="")
    p.add_argument("--lang", default="")
    p.add_argument("--note", default="")
    p.add_argument("--with-attachments", action="store_true")
    p.add_argument("--insecure", action="store_true")
    p.add_argument("--engine", default="requests", choices=["requests", "curl"],
                   help="curl: use the curl command line (not challenged by the chinatax CDN)")
    p.add_argument("--pace", type=float, default=2.0, help="seconds to wait between attachment downloads")
    p.add_argument("--min-bytes", type=int, default=800)
    p.add_argument("--force", action="store_true", help="replace the row and file of an id already in doc.csv")
    p.add_argument("--register-file", default="", help="register a local copy obtained another way; --url says where it came from")
    p.add_argument("--blocked", action="store_true")
    p.add_argument("--reason", default="")
    p.add_argument("--alt-tried", default="")
    p.add_argument("--root", default="", help="library folder (default: database/)")
    args = p.parse_args()
    if args.root:
        ROOT = Path(args.root).resolve()
    ENGINE = args.engine
    if not valid_jur(args.jur):
        print(json.dumps({"failed": args.id, "reason": "jur %r is not in jurisdiction.csv, a pair or intl" % args.jur}))
        return 2
    if not args.blocked and args.type not in DOC_TYPES:
        print(json.dumps({"failed": args.id, "reason": "--type must be one of %s" % "|".join(DOC_TYPES)}))
        return 2
    cats = [c for c in re.split(r"[;,\s]+", args.category) if c]
    if any(c not in CATEGORIES for c in cats) or (not args.blocked and not cats and args.type != "treaty" and "-" not in args.jur and args.jur != "intl"):
        print(json.dumps({"failed": args.id, "reason": "--category must be one or more of %s, separated by ;" % "/".join(CATEGORIES)}))
        return 2
    args.category = ";".join(cats)
    if not args.blocked and not args.lang.strip():
        print(json.dumps({"failed": args.id, "reason": "--lang is required (the language code of the file, such as zh, en, th)"}))
        return 2
    if not re.fullmatch(r"[A-Za-z0-9._\-]+", args.id):
        print(json.dumps({"failed": args.id, "reason": "--id may only hold ASCII letters, digits, . _ -"}, ensure_ascii=False))
        return 2
    prefix = "intl." if args.jur == "intl" else ("treaty.%s." % args.jur if "-" in args.jur else args.jur + ".")
    if not args.id.startswith(prefix):
        print(json.dumps({"failed": args.id, "reason": "--id must start with %s" % prefix}))
        return 2
    if args.type == "treaty" and args.jur != "intl" and "-" not in args.jur:
        print(json.dumps({"failed": args.id, "reason": "a treaty document's --jur must be its pair (such as cn-hk) or intl"}))
        return 2

    if args.blocked:
        append_row(ROOT / "blocked.csv", BLOCKED_FIELDS,
                   {"id": args.id, "jur": args.jur, "title": args.title, "url": args.url,
                    "reason": args.reason, "alt_tried": args.alt_tried, "logged_at": now()})
        print(json.dumps({"blocked": args.id}, ensure_ascii=False))
        return 0

    if any(r["id"] == args.id for r in read_rows(ROOT / "doc.csv")) and not args.force:
        print(json.dumps({"skipped": args.id, "why": "already in doc.csv; use --force to replace it"}))
        return 0

    if args.register_file:
        src = Path(args.register_file)
        content = src.read_bytes()
        ext = src.suffix.lstrip(".") or "txt"
        save(args, args.id, content, ext, args.url, args.title, args.type, "registered from a local copy (%s)" % src.name)
        return 0

    try:
        url = args.url
        if "<OC>" in url:                                   # law.go.kr DRF: the applicant's OC id is filled in here only
            oc = secret("LAW_GO_KR_OC")
            if not oc:
                print(json.dumps({"failed": args.id, "reason": "the url needs the OC id of law.go.kr: set LAW_GO_KR_OC in the "
                                  "environment or in .env (数据库规范.md 4.7)"}, ensure_ascii=False))
                return 2
            url = url.replace("<OC>", oc)
        content, ctype, final_url = get(url, args.insecure, args.min_bytes)
        content, n_parts = fill_sso_parts(content, final_url, args.insecure, max(args.pace, 10.0))
    except RuntimeError as e:
        print(json.dumps({"failed": args.id, "url": args.url, "reason": str(e)}, ensure_ascii=False))
        return 2
    ext = guess_ext(content, ctype, final_url)
    how = "downloaded with %s" % ENGINE + (" and %d lazy-loaded parts of the page filled in" % n_parts if n_parts else "")
    save(args, args.id, content, ext, final_url, args.title, args.type, how)

    if args.with_attachments and ext == "html":
        soup = BeautifulSoup(content, "lxml")
        seen, n = set(), 0
        for a in soup.find_all("a", href=True):
            href = urljoin(final_url, a["href"].strip())
            if not urlparse(href).path.lower().endswith(ATT_EXT) or href in seen:
                continue
            seen.add(href)
            n += 1
            if n > 20:
                break
            time.sleep(args.pace)
            att_id = "%s.a%02d" % (args.id, n)
            name = " ".join(a.get_text(" ", strip=True).split()) or Path(urlparse(href).path).name
            try:
                c2, ct2, u2 = get(href, args.insecure, 300)
                save(args, att_id, c2, guess_ext(c2, ct2, u2), u2, name[:200], "attachment", "downloaded with %s" % ENGINE,
                     parent=args.id)
            except RuntimeError as e:
                print(json.dumps({"failed": att_id, "url": href, "reason": str(e)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
