#!/usr/bin/env python
"""tax-opt: MCP server over the optimization layer (optimization/优化层MCP规范.md).

  python optimization/tools/mcp_server.py --root optimization --rule rule --db database --products-root cases --role front|reader

`run` and `diff` exist only in the `--role front` process. Every `products` / `input` path is relative to --products-root and
must stay inside it. Every answer carries `version`; errors come back as {"error": kind, "detail": text}; nothing is logged
here (the host hook does that). Python 3.11; depends on the `mcp` package (2.x) and this layer's own modules.
"""
import argparse
import hashlib
import io
import json
import sys
from contextlib import redirect_stdout
from datetime import date as _date, datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import optimize as op  # noqa: E402
import fx as fxmod  # noqa: E402
import check as chk  # noqa: E402

SERVER_VERSION = "0.1"


def err(kind, detail, **extra):
    out = {"error": kind, "detail": detail}
    out.update(extra)
    return out


class State:
    def __init__(self, root, rule, db, products_root, role):
        self.root, self.rule, self.db = Path(root), Path(rule), Path(db)
        self.products_root = Path(products_root).resolve()
        self.role = role
        q = op.Query(self.rule, self.db).version()
        self.version = {"optimization": {"rule": q["rule"], "database": q["database"], "server_started": q["generated_at"]},
                        "server": SERVER_VERSION}

    def stamp(self, obj, products=None):
        v = dict(self.version)
        if products is not None:
            vj = products / "version.json"
            if vj.exists():
                pv = op.jload(vj)
                v = dict(v, products={"inputs_sha256": pv.get("inputs_sha256"), "generated_at": pv.get("generated_at")})
        obj["version"] = v
        return obj

    # ------------------------------------------------------------ paths
    def inside(self, rel):
        """Resolve a path relative to the products root; None when it escapes the root."""
        if not rel or Path(rel).is_absolute():
            return None
        p = (self.products_root / rel).resolve()
        try:
            p.relative_to(self.products_root)
        except ValueError:
            return None
        return p

    def normalise(self, rel):
        """The same products folder written from the project root (cases/<case>/...) or from the case folder
        (intake/products/<run_id>, unique across cases) resolves as <case>/intake/products/<run_id>."""
        rel = str(rel or "").replace("\\", "/").strip("/")
        head = self.products_root.name + "/"
        if rel.startswith(head):
            rel = rel[len(head):]
        if rel.startswith("intake/products/"):
            hits = [p for p in self.products_root.glob("*/" + rel) if (p / "version.json").exists()]
            if len(hits) == 1:
                rel = str(hits[0].relative_to(self.products_root)).replace("\\", "/")
        return rel

    def products_dir(self, rel):
        rel = self.normalise(rel)
        p = self.inside(rel)
        if p is None:
            return None, err("forbidden", "products path must be relative to the products root and stay inside it", products=rel)
        if not (p / "version.json").exists():
            return None, err("not_found", "no products directory (version.json missing) at %s; the path is relative to the cases folder: <case_id>/intake/products/<run_id>" % rel, products=rel)
        return p, None

    def load(self, products, name):
        p, e = self.products_dir(products)
        if e:
            return None, None, e
        f = p / name
        if not f.exists():
            return p, None, err("not_found", "%s has no %s" % (products, name), products=products)
        return p, op.jload(f), None

    def optimizer(self, inp):
        return op.Optimizer(inp, root=self.rule, db=self.db)

    # ------------------------------------------------------------ run / validate / evaluate / diff
    def validate_input(self, rel):
        p = self.inside(rel)
        if p is None:
            return err("forbidden", "input path must be relative to the products root and stay inside it", input=rel)
        if not p.exists():
            return err("not_found", "no input file %s" % rel, input=rel)
        try:
            inp = op.jload(p)
            o = self.optimizer(inp)
        except BaseException as e:                              # noqa: BLE001  (Optimizer may raise SystemExit)
            return err("invalid", "%s: %s" % (type(e).__name__, e), input=rel)
        return self.stamp({"input": rel, "date": o.date, "mode": o.mode, "amount": o.amount if hasattr(o, "amount") else inp.get("amount"),
                           "currency": o.currency, "payer": o.payer.get("jur"), "payee": [o.payee.get("jur"), o.payee.get("subject")],
                           "entities": sorted(o.entities), "destinations": o.destinations,
                           "fx_loaded": bool(o.fx), "valuation": bool(o.valuation)})

    def run(self, case_id, rel):
        if not case_id or "/" in case_id or "\\" in case_id or case_id.startswith("."):
            return err("invalid", "case_id must be a plain directory name", case_id=case_id)
        p = self.inside(rel)
        if p is None:
            return err("forbidden", "input path must be relative to the products root and stay inside it", input=rel)
        if not p.exists():
            return err("not_found", "no input file %s" % rel, input=rel)
        raw = p.read_bytes()
        # the run id names the input and the code that computes it: the optimizer, the rules and the parameters
        code = b"".join(q.read_bytes() for q in (Path(op.__file__), Path(self.rule) / "rule.csv", Path(self.db) / "param.csv") if q.exists())
        run_id = "%s-%s" % (datetime.now(timezone.utc).strftime("%Y%m%d"), hashlib.sha256(raw + code).hexdigest()[:8])
        out = self.products_root / case_id / "intake" / "products" / run_id
        if out.exists():
            return err("conflict", "products directory already exists; the same input was run today", run_id=run_id,
                       products=str(out.relative_to(self.products_root)).replace("\\", "/"))
        try:
            inp = json.loads(raw.decode("utf-8-sig"))
            o = self.optimizer(inp)
            with redirect_stdout(io.StringIO()):
                summary = o.run(out)
        except BaseException as e:                              # noqa: BLE001
            return err("invalid", "%s: %s" % (type(e).__name__, e), input=rel)
        ranking = op.jload(out / "ranking.json")["ranking"]
        open_items = op.jload(out / "open_items.json")["open_items"]
        return self.stamp({"run_id": run_id, "products": str(out.relative_to(self.products_root)).replace("\\", "/"),
                           "candidates": summary.get("candidates"), "branches": summary.get("branches"),
                           "ranking_top": [r for r in ranking if r.get("rank")][:3],
                           "open_items_changing_rank": sum(1 for x in open_items if x.get("changes_rank"))}, out)

    def evaluate(self, products, path, moves):
        p, inp, e = self.load(products, "input.json")
        if e:
            return e
        nodes = [x.strip() for x in (path or "").split(";") if x.strip()]
        if len(nodes) < 2:
            return err("invalid", "path needs at least two nodes 'jur:subject;jur:subject'", path=path)
        try:
            o = self.optimizer(inp)
            with redirect_stdout(io.StringIO()):
                summary = o.evaluate(p, nodes, list(moves or []))
        except BaseException as e:                              # noqa: BLE001
            return err("invalid", "%s: %s" % (type(e).__name__, e), path=path)
        paths = op.jload(p / "paths.json")["candidates"]
        cand = [c for c in paths if c.get("requested")][-1]
        taxes = [t for t in op.jload(p / "tax.json")["taxes"] if t["cand_id"] == cand["cand_id"]]
        deltas = [d for d in op.jload(p / "deltas.json")["deltas"] if d["cand_id"] == cand["cand_id"]]
        return self.stamp({"products": products, "cand": cand, "taxes": taxes, "deltas": deltas, "summary": summary}, p)

    def diff(self, products, against):
        p, e = self.products_dir(products)
        if e:
            return e
        b, e = self.products_dir(against)
        if e:
            return e
        try:
            out = op.diff(p, b)
        except Exception as e:                                  # noqa: BLE001
            return err("internal", "%s: %s" % (type(e).__name__, e))
        out["products"], out["against"] = products, against
        return self.stamp(out, p)

    # ------------------------------------------------------------ readers
    def requirements(self, products, cand_id):
        p, e = self.products_dir(products)
        if e:
            return e
        f = p / "requirements" / ("%s.json" % cand_id)
        if f.exists():
            return self.stamp(op.jload(f), p)
        paths = op.jload(p / "paths.json")["candidates"]
        cand = next((c for c in paths if c["cand_id"] == cand_id), None)
        if cand is None:
            return err("not_found", "no candidate %s" % cand_id, products=products)
        try:
            o = self.optimizer(op.jload(p / "input.json"))
            o.graph = op.jload(p / "graph.json")
            hops = o.candidate_hops(cand, o.graph)
            return self.stamp({"cand_id": cand_id, "requirements": o.requirements(cand, hops)}, p)
        except BaseException as e:                              # noqa: BLE001
            return err("internal", "%s: %s" % (type(e).__name__, e))

    def version_of(self, products):
        if not products:
            return self.stamp({"server": SERVER_VERSION})
        p, v, e = self.load(products, "version.json")
        return e or self.stamp({"products": products, "version_json": v}, p)

    def ranking(self, products):
        p, r, e = self.load(products, "ranking.json")
        return e or self.stamp({"products": products, "key": r.get("key"), "ranking": r["ranking"]}, p)

    def deltas(self, products, cand_id, branch_id):
        p, d, e = self.load(products, "deltas.json")
        if e:
            return e
        rows = [x for x in d["deltas"] if (not cand_id or x.get("cand_id") == cand_id) and (not branch_id or x.get("branch_id") == branch_id)]
        if not cand_id and not branch_id:                       # one short row a branch: the full rows of a large run exceed a tool result
            rows = [{"branch_id": x["branch_id"], "cand_id": x["cand_id"], "vs_as_is": (x.get("vs_as_is") or {}).get("amount"), "vs_best": (x.get("vs_best") or {}).get("amount"),
                     "saving_per_payment": x.get("saving_per_payment"), "payback_payments": x.get("payback_payments")} for x in rows]
            return self.stamp({"products": products, "summary": True, "note": "give cand_id or branch_id for the full rows", "deltas": rows}, p)
        return self.stamp({"products": products, "cand_id": cand_id, "branch_id": branch_id, "deltas": rows}, p)

    def scenarios(self, products, changes_first):
        """scenarios.json; with changes_first only the scenarios whose first structure differs from all favourable."""
        p, d, e = self.load(products, "scenarios.json")
        if e:
            return e
        rows = d.get("scenarios", [])
        if changes_first:
            fav = rows[0]["first"] if rows else None
            rows = [r for r in rows if r["scenario_id"] in ("all_favourable", "all_unfavourable") or r["first"] != fav]
        return self.stamp({"products": products, "points": d.get("points", []), "structure_rank": d.get("structure_rank", {}), "scenarios": rows}, p)

    def open_items(self, products, changes_rank):
        p, d, e = self.load(products, "open_items.json")
        if e:
            return e
        items = d["open_items"] if isinstance(d, dict) else d
        if changes_rank is not None:
            items = [x for x in items if bool(x.get("changes_rank")) == bool(changes_rank)]
        return self.stamp({"products": products, "changes_rank": changes_rank, "score_key": d.get("score_key") if isinstance(d, dict) else None,
                           "open_items": items}, p)

    def paths(self, products, cand_id):
        p, d, e = self.load(products, "paths.json")
        if e:
            return e
        rank = {}
        rf = p / "ranking.json"
        if rf.exists():
            for r in op.jload(rf)["ranking"]:
                rank.setdefault(r["cand_id"], r.get("dominated_by"))
        rows = []
        for c in d["candidates"]:
            if cand_id and c["cand_id"] != cand_id:
                continue
            rows.append({k: c.get(k) for k in ("cand_id", "path", "moves", "restructure", "as_is", "requested", "path_complete", "label")}
                        | {"dominated_by": rank.get(c["cand_id"])})
        if cand_id and not rows:
            return err("not_found", "no candidate %s" % cand_id, products=products)
        return self.stamp({"products": products, "cand_id": cand_id, "candidates": rows}, p)

    def tax(self, products, branch_id):
        p, d, e = self.load(products, "tax.json")
        if e:
            return e
        rows = [t for t in d["taxes"] if not branch_id or t.get("branch_id") == branch_id]
        if branch_id and not rows:
            return err("not_found", "no branch %s" % branch_id, products=products)
        return self.stamp({"products": products, "amount": d.get("amount"), "currency": d.get("currency"), "branch_id": branch_id, "taxes": rows}, p)

    def subfile(self, products, folder, key):
        p, e = self.products_dir(products)
        if e:
            return e
        if not key or "/" in key or "\\" in key or key.startswith("."):
            return err("invalid", "give a plain id", key=key)
        f = p / folder / ("%s.json" % key)
        if not f.exists():
            return err("not_found", "%s has no %s/%s.json" % (products, folder, key), products=products)
        return self.stamp({"products": products, "file": "%s/%s.json" % (folder, key), "data": op.jload(f)}, p)

    def product_check(self, products):
        p, e = self.products_dir(products)
        if e:
            return e
        with redirect_stdout(io.StringIO()):
            fails = chk.Checker(p).run_all()
        return self.stamp({"products": products, "passed": not fails, "failures": fails}, p)

    def fx(self, base, date, jur, role, subject, symbols):
        if not date:
            return err("invalid", "date is required (YYYY-MM-DD)")
        try:
            d = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            return err("invalid", "date must be YYYY-MM-DD", date=date)
        if role not in ("outbound", "inbound") or subject not in ("company", "individual"):
            return err("invalid", "role is outbound|inbound, subject is company|individual")
        syms = [s.strip().upper() for s in (symbols or []) if s.strip()] or fxmod.library_currencies(self.db)
        try:
            res = fxmod.fetch((base or "").upper(), syms, d, (jur or "").lower() or None, role, subject)
        except Exception as e:                                  # noqa: BLE001
            return err("internal", "%s: %s" % (type(e).__name__, e))
        return self.stamp(res)


def build_server(root, rule, db, products_root, role, only=None):
    from mcp.server.mcpserver import MCPServer
    if role not in ("front", "reader"):
        raise SystemExit("--role must be front or reader")
    st = State(root, rule, db, products_root, role)
    s = MCPServer("tax-opt-front" if role == "front" else "tax-opt", version=SERVER_VERSION,
                  instructions="Optimization layer: run / evaluate and sliced reads of a products directory. Paths are relative to the cases root.")
    if only:                                                    # register only these tools (agent/retrieval_spec.en.md §5.3: the readers moved to tax-read)
        register = s.tool

        def tool(*a, **kw):
            dec = register(*a, **kw)
            return lambda fn: dec(fn) if fn.__name__ in only else fn
        s.tool = tool

    if role == "front":
        @s.tool()
        def run(case_id: str, input: str) -> dict:
            """Run the optimizer on a facts file; writes cases/<case_id>/intake/products/<run_id>/ and returns run_id, top ranking rows and the count of rank-changing open items."""
            return st.run(case_id, input)

        @s.tool()
        def diff(products: str, against: str) -> dict:
            """Differences between two products directories (ranks, intervals, open items, inputs); writes <products>/diff.json."""
            return st.diff(products, against)

    @s.tool()
    def validate_input(input: str) -> dict:
        """Construct the optimizer from a facts file without running it; a summary when valid, `invalid` with the reason otherwise."""
        return st.validate_input(input)

    @s.tool()
    def evaluate(products: str, path: str, moves: list[str] | None = None) -> dict:
        """Evaluate one requested path 'jur:subject;jur:subject;...' inside an existing products directory; adds an x-<n> candidate (never ranked)."""
        return st.evaluate(products, path, moves)

    @s.tool()
    def requirements(products: str, cand_id: str) -> dict:
        """Requirements of one candidate (rule-layer requirements and reference_params per hop)."""
        return st.requirements(products, cand_id)

    @s.tool()
    def version(products: str = "") -> dict:
        """Layer version (rule, database, server); with `products`, that directory's version.json."""
        return st.version_of(products)

    @s.tool()
    def fx(base: str, date: str = "", jur: str = "", role: str = "outbound", subject: str = "company", symbols: list[str] | None = None) -> dict:
        """Exchange rates for a payment day and the prescribed rate rule of a jurisdiction (network); writes nothing."""
        return st.fx(base, date, jur, role, subject, symbols)

    @s.tool()
    def ranking(products: str) -> dict:
        """ranking.json of a products directory."""
        return st.ranking(products)

    @s.tool()
    def deltas(products: str, cand_id: str = "", branch_id: str = "") -> dict:
        """deltas.json entries, filtered by candidate and/or branch."""
        return st.deltas(products, cand_id, branch_id)

    @s.tool()
    def scenarios(products: str, changes_first: bool = False) -> dict:
        """scenarios.json: every structure under the same judgment answers (all favourable, one point against, all against), the first and second of each; changes_first keeps only the scenarios whose first structure differs."""
        return st.scenarios(products, changes_first)

    @s.tool()
    def open_items(products: str, changes_rank: bool | None = None) -> dict:
        """open_items.json, optionally only the items that do / do not change the ranking."""
        return st.open_items(products, changes_rank)

    @s.tool()
    def paths(products: str, cand_id: str = "") -> dict:
        """Candidates' path, moves, restructure kinds and dominated_by (one candidate or all)."""
        return st.paths(products, cand_id)

    @s.tool()
    def tax(products: str, branch_id: str = "") -> dict:
        """tax.json entries (per-hop tax components, floor / ceiling), one branch or all."""
        return st.tax(products, branch_id)

    @s.tool()
    def transfers(products: str, cand_id: str) -> dict:
        """transfers/<cand_id>.json."""
        return st.subfile(products, "transfers", cand_id)

    @s.tool()
    def hops(products: str, cand_id: str) -> dict:
        """hops/<cand_id>.json (or hops/<branch_id>.json)."""
        return st.subfile(products, "hops", cand_id)

    @s.tool()
    def penalty(products: str, jur: str) -> dict:
        """penalty/<jur>.json."""
        return st.subfile(products, "penalty", jur)

    @s.tool()
    def product_check(products: str) -> dict:
        """The product checks of check.py --products: passed flag and the list of failures."""
        return st.product_check(products)

    return s, st


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=str(HERE.parent))
    ap.add_argument("--rule", default=str(op.RULE))
    ap.add_argument("--db", default=str(op.DB))
    ap.add_argument("--products-root", default=str(HERE.parents[1] / "cases"))
    ap.add_argument("--role", default="reader", choices=("front", "reader"))
    ap.add_argument("--only", default="", help="comma-separated tool names to register (default: all)")
    a = ap.parse_args()
    server, _ = build_server(a.root, a.rule, a.db, a.products_root, a.role, [x for x in a.only.split(",") if x] or None)
    server.run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
