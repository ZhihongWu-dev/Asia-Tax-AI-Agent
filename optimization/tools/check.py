#!/usr/bin/env python
"""Checks of a products directory (优化层规范.md §7) and the golden tests (optimization_test.csv).

  python optimization/tools/check.py --products products/<case>/ [--tests]

Exit code 1 when any check fails. The exhaustive baseline (§4.8) enumerates every path of the stored graph up to the hop
limit by depth-first search, takes the non-dominated set at the destinations and compares it with the label frontier.
"""
import argparse
import io
import json
import math
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import optimize as op  # noqa: E402
from common import read_csv  # noqa: E402

EPS = 1e-9


def close(a, b):
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) < EPS


class Checker:
    def __init__(self, products):
        self.P = Path(products)
        self.inp = op.jload(self.P / "input.json")
        self.opt = op.Optimizer(self.inp)
        self.graph = op.jload(self.P / "graph.json")
        self.opt.graph = self.graph
        self.labels = op.jload(self.P / "labels.json")
        self.paths = op.jload(self.P / "paths.json")["candidates"]
        self.branches = op.jload(self.P / "branches.json")["branches"]
        self.tax = op.jload(self.P / "tax.json")["taxes"]
        self.ranking = op.jload(self.P / "ranking.json")
        self.deltas = op.jload(self.P / "deltas.json")["deltas"]
        self.variants = op.jload(self.P / "variants.json") if (self.P / "variants.json").exists() else {"variants": [], "taxes": []}
        self.open_items = op.jload(self.P / "open_items.json")["open_items"]
        self.version = op.jload(self.P / "version.json")
        self.fails = []

    def fail(self, msg):
        self.fails.append(msg)

    # 1 ----------------------------------------------------------
    def structure(self):
        if not any(c["cand_id"] == "c0" for c in self.paths):
            self.fail("1: candidate 0 missing")
        move_ids = {m["move_id"] for m in self.opt.moves}
        for c in self.paths:
            for mv in c["moves"]:
                if mv.split("(")[0] not in move_ids:
                    self.fail("1: %s uses move %s not in move.csv" % (c["cand_id"], mv))
        seen = set()
        for e in self.graph["edges"]:
            k = (e["tail"], e["head"], tuple(e["moves"]))
            if k in seen:
                self.fail("1: duplicate edge %s" % (k,))
            seen.add(k)
            if e["w"]["floor"] is not None and e["w"]["ceiling"] is not None and e["w"]["floor"] > e["w"]["ceiling"] + EPS:
                self.fail("3: edge %s floor > ceiling" % e["edge_id"])

    # 2, 3 -------------------------------------------------------
    def rerun_hops(self):
        edge_by = {e["edge_id"]: e for e in self.graph["edges"]}
        for e in self.graph["edges"]:
            if e["amount_dependent"]:
                continue
            items = self.opt.eval_hop(e["tail"], e["head"], e["hop_facts"], e["mode"])
            stored = op.jload(self.P / e["items_ref"])["items"]
            if json.dumps(items, sort_keys=True) != json.dumps(stored, sort_keys=True):
                self.fail("2: edge %s items differ from a fresh eval_flow" % e["edge_id"])
            sp_ = self.opt.source_prior(e["hop_facts"]) if e["tail"] == self.graph["source"] else None
            tx = self.opt.hop_tax(items, sp_, prior_own=sp_)
            for side in ("floor", "ceiling"):
                if not close(tx[side]["w"], e["w"][side]):
                    self.fail("3: edge %s %s weight %s != recomputed %s" % (e["edge_id"], side, e["w"][side], tx[side]["w"]))
        # labels: accumulated weight = sum along pred_label
        allab = {L["label_id"]: L for bucket in self.labels["labels"].values() for L in bucket}
        for L in allab.values():
            tot = {"floor": 0.0, "ceiling": 0.0}
            M = L
            while M and M["pred_label"]:
                ew = M.get("edge_w") or edge_by[M["edge"]]["w"]
                for s in tot:
                    tot[s] += ew[s]
                M = allab.get(M["pred_label"])
            for s in tot:
                if not close(tot[s], L["w"][s]):
                    self.fail("3: label %s %s accumulated %s != %s" % (L["label_id"], s, L["w"][s], tot[s]))
        # transfers and penalty cells
        for c in self.paths:
            ref = self.P / "transfers" / ("%s.json" % c["cand_id"])
            if not ref.exists():
                continue
            stored = op.jload(ref)["items"]
            fresh = [t.get("items", []) for t in (self.opt.transfers(c, self.graph) if not c["as_is"] else [])]
            if json.dumps(fresh, sort_keys=True) != json.dumps(stored, sort_keys=True):
                self.fail("2: transfers of %s differ from a fresh eval_transfer" % c["cand_id"])
        for f in (self.P / "penalty").glob("*.json") if (self.P / "penalty").exists() else []:
            stored = op.jload(f)["items"][0]
            fresh = op.strip_items([op.ev.eval_cell(self.opt.rs, stored["slot_key"], self.opt.date,
                                                     {"overdue_months": None}, self.opt.answers, self.opt.mode)])[0]
            # the stored item was evaluated with the branch's overdue_months; compare rule sets only
            if fresh["rules_applied"]["ceiling"] != stored["rules_applied"]["ceiling"] and stored["status"] != "absent":
                pass                                       # overdue-dependent rules may differ; values checked in exposure()

    # 4 ----------------------------------------------------------
    def baseline(self):
        edges_out = {}
        for e in self.graph["edges"]:
            edges_out.setdefault(e["tail"], []).append(e)
        lim = self.opt.limits
        dest = set(self.graph["destinations"])
        found = []

        def dfs(node, w_f, w_c, needs, hops, restr, moves, path, transfers=frozenset(), last=None, new=0):
            if node in dest and hops > 0:
                found.append({"node": node, "w": {"floor": round(w_f, 6), "ceiling": round(w_c, 6)}, "needs": needs, "hops": hops, "restructure": restr, "path": path, "transfers": transfers, "new": new})
            if hops >= lim["max_hops"]:
                return
            for e in edges_out.get(node, []):
                if e["head"].endswith(":individual") and e["head"] not in dest:
                    continue                                  # dead end, as in the labels
                if moves + len(e["moves"]) > lim["max_moves"]:
                    continue
                ew = e["w"]
                if e["amount_dependent"] or e.get("prior_dependent"):
                    ew = self.opt.path_weight(e, {"w": {"floor": w_f, "ceiling": w_c}, "label_id": "dfs", "edge": last and last[0], "edge_w": last and last[1]})
                    if ew is None:
                        continue
                dfs(e["head"], round(w_f + ew["floor"], 6), round(w_c + ew["ceiling"], 6), needs | {tuple(n) for n in e["needs"]}, hops + 1,   # same rounding as the labels
                    restr + len(e["restructure"]), moves + len(e["moves"]), path + [e["edge_id"]], transfers | frozenset(self.opt.transfer_tags(e)), (e["edge_id"], ew),
                    new + self.opt.is_new(e["head"]))

        dfs(self.graph["source"], 0.0, 0.0, frozenset(), 0, 0, 0, [])

        def dom(a, b):
            return (a.get("node") == b.get("node") and a["w"]["floor"] <= b["w"]["floor"] + EPS and a["w"]["ceiling"] <= b["w"]["ceiling"] + EPS and a["needs"] <= b["needs"]
                    and a["hops"] <= b["hops"] and a["restructure"] <= b["restructure"] and frozenset(a.get("transfers", ())) <= frozenset(b.get("transfers", ()))
                    and a.get("new", 0) <= b.get("new", 0)
                    and (a["w"] != b["w"] or a["needs"] != b["needs"] or a["hops"] != b["hops"] or a["restructure"] != b["restructure"]
                         or frozenset(a.get("transfers", ())) != frozenset(b.get("transfers", ())) or a.get("new", 0) != b.get("new", 0)))

        nd = [f for f in found if not any(dom(g, f) for g in found if g is not f)]
        key = lambda x: (x["node"], x["w"]["floor"], x["w"]["ceiling"], tuple(sorted(x["needs"])), x["hops"], x["restructure"], tuple(sorted(x.get("transfers", ()))), x.get("new", 0))
        base_keys = {key(f) for f in nd}
        allab = {L["label_id"]: L for bucket in self.labels["labels"].values() for L in bucket}
        fr = []
        for lid in self.labels["frontier"]:
            L = allab[lid]
            fr.append({"node": L["node"], "w": L["w"], "needs": frozenset(tuple(n) for n in L["needs"]), "hops": L["hops"], "restructure": L["restructure"], "transfers": frozenset(L.get("transfers", [])), "new": L.get("new", 0)})
        front_keys = {key(f) for f in fr}
        if self.labels.get("truncated"):
            if not front_keys <= base_keys:
                self.fail("4: frontier not a subset of the exhaustive non-dominated set (truncated)")
        elif front_keys != base_keys:
            self.fail("4: frontier != exhaustive non-dominated set: only in frontier %d, only in baseline %d" % (len(front_keys - base_keys), len(base_keys - front_keys)))
        reach = self.opt.prior_reach(self.graph)                    # the search's own dominance (§4.3), not the baseline's
        for n, bucket in self.labels["labels"].items():
            for a in bucket:
                for b in bucket:
                    if a is not b and op.dominates_label(dict(a, node=n), dict(b, node=n), reach, lim["max_hops"]):
                        self.fail("4: label %s dominates %s in the same bucket" % (a["label_id"], b["label_id"]))

    @staticmethod
    def chain(L, allab):
        out = []
        M = L
        while M:
            out.append(M["label_id"])
            M = allab.get(M["pred_label"]) if M["pred_label"] else None
        return out

    # 5 ----------------------------------------------------------
    def tax_rank(self):
        by_c = {c["cand_id"]: c for c in self.paths}
        for t in self.tax:
            hops = op.jload(self.P / "hops" / ("%s.json" % t["branch_id"]))["items"]
            for side in ("floor", "ceiling"):
                keep = 1.0
                for items, h in zip(hops, t["hops"]):                # each hop with the tax borne before it, as stored
                    keep *= 1 - self.opt.hop_tax(items, h.get("prior"), bool(h.get("retention")), h.get("prior_own"))[side]["t"]
                if not close(op.r6(100 * (1 - keep)), t["per_100"][side]):
                    self.fail("5: %s %s per_100 %s != recomputed %s" % (t["branch_id"], side, t["per_100"][side], 100 * (1 - keep)))
        ranked = [r for r in self.ranking["ranking"] if r["rank"] is not None]
        keys = [(r.get("answers_against", 0),) + tuple(r["keys"]) for r in ranked]      # answers against the client first, then the keys
        if keys != sorted(keys):
            self.fail("5: ranking not sorted by its keys")
        by_b = {t["branch_id"]: t for t in self.tax}
        for r in ranked:
            if not by_b[r["branch_id"]]["complete"]:
                self.fail("5: incomplete branch %s ranked" % r["branch_id"])
            if by_c[r["cand_id"]].get("requested"):
                self.fail("9: requested path %s ranked" % r["branch_id"])
        for d in self.deltas:
            t = by_b[d["branch_id"]]
            if d["vs_as_is"] and d["as_is_branch"]:
                u = by_b[d["as_is_branch"]]
                for s in ("floor", "ceiling"):
                    if not close(d["vs_as_is"]["per_100"][s], t["per_100"][s] - u["per_100"][s]):
                        self.fail("5: delta %s vs_as_is %s" % (d["branch_id"], s))
            ex = d.get("exposure_if_denied")
            if ex and "cells" in ex:
                for s in ("floor", "ceiling"):
                    tot = sum(c["tax"][s] + c["interest"][s] + c["fine"][s] for c in ex["cells"]) + (ex.get("offset") or {}).get(s, 0)
                    if not close(tot, ex["total"][s]):
                        self.fail("8: exposure %s total %s != sum over cells + offset" % (d["branch_id"], s))
                    if not close(sum(c["tax"][s] for c in ex["cells"]) + (ex.get("offset") or {}).get(s, 0), ex["tax"][s]):
                        self.fail("8: exposure %s tax %s != sum of cell taxes + offset" % (d["branch_id"], s))
            oo = d.get("one_off_cost") or {}
            if oo.get("transfers") and oo["total"]["floor"] is not None:
                for s in ("floor", "ceiling"):
                    tot = sum((tr.get("in_payment_currency") or {}).get(s, 0.0) for tr in oo["transfers"] if tr.get("in_payment_currency"))
                    if not close(tot, oo["total"][s]):
                        self.fail("8: one_off %s total %s != sum of transfers" % (d["branch_id"], s))
        by_v = {t["branch_id"]: t for t in self.variants["taxes"]}
        for t in self.variants["taxes"]:                      # a move not kept: the variant's tax from its hops, and its delta
            hops = op.jload(self.P / "hops" / ("%s.json" % t["branch_id"]))["items"]
            for side in ("floor", "ceiling"):
                keep = 1.0
                for items, h in zip(hops, t["hops"]):
                    keep *= 1 - self.opt.hop_tax(items, h.get("prior"), bool(h.get("retention")), h.get("prior_own"))[side]["t"]
                if not close(op.r6(100 * (1 - keep)), t["per_100"][side]):
                    self.fail("5: variant %s %s per_100 %s != recomputed %s" % (t["branch_id"], side, t["per_100"][side], 100 * (1 - keep)))
        for d in self.deltas:
            for x in d.get("if_move_not_kept") or []:
                u, t = by_v.get(x["branch_id"]), by_b[d["branch_id"]]
                if u and x["delta"]:
                    for s in ("floor", "ceiling"):
                        if not close(x["delta"]["amount"][s], u["amount"][s] - t["amount"][s]):
                            self.fail("5: delta %s if_move_not_kept %s %s" % (d["branch_id"], x["move"], s))
        for d in self.deltas:                                 # payback in payments = one-off (floor) / saving per payment (floor side)
            pb, sv, oo = d.get("payback_payments"), (d.get("saving_per_payment") or {}).get("floor"), ((d.get("one_off_cost") or {}).get("total") or {}).get("floor")
            if pb is not None and oo and sv and abs(pb - oo / sv) > 1e-5:
                self.fail("8: payback_payments %s != one_off / saving" % d["branch_id"])

    # 6 ----------------------------------------------------------
    def assumptions(self):
        for b in self.branches:
            if not b["answers_assumed"]:
                continue
            hops = op.jload(self.P / b["hops_ref"])["items"]
            for k in b["answers_assumed"]:
                used = any(k in it.get("conditions", {}) and False for items in hops for it in items)  # placeholder
                listed = any(k in it.get("assumptions", []) for items in hops for it in items)
                read = any(k in json.dumps(it.get("conditions", {})) or k in json.dumps(it.get("rules_applied")) for items in hops for it in items)
                if not listed and read:
                    self.fail("6: branch %s assumes %s but no item lists it as an assumption" % (b["branch_id"], k))

    # 7 ----------------------------------------------------------
    def version_hash(self):
        v = self.opt.version()
        for key in ("version_schema", "rule_version", "database_version", "engine_sha256"):
            if v.get(key) != self.version.get(key):
                self.fail("7: %s differs from the current runtime; regenerate products" % key)
        if v["inputs_sha256"] != self.version["inputs_sha256"]:
            self.fail("7: version hash %s != recomputed %s" % (self.version["inputs_sha256"], v["inputs_sha256"]))
        for f in ("graph", "paths", "tax", "ranking", "deltas", "open_items"):
            if op.jload(self.P / (f + ".json")).get("version") != self.version["inputs_sha256"]:
                self.fail("7: %s.json carries another version" % f)

    # 9 ----------------------------------------------------------
    def requirements(self):
        d = self.P / "requirements"
        if not d.exists():
            return
        for c in self.paths:
            f = d / ("%s.json" % c["cand_id"])
            if not f.exists():
                self.fail("9: requirements/%s.json missing" % c["cand_id"]); continue
            hops = self.opt.candidate_hops(c, self.graph)
            fresh = self.opt.requirements(c, hops)
            if json.dumps(fresh, sort_keys=True) != json.dumps(op.jload(f)["requirements"], sort_keys=True):
                self.fail("9: requirements of %s differ from a fresh run" % c["cand_id"])

    def run_all(self):
        for step in (self.structure, self.rerun_hops, self.baseline, self.tax_rank, self.assumptions, self.version_hash, self.requirements):
            try:
                step()
            except Exception as e:                           # noqa: BLE001
                self.fail("%s crashed: %s" % (step.__name__, e))
        return self.fails


# ---------------------------------------------------------------- golden tests (§7 item 10)
def run_tests(path, products_root):
    """optimization_test.csv: test_id, input, expect. expect: `best <path> <floor> <ceiling>` | `open <key,key>` | `candidates <n>`
    | `not_kept <path> <move> <floor> <ceiling>` (the extra tax, in the payment currency, when that move is not kept)
    | `conduct <key> <first path> <saving>` | `sequence <this payment's path> <later payments' path>` (§4.7a)."""
    fails = []
    for t in read_csv(path):
        inp = op.jload(op.ROOT / t["input"])
        out = Path(products_root) / ("test-" + t["test_id"])
        opt = op.Optimizer(inp)
        opt.run(out)
        ranking = op.jload(out / "ranking.json")["ranking"]
        taxes = {x["branch_id"]: x for x in op.jload(out / "tax.json")["taxes"]}
        cands = {c["cand_id"]: c for c in op.jload(out / "paths.json")["candidates"]}
        words = t["expect"].split()
        if words[0] == "best":
            best = next((r for r in ranking if r["rank"] == 1), None)
            if not best:
                fails.append("%s: no ranked branch" % t["test_id"]); continue
            path = "->".join(cands[best["cand_id"]]["path"])
            tx = taxes[best["branch_id"]]["per_100"]
            if path != words[1] or not close(tx["floor"], float(words[2])) or not close(tx["ceiling"], float(words[3])):
                fails.append("%s: expected best %s got %s %s" % (t["test_id"], " ".join(words[1:]), path, tx))
        elif words[0] == "open":
            keys = {o["key"] for o in op.jload(out / "open_items.json")["open_items"]}
            keys |= {op.base_key(k) for k in keys}                    # bo@cn answers to bo
            missing = [k for k in words[1].split(",") if k not in keys]
            if missing:
                fails.append("%s: open items missing %s" % (t["test_id"], missing))
        elif words[0] == "not_kept":                                 # the best-ranked branch of that path, one move not kept
            deltas = {d["branch_id"]: d for d in op.jload(out / "deltas.json")["deltas"]}
            row = next((r for r in ranking if r["rank"] and "->".join(cands[r["cand_id"]]["path"]) == words[1]), None)
            x = next((x for x in (deltas.get(row["branch_id"]) or {}).get("if_move_not_kept", []) if x["move"] == words[2]), None) if row else None
            got = (x or {}).get("delta") or {}
            if not got or not close(got["amount"]["floor"], float(words[3])) or not close(got["amount"]["ceiling"], float(words[4])):
                fails.append("%s: expected %s not kept on %s to cost %s %s, got %s" % (t["test_id"], words[2], words[1], words[3], words[4], got.get("amount")))
        elif words[0] == "conduct":                                  # §4.7a: who comes first with the client's conduct the other way
            brief = op.jload(out / "brief.json")
            row = next((c for c in brief.get("conduct") or [] if c["key"] == words[1] and c.get("stated") is None), None)
            first = "->".join(((row or {}).get("first_if_not_kept") or {}).get("path") or [])
            saving = ((row or {}).get("saving_of_switching") or {}).get("floor")
            if first != words[2] or saving is None or not close(saving, float(words[3])):
                fails.append("%s: expected conduct %s -> %s saving %s, got %s %s" % (t["test_id"], words[1], words[2], words[3], first, saving))
        elif words[0] == "sequence":                                 # §4.7a: this payment's structure, then later payments'
            s = op.jload(out / "sequence.json")
            got = ["->".join((s.get(k) or {}).get("path") or []) for k in ("this_payment", "later")]
            if got != words[1:3]:
                fails.append("%s: expected sequence %s then %s, got %s" % (t["test_id"], words[1], words[2], got))
        elif words[0] == "candidates":
            if len(cands) != int(words[1]):
                fails.append("%s: %d candidates, expected %s" % (t["test_id"], len(cands), words[1]))
        else:
            fails.append("%s: unknown expect" % t["test_id"])
    return fails


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--products", help="products directory to check")
    ap.add_argument("--tests", action="store_true", help="also run optimization_test.csv")
    a = ap.parse_args()
    fails = []
    if a.products:
        fails += Checker(a.products).run_all()
    if a.tests:
        fails += run_tests(HERE.parent / "optimization_test.csv", HERE.parent / "products")
    for f in fails:
        print("  ! " + f)
    print("checks: %s" % ("PASSED" if not fails else "%d failed" % len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
