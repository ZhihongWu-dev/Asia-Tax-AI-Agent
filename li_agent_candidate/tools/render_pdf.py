#!/usr/bin/env python
"""Typeset a client briefing (Markdown) into a compact, firm-style PDF (ctexart + xelatex).

  python agent/tools/render_pdf.py <briefing.md> <out.pdf> [--preview <dir>]

Layout rules live here, not in the agent's prompt: 10 pt body, green headings with a hairline, horizontal-rule tables with a
shaded header and ragged cells, appendices in smaller type, the sources appendix in two columns, page x / y in the footer.

Markdown handled: title (#), sections (## / ###), **bold**, `code`, bullet and numbered lists, pipe tables (they break across
pages between rows), ```flow blocks (a JSON description of the current structure, the moves and the target structure, drawn
by this template with a fixed layout, see agent/templates/flowchart.example.json), and other fenced blocks (verbatim). Every
source line is its own paragraph, because the reports write one paragraph per line. Horizontal rules in the source are ignored: headings already
carry a rule. A closing line wrapped in single asterisks is set small and grey (the internal reference).

Prints `pages=<n> latex_errors=<n> overfull=<n>` and `layout=<json>` (the pages before the appendices, the page of each section and of the flowchart, and how full each page is),
so an author who cannot see images can still judge the result. A malformed flow block is an error, not a silent gap. --preview
writes one PNG per page for people and for models that read images. Needs xelatex and PyMuPDF.
"""
import argparse
import io
import json
import math
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
    for a, b in (("→", r"$\rightarrow$"), ("←", r"$\leftarrow$"), ("►", r"$\blacktriangleright$"),
                 ("≥", r"$\geq$"), ("≤", r"$\leq$"), ("×", r"$\times$")):
        s = s.replace(a, b)
    return s


FLOW_STEP = 2.05                                       # cm between two tiers: a box of three lines, then room for a two-line holding label
FLOW_HEAD = 0.72
FLOW_TITLE_LINE = 0.42
FLOW_RESULT_TOP = -0.78
FLOW_RESULT_LINE = 0.33


def lines_of(text, width, per_cm):
    """Lines a text takes in a box of that width (cm), estimated: TikZ cannot size the frame around a node it has not set."""
    return sum(max(1, math.ceil(len(part) / (width * per_cm))) for part in str(text).split("\n"))


def panel(side, x, width, top, bottom, title_lines, emphasised):
    """One structure: an ownership chain from the top holder down to the paying company, with its tax result underneath."""
    chain, holds = side["chain"], side.get("holds", [])
    if len(chain) < 2:
        raise RuntimeError("flow block: a chain needs at least two entities")
    step = top / (len(chain) - 1)
    frame = "emphasis" if emphasised else "plain"
    centre = x + width * 0.355
    box = min(3.8, width - 2.3)
    rail = centre + box / 2 + 0.42                             # the dividend's dashed line, right of the boxes and of the holding labels
    out = [r"\draw[%s] (%.2f,%.2f) rectangle (%.2f,%.2f);" % (frame, x, bottom, x + width, top + FLOW_HEAD + title_lines * FLOW_TITLE_LINE),
           r"\node[paneltitle,text width=%.2fcm,align=center,anchor=south] at (%.2f,%.2f) {%s};" % (width - 0.3, x + width / 2, top + FLOW_HEAD - 0.1, esc(side.get("title", "")))]
    for k, e in enumerate(chain):
        y = top - k * step
        note = (r"\\{\scriptsize %s}" % esc(e["note"])) if e.get("note") else ""
        out.append(r"\node[entity,text width=%.2fcm] (n%d%d) at (%.2f,%.2f) {\textbf{%s}%s};" % (box, int(x), k, centre, y, esc(e["name"]), note))
    for k in range(len(chain) - 1):
        pct = esc(holds[k]) if k < len(holds) else ""
        out.append(r"\draw[hold] (n%d%d) -- node[holdlabel,text width=%.2fcm] {%s} (n%d%d);" % (int(x), k, rail - centre - 0.12, pct, int(x), k + 1))
    target = side.get("dividend_to")
    if target is not None:
        if not 0 <= int(target) < len(chain) - 1:
            raise RuntimeError("flow block: dividend_to must point at an entity above the paying company")
        out.append(r"\draw[dividend] (n%d%d.east) -- (%.2f,%.2f) |- node[divlabel,pos=0.25,text width=%.2fcm] {\hyphenpenalty=10000\relax %s} (n%d%d.east);"
                   % (int(x), len(chain) - 1, rail, top - (len(chain) - 1) * step, x + width - rail - 0.15, esc(side.get("dividend_label", "")), int(x), int(target)))
    out.append(r"\node[result,text width=%.2fcm,anchor=north] at (%.2f,%.2f) {%s};" % (width - 0.4, x + width / 2, FLOW_RESULT_TOP, esc(side.get("result", "")).replace("\n", r"\\")))
    return out


def flow_tex(raw):
    try:
        spec = json.loads(raw)
        current, target = spec["current"], spec["target"]
    except (ValueError, KeyError) as ex:
        raise RuntimeError("flow block is not valid: %s" % ex)
    steps = spec.get("steps", [])
    width = 5.5 if steps else 8.2                              # without steps the two panels take the whole line
    right = 11.5 if steps else 8.8
    top = (max(len(current["chain"]), len(target["chain"])) - 1) * FLOW_STEP
    title_lines = max(lines_of(p.get("title", ""), width - 0.3, 5.2) for p in (current, target))
    bottom = FLOW_RESULT_TOP - 0.25 - max(lines_of(p.get("result", ""), width - 0.4, 7.6) for p in (current, target)) * FLOW_RESULT_LINE
    body = r"\\[2pt]".join(r"%d.\ %s" % (n + 1, esc(t)) for n, t in enumerate(steps))
    out = [r"\begin{center}\begin{tikzpicture}[x=0.985cm,y=1cm,font=\footnotesize,"
           r"plain/.style={draw=rule,rounded corners=3pt},emphasis/.style={draw=ink,line width=0.9pt,rounded corners=3pt,fill=band!45},"
           r"paneltitle/.style={font=\sffamily\bfseries\small,text=ink,inner sep=1pt},"
           r"entity/.style={draw=ink!70,fill=white,rounded corners=2pt,align=flush center,minimum height=0.74cm,inner sep=2.5pt},"
           r"hold/.style={-{Stealth[length=5pt]},draw=ink!75},holdlabel/.style={right,font=\scriptsize,align=left,inner sep=2pt,text=ink!85!black},"
           r"dividend/.style={-{Stealth[length=6pt]},draw=accent,dashed,line width=0.8pt},"
           r"divlabel/.style={right,font=\scriptsize,text=accent,align=left,inner sep=2pt},"
           r"result/.style={align=flush center,font=\scriptsize,inner sep=1pt},"
           r"movearrow/.style={-{Stealth[length=9pt,width=9pt]},draw=ink,line width=1.6pt}]"]
    out += panel(current, 0.0, width, top, bottom, title_lines, False)
    if steps:
        out.append(r"\node[paneltitle] at (8.5,%.2f) {%s};" % (top + FLOW_HEAD + 0.1, esc(spec.get("steps_title", ""))))
        out.append(r"\node[anchor=north,text width=4.7cm,align=left,font=\scriptsize,inner sep=0pt] at (8.5,%.2f) {%s};" % (top + 0.5, body))
        out.append(r"\draw[movearrow] (5.72,%.2f) -- (11.28,%.2f);" % (bottom + 0.6, bottom + 0.6))
    out += panel(target, right, width, top, bottom, title_lines, True)
    out.append(r"\end{tikzpicture}\end{center}")
    return out


def table(rows, size):
    n = max(len(r) for r in rows)
    rows = [r + [""] * (n - len(r)) for r in rows]
    weights = [max(max(len(r[c]) for r in rows), 3) ** 0.55 for c in range(n)]
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
            body.extend(table(rows, r"\scriptsize" if in_appendix else r"\footnotesize"))
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
                body.append(r"\begingroup\footnotesize")
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
            body.append(r"\par\vspace{4pt}{\tiny\color{gray}%s\par}" % esc(reference.group(1)))
        elif l.strip() and l.strip() not in ("---", "***", "___"):
            body.append(esc(l) + "\n")
        i += 1
    close_list()
    close_columns()
    close_front()
    if in_appendix:
        body.append(r"\endgroup")
    return "\n".join(body)


TEMPLATE = r"""\documentclass[10pt,a4paper,linespread=1.2]{ctexart}
\usepackage[top=1.8cm,bottom=1.7cm,left=2.0cm,right=2.0cm,footskip=0.7cm]{geometry}
\usepackage{array,longtable,booktabs,fancyvrb,amssymb,fancyhdr,xcolor,colortbl,multicol,lastpage,needspace,enumitem,tikz}
\usetikzlibrary{arrows.meta}
\definecolor{ink}{HTML}{1E6B4F}\definecolor{rule}{HTML}{AECBBC}\definecolor{band}{HTML}{E8F3ED}\definecolor{accent}{HTML}{B5651D}
\IfFontExistsTF{Cambria}{\setmainfont{Cambria}}{}
\IfFontExistsTF{Calibri}{\setsansfont{Calibri}}{}
\IfFontExistsTF{Consolas}{\setmonofont[Scale=0.88]{Consolas}}{}
\IfFontExistsTF{Microsoft YaHei}{\setCJKsansfont{Microsoft YaHei}}{}
\ctexset{section={format=\sffamily\bfseries\normalsize\color{ink}\raggedright,beforeskip=8pt plus 2pt,afterskip=3pt},
         subsection={format=\sffamily\bfseries\small\color{ink}\raggedright,beforeskip=5pt,afterskip=2pt}}
\setlength{\parindent}{0pt}\setlength{\parskip}{3pt plus 1pt}
\setlength{\tabcolsep}{3.5pt}\setlength{\LTpre}{2pt}\setlength{\LTpost}{3pt}\setlength{\LTleft}{0pt}\setlength{\LTright}{0pt}
\setlength{\aboverulesep}{1.2pt}\setlength{\belowrulesep}{1.2pt}\setlength{\columnsep}{14pt}
\renewcommand{\arraystretch}{1.08}\arrayrulecolor{rule}
\setlist[itemize]{leftmargin=1.5em,topsep=1pt,itemsep=0.5pt,parsep=0pt,partopsep=0pt}
\pagestyle{fancy}\fancyhf{}\renewcommand{\headrulewidth}{0pt}
\rfoot{\scriptsize\color{gray}\thepage\ / \pageref*{LastPage}}
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
            "page_fill": fill, "last_page_fill": fill[-1]}


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
