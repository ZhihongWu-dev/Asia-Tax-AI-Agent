import importlib.util
from pathlib import Path

import pymupdf
import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("builder_id_compilation", ROOT / "database/tools/build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
DOC_ID = "id.tax-law-consolidation-2023.id"


def test_multilaw_compilation_preserves_every_original_page_and_article26_scope():
    with pymupdf.open(ROOT / "database/raw/id/id.tax-law-consolidation-2023.id.pdf") as doc:
        pages = [page.get_text() for page in doc]
    rows, mode = build.slice_doc(dict(id=DOC_ID, type="law", jur="id", real_kind="pdf"),
                                 "\n".join(pages), pages)
    assert len(pages) == 426
    expected = {f"{DOC_ID}#p{i + 1}": page.strip()
                for i, page in enumerate(pages) if page.strip()}
    assert len(rows) == len(expected) == 425  # One blank page retains its page number gap.
    assert {r["cite_id"]: r["text"].strip() for r in rows} == expected
    article26 = expected[f"{DOC_ID}#p242"]
    assert "PASAL 26" in article26
    assert "20% (dua puluh persen)" in article26
    assert "selain bentuk usaha tetap di Indonesia" in article26
    assert "diturunkan dengan Peraturan Pemerintah" in article26
    assert "perkiraan penghasilan" in article26


def test_compilation_cannot_silently_fall_back_to_single_act_without_pages():
    with pytest.raises(ValueError, match="original PDF pages"):
        build.slice_doc(dict(id=DOC_ID, type="law", jur="id", real_kind="pdf"),
                        "Pasal 26\n(1) Incomplete extraction", [])
