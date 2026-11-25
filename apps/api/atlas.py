"""Tax graph for the web host: dividend tax across the library's jurisdictions, a page per jurisdiction and a glossary.

Every rate is evaluated by the rule layer (rule/tools/eval.py); every provision, parameter, treaty, absence record and
document comes from the library. With tax_db=supabase both read the shared Supabase database (database/tools/dbsource.py),
never a copy, so the map follows each upload. Read-only; results are cached per library version and date.
"""
import importlib.util
import json
import re
import sys
import threading
from datetime import date as _date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RULE_TOOLS, DB_TOOLS = ROOT / "rule" / "tools", ROOT / "database" / "tools"

# ISO 3166-1 numeric ids as Natural Earth writes them (the map's country ids)
ISO = {"cn": "156", "hk": "344", "sg": "702", "jp": "392", "th": "764", "id": "360", "vn": "704", "my": "458", "ae": "784",
       "kr": "410", "in": "356"}
LOCALES = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (Path(__file__).resolve().parent / "locales").glob("*.json")}
NAME_ZH = LOCALES.get("zh", {}).get("jurisdictions", {})
SLOTS = ["residence", "outbound_wht", "inbound", "final", "cfc", "anti_abuse", "restructure", "exit", "penalty"]
SLOT_EN = {
    "residence": ("Residence", "Who the jurisdiction treats as its resident: the tests for companies and individuals that decide where income is taxed in full."),
    "outbound_wht": ("Withholding tax", "Tax the paying jurisdiction withholds from a dividend paid to a non-resident, before any treaty relief or with it."),
    "inbound": ("Foreign dividends received", "How a resident recipient treats a dividend from abroad: included, exempt, credited or taxed only when received."),
    "final": ("Tax on the recipient", "The income tax rate or schedule the recipient finally bears on the dividend in its own jurisdiction."),
    "cfc": ("Controlled foreign companies", "Rules that tax a resident on the undistributed profit of a low-taxed foreign company it controls."),
    "anti_abuse": ("Anti-abuse", "Beneficial ownership, principal purpose tests and general anti-avoidance rules that can deny a lower rate."),
    "restructure": ("Restructuring taxes", "Taxes a share transfer or reorganisation triggers once: capital gains, stamp duty, transfer taxes."),
    "exit": ("Exit taxes", "Tax on leaving the jurisdiction: deemed disposal when a company or individual ceases to be resident."),
    "penalty": ("Penalties and deadlines", "Withholding deadlines, late-payment interest and penalties for under-withholding."),
}
SLOT_TEXT = {k: (en[0], LOCALES.get("zh", {}).get("slots", {}).get(k, {}).get("title", en[0]), en[1],
                 LOCALES.get("zh", {}).get("slots", {}).get(k, {}).get("text", en[1])) for k, en in SLOT_EN.items()}
METRICS = {"wht_company": "company", "wht_individual": "individual"}
HEADLINE = {"payer_listed": False, "holding_pct": 100, "holding_months": 24}      # unlisted payer, 100% held for two years
QUALIFYING = {"payer_listed": False, "holding_pct": 100, "holding_months": 24, "days_present": 365}
PORTFOLIO = {"payer_listed": False, "holding_pct": 5, "holding_months": 3, "days_present": 365}
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_.]*")

_lock = threading.RLock()
_st = {}


def state():
    """The rule set and the library, loaded once: the rule layer and the library MCP server's reader, both on dbsource."""
    with _lock:
        if not _st:
            if str(RULE_TOOLS) not in sys.path:
                sys.path.insert(0, str(RULE_TOOLS))
            import eval as ev                                   # noqa: E402  rule/tools/eval.py
            from query import Query                             # noqa: E402
            spec = importlib.util.spec_from_file_location("tax_db_library", DB_TOOLS / "mcp_server.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            q = Query()
            lib = mod.Library(ROOT / "database")
            _st.update(ev=ev, q=q, rs=q.rs, lib=lib, cache={}, version=lib.version_info())
        return _st


def warm():
    threading.Thread(target=lambda: (state(), map_data("")), daemon=True).start()


def today(d):
    return d if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d or "") else _date.today().isoformat()


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
            for a in st["lib"]._absent(jur, slot) if not subject or a.get("subject") in ("", subject, "all")]


def juris(st):
    return [j for j in st["lib"].juris if j["code"] in ISO]


def cached(key, build):
    st = state()
    key = (version(st)["library"],) + key
    with _lock:
        if key not in st["cache"]:
            st["cache"][key] = build(st)
        return st["cache"][key]


# ---------------------------------------------------------------- the map
def map_data(d):
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
    return cached(("map", d), build)


def version(st):
    v = (st["version"].get("version") or {}).get("database") or {}
    return {"library": v.get("uploaded_at") or v.get("param_csv_sha256", ""), "source": v.get("source") or ("supabase" if st["lib"].remote else "local files"),
            "rules": len(st["rs"].rules), "docs": v.get("docs"), "clauses": v.get("clauses"), "params": v.get("params")}


# ---------------------------------------------------------------- one jurisdiction
def pair_params(st, a, b):
    return [p for p in st["lib"].params.values() if p["scope"] in ("%s-%s" % (a, b), "%s-%s" % (b, a))]


def country(code, d):
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
                        for t in lib.treaty(code, pc).get("rows", [])]
            pp = {x["name"]: x for x in pair_params(st, code, pc) if x["slot"] == "outbound_wht"}
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
        cit = next((p for p in params if p["scope"] == code and p["slot"] == "final" and p["name"] == "cit_rate"), None)
        return {"date": d, "version": version(st), "code": code, "iso": ISO[code], "name": j["name"], "name_zh": NAME_ZH.get(code, j["name"]),
                "currency": j["currency"], "headline": head, "facts": {"headline": HEADLINE, "qualifying": QUALIFYING, "portfolio": PORTFOLIO},
                "cit": {"value": cit["value"], "unit": cit["unit"], "cite_id": cit["cite_id"]} if cit else None,
                "partners": partners, "slots": [{"slot": s, "title": SLOT_TEXT[s][0], "title_zh": SLOT_TEXT[s][1]} for s in SLOTS],
                "params": [slim_param(p) for p in params], "absent": absences(st, code), "docs": docs,
                "terms": terms(st, code)}
    return cached(("country", code, d), build)


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


def glossary():
    def build(st):
        return {"version": version(st), "slots": [{"slot": s, "title": SLOT_TEXT[s][0], "title_zh": SLOT_TEXT[s][1], "text": SLOT_TEXT[s][2],
                                                   "text_zh": SLOT_TEXT[s][3]} for s in SLOTS],
                "terms": terms(st), "jurisdictions": [{"code": j["code"], "name": j["name"], "name_zh": NAME_ZH.get(j["code"], j["name"])} for j in juris(st)]}
    return cached(("glossary",), build)


def clause(cite_id):
    st = state()
    c = st["lib"].clause(cite_id, 0, 8000)
    if c.get("error"):
        return None
    doc = st["lib"].docs.get(c.get("doc_id"), {})
    return {"cite_id": cite_id, "doc_id": c.get("doc_id"), "label": c.get("label", ""), "text": c.get("text", ""), "total": c.get("total"),
            "title": doc.get("title", ""), "url": doc.get("url", ""), "lang": doc.get("lang", ""), "jur": doc.get("jur", "")}
