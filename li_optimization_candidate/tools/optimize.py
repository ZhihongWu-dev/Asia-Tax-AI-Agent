#!/usr/bin/env python
"""Optimization layer (优化层规范.md): a read-only shovel that turns one dividend background into products on disk.

  python optimization/tools/optimize.py run --input <case.json> --out products/<case>/
  python optimization/tools/optimize.py evaluate --products products/<case>/ --path 'cn:company;jp:company;sg:individual' [--moves holding_pct=100]
  python optimization/tools/optimize.py requirements --products products/<case>/
  python optimization/tools/optimize.py diff --products products/<case>/ --against products/<case>-v1/
  python optimization/tools/optimize.py version

The input file (JSON) holds everything §3 lists: facts (payment, payer, payee), answers, assume, destinations, date,
mode, amount, currency, limits, constraints, as_of, fx (path or object), valuation, entities (known
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
FAV_EFFECTS = ("cap", "exempt", "share", "exclude", "credit", "credit_underlying")
SIDES = ("floor", "ceiling")
DEFAULT_LIMITS = {"max_hops": 3, "max_moves": 3, "max_labels": 50, "max_fork_keys": 3}
FORK_ROUNDS = 3
# A plan's own conduct when an assumed treatment is later denied (spec 4.7, exposure): the claim was reported as the rules
# require, nothing concealed, no negligence, the return filed. Heavier cases need facts a plan does not make; rule/decision.csv D-cn-9.
PLAN_CONDUCT = {"claim_reported": True, "concealment": False, "negligence": False, "return_filed": True}
JUR_FACTS = ("incorporated_in", "managed_in", "domicile_in", "parent_jur", "payer_jur")
BRIEF_ROWS = 8
FLAG_QUESTIONS = {                                         # one-off inputs, asked as a client would understand them
    "valuation_missing": "What are the latest audited net assets (owners' equity) of {company}, or an appraised value of its shares, and in which currency?",
    "cost_missing": "What did {holder} pay for its shares in {company}, and in which currency?",
    "holder_unknown": "Who holds the shares of {company} today (the shareholder register)?",
    "fx_missing": "An exchange rate for the one-off cost is missing (fx.json); not a question for the client.",
    "exit_inputs_missing": "What is the value of the securities the individual holds at the time of moving, and what did they cost (in the currency of the jurisdiction left)?",
    "exit_person_unknown": "Which of the known individuals would move?"}
TERMS = {                                                  # the words of the products, for whoever writes from them
    "structure": "a candidate: a holding path from the paying company to a destination, with the share transfers or moves it needs; c0 is the as-is structure",
    "scenario": "one set of answers to the judgment points, the same for every structure: all favourable, one point against the client, all against",
    "branch": "the tax of one structure under one scenario",
    "range": "floor and ceiling of one branch, from facts not known and progressive tables; not the spread over scenarios",
    "worst case": "the all_unfavourable scenario",
    "point": "a judgment point key@jur: the predicate and the jurisdiction whose authority decides it; about = whom it is asked of"}
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


def base_key(key):
    """bo@cn -> bo: the predicate of a judgment point, without the jurisdiction that decides it (§4.6)."""
    return str(key).split("@", 1)[0]


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
        self.constraints = dict({"exclude": [], "consider": None, "allow_restructure": True, "payback_max": None, "allowed_subjects": None},
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
        for k in ("exclude", "consider"):                 # jurisdictions the client names, as the library writes them
            if self.constraints.get(k):
                self.constraints[k] = [code(j, "constraints." + k) for j in self.constraints[k]]

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

    def fav(self, key):
        """The favourable answer of a judgment point, qualified (bo@cn) or not."""
        return self.favourable.get(base_key(key), "yes")

    def unfavourable(self, key):
        return "no" if self.fav(key) == "yes" else "yes"

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

    def considered(self):
        """The jurisdictions the client asked to consider, plus those the structure already stands on (payer, payee,
        destinations, known entities): a choice never removes the facts of the case."""
        keep = set(self.constraints.get("consider") or [])
        keep |= {split_node(n)[0] for n in [self.source, self.payee_node] + list(self.destinations) + list(self.entities)}
        return keep

    def nodes(self):
        out = []
        for j in self.lib.juris:
            jur = j["code"]
            if jur in self.constraints["exclude"]:
                continue
            if self.constraints.get("consider") and jur not in self.considered():
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
                facts["holding_months"] = 0                                  # by a transfer now: the as-is holder's months do not pass to it
            elif head in self.entities and self.entities[head].get("holds") == tail:
                facts["holding_pct"] = self.entities[head].get("holding_pct")
                facts["holding_months"] = self.entities[head].get("holding_months")
            elif t_new or h_new:
                facts["holding_pct"] = 100
                facts["holding_months"] = 0
            else:
                facts["holding_months"] = 0                                  # an existing company that takes over a stake it does not hold today
        RES_KEYS = ("incorporated_in", "managed_in", "domicile_in", "days_present", "listed")
        for k, v in t_f.items():
            facts["payer." + k] = v
        if tail != self.source:
            for k in ("payer_etr", "specified_cfc"):         # the tail pays this hop: its own tax burden and CFC status
                if k in t_f:
                    facts[k] = t_f[k]
        as_is = tail == self.source and head == self.payee_node
        for k, v in h_f.items():
            facts["payee." + k] = v
            if k in ("holding_pct", "holding_months") and not as_is:
                continue                                      # the payee's as-is stake is not its stake in a new tail
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

    def gross_up(self, jur):
        """The library says the dividend is grossed up by its underlying tax before the credit (<jur>.inbound.underlying_gross_up)."""
        p = self.lib.params.get("%s.inbound.underlying_gross_up" % jur)
        return bool(p) and str(p["value"]).strip().lower() in ("yes", "true", "1")

    def source_prior(self, facts):
        """Share of the source company's profit taken by its own income tax (payer_etr, else payer_tax_rate): the tax a
        recipient with an underlying credit may credit at the first tier. None when neither is given."""
        for k in ("payer_etr", "payer_tax_rate"):
            v = (facts or {}).get(k)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                return {s: min(max(float(v) / 100.0, 0.0), 0.99) for s in SIDES}
        return None

    def hop_tax(self, items, prior=None, retention=False, prior_own=None):
        """§4.5: the rate components of one hop from its items, both sides. `prior` (per side, 0-1): the share of the
        income's gross taken by taxes before this hop that the recipient's jurisdiction may credit as underlying tax (its
        own taxes left out); None when not known (edge level): then only the tax on this hop is credited. `retention`: the
        pseudo-hop of money that stays in a destination company (only its cfc cell, nothing paid). `prior_own`: the share
        taken by the taxes the payer itself bore on this income (the previous hop), for a CFC credit limited to them."""
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
            elif retention:
                pass
            elif o is None or o["status"] == "absent" or o[side]["value"] is None:
                ab = self.absence(o["jur"], o["subject"], "outbound_wht") if o else None
                notes.append("outbound_wht absent -> 0; %s" % json.dumps(ab, ensure_ascii=False) if ab else "outbound_wht absent or None -> 0")
            incl = i[side]["value"] if i and i["status"] != "absent" and i[side]["value"] is not None else 0.0
            if domestic:
                incl = 100.0                                  # a domestic dividend is not foreign income: the final cell alone taxes it
            rate = fnl[side]["value"] if fnl and fnl["status"] != "absent" and fnl[side]["value"] is not None else 0.0
            exempt_final = bool(fnl) and fnl["status"] != "absent" and (fnl[side].get("included") == 0)     # exempt: no rate needed
            absent_final = bool(fnl) and fnl["status"] == "absent" and bool(self.absence(fnl["jur"], fnl["subject"], "final"))
            missing = (fnl is None or fnl["status"] == "absent" or fnl[side]["value"] is None) and incl > 0 and not (exempt_final or absent_final)
            if retention:
                pass
            elif missing:
                notes.append("final None with inbound inclusion > 0: value_missing")
            elif fnl is None or fnl["status"] == "absent" or fnl[side]["value"] is None:
                ab = self.absence(fnl["jur"], fnl["subject"], "final") if fnl else None
                notes.append("final absent or None -> 0 (nothing included); %s" % json.dumps(ab, ensure_ascii=False) if ab else "final absent or None -> 0 (nothing included)")
            if i is not None and i["status"] == "absent":
                ab = self.absence(i["jur"], i["subject"], "inbound")
                notes.append("inbound absent -> 0 included; %s" % json.dumps(ab, ensure_ascii=False) if ab else "inbound absent -> 0 included")
            s = min(max((prior or {}).get(side) or 0.0, 0.0), 0.99)
            u = s / (1 - s)                                   # underlying tax per unit of dividend
            cd = bool(i and i[side].get("credit"))
            cu = bool(i and i[side].get("credit_underlying")) and u > 0
            base = 100.0 * (1 + u) if (cu and self.gross_up(i["jur"])) else 100.0
            res = incl / 100.0 * rate * base / 100.0
            credit = min(res, (wht if cd else 0.0) + (100.0 * u if cu else 0.0)) if (cd or cu) else 0.0
            if cu and res:
                notes.append("underlying tax credited: %s%% of the gross borne before this hop%s" % (r6(100 * s), ", dividend grossed up" if base > 100 else ""))
            t = (wht + res - credit) / 100.0
            out[side] = {"wht": r6(wht), "incl": r6(incl), "rate": r6(rate), "res": r6(res), "credit": r6(credit), "t": r6(t),
                         "w": None if t >= 1 else r6(-math.log(1 - t)), "value_missing": missing, "notes": notes,
                         "underlying": r6(100.0 * u if cu else 0.0), "cfc_inclusion": None}
        cfc = by.get("cfc")
        payer_home = "outbound_wht" in by and cfc is not None and by["outbound_wht"]["jur"] == cfc["jur"]
        out["cfc_flag"] = bool(cfc and cfc["status"] != "absent" and cfc["ceiling"]["value"] and not payer_home)   # CFC rules reach foreign companies only
        if out["cfc_flag"]:
            self.cfc_inclusion(out, cfc, prior if cfc["ceiling"].get("credit_underlying") else prior_own)
        out["needs"] = sorted({tuple(n) for it in items for n in it.get("needs", [])})
        out["needs_under_assumption"] = sorted({tuple(n) for it in items for n in (it.get("without_assumptions") or {}).get("needs", []) if tuple(n) not in set(out["needs"])})
        return out

    def cfc_inclusion(self, out, cfc, prior):
        """§4.5: the recipient's jurisdiction includes the payer's profit (the dividend of this hop is that profit, paid
        out in full and later excluded). With a credit (and gross-up) the burden from the profit's gross becomes the
        higher of the recipient's rate and the tax already borne; without one the rate falls on the payer's after-tax
        profit on top of this hop's withholding. A pending inclusion is the ceiling only."""
        rc, cc = cfc["ceiling"].get("rate"), cfc["ceiling"].get("credit")
        if rc is None:
            for side in SIDES:
                out[side]["notes"].append("CFC inclusion by %s with no rate in the library: not computed" % cfc["jur"])
            return
        inc = {}
        for side in SIDES:
            on = bool(cfc[side]["value"])
            r = (cfc[side].get("rate") if on else rc) / 100.0
            cr = cfc[side].get("credit") if on else cc
            w = out[side]["wht"] / 100.0
            s = min(max((prior or {}).get(side) or 0.0, 0.0), 0.99)
            inc[side] = max(w, (r - s) / (1 - s)) if cr else min(w + r, 0.999999)
        normal = {side: out[side]["t"] for side in SIDES}
        if cfc["status"] == "T" or cfc["floor"]["value"]:
            new = inc
        else:
            new = {"floor": min(normal["floor"], inc["floor"]), "ceiling": max(normal["ceiling"], inc["ceiling"])}
        for side in SIDES:
            t = new[side]
            out[side].update(t=r6(t), w=None if t >= 1 else r6(-math.log(1 - t)), cfc_inclusion=r6(100 * inc[side]))
            out[side]["notes"].append("CFC: %s includes the payer's profit at %s%%%s; hop rate with inclusion %s%%"
                                      % (cfc["jur"], r6(100 * ((cfc[side].get("rate") or rc) / 100.0)), " with credit" if cc else ", no credit", r6(100 * inc[side])))

    def retention_hop(self, d, keep_by, answers=None, assume=None, last_t=None):
        """§4.5: money that stays in destination company d whose known shareholder's jurisdiction attributes d's profit
        to it (CFC). A pseudo-hop d -> shareholder carrying only that cfc cell; nothing is paid on it."""
        if not d or split_node(d)[1] != "company":
            return None
        holder = next((n for n, x in self.entities.items() if x.get("holds") == d), None)
        if not holder:
            return None
        hj, hs = split_node(holder)
        dj = split_node(d)[0]
        if hj == dj or not any(r["jur"] == hj and r["slot"] == "cfc" and r["subject"] in (hs, "all") for r in self.rs.rules):
            return None                                       # CFC rules reach foreign companies only
        dfacts, _ = self.entity_facts(d, [])
        hfacts, _ = self.entity_facts(holder, [])
        pct = self.entities[holder].get("holding_pct")
        facts = dict(hfacts)
        facts.update({"holding_pct": pct, "resident_holding_pct": pct, "payer_jur": dj})
        for k in ("payer_etr", "specified_cfc"):
            if k in dfacts:
                facts[k] = dfacts[k]
        cit, share = self.lib.params.get("cn.final.cit_rate"), self.lib.params.get("cn.cfc.low_tax_rate_share_max")
        if isinstance(facts.get("payer_etr"), (int, float)) and cit and share:
            facts["payer_low_tax"] = float(facts["payer_etr"]) < float(cit["value"]) * float(share["value"]) / 100
        if hs == "individual":
            ccy = self.jur_ccy(hj)
            rate = self.fx_rate(ccy)
            if rate:
                keep = math.prod(v["ceiling"] for v in keep_by.values()) if keep_by else 1.0
                facts["amount_payee_ccy"] = self.amount * keep * rate
        facts = {k: v for k, v in facts.items() if v is not None}
        item = ev.eval_cell(self.rs, "%s|%s|cfc|*" % (hj, hs), self.date, facts, answers if answers is not None else self.answers,
                            self.mode, assume=assume if assume is not None else self.assume)
        item = strip_items([item])[0]
        if item["status"] == "absent" or not item["ceiling"]["value"]:
            return None
        prior = {s: 1 - math.prod(v[s] for j, v in keep_by.items() if j != hj) for s in SIDES} if keep_by else None
        tx = self.hop_tax([item], prior, retention=True, prior_own=last_t)
        tx["path_notes"] = ["money stays in %s; %s attributes its profit to %s (CFC)" % (d, hj, holder)]
        tx["derived"] = {}
        tx["prior"], tx["prior_own"] = prior, last_t
        return {"edge_id": "keep:%s" % d, "tail": d, "head": holder, "about": d, "items": [item], "tax": tx, "extra_facts": facts,
                "derived": {}, "retention": True}

    def relocation(self, cand):
        """§4.7: an individual destination in a jurisdiction where the known individual does not live: that person moves."""
        last = cand["path"][-1] if cand.get("path") else None
        if not last or split_node(last)[1] != "individual" or last in self.entities or last == self.payee_node:
            return None
        people = [n for n in self.entities if split_node(n)[1] == "individual"]
        if split_node(self.payee_node)[1] == "individual":
            people.append(self.payee_node)
        if len(people) != 1:
            return {"to": last, "from": None, "person": None, "note": "%d known individuals: which one moves is not determined" % len(people)}
        p = people[0]
        if split_node(p)[0] == split_node(last)[0]:
            return None
        return {"to": last, "from": split_node(p)[0], "person": p}

    def exit_cost(self, reloc):
        """§4.7: the exit tax of the jurisdiction the person leaves (cell <jur>|individual|exit|*), on the gain
        exit_assets_value - exit_assets_cost of that person's facts, in the payment currency."""
        row = {"kind": "exit", "target": None, "transferor": reloc.get("person"), "transferee": reloc["to"], "pct": None,
               "from": reloc.get("from"), "needs": [], "derived": {}, "items": []}
        flags = set()
        p, cj = reloc.get("person"), reloc.get("from")
        if not p:
            row["note"] = reloc.get("note")
            return row, {"exit_person_unknown"}
        facts = dict((self.entities.get(p) or {}).get("facts") or {}) if p in self.entities else dict(self.payee.get("facts") or {})
        if not any(r["jur"] == cj and r["slot"] == "exit" for r in self.rs.rules):
            ab = self.absence(cj, "individual", "exit")
            row.update(rate={"floor": 0.0, "ceiling": 0.0}, in_payment_currency={"floor": 0.0, "ceiling": 0.0}, absence=ab)
            if not ab:
                row["in_payment_currency"] = None
                row["note"] = "no exit rules and no absence record for %s" % cj
                flags.add("exit_slot_missing")
            return row, flags
        item = strip_items([ev.eval_cell(self.rs, "%s|individual|exit|*" % cj, self.date, facts, self.answers, self.mode)])[0]
        row["items"] = [item]
        row["needs"] = [list(n) for n in item["needs"]]
        rate = {s: item[s]["value"] or 0.0 for s in SIDES}
        row["rate"] = rate
        if not rate["ceiling"]:
            row["in_payment_currency"] = {"floor": 0.0, "ceiling": 0.0}
            return row, flags
        value, cost = facts.get("exit_assets_value"), facts.get("exit_assets_cost")
        if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (value, cost)):
            row["in_payment_currency"] = None
            row["note"] = "exit_assets_value and exit_assets_cost of %s are needed for the gain" % p
            return row, flags | {"exit_inputs_missing"}
        ccy = self.jur_ccy(cj)
        fxr = self.fx_rate(ccy)
        gain = max(float(value) - float(cost), 0.0)
        local = {s: gain * rate[s] / 100 for s in SIDES}
        row.update(currency=ccy, gain=r6(gain), tax=local and {s: r6(local[s]) for s in SIDES},
                   in_payment_currency=None if not fxr else {s: r6(local[s] / fxr) for s in SIDES})
        if not fxr:
            flags.add("fx_missing")
        return row, flags

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
                    sp_ = self.source_prior(facts) if tail == self.source else None
                    tx = self.hop_tax(items, sp_, prior_own=sp_)
                    inb = next((it for it in items if it["slot"] == "inbound"), None)
                    cfc = next((it for it in items if it["slot"] == "cfc"), None)
                    prior_dep = tail != self.source and bool(
                        (inb and any(inb[s].get("credit_underlying") for s in SIDES))
                        or (cfc and cfc["status"] != "absent" and cfc["ceiling"]["value"] and cfc["ceiling"].get("credit")))
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
                                  "needs": [list(n) for n in tx["needs"]], "amount_dependent": hj_subject_sched, "prior_dependent": prior_dep,
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
                if split_node(e["head"])[1] == "individual" and e["head"] not in self.destinations:
                    continue                                  # an individual pays nothing onward: a dead end unless it is a destination
                hops = L["hops"] + 1
                moves = L["moves"] + len(e["moves"])
                if hops > self.limits["max_hops"] or moves > self.limits["max_moves"]:
                    continue
                ew = e["w"]
                if e["amount_dependent"] or e.get("prior_dependent"):
                    ew = self.path_weight(e, L)
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
                    bucket.sort(key=lambda m: (m["w"]["floor"], m["w"]["ceiling"], m["label_id"]))
                    for M in bucket[self.limits["max_labels"]:]:
                        M["_dead"] = True
                    del bucket[self.limits["max_labels"]:]
                    truncated.add(e["head"])
                allab[Lp["label_id"]] = Lp
                heapq.heappush(openq, (Lp["w"]["floor"], Lp["w"]["ceiling"], Lp["label_id"]))
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

    def path_weight(self, e, L):
        """§4.1, §4.5: an edge whose weight depends on the path: a schedule reads the amount the label delivers; an
        underlying or CFC credit reads the tax borne before this hop (the source company's own tax and the label's
        weight; whoever levied it, which candidate_hops then makes exact)."""
        hj, hs = split_node(e["head"])
        ccy = next((j["currency"] for j in self.lib.juris if j["code"] == hj), None)
        rate = self.fx_rate(ccy)                              # 1 when the recipient uses the payment currency
        extra = {}
        other = (self.payee.get("facts") or {}).get("other_taxable_income") if e["head"] == self.payee_node else \
            (self.entities.get(e["head"], {}).get("facts") or {}).get("other_taxable_income")
        if other is not None:
            extra["payee.other_taxable_income"] = other
        out = {}
        src = self.source_prior(self.payment) or {s: 0.0 for s in SIDES}
        prior = {s: 1 - (1 - src[s]) * math.exp(-L["w"][s]) for s in SIDES} if e.get("prior_dependent") else None
        own = ({s: 1 - math.exp(-(L.get("edge_w") or {}).get(s, 0.0)) for s in SIDES} if L.get("edge") else src) if e.get("prior_dependent") else None
        for side in ("floor", "ceiling"):
            ex = dict(extra)
            if rate and e["amount_dependent"]:
                ex["payee.amount_payee_ccy"] = self.amount * math.exp(-L["w"][side]) * rate
            items = self.eval_hop(e["tail"], e["head"], e["hop_facts"], e["mode"], extra_payee=ex)
            tx = self.hop_tax(items, prior, prior_own=own)
            if tx[side]["w"] is None:
                return None
            out[side] = tx[side]["w"]
            if e["amount_dependent"]:                         # the items change with the amount only
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
                c["restructure"] = sorted({t["kind"] for t in self.transfers(c, graph) if t["kind"] != "unknown_holder"} | {"holder_unknown" for t in self.transfers(c, graph) if t["kind"] == "unknown_holder"}
                                          | ({"relocate"} if self.relocation(c) else set()))
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

    def holder_of(self, n, path):
        """Who holds node n on this path: the next node when the path goes on from n, else the known entity that holds
        it. Returns (holder, holding_pct, holding_months, new) or None."""
        if n in path and path.index(n) + 1 < len(path):
            nxt = path[path.index(n) + 1]
            e = self.entities.get(nxt) or {}
            if e.get("holds") == n:
                return nxt, e.get("holding_pct"), e.get("holding_months"), False
            return nxt, 100, 0, True                      # a holding the structure creates now: no months yet
        for k, e in self.entities.items():
            if e.get("holds") == n:
                return k, e.get("holding_pct"), e.get("holding_months"), False
        return None

    def residence_of(self, n):
        f, _ = self.entity_facts(n, [])
        j, s_ = split_node(n)
        return (f.get("domicile_in") if s_ == "individual" else f.get("managed_in") or f.get("incorporated_in")) or j

    def owner_safe_harbour(self, head, path):
        """STA 2018 No. 9 item 4(4) with item 5 (rule/decision.csv D-cn-5): the payee held 100%, directly or indirectly,
        throughout the 12 months before the dividend, by the government, a listed company or resident individuals of its own
        jurisdiction, any intermediate holder resident in the source jurisdiction or the payee's. True / False / None."""
        R = split_node(head)[0]
        S = split_node(self.source)[0]
        months_min = float((self.lib.params.get("cn.outbound_wht.bo_safe_harbour_holding_months_min") or {}).get("value") or 12)
        n, seen = head, set()
        while n not in seen:
            seen.add(n)
            h = self.holder_of(n, path)
            if h is None:
                return False if n != head else None       # nobody known above the payee: the safe harbour is not shown
            holder, pct, months, _ = h
            if pct is None or months is None:
                return None
            if float(pct) < 100 or float(months) < months_min:
                return False
            hj, hs = split_node(holder)
            f, _ = self.entity_facts(holder, path)
            res = self.residence_of(holder)
            if hs == "individual":
                return res == R
            if f.get("payee_is_government") or f.get("listed") or f.get("payee_listed_in_partner"):
                return res == R
            if res not in (S, R):
                return False
            n = holder
        return None

    def passes_on(self, head, path):
        """Item 2(1) of STA 2018 No. 9: on a candidate the dividend is paid on in full; when the next holder is resident in a
        third jurisdiction, the payee passes it on within the year by the structure itself (a payment fact). None otherwise."""
        if head not in path or path.index(head) + 1 >= len(path):
            return None
        nxt = path[path.index(head) + 1]
        third = self.residence_of(nxt) not in (split_node(self.source)[0], self.residence_of(head))
        return True if third else None

    def candidate_hops(self, cand, graph, answers=None, assume=None, override=None):
        edge_by_id = {e["edge_id"]: e for e in graph["edges"]}
        hops = []
        w_acc = 0.0
        new_holder = self.holder_change(cand["path"])
        prev_items = None
        sp = self.source_prior(self.payment)
        keep_by = {split_node(self.source)[0]: {s: 1 - sp[s] for s in SIDES}} if sp else {}   # what each jurisdiction left of the gross
        for idx, eid in enumerate(cand["edges"]):
            e = edge_by_id[eid]
            extra = {}
            derived = {}
            path_notes = []
            if new_holder and e["head"] == self.payee_node:        # the payee's parent changes downstream: its parent facts no longer hold upstream
                nj, _ = split_node(new_holder)
                extra.update({"parent_jur": nj, "parent_holding_pct": 100, "parent_holding_months": 0, "parent_treaty_not_worse": None,
                              "payee.parent_jur": nj, "payee.parent_holding_pct": 100, "payee.parent_holding_months": 0, "payee.parent_treaty_not_worse": None})
                path_notes.append("payee holder changes to %s on this path: parent safe-harbour facts replaced (label weight may be optimistic)" % new_holder)
            hd = e["head"]
            if split_node(hd)[1] == "company" and "owner_safe_harbour" not in e["hop_facts"]:
                osh = self.owner_safe_harbour(hd, cand["path"])
                if osh is not None:
                    extra["owner_safe_harbour"] = osh
                    extra["payee.owner_safe_harbour"] = osh
                    derived["owner_safe_harbour"] = {"value": osh, "from": "holding chain above %s on this structure (entities and path)" % hd,
                                                     "confirm": "STA 2018 No. 9 item 4(4) and item 5: the 100% holding, its holders' residence and the 12 months"}
                    path_notes.append("owner_safe_harbour=%s derived from the holding chain" % osh)
            if not cand.get("as_is") and not any(str(m).startswith("remit") for m in cand.get("moves") or []):
                po = self.passes_on(hd, cand["path"])
                if po:
                    extra["passes_on_within_12m"] = True
                    extra["payee.passes_on_within_12m"] = True
                    derived["passes_on_within_12m"] = {"value": True, "from": "this structure pays the dividend on from %s to %s, resident in a third jurisdiction" % (hd, cand["path"][cand["path"].index(hd) + 1]),
                                                       "confirm": "item 2(1) of STA 2018 No. 9 counts a payment fact as an obligation; the client's statement covers the structure as it is"}
                    path_notes.append("passes_on_within_12m=true: the structure itself pays the dividend on to a third jurisdiction")
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
                rate = self.fx_rate(ccy)                              # 1 when the recipient uses the payment currency
                if rate:
                    extra["payee.amount_payee_ccy"] = self.amount * math.exp(-w_acc) * rate
                oth = (self.payee.get("facts") or {}).get("other_taxable_income") if e["head"] == self.payee_node else None
                if oth is not None:
                    extra["payee.other_taxable_income"] = oth
            if "tiers" not in e["hop_facts"]:
                extra["tiers"] = idx + 1                            # the payer is tier 1; the underlying tax goes down to the source
            if override:
                for k, v in override.items():
                    extra[k] = v; extra["payer." + k] = v; extra["payee." + k] = v
            extra = {k: v for k, v in extra.items() if v is not None} | {k: "" for k, v in extra.items() if v is None}
            items = self.eval_hop(e["tail"], e["head"], e["hop_facts"], e["mode"], answers, assume, extra or None)
            hj_ = split_node(e["head"])[0]
            prior = {s: 1 - math.prod(v[s] for j, v in keep_by.items() if j != hj_) for s in SIDES} if keep_by else None
            own = sp if idx == 0 else ({s: hops[-1]["tax"][s]["t"] for s in SIDES} if hops else None)   # the payer's own taxes on this income
            tx = self.hop_tax(items, prior, prior_own=own)
            tx["prior"], tx["prior_own"] = prior, own
            tj_ = split_node(e["tail"])[0]
            for s in SIDES:
                w_, t_ = tx[s]["wht"] / 100.0, tx[s]["t"]
                keep_by.setdefault(tj_, {x: 1.0 for x in SIDES})[s] *= (1 - w_)
                keep_by.setdefault(hj_, {x: 1.0 for x in SIDES})[s] *= (1 - (t_ - w_) / (1 - w_)) if w_ < 1 else 0.0
            tx["path_notes"] = path_notes
            if derived:
                hj_, hs_ = split_node(e["head"])
                tj2 = split_node(e["tail"])[0]
                for key, d in derived.items():
                    readers = [r for r in self.rs.rules if (r["jur"] == hj_ and r["slot"] in ("inbound", "final")
                                                          or r["jur"] == tj2 and r["slot_key"].split("|")[-1] in (hj_, "*")) and key in leaves_vars(r)]
                    d["read_by_rules"] = sorted(r["id"] for r in readers)
                    d["recipient_decisions"] = sorted({x for r in readers for x in r["decisions"]})
                    d["cite_ids"] = sorted({c for r in readers for c in r["cites"]})
            tx["derived"] = derived
            hops.append({"edge_id": eid, "tail": e["tail"], "head": e["head"], "items": items, "tax": tx, "extra_facts": extra, "derived": derived})
            w_acc += tx["ceiling"]["w"] or 0.0
            prev_items = items
        if cand.get("path_complete") and cand.get("path"):
            last_t = {s: hops[-1]["tax"][s]["t"] for s in SIDES} if hops else None
            ret = self.retention_hop(cand["path"][-1], keep_by, answers, assume, last_t)
            if ret:
                hops.append(ret)
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
                                qk = "%s@%s" % (n[1], it["jur"])        # the jurisdiction whose cell asks decides the point
                                about.setdefault(qk, h.get("about") or h["head"])    # the recipient of the hop whose cell asks the question
                                if self.answers.get(qk, self.answers.get(n[1], "unknown")) == "unknown":
                                    keys.add(qk)
            return keys

        keys = asked(hops)
        for _ in range(FORK_ROUNDS):                                 # a point can open only once another settles: a denial in doubt hides what it denies
            if not keys:
                break
            best = {k: self.fav(k) for k in keys}
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
            best = {k: self.fav(k) for k in D}
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
            out["hops"].append({"edge_id": h["edge_id"], "tail": h["tail"], "head": h["head"], "retention": bool(h.get("retention")),
                                "prior": h["tax"].get("prior"), "prior_own": h["tax"].get("prior_own"),
                                "floor": {k: h["tax"]["floor"].get(k) for k in ("wht", "incl", "rate", "credit", "underlying", "cfc_inclusion", "t")},
                                "ceiling": {k: h["tax"]["ceiling"].get(k) for k in ("wht", "incl", "rate", "credit", "underlying", "cfc_inclusion", "t")},
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
    def rank_key(self, t, c, per_branch):
        """The ranking key of a branch (§4.7): the tax per payment on the favourable side (the saving against the baseline,
        the same order), then the payback in payments (one-off cost / saving per payment; none for no restructuring; unknown
        last), then the ceiling, payment on the client's date first, fewer hops, id. A deferred payment (wait_months) costs
        time the tax figures do not show."""
        deferred = 1 if any(str(m).startswith("wait_months") for m in c.get("moves") or []) else 0
        pb = (per_branch.get(t["branch_id"]) or {}).get("payback_payments")
        if not c["restructure"]:
            pbk = (0, 0.0)
        elif pb is None:
            pbk = (1, 0.0)
        else:
            pbk = (0, pb)
        return (t["per_100"]["floor"], pbk, t["per_100"]["ceiling"], deferred, len(c["edges"]), t["branch_id"])

    def rank(self, taxes, cands, one_off, per_branch):
        by_c = {c["cand_id"]: c for c in cands}

        def keys(t):
            return self.rank_key(t, by_c[t["cand_id"]], per_branch)

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
            pb = (per_branch.get(t["branch_id"]) or {}).get("payback_payments")
            filtered = pm is not None and c["restructure"] and (pb is None or pb > pm)
            if c.get("requested"):
                incomplete.append((t, "requested path: not ranked"))
            elif k is None:
                incomplete.append((t, "incomplete"))
            elif filtered:
                incomplete.append((t, "payback above %s payments" % pm))
            else:
                complete.append((k, t))
        # the answers come first: a branch that needs n answers against the client ranks after every branch needing fewer,
        # so rank 1 is the first structure under all favourable answers (scenarios.json), whatever an adverse answer costs
        against = {t["branch_id"]: sum(1 for kk, v in t["answers_assumed"].items() if v == self.unfavourable(kk)) for _, t in complete}
        complete.sort(key=lambda x: (against[x[1]["branch_id"]], x[0]))
        for i, (k, t) in enumerate(complete):
            dom = [u["branch_id"] for _, u in complete if u is not t and u["per_100"]["ceiling"] <= t["per_100"]["floor"] + EPS
                   and (u["per_100"]["ceiling"] < t["per_100"]["ceiling"] - EPS or u["per_100"]["floor"] < t["per_100"]["floor"] - EPS)
                   and u["complete"] == t["complete"]]
            rows.append({"branch_id": t["branch_id"], "cand_id": t["cand_id"], "rank": i + 1, "keys": list(k), "answers_against": against[t["branch_id"]], "dominated_by": dom,
                         "key": "per_100", "answers_assumed": t["answers_assumed"], "range_all_branches": spread[t["cand_id"]]})
        for t, why in incomplete:
            rows.append({"branch_id": t["branch_id"], "cand_id": t["cand_id"], "rank": None, "keys": None, "dominated_by": [], "why": why})
        return rows

    def scenarios(self, taxes, cands, per_branch):
        """§4.7: every structure under the same answers. Scenarios: all favourable, each point against the client alone,
        all against. A structure without the point keeps its value; the first of a scenario is by the ranking key.
        Single objective and no probabilities: the table only says who is cheapest if those answers hold."""
        by_c = {c["cand_id"]: c for c in cands}
        comp = [t for t in taxes if t["complete"] and not by_c[t["cand_id"]].get("requested")]
        per_c = {}
        for t in comp:
            per_c.setdefault(t["cand_id"], []).append(t)
        c0 = [t for t in taxes if t["cand_id"] == "c0"]
        pts = sorted({(k, t.get("answers_about", {}).get(k)) for t in comp + c0 for k in t["answers_assumed"]}, key=lambda p: (p[0], str(p[1])))

        def pick(branches, against):
            for t in branches:
                if all((v == self.unfavourable(k)) == ((k, t.get("answers_about", {}).get(k)) in against) for k, v in t["answers_assumed"].items()):
                    return t
            return None

        def cell(t):
            return {"branch_id": t["branch_id"], "per_100": t["per_100"], "amount": t["amount"]}

        specs = [("all_favourable", set())] + [("against:%s:%s" % p, {p}) for p in pts] + ([("all_unfavourable", set(pts))] if pts else [])
        rows = []
        for sid, against in specs:
            cells = {cid: pick(bs, against) for cid, bs in per_c.items()}
            cells = {cid: t for cid, t in cells.items() if t}
            order = sorted((cid for cid in cells if self.rank_key(cells[cid], by_c[cid], per_branch) is not None),
                           key=lambda cid: self.rank_key(cells[cid], by_c[cid], per_branch))
            a0 = pick(c0, against)
            rows.append({"scenario_id": sid, "against": sorted([list(p) for p in against]), "first": order[0] if order else None,
                         "second": order[1] if len(order) > 1 else None, "order": order,
                         "structures": {cid: cell(t) for cid, t in cells.items()},
                         "as_is": dict(cell(a0), path_complete=a0["path_complete"]) if a0 else None})
        return {"points": [list(p) for p in pts], "scenarios": rows,
                "structure_rank": {cid: i + 1 for i, cid in enumerate(rows[0]["order"])} if rows else {}}

    def scenario_items(self, open_items, scen, per_branch, cands):
        """Open items against the scenarios (§4.7): a judgment point changes the decision when the first structure with it
        against the client differs from the first under all favourable answers; a one-off input matters when its structure
        is first in some scenario."""
        rows = {r["scenario_id"]: r for r in scen["scenarios"]}
        fav = rows.get("all_favourable")
        by_c = {c["cand_id"]: c for c in cands}

        def info(r, cid):
            if not r or not cid:
                return None
            c = r["structures"][cid]
            pb = per_branch.get(c["branch_id"]) or {}
            return {"cand_id": cid, "branch_id": c["branch_id"], "amount": c["amount"], "per_100": c["per_100"], "restructure": by_c[cid]["restructure"],
                    "one_off_total": (self.one_off_all.get(cid) or {}).get("total"), "payback_payments": pb.get("payback_payments")}
        firsts = {r["first"] for r in scen["scenarios"] if r["first"]}
        for o in open_items:
            if o["kind"] == "tax" and o["need"] == "DISCRETION":
                r = rows.get("against:%s:%s" % (o["key"], o.get("about")))
                if r and fav:
                    o["first_if_favourable"] = info(fav, fav["first"])
                    o["first_if_unfavourable"] = info(r, r["first"])
                    o["changes_rank"] = fav["first"] != r["first"]
                    f = fav["first"]
                    if f and f in r["structures"]:
                        o["value_at_stake"] = {s: r6(r["structures"][f]["amount"][s] - fav["structures"][f]["amount"][s]) for s in SIDES}
            elif o["kind"] == "one_off":
                blocked = {b.split(".")[0] for b in o.get("blocks", [])}
                o["first_in_scenarios"] = sorted(r["scenario_id"] for r in scen["scenarios"] if r["first"] in blocked)
                o["changes_rank"] = bool(o["first_in_scenarios"]) or bool(o.get("changes_rank"))
        open_items.sort(key=lambda o: (o["kind"] not in ("tax", "derived"), not o["changes_rank"], not o["narrows_best"], -len(o["blocks"]), o["key"]))
        return open_items

    def branch_one_off(self, t, base, oo):
        """Per branch (spec 4.7): the saving per payment against the baseline (the structure as it is when it reaches a
        destination, else the cheapest structure that reaches one without restructuring, under the same answers), both sides,
        and the payback in payments on the favourable side: one-off cost (floor) / saving (floor side). No discounting."""
        tot = (oo or {}).get("total") or {"floor": None, "ceiling": None}
        out = {"baseline_branch": base["branch_id"] if base else None, "saving_per_payment": None, "payback_payments": None}
        if base:
            saving = {s: base["amount"][s] - t["amount"][s] for s in ("floor", "ceiling")}
            out["saving_per_payment"] = {s: r6(saving[s]) for s in saving}
            if tot["floor"] is not None:
                if tot["floor"] == 0:
                    out["payback_payments"] = 0.0
                elif saving["floor"] > EPS:
                    out["payback_payments"] = r6(tot["floor"] / saving["floor"])
        return out

    def baseline(self, t, taxes, by_c):
        """The structure a saving is measured against (spec 4.7), under the answers of branch t."""
        same = t["answers_assumed"]
        fits = lambda u: all(v == same.get(k, self.fav(k)) for k, v in u["answers_assumed"].items())   # a point t does not raise: favourable
        c0 = [u for u in taxes if u["cand_id"] == "c0" and u["complete"] and fits(u)]
        if c0:
            return c0[0]
        nr = sorted((u for u in taxes if u["complete"] and not by_c[u["cand_id"]]["restructure"] and not by_c[u["cand_id"]].get("requested") and fits(u)),
                    key=lambda u: (u["per_100"]["floor"], u["per_100"]["ceiling"], u["branch_id"]))
        return nr[0] if nr else None

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
            ref = next((u for u in sorted(no_restr, key=lambda u: (u["per_100"]["floor"], u["per_100"]["ceiling"], u["branch_id"]))
                        if all(v == same.get(k, self.fav(k)) for k, v in u["answers_assumed"].items())), None)
            vs_nr = None
            if ref and by_c[t["cand_id"]]["restructure"]:
                vs_nr = {"branch_id": ref["branch_id"], **{k: v for k, v in self.branch_one_off(t, ref, one_off.get(t["cand_id"])).items() if k != "baseline_branch"}}
            out.append({"branch_id": t["branch_id"], "cand_id": t["cand_id"],
                        "notes": ["saving_per_payment and payback_payments count payments of the same amount; no discounting", "exposure interest runs from the withholding deadline to as_of = %s (an input, not a fact of the case)" % self.as_of],
                        "vs_as_is": self.delta(t, as_is), "as_is_branch": as_is["branch_id"] if as_is else None,
                        "vs_best_no_restructure": vs_nr,
                        "vs_fallback": self.delta(t, fallback), "fallback_branch": fallback["branch_id"] if fallback else None,
                        "vs_best": self.delta(t, by_b.get(best_id)) if best_id else None, "best_branch": best_id,
                        "exposure_if_denied": exposure.get(t["branch_id"]),
                        "one_off_cost": one_off.get(t["cand_id"]), **(per_branch.get(t["branch_id"]) or {})})
        return out

    # ------------------------------------------------------------ the short version (§5)
    def role_label(self, n):
        """A company as the client knows it: the payer, the payee, or a known entity, with its jurisdiction."""
        role = "the payer" if n == self.source else "the payee" if n == self.payee_node else "the known entity" if n in self.entities else "a new entity"
        return "%s (%s)" % (role, self.node_label(n))

    def client_name(self, n):
        """A company or person as the client calls it: the name the facts give, else its role and jurisdiction."""
        f, _ = self.entity_facts(n, [])
        if f.get("name"):
            return f["name"]
        j, s_ = split_node(n)
        jn = next((x.get("name") for x in self.lib.juris if x["code"] == j and x.get("name")), j.upper())
        if n == self.source:
            return "the paying company (%s)" % jn
        return "the %s %s" % (jn, "company" if s_ == "company" else "individual shareholder")

    def node_label(self, n):
        j, s = split_node(n)
        name = next((x.get("name") for x in self.lib.juris if x["code"] == j and x.get("name")), j.upper())
        return "%s %s" % (name, s)

    def brief(self, cands, taxes, ranking, deltas, open_items, scen=None, per_branch=None):
        """What a reader needs first (§5): the structures that are first or second in some scenario, the scenario table,
        the judgment points with who comes first either way, the gaps that change the decision, the as-is structure."""
        tax = {t["branch_id"]: t for t in taxes}
        delta = {d["branch_id"]: d for d in deltas}
        cand = {c["cand_id"]: c for c in cands}
        scen = scen or {"scenarios": [], "structure_rank": {}}
        per_branch = per_branch or {}
        first = {r["cand_id"]: r for r in ranking if r["rank"]}
        srank = scen["structure_rank"]
        rows_s = scen["scenarios"]
        favr = rows_s[0] if rows_s else None
        unfr = next((r for r in rows_s if r["scenario_id"] == "all_unfavourable"), favr)
        relevant = []
        for r in rows_s:
            for cid in (r["first"], r["second"]):
                if cid and cid not in relevant:
                    relevant.append(cid)
        relevant.sort(key=lambda c: srank.get(c, 10 ** 6))
        spread = {}
        for r in ranking:
            if r.get("range_all_branches"):
                spread.setdefault(r["cand_id"], r["range_all_branches"])

        def srow(cid):
            c = cand[cid]
            fb = favr["structures"].get(cid) if favr else None
            ub = unfr["structures"].get(cid) if unfr else None
            d = delta.get(fb["branch_id"]) or {} if fb else {}
            oo = self.one_off_all.get(cid) or {}
            pb = (per_branch.get(fb["branch_id"]) or {}) if fb else {}
            relies = sorted({tuple(n) for n in (tax.get(fb["branch_id"]) or {}).get("needs", [])}) if fb else []
            return {"cand_id": cid, "label": " > ".join(self.node_label(n) for n in c["path"]), "structure_rank": srank.get(cid), "path": c["path"],
                    "relies_on": [list(n) for n in relies],
                    "restructure": c["restructure"], "all_favourable": fb, "all_unfavourable": ub, "range_all_branches": spread.get(cid),
                    "first_in": [r["scenario_id"] for r in rows_s if r["first"] == cid],
                    "vs_as_is": (d.get("vs_as_is") or {}).get("amount"), "one_off_total": oo.get("total"), "one_off_flags": oo.get("flags", []),
                    "saving_per_payment": pb.get("saving_per_payment"), "payback_payments": pb.get("payback_payments")}
        fav_first = favr["first"] if favr else None

        def says_something(r):
            if r["scenario_id"] in ("all_favourable", "all_unfavourable"):
                return True
            amt = lambda row, cid: (row["structures"].get(cid) or {}).get("amount")
            return r["first"] != fav_first or amt(r, fav_first) != amt(favr, fav_first) or (r["as_is"] or {}).get("amount") != (favr["as_is"] or {}).get("amount")
        shown = [r for r in rows_s if says_something(r)]
        table = [{"scenario_id": r["scenario_id"], "against": r["against"], "first": r["first"],
                  "first_amount": r["structures"][r["first"]]["amount"] if r["first"] else None,
                  "as_is_amount": (r["as_is"] or {}).get("amount"),
                  "amounts": {cid: r["structures"][cid]["amount"] for cid in relevant if cid in r["structures"]}} for r in shown]
        others = [cid for cid in srank if cid not in relevant]
        lowest_other = min((favr["structures"][cid]["amount"]["floor"] for cid in others if favr and cid in favr["structures"]), default=None)
        best_cid = favr["first"] if favr else None
        best = srow(best_cid) if best_cid else None
        exposure = (delta.get(best["all_favourable"]["branch_id"]) or {}).get("exposure_if_denied") or {} if best and best["all_favourable"] else {}
        c0 = [t for t in taxes if t["cand_id"] == "c0"]
        as_is = None
        if c0:
            lead = next((t for t in c0 if all(v == self.fav(k) for k, v in t["answers_assumed"].items())), c0[0])
            as_is = {"branch_id": lead["branch_id"], "cand_id": "c0", "path": cand["c0"]["path"], "ranked": "c0" in first, "answers_assumed": lead["answers_assumed"],
                     "amount": lead["amount"], "range_all_branches": {"amount": {"floor": min(t["amount"]["floor"] for t in c0), "ceiling": max(t["amount"]["ceiling"] for t in c0)}, "branches": len(c0)},
                     "why_not_ranked": None if "c0" in first else next((r.get("why") for r in ranking if r["cand_id"] == "c0"), None)}
        own_pts = {(k, t.get("answers_about", {}).get(k)) for t in taxes if t["cand_id"] in (best_cid, "c0") for k in t["answers_assumed"]}
        points = [{k: o.get(k) for k in ("key", "about", "question", "changes_rank", "value_at_stake", "first_if_favourable", "first_if_unfavourable")}
                  for o in open_items if o["kind"] == "tax" and o["need"] == "DISCRETION"
                  and (o.get("changes_rank") or ((o.get("value_at_stake") or {}).get("ceiling") or 0) > 0 or (o["key"], o.get("about")) in own_pts)]
        gaps = [{k: o.get(k) for k in ("kind", "need", "key", "question", "about", "first_in_scenarios", "blocks")}
                for o in open_items if o.get("changes_rank") and not (o["kind"] == "tax" and o["need"] == "DISCRETION")]
        return {"terms": TERMS, "best": best, "as_is": as_is, "structures": [srow(c) for c in relevant[:BRIEF_ROWS]], "scenarios": table,
                "scenarios_without_effect": len(rows_s) - len(shown), "judgment_points": points, "decision_gaps": gaps,
                "others": {"count": len(others), "lowest_all_favourable_amount": lowest_other},
                "exposure_if_denied": {k: exposure.get(k) for k in ("benefit_assumed", "tax", "interest", "fine", "total", "as_of")},
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
            yes = [k for k, v in b["answers_assumed"].items() if v == self.fav(k)]
            if not yes:
                continue
            fb = next((u for u in branches if u["cand_id"] == b["cand_id"] and self.is_worst(u["answers_assumed"])), None)
            if fb is None or fb is b:
                continue
            t, tf = by_b[b["branch_id"]], by_b[fb["branch_id"]]
            # interval subtraction: the least extra tax pairs the denied floor with the claimed ceiling
            tax = {"floor": r6(tf["amount"]["floor"] - t["amount"]["ceiling"]), "ceiling": r6(tf["amount"]["ceiling"] - t["amount"]["floor"])}
            # the hop-by-hop difference, split between the source cells (wht) and the residence cells (res - credit)
            parts = []                                          # (jur, S, R, subj, slot_keys, tax_part{floor, ceiling}, is_source)
            for h, hf in zip(b["hops"], fb["hops"]):
                S, _ = split_node(h["tail"]); R, subj = split_node(h["head"])
                src_keys = [it["slot_key"] for it in h["items"] if it["jur"] == S and it["slot"] in ("outbound_wht", "anti_abuse") and any(k in it.get("assumptions", []) for k in yes)]
                res_keys = [it["slot_key"] for it in h["items"] if it["jur"] == R and it["slot"] in ("inbound", "final", "anti_abuse") and any(k in it.get("assumptions", []) for k in yes)]
                if src_keys:
                    part = {}
                    for side, other in (("floor", "ceiling"), ("ceiling", "floor")):
                        before = self.amount_before(fb["hops"], h["edge_id"], side)
                        part[side] = r6(before * (hf["tax"][side]["wht"] - h["tax"][other]["wht"]) / 100)
                    parts.append((S, S, R, subj, src_keys, part, True))
                if res_keys:
                    part = {}
                    for side, other in (("floor", "ceiling"), ("ceiling", "floor")):
                        before = self.amount_before(fb["hops"], h["edge_id"], side)
                        d_res = (hf["tax"][side]["res"] - hf["tax"][side]["credit"]) - (h["tax"][other]["res"] - h["tax"][other]["credit"])
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
                pen = strip_items([ev.eval_cell(self.rs, "%s|all|penalty|*" % jur, self.date, dict(PLAN_CONDUCT, overdue_months=overdue_m), self.answers, self.mode)])[0]
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
            # the cells are what each authority assesses; other cells of the fallback can move the other way (a larger foreign
            # credit downstream), so the net tax may be below their sum: the rest is the offset, without interest or fine
            offset = {s: r6(tax[s] - sum(p[5][s] for p in parts)) for s in ("floor", "ceiling")}
            if any(abs(v) > 0.005 for v in offset.values()):
                flags.add("offset_elsewhere")
            out[b["branch_id"]] = {"benefit_assumed": yes, "fallback_branch": fb["branch_id"], "tax": tax, "as_of": self.as_of,
                                   "cells": cells_out, "offset": offset, "interest": {s: r6(interest[s]) for s in interest}, "fine": {s: r6(fine[s]) for s in fine},
                                   "total": {s: r6(tax[s] + interest[s] + fine[s]) for s in total}, "flags": sorted(flags)}
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
        # 1. a new holder of the source company (someone other than the as-is payee holds S); the as-is individual payee
        #    who moves to another jurisdiction still holds the shares: no transfer
        reloc = self.relocation(cand) if not cand.get("as_is") else None
        moved = bool(reloc and reloc.get("person") == self.payee_node and chain[1] == reloc["to"])
        if chain[1] != self.payee_node and not moved:
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
        cc = val.get("cost_currency")
        if cost is not None and cc and cc != out["currency"]:
            r_from, r_to = self.fx_rate(cc), self.fx_rate(out["currency"])
            if r_from is None or r_to is None:
                out["flags"].add("fx_missing"); cost = None
            else:
                cost = float(cost) / r_from * r_to; out["flags"].add("cost_converted")
        if cost is None and "fx_missing" in out["flags"]:
            out["gain"] = out["consideration"]
        elif cost is None:
            out["gain"] = out["consideration"]; out["flags"].add("cost_missing")
        else:
            out["gain"] = max(0.0, out["consideration"] - float(cost))       # cost_base is the cost of the stake transferred (spec §4.7)
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
        listed = tgt_f.get("listed")
        if listed is None and target == self.source:
            listed = tgt_f.get("payer_listed", self.payment.get("payer_listed"))      # the payer is the target
        if listed is not None:
            tf["target_listed"] = listed
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
        """§4.7 one_off_cost of a candidate (payback and total_N are per branch, see branch_one_off): share transfers and
        the exit tax of an individual who moves."""
        reloc = self.relocation(cand) if not cand.get("as_is") else None
        if not transfers and not reloc:
            return {"transfers": [], "total": {"floor": 0.0, "ceiling": 0.0}, "flags": []}
        flags = set()
        unquantified = set()
        total = {"floor": 0.0, "ceiling": 0.0}
        rows = []
        if reloc:
            xr, xf = self.exit_cost(reloc)
            flags |= xf
            rows.append(xr)
            if xr.get("in_payment_currency"):
                for s in total:
                    total[s] += xr["in_payment_currency"][s]
        about = {}                                         # flag -> the companies whose figures it needs
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
            for fl in g["flags"]:
                about.setdefault(fl, set()).add(tr["target"])
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
            if "cost_missing" in g["flags"] and all(abs(inc[s]) < EPS for s in inc):
                row["note"] = "cost base not given, but no side taxes this gain: it changes nothing"
                about.get("cost_missing", set()).discard(tr["target"])
                if not about.get("cost_missing"):
                    flags.discard("cost_missing")
            conv = (1.0 / rate) if rate else None
            row.update({"currency": ccy, "consideration": r6(cons), "gain": r6(gain),
                        "income_tax": {s: r6(inc[s]) for s in inc}, "stamp": {s: r6(stamp[s]) for s in stamp},
                        "in_payment_currency": None if conv is None else {s: r6((inc[s] + stamp[s]) * conv) for s in inc},
                        "items_ref": "transfers/%s.json" % cand["cand_id"]})
            if conv is not None:
                for s in total:
                    total[s] += (inc[s] + stamp[s]) * conv
            rows.append(row)
        res = {"transfers": rows, "flags": sorted(flags), "total": {s: r6(total[s]) for s in total}, "costs_unquantified": sorted(unquantified),
               "flag_about": {fl: sorted(v) for fl, v in about.items()}}
        if flags & {"valuation_missing", "fx_missing", "holder_unknown", "exit_inputs_missing", "exit_person_unknown", "exit_slot_missing"}:
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
        """The ranking measure of a (possibly re-run) branch tax: per_100 (the payback only orders equal taxes)."""
        return t["per_100"]

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
            top = lambda L: min(L, key=lambda t: (self.score(t)["floor"] if self.score(t)["floor"] is not None else float("inf"), self.score(t)["ceiling"] or 0, t["branch_id"])) if L else None
            ty, tn = top(yes_b), top(no_b)
            changes = bool(ty and tn and (ty["cand_id"] != tn["cand_id"] or self.score(ty) != self.score(tn)))
            out.append({"kind": "tax", "need": "DISCRETION", "key": key, "about": node, "question": preds.get(base_key(key), {}).get("question"),
                        "blocks": sorted(t["branch_id"] for t in yes_b + no_b), "changes_rank": changes,
                        "narrows_best": best is not None and key in by_b[best]["answers_assumed"] and by_b[best].get("answers_about", {}).get(key) == node,
                        "factor_vars": preds.get(base_key(key), {}).get("factor_vars", []),
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
                            per[r["branch_id"]] = pick(outcomes, key=lambda p: (p["floor"], p["ceiling"]))
                        else:
                            per[r["branch_id"]] = self.score(t)
                    tops[label] = min(per.items(), key=lambda kv: (kv[1]["floor"] if kv[1]["floor"] is not None else float("inf"), kv[1]["ceiling"] or 0, kv[0]))
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
                            per[r["branch_id"]] = pick(outcomes, key=lambda p: (p["floor"], p["ceiling"]))
                        else:
                            per[r["branch_id"]] = self.score(t)
                    tops[label] = min(per.items(), key=lambda kv: (kv[1]["floor"] if kv[1]["floor"] is not None else float("inf"), kv[1]["ceiling"] or 0, kv[0]))
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
                     "note": "read by a restructure cell of this candidate's transfers (transfers/<cand_id>.json); orders structures of equal tax through the payback (payback_payments)"}
            if values:
                tops = {}
                for label, pick in (("favourable", min), ("unfavourable", max)):
                    per = {}
                    for r in ranked:
                        t = by_b[r["branch_id"]]
                        if r["branch_id"] in blocks:
                            outcomes = [self.score(self.rerun_branch_with(t, key, v)) for v in values]
                            outcomes = [o for o in outcomes if o["ceiling"] is not None] or [self.score(t)]
                            per[r["branch_id"]] = pick(outcomes, key=lambda p: (p["floor"], p["ceiling"]))
                        else:
                            per[r["branch_id"]] = self.score(t)
                    tops[label] = min(per.items(), key=lambda kv: (kv[1]["floor"] if kv[1]["floor"] is not None else float("inf"), kv[1]["ceiling"] or 0, kv[0]))
                entry["changes_rank"] = tops["favourable"][0] != tops["unfavourable"][0] or tops["favourable"][1] != tops["unfavourable"][1]
                entry["if_favourable"] = {"branch_id": tops["favourable"][0], "score": tops["favourable"][1]}
                entry["if_unfavourable"] = {"branch_id": tops["unfavourable"][0], "score": tops["unfavourable"][1]}
            out.append(entry)
        for d in deltas:
            oo = d.get("one_off_cost") or {}
            for fl in oo.get("flags", []):
                if fl in ("valuation_missing", "cost_missing", "holder_unknown", "fx_missing", "exit_inputs_missing", "exit_person_unknown"):
                    q = FLAG_QUESTIONS.get(fl, "one-off cost input missing: %s" % fl)
                    for tgt in (oo.get("flag_about") or {}).get(fl) or [None]:
                        holder = next((tr.get("transferor") for tr in oo.get("transfers", []) if tr.get("target") == tgt and tr.get("transferor")), None)
                        out.append({"kind": "one_off", "need": "MISSING", "key": fl, "about": tgt,
                                    "question": q.format(company=self.client_name(tgt) if tgt else "the company whose shares would be transferred",
                                                         holder=self.client_name(holder) if holder else "its current shareholder"),
                                    "client_supplies": fl != "fx_missing",
                                    "blocks": [d["branch_id"]], "changes_rank": False, "narrows_best": False, "factor_vars": []})
            ex = d.get("exposure_if_denied") or {}
            if ex:
                for v in sorted({"concealment", "negligence", "voluntary_payment", "return_filed"} - set(PLAN_CONDUCT)):
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
                    tops[label] = min(per.items(), key=lambda kv: (kv[1]["floor"] if kv[1]["floor"] is not None else float("inf"), kv[1]["ceiling"] or 0, kv[0]))
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
        key = base_key(key)
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
                 "date_mode": sha([self.date, self.mode, self.assume])}
        v = self.q.version()
        return {"inputs_sha256": sha(parts), "inputs": parts, "rule_version": v["rule"], "database_version": v["database"],
                "engine_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16], "generated_at": v["generated_at"], "limits": self.limits}

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
        by_c = {c["cand_id"]: c for c in cands}
        per_branch = {}
        for t in taxes:
            per_branch[t["branch_id"]] = self.branch_one_off(t, self.baseline(t, taxes, by_c), one_off_all.get(t["cand_id"]))
        ranking = self.rank(taxes, cands, one_off_all, per_branch)
        scen = self.scenarios(taxes, cands, per_branch)
        for r in ranking:
            r["structure_rank"] = scen["structure_rank"].get(r["cand_id"])
        exposure = self.exposure(branches_all, taxes)
        deltas = self.deltas(taxes, ranking, one_off_all, exposure, per_branch)
        open_items = self.scenario_items(self.open_items(taxes, ranking, deltas), scen, per_branch, cands)
        # ---- write
        if lab is not None:
            jdump(dict(version=version["inputs_sha256"], **self.graph), out / "graph.json")
            jdump({"version": version["inputs_sha256"], "labels": lab["labels"], "frontier": lab["frontier"], "truncated": lab["truncated"]}, out / "labels.json")
        jdump({"version": version["inputs_sha256"], "candidates": cands}, out / "paths.json")
        jdump({"version": version["inputs_sha256"], "branches": [{k: v for k, v in b.items() if k != "hops"} | {"hops_ref": "hops/%s.json" % b["branch_id"]} for b in branches_all]}, out / "branches.json")
        jdump({"version": version["inputs_sha256"], "amount": self.amount, "currency": self.currency, "taxes": taxes}, out / "tax.json")
        jdump({"version": version["inputs_sha256"], "key": "per_100, then payback_payments", "ranking": ranking}, out / "ranking.json")
        jdump({"version": version["inputs_sha256"], "deltas": deltas}, out / "deltas.json")
        jdump(dict(version=version["inputs_sha256"], **scen), out / "scenarios.json")
        jdump({"version": version["inputs_sha256"], "score_key": "per_100", "open_items": open_items}, out / "open_items.json")
        jdump(dict(version=version["inputs_sha256"], **self.gap(self.graph)), out / "gap.json")
        if self.fx:
            jdump(self.fx, out / "fx.json")
        for cid, req in requirements.items():
            jdump({"version": version["inputs_sha256"], "cand_id": cid, "requirements": req}, out / "requirements" / ("%s.json" % cid))
        for ref, items in self.hops_store.items():
            jdump({"version": version["inputs_sha256"], "items": items}, out / ref)
        if lab is not None:
            jdump(dict(version=version["inputs_sha256"], **self.brief(cands, taxes, ranking, deltas, open_items, scen, per_branch)), out / "brief.json")
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
def signature(cand):
    """A structure that is the same across runs: cand_id and branch_id are renumbered on every run."""
    return "%s | %s | %s" % (">".join(cand["path"]), ",".join(sorted(cand.get("moves") or [])) or "-", ",".join(sorted(cand.get("restructure") or [])) or "-")


def branch_keys(products):
    """branch_id -> signature + assumed answers, the key two runs are aligned by."""
    sig = {c["cand_id"]: signature(c) for c in jload(Path(products) / "paths.json")["candidates"]}
    return {t["branch_id"]: "%s || %s" % (sig.get(t["cand_id"], t["cand_id"]), ",".join("%s=%s" % kv for kv in sorted((t.get("answers_assumed") or {}).items())))
            for t in jload(Path(products) / "tax.json")["taxes"]}


def diff(products, against):
    a, b = Path(products), Path(against)
    ra, rb = jload(a / "ranking.json"), jload(b / "ranking.json")
    ka, kb = branch_keys(a), branch_keys(b)
    ta = {ka[t["branch_id"]]: t for t in jload(a / "tax.json")["taxes"]}
    tb = {kb[t["branch_id"]]: t for t in jload(b / "tax.json")["taxes"]}
    va, vb = jload(a / "version.json"), jload(b / "version.json")
    rank_a = {ka.get(r["branch_id"], r["branch_id"]): r["rank"] for r in ra["ranking"]}
    rank_b = {kb.get(r["branch_id"], r["branch_id"]): r["rank"] for r in rb["ranking"]}
    out = {"products": str(a), "against": str(b), "incomparable": [], "rank_moves": [], "interval_changes": [], "open_item_changes": {},
           "inputs_changed": sorted(k for k in set(va["inputs"]) | set(vb["inputs"]) if va["inputs"].get(k) != vb["inputs"].get(k))}
    # what else changed between the two runs, so a rank move with unchanged inputs has a cause
    out["engine_changed"] = {"optimize_py": va.get("engine_sha256") != vb.get("engine_sha256"),
                             "rule_csv": va["rule_version"].get("rule_csv_sha256") != vb["rule_version"].get("rule_csv_sha256"),
                             "param_csv": va["database_version"].get("param_csv_sha256") != vb["database_version"].get("param_csv_sha256"),
                             "doc_csv": va["database_version"].get("doc_csv_sha256") != vb["database_version"].get("doc_csv_sha256")}
    if va["rule_version"].get("rule_csv_sha256") != vb["rule_version"].get("rule_csv_sha256"):
        out["incomparable"].append("rule layer version differs")
    if va["inputs"].get("move_csv") != vb["inputs"].get("move_csv"):
        out["incomparable"].append("move.csv differs")
    for bid in sorted(set(rank_a) | set(rank_b)):
        if rank_a.get(bid) != rank_b.get(bid):
            out["rank_moves"].append({"branch": bid, "before": rank_b.get(bid, "absent" if bid not in rank_b else None), "after": rank_a.get(bid, "absent" if bid not in rank_a else None)})
    for bid in sorted(set(ta) & set(tb)):
        if ta[bid]["per_100"] != tb[bid]["per_100"]:
            out["interval_changes"].append({"branch": bid, "branch_id_now": ta[bid]["branch_id"], "branch_id_before": tb[bid]["branch_id"],
                                            "before": tb[bid]["per_100"], "after": ta[bid]["per_100"]})
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
