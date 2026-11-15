#!/usr/bin/env python
"""Exchange rates for the optimization layer (优化层规范.md §3, input 汇率).

The library has no exchange rates (the rule layer says the conversion into the recipient's currency is the caller's).
This tool fetches them and writes a JSON file in which every number carries its source, URL and date, so that
`amount_payee_ccy` in hop facts can be traced. With --jur it applies the rate prescribed by that jurisdiction's tax law:
the rule itself is read from database/param.csv (parameters <jur>.<slot>.fx_rate_*, each citing its clause) and the
number is taken from the matching source:

  cn   RMB central parity of the China Foreign Exchange Trade System (CFETS, chinamoney.com.cn), the official figure;
       day per the rule (withholding: the payment day; company income: last day of the month; individual: last day of
       the previous month); no parity on a non-business day -> the last earlier business day.
  jp   TTM = (TTS + TTB) / 2 of the taxpayer's main bank; there is no official TTM, so MUFG Bank's daily quotation
       (published by MURC, murc-kawasesouba.jp) is used as a REPRESENTATIVE rate and labelled so; earlier nearest day
       when the day has no quotation (circular 13-2-1-2 note 3).
  th   Bank of Thailand daily reference rate (average selling for withholding, average buying for income received),
       through the BoT API when `bot_api_key` is set in .env; otherwise the market rate, labelled as a substitute.
  sg, hk  no prescribed rate: market mid rate of the day, labelled so.
Other currencies and jurisdictions: Frankfurter (ECB reference rates, dated) and the exchangerate-api open endpoint
(latest daily, fills VND / AED), both labelled.

  python optimization/tools/fx.py --base CNY --date 2026-04-30 [--jur hk --role inbound --subject company]
                                  [--symbols HKD,SGD,...] [--out products/<case>/fx.json]

Rates are "units of the target currency per 1 unit of --base". Python 3.11, standard library only.
Exit code 0 when every requested currency has a rate, 2 otherwise.
"""
import argparse
import calendar
import csv
import io
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import date as _date, datetime, timedelta, timezone
from pathlib import Path

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
TIMEOUT = 30
UA = {"User-Agent": "Mozilla/5.0 tax-graph-fx/1.1"}
OPEN_ER = "https://open.er-api.com/v6/latest/%s"
FRANKFURTER = "https://api.frankfurter.dev/v1/%s?base=%s&symbols=%s"
CFETS_HIS = "https://www.chinamoney.com.cn/ags/ms/cm-u-bk-ccpr/CcprHisNew"
MURC_PAST = "https://www.murc-kawasesouba.jp/fx/past/index.php?id=%s"
MURC_TODAY = "https://www.murc-kawasesouba.jp/fx/index.php"
BOT_API = "https://apigw1.bot.or.th/bot/public/Stat-ExchangeRate/v2/DAILY_AVG_EXG_RATE/?start_period=%s&end_period=%s&currency=%s"
JUR_CCY = {"cn": "CNY", "hk": "HKD", "sg": "SGD", "jp": "JPY", "th": "THB", "id": "IDR", "vn": "VND", "my": "MYR",
           "ae": "AED", "kr": "KRW", "in": "INR"}


def http(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=dict(UA, **(headers or {})))
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


def get_json(url, data=None, headers=None):
    return json.loads(http(url, data, headers).decode("utf-8"))


def library_currencies(db=ROOT / "database"):
    path = db / "jurisdiction.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return sorted({r["currency"] for r in csv.DictReader(f) if r.get("currency")})


def env_value(name, env=ROOT / ".env"):
    """One value of .env, never printed."""
    if not env.exists():
        return ""
    for line in env.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.strip().lower().startswith(name.lower() + "="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


# ---------------------------------------------------------------- the rule of the jurisdiction (database parameters)
def fx_rule(jur, role, subject, db=ROOT / "database"):
    """Parameters <jur>.<slot>.fx_rate_* of the slot that fits the role, with their citations."""
    slot = "outbound_wht" if role == "outbound" else "inbound"
    out = []
    with (db / "param.csv").open(encoding="utf-8-sig", newline="") as f:
        for p in csv.DictReader(f):
            if p["scope"] == jur and p["slot"] == slot and p["name"].startswith("fx_rate_") and p["subject"] in (subject, "all"):
                out.append({k: p[k] for k in ("param_id", "subject", "value", "cite_id", "quote", "note")})
    return out


def rule_day(jur, role, subject, d):
    """The day whose rate the rule prescribes (optimization spec §3): cn company income = month end, cn individual =
    last day of the previous month, otherwise the payment / transaction day."""
    if jur == "cn" and role == "inbound":
        if subject == "individual":
            first = d.replace(day=1)
            return first - timedelta(days=1), "last day of the previous month (IIT Reg. art. 32)"
        return d.replace(day=calendar.monthrange(d.year, d.month)[1]), "last day of the month (EIT Reg. art. 129)"
    return d, "the payment / transaction day"


# ---------------------------------------------------------------- sources
def cfets_parity(base, target, d):
    """CFETS central parity on the last business day <= d: target per 1 base, where one of them is CNY."""
    other = target if base == "CNY" else base
    pairs = {"JPY": "100JPY/CNY", "USD": "USD/CNY", "EUR": "EUR/CNY", "HKD": "HKD/CNY", "GBP": "GBP/CNY", "AUD": "AUD/CNY",
             "NZD": "NZD/CNY", "SGD": "SGD/CNY", "CHF": "CHF/CNY", "CAD": "CAD/CNY", "MOP": "CNY/MOP", "MYR": "CNY/MYR",
             "RUB": "CNY/RUB", "ZAR": "CNY/ZAR", "KRW": "CNY/KRW", "AED": "CNY/AED", "SAR": "CNY/SAR", "THB": "CNY/THB"}
    pair = pairs.get(other)
    if not pair:
        return None
    start = d - timedelta(days=14)
    body = urllib.parse.urlencode({"startDate": start.isoformat(), "endDate": d.isoformat(), "currency": pair}).encode()
    data = get_json(CFETS_HIS, body, {"Content-Type": "application/x-www-form-urlencoded"})
    recs = sorted(data.get("records", []), key=lambda r: r["date"])
    if not recs:
        return None
    rec = recs[-1]
    v = float(rec["values"][0])
    cny_per_other = v / 100 if pair.startswith("100") else (v if pair.endswith("/CNY") else 1 / v)   # CNY per 1 other
    rate = (1 / cny_per_other) if base == "CNY" else cny_per_other
    return {"rate": rate, "source": "CFETS RMB central parity (%s)" % pair, "url": CFETS_HIS, "date": rec["date"],
            "note": "" if rec["date"] == d.isoformat() else "no parity on %s; last business day %s" % (d.isoformat(), rec["date"])}


def murc_ttm(base, target, d):
    """MUFG Bank TTM (JPY per 1 unit of the foreign currency) from the MURC daily table, for the nearest day <= d."""
    other = target if base == "JPY" else base
    today = _date.today()
    for back in range(0, 10):
        day = d - timedelta(days=back)
        url = MURC_TODAY if day >= today else MURC_PAST % day.strftime("%y%m%d")
        try:
            raw = http(url)
        except Exception:                                           # noqa: BLE001
            continue
        txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw.decode("shift_jis", "ignore")))
        m = re.search(r"As of ([A-Za-z]+ \d{1,2}, \d{4})", txt)
        asof = datetime.strptime(m.group(1), "%B %d, %Y").date().isoformat() if m else day.isoformat()
        if day < today and asof != day.isoformat():                 # the past page of a holiday redirects to today's table
            continue
        mm = re.search(r"\b%s\b\s+([\d.]+)\s+([\d.]+)" % other, txt)
        if not mm:
            return None
        tts, ttb = float(mm.group(1)), float(mm.group(2))
        per_unit = 100 if other in ("IDR", "KRW", "VND") else 1      # MURC quotes some currencies per 100 units
        jpy_per_other = (tts + ttb) / 2 / per_unit
        rate = jpy_per_other if base != "JPY" else 1 / jpy_per_other
        return {"rate": rate, "source": "representative TTM: MUFG Bank TTS %.2f / TTB %.2f via MURC" % (tts, ttb), "url": url,
                "date": asof, "note": "no official TTM; the taxpayer's main bank's rate is the rule (circular 13-2-1-2)"
                + ("" if asof == d.isoformat() else "; nearest earlier day")}
    return None


def bot_reference(base, target, d, role):
    """Bank of Thailand daily reference rate via the BoT API (needs bot_api_key in .env): THB per 1 unit."""
    key = env_value("bot_api_key")
    if not key:
        return None
    other = target if base == "THB" else base
    start = d - timedelta(days=10)
    url = BOT_API % (start.isoformat(), d.isoformat(), other)
    data = get_json(url, headers={"X-IBM-Client-Id": key, "accept": "application/json"})
    detail = data.get("result", {}).get("data", {}).get("data_detail", [])
    detail = sorted(detail, key=lambda r: r.get("period", ""))
    if not detail:
        return None
    rec = detail[-1]
    kind = "selling" if role == "outbound" else "buying"
    thb = float(rec["selling"] if kind == "selling" else rec["buying_transfer"])
    rate = thb if base != "THB" else 1 / thb
    return {"rate": rate, "source": "Bank of Thailand daily reference rate (average %s)" % kind, "url": url.split("?")[0],
            "date": rec.get("period", ""), "note": ""}


def market(base, symbols, d):
    """Frankfurter (ECB) for the date where available, the open endpoint (latest) for the rest."""
    out, sources = {}, []
    want = [s for s in symbols if s != base]
    if d:
        url = FRANKFURTER % (d.isoformat(), base, ",".join(want))
        try:
            data = get_json(url)
            for k, v in data.get("rates", {}).items():
                out[k] = {"rate": v, "source": "market: Frankfurter (ECB reference rates)", "url": url, "date": data.get("date"), "note": ""}
            sources.append({"name": "frankfurter", "url": url, "date": data.get("date")})
        except Exception as e:                                      # noqa: BLE001
            sources.append({"name": "frankfurter", "url": url, "error": str(e)})
    rest = [s for s in want if s not in out]
    if rest:
        url = OPEN_ER % base
        try:
            data = get_json(url)
            upd = data.get("time_last_update_utc")
            for k in rest:
                if k in data.get("rates", {}):
                    out[k] = {"rate": data["rates"][k], "source": "market: exchangerate-api open endpoint (latest daily)", "url": url,
                              "date": upd, "note": "latest rate, not the rate of --date" if d else ""}
            sources.append({"name": "open.er-api.com", "url": url, "date": upd})
        except Exception as e:                                      # noqa: BLE001
            sources.append({"name": "open.er-api.com", "url": url, "error": str(e)})
    return out, sources


# ---------------------------------------------------------------- assembly
def fetch(base, symbols, d=None, jur=None, role="outbound", subject="company"):
    out = {"base": base, "date": d.isoformat() if d else "latest", "jur": jur or "", "role": role if jur else "",
           "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "rule": [], "rates": {}, "sources": [], "missing": []}
    want = [s for s in symbols if s != base]
    if jur:
        out["rule"] = fx_rule(jur, role, subject)
        target = JUR_CCY.get(jur)
        day, why = rule_day(jur, role, subject, d or _date.today())
        out["rule_day"] = {"date": day.isoformat(), "why": why}
        if target and target in want:
            try:
                r = None
                if jur == "cn":
                    r = cfets_parity(base, target, day)
                elif jur == "jp":
                    r = murc_ttm(base, target, day)
                elif jur == "th":
                    r = bot_reference(base, target, day, role)
                    if r is None and not env_value("bot_api_key"):
                        out["sources"].append({"name": "bot", "error": "bot_api_key not set in .env; market rate used instead"})
                if r:
                    r["rule_cites"] = sorted({p["cite_id"] for p in out["rule"]})
                    out["rates"][target] = r
                    out["sources"].append({"name": r["source"], "url": r["url"], "date": r["date"]})
            except Exception as e:                                  # noqa: BLE001
                out["sources"].append({"name": "official source for %s" % jur, "error": str(e)})
        if jur in ("sg", "hk"):
            out["rule_note"] = "no prescribed rate in %s: a reasonable rate applied consistently; market mid rate used" % jur
    rest = [s for s in want if s not in out["rates"]]
    if rest:
        mk, srcs = market(base, rest, d)
        for k, v in mk.items():
            if jur and k == JUR_CCY.get(jur) and jur not in ("sg", "hk"):
                v["note"] = (v["note"] + "; " if v["note"] else "") + "substitute for the prescribed rate (official source unavailable)"
        out["rates"].update(mk)
        out["sources"] += srcs
    out["missing"] = [s for s in want if s not in out["rates"]]
    out["rates"][base] = {"rate": 1.0, "source": "base", "url": "", "date": out["date"], "note": ""}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", required=True, help="currency the payment is denominated in, e.g. CNY")
    ap.add_argument("--date", default="", help="YYYY-MM-DD payment / transaction day; default latest")
    ap.add_argument("--jur", default="", help="apply this jurisdiction's prescribed rate for its own currency (cn, jp, th; sg / hk have none)")
    ap.add_argument("--role", default="outbound", choices=("outbound", "inbound"), help="outbound = withholding by the payer in --jur; inbound = income received by a resident of --jur")
    ap.add_argument("--subject", default="company", choices=("company", "individual"))
    ap.add_argument("--symbols", default="", help="comma-separated; default: every currency in database/jurisdiction.csv")
    ap.add_argument("--out", default="", help="write the JSON here (default: print)")
    a = ap.parse_args()
    symbols = [s.strip().upper() for s in a.symbols.split(",") if s.strip()] or library_currencies()
    d = datetime.strptime(a.date, "%Y-%m-%d").date() if a.date else None
    res = fetch(a.base.upper(), symbols, d, a.jur.lower() or None, a.role, a.subject)
    text = json.dumps(res, ensure_ascii=False, indent=1)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text, encoding="utf-8")
        print("wrote %s: %d rates, missing %s" % (a.out, len(res["rates"]) - 1, res["missing"] or "none"))
    else:
        print(text)
    return 2 if res["missing"] else 0


if __name__ == "__main__":
    sys.exit(main())
