#!/usr/bin/env python
"""Read-only browser for the library: a map with the jurisdictions as nodes and the agreements between them as edges.
Everything is read from the csv files of database/ on each request (cached until a file changes), so the viewer needs
no upkeep when rows are added.

  python database/viewer/server.py [--port 8770]      then open http://127.0.0.1:8770

Edges: one per treaty.csv row (a treaty, or a recorded "no treaty"); one-way edges for list parameters of one
jurisdiction that name another by its code, such as cn.cfc.cfc_whitelist_jp (数据库规范.md §4.4).
"""
import argparse
import csv
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

csv.field_size_limit(10 ** 9)
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
_cache = {}


def table(name):
    p = ROOT / (name + ".csv")
    if not p.exists():
        return []
    stamp = p.stat().st_mtime
    hit = _cache.get(name)
    if hit and hit[0] == stamp:
        return hit[1]
    with p.open(encoding="utf-8-sig", newline="") as f:
        rows = [{(k or "").replace("﻿", ""): (v or "") for k, v in r.items()} for r in csv.DictReader(f)]
    _cache[name] = (stamp, rows)
    return rows


def codes():
    return [j["code"] for j in table("jurisdiction")]


def list_edges():
    out, cs = [], set(codes())
    for p in table("param"):
        name = p.get("name", "")
        if p["scope"] in cs and "_" in name and p.get("unit") == "bool" and p.get("value") == "yes":
            lst, tgt = name.rsplit("_", 1)
            if tgt in cs and tgt != p["scope"]:
                out.append({"type": "list", "a": p["scope"], "b": tgt, "list": lst, "param_id": p["param_id"]})
    return out


def graph():
    docs, params, dec = table("doc"), table("param"), table("decision")
    nodes = []
    for j in table("jurisdiction"):
        c = j["code"]
        nodes.append({"code": c, "name": j.get("name", ""), "currency": j.get("currency", ""),
                      "docs": sum(d["jur"] == c for d in docs), "params": sum(p["scope"] == c for p in params),
                      "absent": sum(x["jur"] == c for x in dec)})
    edges = []
    for t in table("treaty"):
        if "-" not in t["pair"]:
            continue
        a, b = t["pair"].split("-", 1)
        note = t.get("note", "")
        mli = "applies" if note.startswith("MLI applies") else ("not" if "MLI not applicable" in note else "")
        edges.append({"type": "treaty" if t.get("doc_id") else "none", "a": a, "b": b, "pair": t["pair"], "mli": mli,
                      "params": sum(p["scope"] == t["pair"] for p in params)})
    return {"nodes": nodes, "edges": edges + list_edges(),
            "pairs_owned": len(codes()) * (len(codes()) - 1) // 2, "pairs_recorded": len(table("treaty"))}


def doc_index():
    return {d["id"]: d for d in table("doc")}


def jurisdiction(code):
    j = next((x for x in table("jurisdiction") if x["code"] == code), None)
    if j is None:
        return None
    docs = [d for d in table("doc") if d["jur"] == code]
    pairs = [t for t in table("treaty") if code in t["pair"].split("-")]
    return {"jurisdiction": j, "docs": docs,
            "params": [p for p in table("param") if p["scope"] == code],
            "absent": [x for x in table("decision") if x["jur"] == code],
            "pairs": pairs,
            "lists_out": [e for e in list_edges() if e["a"] == code],
            "lists_in": [e for e in list_edges() if e["b"] == code]}


def pair(name):
    a, _, b = name.partition("-")
    t = next((x for x in table("treaty") if x["pair"] == name), None)
    docs = [d for d in table("doc") if d["jur"] == name]
    ids = {d["id"] for d in docs}
    return {"pair": name, "treaty": t, "docs": docs,
            "params": [p for p in table("param") if p["scope"] == name],
            "superseded": [s for s in table("superseded") if s.get("doc_id") in ids],
            "lists": [e for e in list_edges() if {e["a"], e["b"]} == {a, b}]}


def clause(cite_id):
    c = next((x for x in table("clause") if x["cite_id"] == cite_id), None)
    if c is None:
        return None
    d = doc_index().get(c["doc_id"], {})
    return {"cite_id": cite_id, "label": c.get("label", ""), "text": c.get("text", ""),
            "doc": {k: d.get(k, "") for k in ("id", "title", "url", "jur", "type", "lang")}}


def search(q):
    q = q.strip().lower()
    if len(q) < 2:
        return {"q": q, "hits": []}
    hits = []
    for d in table("doc"):
        if q in (d["id"] + " " + d.get("title", "")).lower():
            hits.append({"kind": "doc", "jur": d["jur"], "id": d["id"], "text": d.get("title", "")})
    for p in table("param"):
        if q in " ".join([p["param_id"], p.get("quote", ""), p.get("note", ""), p.get("value", "")]).lower():
            hits.append({"kind": "param", "jur": p["scope"], "id": p["param_id"], "text": "%s %s" % (p.get("value", ""), p.get("unit", "")),
                         "cite_id": p.get("cite_id", "")})
    for x in table("decision"):
        if q in (x["id"] + " " + x.get("statement", "")).lower():
            hits.append({"kind": "absent", "jur": x["jur"], "id": x["id"], "text": x.get("statement", "")[:160],
                         "cite_id": x.get("cite_id", "")})
    return {"q": q, "hits": hits[:80]}


class Handler(BaseHTTPRequestHandler):
    def _send(self, body, ctype="application/json; charset=utf-8", code=200):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        path = unquote(u.path)
        if path in ("/", "/index.html"):
            return self._send((HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
        if path == "/api/graph":
            return self._send(graph())
        if path.startswith("/api/jur/"):
            r = jurisdiction(path[9:])
            return self._send(r) if r else self._send({"error": "unknown jurisdiction"}, code=404)
        if path.startswith("/api/pair/"):
            return self._send(pair(path[10:]))
        if path.startswith("/api/clause/"):
            r = clause(path[12:])
            return self._send(r) if r else self._send({"error": "clause not found"}, code=404)
        if path == "/api/search":
            return self._send(search(parse_qs(u.query).get("q", [""])[0]))
        self._send({"error": "not found"}, code=404)

    def log_message(self, *a):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8770)
    args = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print("library viewer on http://127.0.0.1:%d  (Ctrl+C to stop)" % args.port, flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
