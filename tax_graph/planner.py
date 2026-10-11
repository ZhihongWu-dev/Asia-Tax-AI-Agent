"""planner.py (优化方案 v2 §1): a case and the answers so far -> a question sheet, or one concrete plan.

    plan(template, event, case, answers) -> Outcome(questions, plan)

Each round:
  1. every candidate structure is evaluated with the answers: data become facts of the case, confirmed actions and
     rulings become answers to the rules' conditions (addressed to a role or a flow, never to a field name at large);
  2. the plan candidate is the one with the least guaranteed tax — the tax under the worst outcome of every
     judgement and every datum still unknown, with the plan's own actions done — ties: least best-case tax, fewest
     open judgements, fewest companies (J6: Γ-maximin; E2/E3: an answer that holds in every completion);
  3. questions, in this order: data without which a tax is unbounded (always asked); data whose favourable answer
     could lower the plan's guaranteed tax or let another candidate beat it; actions the plan relies on that are not
     yet confirmed; rulings that would change the plan; library material (a holiday calendar) the deadlines need;
  4. no question left -> the plan: structure, actions, taxes, deadlines and the judgements it still depends on, each
     placed in its jurisdiction region (CN, HK, SG, CN∩HK, CN∩SG, HK∩SG, CN∩HK∩SG).
Answers are data values (with a source), yes / no, or "unknown". An unknown datum stays unknown: it is taken at its
worst, and if a tax is unbounded without it the candidates that need it cannot be planned. Nothing is filled in.
"""
import copy
import csv
import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

from .data.domain import ADJUSTABLE
from .engine import (EX_ANTE, OPPOSITE, PEM_RULE, RULES_BY_ID, Bounds, CaseCtx, Defect, Undecidable, bounds, flow_name,
                     outside_steps, plan_favourable)
from .ex_ante import validate_core
from .model import JURISDICTIONS, HoldEdge
from .params import Params
from .regions import absolute_key, item_region, name as region_name, order_key, rule_region
from .rules.eval import SHARED_GROUPS
from .rules.model import Discretion, Leaf, Not, And, Or, leaves
from .rules.tri import DATA, DISCRETION, MISSING, PLAN, Need
from .scenarios import NEW, same_settled

STEP_TEXT = {"ip_transfer": "IP 由 %s 转给 %s",       # 口径 D19: steps whose tax no rule computes
             # 口径 D30: a levy a group company bears on a flow dated before the law the library starts from
             "before_law": "流 %s（%s）早于%s施行（%s），此前的规定不在库内（库只留现行规定），其%s未计算"}


def _step_text(step):
    return STEP_TEXT.get(step[0], step[0] + "：%s → %s") % tuple(step[1:])

EPS = 0.005
CONTENTION_MAX = 12
GLOSS_FILE = Path(__file__).resolve().parent / "data" / "field_gloss.csv"
FORMS_FILE = Path(__file__).resolve().parents[1] / "official" / "form_fields.csv"
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _load_gloss():
    with open(str(GLOSS_FILE), encoding="utf-8") as f:
        return {r["field"]: r for r in csv.DictReader(f)}


def _load_forms():
    out = {}
    if FORMS_FILE.exists():
        with open(str(FORMS_FILE), encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                out.setdefault(r["maps_to"], []).append("%s · %s" % (r["form_id"], r["label"][:40]))
    return out


GLOSS, FORMS = _load_gloss(), _load_forms()
JUR_NAME = {"cn": "内地", "hk": "香港", "sg": "新加坡"}


def _gloss(f):
    """A field's gloss row; <name>_hk / _sg (a jurisdiction's own group fact, 口径 D17) reads <name>'s, the place named."""
    if f in GLOSS:
        return GLOSS[f]
    head, _, j = f.rpartition("_")
    if j in JUR_NAME and head in GLOSS:
        g = dict(GLOSS[head])
        g["gloss"] = "%s：%s" % (JUR_NAME[j], g.get("gloss", head))
        return g
    if j.isdigit() and head in GLOSS:                       # a year's own figure (p2_eur_rate_2027)
        g = dict(GLOSS[head])
        g["gloss"] = "%s 财年：%s" % (j, g.get("gloss", head))
        return g
    return {}


# ---------------------------------------------------------------- answers
@dataclass
class Answers:
    data: Dict[str, object] = field(default_factory=dict)        # address -> value, {"value", "source"} or "unknown"
    actions: Dict[str, str] = field(default_factory=dict)        # address -> yes / no / unknown
    rulings: Dict[str, str] = field(default_factory=dict)        # address -> yes / no / unknown
    library: Dict[str, object] = field(default_factory=dict)     # "calendar:SG:2028" -> answer

    @classmethod
    def load(cls, path):
        p = Path(path)
        if not p.exists():
            return cls()
        d = json.loads(p.read_text(encoding="utf-8"))
        return cls(d.get("data", {}), d.get("actions", {}), d.get("rulings", {}), d.get("library", {}))

    def value(self, key):
        v = self.data.get(key)
        if isinstance(v, dict):
            v = v.get("value")
        return v

    def answered(self, key):
        return key in self.data or key in self.actions or key in self.rulings or key in self.library


def _conv(v):
    if isinstance(v, str) and ISO.match(v):
        return date.fromisoformat(v)
    return v


def apply_data(case, answers):
    """A copy of the case with the data answers in it ("unknown" answers leave the fact absent)."""
    c = copy.deepcopy(case)
    extra = getattr(c, "extra", None)
    if extra is None:
        c.extra = extra = {}
    for key, raw in answers.data.items():
        v = answers.value(key)
        if v is None or v == "unknown":
            continue
        v = _conv(v)
        m = re.match(r"^hold:([A-Z_]+)>([A-Z_]+)\.(\w+)$", key)
        if m:
            a, b, attr = m.groups()
            h = c.holds.get((a, b)) or HoldEdge(a, b, None)
            c.holds[(a, b)] = HoldEdge(a, b, float(v) if attr == "ratio" else h.ratio,
                                       v if attr == "since" else h.since, float(v) if attr == "cost" else h.cost)
            continue
        m = re.match(r"^flow:(.+)\.(\w+)$", key)
        if m:
            fid, attr = m.groups()
            c.flows.setdefault(flow_name(fid), {})[attr] = v
            continue
        m = re.match(r"^group\.(\w+)$", key)
        if m:
            for rf in c.roles.values():
                rf.attrs[m.group(1)] = v
            continue
        m = re.match(r"^([A-Z_]+)\.(\w+)$", key)
        if m:
            role, attr = m.groups()
            if role in c.roles:
                c.roles[role].attrs[attr] = v
            else:
                extra.setdefault(role, {})[attr] = v
    return c


# ---------------------------------------------------------------- structures
@dataclass
class Question:
    key: str
    kind: str                     # blocking | data | action | ruling | library
    region: frozenset
    prompt: str
    value: str = ""
    source_hint: str = ""
    why: List[str] = field(default_factory=list)
    impact: Optional[float] = None
    forms: List[str] = field(default_factory=list)


@dataclass
class Evaluation:
    cand: dict
    graph: object
    b: object
    ticks: dict
    plan_keys: Dict[str, tuple]            # absolute PLAN key -> (group, need)
    blocking: Dict[str, tuple]             # absolute DATA key -> group
    excluded: str = ""                     # why this candidate cannot be planned (a blocking datum answered unknown)

    @property
    def n_discretion(self):
        return sum(1 for ns in self.b.groups.values() for n in ns if n.source == DISCRETION)


@dataclass
class Outcome:
    questions: List[Question]
    plan: Optional[dict]
    evaluations: List[Evaluation]
    note: str = ""


# ---------------------------------------------------------------- helpers
def _flow_of_group(grp, ev_graph, b):
    for labels in ((b.L_lo, b.L_hi) if b is not None else ()):
        lb = labels.get(grp[1]) if isinstance(grp[1], str) else None
        if lb is not None:
            return lb.flow
    fid = grp[1] if isinstance(grp[1], str) else None
    return next((f for f in ev_graph.flows if fid in (f.id, flow_name(f.id)) or (fid and flow_name(fid) == f.id)), None)


def _abs(n, grp, graph, b):
    if n.source == DATA or grp[0] == PEM_RULE or str(grp[0]).startswith("data."):
        return n.key
    f = _flow_of_group(grp, graph, b)
    return absolute_key(n.key, f) if f is not None else n.key


def _field_of(key):
    """'OP.after_tax_profit' / 'flow:up1@2027.holding_months:ge' / 'hold:ULT>OP.ratio' -> the field name."""
    k = key.split(":", 1)[1] if key.startswith(("flow:", "hold:")) else key
    k = k.rsplit(".", 1)[-1] if "." in k else k
    return k.split(":")[0]


def _pred_of(key):
    last = key.rsplit(":", 1)
    return last[1] if len(last) == 2 and "." not in last[1] and not key.startswith("calendar") else ""


def _region_of_group(grp, graph):
    r = RULES_BY_ID.get(grp[0])
    if r is not None:
        return rule_region(r)
    if grp[0] in SHARED_GROUPS:                         # a decision several rules share (口径 D23)
        return frozenset({SHARED_GROUPS[grp[0]]})
    if grp[0] == PEM_RULE:
        e = graph.entities.get(grp[1])
        return frozenset({"CN"} | ({e.loc} if e is not None and e.loc else set()))
    if str(grp[0]).startswith("data."):
        if grp[0] == "data.holding":
            a, b = grp[1].split(">")
            return frozenset(x.loc for x in (graph.entities.get(a), graph.entities.get(b)) if x is not None and x.loc)
        if grp[0] == "data.cfc_profit":
            e = graph.entities.get(grp[1])
            return frozenset({"CN"} | ({e.loc} if e is not None and e.loc else set()))
        if grp[1] in JURISDICTIONS:                     # a jurisdiction's own fact or action (Pillar Two, 口径 D14)
            return frozenset({grp[1]})
        e = graph.entities.get(grp[1])
        if e is not None and e.loc:
            return frozenset({e.loc})
        return frozenset(j for j in (x.loc for x in graph.entities.values()) if j)
    if grp[0] in ("cn.liquidation.split", "cn.capital_reduction.split"):
        return frozenset({"CN"})
    return frozenset()


def _polarity(rule, key):
    """True when the Discretion leaf `key` sits under an even number of negations (its True supports the rule)."""
    def walk(c, neg):
        if isinstance(c, Discretion):
            return [neg] if c.key == key else []
        if isinstance(c, Not):
            return walk(c.x, not neg)
        if isinstance(c, (And, Or)):
            return [x for y in c.xs for x in walk(y, neg)]
        return []
    hits = walk(rule.cond, False) if rule.cond is not None else []
    return (not hits[0]) if hits else True


def _ruling_ticks(answers, evaluations=None):
    """Rulings answered "yes": the authority's favourable reading. Its tick value depends on the rule: a favourable
    rule wants the judgement true, an unfavourable one (a denial, a charge) wants it false."""
    out = {}
    for key, v in answers.rulings.items():
        if v != "yes":
            continue
        field_ = key.split(".", 1)[1] if "." in key else key
        val = None
        if field_ in ("effective_management_in_cn", "cn_main_controlling_investor"):
            out[Need(DISCRETION, key)] = False          # the favourable reading: not a Mainland resident by management
            continue
        for r in RULES_BY_ID.values():
            if r.cond is None:
                continue
            if any(isinstance(x, Discretion) and x.key == field_ for x in leaves(r.cond)):
                pol = _polarity(r, field_)
                val = (bool(r.favourable) == pol)
                break
        if val is not None:
            out[Need(DISCRETION, key)] = val
    return out


def _ctx_of(ticks):
    return lambda facts: CaseCtx(facts, ticks, EX_ANTE, ADJUSTABLE)


def _plan_value(key, ticks):
    """The value the plan gives an action: decided by an action already taken on the same field (the opposite
    predicate), else the side that favours the taxpayer; None when only computing both can tell."""
    head, _, pred = key.rpartition(":")
    opp = OPPOSITE.get(pred)
    if opp and Need(PLAN, head + ":" + opp) in ticks:
        return not ticks[Need(PLAN, head + ":" + opp)]
    return plan_favourable(_field_of(key), pred)


def evaluate(template, event, case, a, answers, P, g0=None):
    g = template.build(event, a, case)
    validate_core(g)
    if g0 is not None and not same_settled(g, g0, case.settled):
        return None
    ticks = dict(_ruling_ticks(answers))
    for key, v in answers.actions.items():                  # "yes": the plan can take the favourable side
        fav = _plan_value(key, ticks)
        fav = True if fav is None else fav
        ticks[Need(PLAN, key)] = fav if v == "yes" else (not fav)
    plan_keys, undecided = {}, []
    b, joint = None, None
    for _ in range(5):
        try:
            b = bounds(g, _ctx_of(ticks), P, settled=case.settled, as_at=event.as_at, closed=case.closed, ticks=ticks)
        except Undecidable as u:                            # the plan's own actions first: they may close enough
            new = {}
            for grp, ns in u.groups.items():
                for n in ns:
                    if n.source == PLAN and Need(PLAN, _abs(n, grp, g, None)) not in ticks:
                        new[_abs(n, grp, g, None)] = (grp, n)
            for ak, gn in new.items():
                v = _plan_value(ak, ticks)
                if v is None:
                    undecided.append(ak)
                ticks[Need(PLAN, ak)] = True if v is None else v
                plan_keys[ak] = gn
            if new:
                continue
            joint = u
            break
        new = {}
        for grp, ns in b.groups.items():
            for n in ns:
                if n.source == PLAN:
                    ak = _abs(n, grp, g, b)
                    if Need(PLAN, ak) not in ticks:
                        new[ak] = (grp, n)
        if not new:
            break
        for ak, gn in new.items():                          # the plan's own action, pending confirmation
            v = _plan_value(ak, ticks)
            if v is None:
                undecided.append(ak)
            ticks[Need(PLAN, ak)] = True if v is None else v
            plan_keys[ak] = gn
    if joint is None:                                       # actions whose side only the numbers decide: the lower
        for ak in undecided:                                # guaranteed tax
            if answers.answered(ak):
                continue
            t2 = dict(ticks)
            t2[Need(PLAN, ak)] = not ticks[Need(PLAN, ak)]
            try:
                b2 = bounds(g, _ctx_of(t2), P, settled=case.settled, as_at=event.as_at, closed=case.closed, ticks=t2)
            except Undecidable:
                continue
            if b2.hi < b.hi - EPS:
                ticks, b = t2, b2
    if joint is not None:                                   # ask what closes the interacting decisions
        b = Bounds(float("-inf"), float("inf"), dict(joint.groups), {}, {}, {})
        blocking, kinds = {}, {}
        for grp, ns in joint.groups.items():
            for n in ns:
                if n.source in (MISSING, DISCRETION, DATA):
                    k = _abs(n, grp, g, None)
                    blocking[k] = grp
                    kinds[k] = "ruling" if n.source == DISCRETION else "joint"
        ev = Evaluation(a, g, b, ticks, plan_keys, blocking)
        ev.prereq, ev.joint = {}, kinds
        if all(answers.answered(k) for k in blocking):
            ev.excluded = "无法精确计算：%d 个相互影响的未决项在答复后仍开放（%s）" % (len(blocking), "，".join(sorted(blocking)[:6]))
        return ev
    blocking, prereq = {}, {}
    for grp, ns in b.groups.items():
        for n in ns:
            if n.source == DATA:
                blocking[n.key] = grp
                prereq[n.key] = [m.key for m in ns if m.source == MISSING]   # questions that decide whether it applies
    ev = Evaluation(a, g, b, ticks, plan_keys, blocking)
    ev.prereq = prereq
    unknown = [k for k in blocking if answers.data.get(k) == "unknown"]
    if unknown:
        ev.excluded = "unbounded without %s (answered unknown)" % ", ".join(sorted(unknown))
    steps = outside_steps(b, g)[0]                          # 口径 D30: a group-borne levy the library cannot compute there
    if steps:
        g.unmodelled = tuple(g.unmodelled) + tuple(x for x in steps if x not in g.unmodelled)
    if g.unmodelled:                                        # 口径 D19: the step's tax is not computed: no plan
        ev.excluded = "需要的步骤本程序尚未建模（%s），其税额未知" % "；".join(_step_text(x) for x in g.unmodelled)
    return ev


def _key(ev):
    return (ev.b.hi, ev.b.lo, ev.n_discretion, len(ev.graph.entities))


def _forced_hi(ev, groups, case, event, P):
    force = {g: "fav" for g in groups}
    try:
        return bounds(ev.graph, _ctx_of(ev.ticks), P, settled=case.settled, as_at=event.as_at, closed=case.closed,
                      ticks=ev.ticks, force=force).hi
    except Defect:
        return None


def _with_tick(ev, need, value, case, event, P):
    t = dict(ev.ticks)
    t[need] = value
    return bounds(ev.graph, _ctx_of(t), P, settled=case.settled, as_at=event.as_at, closed=case.closed, ticks=t).hi


PAIR_MAX = 60                                       # item pairs tried on the chosen structure, per round


def _joint_pairs(ev, case, event, P, answers):
    """Pairs of open data / rulings on the chosen structure that lower its guaranteed tax only together: each worth
    nothing alone (forcing its groups favourable leaves the guaranteed tax), both touching the same flow or company,
    forced favourable together. -> [(key_a, key_b, impact, groups_a, groups_b, source_a, source_b)]"""
    from itertools import combinations
    by_key = {}
    for grp, ns in ev.b.groups.items():
        for n in ns:
            if n.source in (MISSING, DISCRETION):
                k = _abs(n, grp, ev.graph, ev.b)
                if not answers.answered(k):
                    by_key.setdefault(k, (n.source, set()))[1].add(grp)
    zero = []
    for k, (src, grps) in by_key.items():
        hi = _forced_hi(ev, grps, case, event, P)
        if hi is not None and hi >= ev.b.hi - EPS:
            zero.append(k)

    def touch(k):
        out = {("flow", str(g[1]).split(".")[0]) for g in by_key[k][1]}
        head = k.split(":", 1)[1] if k.startswith(("flow:", "hold:")) else k
        out.add(("company", head.split(".")[0]))
        return out
    found = []
    for a, b in [(a, b) for a, b in combinations(sorted(zero), 2) if touch(a) & touch(b)][:PAIR_MAX]:
        hi = _forced_hi(ev, by_key[a][1] | by_key[b][1], case, event, P)
        if hi is not None and hi < ev.b.hi - EPS:
            found.append((a, b, round(ev.b.hi - hi, 2), by_key[a][1], by_key[b][1], by_key[a][0], by_key[b][0]))
    return found


# the amounts of the steps a structure itself needs (口径 D18, D19): asked by name, never filled
STEP_AMOUNT = {"reorg": ("重组步骤的对价：ULT 把所持 OP 股权转给新控股公司的价格（按转让日市场价值）", "金额", "评估报告或股权转让协议"),
               "unwind": ("现有 HOLD 所持 OP 股权在转出日的市场价值（撤销或迁出 HOLD 时按此转给 ULT 或新公司）", "金额", "评估报告"),
               "wind": ("现有 HOLD 清算时分配给股东 ULT 的全部剩余财产（含 OP 股权或其转让价款，扣除税费与负债后）", "金额", "清算方案与资产负债表"),
               "iptx": ("IP 转让价：现在持有 IP 的公司把 IP 所有权转给新持有人的价格（按转让日市场价值）", "金额", "评估报告或 IP 转让协议")}


def _question_for(key, kind, region, why, impact=None, extra="", with_=None):
    f = _field_of(key)
    gl = _gloss(f)
    m = re.match(r"^flow:(.+)\.amount$", key)
    if m and flow_name(m.group(1)) in STEP_AMOUNT:
        g_, v_, h_ = STEP_AMOUNT[flow_name(m.group(1))]
        gl = {"gloss": g_, "value": v_, "source_hint": h_}
    target = key.split(":")[0] if key.startswith(("flow:", "hold:", "calendar:")) else key.split(".")[0]
    if kind == "action":
        prompt = "能否做到：%s（%s）" % (gl.get("gloss", f), extra or key)
    elif kind == "ruling":
        prompt = "是否已取得税务机关对以下事项的书面裁定或确认：%s（%s）" % (gl.get("gloss", f), key)
    elif kind == "library":
        prompt = extra
    else:
        prompt = "请提供：%s（%s）" % (gl.get("gloss", f), key)
    if with_:
        prompt += "——须与 `%s` 同时成立才有影响" % with_
    return Question(key, kind, region, prompt, gl.get("value", ""), gl.get("source_hint", ""), sorted(why), impact,
                    FORMS.get(f, [])[:3])


def _published(gap, today):
    jur, year = gap
    if jur == "CN":
        return today >= date(year - 1, 12, 1)        # the State Council notice comes out late in the year before
    return today >= date(year - 1, 7, 1)              # MOM publishes the coming year's holidays around mid-year


# ---------------------------------------------------------------- the plan
def plan(template, event, case, answers=None, P=None, today=None) -> Outcome:
    answers = answers or Answers()
    P = P or Params()
    today = today or date.today()
    case = apply_data(case, answers)
    g0 = template.build(event, case.present, case) if case.settled else None
    evals = []
    for a in template.candidates(event, case):
        ev = evaluate(template, event, case, a, answers, P, g0)
        if ev is not None:
            evals.append(ev)
    if not evals:
        return Outcome([], None, [], "没有候选结构能保留已缴税的那几笔流。")
    plannable = [e for e in evals if not e.blocking and not e.excluded]
    best = min(plannable, key=_key) if plannable else None
    contention = sorted([e for e in evals if not e.excluded and (best is None or e is best or e.b.lo < best.b.hi - EPS)],
                        key=lambda e: e.b.lo)[:CONTENTION_MAX]
    qs: Dict[str, Question] = {}

    def add(q):
        cur = qs.get(q.key)
        if cur is None or (q.impact or 0) > (cur.impact or 0):
            qs[q.key] = q

    # 1. data without which a tax is unbounded
    for ev in contention:
        for key, grp in ev.blocking.items():
            pre = [k for k in getattr(ev, "prereq", {}).get(key, []) if not answers.answered(k)]
            for k in pre or ([key] if not answers.answered(key) else []):
                kind = getattr(ev, "joint", {}).get(k, "blocking") if getattr(ev, "joint", None) else "blocking"
                add(_question_for(k, kind, _region_of_group(grp, ev.graph), [grp[0]]))
    # 2. data and rulings that could lower the guaranteed tax or change the plan
    if best is not None:
        for ev in contention:
            by_key = {}
            for grp, ns in ev.b.groups.items():
                for n in ns:
                    if n.source in (MISSING, DISCRETION):
                        by_key.setdefault((n.source, _abs(n, grp, ev.graph, ev.b)), []).append(grp)
            for (src, key), grps in by_key.items():
                if answers.answered(key):
                    continue
                hi = _forced_hi(ev, grps, case, event, P)
                if hi is None or hi >= best.b.hi - EPS:
                    continue
                impact = round(best.b.hi - hi, 2)
                kind = "data" if src == MISSING else "ruling"
                why = sorted({"%s [%s]" % (g[0], region_name(_region_of_group(g, ev.graph))) for g in grps})
                add(_question_for(key, kind, frozenset().union(*(_region_of_group(g, ev.graph) for g in grps)), why, impact))
        # 2b. items that matter only together: on the chosen structure, a pair each worth nothing alone
        for a, b, impact, ga, gb, sa, sb in _joint_pairs(best, case, event, P, answers):
            for k, src, grps, other in ((a, sa, ga, b), (b, sb, gb, a)):
                why = sorted({"%s [%s]" % (g[0], region_name(_region_of_group(g, best.graph))) for g in grps})
                add(_question_for(k, "data" if src == MISSING else "ruling",
                                  frozenset().union(*(_region_of_group(g, best.graph) for g in grps)), why, impact, with_=other))
        # 3. the plan's own actions, if they matter
        for ak, (grp, n) in best.plan_keys.items():
            if answers.answered(ak) or Need(PLAN, ak) not in best.ticks:
                continue
            v = best.ticks[Need(PLAN, ak)]
            hi = _with_tick(best, Need(PLAN, ak), not v, case, event, P)
            if hi > best.b.hi + EPS:
                add(_question_for(ak, "action", _region_of_group(grp, best.graph), [grp[0]], round(hi - best.b.hi, 2),
                                  _action_text(ak, grp, P, v)))
        # 4. library material the deadlines need
        for labels in (best.b.L_hi,):
            for lb in labels.values():
                for name_, gap in (lb.gaps or {}).items():
                    k = "calendar:%s:%d" % gap
                    if _published(gap, today) and not answers.answered(k):
                        add(_question_for(k, "library", frozenset({gap[0]}), [name_], None,
                                          "库里缺 %s %d 年的公众假期表（官方已公布），期限顺延需要它：请提供官方公布的假期清单" % gap))
    questions = sorted(qs.values(), key=lambda q: (order_key(q.region), ["blocking", "joint", "data", "action", "ruling", "library"].index(q.kind),
                                                   -(q.impact or 0), q.key))
    if questions:
        return Outcome(questions, None, evals)
    if best is None:
        why = "; ".join(sorted({e.excluded for e in evals if e.excluded})) or "every candidate needs data that leaves a tax unbounded"
        return Outcome([], None, evals, "无法给出方案：" + why)
    return Outcome([], build_plan(best, evals, case, event, answers, P, today), evals)


ENUM_TEXT = {"REMITTED": "汇入", "DEBT_SETTLED": "用于清偿本地业务债务", "MOVABLE_PROPERTY": "购买动产带入",
             "PATENT": "专利", "KNOW_HOW": "专有技术", "SOFTWARE_COPYRIGHT": "软件著作权", "IC_LAYOUT": "集成电路布图设计",
             "PLANT_VARIETY": "植物新品种", "BIOMEDICINE_VARIETY": "生物医药新品种", "capital_increase": "增资",
             "new_entity": "新设企业", "unrelated_acquisition": "收购非关联方股权"}


def _action_text(ak, grp, P, value=True):
    """'flow:up1.holding_months:ge' on rule X -> 'flow:up1 持股月数 ≥ 12 月' with the threshold the rule reads; with
    value False the action is the opposite side ('< 12 月'; a yes/no field: 否)."""
    f = _field_of(ak)
    pred = _pred_of(ak)
    if not value and pred in OPPOSITE:
        pred = OPPOSITE[pred]
    r = RULES_BY_ID.get(grp[0])
    thr = ""
    if r is not None and r.cond is not None:
        for x in leaves(r.cond):
            if isinstance(x, Leaf) and x.field == f and x.param:
                try:
                    v = P[x.param]
                    unit = P.rows[x.param].get("unit", "")
                    if pred == "is_in":                       # an enumerated field: the side the plan takes, in words
                        thr = "：%s %s" % ("属于" if value else "不属于", "、".join(ENUM_TEXT.get(e, e) for e in str(v).split(";")))
                    else:
                        thr = " %s %s%s" % ({"ge": "≥", "gt": ">", "le": "≤", "lt": "<"}.get(pred, pred),
                                            ("%g" % v) if isinstance(v, float) else v, unit)
                except KeyError:
                    pass
                break
    target = ak.rsplit(".", 1)[0] if ak.startswith("flow:") else ak.split(".")[0]
    if f == "managed_from":
        return "%s · 实际管理机构（董事会与高管的经营决策地）设在%s" % (target, "内地以外" if value else "内地")
    if pred in ("is_true", "is_false"):
        thr = "：%s" % ("是" if pred == "is_true" else "否")
    return "%s · %s%s" % (target, _gloss(f).get("gloss", f), thr)


def build_plan(best, evals, case, event, answers, P, today):
    g, b = best.graph, best.b
    regions = {}

    def bucket(rg):
        return regions.setdefault(rg or frozenset({"—"}), {"actions": [], "guaranteed": [], "best": [], "deadlines": [], "conditions": []})

    # structure
    structure = {"entities": [], "holds": [], "flows": []}
    for e in g.entities.values():
        if e.id not in g.group():
            status = "集团外（由方案选定所在地）" if e.attrs.get("placed_by_plan") else "集团外"
        elif e.attrs.get("wound_up_by_plan"):               # 口径 D19: the client's company leaves the chain
            status = "转出所持股权后清算注销"
            took = next((f for f in g.flows if f.id == "unwind"), None)
            if took is not None:
                bucket(frozenset({e.loc})).get("actions").append(
                    ("%s（%s）把所持 %s 股权按市值转给 %s，随后清算注销、剩余财产分配给股东：两步的税已计入（流 unwind、wind）"
                     % (e.id, e.loc, took.target, took.payer), "设计", None))
        else:
            status = "新设" if e.attrs.get("created_by_plan") else ("迁移或重新安排" if e.attrs.get("placed_by_plan") else "现有")
            base = e.id[:-len(NEW)] if e.id.endswith(NEW) else None
            if base and base in case.roles and base not in g.entities:
                status = "新设（承接现有 %s 的这项业务；现有 %s 不再为 OP 提供）" % (base, base)
        structure["entities"].append((e.id, e.loc, status))
    for h in g.holds:
        how = "方案设计（全资新设）" if h.designed else ("案例陈述" if (h.holder, h.held) in case.holds else "承接原持股")
        structure["holds"].append((h.holder, h.held, h.ratio, how))
        if h.designed:
            bucket(frozenset({g.entities[h.held].loc})).get("actions").append(
                ("设立 %s（%s），由 %s 持股 %g%%；%s 只有本方案列出的各笔流" % (h.held, g.entities[h.held].loc, h.holder, h.ratio, h.held),
                 "设计", None))
    for f in g.flows:
        structure["flows"].append((f.id, f.income, f.payer, f.payee, f.amount, f.on.isoformat() if f.on else ""))
    # actions the plan relies on (only those that change the guaranteed tax)
    for ak, (grp, n) in best.plan_keys.items():
        if Need(PLAN, ak) not in best.ticks:
            continue
        v = best.ticks[Need(PLAN, ak)]
        hi = _with_tick(best, Need(PLAN, ak), not v, case, event, P)
        if hi <= b.hi + EPS:
            continue
        status = "已确认" if answers.actions.get(ak) == "yes" else "待确认"
        bucket(_region_of_group(grp, g))["actions"].append((_action_text(ak, grp, P, v), status, round(hi - b.hi, 2)))
    # taxes, guaranteed and best case; items borne outside the group are shown but not counted
    members = g.group()
    for side, labels in (("guaranteed", b.L_hi), ("best", b.L_lo)):
        for fid, lb in labels.items():
            for it in lb.items:
                if not it.effective or it.deferred:
                    continue
                amt = round(lb.flow.amount * it.effective / 100.0, 2)
                rg = item_region(it, lb, RULES_BY_ID, g)
                who = lb.flow.payer if it.borne_by == "payer" else lb.flow.payee
                bucket(rg)[side].append((fid, it.jur, it.levy, who, amt, sorted(set(it.cites)), who in members))
    # deadlines
    for fid, lb in b.L_hi.items():
        for name_, d in (lb.deadlines or {}).items():
            jur = lb.deadline_jur.get(name_)
            gap = (lb.gaps or {}).get(name_)
            note = ""
            if gap:
                note = ("该年假期表官方尚未公布，按名义日期；公布后可能顺延" if not _published(gap, today)
                        else "该年假期表缺失（已向人索取）")
            bucket(frozenset({jur}) if jur else frozenset())["deadlines"].append((fid, name_, d.isoformat() if d else "", note))
    # judgements the plan still depends on: what the authority would have to accept, and what it is worth
    seen = set()
    for grp, ns in b.groups.items():
        for n in ns:
            if n.source != DISCRETION:
                continue
            key = _abs(n, grp, g, b)
            if key in seen:
                continue
            seen.add(key)
            hi = _forced_hi(best, [x for x, y in b.groups.items() if any(_abs(m, x, g, b) == key for m in y)], case, event, P)
            upside = round(b.hi - hi, 2) if hi is not None else None
            gl = _gloss(_field_of(key)).get("gloss", _field_of(key))
            bucket(_region_of_group(grp, g))["conditions"].append((key, gl, grp[0], upside))
    present = next((e for e in evals if all(e.cand.get(k) == v for k, v in case.present.items())), None) if case.present else None
    others = sorted([e for e in evals if e is not best and not e.blocking and not e.excluded], key=_key)
    unmodelled = sorted([(e.cand, "；".join(_step_text(x) for x in e.graph.unmodelled), e.b.hi, e.b.lo)
                         for e in evals if e.graph.unmodelled and not e.blocking and e.b.hi < b.hi - EPS], key=lambda x: x[2])
    ties = [e for e in others if e.b.hi <= b.hi + EPS]               # the same guaranteed tax: equal under the criterion
    runner = [e for e in others if e.b.hi > b.hi + EPS][:1]
    data_used = [(k, answers.value(k), (v.get("source") if isinstance(v, dict) else "")) for k, v in answers.data.items()]
    totals = {rg: (round(sum(x[4] for x in d["guaranteed"] if x[6]), 2), round(sum(x[4] for x in d["best"] if x[6]), 2))
              for rg, d in regions.items()}
    claims_ = []
    if case.settled:
        from .claims import claims as _claims
        cl, archived = _claims(b, case.settled, event.as_at, g)
        claims_ = [(c.flow, c.jur, c.actual, c.lo, c.hi, c.confirmed, c.potential, c.shortfall,
                    {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in c.deadlines.items()}, [r[0] for r in c.routes])
                   for c in cl] + [(f_, j_, None, None, None, None, None, None, {}, ["已结"]) for f_, j_ in archived]
    return {"cand": best.cand, "guaranteed": b.hi, "best": b.lo, "structure": structure,
            "regions": dict(sorted(regions.items(), key=lambda kv: order_key(kv[0]))), "totals": totals,
            "present": (present.cand, present.b.hi, present.b.lo) if present else None,
            "runner_up": (runner[0].cand, runner[0].b.hi, runner[0].b.lo) if runner else None,
            "ties": [(e.cand, e.b.hi, e.b.lo) for e in ties],
            "data_used": data_used, "claims": claims_, "unmodelled": unmodelled,
            "notes": (["新设公司（若有）按方案设计视为只有所列各笔流；改为有其他业务时须重新运行。"]
                      if any(e.attrs.get("created_by_plan") for e in g.entities.values()) else [])
            + ["流 %s（%s）早于%s施行（%s）：其%s由集团外的 %s 承担，库内没有此前的规定，未计算，不影响集团税额（口径 D30）。"
               % (x[1], x[2], x[3], x[4], x[5], x[6]) for x in outside_steps(b, g)[1]]}


# ---------------------------------------------------------------- rendering
def render(template, event, outcome, case_name=""):
    L = []
    w = L.append
    if outcome.questions:
        w("# 问题单：%s（模板 %s）" % (case_name, template.name))
        w("")
        w("方案尚不能给出：下列数据或确认会改变所选方案或其保证税额。只需答这些；答不上请填 unknown（按最不利处理，不会补值）。")
        w("答复写进 `<案例名>.answers.json`：data（数值或 {\"value\", \"source\"}）、actions（yes / no / unknown）、rulings（yes / no / unknown）、library。")
        cur = None
        for q in outcome.questions:
            if q.region != cur:
                cur = q.region
                w("")
                w("## %s" % region_name(q.region))
                w("")
                w("| 类型 | 地址 | 问题 | 取值 | 常见出处 | 影响 |")
                w("|---|---|---|---|---|---|")
            kind = {"blocking": "必答（缺则税额无界）", "joint": "必答（相互影响的未决项太多，缺则无法精确计算）", "data": "数据",
                    "action": "动作可行性", "ruling": "裁定", "library": "资料"}[q.kind]
            imp = "可使保证税额下降 %.2f" % q.impact if q.impact else ({"blocking": "无界", "joint": "无法精确计算"}.get(q.kind, "—"))
            hint = q.source_hint + ("；表单：" + "；".join(q.forms) if q.forms else "")
            w("| %s | `%s` | %s | %s | %s | %s |" % (kind, q.key, q.prompt, q.value, hint, imp))
        w("")
        w("候选结构 %d 个；其中需要上面必答数据才能计算的 %d 个。" % (len(outcome.evaluations), sum(1 for e in outcome.evaluations if e.blocking)))
        return "\n".join(L) + "\n"
    if outcome.plan is None:
        w("# 无法给出方案：%s" % case_name)
        w("")
        w(outcome.note)
        return "\n".join(L) + "\n"
    p = outcome.plan
    w("# 方案：%s（模板 %s）" % (case_name, template.name))
    w("")
    w("**结构**：%s" % ("，".join("%s=%s" % kv for kv in p["cand"].items()) or "唯一结构"))
    w("")
    w("**保证税额**（所有裁量项按不利、未知数据按不利）：%.2f；**最好情形**（裁量项全部有利）：%.2f。" % (p["guaranteed"], p["best"]))
    if p["present"]:
        w("")
        w("**现状**：保证 %.2f / 最好 %.2f。" % (p["present"][1], p["present"][2]))
    if p.get("ties"):
        w("**保证税额相同的其他结构**（按最好情形、再按待定裁量项少、再按公司少取了本方案；能改变它们先后的只有不影响保证税额的数据，不再询问）：%s。" % (
            "；".join("%s（最好 %.2f）" % (c, lo) for c, hi, lo in p["ties"])))
    if p["runner_up"]:
        w("**次优**：%s，保证 %.2f / 最好 %.2f。" % (p["runner_up"][0], p["runner_up"][1], p["runner_up"][2]))
    if p.get("unmodelled"):
        w("")
        w("**未作为方案的结构**（需要的步骤本程序尚未建模，下列数字不含该步骤的税；该步骤的税低于差额时才可能更优）：%s。" % "；".join(
            "%s：%s，不含该步骤时保证 %.2f / 最好 %.2f，比本方案低 %.2f" % (c, why, hi, lo, p["guaranteed"] - hi)
            for c, why, hi, lo in p["unmodelled"]))
    w("")
    w("## 分区汇总")
    w("")
    w("| 区 | 保证税额 | 最好情形 | 动作 | 期限 | 待机关认可的条件 |")
    w("|---|---|---|---|---|---|")
    for rg, d in p["regions"].items():
        tg, tb = p["totals"].get(rg, (0, 0))
        w("| %s | %.2f | %.2f | %d | %d | %d |" % (region_name(rg), tg, tb, len(d["actions"]), len(d["deadlines"]), len(d["conditions"])))
    for rg, d in p["regions"].items():
        w("")
        w("## %s" % region_name(rg))
        if d["actions"]:
            w("")
            w("要做的事：")
            for text, status, worth in d["actions"]:
                w("- %s（%s%s）" % (text, status, "；不做则保证税额上升 %.2f" % worth if worth else ""))
        if d["guaranteed"]:
            w("")
            w("税项（保证口径）：")
            for fid, jur, levy, who, amt, cites, mine in d["guaranteed"]:
                w("- %s · %s · %s · %s 承担%s · %.2f · %s" % (fid, jur, levy, who, "" if mine else "（集团外，不计入）", amt, ", ".join(cites)))
        if d["deadlines"]:
            w("")
            w("期限：")
            for fid, name_, dd, note in d["deadlines"]:
                w("- %s · %s · %s%s" % (fid, name_, dd, "（%s）" % note if note else ""))
        if d["conditions"]:
            w("")
            w("仍取决于税务机关认可的条件：")
            for key, gl, rule, upside in d["conditions"]:
                w("- %s（%s，规则 %s）%s" % (gl, key, rule, "：若认可，税额最多下降 %.2f" % upside if upside else ""))
    if p.get("claims"):
        w("")
        w("## 已缴税款：可追回与补税风险")
        for fl, jur, actual, lo, hi, conf, pot, short, clocks, routes in p["claims"]:
            if actual is None:
                w("- %s / %s：已结（时钟全部过期或声明），无主张" % (fl, jur))
                continue
            w("- %s / %s：实缴 %.2f；规则口径 [%.2f, %.2f]；确定可追回 %.2f，最多可追回 %.2f；补税风险 [%.2f, %.2f]；时钟 %s；路线 %s" % (
                fl, jur, actual, lo, hi, conf, pot, short[0], short[1], clocks, " → ".join(routes)))
    w("")
    w("## 结构明细")
    for e in p["structure"]["entities"]:
        w("- 公司 %s · %s · %s" % e)
    for h in p["structure"]["holds"]:
        w("- 持股 %s → %s · %g%% · %s" % h)
    for f in p["structure"]["flows"]:
        w("- 流 %s · %s · %s → %s · %.2f · %s" % f)
    if p["data_used"]:
        w("")
        w("## 所用答复")
        for k, v, src in p["data_used"]:
            w("- %s = %s%s" % (k, v, "（%s）" % src if src else ""))
    if p["notes"]:
        w("")
        w("## 方案的设计前提")
        for n in p["notes"]:
            w("- " + n)
    return "\n".join(L) + "\n"
