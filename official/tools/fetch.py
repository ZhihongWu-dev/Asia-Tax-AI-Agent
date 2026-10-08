#!/usr/bin/env python
"""Download one official document, keep the raw bytes untouched, and register it.

Usage (Python 3.9, conda env "pytorch"):
  python official/tools/fetch.py --id cn.sta.2018-09 --jur cn --type guidance \
      --title "..." --url https://... [--doc-no ...] [--issuer ...] [--issued YYYY-MM-DD]
      [--effective YYYY-MM-DD] [--lang zh] [--with-attachments] [--via curl|alt]
  python official/tools/fetch.py --register-file PATH --id ... --jur ... --type ... --title ... --url ...
  python official/tools/fetch.py --blocked --id ... --jur ... --title ... --url ... --reason "..."

One call = 1 attempt + 2 retries. Exit code 0 on success, 2 on failure.
"""
import argparse
import csv
import hashlib
import io
import json
import shutil
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

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]                     # official/
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
FIELDS = ["id", "jur", "type", "title", "doc_no", "issuer", "issued", "effective_from",
          "effective_to", "lang", "url", "file", "ext", "bytes", "sha256", "retrieved_at",
          "via", "verbatim", "official_domain", "parent", "note"]
BLOCKED_FIELDS = ["id", "jur", "title", "url", "reason", "alt_tried", "logged_at"]
ATT_EXT = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".rar", ".ofd", ".wps", ".et", ".rtf")
OFFICIAL = ("chinatax.gov.cn", "gov.cn", "npc.gov.cn", "court.gov.cn", "ird.gov.hk", "elegislation.gov.hk",
            "gov.hk", "iras.gov.sg", "agc.gov.sg", "mof.gov.sg", "gov.sg", "oecd.org", "europa.eu",
            "chinamoney.com.cn")          # 中国外汇交易中心：经人民银行授权发布人民币汇率中间价
CT_EXT = {"application/pdf": "pdf", "text/html": "html", "application/msword": "doc",
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
          "application/vnd.ms-excel": "xls",
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
          "text/plain": "txt", "application/rtf": "rtf", "application/zip": "zip"}


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


def guess_ext(content, ctype, url):
    if content[:5] == b"%PDF-":
        return "pdf"
    if ctype in CT_EXT:
        return CT_EXT[ctype]
    suffix = Path(urlparse(url).path).suffix.lower().lstrip(".")
    return suffix if 1 <= len(suffix) <= 5 else "bin"


def append_csv(path, fields, row):
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in fields})


def existing_ids(jur):
    p = ROOT / ("manifest_%s.csv" % jur)
    if not p.exists():
        return set()
    with p.open(encoding="utf-8-sig", newline="") as f:
        return {r["id"] for r in csv.DictReader(f)}


def save(args, doc_id, content, ext, url, title, doc_type, via, verbatim, parent=""):
    out_dir = ROOT / "raw" / args.jur
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / ("%s.%s" % (doc_id, ext))
    out.write_bytes(content)
    row = {"id": doc_id, "jur": args.jur, "type": doc_type, "title": title, "doc_no": args.doc_no,
           "issuer": args.issuer, "issued": args.issued, "effective_from": args.effective,
           "effective_to": args.effective_to, "lang": args.lang, "url": url,
           "file": str(out.relative_to(ROOT)).replace("\\", "/"), "ext": ext, "bytes": len(content),
           "sha256": hashlib.sha256(content).hexdigest(), "retrieved_at": now(), "via": via,
           "verbatim": verbatim, "official_domain": "yes" if is_official(url) else "no",
           "parent": parent, "note": args.note}
    append_csv(ROOT / ("manifest_%s.csv" % args.jur), FIELDS, row)
    print(json.dumps({"saved": row["id"], "file": row["file"], "bytes": row["bytes"], "ext": ext,
                      "official_domain": row["official_domain"]}, ensure_ascii=False))
    return row


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--id", required=True)
    p.add_argument("--jur", required=True, choices=["cn", "hk", "sg", "treaty", "intl"])
    p.add_argument("--type", default="", help="law|regulation|guidance|treaty|form|rates|example|guide|page")
    p.add_argument("--title", required=True)
    p.add_argument("--url", required=True)
    p.add_argument("--doc-no", default="")
    p.add_argument("--issuer", default="")
    p.add_argument("--issued", default="")
    p.add_argument("--effective", default="")
    p.add_argument("--effective-to", default="")
    p.add_argument("--lang", default="")
    p.add_argument("--via", default="curl", help="curl | alt")
    p.add_argument("--note", default="")
    p.add_argument("--with-attachments", action="store_true")
    p.add_argument("--insecure", action="store_true")
    p.add_argument("--engine", default="requests", choices=["requests", "curl"],
                   help="curl: use the curl command line (not challenged by the chinatax CDN)")
    p.add_argument("--pace", type=float, default=2.0, help="seconds to wait between attachment downloads")
    p.add_argument("--min-bytes", type=int, default=800)
    p.add_argument("--force", action="store_true")
    p.add_argument("--register-file", default="", help="register a local text copy obtained through web tools")
    p.add_argument("--blocked", action="store_true")
    p.add_argument("--reason", default="")
    p.add_argument("--alt-tried", default="")
    args = p.parse_args()
    global ENGINE
    ENGINE = args.engine

    if args.blocked:
        append_csv(ROOT / ("blocked_%s.csv" % args.jur), BLOCKED_FIELDS,
                   {"id": args.id, "jur": args.jur, "title": args.title, "url": args.url,
                    "reason": args.reason, "alt_tried": args.alt_tried, "logged_at": now()})
        print(json.dumps({"blocked": args.id}, ensure_ascii=False))
        return 0

    if args.id in existing_ids(args.jur) and not args.force:
        print(json.dumps({"skipped": args.id, "why": "already in manifest; use --force to add again"}))
        return 0

    if args.register_file:
        src = Path(args.register_file)
        content = src.read_bytes()
        ext = src.suffix.lstrip(".") or "md"
        save(args, args.id, content, ext, args.url, args.title, args.type, "webfetch_copy", "unverified")
        return 0

    try:
        content, ctype, final_url = get(args.url, args.insecure, args.min_bytes)
    except RuntimeError as e:
        print(json.dumps({"failed": args.id, "url": args.url, "reason": str(e)}, ensure_ascii=False))
        return 2
    ext = guess_ext(content, ctype, final_url)
    save(args, args.id, content, ext, final_url, args.title, args.type, args.via, "raw")

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
                save(args, att_id, c2, guess_ext(c2, ct2, u2), u2, name[:200], "attachment", args.via, "raw",
                     parent=args.id)
            except RuntimeError as e:
                print(json.dumps({"failed": att_id, "url": href, "reason": str(e)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
