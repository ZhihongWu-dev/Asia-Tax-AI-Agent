"""Offline segmenter tests on minimal fixtures (no network)."""

from __future__ import annotations

import pytest

from packages.knowledge_pipeline.fetch import _check_domain, FetchError
from packages.knowledge_pipeline.segment import segment_cap112, segment_html

MINI_CAP112 = b"""<?xml version="1.0" encoding="UTF-8"?>
<ordinance xmlns="http://www.xml.gov.hk/schemas/hklm/1.0">
<main>
<part name="P4"><section name="s15J"><num value="15J">15J.</num>
<heading>Notification</heading>
<content>A person must notify.</content></section>
<section name="s15M"><num value="15M">15M.</num><heading>Participation</heading>
<subsection name="1"><num>(1)</num><content>Subject to section 15N.</content></subsection>
<subsection name="2"><num>(2)</num><content>Not less than 5% for 12 months.</content></subsection>
</section>
<section name="s99Z"><heading>Unrelated</heading><content>Other part.</content></section>
</part>
</main>
</ordinance>"""


def test_cap112_splits_subsections_and_skips_other_sections():
    units = segment_cap112(MINI_CAP112)
    refs = [u.unit_ref for u in units]
    assert refs == ["cap112:s15J", "cap112:s15M(1)", "cap112:s15M(2)"]
    by_ref = {u.unit_ref: u for u in units}
    assert by_ref["cap112:s15M(2)"].statute_locator == "s.15M(2)"
    assert by_ref["cap112:s15M(2)"].unit_type == "subsection"
    assert by_ref["cap112:s15J"].unit_type == "section"
    assert "5%" in by_ref["cap112:s15M(2)"].text


def test_cap112_units_carry_stable_hashes():
    units = segment_cap112(MINI_CAP112)
    assert all(len(u.text_sha256) == 64 for u in units)


MINI_HTML = b"""<html><body>
<div id="header"><p>Skip to main content and other navigation chrome here</p></div>
<div id="content">
<p>This paragraph explains the foreign-sourced income exemption scope in enough detail.</p>
<p>Short.</p>
<p>Another substantive paragraph about the economic substance requirement details.</p>
<p>This paragraph explains the foreign-sourced income exemption scope in enough detail.</p>
</div>
<div id="footer"><p>Copyright notice and privacy policy boilerplate text here</p></div>
</body></html>"""


def test_html_scopes_to_content_div_dedupes_and_filters():
    units = segment_html(MINI_HTML, "hk_ird_test")
    assert len(units) == 2  # dedupe dropped the copy; 'Short.' too short
    assert all(u.unit_ref.startswith("hk_ird_test:block") for u in units)
    assert all("navigation chrome" not in u.text for u in units)
    assert all("Copyright" not in u.text for u in units)


def test_domain_allowlist_blocks_foreign_hosts():
    allowed = ["www.ird.gov.hk", "www.elegislation.gov.hk"]
    _check_domain("https://www.ird.gov.hk/eng/tax/bus_fsie.htm", allowed)
    with pytest.raises(FetchError):
        _check_domain("https://evil.example.com/x", allowed)
