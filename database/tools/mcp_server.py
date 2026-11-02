#!/usr/bin/env python
"""tax-db: read-only MCP server over the library tables (database/数据库MCP规范.md).

  python database/tools/mcp_server.py --root database

Reads doc, clause, param, treaty, jurisdiction, superseded, decision and blocked plus STATUS.md once at start-up; restart
after a rebuild. Every answer carries `version`; errors come back as {"error": kind, "detail": text}. Nothing is written.
Python 3.11; depends on the `mcp` package (2.x: mcp.server.mcpserver.MCPServer) and the standard library.
"""
import argparse
import csv
import json
import hashlib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from find import search, sentence, squash  # noqa: E402

csv.field_size_limit(10 ** 9)
ENC = "utf-8-sig"
SERVER_VERSION = "0.1"


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding=ENC, newline="") as f:
        return list(csv.DictReader(f))


def sha16(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16] if path.exists() else ""


def err(kind, detail, **extra):
    out = {"error": kind, "detail": detail}
    out.update(extra)
    return out


class Library:
    def __init__(self, root):
        self.root = Path(root)
        self.docs = {r["id"]: r for r in read_csv(self.root / "doc.csv")}
        self.clauses = read_csv(self.root / "clause.csv")
        self.bodies = {}
        self.by_cite = {c["cite_id"]: c for c in self.clauses}
        self.order = {}                                        # doc_id -> [cite_id ...] in file order
        for c in self.clauses:
            self.order.setdefault(c["doc_id"], []).append(c["cite_id"])
        self.params = {r["param_id"]: r for r in read_csv(self.root / "param.csv")}
        self.treaties = read_csv(self.root / "treaty.csv")
        self.juris = read_csv(self.root / "jurisdiction.csv")
        self.superseded = read_csv(self.root / "superseded.csv")
        self.decisions = read_csv(self.root / "decision.csv")
        self.blocked = read_csv(self.root / "blocked.csv")
        self.status = self._status()
        self.version = {
            "database": {
                "docs": len(self.docs), "clauses": len(self.clauses), "params": len(self.params),
                "treaty_rows": len(self.treaties), "absence_records": sum(1 for d in self.decisions if ".absent." in d["id"]),
                "doc_csv_sha256": sha16(self.root / "doc.csv"), "param_csv_sha256": sha16(self.root / "param.csv"),
                "clause_csv_sha256": sha16(self.root / "clause.csv"),
                "status_written": self.status.get("written", ""),
            },
            "server": SERVER_VERSION,
        }

    def _status(self):
        p = self.root / "STATUS.md"
        out = {"counts": {}, "written": ""}
        if not p.exists():
            return out
        out["written"] = datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for line in p.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\|\s*(.+?)\s*\|\s*([0-9][0-9 /]*)\s*\|$", line)
            if m and m.group(1) not in ("What",):
                out["counts"][m.group(1)] = m.group(2).strip()
        return out

    def stamp(self, obj):
        obj["version"] = self.version
        return obj

    # ------------------------------------------------------------ tools
    def find(self, words, jur="", doc="", max_hits=20):
        words = [w for w in (words or []) if w and w.strip()]
        if not words:
            return err("invalid", "give one or more words")
        scope = [c for c in self.clauses if (not doc or c["doc_id"] == doc) and (not jur or self.docs.get(c["doc_id"], {}).get("jur") == jur)]
        hits, relaxed = search(scope, words, self.body)
        self.log_find(words, jur, doc, len(hits), relaxed)
        return self.stamp({"words": words, "jur": jur, "doc": doc, "total": len(hits), "relaxed": relaxed,
                           "hits": [{"cite_id": h["clause"]["cite_id"], "doc_id": h["clause"]["doc_id"], "label": h["clause"]["label"], "matched": h["matched"],
                                     "sentence": sentence(h["clause"]["text"], h["word"])} for h in hits[:max_hits]]})

    def body(self, clause):
        cached = self.bodies.get(clause["cite_id"])
        if cached is None:
            cached = self.bodies[clause["cite_id"]] = squash(clause["text"])
        return cached

    def log_find(self, words, jur, doc, total, relaxed):
        """What was searched and what came back: the evidence for or against semantic retrieval."""
        folder = self.root.parent / "cases" / "_log"
        if folder.is_dir():
            row = {"time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "words": words, "jur": jur, "doc": doc, "total": total, "relaxed": relaxed}
            with (folder / "find.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def clause(self, cite_id, offset=0, max_chars=0):
        c = self.by_cite.get(cite_id)
        if c is None:
            return err("not_found", "no clause %s" % cite_id, cite_id=cite_id)
        text = c["text"]
        total = len(text)
        offset = max(0, int(offset or 0))
        part = text[offset:offset + int(max_chars)] if max_chars else text[offset:]
        order = self.order.get(c["doc_id"], [])
        i = order.index(cite_id)
        d = self.docs.get(c["doc_id"], {})
        return self.stamp({"cite_id": cite_id, "doc_id": c["doc_id"], "label": c["label"], "text": part,
                           "offset": offset, "total_chars": total, "complete": offset == 0 and len(part) == total,
                           "doc_effective_from": d.get("effective_from", ""), "doc_effective_to": d.get("effective_to", ""),
                           "prev": order[i - 1] if i > 0 else None, "next": order[i + 1] if i + 1 < len(order) else None})

    def doc(self, doc_id):
        d = self.docs.get(doc_id)
        if d is None:
            return err("not_found", "no document %s" % doc_id, doc_id=doc_id)
        out = dict(d)
        out["clauses"] = len(self.order.get(doc_id, []))
        return self.stamp(out)

    def param(self, param_id):
        p = self.params.get(param_id)
        if p is None:
            return err("not_found", "no parameter %s" % param_id, param_id=param_id)
        return self.stamp(dict(p))

    def _scope_matches(self, scope, jur):
        return scope == jur or scope.startswith(jur + "-") or scope.endswith("-" + jur)

    def params_for(self, jur, slot="", subject=""):
        if not jur:
            return err("invalid", "give a jurisdiction code")
        rows = [dict(p) for p in self.params.values() if self._scope_matches(p["scope"], jur)
                and (not slot or p["slot"] == slot) and (not subject or p["subject"] in (subject, "all"))]
        rows.sort(key=lambda p: (p["slot"], p["subject"], p["param_id"]))
        return self.stamp({"jur": jur, "slot": slot, "subject": subject, "params": rows,
                           "absent": self._absent(jur, slot)})

    def _absent(self, jur, slot=""):
        return [dict(d) for d in self.decisions if ".absent." in d["id"] and d["jur"] == jur and (not slot or d["slot"] == slot)]

    def absent(self, jur, slot=""):
        if not jur:
            return err("invalid", "give a jurisdiction code")
        return self.stamp({"jur": jur, "slot": slot, "absent": self._absent(jur, slot)})

    def treaty(self, jur_a, jur_b=""):
        if not jur_a:
            return err("invalid", "give at least one jurisdiction code")
        rows = []
        for t in self.treaties:
            a, _, b = t["pair"].partition("-")
            if jur_b:
                if {a, b} == {jur_a, jur_b}:
                    rows.append(dict(t))
            elif jur_a in (a, b):
                rows.append(dict(t))
        for r in rows:
            d = self.docs.get(r["doc_id"], {})
            r["title"] = d.get("title", "")
            r["doc_effective_from"] = d.get("effective_from", "")
            r["doc_effective_to"] = d.get("effective_to", "")
        return self.stamp({"jur_a": jur_a, "jur_b": jur_b, "rows": rows})

    def jurisdictions(self):
        return self.stamp({"jurisdictions": [dict(j) for j in self.juris]})

    def param_history(self, param_id):
        p = self.params.get(param_id)
        if p is None:
            return err("not_found", "no parameter %s" % param_id, param_id=param_id)
        chain, seen, cur = [], set(), p
        while cur and cur["param_id"] not in seen:                # forward along superseded_by
            seen.add(cur["param_id"]); chain.append(dict(cur))
            cur = self.params.get(cur["superseded_by"]) if cur.get("superseded_by") else None
        back = [dict(q) for q in self.params.values() if q.get("superseded_by") == param_id]   # versions this one replaced
        doc_id = p["cite_id"].split("#")[0]
        sup = [dict(s) for s in self.superseded if s["doc_id"] == doc_id or s["by"] == p["cite_id"]]
        return self.stamp({"param_id": param_id, "versions": back + chain, "superseded_clauses": sup})

    def decision(self, id=""):
        rows = [dict(d) for d in self.decisions if not id or d["id"] == id]
        if id and not rows:
            return err("not_found", "no decision %s" % id, id=id)
        return self.stamp({"id": id, "decisions": rows})

    def blocked_docs(self):
        return self.stamp({"blocked": [dict(b) for b in self.blocked]})

    def version_info(self):
        return self.stamp({"status_counts": self.status["counts"]})


def build_server(root):
    from mcp.server.mcpserver import MCPServer
    lib = Library(root)
    s = MCPServer("tax-db", version=SERVER_VERSION,
                  instructions="Read-only queries of the tax law library (database/). Quotes and texts are verbatim.")

    @s.tool()
    def find(words: list[str], jur: str = "", doc: str = "", max: int = 20) -> dict:
        """Clauses containing the words (case and spacing ignored), most of the words first, then by BM25; a word that finds nothing is split and listed under relaxed; each with the sentence around the first word."""
        return lib.find(words, jur, doc, max)

    @s.tool()
    def clause(cite_id: str, offset: int = 0, max_chars: int = 0) -> dict:
        """One clause verbatim (paged with offset / max_chars), its document's effective dates and the neighbouring cite_ids."""
        return lib.clause(cite_id, offset, max_chars)

    @s.tool()
    def doc(doc_id: str) -> dict:
        """One document's doc.csv row: title, jurisdiction, type, category, source URL, file, language, effective dates."""
        return lib.doc(doc_id)

    @s.tool()
    def param(param_id: str) -> dict:
        """One parameter's param.csv row: value, unit, verbatim quote, cite_id, effective dates, note."""
        return lib.param(param_id)

    @s.tool()
    def params_for(jur: str, slot: str = "", subject: str = "") -> dict:
        """All parameters of a jurisdiction (and its treaty pairs), optionally one slot / subject, plus the absence records."""
        return lib.params_for(jur, slot, subject)

    @s.tool()
    def absent(jur: str, slot: str = "") -> dict:
        """Absence records: slots a jurisdiction has no tax or relief for, as recorded in decision.csv."""
        return lib.absent(jur, slot)

    @s.tool()
    def treaty(jur_a: str, jur_b: str = "") -> dict:
        """treaty.csv rows of a jurisdiction pair (either order), or every treaty of one jurisdiction."""
        return lib.treaty(jur_a, jur_b)

    @s.tool()
    def jurisdictions() -> dict:
        """jurisdiction.csv: code, name, currency, whether companies / individuals are in scope."""
        return lib.jurisdictions()

    @s.tool()
    def param_history(param_id: str) -> dict:
        """All versions of a parameter along superseded_by, and superseded.csv rows touching its cited document."""
        return lib.param_history(param_id)

    @s.tool()
    def decision(id: str = "") -> dict:
        """decision.csv (library-level readings and absence records): one row by id, or all."""
        return lib.decision(id)

    @s.tool()
    def blocked() -> dict:
        """blocked.csv: official texts that could not be fetched, why, and the alternatives tried."""
        return lib.blocked_docs()

    @s.tool()
    def version() -> dict:
        """Library build version: table counts, csv hashes, STATUS.md counts and write time."""
        return lib.version_info()

    return s, lib


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]), help="library folder (default: database/)")
    a = ap.parse_args()
    server, _ = build_server(a.root)
    server.run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
