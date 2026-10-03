"""Segmenters: raw official content -> citable legal units (pure functions)."""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

H = "{http://www.xml.gov.hk/schemas/hklm/1.0}"

# Cap.112 Part 4 Division 3A — the FSIE statutory backbone (ss.15H–15S).
FSIE_SECTIONS = [f"15{c}" for c in "HIJKLMNOPQRS"]

_BOILERPLATE_MARKERS = (
    "skip to main content", "other languages", "copyright", "privacy policy",
    "important notice", "ird search", "font size", "back to top",
    "home |", "contact us", "©",
)

_FAQ_QUESTION = re.compile(r"^\s*(?:Q(?:uestion)?\s*\.?\s*)?(\d+)\s*[.:、]\s*(.{12,})", re.I)


@dataclass(frozen=True)
class UnitDraft:
    unit_ref: str
    unit_type: str
    ordinal: int
    text: str
    statute_locator: str | None = None
    heading: str | None = None
    language: str = "en"

    @property
    def text_sha256(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def segment_cap112(xml_bytes: bytes) -> list[UnitDraft]:
    """Split Division 3A into subsection-level units (s.15M(2) granularity).

    Sections without subsections become single section-level units.
    """
    root = ET.fromstring(xml_bytes)
    drafts: list[UnitDraft] = []
    ordinal = 0
    for sec_num in FSIE_SECTIONS:
        section = None
        for candidate in root.iter(H + "section"):
            if candidate.get("name") == f"s{sec_num}":
                section = candidate
                break
        if section is None:
            continue
        heading = section.find(H + "heading")
        heading_text = _clean("".join(heading.itertext())) if heading is not None else None

        subsections = list(section.iter(H + "subsection"))
        if subsections:
            for sub in subsections:
                sub_num = sub.get("name")
                text = _clean("".join(sub.itertext()))
                if not text:
                    continue
                ordinal += 1
                drafts.append(
                    UnitDraft(
                        unit_ref=f"cap112:s{sec_num}({sub_num})",
                        unit_type="subsection",
                        ordinal=ordinal,
                        text=text,
                        statute_locator=f"s.{sec_num}({sub_num})",
                        heading=heading_text,
                    )
                )
        else:
            text = _clean("".join(section.itertext()))
            if not text:
                continue
            ordinal += 1
            drafts.append(
                UnitDraft(
                    unit_ref=f"cap112:s{sec_num}",
                    unit_type="section",
                    ordinal=ordinal,
                    text=text,
                    statute_locator=f"s.{sec_num}",
                    heading=heading_text,
                )
            )
    return drafts


def segment_html(html_bytes: bytes, source_id: str) -> list[UnitDraft]:
    """Coarse guidance segmentation for IRD pages (tables/paragraphs era).

    FAQ-style blocks (Q1/A1) become faq_item units; everything else becomes
    guidance_block units. Boilerplate navigation text is dropped.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_bytes.decode("utf-8", errors="replace"), "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    # IRD pages wrap the real article in div#content; everything outside is
    # navigation chrome. Fall back to body when the container is absent.
    root = soup.select_one("div#content") or soup.body or soup
    for chrome in root.select("div.content-title-div, .breadcrumb, #pagination"):
        chrome.decompose()

    if source_id.startswith('hk_ird_advance_'):
        return _segment_ruling(root, source_id)

    seen: set[str] = set()
    blocks: list[str] = []
    for el in root.find_all(["p", "li", "td", "h2", "h3", "h4"]):
        text = _clean(el.get_text(" "))
        if len(text) < 40:
            continue
        low = text.lower()
        if any(marker in low for marker in _BOILERPLATE_MARKERS):
            continue
        digest = hashlib.sha256(text.encode()).hexdigest()[:16]
        if digest in seen:
            continue
        seen.add(digest)
        blocks.append(text)

    drafts: list[UnitDraft] = []
    for i, text in enumerate(blocks, start=1):
        match = _FAQ_QUESTION.match(text)
        if match:
            unit_type = "faq_item"
            heading = f"Q{match.group(1)}: {match.group(2)[:72]}"
        else:
            unit_type = "guidance_block"
            heading = text[:72]
        drafts.append(
            UnitDraft(
                unit_ref=f"{source_id}:block{i:03d}",
                unit_type=unit_type,
                ordinal=i,
                text=text,
                heading=heading,
            )
        )
    return drafts


def _segment_ruling(root, source_id: str) -> list[UnitDraft]:
    """Keep the numbered IRD sections, including short dates and applicability.

    Whole table text is collected once; nested rows are not duplicated. The
    published ruling is separate from facts so retrieval can label its role.
    """
    headings = [p for p in root.find_all('p') if re.match(r'^\d+\.\s+\S', _clean(p.get_text(' ')))]
    drafts = []
    if not headings:
        for cell in root.find_all('td'):
            label = _clean(cell.get_text(' '))
            if not re.fullmatch(r'\d+\.', label):
                continue
            row = cell.find_parent('tr')
            table = cell.find_parent('table')
            if row is None or table is None:
                continue
            title = _clean(row.get_text(' '))
            parts = [_clean(r.get_text(' ')) for r in row.next_siblings
                     if getattr(r, 'name', None) == 'tr']
            body = '\n'.join(p for p in parts if p)
            if body:
                number = int(label[:-1])
                drafts.append(UnitDraft(unit_ref=f'{source_id}:section{number}',
                                        unit_type='ruling_block', ordinal=number,
                                        heading=title, text=body))
    for heading in headings:
        title = _clean(heading.get_text(' '))
        number = re.match(r'^(\d+)\.', title).group(1)
        parts = []
        for sibling in heading.next_siblings:
            if getattr(sibling, 'name', None) is None:
                continue
            if sibling.name == 'p' and re.match(r'^\d+\.\s+\S', _clean(sibling.get_text(' '))):
                break
            text = _clean(sibling.get_text(' '))
            if text and not any(marker in text.lower() for marker in _BOILERPLATE_MARKERS):
                parts.append(text)
        if parts:
            drafts.append(UnitDraft(unit_ref=f'{source_id}:section{number}', unit_type='ruling_block',
                                    ordinal=int(number), heading=title, text='\n'.join(parts)))
    if not drafts:
        raise ValueError('Expected numbered IRD ruling sections were not found')
    return drafts


def segment_pdf(pdf_bytes: bytes, source_id: str) -> list[UnitDraft]:
    """Page-level units for text PDFs (L0 traceability floor)."""
    from pypdf import PdfReader
    import io

    reader = PdfReader(io.BytesIO(pdf_bytes))
    drafts: list[UnitDraft] = []
    for page_no, page in enumerate(reader.pages, start=1):
        text = _clean(page.extract_text() or "")
        if len(text) < 40:
            continue
        drafts.append(
            UnitDraft(
                unit_ref=f"{source_id}:page{page_no:03d}",
                unit_type="pdf_page",
                ordinal=page_no,
                text=text,
                heading=f"page {page_no}",
            )
        )
    return drafts
