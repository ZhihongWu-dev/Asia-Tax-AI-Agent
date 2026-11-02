#!/usr/bin/env python
"""Upload the library to the shared remote by overwriting it (数据库规范.md §4.5).

  python database/tools/upload.py [--jur cn ...] [--partial] [--dry-run] [--schema database] [--bucket database]

The jurisdictions that pass the acceptance (§5; every jurisdiction of jurisdiction.csv when no --jur is given; with
--partial also those with gaps but no error) are uploaded, and the remote is replaced by exactly that data:
  1. files: every raw/ and text/ file of those jurisdictions, and the spec and task sheet in Chinese and English (DOCS,
     under docs/), are written to the bucket (a path already there is overwritten); then every other object is deleted;
  2. tables: in one transaction the schema is dropped and created again with the seven tables and their rows, so a
     failure leaves the previous tables as they were.
Nothing is compared and nothing is checked afterwards. Upload from the folder that holds everyone's data: what is not
in it is gone from the remote afterwards.
--dry-run     print what would be uploaded; write nothing
Credentials (never printed) come from the environment or the .env next to or above database/: database_url for
Postgres, supabase_url and supabase_key for the bucket. The tools and samples/ are not uploaded. The bucket has a standing rule that lets the publishable key
(role anon) read and write it, so a publishable key is enough. Uploaded: the seven tables, raw/, text/ and the four docs.
Exit code 0 when the upload went through, 1 otherwise.
"""
import argparse
import csv
import io
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build                               # noqa: E402  tables, subset of one jurisdiction
import fetch                               # noqa: E402  secrets from the environment or .env

csv.field_size_limit(10 ** 9)
TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
KEY = {"jurisdiction": "code", "treaty": "pair", "doc": "id", "clause": "cite_id", "param": "param_id",
       "files": "path", "decision": "id"}
ORDER = ["jurisdiction", "doc", "clause", "param", "treaty", "decision", "files"]
SAFE_PATH = re.compile(r"^[A-Za-z0-9._/-]+$")
SAFE_NAME = re.compile(r"^[a-z0-9_-]{1,63}$")
DOCS = {"数据库规范.md": "docs/spec.zh.md", "database_spec.en.md": "docs/spec.en.md",      # local file -> bucket path;
        "采集任务单.md": "docs/task_sheet.zh.md", "collection_task_sheet.en.md": "docs/task_sheet.en.md"}   # uploaded each time


def clean(msg, secrets):
    for s in secrets:
        if s:
            msg = msg.replace(s, "***")
    return re.sub(r"postgres(?:ql)?(?:[+]psycopg)?://[^ ]+", "<database_url>", msg)


# ---------------------------------------------------------------- remote
class Bucket:
    def __init__(self, url, key, name):
        import requests
        self.http, self.base, self.name = requests.Session(), url.rstrip("/") + "/storage/v1", name
        self.http.headers.update({"apikey": key})
        if key.startswith("eyJ"):                         # a legacy service_role JWT also goes in Authorization
            self.http.headers["Authorization"] = "Bearer " + key

    def ensure(self):
        if self.http.get("%s/bucket/%s" % (self.base, self.name), timeout=60).status_code == 200:
            return
        r = self.http.post("%s/bucket" % self.base, json={"id": self.name, "name": self.name, "public": False}, timeout=60)
        if r.status_code not in (200, 201):
            raise RuntimeError("cannot see or create bucket %s: HTTP %s %s" % (self.name, r.status_code, r.text[:120]))

    def put(self, path, data, ctype="application/octet-stream"):
        """Write one object; a server error (5xx, e.g. Cloudflare 520) or a dropped connection is tried again twice."""
        import time
        import requests
        for attempt in range(3):
            try:
                r = self.http.post("%s/object/%s/%s" % (self.base, self.name, quote(path)), data=data, timeout=600,
                                   headers={"Content-Type": ctype, "x-upsert": "true"})
            except requests.RequestException as e:
                if attempt == 2:
                    raise RuntimeError("upload of %s failed: %s" % (path, type(e).__name__))
                time.sleep(5 * (attempt + 1))
                continue
            if r.status_code in (200, 201):
                return
            if r.status_code < 500 or attempt == 2:
                hint = (" (with a publishable key the bucket needs its standing rule for role anon, 数据库规范.md 4.5)"
                        if r.status_code in (400, 401, 403) else "")
                raise RuntimeError("upload of %s failed: HTTP %s %s%s" % (path, r.status_code, " ".join(r.text[:120].split()), hint))
            time.sleep(5 * (attempt + 1))

    def delete(self, paths):
        for i in range(0, len(paths), 100):
            r = self.http.delete("%s/object/%s" % (self.base, self.name), json={"prefixes": paths[i:i + 100]}, timeout=120)
            if r.status_code != 200:
                raise RuntimeError("deleting old files failed: HTTP %s %s" % (r.status_code, r.text[:120]))


def replace_tables(con, schema, rows):
    """Drop the schema and create it again with the seven tables and their rows, in one transaction."""
    with con.cursor() as cur:
        cur.execute('DROP SCHEMA IF EXISTS "%s" CASCADE' % schema)
        cur.execute('CREATE SCHEMA "%s"' % schema)
        for name in ORDER:
            cols = build.TABLES[name]
            cur.execute('CREATE TABLE "%s"."%s" (%s, PRIMARY KEY ("%s"))' % (
                schema, name, ", ".join('"%s" TEXT' % c for c in cols), KEY[name]))
            with cur.copy('COPY "%s"."%s" (%s) FROM STDIN' % (schema, name, ", ".join('"%s"' % c for c in cols))) as cp:
                for r in rows[name].values():
                    cp.write_row([str(r.get(c) or "") for c in cols])
    con.commit()


# ---------------------------------------------------------------- plan
def accepted(jur, partial):
    """Runs build.py --jur; returns (ok, the acceptance line)."""
    p = subprocess.run([sys.executable, str(TOOLS / "build.py"), "--root", str(ROOT), "--jur", jur],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    line = next((ln for ln in p.stdout.splitlines() if ln.startswith("acceptance")), p.stdout.strip()[-200:])
    if p.returncode == 0:
        return True, line
    m = re.search(r"errors=(\d+)", line)
    return bool(partial and m and m.group(1) == "0"), line


def plan_rows(jurs):
    """Rows and files of the given jurisdictions, as the acceptance sees them (build.subset)."""
    t = {name: build.read_csv(ROOT / (name + ".csv")) for name in build.FILLED}
    codes = {j["code"] for j in t["jurisdiction"]}
    rows = {name: {} for name in ORDER}
    for j in t["jurisdiction"]:
        rows["jurisdiction"][j["code"]] = j
    for jur in jurs:
        sub = build.subset(t, jur, codes)
        for name in ("doc", "param", "decision", "treaty"):
            for r in sub[name]:
                rows[name][r[KEY[name]]] = r
    doc_ids = set(rows["doc"])
    for c in build.read_csv(ROOT / "clause.csv"):
        if c["doc_id"] in doc_ids:
            rows["clause"][c["cite_id"]] = c
    paths = set()
    for d in rows["doc"].values():
        paths.add(d["file"])
        if (ROOT / "text" / (d["id"] + ".txt")).exists():
            paths.add("text/%s.txt" % d["id"])
    for f in build.read_csv(ROOT / "files.csv"):
        if f["path"] in paths:
            rows["files"][f["path"]] = f
    return rows, sorted(paths)


def main():
    global ROOT
    ap = argparse.ArgumentParser()
    ap.add_argument("--jur", action="append", default=[], help="jurisdiction to upload (repeatable; default: all that pass)")
    ap.add_argument("--partial", action="store_true", help="also upload a jurisdiction with gaps but no error")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--schema", default="database")
    ap.add_argument("--bucket", default="database")
    ap.add_argument("--root", default="", help="library folder (default: database/)")
    args = ap.parse_args()
    if args.root:
        ROOT = Path(args.root).resolve()
    build.ROOT = fetch.ROOT = ROOT
    if not SAFE_NAME.match(args.schema) or not SAFE_NAME.match(args.bucket):
        print("! schema and bucket names: only a-z 0-9 _ -")
        return 1

    # 1. a full build, then the acceptance of each jurisdiction
    subprocess.run([sys.executable, str(TOOLS / "build.py"), "--root", str(ROOT)], capture_output=True)
    jurs = args.jur or [j["code"] for j in build.read_csv(ROOT / "jurisdiction.csv")]
    ok_jurs = []
    for jur in jurs:
        ok, line = accepted(jur, args.partial)
        print(("  upload  " if ok else "  refused ") + line)
        if ok:
            ok_jurs.append(jur)
    if not ok_jurs:
        print("! nothing to upload: no jurisdiction passed (use --partial for one with gaps but no error)")
        return 1
    rows, paths = plan_rows(ok_jurs)
    bad = [p for p in paths if not SAFE_PATH.match(p)]
    if bad:
        print("! file paths must be ASCII letters, digits, . _ - /: %s" % ", ".join(bad[:5]))
        return 1
    print("  plan    %d rows in %d tables, %d files; they replace the remote schema %s and bucket %s" % (
        sum(len(v) for v in rows.values()), len(ORDER), len(paths), args.schema, args.bucket))
    if args.dry_run:
        print("dry run: nothing written")
        return 0

    # 2. files, then tables
    dsn = fetch.secret("database_url").replace("postgresql+psycopg://", "postgresql://")
    url, key = fetch.secret("supabase_url"), fetch.secret("supabase_key")
    secrets = [dsn, key]
    try:
        import psycopg
        con = psycopg.connect(dsn, connect_timeout=30)
    except Exception as e:                                     # noqa: BLE001
        print("! database not reachable: %s: %s" % (type(e).__name__, clean(str(e), secrets)[:200]))
        return 1
    try:
        bucket = Bucket(url, key, args.bucket)
        bucket.ensure()
        for k, p in enumerate(paths, 1):
            bucket.put(p, (ROOT / p).read_bytes())
            if k % 25 == 0 or k == len(paths):
                print("  files   %d/%d written" % (k, len(paths)))
        docs = {remote: ROOT / local for local, remote in DOCS.items() if (ROOT / local).exists()}
        for remote, local in docs.items():
            bucket.put(remote, local.read_bytes(), "text/markdown; charset=utf-8")
        print("  docs    %d written (%s)" % (len(docs), ", ".join(sorted(docs))))
        with con.cursor() as cur:
            cur.execute("SELECT name FROM storage.objects WHERE bucket_id = %s", (args.bucket,))
            stale = sorted({r[0] for r in cur.fetchall()} - set(paths) - set(docs))
        con.commit()
        bucket.delete(stale)
        print("  files   %d old files deleted" % len(stale))
    except Exception as e:                                     # noqa: BLE001
        print("! file step stopped: %s: %s; the tables were not touched" % (type(e).__name__, clean(str(e), secrets)[:300]))
        con.close()
        return 1
    try:
        replace_tables(con, args.schema, rows)
    except Exception as e:                                     # noqa: BLE001
        con.rollback()
        print("! tables not replaced: %s: %s; the previous tables are unchanged" % (type(e).__name__, clean(str(e), secrets)[:300]))
        return 1
    finally:
        con.close()
    print("uploaded: %d rows, %d files; remote schema %s and bucket %s replaced" % (
        sum(len(v) for v in rows.values()), len(paths), args.schema, args.bucket))
    return 0


if __name__ == "__main__":
    sys.exit(main())
