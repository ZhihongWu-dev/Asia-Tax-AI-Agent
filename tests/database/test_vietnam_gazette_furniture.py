import importlib.util
from pathlib import Path
import sys

import pymupdf
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'database/tools'))
spec = importlib.util.spec_from_file_location('builder_vn_gazette', ROOT / 'database/tools/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def test_verified_gazette_furniture_is_removed_without_changing_body():
    with pymupdf.open(ROOT / 'database/raw/vn/vn.law.cit67.2025.gazette.vi.pdf') as doc:
        text = '\n'.join(page.get_text() for page in doc)
    before, _ = build.slice_vn('vn.unchanged', text)
    after, mode = build.slice_vn('vn.law.cit67.2025.gazette.vi', text)
    assert mode == 'vn_article'
    assert len(before) == len(after) == 105
    furniture = (
        'CÔNG BÁO/Số 965 + 966/Ngày 24-7-2025',
        'Người ký: CỔNG THÔNG TIN ĐIỆN TỬ CHÍNH PHỦ',
        'Email: thongtinchinhphu@chinhphu.vn',
        'Cơ quan: VĂN PHÒNG CHÍNH PHỦ',
        'Thời gian ký: 28.07.2025 10:19:28 +07:00')
    normalize = lambda value: ''.join(value.split())
    for old, new in zip(before, after):
        expected = old['text']
        for line in furniture:
            expected = expected.replace(line, '')
            assert line not in new['text']
        assert old['cite_id'].split('#')[1] == new['cite_id'].split('#')[1]
        assert normalize(expected) == normalize(new['text'])
    assert any(furniture[0] in r['text'] for r in before)


def test_decree320_gazette_excludes_other_instruments_and_preserves_credit_conditions():
    with pymupdf.open(ROOT / 'database/raw/vn/vn.gazette1737-1738.2025.vi.pdf') as doc:
        pages = [page.get_text() for page in doc]
    rows, mode = build.slice_vn('vn.decree320.2025.gazette.vi', '\n'.join(pages))
    assert mode == 'vn_article'
    assert len({r['cite_id'] for r in rows}) == len(rows)
    body = '\n'.join(r['text'] for r in rows)
    assert '66.10/2025/NQ-CP' not in body
    assert 'CÔNG BÁO/' not in body
    assert 'Thời gian ký:' not in body
    credit = next(r['text'] for r in rows if r['cite_id'].endswith('#12.2'))
    # Independently locate the complete provision on verified PDF pages47-48.
    expected = pages[46].split('2. Doanh nghiệp Việt Nam', 1)[1]
    expected = '2. Doanh nghiệp Việt Nam' + expected
    continuation = pages[47].split('b3)', 1)[1].split('3. Số thuế thu nhập', 1)[0]
    expected += 'b3)' + continuation
    normalize = lambda value: ''.join(value.split())
    assert normalize(credit) == normalize(expected)
    assert any(r['cite_id'].endswith('#25') for r in rows)


def test_decree320_rejects_missing_issue_boundary():
    with pytest.raises(ValueError, match='instrument boundaries'):
        build.slice_vn('vn.decree320.2025.gazette.vi',
                       'Số: 320/2025/NĐ-CP\nĐiều 1. Scope\n1. Text')
