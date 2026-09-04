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
