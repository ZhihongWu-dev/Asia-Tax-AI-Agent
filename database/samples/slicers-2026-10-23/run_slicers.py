# -*- coding: utf-8 -*-
"""Trial run of the slicers on the real texts in this folder: counts, first/last ids, gaps, sample clauses."""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import build  # noqa: E402

D = Path(__file__).parent
which = sys.argv[1:] or ["id", "jp", "kr", "in", "vn", "my", "th", "ae", "treaty", "secondary"]


def report(name, out, mode, show=()):
    arts = [c for c in out if c["kind"] in ("section", "article")]
    subs = [c for c in out if c["kind"] == "paragraph"]
    print("=== %s: mode=%s articles=%d paragraphs=%d" % (name, mode, len(arts), len(subs)))
    if arts:
        print("first", arts[0]["cite_id"], "| last", arts[-1]["cite_id"])
        nums = []
        for c in arts:
            m = re.search(r"#[a-z]*?(\d+)", c["cite_id"])
            if m:
                nums.append(int(m.group(1)))
        gaps = [(a, b) for a, b in zip(nums, nums[1:]) if b - a > 1]
        print("numbers", nums[0], "->", nums[-1], "gaps(>1):", gaps[:15], "count", len(gaps))
        short = [c["cite_id"] for c in arts if len(c["text"]) < 40]
        print("short(<40 chars):", short[:10], len(short))
    for cid in show:
        for c in out:
            if c["cite_id"] == cid:
                print("--- %s [%s]\n%s" % (cid, c["label"], c["text"][:700]))


if "id" in which:
    text = build.html_text((D / "id.uu36-2008.htm").read_bytes())          # same reader as the build
    out, mode = build.slice_id("id.uu36-2008", text)
    report("ID UU 36/2008", out, mode, ("id.uu36-2008#26", "id.uu36-2008#26(1)", "id.uu36-2008#2(1a)"))
if "jp" in which:
    raw = (D / "jp.cta.xml").read_bytes()
    out, mode = build.slice_jp("jp.cta", raw)
    report("JP 法人税法", out, mode, ("jp.cta#23", "jp.cta#23.1", "jp.cta#4-2", "jp.cta#2"))
    t = build.jp_text(raw)
    print("jp_text chars", len(t), "| sample:", t[:300].replace("\n", " / "))
if "kr" in which:
    raw = (D / "kr.cita.xml").read_bytes()
    s = raw.decode("utf-8", "replace")
    if not s.rstrip().endswith("</법령>"):                      # the download was cut: close it at the last complete unit
        s = s[: s.rfind("</조문단위>") + len("</조문단위>")] + "\n</조문>\n</법령>"
        print("(KR file repaired at last complete 조문단위; real registration needs the complete file)")
    raw = s.encode("utf-8")
    out, mode = build.slice_kr("kr.cita", raw)
    report("KR 법인세법", out, mode, ("kr.cita#98", "kr.cita#98.1", "kr.cita#98-2", "kr.cita#2"))
    text = chr(10).join(build.pdf_pages(D / "kr.cita.20260701.pdf"))      # the same act printed from law.go.kr as PDF (2026-11-07)
    out, mode = build.slice_kr_pdf("kr.cita.pdf", text)
    report("KR 법인세법, law.go.kr PDF as at 2026-07-01", out, mode, ("kr.cita.pdf#98", "kr.cita.pdf#98.1"))
if "in" in which:
    p = D / "in.ita1961.pdf"
    if p.exists():
        text = chr(10).join(build.pdf_pages(p))
        out, mode = build.slice_in("in.ita1961", text)
        report("IN ITA 1961", out, mode, ("in.ita1961#s195", "in.ita1961#s195(1)", "in.ita1961#s115A", "in.ita1961#s90"))
    text = chr(10).join(build.pdf_pages(D / "in.ita2025.pdf"))
    out, mode = build.slice_in("in.ita2025", text)
    report("IN Income-tax Act 2025 (as amended 2026)", out, mode, ("in.ita2025#s207(1)",))
if "vn" in which:
    text = build.html_text((D / "vn.cit2025.html").read_bytes())
    out, mode = build.slice_vn("vn.cit2025", text)
    report("VN Luật Thuế TNDN 67/2025/QH15", out, mode, ("vn.cit2025#10", "vn.cit2025#10.1"))
if "my" in which:
    text = chr(10).join(build.pdf_pages(D / "my.ita1967.pdf"))
    out, mode = build.slice_act("my.ita1967", text, "my")
    report("MY Income Tax Act 1967", out, mode, ("my.ita1967#s109", "my.ita1967#s44"))
    text = chr(10).join(build.pdf_pages(D / "my.pua235.2022.pdf"))         # a bilingual order: Malay half, then English (2026-11-07)
    out, mode = build.slice_act("my.pua235", text, "my")
    report("MY P.U. (A) 235/2022 (bilingual)", out, mode, ("my.pua235#s4", "my.pua235#ms.s4"))
if "th" in which:
    for page in ("5937", "5939"):
        text = build.html_text((D / ("th.rc.th.%s.html" % page)).read_bytes())
        out, mode = build.slice_act("th.rc.th", text, "th")
        report("TH Revenue Code ch. 3 (Thai), rd.go.th page " + page, out, mode)
    for page in ("37749", "37764"):
        text = build.html_text((D / ("th.rc.%s.html" % page)).read_bytes())
        out, mode = build.slice_act("th.rc." + page, text, "th")
        report("TH Revenue Code ch. 3, rd.go.th page " + page, out, mode, ("th.rc.37764#s70",) if page == "37764" else ())
if "ae" in which:
    text = chr(10).join(build.pdf_pages(D / "ae.ctl2022.pdf"))
    out, mode = build.slice_act("ae.ctl2022.en", text, "ae")
    report("AE Federal Decree-Law 47/2022, English", out, mode, ("ae.ctl2022.en#a45(1)",))
    text = build.html_text((D / "ae.ctl2022.ar.html").read_bytes())
    out, mode = build.slice_act("ae.ctl2022.ar", text, "ae")
    report("AE Federal Decree-Law 47/2022, Arabic", out, mode, ("ae.ctl2022.ar#a45(1)",))
if "treaty" in which:
    for name in ("syn.jp-my", "syn.jp-th", "tr.in-jp", "tr.id-jp"):
        text = chr(10).join(build.pdf_pages(D / ("treaty.%s.pdf" % name)))
        out, mode = build.slice_en_treaty("treaty." + name, text)
        report("Treaty text of the Japanese Ministry of Finance: " + name, out, mode)
        print("MLI boxes:", [c["cite_id"].split("#")[1] for c in out if c["kind"] == "mli_box"])
if "secondary" in which:
    for f in ("jp.nta.tsutatsu.03_03_01.htm", "jp.nta.tsutatsu.02_01_05.htm"):
        out, mode = build.slice_jp_tsutatsu("jp.nta." + f[16:24], build.html_text((D / f).read_bytes()))
        report("JP NTA circular " + f, out, mode)
        print("items:", [c["cite_id"].split("#")[1] for c in out])
    out, mode = build.slice_kr("kr.nts.intltax-rule", (D / "kr.nts.intltax-rule.xml").read_bytes())
    report("KR administrative rule 국제조세사무처리규정", out, mode)
    out, mode = build.slice_act("th.mr.21452", build.html_text((D / "th.mr.21452.html").read_bytes()), "th")
    report("TH ministerial regulation (rd.go.th/21452)", out, mode)
    out, mode = build.slice_in("in.itr2026", chr(10).join(build.pdf_pages(D / "in.itr2026.pdf")))
    report("IN Income-tax Rules 2026", out, mode)
