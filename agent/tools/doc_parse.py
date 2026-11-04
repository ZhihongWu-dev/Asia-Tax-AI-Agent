#!/usr/bin/env python
"""Parse a case document once, cached by sha256 (agent/retrieval_spec.en.md §6.2).

  python agent/tools/doc_parse.py <file> <cache_dir> [--ocr]

A PDF with a text layer: text and tables from the text layer (PyMuPDF), derived = "text_layer". A scan or an image: OCR
with Qwen3-VL-4B-Instruct (transformers, local weights, greedy decoding), one pass per page giving the text and its tables as
HTML, derived = "ocr", confidence graded high / medium / low, never a score.
OCR text is a derivative, not a source: the source stays "document + page". Without --ocr an image or a scanned page is
recorded as "needs_ocr". The cache file is <cache_dir>/<sha16>.json.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

OCR_MODEL = "Qwen/Qwen3-VL-4B-Instruct"
OCR_SMALL = "Qwen/Qwen3-VL-2B-Instruct"   # when the GPU lacks room for the 4B model (other agents' models loaded); also Apache-2.0
NEED_GB = 10.5                            # free GPU memory the 4B model needs: about 8 GB of weights plus activations
PARSER_VERSION = "2"
MAX_PIXELS = 1600000              # about 2,000 vision tokens a page (patches of 32 x 32 pixels after merging)
OCR_PROMPT = ("Transcribe this page exactly as written, in reading order and in its original language. Do not translate, summarise, "
              "correct or complete anything; keep figures, dates, names and punctuation as they appear. Write every table as an HTML "
              "<table> with one <tr> per row and one <td> per cell, empty cells kept; write everything else as plain lines. Output only "
              "the transcription.")
_ocr = None


def sha16(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def cache_path(path, cache_dir):
    return Path(cache_dir) / ("%s.json" % sha16(path))


def cached(path, cache_dir):
    p = cache_path(path, cache_dir)
    try:
        d = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    except ValueError:
        return None
    return d if d and d.get("parser") == PARSER_VERSION else None


def pymupdf():
    import warnings
    warnings.filterwarnings("ignore", category=FutureWarning)
    try:
        import pymupdf as m
    except ImportError:
        import fitz as m
    return m


def text_layer(path):
    """[{page, text, tables}] from a PDF's text layer; a page with almost no text is marked for OCR."""
    m = pymupdf()
    out = []
    with m.open(str(path)) as doc:
        for i, page in enumerate(doc, 1):
            text = page.get_text("text") or ""
            tables = []
            try:
                for t in page.find_tables().tables:
                    rows = [[(c or "").strip() for c in row] for row in t.extract()]
                    if rows and any(any(c for c in r) for r in rows):
                        tables.append(rows)
            except Exception:                                    # noqa: BLE001  (table finder is best effort)
                tables = []
            scanned = len(re.sub(r"\s+", "", text)) < 20
            out.append({"page": i, "text": text.strip(), "tables": tables, "derived": "needs_ocr" if scanned else "text_layer",
                        "confidence": None if scanned else "high"})
    return out


def page_images(path):
    """PIL images of the pages of a PDF or of an image file."""
    from PIL import Image
    if Path(path).suffix.lower() == ".pdf":
        m = pymupdf()
        imgs = []
        with m.open(str(path)) as doc:
            for page in doc:
                pix = page.get_pixmap(dpi=200)
                imgs.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
        return imgs
    return [Image.open(path).convert("RGB")]


def ocr_engine():
    """Qwen3-VL-4B-Instruct through transformers' own implementation, loaded once per process on the GPU when there is one."""
    global _ocr
    if _ocr is None:
        import os
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        import torch
        from transformers import AutoProcessor, Qwen3VLForConditionalGeneration
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.bfloat16 if dev == "cuda" else torch.float32
        name = OCR_MODEL
        if dev == "cuda" and torch.cuda.mem_get_info()[0] / 2 ** 30 < NEED_GB:
            name = OCR_SMALL
        model = Qwen3VLForConditionalGeneration.from_pretrained(name, dtype=dtype, attn_implementation="sdpa").to(dev).eval()
        proc = AutoProcessor.from_pretrained(name)
        _ocr = (model, proc, dev, name)
    return _ocr


def ocr_image(img, task=OCR_PROMPT):
    """The transcription of one page image (plain lines and HTML tables), greedy decoding: the same page gives the same text."""
    import torch
    model, proc, dev, _ = ocr_engine()
    if img.width * img.height > MAX_PIXELS:                     # vision tokens grow with the pixels; a page needs no more
        f = (MAX_PIXELS / (img.width * img.height)) ** 0.5
        img = img.resize((int(img.width * f), int(img.height * f)))
    messages = [{"role": "user", "content": [{"type": "image", "image": img}, {"type": "text", "text": task}]}]
    inputs = proc.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_dict=True, return_tensors="pt").to(dev)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=2048, do_sample=False, repetition_penalty=1.02, use_cache=True)
    text = proc.batch_decode(out[:, inputs["input_ids"].shape[-1]:], skip_special_tokens=True)[0]
    return re.sub(r"^```(?:html)?\s*|\s*```$", "", text.strip())


def plain_text(transcription):
    """The page text of a transcription: tables as one line per row with cells separated by tabs, other tags removed."""
    def table(m):
        rows = []
        for tr in re.findall(r"(?is)<tr.*?</tr>", m.group(0)):
            rows.append("\t".join(re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", tr)))
        return "\n".join(rows)
    text = re.sub(r"(?is)<table.*?</table>", table, transcription)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def grade(text):
    """A confidence grade from what the text looks like, never a score: high / medium / low."""
    t = re.sub(r"\s+", "", text or "")
    if len(t) < 15:
        return "low"
    odd = len(re.findall(r"[^\w㐀-鿿぀-ヿ.,;:()（）、，。；：%/\-+#¥$€£·\"'“”‘’《》\[\]]", t)) / len(t)
    return "high" if odd < 0.02 else "medium" if odd < 0.08 else "low"


def html_tables(text):
    """Rows of the HTML (or markdown) tables of a transcription."""
    tables = []
    for tbl in re.findall(r"(?is)<table.*?</table>", text):
        rows = []
        for tr in re.findall(r"(?is)<tr.*?</tr>", tbl):
            rows.append([re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", tr)])
        if rows:
            tables.append(rows)
    if not tables:
        rows = [[c.strip() for c in line.strip().strip("|").split("|")] for line in text.splitlines() if line.strip().startswith("|")]
        rows = [r for r in rows if not all(re.fullmatch(r":?-{2,}:?", c or "-") for c in r)]
        if len(rows) >= 2:
            tables.append(rows)
    return tables


def parse(path, cache_dir, ocr=False):
    """The parsed document, from the cache when the file is unchanged; OCR only when asked and needed."""
    path = Path(path)
    old = cached(path, cache_dir)
    need_ocr = lambda d: any(p.get("derived") == "needs_ocr" for p in d.get("pages", []))
    if old and not (ocr and need_ocr(old)):
        return old
    if path.suffix.lower() == ".pdf":
        pages = text_layer(path)
    elif path.suffix.lower() in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"):
        pages = [{"page": 1, "text": "", "tables": [], "derived": "needs_ocr", "confidence": None}]
    else:
        try:
            pages = [{"page": 1, "text": path.read_text(encoding="utf-8"), "tables": [], "derived": "text", "confidence": "high"}]
        except (UnicodeDecodeError, ValueError):
            pages = []
    if ocr and any(p["derived"] == "needs_ocr" for p in pages):
        imgs = page_images(path)
        for p in pages:
            if p["derived"] != "needs_ocr" or p["page"] > len(imgs):
                continue
            img = imgs[p["page"] - 1]
            raw = ocr_image(img)
            p["text"], p["tables"] = plain_text(raw), html_tables(raw)
            p["derived"], p["confidence"] = "ocr", grade(p["text"])
    status = "parsed" if pages and not any(p["derived"] == "needs_ocr" for p in pages) else ("needs_ocr" if pages else "unreadable")
    derived = sorted({p["derived"] for p in pages})
    out = {"parser": PARSER_VERSION, "file": path.name, "sha16": sha16(path), "status": status, "derived": derived,
           "ocr_model": (_ocr[3] if _ocr else OCR_MODEL) if "ocr" in derived else None, "pages": pages}
    cp = cache_path(path, cache_dir)
    cp.parent.mkdir(parents=True, exist_ok=True)
    cp.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    d = parse(sys.argv[1], sys.argv[2], ocr="--ocr" in sys.argv)
    print(json.dumps({k: v for k, v in d.items() if k != "pages"}, ensure_ascii=False))
    for p in d["pages"]:
        print("--- page %d %s %s tables %d" % (p["page"], p["derived"], p["confidence"], len(p.get("tables") or [])))
        print(p["text"][:600])
