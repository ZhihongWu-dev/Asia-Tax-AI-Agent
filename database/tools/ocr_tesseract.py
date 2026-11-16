"""Resumable local OCR with explicit page orientation and extraction scope.

Retains originals. Outputs unverified transcriptions, never legal approval.
A source/config/model fingerprint isolates resumed pages from stale runs.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import tempfile
import os
import pymupdf


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fingerprint(source_sha256, config, model_hashes):
    return digest(json.dumps({"source": source_sha256, "config": config, "models": model_hashes},
                             sort_keys=True, separators=(",", ":")).encode())


def atomic_text(path, text):
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".ocr-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def transcribe(row, root, tessdata, config):
    source = (root / row["file"]).resolve()
    if not source.is_relative_to(root.resolve()):
        raise ValueError("source_outside_library")
    sha = digest(source.read_bytes())
    if sha != row["sha256"]:
        raise ValueError("source_hash_mismatch")
    models = {lang: digest((tessdata / (lang + ".traineddata")).read_bytes())
              for lang in config["language"].split("+")}
    profile = fingerprint(sha, config, models)
    output = root / "ocr"
    output.mkdir(exist_ok=True)
    # A new source/config never reuses old partial transcriptions.
    parts = output / ".parts" / row["id"] / profile
    parts.mkdir(parents=True, exist_ok=True)
    pages, records = [], []
    with pymupdf.open(source) as pdf:
        if any(p < 1 or p > len(pdf) for p in config["skip_pages"]):
            raise ValueError("skip_page_out_of_range")
        for index, page in enumerate(pdf, 1):
            path = parts / ("%04d.txt" % index)
            if index in config["skip_pages"]:
                text, state = "", "excluded_by_explicit_scope"
            elif path.exists():
                text = path.read_text(encoding="utf-8")
                state = "ocr_pending_review" if text.strip() else "empty_requires_review"
            else:
                area = page.rect
                clip = pymupdf.Rect(area.x0, area.y0 + area.height * config["clip_top"], area.x1, area.y1)
                pix = page.get_pixmap(matrix=pymupdf.Matrix(config["dpi"] / 72, config["dpi"] / 72).prerotate(config["rotation"]),
                                     clip=clip, alpha=False)
                encoded = pix.pdfocr_tobytes(language=config["language"], tessdata=str(tessdata))
                with pymupdf.open(stream=encoded, filetype="pdf") as recognized:
                    text = recognized[0].get_text()
                atomic_text(path, text)
                state = "ocr_pending_review" if text.strip() else "empty_requires_review"
            pages.append(text)
            records.append({"page": index, "status": state, "characters": len(text), "sha256": digest(text.encode())})
            print("%s: page %d/%d (%s)" % (row["id"], index, len(pdf), state), flush=True)
    stamp = datetime.now(timezone.utc).isoformat()
    metadata = {"doc_id": row["id"], "source_sha256": sha, "profile": profile, "config": config,
                "model_sha256": models, "created_at": stamp, "review_status": "pending_original_comparison", "pages": records}
    body = "#ocr sha256=%s model=tesseract-%s date=%s\n%s" % (sha, profile[:16], stamp[:10], "\f".join(pages))
    # Text remains unapproved even when the build can index it.
    atomic_text(output / (row["id"] + ".json"), json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    atomic_text(output / (row["id"] + ".txt"), body)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ids", nargs="+")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--tessdata", type=Path, required=True)
    parser.add_argument("--language", default="eng")
    parser.add_argument("--rotation", type=int, choices=[0, 90, 180, 270], default=0)
    parser.add_argument("--clip-top", type=float, default=0)
    parser.add_argument("--skip-pages", default="", help="1-based comma-separated pages excluded from the stated scope")
    parser.add_argument("--scope", required=True, help="Human-readable scope; explicitly state excluded languages/regions")
    parser.add_argument("--dpi", type=int, default=300)
    args = parser.parse_args()
    if not 0 <= args.clip_top < 1 or not 100 <= args.dpi <= 600:
        parser.error("clip-top must be in [0,1), dpi in [100,600]")
    if not re.fullmatch(r"[a-z_]+(?:\+[a-z_]+)*", args.language):
        parser.error("invalid language code")
    csv.field_size_limit(10**9)
    with (args.root / "doc.csv").open(encoding="utf-8-sig", newline="") as stream:
        docs = {row["id"]: row for row in csv.DictReader(stream)}
    config = {"language": args.language, "rotation": args.rotation, "clip_top": args.clip_top,
              "skip_pages": sorted({int(p) for p in args.skip_pages.split(",") if p}), "scope": args.scope,
              "dpi": args.dpi, "pymupdf": pymupdf.version[0], "mupdf": pymupdf.version[1]}
    for id in args.ids:
        transcribe(docs[id], args.root, args.tessdata, config)


if __name__ == "__main__":
    main()
