"""Download a Singapore Statutes Online document whose body is lazy-loaded.
Usage: python official/tools/sso_whole.py <doc_id> <url?WholeDoc=1> "<title>" <type>
base page -> fetch.py (<id>), each lazy fragment -> fetch.py (<id>.fragNN), assembled copy -> --register-file (<id>.full)."""
import re, io, sys, json, subprocess, html as H, time
from pathlib import Path
import requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
doc_id, url, title, typ = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
extra = sys.argv[5:]
FETCH = [sys.executable, "official/tools/fetch.py"]
def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(r.returncode, r.stdout.strip()[:300], r.stderr.strip()[-300:])
    return r
common = ["--jur", "sg", "--type", typ, "--issuer", "Singapore Statutes Online (AGC)", "--lang", "en"] + extra
r = run(FETCH + ["--id", doc_id, "--title", title, "--url", url] + common + ["--note", "SSO base page; body parts are lazy-loaded, see %s.fragNN and %s.full" % (doc_id, doc_id)])
if r.returncode != 0:
    sys.exit(2)
base = Path("official/raw/sg/%s.html" % doc_id)
page = base.read_bytes().decode("utf-8")
gv = {}
for m in re.finditer(r"class=\"global-vars\" data-json='([^']+)'", page):
    gv.update(json.loads(H.unescape(m.group(1))))
fr = gv.get("fragments") or {}
terms = re.findall(r'<div class="dms" data-field="seriesId" data-term="([0-9a-f-]{36})"></div>', page)
out = page
for n, t in enumerate(terms, 1):
    params = {k: ("" if v is None else v) for k, v in gv["lazyLoadFilter"].items()}
    params["SeriesId"] = t
    if t in fr:
        params["FragSysId"] = fr[t]["Item1"]; params["_"] = fr[t]["Item2"]
    furl = requests.Request("GET", "https://sso.agc.gov.sg/Details/GetLazyLoadContent", params=params).prepare().url
    fid = "%s.frag%02d" % (doc_id, n)
    ph = '<div class="dms" data-field="seriesId" data-term="%s"></div>' % t
    try:
        probe = requests.get(furl, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}, timeout=120)
    except Exception as e:                           # noqa: BLE001 — the site is slow: let fetch.py (curl, 3 attempts) decide
        print("probe of fragment %d failed (%s); handing to fetch.py" % (n, type(e).__name__))
        probe = None
    if probe is not None and probe.status_code == 200 and len(probe.content) == 0:
        print("fragment %d is empty on the server (XmlTag=%s); placeholder removed" % (n, probe.headers.get("XmlTag")))
        out = out.replace(ph, "", 1)
        continue
    r = run(FETCH + ["--id", fid, "--title", "%s [lazy-load fragment %02d/%02d]" % (title, n, len(terms)), "--url", furl, "--min-bytes", "200"] + common + ["--note", "Lazy-load fragment %d of %d of %s (/Details/GetLazyLoadContent)" % (n, len(terms), doc_id)])
    if r.returncode != 0:
        print("FRAGMENT FAILED", fid); sys.exit(2)
    frag = Path("official/raw/sg/%s.html" % fid).read_bytes().decode("utf-8")
    ph = '<div class="dms" data-field="seriesId" data-term="%s"></div>' % t
    out = out.replace(ph, frag, 1)
    time.sleep(0.3)
full = Path("official/_conv/sso") / ("%s.full.html" % doc_id)
full.parent.mkdir(parents=True, exist_ok=True)
full.write_bytes(out.encode("utf-8"))
run(FETCH + ["--register-file", str(full).replace("\\", "/"), "--id", doc_id + ".full", "--title", title + " (assembled: base page + %d lazy-load fragments)" % len(terms), "--url", url] + common + ["--note", "Locally assembled from raw bytes of %s and its fragments in placeholder order; not a single server response" % doc_id])
from bs4 import BeautifulSoup
s = BeautifulSoup(out, "lxml")
legis = s.find(id="legisContent") or s
txt = " ".join(legis.get_text(" ", strip=True).split())
print("assembled text chars:", len(txt)); print(txt[:300]); print("...", txt[-300:])
