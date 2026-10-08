#!/usr/bin/env python
"""Text of a dynamic (XFA) PDF form, read from the embedded XFA template instead of the rendered page.

Dynamic forms built with Adobe LiveCycle keep every caption, static text and choice list in an XML
template stream; the page itself only holds a "Please wait" placeholder. build.py uses xfa_text() for
such files. Python 3.9, conda env "pytorch".   python official/tools/xfa_text.py <pdf>
"""
import io
import re
import sys
from pathlib import Path

import fitz
from lxml import etree

NS_TPL = "http://www.xfa.org/schema/xfa-template/"
HTML_TAGS = re.compile(r"<[^>]+>")


def xfa_streams(path):
    """All XML streams of the XFA packet, as (first_tag, bytes)."""
    out = []
    with fitz.open(str(path)) as doc:
        for xref in range(1, doc.xref_length()):
            try:
                if not doc.xref_is_stream(xref):
                    continue
                data = doc.xref_stream(xref)
            except Exception:                                   # noqa: BLE001
                continue
            head = data[:120].lstrip()
            if head.startswith(b"<"):
                tag = re.match(rb"<\??([A-Za-z:]+)", head)
                out.append((tag.group(1).decode() if tag else "", data))
    return out


def is_xfa(path):
    return any(t == "template" for t, _ in xfa_streams(path))


def _text(el):
    """Visible text of a <value>: plain <text> or XHTML in <exData>."""
    parts = []
    for node in el.iter():
        if node.text and node.text.strip():
            parts.append(node.text.strip())
        if node.tail and node.tail.strip():
            parts.append(node.tail.strip())
    s = " ".join(parts)
    return " ".join(HTML_TAGS.sub(" ", s).split())


def xfa_text(path):
    tpl = next((d for t, d in xfa_streams(path) if t == "template"), None)
    if tpl is None:
        return ""
    root = etree.fromstring(tpl)
    lines, seen = [], set()

    def local(el):
        return etree.QName(el).localname if isinstance(el.tag, str) else ""

    def path_of(el):
        names = []
        p = el.getparent()
        while p is not None:
            if local(p) == "subform" and p.get("name"):
                names.append(p.get("name"))
            p = p.getparent()
        return "/".join(reversed(names))

    for el in root.iter():
        kind = local(el)
        if kind == "draw":                                    # static text, headings, instructions
            v = el.find("{%s}value" % etree.QName(el).namespace)
            txt = _text(v) if v is not None else ""
            if txt:
                lines.append("%s | text | %s" % (path_of(el), txt))
        elif kind in ("field", "exclGroup"):                   # fillable field with its caption
            ns = etree.QName(el).namespace
            cap = el.find("{%s}caption" % ns)
            caption = _text(cap) if cap is not None else ""
            ui = el.find("{%s}ui" % ns)
            widget = local(ui[0]) if ui is not None and len(ui) else kind
            items = [_text(i) for i in el.findall(".//{%s}items/{%s}text" % (ns, ns))]
            tip = el.find("{%s}assist/{%s}toolTip" % (ns, ns))
            tip_txt = _text(tip) if tip is not None else ""
            line = "%s | %s %s | %s" % (path_of(el), widget, el.get("name", ""), caption or tip_txt)
            if items:
                line += " | options: " + "; ".join(x for x in items if x)
            lines.append(line)
    uniq = []
    for ln in lines:
        if ln not in seen:
            seen.add(ln)
            uniq.append(ln)
    return "\n".join(uniq)


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    for a in sys.argv[1:]:
        print(xfa_text(Path(a)))
