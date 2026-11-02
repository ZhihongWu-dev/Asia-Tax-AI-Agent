#!/usr/bin/env python
"""tax-rule: read-only MCP server over the rule layer (rule/规则层MCP规范.md).

  python rule/tools/mcp_server.py --root rule --db database --cases cases

Exposes query.py, eval.py, trace.py and rule_tool.py under their own names; facts / answers / set / answer_set are JSON
objects instead of the CLI's "k=v;k=v" strings. The server converts arguments and stamps every answer with `version`;
it adds no semantics, writes nothing and keeps no log. Errors come back as {"error": kind, "detail": text}.
Python 3.11; depends on the `mcp` package (2.x: mcp.server.mcpserver.MCPServer) and the layer's own modules.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import eval as ev  # noqa: E402
from query import Query, cells_for_flow as _cells_for_flow  # noqa: E402
from trace import Tracer  # noqa: E402

SERVER_VERSION = "0.1"
MODES = ("record", "plan")


def err(kind, detail, **extra):
    out = {"error": kind, "detail": detail}
    out.update(extra)
    return out


def kv(obj):
    """A facts / answers object as the CLI's parse_kv would have produced it: str keys, str values, bools as true/false."""
    out = {}
    for k, v in (obj or {}).items():
        if isinstance(v, bool):
            out[str(k)] = "true" if v else "false"
        elif v is None:
            continue
        elif isinstance(v, float) and v.is_integer():
            out[str(k)] = str(int(v))
        else:
            out[str(k)] = str(v).strip()
    return out


RESIDENCE_FACTS = ("incorporated_in", "managed_in", "domicile_in", "days_present", "listed")


def flat_facts(facts):
    """The case's facts.json shape {payer: {jur, facts}, payee: {jur, facts}, payment: {...}} as `payer.x` / `payee.x` / plain names;
    a flat object passes through."""
    out = {}
    for k, v in (facts or {}).items():
        if k in ("payer", "payee") and isinstance(v, dict):
            inner = v.get("facts") if isinstance(v.get("facts"), dict) else {x: y for x, y in v.items() if x not in ("jur", "subject")}
            out.update({"%s.%s" % (k, x): y for x, y in inner.items()})
            # the source cells read the payee's holding and factor facts, the recipient's cells the payer's, as plain names
            out.update({x: y for x, y in inner.items() if (x.startswith("payer_") if k == "payer" else x not in RESIDENCE_FACTS)})
        elif k == "payment" and isinstance(v, dict):
            out.update(v)
        else:
            out[k] = v
    return kv(out)


def cell_facts(rs, slot, date, facts, answers, mode):
    """One cell, plain names only: the entity facts of a nested shape, and the residence of the recipient from its own facts."""
    flat = flat_facts(facts)
    out = {k.split(".", 1)[1]: v for k, v in flat.items() if k.startswith("payer.")}
    out.update({k.split(".", 1)[1]: v for k, v in flat.items() if k.startswith("payee.")})
    out.update({k: v for k, v in flat.items() if "." not in k})
    parts = slot.split("|")
    if len(parts) == 4 and "payee_resident" not in out and parts[2] in ("outbound_wht", "anti_abuse", "inbound", "final"):
        home = parts[3] if parts[2] in ("outbound_wht", "anti_abuse") and parts[3] != "*" else parts[0]
        item = ev.eval_cell(rs, "%s|%s|residence|*" % (home, parts[1] if parts[1] != "all" else "company"), date, out, answers, mode)
        out["payee_resident"] = ev.tri(item, "payee_resident")
    return out


class State:
    def __init__(self, root, db, cases):
        self.root, self.db, self.cases = Path(root), Path(db), Path(cases)
        self.q = Query(self.root, self.db)
        self.rs = self.q.rs                         # RuleSet shared with RuleTool
        self.tool = self.q.tool
        self.tracer = Tracer(self.root, self.db)
        # MCP runs each tool call in a worker thread; Library's lazy sqlite connection is thread-bound, so open it here
        # for every thread (read-only use) before the first call.
        sqlite_path = self.db / "database.sqlite"
        if sqlite_path.exists():
            import sqlite3
            for lib in {id(self.q.lib): self.q.lib, id(self.tracer.lib): self.tracer.lib}.values():
                lib._con = sqlite3.connect(str(sqlite_path), check_same_thread=False)
        v = self.q.version()
        v.pop("generated_at", None)                 # the build is what matters, not the start-up time
        self.version = {"rule": v["rule"], "database": v["database"], "server": SERVER_VERSION}

    def stamp(self, obj):
        if isinstance(obj, dict):
            if "error" in obj:
                return obj
            obj["version"] = self.version
            return obj
        return {"result": obj, "version": self.version}

    def guard(self, fn, *args, **kwargs):
        try:
            return self.stamp(fn(*args, **kwargs))
        except (ValueError, KeyError) as e:
            return err("invalid", "%s: %s" % (type(e).__name__, e))
        except FileNotFoundError as e:
            return err("not_found", str(e))
        except Exception as e:                      # noqa: BLE001 - reported to the agent, never swallowed
            return err("internal", "%s: %s" % (type(e).__name__, e))

    # ------------------------------------------------------------ argument checks
    @staticmethod
    def need_date(date):
        return None if date else err("invalid", "date is required (YYYY-MM-DD); the server gives no default")

    @staticmethod
    def check_mode(mode):
        return None if mode in MODES else err("invalid", "mode must be record or plan, got %r" % mode)

    @staticmethod
    def flow_or_slot(flow, slot):
        if slot:
            return None
        if not flow or any(k not in flow for k in ("payer_jur", "payee_jur", "subject")):
            return err("invalid", "give slot, or flow with payer_jur, payee_jur and subject")
        return None

    @staticmethod
    def flow_list(flow):
        return [flow["payer_jur"], flow["payee_jur"], flow["subject"]] if flow else None

    # ------------------------------------------------------------ trace items
    def load_items(self, items):
        if isinstance(items, str):
            p = (self.cases / items).resolve()
            if not p.is_relative_to(self.cases.resolve()):
                return err("invalid", "items path must stay under the cases root")
            if not p.exists():
                return err("not_found", "no file %s" % items)
            items = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(items, dict) and "items" in items:
            items = items["items"]
        flat, stack = [], list(items if isinstance(items, list) else [items])
        while stack:
            x = stack.pop(0)
            (stack.extend(x) if isinstance(x, list) else flat.append(x))
        if not flat or not all(isinstance(x, dict) and "slot_key" in x for x in flat):
            return err("invalid", "items must be eval items (objects with slot_key) or a path to a file of them")
        return flat


def build_server(root, db, cases):
    from mcp.server.mcpserver import MCPServer
    st = State(root, db, cases)
    s = MCPServer("tax-rule", version=SERVER_VERSION,
                  instructions="Read-only queries and evaluations of the rule layer (rule/). Dates are required; nothing is assumed.")

    @s.tool()
    def variables() -> dict:
        """Field dictionary: every variable with type, value_kind, question and meaning."""
        return st.guard(lambda: {"variables": st.q.variables()})

    @s.tool()
    def predicates() -> dict:
        """Predicate table: question, factor variables, factor clauses, cells that depend on each."""
        return st.guard(lambda: {"predicates": st.q.predicates()})

    @s.tool()
    def version() -> dict:
        """Rule-layer build version: counts of rules / variables / predicates / decisions / tests and csv hashes."""
        return st.stamp({})

    @s.tool()
    def cells_for_flow(payer_jur: str, payee_jur: str, subject: str) -> dict:
        """slot_keys of the cells a dividend flow passes through."""
        return st.guard(lambda: {"cells": _cells_for_flow(payer_jur, payee_jur, subject)})

    @s.tool()
    def judgment_points(date: str, flow: dict | None = None, slot: str = "", facts: dict | None = None,
                        answers: dict | None = None, mode: str = "record") -> dict:
        """Predicates the evaluation is stuck on: question, factor variables, blocked rules, outcome if answered yes / no."""
        for e in (st.need_date(date), st.check_mode(mode), st.flow_or_slot(flow, slot)):
            if e:
                return e
        return st.guard(lambda: {"judgment_points": st.q.judgment_points(st.flow_list(flow), slot or None, date, kv(facts), kv(answers), mode)})

    @s.tool()
    def requirements(slot: str = "", rule: str = "", effect: str = "", date: str = "") -> dict:
        """Conditions, procedure, cite_ids and reference parameters of a cell's rules (or of one rule)."""
        if not (slot or rule):
            return err("invalid", "give slot or rule")
        if slot and not date:
            return st.need_date(date)
        return st.guard(st.q.requirements, slot or None, effect or None, rule or None, date or None)

    @s.tool()
    def options(payer_jur: str, payee_jur: str, subject: str, date: str) -> dict:
        """Favourable treatments available along a flow and the conditions of each."""
        e = st.need_date(date)
        if e:
            return e
        return st.guard(lambda: {"options": st.q.options(payer_jur, payee_jur, subject, date)})

    @s.tool()
    def what_if(date: str, flow: dict | None = None, slot: str = "", facts: dict | None = None, answers: dict | None = None,
                set: dict | None = None, answer_set: dict | None = None, mode: str = "record") -> dict:
        """Before / after comparison when some facts or answers change."""
        for e in (st.need_date(date), st.check_mode(mode), st.flow_or_slot(flow, slot)):
            if e:
                return e
        return st.guard(st.q.what_if, st.flow_list(flow), slot or None, date, kv(facts), kv(answers), mode, kv(set), kv(answer_set))

    @s.tool()
    def gap(payer_jur: str, payee_jur: str, subject: str) -> dict:
        """Cells of a flow with no rules or missing effects, and treaty texts the library lacks."""
        return st.guard(st.q.gap, payer_jur, payee_jur, subject)

    @s.tool()
    def eval_cell(slot: str, date: str, facts: dict | None = None, answers: dict | None = None, mode: str = "record",
                  assume: list[str] | None = None) -> dict:
        """Three-valued evaluation of one cell: status, floor / ceiling, value_kind, rules applied, pending needs."""
        for e in (st.need_date(date), st.check_mode(mode)):
            if e:
                return e
        return st.guard(lambda: {"items": [ev.eval_cell(st.rs, slot, date, cell_facts(st.rs, slot, date, facts, kv(answers), mode), kv(answers), mode, assume=list(assume or []))]})

    @s.tool()
    def eval_flow(payer_jur: str, payee_jur: str, subject: str, date: str, facts: dict | None = None, answers: dict | None = None,
                  mode: str = "record", assume: list[str] | None = None) -> dict:
        """Three-valued evaluation of every cell of a dividend flow."""
        for e in (st.need_date(date), st.check_mode(mode)):
            if e:
                return e
        return st.guard(lambda: {"items": ev.eval_flow(st.rs, payer_jur, payee_jur, subject, date, flat_facts(facts), kv(answers), mode, assume=list(assume or []))})

    @s.tool()
    def eval_transfer(target_jur: str, home_jur: str, subject: str, date: str, facts: dict | None = None, answers: dict | None = None,
                      mode: str = "record", assume: list[str] | None = None) -> dict:
        """Three-valued evaluation of a share transfer: the company transferred is in target_jur, the transferor in home_jur."""
        for e in (st.need_date(date), st.check_mode(mode)):
            if e:
                return e
        return st.guard(lambda: {"items": ev.eval_transfer(st.rs, target_jur, home_jur, subject, date, kv(facts), kv(answers), mode, assume=list(assume or []))})

    @s.tool()
    def trace(items: list | str | None = None, flow: dict | None = None, slot: str = "", date: str = "",
              facts: dict | None = None, answers: dict | None = None, mode: str = "record") -> dict:
        """Per-rule trace of eval items (given, or read from a hops / transfers file under cases/, or evaluated here from flow / slot + date)."""
        if items is not None:
            loaded = st.load_items(items)
            if isinstance(loaded, dict):
                return loaded
        else:
            for e in (st.need_date(date), st.check_mode(mode), st.flow_or_slot(flow, slot)):
                if e:
                    return e
            try:
                loaded = st.q._run(st.flow_list(flow), slot or None, date, kv(facts), kv(answers), mode)
            except Exception as e:                  # noqa: BLE001
                return err("invalid", "%s: %s" % (type(e).__name__, e))
        return st.guard(lambda: {"traces": [st.tracer.trace_item(it) for it in loaded]})

    @s.tool()
    def rule_tool(slot: str = "", rule: str = "", variable: str = "", predicate: str = "", date: str = "", brief: bool = False) -> dict:
        """Rule rows with their clauses, parameters, decisions and procedure; reference_params for a slot; variable / predicate rows."""
        if not (slot or rule or variable or predicate):
            return err("invalid", "give slot, rule, variable or predicate")

        def run():
            rows = st.tool.rule_rows(slot or None, date or None, rule or None, variable or None, predicate or None)
            out = {"found": len(rows), "rules": [st.tool.expand(r, brief) for r in rows]}
            if slot:
                out["reference_params"] = st.tool.reference_params(slot)
            if variable:
                out["variable"] = st.tool.variable_row(variable)
            if predicate:
                out["predicate"] = st.tool.predicate_row(predicate)
            return out
        return st.guard(run)

    return s, st


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=str(HERE.parent), help="rule folder (default: rule/)")
    ap.add_argument("--db", default=str(HERE.parent.parent / "database"), help="library folder (default: database/)")
    ap.add_argument("--cases", default=str(HERE.parent.parent / "cases"), help="root that trace item paths are relative to")
    a = ap.parse_args()
    server, _ = build_server(a.root, a.db, a.cases)
    server.run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
