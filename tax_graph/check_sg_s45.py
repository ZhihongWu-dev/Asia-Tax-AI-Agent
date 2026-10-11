"""Compare tax_graph.sg_s45 with the labels taken by hand from the IRAS calculator.

  python -m tax_graph.check_sg_s45          (conda env "pytorch")
Exit code 0 when every comparable field of every label agrees.
"""
import csv
import io
import sys
from datetime import datetime

from .params import OFFICIAL, Params
from datetime import date

from .sg_s45 import (BANK_FI, CN, CORPORATE, EQUIPMENT_RENT, GOVERNMENT, HK, INTEREST, ROYALTY, SERVICE_FEE, due_dates,
                     late_penalty, s45)

COUNTRY = {"PEOPLE'S REPUBLIC OF CHINA": CN, "HONG KONG": HK}
STRUCTURE = {"CORPORATE COMPANY": CORPORATE, "BANK / FINANCIAL INSTITUTION": BANK_FI,
             "GOVERNMENT BODY/GOVT RELATED": GOVERNMENT}
NATURE = {"INTEREST FROM LOAN OR INDEBTEDNESS": INTEREST,
          "ROYALTIES - INTELLECTUAL PROPERTY RIGHTS (PATENTS, COPYRIGHTS, TRADEMARKS, ETC.)": ROYALTY,
          "RENTAL OF EQUIPMENT / OTHER MOVEABLE PROPERTY (EXCEPT SHIP AND AIRCRAFT)": EQUIPMENT_RENT,
          "TECHNICAL ASSISTANCE FEE": SERVICE_FEE, "MANAGEMENT FEES": SERVICE_FEE}


def dmy(s):
    return datetime.strptime(s, "%d/%m/%Y").date() if s else None


def rate(s):
    return None if s == "Not Applicable" else float(s.replace("%", "").strip())


def main():
    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    with open(str(OFFICIAL / "labels" / "sg_s45_labels.csv"), encoding="utf-8-sig", newline="") as f:
        labels = list(csv.DictReader(f))
    P, bad = Params(), 0
    for lb in labels:
        r = s45(COUNTRY[lb["country"]], STRUCTURE[lb["structure"]], NATURE[lb["nature"]], dmy(lb["period_to"]),
                fixed_place_in_sg=(lb["fixed_place_in_sg"] == "Yes"), date_of_payment=dmy(lb["date_of_payment"]),
                amount=float(lb["amount"]) if lb["amount"] else None, as_at=dmy(lb["penalty_as_at"]), params=P)
        checks = [("dtr", rate(lb["dtr_rate"]), r.dtr_rate), ("without", rate(lb["rate_without_dtr"]), r.rate_without_dtr)]
        if lb["due_date"]:
            checks.append(("due", datetime.strptime(lb["due_date"], "%d %b %Y").date(), r.due_date))
        if lb["penalty"]:
            checks.append(("penalty", float(lb["penalty"].replace("$", "")), r.penalty))
        if "within 3 months from the date of submission" in lb["remarks"]:
            checks.append(("cor_rule", "3 months from WHT submission", r.cor_rule))
        if "Certificate of Residence by" in lb["remarks"]:
            want = lb["remarks"].split("Certificate of Residence by ")[1].split(" |")[0].strip()
            checks.append(("cor", datetime.strptime(want, "%d %b %Y").date(), r.cor_due))
        wrong = [(k, a, b) for k, a, b in checks if a != b]
        bad += bool(wrong)
        extra = ""
        if r.dtr_rate is not None and r.dtr_base_share != 1.0:
            extra = "  our effective rate %.2f%% (rate %.0f%% on %.0f%% of gross)" % (
                r.effective_rate, r.dtr_rate, r.dtr_base_share * 100)
        if r.conditions:
            extra += "  conditions: " + ", ".join(r.conditions)
        if r.due_date is not None and r.due_date != r.due_date_statutory:
            extra += "  statutory due %s, IRAS practice %s" % (r.due_date_statutory, r.due_date)
        out.write("%s  %-4s %s%s\n" % (lb["label_id"], "ok" if not wrong else "DIFF",
                                       " ".join(k for k, _, _ in checks), extra))
        for k, a, b in wrong:
            out.write("        %s: calculator %s, ours %s\n" % (k, a, b))
    with open(str(OFFICIAL / "labels" / "sg_iras_wht_examples.csv"), encoding="utf-8-sig", newline="") as f:
        examples = list(csv.DictReader(f))
    for ex in examples:                              # worked examples printed on the IRAS late-payment page
        nominal, statutory, effective = due_dates(date.fromisoformat(ex["date_of_payment"]), P)
        pen = late_penalty(float(ex["tax"]), effective, date.fromisoformat(ex["paid_on"]), P)
        wrong = []
        if nominal != date.fromisoformat(ex["page_due_date"]):
            wrong.append(("nominal due", ex["page_due_date"], nominal))
        if pen != float(ex["page_penalty_total"]):
            wrong.append(("penalty", ex["page_penalty_total"], pen))
        bad += bool(wrong)
        out.write("%s  %-4s nominal_due penalty  effective due %s%s\n" % (
            ex["label_id"], "ok" if not wrong else "DIFF", effective,
            " (rolled from a %s)" % nominal.strftime("%A") if effective != nominal else ""))
        for k, a, b in wrong:
            out.write("        %s: page %s, ours %s\n" % (k, a, b))
    out.write("%d labels, %d with differences\n" % (len(labels) + len(examples), bad))
    out.flush()
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
