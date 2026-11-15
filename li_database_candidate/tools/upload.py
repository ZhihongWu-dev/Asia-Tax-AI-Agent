#!/usr/bin/env python
"""Upload the library to the shared remote by overwriting it (数据库规范.md §4.5).

  python database/tools/upload.py [--jur cn ...] [--partial] [--dry-run] [--schema database] [--bucket database]

The jurisdictions that pass the acceptance (§5; every jurisdiction of jurisdiction.csv when no --jur is given; with
--partial also those with gaps but no error) are uploaded, and the remote is replaced by exactly that data:
  1. files: every raw/, ocr/ and text/ file of those jurisdictions, superseded.csv (the rows of their documents), and the
     spec and task sheet in Chinese and English (DOCS, under docs/), are written to the bucket (a path already there is
     overwritten); then every other object is deleted;
  2. tables: in one transaction the schema is dropped and created again with the seven tables and their rows and the
     table meta (key, value: spec_version, the sha256 of build.py and upload.py, the git commit of the tools, who
     uploaded and when, the acceptance line of each jurisdiction), so a failure leaves the previous tables as they were.
Before writing, the remote meta is read: a remote written under a newer specification (spec_version later than
build.SPEC_VERSION) is not overwritten; update the tools first. Nothing else is compared. Upload from the folder that
holds everyone's data: what is not in it is gone from the remote afterwards.
--dry-run     print what would be uploaded and the remote meta; write nothing
Credentials (never printed) come from the environment or the .env next to or above database/: database_url for
Postgres, supabase_url and supabase_key for the bucket. The tools and samples/ are not uploaded (their commit is in meta).
The bucket has a standing rule that lets the publishable key (role anon) read and write it, so a publishable key is
enough. Uploaded: the seven tables and meta, raw/, ocr/, text/, superseded.csv and the four docs.
Exit code 0 when the upload went through, 1 otherwise.
"""
import argparse
import csv
import datetime
import getpass
import hashlib
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


def tools_meta(accepted_lines):
    """The meta rows of this upload: who, when, with which specification and which tools."""
    def sha(name):
        return hashlib.sha256((TOOLS / name).read_bytes()).hexdigest()
    git = subprocess.run(["git", "-C", str(TOOLS), "rev-parse", "HEAD"], capture_output=True, text=True)
    dirty = subprocess.run(["git", "-C", str(TOOLS), "status", "--porcelain", "--", "."], capture_output=True, text=True)
    commit = git.stdout.strip() if git.returncode == 0 else "not a git checkout"
    if git.returncode == 0 and dirty.stdout.strip():
        commit += " (tools changed since)"
    meta = {"spec_version": build.SPEC_VERSION, "build_py_sha256": sha("build.py"), "upload_py_sha256": sha("upload.py"),
            "tools_commit": commit, "uploaded_by": getpass.getuser(),
            "uploaded_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    for line in accepted_lines:
        m = re.match(r"acceptance (\S+): (.*)$", line)
        if m:
            meta["acceptance_" + m.group(1)] = m.group(2)
    return meta


def remote_meta(con, schema):
    """The meta table of the remote as {key: value}; empty when the remote has none (written before 2026-11-07)."""
    with con.cursor() as cur:
        cur.execute("SELECT 1 FROM information_schema.tables WHERE table_schema = %s AND table_name = 'meta'", (schema,))
        if not cur.fetchone():
            return {}
        cur.execute('SELECT key, value FROM "%s"."meta"' % schema)
        return dict(cur.fetchall())


def replace_tables(con, schema, rows, meta):
    """Drop the schema and create it again with the seven tables, their rows and meta, in one transaction."""
    with con.cursor() as cur:
        # the COPY of clause (about 40 MB) runs past Supabase's default statement timeout on a slow uplink
        cur.execute("SET LOCAL statement_timeout = 0")
        cur.execute('DROP SCHEMA IF EXISTS "%s" CASCADE' % schema)
        cur.execute('CREATE SCHEMA "%s"' % schema)
        for name in ORDER:
            cols = build.TABLES[name]
            cur.execute('CREATE TABLE "%s"."%s" (%s, PRIMARY KEY ("%s"))' % (
                schema, name, ", ".join('"%s" TEXT' % c for c in cols), KEY[name]))
            with cur.copy('COPY "%s"."%s" (%s) FROM STDIN' % (schema, name, ", ".join('"%s"' % c for c in cols))) as cp:
                for r in rows[name].values():
                    cp.write_row([str(r.get(c) or "") for c in cols])
        cur.execute('CREATE TABLE "%s"."meta" ("key" TEXT PRIMARY KEY, "value" TEXT)' % schema)
        with cur.copy('COPY "%s"."meta" ("key", "value") FROM STDIN' % schema) as cp:
            for k, v in meta.items():
                cp.write_row([k, v])
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
        for folder in ("text", "ocr"):
            if (ROOT / folder / (d["id"] + ".txt")).exists():
                paths.add("%s/%s.txt" % (folder, d["id"]))
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
    ok_jurs, lines = [], []
    for jur in jurs:
        ok, line = accepted(jur, args.partial)
        print(("  upload  " if ok else "  refused ") + line)
        if ok:
            ok_jurs.append(jur)
            lines.append(line)
    if not ok_jurs:
        print("! nothing to upload: no jurisdiction passed (use --partial for one with gaps but no error)")
        return 1
    rows, paths = plan_rows(ok_jurs)
    bad = [p for p in paths if not SAFE_PATH.match(p)]
    if bad:
        print("! file paths must be ASCII letters, digits, . _ - /: %s" % ", ".join(bad[:5]))
        return 1
    doc_ids = set(rows["doc"])
    superseded = [r for r in build.read_csv(ROOT / "superseded.csv") if r["doc_id"] in doc_ids]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=build.SUPERSEDED, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    w.writerows(superseded)
    meta = tools_meta(lines)
    print("  plan    %d rows in %d tables + meta, %d files, superseded.csv %d rows; they replace the remote schema %s and bucket %s" % (
        sum(len(v) for v in rows.values()), len(ORDER), len(paths), len(superseded), args.schema, args.bucket))

    # 2. the remote meta, then files, then tables
    dsn = fetch.secret("database_url").replace("postgresql+psycopg://", "postgresql://")
    url, key = fetch.secret("supabase_url"), fetch.secret("supabase_key")
    secrets = [dsn, key]
    try:
        import psycopg
        con = psycopg.connect(dsn, connect_timeout=30)
        old = remote_meta(con, args.schema)
        con.commit()
    except Exception as e:                                     # noqa: BLE001
        print("! database not reachable: %s: %s" % (type(e).__name__, clean(str(e), secrets)[:200]))
        return 1
    print("  remote  " + (", ".join("%s=%s" % (k, old[k]) for k in ("spec_version", "tools_commit", "uploaded_by", "uploaded_at") if k in old)
                          or "no meta table: written before 2026-11-07 or by older tools"))
    if old.get("spec_version", "") > build.SPEC_VERSION:
        print("! the remote was written under the specification of %s, these tools follow %s: update the tools first"
              % (old["spec_version"], build.SPEC_VERSION))
        con.close()
        return 1
    if args.dry_run:
        print("dry run: nothing written")
        con.close()
        return 0
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
        bucket.put("superseded.csv", buf.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8")
        docs["superseded.csv"] = None
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
        replace_tables(con, args.schema, rows, meta)
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
