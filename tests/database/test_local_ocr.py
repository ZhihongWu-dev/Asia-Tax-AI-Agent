import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local_ocr", ROOT / "database/tools/ocr_tesseract.py")
ocr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ocr)


def test_fingerprint_separates_source_models_and_orientation():
    config = {"rotation": 270, "scope": "English region"}
    original = ocr.fingerprint("source", config, {"eng": "model"})
    assert original == ocr.fingerprint("source", dict(reversed(list(config.items()))), {"eng": "model"})
    assert original != ocr.fingerprint("other source", config, {"eng": "model"})
    assert original != ocr.fingerprint("source", {**config, "rotation": 0}, {"eng": "model"})
    assert original != ocr.fingerprint("source", config, {"eng": "new model"})


def test_source_hash_mismatch_fails_before_ocr_or_output(tmp_path):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"original bytes")
    with pytest.raises(ValueError, match="source_hash_mismatch"):
        ocr.transcribe({"file": source.name, "sha256": "wrong", "id": "test"}, tmp_path, tmp_path, {})
    assert source.read_bytes() == b"original bytes"
    assert not (tmp_path / "ocr").exists()


def test_source_cannot_escape_library(tmp_path):
    root = tmp_path / "library"
    root.mkdir()
    with pytest.raises(ValueError, match="source_outside_library"):
        ocr.transcribe({"file": "../outside.pdf"}, root, tmp_path, {})


def test_resumed_blank_page_retains_review_warning_and_original(tmp_path):
    source = tmp_path / "source.pdf"
    with ocr.pymupdf.open() as pdf:
        pdf.new_page()
        pdf.save(source)
    original = source.read_bytes()
    sha = ocr.digest(original)
    model = tmp_path / "eng.traineddata"
    model.write_bytes(b"not needed because page is cached")
    config = {"language": "eng", "skip_pages": [], "scope": "full page", "rotation": 0, "clip_top": 0, "dpi": 300}
    profile = ocr.fingerprint(sha, config, {"eng": ocr.digest(model.read_bytes())})
    parts = tmp_path / "ocr" / ".parts" / "test" / profile
    parts.mkdir(parents=True)
    (parts / "0001.txt").write_text("", encoding="utf-8")
    result = ocr.transcribe({"file": source.name, "sha256": sha, "id": "test"}, tmp_path, tmp_path, config)
    assert result["pages"][0]["status"] == "empty_requires_review"
    assert result["review_status"] == "pending_original_comparison"
    assert source.read_bytes() == original
    assert json.loads((tmp_path / "ocr/test.json").read_text(encoding="utf-8"))["source_sha256"] == sha
