"""Li atlas projections over an explicitly supplied, verified library snapshot.

Adapted from LiZiheng commit140a9ef. No global reader, network lookup or cache.
The rule engine state must be created in an isolated process, not a web worker.
"""
from datetime import date as _date
from copy import deepcopy
import re

# ISO 3166-1 numeric ids as Natural Earth writes them (the map's country ids)
ISO = {"cn": "156", "hk": "344", "sg": "702", "jp": "392", "th": "764", "id": "360", "vn": "704", "my": "458", "ae": "784",
       "kr": "410", "in": "356"}
NAME_ZH = {"cn": "中国内地", "hk": "中国香港", "sg": "新加坡", "jp": "日本", "th": "泰国", "id": "印度尼西亚", "vn": "越南",
           "my": "马来西亚", "ae": "阿联酋", "kr": "韩国", "in": "印度"}
SLOTS = ["residence", "outbound_wht", "inbound", "final", "cfc", "anti_abuse", "restructure", "exit", "penalty"]
SLOT_TEXT = {
    "residence": ("Residence", "税收居民", "Who the jurisdiction treats as its resident: the tests for companies and individuals that decide where income is taxed in full.",
                  "辖区认定谁是本地税收居民：公司和个人的判定标准，决定在哪里就全部所得纳税。"),
    "outbound_wht": ("Withholding tax", "预提所得税", "Tax the paying jurisdiction withholds from a dividend paid to a non-resident, before any treaty relief or with it.",
                     "付款地对支付给非居民的股息代扣的税款，分无协定和适用协定两种情形。"),
    "inbound": ("Foreign dividends received", "境外股息的处理", "How a resident recipient treats a dividend from abroad: included, exempt, credited or taxed only when received.",
                "居民收款方如何处理来自境外的股息：计入、免税、抵免，或汇入时才征税。"),
    "final": ("Tax on the recipient", "收款方所得税", "The income tax rate or schedule the recipient finally bears on the dividend in its own jurisdiction.",
              "收款方在本地对股息最终承担的所得税率或累进表。"),
    "cfc": ("Controlled foreign companies", "受控外国公司", "Rules that tax a resident on the undistributed profit of a low-taxed foreign company it controls.",
            "对居民控制的低税外国公司的未分配利润，在居民层面征税的规则。"),
    "anti_abuse": ("Anti-abuse", "反滥用", "Beneficial ownership, principal purpose tests and general anti-avoidance rules that can deny a lower rate.",
                   "受益所有人、主要目的测试和一般反避税规则，可能否定较低税率。"),
    "restructure": ("Restructuring taxes", "重组税负", "Taxes a share transfer or reorganisation triggers once: capital gains, stamp duty, transfer taxes.",
                    "股权转让或重组一次性触发的税负：资本利得、印花税、转让税。"),
    "exit": ("Exit taxes", "退出税", "Tax on leaving the jurisdiction: deemed disposal when a company or individual ceases to be resident.",
             "离开辖区时的税负：公司或个人不再是居民时的视同处置。"),
    "penalty": ("Penalties and deadlines", "罚则与期限", "Withholding deadlines, late-payment interest and penalties for under-withholding.",
                "代扣代缴期限、滞纳金和少扣税款的罚则。"),
}
METRICS = {"wht_company": "company", "wht_individual": "individual"}
HEADLINE = {"payer_listed": False, "holding_pct": 100, "holding_months": 24}      # unlisted payer, 100% held for two years
QUALIFYING = {"payer_listed": False, "holding_pct": 100, "holding_months": 24, "days_present": 365}
PORTFOLIO = {"payer_listed": False, "holding_pct": 5, "holding_months": 3, "days_present": 365}
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_.]*")

def today(value):
    if not value:
        return _date.today().isoformat()
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('invalid_atlas_date')
    try:
        return _date.fromisoformat(value).isoformat()
    except ValueError:
        raise ValueError('invalid_atlas_date') from None


def favourable(st):
    return {p["key"]: p["favourable"] for p in st["q"].predicates() if p.get("favourable")}


def resident(code, subject):
    """The recipient's facts that make it resident of its jurisdiction under that jurisdiction's own tests."""
    if subject == "individual":
        return {"domicile_in": code, "ordinarily_resides": True, "days_present": 365}
    return {"incorporated_in": code, "managed_in": code}


def cell(st, slot_key, d, facts, answers=None):
    """One cell as the rule layer's tax-rule server evaluates it: for a treaty cell the recipient's residence comes first,
    from the residence cell of its own jurisdiction (rule/tools/mcp_server.py cell_facts)."""
    facts, answers = dict(facts), dict(answers or {})
    jur, subject, slot, other = slot_key.split("|")
    if slot == "outbound_wht" and other != "*":
        facts.update(resident(other, subject))
        res = st["ev"].eval_cell(st["rs"], "%s|%s|residence|*" % (other, subject), d, facts, answers, "plan")
        facts["payee_resident"] = st["ev"].tri(res, "payee_resident")
    it = st["ev"].eval_cell(st["rs"], slot_key, d, facts, answers, "plan")
    side = lambda s: (it.get(s) or {}).get("value")
    rules = sorted(set((it.get("floor") or {}).get("rules", [])) | set((it.get("ceiling") or {}).get("rules", [])))
    return {"floor": side("floor"), "ceiling": side("ceiling"), "status": it.get("status"), "value_kind": it.get("value_kind"),
            "needs": [n[1] for n in it.get("needs", [])], "rules": rules, "cite_ids": it.get("cite_ids", [])}


def absences(st, jur, slot="", subject=""):
    return [{"id": a["id"], "statement": a["statement"], "cite_id": a["cite_id"], "quote": a.get("quote", ""), "subject": a.get("subject", "")}
            for a in st["lib"].absences if a.get('jur') == jur
            and (not slot or a.get('slot') in ('', slot))
            and (not subject or a.get("subject") in ("", subject, "all"))]


def juris(st):
    return [j for j in st["lib"].juris if j["code"] in ISO]


# ---------------------------------------------------------------- the map
def map_data(st, d):
    d = today(d)

    def build(st):
        rows = []
        for j in juris(st):
            code = j["code"]
            row = {"code": code, "iso": ISO[code], "name": j["name"], "name_zh": NAME_ZH.get(code, j["name"]), "currency": j["currency"]}
            for metric, subject in METRICS.items():
                c = cell(st, "%s|%s|outbound_wht|*" % (code, subject), d, HEADLINE)
                if c["ceiling"] is None:
                    c["absent"] = absences(st, code, "outbound_wht", subject)
                row[metric] = c
            rows.append(row)
        return {"date": d, "version": version(st), "metrics": list(METRICS), "facts": HEADLINE, "jurisdictions": rows}
    return deepcopy(build(st))


def version(st):
    from copy import deepcopy
    metadata = deepcopy(st['version'])
    return {'library': metadata['bundle_sha256'], 'source': 'reviewed snapshot',
            'rules': len(st['rs'].rules), 'snapshot': metadata}


# ---------------------------------------------------------------- one jurisdiction
def pair_params(st, a, b):
    return [p for p in st["lib"].params.values() if p["scope"] in ("%s-%s" % (a, b), "%s-%s" % (b, a))]


def country(st, code, d):
    d = today(d)

    def build(st):
        j = next((x for x in juris(st) if x["code"] == code), None)
        if j is None:
            return None
        lib, fav = st["lib"], favourable(st)
        head = {m: cell(st, "%s|%s|outbound_wht|*" % (code, s), d, HEADLINE) for m, s in METRICS.items()}
        for m, s in METRICS.items():
            if head[m]["ceiling"] is None:
                head[m]["absent"] = absences(st, code, "outbound_wht", s)
        partners = []
        for p in juris(st):
            if p["code"] == code:
                continue
            pc = p["code"]
            treaties = [{"pair": t["pair"], "doc_id": t["doc_id"], "in_force_from": t.get("in_force_from", ""), "title": t.get("title", ""),
                         "mli": bool(t.get("mli_doc_id")), "url": lib.docs.get(t["doc_id"], {}).get("url", "")}
                        for t in [lib.treaty(code, pc)] if t]
            pp = {x["name"]: x for x in pair_params(st, code, pc) if x["slot"] == "outbound_wht" and lib.param_effective(x["param_id"], d) and not x.get("superseded_by")}
            partners.append({
                "code": pc, "name": p["name"], "name_zh": NAME_ZH.get(pc, p["name"]), "treaty": treaties,
                "qualifying": cell(st, "%s|company|outbound_wht|%s" % (code, pc), d, QUALIFYING, fav),
                "portfolio": cell(st, "%s|company|outbound_wht|%s" % (code, pc), d, PORTFOLIO, fav),
                "individual": cell(st, "%s|individual|outbound_wht|%s" % (code, pc), d, PORTFOLIO, fav),
                "conditions": {k: {"value": pp[k]["value"], "unit": pp[k]["unit"], "cite_id": pp[k]["cite_id"], "quote": pp[k]["quote"]}
                               for k in ("holding_pct_min", "holding_months_min") if k in pp},
            })
        params = [p for p in lib.params.values() if p["scope"] == code or code in p["scope"].split("-")]
        params.sort(key=lambda p: (SLOTS.index(p["slot"]) if p["slot"] in SLOTS else 99, "-" in p["scope"], p["scope"], p["subject"], p["param_id"]))
        docs = sorted(({"id": x["id"], "title": x.get("title", ""), "type": x.get("type", ""), "url": x.get("url", ""), "lang": x.get("lang", ""),
                        "effective_from": x.get("effective_from", ""), "effective_to": x.get("effective_to", "")}
                       for x in lib.docs.values() if x.get("jur") == code), key=lambda x: (x["type"], x["id"]))
        cit = next((p for p in params if p["scope"] == code and p["slot"] == "final" and p["name"] == "cit_rate" and lib.param_effective(p["param_id"], d) and not p.get("superseded_by")), None)
        return {"date": d, "version": version(st), "code": code, "iso": ISO[code], "name": j["name"], "name_zh": NAME_ZH.get(code, j["name"]),
                "currency": j["currency"], "headline": head, "facts": {"headline": HEADLINE, "qualifying": QUALIFYING, "portfolio": PORTFOLIO},
                "cit": {"value": cit["value"], "unit": cit["unit"], "cite_id": cit["cite_id"]} if cit else None,
                "partners": partners, "slots": [{"slot": s, "title": SLOT_TEXT[s][0], "title_zh": SLOT_TEXT[s][1]} for s in SLOTS],
                "params": [slim_param(p) for p in params], "absent": absences(st, code), "docs": docs,
                "terms": terms(st, code), "assumed_judgments": fav, "scope": "illustrative_dividend_scenarios_not_case_assessment"}
    return deepcopy(build(st))


def slim_param(p):
    return {k: p.get(k, "") for k in ("param_id", "scope", "subject", "slot", "name", "value", "unit", "cite_id", "quote",
                                      "effective_from", "effective_to", "note", "superseded_by")}


# ---------------------------------------------------------------- glossary
def rule_vars(st):
    """name -> {jurisdictions, rules, cite_ids}: the fields and judgment points each rule's condition reads."""
    known = {v["name"] for v in st["q"].variables()} | {p["key"] for p in st["q"].predicates()}
    out = {}
    for r in st["rs"].rules:
        names = {n.split(".")[-1] for n in IDENT.findall(r.get("condition") or "")} & known
        jur = r["slot_key"].split("|")[0]
        for n in names:
            o = out.setdefault(n, {"jurisdictions": set(), "rules": set(), "cite_ids": set()})
            o["jurisdictions"].add(jur.split("-")[0])
            o["rules"].add(r["id"])
            o["cite_ids"].update(c for c in (r.get("cite_ids") or "").split(";") if c)
    return out


def split(x):
    return [str(v) for v in x] if isinstance(x, (list, tuple)) else [v for v in str(x or "").split(";") if v]


def terms(st, code=None):
    used = rule_vars(st)
    out = []
    for v in st["q"].variables():
        u = used.get(v["name"])
        if code and (not u or code not in u["jurisdictions"]):
            continue
        out.append({"key": v["name"], "kind": v.get("kind", ""), "type": v.get("type", ""), "allowed": v.get("allowed_values", ""),
                    "question": v.get("question", ""), "meaning": v.get("meaning", ""),
                    "jurisdictions": sorted(u["jurisdictions"]) if u else [], "cite_ids": sorted(u["cite_ids"])[:8] if u else []})
    for p in st["q"].predicates():
        u = used.get(p["key"])
        if code and (not u or code not in u["jurisdictions"]):
            continue
        cites = [c for c in split(p.get("factors_cite")) if c]
        factors = ", ".join(split(p.get("factor_vars")))
        out.append({"key": p["key"], "kind": "judgment", "type": "yes/no", "allowed": "", "question": p.get("question", ""),
                    "meaning": "A legal judgment the client or an adviser confirms; the system evaluates both answers."
                               + (" Factors: %s." % factors if factors else ""),
                    "jurisdictions": sorted(u["jurisdictions"]) if u else [], "cite_ids": (cites + sorted(u["cite_ids"]) if u else cites)[:8]})
    return out


def glossary(st):
    def build(st):
        return {"version": version(st), "slots": [{"slot": s, "title": SLOT_TEXT[s][0], "title_zh": SLOT_TEXT[s][1], "text": SLOT_TEXT[s][2],
                                                   "text_zh": SLOT_TEXT[s][3]} for s in SLOTS],
                "terms": terms(st), "jurisdictions": [{"code": j["code"], "name": j["name"], "name_zh": NAME_ZH.get(j["code"], j["name"])} for j in juris(st)]}
    return deepcopy(build(st))


def clause(st, cite_id):
    c = st['lib'].source(cite_id)
    doc_id = c.get('doc_id') or c.get('source_id') or cite_id.split('#')[0]
    doc = st['lib'].docs.get(doc_id, {})
    return {'cite_id': cite_id, 'doc_id': doc_id, 'label': c.get('label', ''),
            'text': c['passage'], 'total': len(c['passage']),
            'passage_sha256': c['passage_sha256'], 'version': version(st),
            **{key: c.get(key) or doc.get(key, '') for key in ('title', 'url', 'lang', 'jur')}}
