import importlib.util
from pathlib import Path
import sys

import pymupdf

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
