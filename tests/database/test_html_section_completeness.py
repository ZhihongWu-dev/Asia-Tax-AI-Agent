import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "database/tools"))
spec = importlib.util.spec_from_file_location("library_builder_completeness", ROOT / "database/tools/build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def test_retains_leading_and_short_rules_without_renumbering_existing_sections():
    raw = ("<html><body><p>Returns must be filed within 150 days.</p>"
           "<h2>First</h2><p>" + "long text " * 8 + "</p><h2>Rate</h2><p>17%</p>"
           "<h2>Second</h2><p>" + "more text " * 8 + "</p><h2>Third</h2><p>" + "last text " * 8 + "</p></body></html>").encode()
    clauses, mode = build.slice_html_sections("test", raw)
    by = {c["cite_id"]: c["text"] for c in clauses}
    assert mode == "html_section"
    assert by["test#h1"].startswith("First")
    assert by["test#h2"].startswith("Second")
    assert by["test#h3"].startswith("Third")
    assert "150 days" in by["test#lead"]
    assert "17%" in by["test#short1"]


def test_thai_corporate_guidance_keeps_filing_obligations():
    clauses, mode = build.slice_html_sections("th.rd.cit", (ROOT / "database/raw/th/th.rd.cit.html").read_bytes())
    text = "\n".join(c["text"] for c in clauses)
    assert "one hundred and fifty (150) days" in text
    assert "within seven days of the following month" in text


def test_failed_database_write_preserves_previous_database(tmp_path):
    import sqlite3
    import pytest
    target = tmp_path / "database.sqlite"
    build.publish_database(target, {})
    previous = target.read_bytes()
    class InvalidValue:
        def __str__(self):
            raise ValueError("invalid row")
    with pytest.raises(ValueError, match="invalid row"):
        build.publish_database(target, {"doc": [{"id": InvalidValue()}]})
    assert target.read_bytes() == previous
    assert list(tmp_path.glob(".database-*.sqlite")) == []
    build.publish_database(target, {"doc": [{"id": "verified.source"}]})
    with sqlite3.connect(target) as con:
        assert con.execute("select id from doc").fetchall() == [("verified.source",)]


def test_validation_error_does_not_publish_database(tmp_path, monkeypatch):
    target = tmp_path / "database.sqlite"
    build.publish_database(target, {"doc": [{"id": "previous.valid.source"}]})
    previous = target.read_bytes()
    monkeypatch.setattr(build, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["build.py"])
    def invalid_source(docs, errors, warnings, write_text):
        errors.append("invalid source fixture")
        return [], 0
    monkeypatch.setattr(build, "slice_all", invalid_source)
    assert build.main() == 1
    assert target.read_bytes() == previous
    assert "invalid source fixture" in (tmp_path / "STATUS.md").read_text(encoding="utf-8")
