import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'database/tools'))
spec = importlib.util.spec_from_file_location('library_builder_main', ROOT / 'database/tools/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


@pytest.mark.parametrize('wrapper', ['header', 'footer', 'nav'])
def test_explicit_main_survives_malformed_chrome_wrapper(wrapper):
    sections = ''.join(
        f'<h2>Tax rule {i}</h2><p>Legal text remains. This provision specifies the annual reporting obligation.</p>'
        for i in range(3)
    )
    raw = f'<body><{wrapper}><nav>Menu only</nav><main>{sections}</main></{wrapper}><footer>Footer only</footer></body>'.encode()
    text = build.html_text(raw)
    assert 'Legal text remains.' in text
    assert 'Menu only' not in text and 'Footer only' not in text
    rows, mode = build.slice_html_sections('ae.fixture', raw)
    assert mode == 'html_section'
    assert len(rows) == 3
    assert all('Legal text remains.' in row['text'] for row in rows)


def test_ordinary_chrome_removal_still_excludes_navigation_text():
    raw = b'<body><header>Banner</header><main><p>Rule</p></main><footer>Contact</footer></body>'
    assert build.html_text(raw) == 'Rule'


def test_archived_uae_topup_page_retains_actual_policy_text():
    raw = (ROOT / 'database/raw/ae/ae.mof.top-up-tax.html').read_bytes()
    text = build.html_text(raw)
    assert len(text) > 1000
    assert '750' in text and '2025' in text
    assert 'controlled foreign' in text.lower()
    assert text.strip() != 'Skip to main content'
