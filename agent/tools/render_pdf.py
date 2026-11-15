#!/usr/bin/env python
"""Typeset a client briefing (Markdown) into a compact, firm-style PDF (ctexart + xelatex).

  python agent/tools/render_pdf.py <briefing.md> <out.pdf> [--preview <dir>]

Layout rules live here, not in the agent's prompt: 11 pt body, 13 pt part headings and 11.5 pt sub-headings in green with a
hairline, horizontal-rule tables with a shaded header and ragged cells (10 pt, 9 pt from six columns), the flowchart at 9 pt,
nothing below 8 pt (the footer and the internal reference), the sources appendix in two columns, page x / y in the footer.

Markdown handled: title (#), sections (## / ###), **bold**, `code`, bullet and numbered lists, pipe tables (they break across
pages between rows), ```flow blocks (a JSON description of the current structure, the moves and the target structure, drawn
by this template; the program writes it from the products, frame/blocks/flow.json), and other fenced blocks (verbatim). Every
source line is its own paragraph, because the reports write one paragraph per line. Horizontal rules in the source are ignored: headings already
carry a rule. A closing line wrapped in single asterisks is set small and grey (the internal reference).

Prints `pages=<n> latex_errors=<n> overfull=<n>` and `layout=<json>` (the pages before the appendices, the page of each section and of the flowchart, and how full each page is),
so an author who cannot see images can still judge the result. A malformed flow block is an error, not a silent gap. --preview
writes one PNG per page for people and for models that read images. Needs xelatex and PyMuPDF.
"""
import argparse
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CJK = re.compile(r"[\u3000-\u9fff\uff00-\uffef]")


def quotes(s):
    """Straight double quotes become curly pairs in CJK text and TeX quotes in Latin text."""
    pair = ("“", "”") if CJK.search(s) else ("``", "''")
    out, opening = [], True
    for ch in s:
        if ch == '"':
            out.append(pair[0] if opening else pair[1])
            opening = not opening
        else:
            out.append(ch)
    s = "".join(out)
    if not CJK.search(s):                                 # curly quotes would fall back to the CJK font in Latin text
        for a, b in (("“", "``"), ("”", "''"), ("‘", "`"), ("’", "'")):
            s = s.replace(a, b)
    return s


def esc(s):
    s = s.replace("\\", "\x00")
    for ch in "&%$#_{}":
        s = s.replace(ch, "\\" + ch)
    s = s.replace("\x00", r"\textbackslash{}").replace("~", r"\textasciitilde{}").replace("^", r"\textasciicircum{}")
    s = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", s)
    s = re.sub(r"`([^`]+?)`", r"\\texttt{\1}", s)
    s = quotes(s)
    if not CJK.search(s):                                 # xeCJK sets U+2014 as a CJK glyph and swallows the spaces around it
        s = s.replace("—", "---").replace("–", "--")
    for a, b in (("→", r"$\rightarrow$"), ("←", r"$\leftarrow$"), ("►", r"$\blacktriangleright$"),
                 ("≥", r"$\geq$"), ("≤", r"$\leq$"), ("×", r"$\times$")):
        s = s.replace(a, b)
    return s


PANEL_W = 7.65                                         # cm: a holding label, the box, the dividend's rail and its label
BOX_W = 3.55
LABEL_W = 1.8
GAP = 0.75                                             # between the two panels, where the move arrow sits


def panel(side, tag, x0, emphasised):
    """One structure: the holding chain from the top holder down to the paying company, the dividend's route on it and the tax
    underneath. Every box sits below the one before at its real height (positioning), so nothing is estimated or overlaps."""
    chain, holds = side["chain"], side.get("holds", [])
    if len(chain) < 2:
        raise RuntimeError("flow block: a chain needs at least two entities")
    cx = x0 + LABEL_W + 0.15 + BOX_W / 2
    out = [r"\coordinate (%sL) at (%.2f,0);" % (tag, x0), r"\coordinate (%sR) at (%.2f,0);" % (tag, x0 + PANEL_W),
           r"\coordinate (%sC) at (%.2f,0);" % (tag, x0 + PANEL_W / 2)]
    for k, e in enumerate(chain):
        note = (r"\\ %s" % esc(e["note"])) if e.get("note") else ""
        where = "at (%.2f,0)" % cx if k == 0 else ""
        place = "" if k == 0 else ",below=9mm of %s%d" % (tag, k - 1)
        out.append(r"\node[entity,text width=%.2fcm%s] (%s%d) %s {\textbf{%s}%s};" % (BOX_W, place, tag, k, where, esc(e["name"]), note))
    for k in range(len(chain) - 1):
        pct = esc(holds[k]) if k < len(holds) else ""
        out.append(r"\draw[hold] (%s%d.south) -- node[holdlabel,text width=%.2fcm] {%s} (%s%d.north);" % (tag, k, LABEL_W, pct, tag, k + 1))
    n = len(chain) - 1
    target = side.get("dividend_to")
    if target is not None:
        if not 0 <= int(target) < n:
            raise RuntimeError("flow block: dividend_to must point at an entity above the paying company")
        out.append(r"\draw[dividend] (%s%d.east) -- ++(0.45,0) coordinate (%srail) |- node[divlabel,pos=0.25,text width=%.2fcm] {%s} (%s%d.east);"
                   % (tag, n, tag, PANEL_W - LABEL_W - 0.15 - BOX_W - 0.7, esc(side.get("dividend_label", "")), tag, int(target)))
    out.append(r"\node[result,text width=%.2fcm,anchor=north] (%sres) at ($(%sC |- %s%d.south)+(0,-0.45)$) {%s};"
               % (PANEL_W - 0.4, tag, tag, tag, n, esc(side.get("result", "")).replace("\n", r"\\")))
    out.append(r"\node[paneltitle,text width=%.2fcm,anchor=south] (%stitle) at ($(%sC |- %s0.north)+(0,0.35)$) {%s};"
               % (PANEL_W - 0.3, tag, tag, tag, esc(side.get("title", ""))))
    out.append(r"\begin{scope}[on background layer]\node[%s,fit=(%stitle)(%sres)(%sL)(%sR),inner sep=5pt] (%sframe) {};\end{scope}"
               % ("emphasis" if emphasised else "plain", tag, tag, tag, tag, tag))
    return out


def flow_tex(raw):
    """The flowchart the program writes into Part 1 (frame/blocks/flow.json): two panels side by side, the moves underneath.
    Type is never below 9 pt."""
    try:
        spec = json.loads(raw)
        current, target = spec["current"], spec["target"]
    except (ValueError, KeyError) as ex:
        raise RuntimeError("flow block is not valid: %s" % ex)
    right = PANEL_W + GAP
    out = [r"\begin{center}\begin{tikzpicture}[font=\fontsize{9}{11}\selectfont,"
           r"plain/.style={draw=rule,rounded corners=3pt},emphasis/.style={draw=ink,line width=0.9pt,rounded corners=3pt,fill=band!45},"
           r"paneltitle/.style={font=\sffamily\bfseries\fontsize{9.5}{11.5}\selectfont,text=ink,inner sep=1pt,align=center},"
           r"entity/.style={draw=ink!70,fill=white,rounded corners=2pt,align=flush center,minimum height=0.8cm,inner sep=3pt},"
           r"hold/.style={-{Stealth[length=5pt]},draw=ink!75},holdlabel/.style={left,align=right,inner sep=2pt,text=ink!85!black},"
           r"dividend/.style={-{Stealth[length=6pt]},draw=accent,dashed,line width=0.8pt},"
           r"divlabel/.style={right,text=accent,align=left,inner sep=2pt},"
           r"result/.style={align=flush center,inner sep=1pt},"
           r"movearrow/.style={-{Stealth[length=9pt,width=9pt]},draw=ink,line width=1.6pt}]"]
    out += panel(current, "P", 0.0, False)
    out += panel(target, "Q", right, True)
    out.append(r"\draw[movearrow] ($(Pframe.east)+(0.1,0)$) -- ($(Pframe.east -| Qframe.west)+(-0.1,0)$);")
    out.append(r"\end{tikzpicture}\end{center}")
    steps = spec.get("steps", [])
    if steps:
        moves = [s.rstrip(".") for s in steps]
        moves = moves[:1] + [m[:1].lower() + m[1:] for m in moves[1:]]
        out.append(r"\par{\small\textbf{%s:} %s.\par}" % (esc(spec.get("steps_title", "Moves")), "; ".join(esc(m) for m in moves)))
    return out


def table(rows, size):
    n = max(len(r) for r in rows)
    rows = [r + [""] * (n - len(r)) for r in rows]
    weights = [max(max(len(r[c]) for r in rows), 3) ** 0.55 for c in range(n)]
    longest = [max(len(w) for r in rows for w in (r[c].split() or [""])) for c in range(n)]
    per_line = 100 if n >= 6 else 90                   # characters across the text width at the table's size
    floor = [(k + 2) / per_line for k in longest]      # no column narrower than its longest word ("Payback" overflowed)
    share = [w / sum(weights) for w in weights]
    for _ in range(n if sum(floor) < 1 else 0):
        short = [c for c in range(n) if share[c] < floor[c] - 1e-9]
        if not short:
            break
        free = [c for c in range(n) if c not in short and share[c] > floor[c]]
        need = sum(floor[c] - share[c] for c in short)
        room = sum(share[c] - floor[c] for c in free) or 1
        for c in short:
            share[c] = floor[c]
        for c in free:
            share[c] -= need * (share[c] - floor[c]) / room
    weights = share
    if size is None:
        size = r"\footnotesize" if n >= 6 else r"\small"
    spec = "".join(r">{\raggedright\arraybackslash}p{\dimexpr%.4f\textwidth-2\tabcolsep\relax}" % (w / sum(weights)) for w in weights)
    out = ["{%s\\needspace{5\\baselineskip}\\begin{longtable}{%s}" % (size, spec), r"\toprule\rowcolor{band}"]
    out.append(" & ".join(r"\textbf{%s}" % esc(c) for c in rows[0]) + r" \\ \midrule\endhead")
    for i, r in enumerate(rows[1:]):
        out.append(" & ".join(esc(c) for c in r) + (r" \\ \bottomrule" if i == len(rows) - 2 else r" \\ \cmidrule[0.2pt]{1-%d}" % n))
    out.append(r"\end{longtable}}")
    return out


def to_tex(md):
    lines = md.splitlines()
    body, i, in_list = [], 0, False
    in_front, in_appendix, in_columns = True, False, False

    def close_list():
        nonlocal in_list
        if in_list:
            body.append(r"\end{itemize}")
            in_list = False

    def close_columns():
        nonlocal in_columns
        if in_columns:
            body.append(r"\end{multicols}")
            in_columns = False

    def close_front():
        nonlocal in_front
        if in_front:
            body.append(r"\endgroup")
            in_front = False

    body.append(r"\begingroup\small")
    while i < len(lines):
        l = lines[i]
        if l.startswith("```"):
            close_list()
            lang = l[3:].strip().lower()
            i += 1
            block = []
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            if lang == "flow":
                body.extend(flow_tex("\n".join(block)))
            else:
                body.append(r"\begin{Verbatim}[frame=single,rulecolor=\color{rule},fontsize=\footnotesize]")
                body.extend(block)
                body.append(r"\end{Verbatim}")
            continue
        if l.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s\-:|]+\|$", lines[i + 1]):
            close_list()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.match(r"^\|[\s\-:|]+\|$", lines[i]):
                    rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            body.extend(table(rows, None))                         # 10 pt, 9 pt from six columns, body and appendices alike
            continue
        bullet = re.match(r"^\s*[-*]\s+(.*)$", l)
        numbered = re.match(r"^\s*(\d+)[.、]\s+(.*)$", l)
        if in_list and not (bullet or numbered):
            close_list()
        reference = re.match(r"^\*([^*].*[^*])\*$", l.strip())
        if l.startswith("# "):
            body.append(r"{\sffamily\bfseries\LARGE\color{ink}%s\par}\vspace{3pt}{\color{ink}\hrule height 1.1pt}\vspace{5pt}" % esc(l[2:]))
        elif l.startswith("## "):
            close_front()
            close_columns()
            title = l[3:]
            appendix = re.match(r"^(附录|Appendix)", title)
            if appendix and not in_appendix:
                body.append(r"\begingroup\small")
                in_appendix = True
            body.append(r"\needspace{6\baselineskip}\section*{%s}\nopagebreak\vspace{-3pt}{\color{rule}\hrule height 0.4pt}\nopagebreak\vspace{3pt}" % esc(title))
            rest = lines[i + 1:]
            if re.match(r"^(附录\s*B|Appendix\s*B)", title) and not any(x.startswith("|") or x.startswith("## ") for x in rest):
                body.append(r"\begin{multicols}{2}\raggedright")
                in_columns = True
        elif l.startswith("### "):
            body.append(r"\subsection*{" + esc(l[4:]) + "}")
        elif bullet or numbered:
            if not in_list:
                body.append(r"\begin{itemize}")
                in_list = True
            body.append(r"\item " + esc(bullet.group(1)) if bullet else r"\item[%s.] %s" % (numbered.group(1), esc(numbered.group(2))))
        elif reference:
            close_columns()
            body.append(r"\par\vspace{4pt}{\scriptsize\color{gray}%s\par}" % esc(reference.group(1)))
        elif l.strip() and l.strip() not in ("---", "***", "___"):
            body.append(esc(l) + "\n")
        i += 1
    close_list()
    close_columns()
    close_front()
    if in_appendix:
        body.append(r"\endgroup")
    return "\n".join(body)


TEMPLATE = r"""\documentclass[11pt,a4paper,linespread=1.2]{ctexart}
\usepackage[top=2.0cm,bottom=1.9cm,left=2.2cm,right=2.2cm,footskip=0.8cm]{geometry}
\usepackage{array,longtable,booktabs,fancyvrb,amssymb,fancyhdr,xcolor,colortbl,multicol,lastpage,needspace,enumitem,tikz}
\usetikzlibrary{arrows.meta,positioning,calc,fit,backgrounds}
\definecolor{ink}{HTML}{1E6B4F}\definecolor{rule}{HTML}{AECBBC}\definecolor{band}{HTML}{E8F3ED}\definecolor{accent}{HTML}{B5651D}
\IfFontExistsTF{Cambria}{\setmainfont{Cambria}}{}
\IfFontExistsTF{Calibri}{\setsansfont{Calibri}}{}
\IfFontExistsTF{Consolas}{\setmonofont[Scale=0.88]{Consolas}}{}
\IfFontExistsTF{Microsoft YaHei}{\setCJKsansfont{Microsoft YaHei}}{}
\ctexset{section={format=\sffamily\bfseries\fontsize{13}{16}\selectfont\color{ink}\raggedright,beforeskip=10pt plus 2pt,afterskip=3pt},
         subsection={format=\sffamily\bfseries\fontsize{11.5}{14}\selectfont\color{ink}\raggedright,beforeskip=6pt,afterskip=2pt}}
\setlength{\parindent}{0pt}\setlength{\parskip}{3pt plus 1pt}
\setlength{\tabcolsep}{3.5pt}\setlength{\LTpre}{2pt}\setlength{\LTpost}{3pt}\setlength{\LTleft}{0pt}\setlength{\LTright}{0pt}
\setlength{\aboverulesep}{1.2pt}\setlength{\belowrulesep}{1.2pt}\setlength{\columnsep}{14pt}
\renewcommand{\arraystretch}{1.08}\arrayrulecolor{rule}
\setlist[itemize]{leftmargin=1.5em,topsep=1pt,itemsep=0.5pt,parsep=0pt,partopsep=0pt}
\pagestyle{fancy}\fancyhf{}\renewcommand{\headrulewidth}{0pt}
\rfoot{\fontsize{8}{10}\selectfont\color{gray}\thepage\ / \pageref*{LastPage}}
\begin{document}
%s
\end{document}
"""


def layout(pdf, md):
    """Where each section landed and how full the last page is, for authors who cannot look at the pages."""
    import pymupdf
    doc = pymupdf.open(str(pdf))
    texts = [re.sub(r"\s+", "", p.get_text()) for p in doc]
    sections, page = [], 0
    for title in re.findall(r"^##\s+(.+)$", md, re.M):
        key = re.sub(r"\s+", "", title.replace("*", ""))
        while page < len(texts) and key not in texts[page]:
            page += 1
        if page == len(texts):
            page = 0
            sections.append({"section": title, "page": None})
            continue
        sections.append({"section": title, "page": page + 1})
    fill = []
    for p in doc:
        bottom = max([b[3] for b in p.get_text("blocks") if b[3] < p.rect.height * 0.94] or [0])
        fill.append(round(bottom / p.rect.height, 2))
    flow = re.search(r'^```flow\s*\n.*?"steps_title"\s*:\s*"([^"]+)"', md, re.M | re.S)
    key = re.sub(r"\s+", "", flow.group(1)) if flow else ""
    flow_page = next((i + 1 for i, t in enumerate(texts) if key and key in t), None)
    first_appendix = next((s["page"] for s in sections if s["page"] and re.match(r"(附录|Appendix)", s["section"])), None)
    return {"pages": len(doc), "body_pages": first_appendix or len(doc), "sections": sections, "flow_page": flow_page,
            "flow_overlaps": overlaps(doc[flow_page - 1]) if flow_page else 0, "page_fill": fill, "last_page_fill": fill[-1]}


def overlaps(page):
    """Pairs of text lines on a page whose boxes overlap: the check that the flowchart's layout held (a program defect if not)."""
    boxes = []
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            if "".join(s["text"] for s in l["spans"]).strip():
                x0, y0, x1, y1 = l["bbox"]
                boxes.append((x0 + 0.5, y0 + 1.0, x1 - 0.5, y1 - 1.0))       # a little slack: touching lines are not overlapping
    n = 0
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                n += 1
    return n


def previews(pdf, folder):
    import pymupdf
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("page-*.png"):
        old.unlink()
    doc = pymupdf.open(str(pdf))
    paths = []
    for i, page in enumerate(doc):
        path = folder / ("page-%d.png" % (i + 1))
        page.get_pixmap(dpi=110).save(str(path))
        paths.append(path)
    return paths


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("source")
    ap.add_argument("out")
    ap.add_argument("--preview", default="")
    a = ap.parse_args()
    src, out = Path(a.source), Path(a.out)
    if not shutil.which("xelatex"):
        sys.stderr.write("xelatex not found on PATH\n")
        return 3
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        try:
            tex = TEMPLATE.replace("%s", to_tex(src.read_text(encoding="utf-8")), 1)
        except RuntimeError as ex:
            sys.stderr.write(str(ex) + "\n")
            return 1
        (d / "r.tex").write_text(tex, encoding="utf-8")
        for _ in range(3):                                      # longtable and lastpage need extra passes to settle
            r = subprocess.run(["xelatex", "-interaction=nonstopmode", "r.tex"], cwd=str(d), capture_output=True,
                               text=True, encoding="utf-8", errors="replace", timeout=240)
        pdf = d / "r.pdf"
        if not pdf.exists():
            sys.stderr.write((r.stdout or "")[-1500:])
            return 1
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(pdf, out)
        m = re.search(r"Output written on r\.pdf \((\d+) page", r.stdout)
        errors = re.findall(r"^! (.*)$", r.stdout, re.M)
        overfull = len(re.findall(r"Overfull \\hbox \(([1-9]\d|[5-9])", r.stdout))
        print("pages=%s latex_errors=%d overfull=%d -> %s" % (m.group(1) if m else "?", len(errors), overfull, out))
        for e in errors[:3]:
            print("latex error: " + e[:120])
        print("layout=" + json.dumps(layout(out, src.read_text(encoding="utf-8")), ensure_ascii=False))
        if a.preview:
            for p in previews(out, Path(a.preview)):
                print("preview=%s" % p)
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main())
