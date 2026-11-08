#!/usr/bin/env python
"""Where the layers above read the library from: the folder database/ or the shared remote, directly (数据库规范.md §4.5).

The setting tax_db (environment first, then the .env at the project root) chooses: `supabase` reads the tables from the
remote's Postgres and superseded.csv from its bucket, keeping nothing on disk; anything else, or no setting, leaves the
readers on the folder. A --db argument spelled `supabase` chooses the remote for that one process. The collector's tools
(build, fetch, find, recite, merge, upload) always work on the folder.

  online(db)                  True when the remote is read
  remote()                    the process's one connection: rows(name), clause(cite_id), clauses(), meta(), digest(name)

Read-only: the session is opened with default_transaction_read_only. Not on the remote: blocked.csv, STATUS.md and
session_log.md (rows("blocked") is empty; status() is made from meta). Credentials (never printed): database_url,
supabase_url and supabase_key, as for upload.py.
"""
import csv
import io
import os
import re
import threading
from pathlib import Path
from urllib.parse import quote

PROJECT = Path(__file__).resolve().parents[2]
SCHEMA = BUCKET = "database"
TABLES = ("jurisdiction", "doc", "clause", "param", "treaty", "decision", "files")      # upload.ORDER
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
                    self.tables[name] = self.query('SELECT * FROM "%s"."%s" ORDER BY ctid' % (SCHEMA, name))
                elif name == "superseded":
                    data = self.object("superseded.csv").decode("utf-8-sig")
                    self.tables[name] = list(csv.DictReader(io.StringIO(data)))
                elif name == "blocked":
                    self.tables[name] = []
                else:
                    raise ValueError("no table %s" % name)
            return self.tables[name]

    def clause(self, cite_id):
        """One clause row or None; asks the remote for this clause only, unless the clause table is already loaded."""
        with self.lock:
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
                got = self.query("SELECT encode(sha256(convert_to(coalesce(string_agg(t::text, chr(30) ORDER BY t.ctid), ''), 'UTF8')), 'hex') AS h "
                                 'FROM "%s"."%s" t' % (SCHEMA, name))
                self.tables[key] = got[0]["h"][:16]
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
