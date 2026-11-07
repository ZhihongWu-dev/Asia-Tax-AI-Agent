"""OCR for originals without a text layer (数据库规范.md §4.1 step 9): Qwen3-VL through agent/tools/doc_parse.py, one pass per
page, greedy decoding, so the same page gives the same text. No Baidu components.

  python database/tools/ocr.py <doc_id> [<doc_id> ...]
  python database/tools/ocr.py --scans            # every PDF in doc.csv with at least half of its pages scanned

Only pages whose text layer is (nearly) empty are read (fewer than build.OCR_PAGE_MIN characters); the others are left
empty in the file. Writes ocr/<doc_id>.txt: a first line "#ocr sha256=<sha256 of the original> model=<model>
date=<YYYY-MM-DD>", then the pages separated by form feeds. When the sha256 matches the original, build.py gives each
scanned page its OCR text and keeps the text layer of the others (text_status "ocr"). Pages are kept one by one under ocr/.parts/<doc_id>/ while running, so an interrupted run resumes.
OCR text is a reading of the scan, not the original: quotes are copied from it as from any text, and the note of a
parameter citing it says "OCR text, to be checked against the original".
"""
import argparse
import datetime
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "agent" / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def page_image(page):
    from PIL import Image
    pix = page.get_pixmap(dpi=200)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def tidy(text):
    """A page whose transcription ran away repeats one line until the token limit: keep the line three times at most."""
    out, run = [], 0
    for ln in text.splitlines():
        run = run + 1 if out and ln.strip() and ln.strip() == out[-1].strip() else 0
        if run < 3:
            out.append(ln)
    return "\n".join(out)


def ocr_doc(row):
    import fitz
    import doc_parse
    import build
    src = ROOT / row["file"]
    sha = hashlib.sha256(src.read_bytes()).hexdigest()
    dst = ROOT / "ocr" / (row["id"] + ".txt")
    if dst.exists() and dst.read_text(encoding="utf-8").startswith("#ocr sha256=%s " % sha):
        print("%s: done already" % row["id"])
        return
    parts = ROOT / "ocr" / ".parts" / row["id"]
    parts.mkdir(parents=True, exist_ok=True)
    model = doc_parse.ocr_engine()[3]
    with fitz.open(str(src)) as pdf:
        n = len(pdf)
        for i, page in enumerate(pdf):
            f = parts / ("%04d.txt" % (i + 1))
            if f.exists():
                continue
            if len(page.get_text("text").strip()) >= build.OCR_PAGE_MIN:
                f.write_text("", encoding="utf-8")         # the text layer serves for this page
                continue
            f.write_text(tidy(doc_parse.plain_text(doc_parse.ocr_image(page_image(page)))), encoding="utf-8")
            print("%s: page %d/%d" % (row["id"], i + 1, n), flush=True)
    pages = [(parts / ("%04d.txt" % (i + 1))).read_text(encoding="utf-8") for i in range(n)]
    head = "#ocr sha256=%s model=%s date=%s" % (sha, model, datetime.date.today().isoformat())
    dst.write_text(head + "\n" + "\f".join(pages), encoding="utf-8")
    shutil.rmtree(str(parts), ignore_errors=True)
    print("%s: %d pages -> %s" % (row["id"], n, dst.relative_to(ROOT)))


def main():
    import build
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--scans", action="store_true", help="every PDF of doc.csv whose text layer is empty")
    args = ap.parse_args()
    docs = {r["id"]: r for r in build.read_csv(ROOT / "doc.csv")}
    ids = list(args.ids)
    if args.scans:
        for r in docs.values():
            p = ROOT / r["file"]
            if p.exists() and build.real_kind(p, p.suffix.lstrip(".")) == "pdf" and r["id"] not in ids:
                pages = build.pdf_pages(p)
                if 2 * sum(1 for x in pages if len(x.strip()) < build.OCR_PAGE_MIN) >= len(pages):
                    ids.append(r["id"])
    for i in ids:
        if i not in docs:
            print("! %s: not in doc.csv" % i)
            continue
        ocr_doc(docs[i])
    return 0


if __name__ == "__main__":
    sys.exit(main())
