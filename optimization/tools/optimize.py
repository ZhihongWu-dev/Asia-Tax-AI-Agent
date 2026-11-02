#!/usr/bin/env python
"""Optimization layer (优化层规范.md): a read-only shovel that turns one dividend background into products on disk.

  python optimization/tools/optimize.py run --input <case.json> --out products/<case>/
  python optimization/tools/optimize.py evaluate --products products/<case>/ --path 'cn:company;jp:company;sg:individual' [--moves holding_pct=100]
  python optimization/tools/optimize.py requirements --products products/<case>/
  python optimization/tools/optimize.py diff --products products/<case>/ --against products/<case>-v1/
  python optimization/tools/optimize.py version

The input file (JSON) holds everything §3 lists: facts (payment, payer, payee), answers, assume, destinations, date,
mode, amount, currency, limits, constraints, as_of, fx (path or object), valuation, horizon_years, entities (known
existing group entities). Nothing is read from anywhere else; the rule layer is called through rule/tools/eval.py,
query.py and rule_tool.py. Same input → same products (version.json carries the hashes).

Python 3.11, standard library only.
"""
import argparse
import calendar
import copy
import hashlib
import heapq
import io
import json
import math
import sys
from datetime import date as _date, datetime, timedelta
from pathlib import Path

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]                                   # project root
RULE = ROOT / "rule"
DB = ROOT / "database"
sys.path.insert(0, str(RULE / "tools"))
import eval as ev  # noqa: E402
from common import read_csv, split_list  # noqa: E402
from query import Query, cells_for_flow  # noqa: E402
from common import leaves as _leaves  # noqa: E402


def leaves_vars(rule):
    return set(_leaves(rule["tree"], "var"))

SIX = ("outbound_wht", "inbound", "final", "residence", "cfc", "anti_abuse")
FAV_EFFECTS = ("cap", "exempt", "share", "exclude", "credit")
DEFAULT_LIMITS = {"max_hops": 3, "max_moves": 3, "max_labels": 50, "max_fork_keys": 3}
FORK_ROUNDS = 3
JUR_FACTS = ("incorporated_in", "managed_in", "domicile_in", "parent_jur", "payer_jur")
BRIEF_ROWS = 8
EPS = 1e-9


# ---------------------------------------------------------------- helpers
def jdump(obj, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def jload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def r6(x):
    return None if x is None else round(float(x) + 0.0, 6)


def node_id(jur, subject):
    return "%s:%s" % (jur, subject)


def split_node(nid):
    j, s = nid.split(":")
    return j, s


def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def months_between(a, b):
    """Whole months from date a to date b (0 when b <= a)."""
    if b <= a:
        return 0
    m = (b.year - a.year) * 12 + (b.month - a.month)
    if b.day < a.day:
        m -= 1
    return max(0, m)


def strip_items(items):
    """Items as the rule layer returns them, JSON-safe (tuples in needs become lists)."""
    return json.loads(json.dumps(items, ensure_ascii=False, default=list))


# ---------------------------------------------------------------- moves (move.csv)
def load_moves(path):
    rows = read_csv(path)
    out = []
    for r in rows:
        dom = r.get("arg_domain") or ""
        args = [None]
        if dom and dom not in ("jur",):
            kind, _, vals = dom.partition(":")
            if kind == "bool":
                args = ["true", "false"]
            elif vals:
                args = vals.split(";")
            else:
                args = [None]
        out.append({"move_id": r["move_id"], "kind": r["kind"], "sets": split_list(r.get("sets")), "arg_domain": dom,
                    "args": args, "precondition": r.get("precondition") or "", "restructure": r.get("restructure") or "no",
                    "note": r.get("note") or ""})
    return out


def move_sets(move, arg):
    out = {}
    for kv in move["sets"]:
        k, _, v = kv.partition("=")
        v = v.strip()
        out[k.strip()] = (arg if v == "<arg>" else v)
    return out


# ---------------------------------------------------------------- the optimizer
class Optimizer:
    def __init__(self, inp, root=RULE, db=DB):
        self.inp = inp
        self.q = Query(root, db)
        self.rs, self.lib, self.tool = self.q.rs, self.q.lib, self.q.tool
        self.date = inp["date"]
        self.mode = inp.get("mode", "record")
        self.amount = float(inp.get("amount") or 100.0)
        self.currency = inp.get("currency") or ""
        self.answers = {k: (v["answer"] if isinstance(v, dict) else v) for k, v in (inp.get("answers") or {}).items()}
        self.assume = list(inp.get("assume") or [])
        self.limits = dict(DEFAULT_LIMITS, **(inp.get("limits") or {}))
        self.constraints = dict({"exclude": [], "allow_restructure": True, "payback_max": None, "allowed_subjects": None},
                                **(inp.get("constraints") or {}))
        self.payer = inp["payer"]
        self.payee = inp["payee"]
        self.payment = dict(inp.get("payment") or {})
        for k, v in (self.payer.get("facts") or {}).items():         # facts of the payment may also sit on the two entities
            if k.startswith("payer_"):
                self.payment.setdefault(k, v)
        for k in ("holding_pct", "holding_months"):
            if k in (self.payee.get("facts") or {}):
                self.payment.setdefault(k, self.payee["facts"][k])
        self.entities = dict(inp.get("entities") or {})
        self.valuation = inp.get("valuation") or {}
        self.horizon = inp.get("horizon_years")
        self.as_of = inp.get("as_of") or self.date
        fx = inp.get("fx")
        self.fx = jload(fx) if isinstance(fx, str) and fx else (fx or {})
        self.moves = load_moves(HERE.parent / "move.csv")
        self.source = node_id(self.payer["jur"], "company")
        self.payee_node = node_id(self.payee["jur"], self.payee.get("subject", "company"))
        self.destinations = [node_id(*d) if isinstance(d, (list, tuple)) else d for d in (inp.get("destinations") or [self.payee_node])]
        self.notes = []
        self.normalise_codes()
        self.source = node_id(self.payer["jur"], "company")
        self.payee_node = node_id(self.payee["jur"], self.payee.get("subject", "company"))
        self.destinations = self.dest_codes or [self.payee_node]
        self.favourable = {p["key"]: p["favourable"] for p in self.q.predicates()}
        self.add_parent()
        self._hop_cache = {}
        self.hops_store = {}                              # cand_id -> list of hop items (per hop list)

    def normalise_codes(self):
        """Jurisdiction codes as the library writes them: an unknown code is an error, never an empty graph."""
        codes = {j["code"] for j in self.lib.juris}

        def code(value, where):
            c = str(value or "").strip().lower()
            if c not in codes:
                raise ValueError("%s %r is not a jurisdiction of the library (%s)" % (where, value, ", ".join(sorted(codes))))
            return c

        def node(value, where):
            j, _, s = (value if isinstance(value, str) else ":".join(value)).partition(":")
            return "%s:%s" % (code(j, where), (s or "company").strip().lower())

        self.payer = dict(self.payer, jur=code(self.payer.get("jur"), "payer.jur"))
        self.payee = dict(self.payee, jur=code(self.payee.get("jur"), "payee.jur"), subject=str(self.payee.get("subject") or "company").lower())
        for side in (self.payer, self.payee):
            facts = dict(side.get("facts") or {})
            for k in JUR_FACTS:
                if isinstance(facts.get(k), str):
                    facts[k] = code(facts[k], k)
            side["facts"] = facts
        self.entities = {node(k, "entities key"): dict(v, holds=node(v["holds"], "entities holds") if v.get("holds") else None,
                                                       facts={k2: (code(v2, k2) if k2 in JUR_FACTS and isinstance(v2, str) else v2) for k2, v2 in (v.get("facts") or {}).items()})
                         for k, v in self.entities.items()}
        self.dest_codes = [node(d, "destination") for d in (self.inp.get("destinations") or [])]

    def add_parent(self):
        """The payee's parent stated by its facts is a group entity: paying up to it changes no holding."""
        f = self.payee.get("facts") or {}
        jur, pct = f.get("parent_jur"), f.get("parent_holding_pct")
        node = node_id(jur, "company") if jur else None
        if not node or not pct or node in self.entities or node == self.payee_node \
                or any(e.get("holds") == self.payee_node for e in self.entities.values()):
            return
        facts = {"incorporated_in": jur, "managed_in": jur}
        if "mne_entity" in f:
            facts["mne_entity"] = f["mne_entity"]
        self.entities[node] = {"holds": self.payee_node, "holding_pct": pct, "holding_months": f.get("parent_holding_months"), "facts": facts}
        self.notes.append("%s taken from the payee's parent facts; its residence is assumed from parent_jur unless entities says otherwise" % node)

    def unfavourable(self, key):
        return "no" if self.favourable.get(key, "yes") == "yes" else "yes"

    def is_worst(self, asg):
        """Every judgment point of this branch goes against the client."""
        return all(v == self.unfavourable(k) for k, v in asg.items())

    def schedule_final(self, jur, subject):
        return subject == "individual" or any(r["jur"] == jur and r["slot"] == "final" and r["eff"] == "schedule" and r["subject"] in (subject, "all") for r in self.rs.rules)

    # ------------------------------------------------------------ coverage and nodes
    def covered(self, jur, subject):
        """The six dividend slots have rules or an absence record for this jurisdiction and subject."""
        absent = {(a["jur"], s, a["slot"]) for a in self.lib.absences if a.get("subject") and a.get("slot")
                  for s in (("company", "individual") if a["subject"] == "all" else (a["subject"],))}
        for slot in SIX:
            subj = "company" if slot == "residence" and subject == "company" else subject
            has_rule = any(r["jur"] == jur and r["slot"] == slot and r["subject"] in (subj, "all") for r in self.rs.rules)
            if not has_rule and (jur, subj, slot) not in absent:
                return False
        return True

    def nodes(self):
        out = []
        for j in self.lib.juris:
            jur = j["code"]
            if jur in self.constraints["exclude"]:
                continue
            for subject in ("company", "individual"):
                if self.constraints.get("allowed_subjects") and subject not in self.constraints["allowed_subjects"] \
                        and node_id(jur, subject) not in self.destinations and node_id(jur, subject) != self.payee_node:
                    continue
                if self.covered(jur, subject):
                    out.append({"node_id": node_id(jur, subject), "jur": jur, "subject": subject})
        ids = {n["node_id"] for n in out}
        for d in self.destinations + [self.payee_node, self.source]:
            if d not in ids:
                j, s = split_node(d)
                self.notes.append("node %s requested but its six slots are not covered by the library" % d)
        return out

    # ------------------------------------------------------------ facts of entities and hops
    def entity_facts(self, nid, path_so_far):
        """Facts of the entity at node nid: the payer, the current payee, a known group entity, or a new entity
        (facts only from the move that created it, group-level facts inherited)."""
        if nid == self.source:
            return dict(self.payer.get("facts") or {}), False
        if nid == self.payee_node:
            return dict(self.payee.get("facts") or {}), False
        if nid in self.entities:
            return dict(self.entities[nid].get("facts") or {}), False
        jur, subject = split_node(nid)
        f = {"incorporated_in": jur, "managed_in": jur}
        if subject == "individual":
            f = {"domicile_in": jur}
        for k in ("mne_entity",):                          # group-level facts inherited from the current payee
            if k in (self.payee.get("facts") or {}):
                f[k] = self.payee["facts"][k]
        return f, True

    def hop_facts(self, tail, head, path_so_far, fact_moves):
        """Facts of one hop tail -> head (spec §4.1)."""
        t_f, t_new = self.entity_facts(tail, path_so_far)
        h_f, h_new = self.entity_facts(head, path_so_far)
        facts = {}
        # payment facts: the as-is payment when the hop is the as-is hop; holding facts follow the structure
        if tail == self.source and head == self.payee_node:
            facts.update(self.payment)
        else:
            for k, v in self.payment.items():
                if k.startswith("payer_") and tail == self.source:
                    facts[k] = v                          # facts about the source company stay with it
            if tail == self.source:
                facts["holding_pct"] = self.payment.get("holding_pct")      # the new holder takes over the as-is stake
                facts["holding_months"] = 0 if h_new else self.payment.get("holding_months")
            elif head in self.entities and self.entities[head].get("holds") == tail:
                facts["holding_pct"] = self.entities[head].get("holding_pct")
                facts["holding_months"] = self.entities[head].get("holding_months")
            elif t_new or h_new:
                facts["holding_pct"] = 100
                facts["holding_months"] = 0
        RES_KEYS = ("incorporated_in", "managed_in", "domicile_in", "days_present", "listed")
        for k, v in t_f.items():
            facts["payer." + k] = v
        for k, v in h_f.items():
            facts["payee." + k] = v
            if k not in RES_KEYS:
                facts[k] = v                                  # payee-side facts the source cells read as plain names (safe harbours, factors)
        if tail != self.source:
            facts.setdefault("payer_listed", t_f.get("listed", False) if not t_new else False)
        for m, arg in fact_moves:
            facts.update(move_sets(m, arg))
        facts = {k: v for k, v in facts.items() if v is not None}
        mode = self.mode if (tail == self.source and head == self.payee_node and not fact_moves) else "plan"   # only the as-is hop is a record
        return facts, mode, (t_new or h_new)

    # ------------------------------------------------------------ one hop through the rule layer
    def eval_hop(self, tail, head, facts, mode, answers=None, assume=None, extra_payee=None):
        tj, _ = split_node(tail)
        hj, hs = split_node(head)
        f = dict(facts)
        if extra_payee:
            f.update(extra_payee)
            f = {k: v for k, v in f.items() if v != ""}             # "" removes an as-is fact (e.g. a parent fact that no longer holds)
        key = sha([tail, head, f, mode, answers or self.answers, sorted(assume or self.assume)])
        if key in self._hop_cache:
            return copy.deepcopy(self._hop_cache[key])
        items = ev.eval_flow(self.rs, tj, hj, hs, self.date, f, answers if answers is not None else self.answers, mode,
                             assume=assume if assume is not None else self.assume)
        items = strip_items(items)
        self._hop_cache[key] = items
        return copy.deepcopy(items)

    def absence(self, jur, subject, slot):
        for a in self.lib.absences:
            if a.get("jur") == jur and a.get("slot") == slot and a.get("subject") in (subject, "all"):
                return {"absence_record": a["id"], "cite_id": a.get("cite_id"), "statement": a.get("statement")}
        return None

    def hop_tax(self, items):
        """§4.5: the rate components of one hop from its items, both sides."""
        by = {it["slot"]: it for it in items if it["slot"] in ("outbound_wht", "inbound", "final", "cfc")}
        domestic = "outbound_wht" in by and "inbound" in by and by["outbound_wht"]["jur"] == by["inbound"]["jur"]
        out = {}
        for side in ("floor", "ceiling"):
            notes = []
            o = by.get("outbound_wht"); i = by.get("inbound"); fnl = by.get("final")
            wht = o[side]["value"] if o and o["status"] != "absent" and o[side]["value"] is not None else 0.0
            if domestic:
                wht = 0.0
                notes.append("domestic hop: outbound_wht not applied, the final cell taxes the recipient")
            elif o is None or o["status"] == "absent" or o[side]["value"] is None:
                ab = self.absence(o["jur"], o["subject"], "outbound_wht") if o else None
                notes.append("outbound_wht absent -> 0; %s" % json.dumps(ab, ensure_ascii=False) if ab else "outbound_wht absent or None -> 0")
            incl = i[side]["value"] if i and i["status"] != "absent" and i[side]["value"] is not None else 0.0
            rate = fnl[side]["value"] if fnl and fnl["status"] != "absent" and fnl[side]["value"] is not None else 0.0
            missing = (fnl is None or fnl["status"] == "absent" or fnl[side]["value"] is None) and incl > 0
            if missing:
                notes.append("final None with inbound inclusion > 0: value_missing")
            elif fnl is None or fnl["status"] == "absent" or fnl[side]["value"] is None:
                ab = self.absence(fnl["jur"], fnl["subject"], "final") if fnl else None
                notes.append("final absent or None -> 0 (nothing included); %s" % json.dumps(ab, ensure_ascii=False) if ab else "final absent or None -> 0 (nothing included)")
            if i is not None and i["status"] == "absent":
                ab = self.absence(i["jur"], i["subject"], "inbound")
                notes.append("inbound absent -> 0 included; %s" % json.dumps(ab, ensure_ascii=False) if ab else "inbound absent -> 0 included")
            res = incl / 100.0 * rate
            credit = min(wht, res) if (i and i[side].get("credit")) else 0.0
            t = (wht + res - credit) / 100.0
            out[side] = {"wht": r6(wht), "incl": r6(incl), "rate": r6(rate), "res": r6(res), "credit": r6(credit), "t": r6(t),
                         "w": None if t >= 1 else r6(-math.log(1 - t)), "value_missing": missing, "notes": notes}
        cfc = by.get("cfc")
        out["cfc_flag"] = bool(cfc and cfc["status"] != "absent" and cfc["ceiling"]["value"])
        out["needs"] = sorted({tuple(n) for it in items for n in it.get("needs", [])})
        out["needs_under_assumption"] = sorted({tuple(n) for it in items for n in (it.get("without_assumptions") or {}).get("needs", []) if tuple(n) not in set(out["needs"])})
        return out

    # ------------------------------------------------------------ graph
    def build_graph(self):
        nodes = self.nodes()
        ids = [n["node_id"] for n in nodes]
        edges = []
        fact_moves = [m for m in self.moves if m["kind"] == "fact"]
        combos = [[]]
        for m in fact_moves:
            if m["restructure"] != "no" and not self.constraints["allow_restructure"]:
                continue
            new = []
            for c in combos:
                if any(x[0]["move_id"] == m["move_id"] for x in c):
                    continue                                  # one move at most once per edge
                for a in m["args"]:
                    if len(c) + 1 <= self.limits["max_moves"]:
                        new.append(c + [(m, a)])
            combos += new
        for tail in ids:
            tj, ts = split_node(tail)
            if ts == "individual":
                continue                                     # an individual does not pay dividends onward
            for head in ids:
                if head == tail:
                    continue
                hj, hs = split_node(head)
                for fm in combos:
                    facts, mode, is_new = self.hop_facts(tail, head, [], fm)
                    if not self.precondition_ok(fm, facts):
                        continue
                    items = self.eval_hop(tail, head, facts, mode)
                    tx = self.hop_tax(items)
                    if any(tx[s]["w"] is None for s in ("floor", "ceiling")):
                        self.notes.append("edge %s->%s infeasible: t >= 1" % (tail, head))
                        continue
                    hj_subject_sched = self.schedule_final(hj, hs)
                    eid = "e%03d" % len(edges)
                    edges.append({"edge_id": eid, "tail": tail, "head": head, "hop_facts": facts, "mode": mode,
                                  "moves": [m["move_id"] + ("(%s)" % a if a else "") for m, a in fm],
                                  "restructure": [m["restructure"] for m, _ in fm if m["restructure"] != "no"],
                                  "w": {"floor": tx["floor"]["w"], "ceiling": tx["ceiling"]["w"]},
                                  "t": {"floor": tx["floor"]["t"], "ceiling": tx["ceiling"]["t"]},
                                  "needs": [list(n) for n in tx["needs"]], "amount_dependent": hj_subject_sched,
                                  "value_missing": tx["floor"]["value_missing"] or tx["ceiling"]["value_missing"],
                                  "items_ref": "edges/%s.json" % eid})
                    self.hops_store["edges/%s.json" % eid] = items
        return {"nodes": nodes, "edges": edges, "source": self.source, "destinations": self.destinations, "notes": self.notes}

    def precondition_ok(self, fm, facts):
        for m, a in fm:
            if not m["precondition"]:
                continue
            try:
                tree = ev.parse_condition(m["precondition"])
                ctx = ev.Context(self.rs, self.date, facts, self.answers, self.mode)
                s, _ = ctx.eval(tree)
                if s == "F":
                    return False
            except Exception:                                 # noqa: BLE001 - a bad precondition is reported by check.py
                return True
        return True

    # ------------------------------------------------------------ labels (§4.3)
    def labels(self, graph):
        edges_out = {}
        for e in graph["edges"]:
            edges_out.setdefault(e["tail"], []).append(e)
        edge_by_id = {e["edge_id"]: e for e in graph["edges"]}
        L0 = {"label_id": "L0", "node": self.source, "w": {"floor": 0.0, "ceiling": 0.0}, "needs": [], "hops": 0,
              "restructure": 0, "moves": 0, "transfers": [], "pred_label": None, "edge": None}
        labels = {self.source: [L0]}
        allab = {"L0": L0}
        counter = [0]
        openq = [(0.0, 0.0, "L0")]
        truncated = set()

        def dominates(a, b):
            return (a["w"]["floor"] <= b["w"]["floor"] + EPS and a["w"]["ceiling"] <= b["w"]["ceiling"] + EPS
                    and set(map(tuple, a["needs"])) <= set(map(tuple, b["needs"])) and a["hops"] <= b["hops"]
                    and a["restructure"] <= b["restructure"] and set(a.get("transfers", [])) <= set(b.get("transfers", [])))   # different companies sold = different one-off costs: incomparable

        while openq:
            _, _, lid = heapq.heappop(openq)
            L = allab[lid]
            if L.get("_dead"):
                continue
            for e in sorted(edges_out.get(L["node"], []), key=lambda x: x["edge_id"]):
                hops = L["hops"] + 1
                moves = L["moves"] + len(e["moves"])
                if hops > self.limits["max_hops"] or moves > self.limits["max_moves"]:
                    continue
                ew = e["w"]
                if e["amount_dependent"]:
                    ew = self.amount_dependent_weight(e, L)
                    if ew is None:
                        continue
                counter[0] += 1
                Lp = {"label_id": "L%d" % counter[0], "node": e["head"],
                      "w": {"floor": r6(L["w"]["floor"] + ew["floor"]), "ceiling": r6(L["w"]["ceiling"] + ew["ceiling"])},
                      "needs": sorted({tuple(n) for n in L["needs"]} | {tuple(n) for n in e["needs"]}),
                      "hops": hops, "restructure": L["restructure"] + len(e["restructure"]), "moves": moves,
                      "transfers": sorted(set(L.get("transfers", [])) | set(self.transfer_tags(e))),
                      "pred_label": lid, "edge": e["edge_id"], "edge_w": ew}
                Lp["needs"] = [list(n) for n in Lp["needs"]]
                bucket = labels.setdefault(e["head"], [])
                if any(dominates(M, Lp) for M in bucket):
                    continue
                for M in bucket:
                    if dominates(Lp, M):
                        M["_dead"] = True
                bucket[:] = [M for M in bucket if not M.get("_dead")] + [Lp]
                if len(bucket) > self.limits["max_labels"]:
                    bucket.sort(key=lambda m: (m["w"]["ceiling"], m["w"]["floor"], m["label_id"]))
                    for M in bucket[self.limits["max_labels"]:]:
                        M["_dead"] = True
                    del bucket[self.limits["max_labels"]:]
                    truncated.add(e["head"])
                allab[Lp["label_id"]] = Lp
                heapq.heappush(openq, (Lp["w"]["ceiling"], Lp["w"]["floor"], Lp["label_id"]))
        for n, bucket in labels.items():
            for M in bucket:
                M.pop("_dead", None)
        frontier = [M for n in self.destinations for M in labels.get(n, [])]
        return {"labels": labels, "frontier": [M["label_id"] for M in frontier], "truncated": sorted(truncated)}, allab

    def transfer_tags(self, e):
        """Which shares an edge implies selling (spec 4.2 resources): the source company when its holder changes, the
        as-is payee when its holder changes; acquisitions are tagged by their move."""
        tags = []
        if e["tail"] == self.source and e["head"] != self.payee_node:
            tags.append("sell:" + self.source)
        parent = next((n for n, x in self.entities.items() if x.get("holds") == self.payee_node), None)
        if e["tail"] == self.payee_node and e["head"] != parent:
            tags.append("sell:" + self.payee_node)
        tags += ["acquire:" + m for m in e["moves"] if m.startswith("holding_pct(")]
        return tags

    def amount_dependent_weight(self, e, L):
        """§4.1: an edge into a recipient whose final cell is a schedule: evaluate with the amount the label delivers."""
        hj, hs = split_node(e["head"])
        ccy = next((j["currency"] for j in self.lib.juris if j["code"] == hj), None)
        rate = (self.fx.get("rates") or {}).get(ccy, {}).get("rate") if self.fx else None
        extra = {}
        other = (self.payee.get("facts") or {}).get("other_taxable_income") if e["head"] == self.payee_node else \
            (self.entities.get(e["head"], {}).get("facts") or {}).get("other_taxable_income")
        if other is not None:
            extra["payee.other_taxable_income"] = other
        out = {}
        for side in ("floor", "ceiling"):
            ex = dict(extra)
            if rate:
                ex["payee.amount_payee_ccy"] = self.amount * math.exp(-L["w"][side]) * rate
            items = self.eval_hop(e["tail"], e["head"], e["hop_facts"], e["mode"], extra_payee=ex)
            tx = self.hop_tax(items)
            if tx[side]["w"] is None:
                return None
            out[side] = tx[side]["w"]
            self.hops_store["edges/%s.%s.%s.json" % (e["edge_id"], L["label_id"], side)] = items
        return out

    # ------------------------------------------------------------ paths (§1 [3])
    def paths(self, lab, allab, graph):
        edge_by_id = {e["edge_id"]: e for e in graph["edges"]}
        out = []
        # candidate 0: the as-is hop
        as_is_edge = next((e for e in graph["edges"] if e["tail"] == self.source and e["head"] == self.payee_node and not e["moves"]), None)
        cand0 = {"cand_id": "c0", "path": [self.source, self.payee_node], "edges": [as_is_edge["edge_id"]] if as_is_edge else [],
                 "moves": [], "restructure": [], "path_complete": self.payee_node in self.destinations, "as_is": True,
                 "requested": False, "label": None}
        out.append(cand0)
        k = 0
        for lid in lab["frontier"]:
            chain, edges = [], []
            M = allab[lid]
            while M is not None:
                chain.append(M["node"])
                if M["edge"]:
                    edges.append(M["edge"])
                M = allab[M["pred_label"]] if M["pred_label"] else None
            chain.reverse(); edges.reverse()
            if chain == cand0["path"] and all(not edge_by_id[e]["moves"] for e in edges):
                cand0["label"] = lid
                continue
            k += 1
            out.append({"cand_id": "c%d" % k, "path": chain, "edges": edges,
                        "moves": [m for e in edges for m in edge_by_id[e]["moves"]],
                        "restructure": [], "path_complete": chain[-1] in self.destinations, "as_is": False, "requested": False, "label": lid})
        for c in out:
            if not c["as_is"]:
                c["restructure"] = sorted({t["kind"] for t in self.transfers(c, graph) if t["kind"] != "unknown_holder"} | {"holder_unknown" for t in self.transfers(c, graph) if t["kind"] == "unknown_holder"})
        return out

    def inserts(self, chain):
        """A new entity between the source and the as-is payee, or a new holder of the as-is payee = a transfer."""
        if len(chain) < 2:
            return False
        if chain[1] != self.payee_node:
            return True
        return False

    # ------------------------------------------------------------ hops of a candidate, fork (§4.6)
    def holder_change(self, chain):
        """If the as-is payee gets a holder other than its known parent on this path: (new holder node) or None."""
        if self.payee_node in chain:
            i = chain.index(self.payee_node)
            if i + 1 < len(chain):
                nxt = chain[i + 1]
                parent = next((n for n, e in self.entities.items() if e.get("holds") == self.payee_node), None)
                if nxt != parent:
                    return nxt
        return None

    def candidate_hops(self, cand, graph, answers=None, assume=None, override=None):
        edge_by_id = {e["edge_id"]: e for e in graph["edges"]}
        hops = []
        w_acc = 0.0
        new_holder = self.holder_change(cand["path"])
        prev_items = None
        for eid in cand["edges"]:
            e = edge_by_id[eid]
            extra = {}
            derived = {}
            path_notes = []
            if new_holder and e["head"] == self.payee_node:        # the payee's parent changes downstream: its parent facts no longer hold upstream
                nj, _ = split_node(new_holder)
                extra.update({"parent_jur": nj, "parent_holding_pct": 100, "parent_holding_months": 0, "parent_treaty_not_worse": None,
                              "payee.parent_jur": nj, "payee.parent_holding_pct": 100, "payee.parent_holding_months": 0, "payee.parent_treaty_not_worse": None})
                path_notes.append("payee holder changes to %s on this path: parent safe-harbour facts replaced (label weight may be optimistic)" % new_holder)
            if prev_items is not None and e["tail"] != self.source:  # facts about the payer derived from the previous hop
                tj, _ = split_node(e["tail"])
                prev = {it["slot"]: it for it in prev_items if it["slot"] in ("inbound", "final")}
                taxed = {}
                for side in ("floor", "ceiling"):
                    inc = (prev.get("inbound") or {}).get(side, {}).get("value")
                    rate = (prev.get("final") or {}).get(side, {}).get("value")
                    taxed[side] = None if inc is None or rate is None else (inc > 0 and rate > 0)
                if taxed["floor"] is not None and taxed["floor"] == taxed["ceiling"] and "payer_income_taxed" not in e["hop_facts"]:
                    extra["payer_income_taxed"] = taxed["floor"]
                    derived["payer_income_taxed"] = {"value": taxed["floor"], "from": "previous hop %s: inbound / final items (included %s, rate %s)" % (hops[-1]["edge_id"] if hops else "", (prev.get("inbound") or {}).get("ceiling", {}).get("value"), (prev.get("final") or {}).get("ceiling", {}).get("value")),
                                                     "items_ref": "hops of the previous hop", "confirm": "the recipient's inbound rules read the immediate payer's taxation; see the decisions of its inbound cell for how far the look-through goes"}
                    path_notes.append("payer_income_taxed=%s derived from the previous hop's inbound / final items" % taxed["floor"])
                cit = self.lib.params.get("%s.final.cit_rate" % tj)
                if cit and "payer_tax_rate" not in e["hop_facts"]:
                    extra["payer_tax_rate"] = float(cit["value"])
                    derived["payer_tax_rate"] = {"value": float(cit["value"]), "from": cit["param_id"], "cite_id": cit["cite_id"]}
                    path_notes.append("payer_tax_rate=%s from %s" % (cit["value"], cit["param_id"]))
            if e["amount_dependent"]:
                hj, _ = split_node(e["head"])
                ccy = next((j["currency"] for j in self.lib.juris if j["code"] == hj), None)
                rate = (self.fx.get("rates") or {}).get(ccy, {}).get("rate") if self.fx else None
                if rate:
                    extra["payee.amount_payee_ccy"] = self.amount * math.exp(-w_acc) * rate
                oth = (self.payee.get("facts") or {}).get("other_taxable_income") if e["head"] == self.payee_node else None
                if oth is not None:
                    extra["payee.other_taxable_income"] = oth
            if override:
                for k, v in override.items():
                    extra[k] = v; extra["payer." + k] = v; extra["payee." + k] = v
            extra = {k: v for k, v in extra.items() if v is not None} | {k: "" for k, v in extra.items() if v is None}
            items = self.eval_hop(e["tail"], e["head"], e["hop_facts"], e["mode"], answers, assume, extra or None)
            tx = self.hop_tax(items)
            tx["path_notes"] = path_notes
            if derived:
                hj_, hs_ = split_node(e["head"])
                for key, d in derived.items():
                    readers = [r for r in self.rs.rules if r["jur"] == hj_ and r["slot"] in ("inbound", "final") and key in leaves_vars(r)]
                    d["read_by_rules"] = sorted(r["id"] for r in readers)
                    d["recipient_decisions"] = sorted({x for r in readers for x in r["decisions"]})
                    d["cite_ids"] = sorted({c for r in readers for c in r["cites"]})
            tx["derived"] = derived
            hops.append({"edge_id": eid, "tail": e["tail"], "head": e["head"], "items": items, "tax": tx, "extra_facts": extra, "derived": derived})
            w_acc += tx["ceiling"]["w"] or 0.0
            prev_items = items
        return hops

    def fork(self, cand, hops):
        about = {}

        def asked(hs):
            keys = set()
            for h in hs:
                for it in h["items"]:
                    for g in it.get("pending", []):
                        for n in g["needs"]:
                            if n[0] == "DISCRETION":
                                about.setdefault(n[1], h["head"])    # the recipient of the hop whose cell asks the question
                                if self.answers.get(n[1], "unknown") == "unknown":
                                    keys.add(n[1])
            return keys

        keys = asked(hops)
        for _ in range(FORK_ROUNDS):                                 # a point can open only once another settles: a denial in doubt hides what it denies
            if not keys:
                break
            best = {k: self.favourable.get(k, "yes") for k in keys}
            more = asked(self.candidate_hops(cand, self.graph, dict(self.answers, **best), sorted(set(self.assume) | set(best)))) - keys
            if not more:
                break
            keys |= more
        D = sorted(keys)
        branches = []
        if not D:
            branches.append({"branch_id": cand["cand_id"] + ".b0", "cand_id": cand["cand_id"], "answers_assumed": {}, "answers_about": {}, "hops": hops})
            return branches
        assignments = []
        if len(D) > self.limits["max_fork_keys"]:
            best = {k: self.favourable.get(k, "yes") for k in D}
            worst = {k: self.unfavourable(k) for k in D}
            assignments = [best, worst] + [dict(best, **{k: worst[k]}) for k in D]
            self.notes.append("%s: %d judgment points: all favourable, all unfavourable, and each one going against the client alone" % (cand["cand_id"], len(D)))
        else:
            for i in range(2 ** len(D)):
                assignments.append({k: ("yes" if (i >> j) & 1 == 0 else "no") for j, k in enumerate(D)})
        for i, asg in enumerate(assignments):
            answers = dict(self.answers, **asg)
            assume = sorted(set(self.assume) | set(asg))
            hs = self.candidate_hops(cand, self.graph, answers, assume)
            branches.append({"branch_id": "%s.b%d" % (cand["cand_id"], i), "cand_id": cand["cand_id"], "answers_assumed": asg, "answers_about": {k: about.get(k) for k in asg}, "hops": hs})
        return branches

    # ------------------------------------------------------------ tax table (§4.5)
    def branch_tax(self, branch, cand):
        out = {"branch_id": branch["branch_id"], "cand_id": branch["cand_id"], "path_complete": cand["path_complete"],
               "answers_assumed": branch["answers_assumed"], "answers_about": branch.get("answers_about", {}), "hops": [], "cfc_flag": False, "value_missing": False}
        per = {}
        for side in ("floor", "ceiling"):
            keep = 1.0
            for h in branch["hops"]:
                tx = h["tax"][side]
                keep *= (1 - tx["t"])
                if tx["value_missing"]:
                    out["value_missing"] = True
            per[side] = r6(100 * (1 - keep))
        for h in branch["hops"]:
            out["hops"].append({"edge_id": h["edge_id"], "tail": h["tail"], "head": h["head"],
                                "floor": {k: h["tax"]["floor"][k] for k in ("wht", "incl", "rate", "credit", "t")},
                                "ceiling": {k: h["tax"]["ceiling"][k] for k in ("wht", "incl", "rate", "credit", "t")},
                                "notes": sorted(set(h["tax"]["floor"]["notes"] + h["tax"]["ceiling"]["notes"] + h["tax"].get("path_notes", [])))})
            out["cfc_flag"] = out["cfc_flag"] or h["tax"]["cfc_flag"]
        out["per_100"] = per
        out["amount"] = {s: r6(per[s] / 100 * self.amount) for s in per}
        out["needs"] = sorted({tuple(n) for h in branch["hops"] for n in h["tax"]["needs"]})
        out["needs"] = [list(n) for n in out["needs"]]
        hidden = sorted({tuple(n) for h in branch["hops"] for n in h["tax"].get("needs_under_assumption", [])} - {tuple(n) for n in out["needs"]})
        out["needs_under_assumption"] = [list(n) for n in hidden]
        out["derived_facts"] = {h["edge_id"]: h.get("derived", {}) for h in branch["hops"] if h.get("derived")}
        out["complete"] = cand["path_complete"] and not out["value_missing"]
        return out

    # ------------------------------------------------------------ ranking, deltas (§4.7)
    def rank(self, taxes, cands, one_off, per_branch):
        by_c = {c["cand_id"]: c for c in cands}
        key_total = self.horizon is not None

        def keys(t):
            c = by_c[t["cand_id"]]
            if key_total:
                tot = (per_branch.get(t["branch_id"]) or {}).get("total_N") or {}
                if tot.get("ceiling") is None:
                    return None
                return (tot["ceiling"], tot["floor"], 1 if c["restructure"] else 0, len(c["edges"]), t["branch_id"])
            return (t["per_100"]["ceiling"], t["per_100"]["floor"], 1 if c["restructure"] else 0, len(c["edges"]), t["branch_id"])

        spread = {}
        for t in taxes:
            if t["complete"]:
                s = spread.setdefault(t["cand_id"], {"branches": 0, "per_100": {"floor": math.inf, "ceiling": -math.inf}, "amount": {"floor": math.inf, "ceiling": -math.inf}})
                s["branches"] += 1
                for part in ("per_100", "amount"):
                    s[part]["floor"] = min(s[part]["floor"], t[part]["floor"])
                    s[part]["ceiling"] = max(s[part]["ceiling"], t[part]["ceiling"])
        rows = []
        complete, incomplete = [], []
        for t in taxes:
            c = by_c[t["cand_id"]]
            k = keys(t) if t["complete"] else None
            pm = self.constraints.get("payback_max")
            pb = ((per_branch.get(t["branch_id"]) or {}).get("payback_years") or {}).get("ceiling")
            filtered = pm is not None and c["restructure"] and (pb is None or pb > pm)
            if c.get("requested"):
                incomplete.append((t, "requested path: not ranked"))
            elif k is None:
                incomplete.append((t, "incomplete" if not t["complete"] else "one_off_cost missing under horizon"))
            elif filtered:
                incomplete.append((t, "payback above %s years" % pm))
            else:
                complete.append((k, t))
        complete.sort(key=lambda x: x[0])
        for i, (k, t) in enumerate(complete):
            dom = [u["branch_id"] for _, u in complete if u is not t and u["per_100"]["ceiling"] <= t["per_100"]["floor"] + EPS
                   and (u["per_100"]["ceiling"] < t["per_100"]["ceiling"] - EPS or u["per_100"]["floor"] < t["per_100"]["floor"] - EPS)
                   and u["complete"] == t["complete"]]
            rows.append({"branch_id": t["branch_id"], "cand_id": t["cand_id"], "rank": i + 1, "keys": list(k), "dominated_by": dom,
                         "key": "total_N" if key_total else "per_100", "answers_assumed": t["answers_assumed"], "range_all_branches": spread[t["cand_id"]]})
        for t, why in incomplete:
            rows.append({"branch_id": t["branch_id"], "cand_id": t["cand_id"], "rank": None, "keys": None, "dominated_by": [], "why": why})
        return rows

    def branch_one_off(self, t, as_is, oo):
        """Per-branch payback_years and total_N from the candidate one-off cost (spec 4.7)."""
        tot = (oo or {}).get("total") or {"floor": None, "ceiling": None}
        out = {"payback_years": None, "total_N": None, "saving_per_year": None}
        if tot["floor"] is None:
            return out
        if as_is:
            saving = {s: as_is["amount"][s] - t["amount"][s] for s in ("floor", "ceiling")}
            out["saving_per_year"] = {s: r6(saving[s]) for s in saving}
            out["payback_years"] = {"floor": None if saving["ceiling"] <= 0 else r6(tot["floor"] / saving["ceiling"]),
                                    "ceiling": None if saving["floor"] <= 0 else r6(tot["ceiling"] / saving["floor"])}
            if tot["floor"] == 0 and tot["ceiling"] == 0:
                out["payback_years"] = {"floor": 0.0, "ceiling": 0.0}
        if self.horizon is not None:
            N = float(self.horizon)
            out["total_N"] = {s: r6(tot[s] + N * t["amount"][s]) for s in ("floor", "ceiling")}
        return out

    @staticmethod
    def delta(a, b):
        if a is None or b is None:
            return None
        return {"per_100": {s: r6(a["per_100"][s] - b["per_100"][s]) for s in ("floor", "ceiling")},
                "amount": {s: r6(a["amount"][s] - b["amount"][s]) for s in ("floor", "ceiling")}}

    def deltas(self, taxes, ranking, one_off, exposure, per_branch):
        by_b = {t["branch_id"]: t for t in taxes}
        c0 = [t for t in taxes if t["cand_id"] == "c0"]
        best_id = next((r["branch_id"] for r in ranking if r["rank"] == 1), None)
        by_c = {c["cand_id"]: c for c in self.cands}
        no_restr = [t for t in taxes if t["complete"] and not by_c[t["cand_id"]]["restructure"] and not by_c[t["cand_id"]].get("requested")]
        out = []
        for t in taxes:
            same = t["answers_assumed"]
            as_is = next((u for u in c0 if all(u["answers_assumed"].get(k, v) == v for k, v in same.items())), c0[0] if c0 else None)
            fallback = next((u for u in taxes if u["cand_id"] == t["cand_id"] and self.is_worst(u["answers_assumed"])), None)
            ref = next((u for u in sorted(no_restr, key=lambda u: (u["per_100"]["ceiling"], u["per_100"]["floor"], u["branch_id"]))
                        if all(u["answers_assumed"].get(k, v) == v for k, v in same.items())), None)
            vs_nr = None
            if ref and by_c[t["cand_id"]]["restructure"]:
                tot = ((one_off.get(t["cand_id"]) or {}).get("total") or {})
                saving = {s: ref["amount"][s] - t["amount"][s] for s in ("floor", "ceiling")}
                vs_nr = {"branch_id": ref["branch_id"], "saving_per_year": {s: r6(saving[s]) for s in saving},
                         "payback_years": None if tot.get("floor") is None else {"floor": None if saving["ceiling"] <= 0 else r6(tot["floor"] / saving["ceiling"]),
                                                                                "ceiling": None if saving["floor"] <= 0 else r6(tot["ceiling"] / saving["floor"])}}
            out.append({"branch_id": t["branch_id"], "cand_id": t["cand_id"],
                        "notes": ["saving_per_year and payback assume the same amount every year", "exposure interest runs from the withholding deadline to as_of = %s (an input, not a fact of the case)" % self.as_of],
                        "vs_as_is": self.delta(t, as_is), "as_is_branch": as_is["branch_id"] if as_is else None,
                        "vs_best_no_restructure": vs_nr,
                        "vs_fallback": self.delta(t, fallback), "fallback_branch": fallback["branch_id"] if fallback else None,
                        "vs_best": self.delta(t, by_b.get(best_id)) if best_id else None, "best_branch": best_id,
                        "exposure_if_denied": exposure.get(t["branch_id"]),
                        "one_off_cost": one_off.get(t["cand_id"]), **(per_branch.get(t["branch_id"]) or {})})
        return out

    # ------------------------------------------------------------ the short version (§5)
    def brief(self, cands, taxes, ranking, deltas, open_items):
        """What a reader needs first: the best branch of each candidate, the exposure of the winner, the open items that move the ranking."""
        tax = {t["branch_id"]: t for t in taxes}
        delta = {d["branch_id"]: d for d in deltas}
        cand = {c["cand_id"]: c for c in cands}

        def row(r):
            d, c = delta[r["branch_id"]], cand[r["cand_id"]]
            cost = d.get("one_off_cost") or {}
            return {"branch_id": r["branch_id"], "cand_id": r["cand_id"], "rank": r["rank"], "path": c["path"], "restructure": c["restructure"],
                    "answers_assumed": r["answers_assumed"], "amount": tax[r["branch_id"]]["amount"], "range_all_branches": r["range_all_branches"],
                    "vs_as_is": (d.get("vs_as_is") or {}).get("amount"), "one_off_total": cost.get("total"), "one_off_flags": cost.get("flags", [])}
        ranked = [r for r in ranking if r["rank"]]
        first = {}
        for r in ranked:
            first.setdefault(r["cand_id"], r)
        best = ranked[0] if ranked else None
        exposure = (delta[best["branch_id"]].get("exposure_if_denied") or {}) if best else {}
        c0 = [t for t in taxes if t["cand_id"] == "c0"]
        as_is = None
        if c0:
            lead = next((t for t in c0 if all(v == self.favourable.get(k, "yes") for k, v in t["answers_assumed"].items())), c0[0])
            as_is = {"branch_id": lead["branch_id"], "cand_id": "c0", "path": cand["c0"]["path"], "ranked": "c0" in first, "answers_assumed": lead["answers_assumed"],
                     "amount": lead["amount"], "range_all_branches": {"amount": {"floor": min(t["amount"]["floor"] for t in c0), "ceiling": max(t["amount"]["ceiling"] for t in c0)}, "branches": len(c0)},
                     "why_not_ranked": None if "c0" in first else next((r.get("why") for r in ranking if r["cand_id"] == "c0"), None)}
        return {"best": row(best) if best else None, "as_is": as_is, "candidates": [row(r) for r in list(first.values())[:BRIEF_ROWS]],
                "exposure_if_denied": {k: exposure.get(k) for k in ("benefit_assumed", "tax", "interest", "fine", "total", "as_of")},
                "open_items_changing_rank": [{k: x.get(k) for k in ("key", "kind", "question", "about", "if_yes", "if_no")} for x in open_items if x.get("changes_rank")],
                "not_ranked": sum(1 for r in ranking if not r["rank"]), "notes": self.notes}

    # ------------------------------------------------------------ past payments (§4.11)
    def past_payment(self, row):
        """One earlier dividend on the as-is hop: the tax it should have borne, what can be reclaimed and until when, and
        the stated figures that do not reconcile."""
        tj, _ = split_node(self.source)
        hj, hs = split_node(self.payee_node)
        date, share = row["date"], float(row["payee_share"])
        facts, _, _ = self.hop_facts(self.source, self.payee_node, [], [])
        if "holding_months" in facts:
            facts["holding_months"] = max(0, int(facts["holding_months"]) - months_between(parse_date(date), parse_date(self.date)))
        keys = sorted(self.favourable)
        rate = {}
        for world, side, asg in (("treaty", "floor", self.favourable), ("statutory", "ceiling", {k: self.unfavourable(k) for k in keys})):
            items = strip_items(ev.eval_flow(self.rs, tj, hj, hs, date, facts, asg, "record"))
            cell = next(it for it in items if it["slot"] == "outbound_wht")
            rate[world], cites = cell[side]["value"], cell["cite_ids"]
        due = None if rate["statutory"] is None else share * rate["statutory"] / 100
        refund = None
        if rate["statutory"] is not None and rate["treaty"] is not None and not row.get("treaty_claimed"):
            refund = share * max(0.0, rate["statutory"] - rate["treaty"]) / 100
        conflicts = []
        withheld, gross, net = row.get("withheld"), row.get("gross"), row.get("net_received")
        if withheld is not None and due is not None and abs(float(withheld) - due) > 1:
            text = "tax stated %s, but %s%% on the payee's share %s is %s" % (withheld, rate["statutory"], row["payee_share"], r6(due))
            if gross is not None and abs(float(withheld) - float(gross) * rate["statutory"] / 100) <= 1:
                text += "; the stated tax equals the rate on the whole dividend %s" % gross
            conflicts.append(text)
        if net is not None and due is not None and abs(float(net) - (share - due)) > 1:
            conflicts.append("net received stated %s, but the payee's share less tax is %s" % (net, r6(share - due)))
        limit, param = None, None
        for p in self.tool.reference_params("%s|company|outbound_wht|%s" % (tj, hj)):
            if p["param_id"].endswith(".refund_claim_years"):
                d = parse_date(date)
                years = int(float(p["value"]))
                limit = d.replace(year=d.year + years, day=min(d.day, calendar.monthrange(d.year + years, d.month)[1])).isoformat()
                param = p["param_id"]
        return {"date": date, "payee_share": share, "withheld_stated": withheld, "treaty_claimed": bool(row.get("treaty_claimed")),
                "rate_statutory": rate["statutory"], "rate_treaty": rate["treaty"], "tax_at_statutory_rate": None if due is None else r6(due),
                "refundable_if_qualified": None if refund is None else r6(refund), "condition": "every judgment point of the as-is hop goes the client's way for that year",
                "refund_limit_date": limit, "limit_param": param, "still_open_at_payment_date": None if limit is None else limit >= self.date,
                "limit_note": "counted from the payment date; the law counts from the date the tax was settled", "conflicts": conflicts,
                "source": row.get("source"), "cite_ids": cites}

    # ------------------------------------------------------------ exposure (§4.7)
    def deadline(self, S, R, subject):
        """The withholding deadline of the source hop from reference parameters, or None."""
        refs = self.tool.reference_params("%s|%s|outbound_wht|%s" % (S, subject, R))
        d = parse_date(self.date)
        for p in refs:
            n = p["param_id"].split(".")[2] if p["param_id"].count(".") >= 2 else p["param_id"]
            try:
                v = float(p["value"])
            except ValueError:
                continue
            if n == "withholding_deadline_days":
                return d + timedelta(days=int(v)), p["param_id"]
            if n == "withholding_deadline_days_after_month_end":
                end = d.replace(day=calendar.monthrange(d.year, d.month)[1])
                return end + timedelta(days=int(v)), p["param_id"]
            if n == "withholding_deadline_day_of_next_month":
                y, m = (d.year + (1 if d.month == 12 else 0)), (1 if d.month == 12 else d.month + 1)
                return _date(y, m, min(int(v), calendar.monthrange(y, m)[1])), p["param_id"]
        return None, None

    def exposure(self, branches, taxes):
        by_b = {t["branch_id"]: t for t in taxes}
        out = {}
        for b in branches:
            yes = [k for k, v in b["answers_assumed"].items() if v == self.favourable.get(k, "yes")]
            if not yes:
                continue
            fb = next((u for u in branches if u["cand_id"] == b["cand_id"] and self.is_worst(u["answers_assumed"])), None)
            if fb is None or fb is b:
                continue
            t, tf = by_b[b["branch_id"]], by_b[fb["branch_id"]]
            tax = {s: r6(tf["amount"][s] - t["amount"][s]) for s in ("floor", "ceiling")}
            # the hop-by-hop difference, split between the source cells (wht) and the residence cells (res - credit)
            parts = []                                          # (jur, S, R, subj, slot_keys, tax_part{floor, ceiling}, is_source)
            for h, hf in zip(b["hops"], fb["hops"]):
                S, _ = split_node(h["tail"]); R, subj = split_node(h["head"])
                src_keys = [it["slot_key"] for it in h["items"] if it["jur"] == S and it["slot"] in ("outbound_wht", "anti_abuse") and any(k in it.get("assumptions", []) for k in yes)]
                res_keys = [it["slot_key"] for it in h["items"] if it["jur"] == R and it["slot"] in ("inbound", "final", "anti_abuse") and any(k in it.get("assumptions", []) for k in yes)]
                for side in ("floor", "ceiling"):
                    pass
                if src_keys:
                    part = {}
                    for side in ("floor", "ceiling"):
                        before = self.amount_before(fb["hops"], h["edge_id"], side)
                        part[side] = r6(before * (hf["tax"][side]["wht"] - h["tax"][side]["wht"]) / 100)
                    parts.append((S, S, R, subj, src_keys, part, True))
                if res_keys:
                    part = {}
                    for side in ("floor", "ceiling"):
                        before = self.amount_before(fb["hops"], h["edge_id"], side)
                        d_res = (hf["tax"][side]["res"] - hf["tax"][side]["credit"]) - (h["tax"][side]["res"] - h["tax"][side]["credit"])
                        part[side] = r6(before * d_res / 100)
                    parts.append((R, S, R, subj, res_keys, part, False))
            if not parts:
                continue
            as_of = parse_date(self.as_of)
            cells_out, interest, fine, total, flags = [], {"floor": 0.0, "ceiling": 0.0}, {"floor": 0.0, "ceiling": 0.0}, {"floor": 0.0, "ceiling": 0.0}, set()
            for jur, S, R, subj, keys, part, is_src in parts:
                dl, dl_param = self.deadline(S, R, subj) if is_src else (None, None)
                overdue_m = months_between(dl, as_of) if dl else 0
                overdue_d = max(0, (as_of - dl).days) if dl else 0
                pen = strip_items([ev.eval_cell(self.rs, "%s|all|penalty|*" % jur, self.date, {"overdue_months": overdue_m}, self.answers, self.mode)])[0]
                self.hops_store["penalty/%s.json" % jur] = [pen]
                cell = {"jurisdiction": jur, "cells": keys, "penalty_cell": pen["slot_key"], "tax": part, "deadline": dl.isoformat() if dl else None,
                        "deadline_param": dl_param, "overdue_months": overdue_m, "interest": {}, "fine": {}, "flags": [], "items_ref": "penalty/%s.json" % jur}
                if pen["status"] == "absent":
                    cell["flags"].append("penalty_missing")
                if dl is None:
                    cell["flags"].append("deadline_missing")
                for side in ("floor", "ceiling"):
                    v = (pen[side]["value"] or {}) if pen["status"] != "absent" else {}
                    base = part[side]
                    acc = 0.0
                    for i in v.get("interest", []):
                        per, pct = i.get("period"), i["pct"]
                        if dl is None:
                            continue
                        if per == "day":
                            acc += base * pct / 100 * overdue_d
                        elif per == "month":
                            acc += base * pct / 100 * overdue_m
                        elif per == "year":
                            acc += base * pct / 100 * overdue_d / 365.0
                        elif per == "once":
                            acc += base * pct / 100
                    if v.get("interest_cap") is not None:
                        acc = min(acc, base * v["interest_cap"] / 100)
                    if pen["status"] != "absent" and not v.get("interest"):
                        cell["flags"].append("interest_missing")
                    fmin, fmax = v.get("fine_min") or 0.0, v.get("fine_max") or 0.0
                    cell["interest"][side] = r6(acc)
                    cell["fine"][side] = r6(base * (fmin if side == "floor" else fmax) / 100)
                    interest[side] += acc
                    fine[side] += cell["fine"][side]
                    total[side] += base + acc + cell["fine"][side]
                cell["flags"] = sorted(set(cell["flags"]))
                flags |= set(cell["flags"])
                cells_out.append(cell)
            out[b["branch_id"]] = {"benefit_assumed": yes, "fallback_branch": fb["branch_id"], "tax": tax, "as_of": self.as_of,
                                   "cells": cells_out, "interest": {s: r6(interest[s]) for s in interest}, "fine": {s: r6(fine[s]) for s in fine},
                                   "total": {s: r6(total[s]) for s in total}, "flags": sorted(flags)}
        return out

    def amount_before(self, hops, edge_id, side):
        """The amount arriving at the hop (full redistribution): amount × Π(1 − t) of the earlier hops."""
        keep = 1.0
        for h in hops:
            if h["edge_id"] == edge_id:
                break
            keep *= 1 - h["tax"][side]["t"]
        return self.amount * keep

    # ------------------------------------------------------------ transfers and one-off cost (§4.7)
    def fx_rate(self, ccy):
        if not ccy or ccy == self.currency:
            return 1.0
        r = (self.fx.get("rates") or {}).get(ccy, {}).get("rate") if self.fx else None
        return r

    def jur_ccy(self, jur):
        return next((j["currency"] for j in self.lib.juris if j["code"] == jur), None)

    def transfers(self, cand, graph):
        """The holding changes of a candidate against the as-is structure (§4.4): each is one eval_transfer."""
        chain = cand["path"]
        out = []
        if len(chain) < 2:
            return out
        # 1. a new holder of the source company (someone other than the as-is payee holds S)
        if chain[1] != self.payee_node:
            tgt, new_holder = self.source, chain[1]
            holder = self.payee_node                       # the as-is holder transfers its S shares to the new holder
            out.append(self._transfer(tgt, holder, new_holder, self.payment.get("holding_pct"), "transfer"))
        # 2. the as-is payee gets a new holder (next node after it that is not its known parent)
        if self.payee_node in chain:
            i = chain.index(self.payee_node)
            if i + 1 < len(chain):
                nxt = chain[i + 1]
                parent = next((n for n, e in self.entities.items() if e.get("holds") == self.payee_node), None)
                if parent and nxt != parent:
                    out.append(self._transfer(self.payee_node, parent, nxt, self.entities[parent].get("holding_pct"), "transfer"))
                elif parent is None and nxt not in self.entities:
                    out.append({"target": self.payee_node, "transferor": None, "transferee": nxt, "kind": "unknown_holder",
                                "note": "the as-is holder of %s is not in the input (entities), transfer cost unknown" % self.payee_node})
        # 2b. indirect transfers: the transferred company holds a company of another jurisdiction (STA 2015 No. 7 and the like)
        for tr in list(out):
            if tr["kind"] != "transfer" or not tr.get("transferor"):
                continue
            for held, hpct in self.holdings_of(tr["target"]):
                if split_node(held)[0] != split_node(tr["target"])[0]:
                    out.append(self._transfer(held, tr["transferor"], tr["transferee"], float(tr["pct"] or 0) * hpct / 100, "indirect"))
        # 3. acquisitions by fact moves
        edge_by_id = {e["edge_id"]: e for e in graph["edges"]}
        for eid in cand["edges"]:
            e = edge_by_id[eid]
            for mv in e["moves"]:
                if mv.startswith("holding_pct("):
                    pct = float(mv[len("holding_pct("):-1])
                    base = float(self.payment.get("holding_pct") or 0) if e["tail"] == self.source else 0.0
                    if pct > base:
                        out.append(self._transfer(e["tail"], None, e["head"], pct - base, "acquire"))
        return out

    def holdings_of(self, node):
        """What a node holds: (held node, pct) from the as-is payment (payee holds the source) or the entities map."""
        if node == self.payee_node:
            return [(self.source, float(self.payment.get("holding_pct") or 0))]
        e = self.entities.get(node) or {}
        return [(e["holds"], float(e.get("holding_pct") or 0))] if e.get("holds") else []

    def relation_pct(self, a, b):
        """Ownership relation between two nodes through the known chain (a holds b, b holds a, or a common holder), else None."""
        def chain_pct(x, y, depth=0):
            if depth > 4:
                return None
            for held, pct in self.holdings_of(x):
                if held == y:
                    return pct
                sub = chain_pct(held, y, depth + 1)
                if sub is not None:
                    return pct * sub / 100
            return None
        for x, y in ((a, b), (b, a)):
            p = chain_pct(x, y)
            if p is not None:
                return p
        return None

    def gain_of(self, target, pct, kind):
        """Consideration and gain of a transfer in the target's currency (§4.7): appraised value, else net assets, times pct."""
        tj, _ = split_node(target)
        val = self.valuation.get(target, {})
        out = {"currency": val.get("currency") or self.jur_ccy(tj), "flags": set(), "basis": None, "consideration": None, "gain": None}
        if val.get("appraised_value") is not None:
            out["consideration"], out["basis"] = float(val["appraised_value"]) * float(pct or 0) / 100, "appraised_value"
        elif val.get("net_assets") is not None:
            out["consideration"], out["basis"] = float(val["net_assets"]) * float(pct or 0) / 100, "net_assets"
        else:
            out["flags"].add("valuation_missing"); return out
        cost = val.get("cost_base")
        if cost is None:
            out["gain"] = out["consideration"]; out["flags"].add("cost_missing")
        else:
            out["gain"] = max(0.0, out["consideration"] - float(cost) * float(pct or 0) / 100)
        if kind == "acquire":
            out["gain"] = 0.0
        return out

    def convert(self, amount, from_ccy, to_ccy):
        """amount in from_ccy expressed in to_ccy through the fx table (rates are units per payment currency); None without rates."""
        if amount is None:
            return None
        a, b = self.fx_rate(from_ccy), self.fx_rate(to_ccy)
        return None if not a or not b else amount / a * b

    def direct_transfer_rate(self, target, holder, pct):
        """Ceiling rate of the target jurisdiction's restructure cell for a direct transfer of `target` by `holder` (plan mode)."""
        tj, _ = split_node(target)
        hj, hs = split_node(holder)
        tf = {"target." + k: v for k, v in self.entity_facts(target, [])[0].items()}
        for k, v in self.entity_facts(holder, [])[0].items():
            tf["transferor." + k] = v
        tf.update({"target_jur": tj, "transferred_pct": pct, "holding_pct": pct, "indirect_transfer": False})
        tf = {k: v for k, v in tf.items() if v is not None}
        items = ev.eval_transfer(self.rs, tj, hj, hs, self.date, tf, self.answers, "plan", assume=self.assume)
        src = next((it for it in items if it["slot"] == "restructure" and it["jur"] == tj), None)
        return None if src is None else (src["ceiling"] or {}).get("value")

    def _transfer(self, target, transferor, transferee, pct, kind):
        tj, _ = split_node(target)
        rec = {"target": target, "transferor": transferor, "transferee": transferee, "kind": kind, "pct": pct}
        tf = {}
        tgt_f, _ = self.entity_facts(target, [])
        for k, v in tgt_f.items():
            tf["target." + k] = v
        val = self.valuation.get(target, {})
        if val.get("property_rich_ratio") is not None:
            tf["property_rich_ratio"] = val["property_rich_ratio"]
        if "listed" in tgt_f:
            tf["target_listed"] = tgt_f["listed"]
        tf["target_jur"] = tj
        tf["transferred_pct"] = pct
        tf["indirect_transfer"] = kind == "indirect"
        derived = {}
        if kind == "indirect" and transferor and transferee:
            rel = self.relation_pct(transferor, transferee)
            if rel is not None:
                tf["group_relation_pct"] = rel
            if tj == "cn" and "future_cn_tax_not_reduced" not in getattr(self, "transfer_override", {}):   # STA 2015 No. 7 item 6(2)
                old_r, new_r = self.direct_transfer_rate(target, transferor, pct), self.direct_transfer_rate(target, transferee, pct)
                if old_r is not None and new_r is not None:
                    tf["future_cn_tax_not_reduced"] = new_r >= old_r - EPS
                    derived["future_cn_tax_not_reduced"] = {
                        "value": tf["future_cn_tax_not_reduced"], "cite_id": "cn.sta.2015-07#i6",
                        "from": "Chinese tax on a direct transfer of %s: by the transferee %s %s%%, by the transferor %s %s%% (ceiling of the cn restructure cell, plan mode)" % (target, transferee, new_r, transferor, old_r),
                        "confirm": "item 6(2) compares the Chinese tax on a later indirect transfer with and without this one; the layer proxies it by the direct-transfer rate of the new and the old holder (treaty Article 13 position)"}
        if kind == "indirect" and tj == "cn" and transferee and split_node(transferee)[1] == "individual"                 and "consideration_in_shares" not in getattr(self, "transfer_override", {}):   # item 6(3): an individual has no enterprise shares to pay with
            tf["consideration_in_shares"] = False
            derived["consideration_in_shares"] = {"value": False, "cite_id": "cn.sta.2015-07#i6",
                                                  "from": "the transferee %s is an individual: item 6(3) requires payment entirely in shares of the transferee enterprise or an enterprise it controls" % transferee,
                                                  "confirm": "holds unless the deal is restructured so that an enterprise controlled by the individual is the transferee"}
        if kind in ("transfer", "indirect") and transferor:
            hj, hs = split_node(transferor)
            tr_f, _ = self.entity_facts(transferor, [])
            for k, v in tr_f.items():
                tf["transferor." + k] = v
            if hs == "individual":                           # a schedule in the home cell reads the gain in the home currency
                g = self.gain_of(target, pct, kind)
                amt = self.convert(g["gain"], g["currency"], self.jur_ccy(hj))
                if amt is not None:
                    tf["amount_payee_ccy"] = amt
                if tr_f.get("other_taxable_income") is not None:
                    tf["other_taxable_income"] = tr_f["other_taxable_income"]
            tf["holding_pct"] = pct
            tf["holding_months"] = self.payment.get("holding_months") if target == self.source else (self.entities.get(transferor, {}).get("holding_months") if self.entities.get(transferor, {}).get("holds") == target else None)
            tf.update(getattr(self, "transfer_override", {}))
            tf = {k: v for k, v in tf.items() if v is not None}
            items = strip_items(ev.eval_transfer(self.rs, tj, hj, hs, self.date, tf, self.answers, "plan", assume=self.assume))
        else:                                              # acquire: only the source-side stamp duty matters
            hj, hs = split_node(transferee)
            tf["transferor.incorporated_in"] = hj
            tf = {k: v for k, v in tf.items() if v is not None}
            items = strip_items(ev.eval_transfer(self.rs, tj, hj, hs, self.date, tf, self.answers, "plan", assume=self.assume))
        rec["items"] = items
        rec["facts"] = {k: v for k, v in tf.items() if not k.startswith(("target.", "transferor."))}
        rec["needs"] = sorted({tuple(n) for it in items for n in it.get("needs", [])})
        rec["derived"] = derived
        return rec

    def one_off(self, cand, transfers):
        """§4.7 one_off_cost of a candidate (payback and total_N are per branch, see branch_one_off)."""
        if not transfers:
            return {"transfers": [], "total": {"floor": 0.0, "ceiling": 0.0}, "flags": []}
        flags = set()
        unquantified = set()
        total = {"floor": 0.0, "ceiling": 0.0}
        rows = []
        for tr in transfers:
            row = {k: tr.get(k) for k in ("target", "transferor", "transferee", "kind", "pct", "facts")}
            row["needs"] = [list(n) for n in tr.get("needs", [])]
            row["derived"] = tr.get("derived") or {}
            if tr["kind"] == "unknown_holder":
                flags.add("holder_unknown"); row["note"] = tr["note"]; rows.append(row); continue
            tj, _ = split_node(tr["target"])
            g = self.gain_of(tr["target"], tr["pct"], tr["kind"])
            ccy = g["currency"]
            rate = self.fx_rate(ccy)
            if rate is None:
                flags.add("fx_missing")
            flags |= g["flags"]
            if g["consideration"] is None:
                row["note"] = "net_assets / appraised_value of %s not given" % tr["target"]; rows.append(row); continue
            cons, gain = g["consideration"], g["gain"]
            row["consideration_basis"] = g["basis"]
            if tr["kind"] == "indirect":
                unquantified.add("indirect transfer reporting (STA 2015 No. 7 item 9) for %s" % tr["target"])
            src = next((it for it in tr["items"] if it["slot"] == "restructure" and it["jur"] == tj), None)
            home = next((it for it in tr["items"] if it["slot"] == "restructure" and it["jur"] != tj), None)
            inc, stamp = {}, {}
            for side in ("floor", "ceiling"):
                r_src = (src or {}).get(side, {}).get("value") or 0.0
                r_home = ((home or {}).get(side, {}).get("value") or 0.0) if tr["kind"] in ("transfer", "indirect") else 0.0
                credit = min(r_src, r_home) if (home and (home.get(side) or {}).get("credit")) else 0.0   # ordinary credit at home (rule effect credit)
                if home and tr["kind"] in ("transfer", "indirect") and r_home and not (home.get(side) or {}).get("credit"):
                    flags.add("no_credit")
                inc[side] = gain * (r_src + r_home - credit) / 100
                st_total = (src or {}).get(side, {}).get("stamp") or 0.0
                if tr["kind"] == "acquire":                     # buyer side only: rules whose id ends with transferee / bought_note
                    buyer = [rid for rid in (src or {}).get("rules_applied", {}).get(side, []) if rid.endswith((".transferee", ".bought_note"))]
                    seller = [rid for rid in (src or {}).get("rules_applied", {}).get(side, []) if rid.endswith((".transferor", ".sold_note"))]
                    if buyer or seller:
                        st = sum(self.rs.pvalue(next(r for r in self.rs.rules if r["id"] == rid)["param"]) for rid in buyer)
                    else:
                        st = st_total
                        if st_total:
                            flags.add("stamp_side_unknown")
                elif tr["kind"] == "indirect":
                    st = 0.0                                      # no instrument over the underlying shares: stamp duty falls on the direct transfer only
                else:
                    st = st_total
                stamp[side] = cons * st / 100
            conv = (1.0 / rate) if rate else None
            row.update({"currency": ccy, "consideration": r6(cons), "gain": r6(gain),
                        "income_tax": {s: r6(inc[s]) for s in inc}, "stamp": {s: r6(stamp[s]) for s in stamp},
                        "in_payment_currency": None if conv is None else {s: r6((inc[s] + stamp[s]) * conv) for s in inc},
                        "items_ref": "transfers/%s.json" % cand["cand_id"]})
            if conv is not None:
                for s in total:
                    total[s] += (inc[s] + stamp[s]) * conv
            rows.append(row)
        res = {"transfers": rows, "flags": sorted(flags), "total": {s: r6(total[s]) for s in total}, "costs_unquantified": sorted(unquantified)}
        if "valuation_missing" in flags or "fx_missing" in flags or "holder_unknown" in flags:
            res["total"] = {"floor": None, "ceiling": None}
        return res

    # ------------------------------------------------------------ requirements (§4.10)
    def requirements(self, cand, hops):
        out = []
        for h in hops:
            for it in h["items"]:
                fav_rules = [rid for rid in it["rules_applied"]["floor"]]
                rows = []
                for rid in fav_rules:
                    r = next((x for x in self.rs.rules if x["id"] == rid), None)
                    if r is None or r["eff"] not in FAV_EFFECTS:
                        continue
                    rows.append(self.q.requirements(rule_id=rid))
                if rows or it["slot"] == "outbound_wht":
                    out.append({"edge_id": h["edge_id"], "slot_key": it["slot_key"], "favourable_rules": rows,
                                "reference_params": self.tool.reference_params(it["slot_key"])})
        return out

    # ------------------------------------------------------------ open items (§4.7)
    def score(self, t):
        """The ranking measure of a (possibly re-run) branch tax: total_N ceiling under a horizon, else per_100."""
        if self.horizon is None:
            return t["per_100"]
        tot = ((t.get("one_off_override") or self.one_off_all.get(t["cand_id"]) or {}).get("total") or {})
        if tot.get("floor") is None:
            return {"floor": None, "ceiling": None}
        N = float(self.horizon)
        return {s: r6(tot[s] + N * t["amount"][s]) for s in ("floor", "ceiling")}

    def open_items(self, taxes, ranking, deltas, top_k=None):
        by_b = {t["branch_id"]: t for t in taxes}
        all_ranked = [r for r in ranking if r["rank"] is not None]
        best = all_ranked[0]["branch_id"] if all_ranked else None
        seen_c, ranked = set(), []                           # the best ranked branch of every candidate (not only the top k)
        for r in all_ranked:
            if r["cand_id"] not in seen_c:
                seen_c.add(r["cand_id"]); ranked.append(r)
        needs, hidden = {}, {}
        for r in ranked:
            for n in by_b[r["branch_id"]]["needs"]:
                needs.setdefault(tuple(n), set()).add(r["branch_id"])
            for n in by_b[r["branch_id"]].get("needs_under_assumption", []):
                hidden.setdefault(tuple(n), set()).add(r["branch_id"])
        out = []
        vars_ = {v["name"]: v for v in self.q.variables()}
        preds = {p["key"]: p for p in self.q.predicates()}
        # judgment points that were forked: which answer puts which branch first
        complete = [t for t in taxes if t["complete"] and not t["cand_id"].startswith("x-")]
        forked = sorted({(k, t.get("answers_about", {}).get(k)) for t in complete for k in t["answers_assumed"]})
        for key, node in forked:
            group = [t for t in complete if t.get("answers_about", {}).get(key) == node]
            yes_b = [t for t in group if t["answers_assumed"].get(key) == "yes"]
            no_b = [t for t in group if t["answers_assumed"].get(key) == "no"]
            top = lambda L: min(L, key=lambda t: (self.score(t)["ceiling"] if self.score(t)["ceiling"] is not None else float("inf"), self.score(t)["floor"] or 0, t["branch_id"])) if L else None
            ty, tn = top(yes_b), top(no_b)
            changes = bool(ty and tn and (ty["cand_id"] != tn["cand_id"] or self.score(ty) != self.score(tn)))
            out.append({"kind": "tax", "need": "DISCRETION", "key": key, "about": node, "question": preds.get(key, {}).get("question"),
                        "blocks": sorted(t["branch_id"] for t in yes_b + no_b), "changes_rank": changes,
                        "narrows_best": best is not None and key in by_b[best]["answers_assumed"] and by_b[best].get("answers_about", {}).get(key) == node,
                        "factor_vars": preds.get(key, {}).get("factor_vars", []),
                        "if_yes": ty and {"branch_id": ty["branch_id"], "per_100": ty["per_100"], "score": self.score(ty)}, "if_no": tn and {"branch_id": tn["branch_id"], "per_100": tn["per_100"], "score": self.score(tn)}})
        for (kind, key), blocks in sorted(needs.items()):
            if kind == "DISCRETION":
                continue                                      # handled above through the forks
            q = vars_.get(key, {}).get("question")
            values = self.flip_values(key, vars_.get(key))
            entry = {"kind": "tax", "need": kind, "key": key, "question": q, "blocks": sorted(blocks), "changes_rank": None,
                     "narrows_best": best in blocks, "factor_vars": [], "tried_values": values}
            if values:
                # re-evaluate every affected branch under each value, keep the favourable (lowest ceiling) and unfavourable outcome
                tops = {}
                for label, pick in (("favourable", min), ("unfavourable", max)):
                    per = {}
                    for r in ranked:
                        t = by_b[r["branch_id"]]
                        if r["branch_id"] in blocks:
                            outcomes = [self.score(self.rerun_branch_with(t, key, v)) for v in values]
                            outcomes = [o for o in outcomes if o["ceiling"] is not None] or [self.score(t)]
                            per[r["branch_id"]] = pick(outcomes, key=lambda p: (p["ceiling"], p["floor"]))
                        else:
                            per[r["branch_id"]] = self.score(t)
                    tops[label] = min(per.items(), key=lambda kv: (kv[1]["ceiling"] if kv[1]["ceiling"] is not None else float("inf"), kv[1]["floor"] or 0, kv[0]))
                entry["changes_rank"] = tops["favourable"][0] != tops["unfavourable"][0] or tops["favourable"][1] != tops["unfavourable"][1]
                entry["if_favourable"] = {"branch_id": tops["favourable"][0], "score": tops["favourable"][1]}
                entry["if_unfavourable"] = {"branch_id": tops["unfavourable"][0], "score": tops["unfavourable"][1]}
            out.append(entry)
        for (kind, key), blocks in sorted(hidden.items()):
            if (kind, key) in needs or kind == "DISCRETION":
                continue
            entry = {"kind": "tax", "need": kind, "key": key, "question": vars_.get(key, {}).get("question"), "blocks": sorted(blocks),
                     "changes_rank": None, "narrows_best": best in blocks, "factor_vars": [], "hidden_by_assumption": True,
                     "note": "missing fact whose favourable reading was taken under an assumption (see without_assumptions in the items)"}
            values = self.flip_values(key, vars_.get(key))
            entry["tried_values"] = values
            if values:
                tops = {}
                for label, pick in (("favourable", min), ("unfavourable", max)):
                    per = {}
                    for r in ranked:
                        t = by_b[r["branch_id"]]
                        if r["branch_id"] in blocks:
                            outcomes = [self.score(self.rerun_branch_with(t, key, v)) for v in values]
                            outcomes = [o for o in outcomes if o["ceiling"] is not None] or [self.score(t)]
                            per[r["branch_id"]] = pick(outcomes, key=lambda p: (p["ceiling"], p["floor"]))
                        else:
                            per[r["branch_id"]] = self.score(t)
                    tops[label] = min(per.items(), key=lambda kv: (kv[1]["ceiling"] if kv[1]["ceiling"] is not None else float("inf"), kv[1]["floor"] or 0, kv[0]))
                entry["changes_rank"] = tops["favourable"][0] != tops["unfavourable"][0] or tops["favourable"][1] != tops["unfavourable"][1]
                entry["if_favourable"] = {"branch_id": tops["favourable"][0], "score": tops["favourable"][1]}
                entry["if_unfavourable"] = {"branch_id": tops["unfavourable"][0], "score": tops["unfavourable"][1]}
            out.append(entry)
        tr_needs = {}
        for r in ranked:
            cid = by_b[r["branch_id"]]["cand_id"]
            for tr in (self.one_off_all.get(cid) or {}).get("transfers", []):
                for n in tr.get("needs", []):
                    tr_needs.setdefault((n[0], n[1]), set()).add(r["branch_id"])
        for (kind, key), blocks in sorted(tr_needs.items()):
            if kind == "DISCRETION":
                q = self.pred_row(key)
                values = ["yes", "no"]
            else:
                q = vars_.get(key, {})
                values = self.flip_values(key, q)
            entry = {"kind": "one_off", "need": kind, "key": key, "question": q.get("question"), "blocks": sorted(blocks), "changes_rank": None,
                     "narrows_best": best in blocks, "factor_vars": q.get("factor_vars", []) if kind == "DISCRETION" else [], "tried_values": values,
                     "note": "read by a restructure cell of this candidate's transfers (transfers/<cand_id>.json); enters the ranking only under a horizon (total_N)"}
            if values:
                tops = {}
                for label, pick in (("favourable", min), ("unfavourable", max)):
                    per = {}
                    for r in ranked:
                        t = by_b[r["branch_id"]]
                        if r["branch_id"] in blocks:
                            outcomes = [self.score(self.rerun_branch_with(t, key, v)) for v in values]
                            outcomes = [o for o in outcomes if o["ceiling"] is not None] or [self.score(t)]
                            per[r["branch_id"]] = pick(outcomes, key=lambda p: (p["ceiling"], p["floor"]))
                        else:
                            per[r["branch_id"]] = self.score(t)
                    tops[label] = min(per.items(), key=lambda kv: (kv[1]["ceiling"] if kv[1]["ceiling"] is not None else float("inf"), kv[1]["floor"] or 0, kv[0]))
                entry["changes_rank"] = tops["favourable"][0] != tops["unfavourable"][0] or tops["favourable"][1] != tops["unfavourable"][1]
                entry["if_favourable"] = {"branch_id": tops["favourable"][0], "score": tops["favourable"][1]}
                entry["if_unfavourable"] = {"branch_id": tops["unfavourable"][0], "score": tops["unfavourable"][1]}
            out.append(entry)
        for d in deltas:
            oo = d.get("one_off_cost") or {}
            for fl in oo.get("flags", []):
                if fl in ("valuation_missing", "cost_missing", "holder_unknown", "fx_missing"):
                    out.append({"kind": "one_off", "need": "MISSING", "key": fl, "question": "one-off cost input missing: %s" % fl,
                                "blocks": [d["branch_id"]], "changes_rank": self.horizon is not None, "narrows_best": False, "factor_vars": []})
            ex = d.get("exposure_if_denied") or {}
            if ex:
                for v in ("concealment", "negligence", "voluntary_payment", "return_filed"):
                    out.append({"kind": "exposure", "need": "MISSING", "key": v, "question": vars_.get(v, {}).get("question"),
                                "blocks": [d["branch_id"]], "changes_rank": False, "narrows_best": False, "factor_vars": []})
        # derived facts: decisive inputs the layer inferred, listed for confirmation and re-run with the opposite value
        derived = {}
        for r in ranked:
            t = by_b[r["branch_id"]]
            for eid, d in (t.get("derived_facts") or {}).items():
                for key, info in d.items():
                    derived.setdefault((key, json.dumps(info["value"])), {"info": info, "blocks": set()})["blocks"].add(r["branch_id"])
            for tr in (self.one_off_all.get(t["cand_id"]) or {}).get("transfers", []):   # facts derived for the transfers (item 6(2))
                for key, info in (tr.get("derived") or {}).items():
                    info = dict(info, read_by_rules=sorted(r_["id"] for r_ in self.rs.rules if r_["slot"] == "restructure" and key in leaves_vars(r_)),
                                about=tr["target"], items_ref="transfers/%s.json" % t["cand_id"])
                    derived.setdefault((key, json.dumps(info["value"])), {"info": info, "blocks": set()})["blocks"].add(r["branch_id"])
        for (key, val), d in sorted(derived.items()):
            info = d["info"]
            entry = {"kind": "derived", "need": "DERIVED", "key": key, "value": info["value"], "from": info.get("from"), "cite_id": info.get("cite_id"),
                     "read_by_rules": info.get("read_by_rules", []), "recipient_decisions": info.get("recipient_decisions", []), "cite_ids": info.get("cite_ids", []),
                     "question": vars_.get(key, {}).get("question"), "blocks": sorted(d["blocks"]), "changes_rank": None, "narrows_best": best in d["blocks"],
                     "factor_vars": [], "about": info.get("about"), "items_ref": info.get("items_ref"),
                     "confirm": info.get("confirm", "derived by the optimization layer from the previous hop; confirm with the recipient jurisdiction")}
            if isinstance(info["value"], bool):
                tops = {}
                for label, v in (("as_derived", info["value"]), ("opposite", not info["value"])):
                    per = {}
                    for r in ranked:
                        t = by_b[r["branch_id"]]
                        per[r["branch_id"]] = self.score(self.rerun_branch_with(t, key, v)) if r["branch_id"] in d["blocks"] else self.score(t)
                    tops[label] = min(per.items(), key=lambda kv: (kv[1]["ceiling"] if kv[1]["ceiling"] is not None else float("inf"), kv[1]["floor"] or 0, kv[0]))
                entry["changes_rank"] = tops["as_derived"][0] != tops["opposite"][0] or tops["as_derived"][1] != tops["opposite"][1]
                entry["if_as_derived"] = {"branch_id": tops["as_derived"][0], "score": tops["as_derived"][1]}
                entry["if_opposite"] = {"branch_id": tops["opposite"][0], "score": tops["opposite"][1]}
            out.append(entry)
        # merge duplicates
        merged = {}
        for o in out:
            k = (o["kind"], o["need"], o["key"], o.get("about"), json.dumps(o.get("value")) if o["kind"] == "derived" else None)
            if k in merged:
                merged[k]["blocks"] = sorted(set(merged[k]["blocks"]) | set(o["blocks"]))
                merged[k]["changes_rank"] = merged[k]["changes_rank"] or o["changes_rank"]
                merged[k]["narrows_best"] = merged[k]["narrows_best"] or o["narrows_best"]
            else:
                merged[k] = o
        res = list(merged.values())
        res.sort(key=lambda o: (o["kind"] not in ("tax", "derived"), not o["changes_rank"], not o["narrows_best"], -len(o["blocks"]), o["key"]))
        return res

    def flip_values(self, key, row):
        """Candidate values of a missing variable: bool -> true / false; number -> each threshold a rule compares it with, just
        below and at the threshold; enum -> its allowed values; text -> none."""
        if not row:
            return []
        t = row.get("type")
        if t == "bool":
            return [True, False]
        if t == "enum":
            return split_list(row.get("allowed_values"))
        if t == "text" and key.endswith("_jur"):
            return sorted(j["code"] for j in self.lib.juris)
        if t != "number":
            return []
        vals = set()
        for r in self.rs.rules:
            for node in self._compare_nodes(r["tree"]):
                op, (a, b) = node
                if isinstance(a, dict) and a.get("var") == key:
                    other = b
                elif isinstance(b, dict) and b.get("var") == key:
                    other = a
                else:
                    continue
                try:
                    v = self.rs.pvalue(other["param"]) if isinstance(other, dict) and "param" in other else float(other)
                except (TypeError, ValueError, KeyError):
                    continue
                vals.add(v); vals.add(max(0.0, v - 1)); vals.add(v + 1)
        return sorted(vals)

    @staticmethod
    def _compare_nodes(tree):
        out = []
        if isinstance(tree, dict):
            for k, v in tree.items():
                if k in ("and", "or"):
                    for x in v:
                        out += Optimizer._compare_nodes(x)
                elif k == "not":
                    out += Optimizer._compare_nodes(v)
                elif k in ("=", "!=", "<", "<=", ">", ">=") and isinstance(v, list) and len(v) == 2:
                    out.append((k, v))
        return out

    def rerun_branch_with(self, t, key, value):
        """Tax of a branch with one variable set (plain and entity-prefixed) in every hop."""
        cand = next(c for c in self.cands if c["cand_id"] == t["cand_id"])
        answers = dict(self.answers, **t["answers_assumed"])
        assume = sorted(set(self.assume) | set(t["answers_assumed"]))
        hops = self.candidate_hops(cand, self.graph, answers, assume, override={key: value})
        out = self.branch_tax({"branch_id": t["branch_id"], "cand_id": t["cand_id"], "answers_assumed": t["answers_assumed"], "answers_about": t.get("answers_about", {}), "hops": hops}, cand)
        if key in self.transfer_keys(cand["cand_id"]):      # the variable is read by a transfer: re-run the one-off cost too
            saved, self.transfer_override = getattr(self, "transfer_override", {}), {key: value}
            try:
                out["one_off_override"] = self.one_off(cand, self.transfers(cand, self.graph))
            finally:
                self.transfer_override = saved
        return out

    def pred_row(self, key):
        p = getattr(self.rs, "predicates", {})
        if isinstance(p, dict):
            return p.get(key, {}) or {}
        return next((x for x in p if x.get("key") == key), {})

    def transfer_keys(self, cand_id):
        """Variables and predicates the transfers of a candidate still need, plus the facts the layer derived for them."""
        keys = set()
        for tr in (getattr(self, "transfers_all", {}) or {}).get(cand_id, []):
            keys |= {n[1] for n in tr.get("needs", [])}
            keys |= set((tr.get("derived") or {}).keys())
        return keys

    # ------------------------------------------------------------ gap, version
    def gap(self, graph):
        pairs = sorted({(split_node(e["tail"])[0], split_node(e["head"])[0], split_node(e["head"])[1]) for e in graph["edges"]})
        return {"edges": [{"S": S, "R": R, "subject": s, "gap": self.q.gap(S, R, s)} for S, R, s in pairs],
                "excluded_jurisdictions": sorted({j["code"] for j in self.lib.juris} - {n["jur"] for n in graph["nodes"]}),
                "notes": self.notes}

    def version(self):
        parts = {"facts": sha({"payer": self.payer, "payee": self.payee, "payment": self.payment, "answers": self.answers, "entities": self.entities}),
                 "destinations": sha(self.destinations), "move_csv": hashlib.sha256((HERE.parent / "move.csv").read_bytes()).hexdigest()[:16],
                 "limits": sha(self.limits), "constraints": sha(self.constraints), "fx": sha(self.fx) if self.fx else "",
                 "as_of": sha(self.as_of), "valuation": sha(self.valuation) if self.valuation else "",
                 "horizon_years": sha(self.horizon) if self.horizon is not None else "", "date_mode": sha([self.date, self.mode, self.assume])}
        v = self.q.version()
        return {"inputs_sha256": sha(parts), "inputs": parts, "rule_version": v["rule"], "database_version": v["database"],
                "generated_at": v["generated_at"], "limits": self.limits}

    # ------------------------------------------------------------ run everything
    def run(self, out_dir):
        out = Path(out_dir)
        if out.exists():
            import shutil
            shutil.rmtree(out)
        self.transfer_override = {}
        self.graph = self.build_graph()
        lab, allab = self.labels(self.graph)
        cands = self.paths(lab, allab, self.graph)
        return self.products(out, cands, lab)

    def products(self, out, cands, lab=None, extra_only=False):
        self.cands = cands
        version = self.version()
        branches_all, taxes, requirements = [], [], {}
        transfers_all, one_off_all = {}, {}
        for c in cands:
            hops = self.candidate_hops(c, self.graph)
            self.hops_store["hops/%s.json" % c["cand_id"]] = [h["items"] for h in hops]
            brs = self.fork(c, hops)
            for b in brs:
                self.hops_store["hops/%s.json" % b["branch_id"]] = [h["items"] for h in b["hops"]]
            branches_all += brs
            requirements[c["cand_id"]] = self.requirements(c, hops)
            trs = self.transfers(c, self.graph) if not c["as_is"] else []
            transfers_all[c["cand_id"]] = trs
            self.transfers_all = transfers_all
            self.hops_store["transfers/%s.json" % c["cand_id"]] = [t.get("items", []) for t in trs]
        for b in branches_all:
            c = next(x for x in cands if x["cand_id"] == b["cand_id"])
            taxes.append(self.branch_tax(b, c))
        for c in cands:
            one_off_all[c["cand_id"]] = self.one_off(c, transfers_all[c["cand_id"]])
        self.one_off_all = one_off_all
        c0 = [t for t in taxes if t["cand_id"] == "c0"]
        per_branch = {}
        for t in taxes:
            as_is = next((u for u in c0 if all(u["answers_assumed"].get(k, v) == v for k, v in t["answers_assumed"].items())), c0[0] if c0 else None)
            per_branch[t["branch_id"]] = self.branch_one_off(t, as_is, one_off_all.get(t["cand_id"]))
        ranking = self.rank(taxes, cands, one_off_all, per_branch)
        exposure = self.exposure(branches_all, taxes)
        deltas = self.deltas(taxes, ranking, one_off_all, exposure, per_branch)
        open_items = self.open_items(taxes, ranking, deltas)
        # ---- write
        if lab is not None:
            jdump(dict(version=version["inputs_sha256"], **self.graph), out / "graph.json")
            jdump({"version": version["inputs_sha256"], "labels": lab["labels"], "frontier": lab["frontier"], "truncated": lab["truncated"]}, out / "labels.json")
        jdump({"version": version["inputs_sha256"], "candidates": cands}, out / "paths.json")
        jdump({"version": version["inputs_sha256"], "branches": [{k: v for k, v in b.items() if k != "hops"} | {"hops_ref": "hops/%s.json" % b["branch_id"]} for b in branches_all]}, out / "branches.json")
        jdump({"version": version["inputs_sha256"], "amount": self.amount, "currency": self.currency, "taxes": taxes}, out / "tax.json")
        jdump({"version": version["inputs_sha256"], "key": "total_N" if self.horizon is not None else "per_100", "ranking": ranking}, out / "ranking.json")
        jdump({"version": version["inputs_sha256"], "deltas": deltas}, out / "deltas.json")
        jdump({"version": version["inputs_sha256"], "score_key": "total_N" if self.horizon is not None else "per_100", "open_items": open_items}, out / "open_items.json")
        jdump(dict(version=version["inputs_sha256"], **self.gap(self.graph)), out / "gap.json")
        if self.fx:
            jdump(self.fx, out / "fx.json")
        for cid, req in requirements.items():
            jdump({"version": version["inputs_sha256"], "cand_id": cid, "requirements": req}, out / "requirements" / ("%s.json" % cid))
        for ref, items in self.hops_store.items():
            jdump({"version": version["inputs_sha256"], "items": items}, out / ref)
        if lab is not None:
            jdump(dict(version=version["inputs_sha256"], **self.brief(cands, taxes, ranking, deltas, open_items)), out / "brief.json")
        if lab is not None and self.inp.get("past_payments"):
            jdump({"version": version["inputs_sha256"], "past_payments": [self.past_payment(r) for r in self.inp["past_payments"]]}, out / "past_payments.json")
        jdump(version, out / "version.json")
        jdump(self.inp, out / "input.json")
        return {"candidates": len(cands), "branches": len(branches_all), "ranked": sum(1 for r in ranking if r["rank"]), "out": str(out)}

    # ------------------------------------------------------------ evaluate a requested path (§4.10)
    def evaluate(self, out_dir, path_nodes, moves=None):
        out = Path(out_dir)
        self.graph = jload(out / "graph.json")
        self.graph.pop("version", None)
        edge_by = {(e["tail"], e["head"], tuple(e["moves"])): e for e in self.graph["edges"]}
        edges = []
        for a, b in zip(path_nodes, path_nodes[1:]):
            e = edge_by.get((a, b, tuple(moves or [])))
            if e is None:
                e = edge_by.get((a, b, ()))
            if e is None:
                raise SystemExit("no edge %s -> %s in the graph (jurisdiction not covered or excluded)" % (a, b))
            edges.append(e["edge_id"])
        paths = jload(out / "paths.json")
        existing = [c for c in paths["candidates"] if c.get("requested")]
        cand = {"cand_id": "x-%d" % (len(existing) + 1), "path": path_nodes, "edges": edges, "moves": moves or [],
                "restructure": [], "path_complete": path_nodes[-1] in self.destinations,
                "as_is": False, "requested": True, "label": None}
        cand["restructure"] = sorted({t["kind"] for t in self.transfers(cand, self.graph)})
        cands = paths["candidates"] + [cand]
        return self.products(out, cands)


# ---------------------------------------------------------------- diff (§4.10)
def diff(products, against):
    a, b = Path(products), Path(against)
    ra, rb = jload(a / "ranking.json"), jload(b / "ranking.json")
    ta = {t["branch_id"]: t for t in jload(a / "tax.json")["taxes"]}
    tb = {t["branch_id"]: t for t in jload(b / "tax.json")["taxes"]}
    va, vb = jload(a / "version.json"), jload(b / "version.json")
    rank_a = {r["branch_id"]: r["rank"] for r in ra["ranking"]}
    rank_b = {r["branch_id"]: r["rank"] for r in rb["ranking"]}
    out = {"products": str(a), "against": str(b), "incomparable": [], "rank_moves": [], "interval_changes": [], "open_item_changes": {},
           "inputs_changed": sorted(k for k in set(va["inputs"]) | set(vb["inputs"]) if va["inputs"].get(k) != vb["inputs"].get(k))}
    if va["rule_version"].get("rule_csv_sha256") != vb["rule_version"].get("rule_csv_sha256"):
        out["incomparable"].append("rule layer version differs")
    if va["inputs"].get("move_csv") != vb["inputs"].get("move_csv"):
        out["incomparable"].append("move.csv differs")
    for bid in sorted(set(rank_a) | set(rank_b)):
        if rank_a.get(bid) != rank_b.get(bid):
            out["rank_moves"].append({"branch_id": bid, "before": rank_b.get(bid, "absent" if bid not in rank_b else None), "after": rank_a.get(bid, "absent" if bid not in rank_a else None)})
    for bid in sorted(set(ta) & set(tb)):
        if ta[bid]["per_100"] != tb[bid]["per_100"]:
            out["interval_changes"].append({"branch_id": bid, "before": tb[bid]["per_100"], "after": ta[bid]["per_100"]})
    oa = {(o["kind"], o["key"]): o for o in jload(a / "open_items.json")["open_items"]}
    ob = {(o["kind"], o["key"]): o for o in jload(b / "open_items.json")["open_items"]}
    out["open_item_changes"] = {"new": sorted("%s:%s" % k for k in set(oa) - set(ob)), "gone": sorted("%s:%s" % k for k in set(ob) - set(oa)),
                                "changed": sorted("%s:%s" % k for k in set(oa) & set(ob) if (oa[k]["changes_rank"], oa[k]["narrows_best"]) != (ob[k]["changes_rank"], ob[k]["narrows_best"]))}
    jdump(out, a / "diff.json")
    return out


# ---------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("command", choices=("run", "evaluate", "requirements", "diff", "version"))
    ap.add_argument("--input", help="case input JSON (run)")
    ap.add_argument("--out", help="products directory (run)")
    ap.add_argument("--products", help="existing products directory (evaluate / requirements / diff)")
    ap.add_argument("--path", help="evaluate: 'jur:subject;jur:subject;…'")
    ap.add_argument("--moves", default="", help="evaluate: moves of the last hop, ';'-separated, as in graph.json")
    ap.add_argument("--against", help="diff: the other products directory")
    a = ap.parse_args()
    if a.command == "version":
        print(json.dumps(Query().version(), ensure_ascii=False, indent=1)); return 0
    if a.command == "run":
        inp = jload(a.input)
        opt = Optimizer(inp)
        print(json.dumps(opt.run(a.out), ensure_ascii=False)); return 0
    if a.command == "diff":
        print(json.dumps(diff(a.products, a.against), ensure_ascii=False, indent=1)); return 0
    inp = jload(Path(a.products) / "input.json")
    opt = Optimizer(inp)
    if a.command == "evaluate":
        nodes = [p.strip() for p in a.path.split(";") if p.strip()]
        print(json.dumps(opt.evaluate(a.products, nodes, [m for m in a.moves.split(";") if m]), ensure_ascii=False)); return 0
    if a.command == "requirements":
        opt.graph = jload(Path(a.products) / "graph.json")
        paths = jload(Path(a.products) / "paths.json")
        for c in paths["candidates"]:
            hops = opt.candidate_hops(c, opt.graph)
            jdump({"cand_id": c["cand_id"], "requirements": opt.requirements(c, hops)}, Path(a.products) / "requirements" / ("%s.json" % c["cand_id"]))
        print("requirements written for %d candidates" % len(paths["candidates"])); return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
