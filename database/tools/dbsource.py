#!/usr/bin/env python
"""Where the layers above read the library from: the folder database/ or the shared remote, directly (数据库规范.md §4.5).

The setting tax_db (environment first, then the .env at the project root) chooses: `supabase` reads the tables from the
remote's Postgres and superseded.csv from its bucket; anything else, or no setting, leaves the readers on the folder. A --db argument spelled `supabase` chooses the remote for that one process. The collector's tools
(build, fetch, find, recite, merge, upload) always work on the folder.

  online(db)                  True when the remote is read
  remote()                    the process's one connection: rows(name), clause(cite_id), clauses(), meta(), digest(name)

Cache: what a process downloads (whole tables, superseded.csv, the digests) is kept in .cache/remote/<uploaded_at>/, so
the servers of one machine download each table once per upload; one process downloads while the others wait for it.
A new upload has a new uploaded_at, so a stale table is never read; older folders are deleted. tax_db_cache=off turns it
off. Single clauses asked by cite_id are not cached; they come from the cached clause table once it exists.

Read-only: the session is opened with default_transaction_read_only. Not on the remote: blocked.csv, STATUS.md and
session_log.md (rows("blocked") is empty; status() is made from meta). Credentials (never printed): database_url,
supabase_url and supabase_key, as for upload.py.
"""
import csv
import io
import os
import pickle
import re
import shutil
import threading
import time
from pathlib import Path
from urllib.parse import quote

PROJECT = Path(__file__).resolve().parents[2]
SCHEMA = BUCKET = "database"
TABLES = ("jurisdiction", "doc", "clause", "param", "treaty", "decision", "files")      # upload.ORDER
CACHE = PROJECT / ".cache" / "remote"
WAIT = 1800                                               # seconds a process waits for another one's download
csv.field_size_limit(10 ** 9)


def setting(name):
    """A value from the environment, or from the .env at the project root (names compared without case)."""
    for k, v in os.environ.items():
        if k.lower() == name.lower() and v.strip():
            return v.strip()
    env = PROJECT / ".env"
    if env.exists():
        for ln in env.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", ln)
            if m and m.group(1).lower() == name.lower() and m.group(2).strip():
                return m.group(2).strip().strip('"').strip("'")
    return ""


def online(db=None):
    return str(db or "") == "supabase" or setting("tax_db").lower() == "supabase"


class Remote:
    def __init__(self):
        self.lock = threading.RLock()
        self.con = None
        self.tables = {}
        self.texts = {}                                   # cite_id -> clause row, filled by clause() and clauses()
        self.all = None

    def _connect(self):
        import psycopg
        dsn = setting("database_url").replace("postgresql+psycopg://", "postgresql://")
        # prepare_threshold=None: the Supabase pooler (transaction mode) does not keep prepared statements
        con = psycopg.connect(dsn, connect_timeout=30, autocommit=True, prepare_threshold=None)
        con.execute("SET default_transaction_read_only = on")
        return con

    def query(self, sql, args=()):
        """Rows as dicts (NULL as ""); a dropped connection is opened again once."""
        import psycopg
        with self.lock:
            for attempt in (0, 1):
                try:
                    if self.con is None or self.con.closed:
                        self.con = self._connect()
                    cur = self.con.execute(sql, args)
                    cols = [d.name for d in cur.description]
                    return [dict(zip(cols, ("" if v is None else v for v in r))) for r in cur.fetchall()]
                except psycopg.OperationalError as e:
                    self.con = None
                    if attempt:
                        raise RuntimeError("the remote library is not reachable: %s" % type(e).__name__) from None

    def rows(self, name):
        """A table in the order it was uploaded (the order of the csv), or superseded / blocked."""
        with self.lock:
            if name not in self.tables:
                if name in TABLES:
                    self.tables[name] = self.cached(name, lambda: self.query('SELECT * FROM "%s"."%s" ORDER BY ctid' % (SCHEMA, name)))
                elif name == "superseded":
                    self.tables[name] = self.cached(name, lambda: list(csv.DictReader(io.StringIO(
                        self.object("superseded.csv").decode("utf-8-sig")))))
                elif name == "blocked":
                    self.tables[name] = []
                else:
                    raise ValueError("no table %s" % name)
            return self.tables[name]

    def clause(self, cite_id):
        """One clause row or None; asks the remote for this clause only, unless the clause table is already loaded."""
        with self.lock:
            if cite_id not in self.texts and self.all is None and self.path("clause") and self.path("clause").exists():
                self.clauses()
            if cite_id not in self.texts and self.all is None:
                got = self.query('SELECT * FROM "%s"."clause" WHERE cite_id = %%s' % SCHEMA, (cite_id,))
                self.texts[cite_id] = got[0] if got else None
            return self.texts.get(cite_id)

    def clauses(self):
        """Every clause row (about 40 MB; some 20 s): for the tools that search all texts."""
        with self.lock:
            if self.all is None:
                self.all = self.rows("clause")
                self.texts = {c["cite_id"]: c for c in self.all}
            return self.all

    def path(self, key):
        """The cache file of a table of this upload, or None when the cache is off or the upload has no stamp."""
        if setting("tax_db_cache").lower() in ("off", "0", "false", "no"):
            return None
        stamp = re.sub(r"[^0-9A-Za-z]", "", self.meta().get("uploaded_at", ""))
        return CACHE / stamp / (key + ".pickle") if stamp else None

    def cached(self, key, fetch):
        """fetch() once per upload on this machine: read from the cache, or fetched by this process while the others wait."""
        path = self.path(key)
        if path is None:
            return fetch()
        path.parent.mkdir(parents=True, exist_ok=True)
        lock = path.with_suffix(".lock")
        start = time.time()
        while True:
            if path.exists():
                try:
                    return pickle.loads(path.read_bytes())
                except Exception:                         # a damaged file: fetch it again
                    path.unlink(missing_ok=True)
            try:
                os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                break
            except FileExistsError:
                try:
                    if time.time() - lock.stat().st_mtime > WAIT:     # left by a process that died
                        lock.unlink(missing_ok=True)
                        continue
                except FileNotFoundError:
                    continue
                if time.time() - start > WAIT:
                    return fetch()
                time.sleep(1)
        try:
            data = fetch()
            tmp = path.with_suffix(".%d.tmp" % os.getpid())
            tmp.write_bytes(pickle.dumps(data, pickle.HIGHEST_PROTOCOL))
            os.replace(tmp, path)
            for old in CACHE.iterdir():                   # earlier uploads
                if old != path.parent:
                    shutil.rmtree(old, ignore_errors=True)
            return data
        finally:
            lock.unlink(missing_ok=True)

    def count(self, name):
        return int(self.query('SELECT count(*) AS n FROM "%s"."%s"' % (SCHEMA, name))[0]["n"])

    def meta(self):
        with self.lock:
            if "meta" not in self.tables:
                self.tables["meta"] = self.query('SELECT key, value FROM "%s"."meta"' % SCHEMA)
            return {r["key"]: r["value"] for r in self.tables["meta"]}

    def digest(self, name):
        """sha256[:16] of a table's rows, computed by the remote (so the clause texts are not downloaded)."""
        with self.lock:
            key = "digest:" + name
            if key not in self.tables:
                sql = ("SELECT encode(sha256(convert_to(coalesce(string_agg(t::text, chr(30) ORDER BY t.ctid), ''), 'UTF8')), 'hex') AS h "
                       'FROM "%s"."%s" t' % (SCHEMA, name))
                self.tables[key] = self.cached("digest_" + name, lambda: self.query(sql)[0]["h"][:16])
            return self.tables[key]

    def status(self):
        """What the folder's STATUS.md gives: the write time (here: the upload time), the counts of its first table and,
        from meta, the acceptance line of each jurisdiction."""
        m = self.meta()
        counts = {"Documents": len(self.rows("doc")), "Clauses": self.count("clause"), "Parameters": len(self.rows("param")),
                  "Treaty rows": len(self.rows("treaty")), "Absence records": len(self.rows("decision"))}
        counts = {k: str(v) for k, v in counts.items()}
        counts.update({"acceptance " + k[len("acceptance_"):]: v for k, v in sorted(m.items()) if k.startswith("acceptance_")})
        return {"written": m.get("uploaded_at", ""), "counts": counts}

    def object(self, path):
        import requests
        key = setting("supabase_key")
        headers = {"apikey": key}
        if key.startswith("eyJ"):
            headers["Authorization"] = "Bearer " + key
        url = "%s/storage/v1/object/%s/%s" % (setting("supabase_url").rstrip("/"), BUCKET, quote(path))
        r = requests.get(url, headers=headers, timeout=120)
        if r.status_code != 200:
            raise RuntimeError("the remote bucket has no %s (HTTP %s)" % (path, r.status_code))
        return r.content

    def version(self):
        """The stamp of the remote library: where it is read from and which upload."""
        m = self.meta()
        return {"source": "supabase", "uploaded_at": m.get("uploaded_at", ""), "spec_version": m.get("spec_version", "")}


_REMOTE = None


def remote():
    global _REMOTE
    if _REMOTE is None:
        _REMOTE = Remote()
    return _REMOTE
