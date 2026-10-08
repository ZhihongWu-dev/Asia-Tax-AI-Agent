#!/usr/bin/env python
"""Exact lookups on official.sqlite. Python 3.9, conda env "pytorch".

  python official/tools/query.py source "treaty.cn-hk.2006.zh#10.2"
  python official/tools/query.py cell "pair(CN,HK)" DIVIDEND [topic] [--on 2021-06-30]
  python official/tools/query.py doc treaty.cn-hk.2006.zh
  python official/tools/query.py find "受益所有人" [--doc cn.sta.2018-09]
"""
import io
import sqlite3
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
DB = Path(__file__).resolve().parents[1] / "official.sqlite"


def connect():
    con = sqlite3.connect(str(DB))
    con.row_factory = sqlite3.Row
    return con


def source(cite_id):
    """Clause text by exact cite_id."""
    with connect() as con:
        return con.execute("SELECT * FROM clause WHERE cite_id = ?", (cite_id,)).fetchone()


def cell(scope, income, topic=None, on=None):
    """Parameters of one cell: scope is a jurisdiction (CN) or a pair (pair(CN,HK)); income also matches ALL.
    With `on`, keep rows whose effective_from is empty or not later than that date."""
    q = "SELECT * FROM param WHERE scope = ? AND income IN (?, 'ALL')"
    args = [scope, income]
    if topic:
        q += " AND topic = ?"
        args.append(topic)
    if on:
        q += " AND (effective_from = '' OR effective_from <= ?) AND (effective_to = '' OR effective_to > ?)"
        args += [on, on]
    with connect() as con:
        return con.execute(q + " ORDER BY param_id", args).fetchall()


def doc(doc_id):
    with connect() as con:
        d = con.execute("SELECT * FROM doc WHERE id = ?", (doc_id,)).fetchone()
        n = con.execute("SELECT kind, COUNT(*) c FROM clause WHERE doc_id = ? GROUP BY kind", (doc_id,)).fetchall()
    return d, n


def find(text, doc_id=None, limit=20):
    """Exact substring search in clause text; not a similarity search."""
    q, args = "SELECT cite_id, kind, text FROM clause WHERE instr(text, ?) > 0", [text]
    if doc_id:
        q += " AND doc_id = ?"
        args.append(doc_id)
    with connect() as con:
        return con.execute(q + " LIMIT ?", args + [limit]).fetchall()


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    cmd, args = argv[0], argv[1:]
    opt = {}
    for flag in ("--on", "--doc"):
        if flag in args:
            i = args.index(flag)
            opt[flag] = args[i + 1]
            args = args[:i] + args[i + 2:]
    if cmd == "source":
        r = source(args[0])
        print("NOT FOUND" if r is None else "[%s] %s\n%s" % (r["kind"], r["cite_id"], r["text"]))
    elif cmd == "cell":
        rows = cell(args[0], args[1], args[2] if len(args) > 2 else None, opt.get("--on"))
        for r in rows:
            print("%-38s %-10s %-34s = %s %s   <- %s  (from %s)" % (
                r["param_id"], r["topic"], r["name"], r["value"], r["unit"], r["cite_id"], r["effective_from"] or "?"))
        print("%d row(s)" % len(rows))
    elif cmd == "doc":
        d, n = doc(args[0])
        if d is None:
            print("NOT FOUND")
        else:
            for k in d.keys():
                if d[k]:
                    print("%-16s %s" % (k, d[k]))
            print("clauses          " + ", ".join("%s=%s" % (x["kind"], x["c"]) for x in n))
    elif cmd == "find":
        for r in find(args[0], opt.get("--doc")):
            i = r["text"].find(args[0])
            print("%-40s %s" % (r["cite_id"], r["text"][max(0, i - 40):i + 80].replace("\n", " ")))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
