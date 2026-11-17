import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'database/tools'))
spec = importlib.util.spec_from_file_location('builder_id_numeric', ROOT / 'database/tools/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def test_wrapped_reference_and_payment_day_survive_indonesian_slicing():
    text = '\n'.join(
        f'Pasal {n}\n(1)\nPembayaran Pajak Penghasilan Pasal\n22\n'
        'dilakukan paling lambat tanggal\n15\nbulan berikutnya setelah Masa Pajak berakhir.'
        for n in (94, 95, 96)
    )
    rows, mode = build.slice_id('id.fixture', text)
    assert mode == 'id_pasal'
    assert {r['cite_id'] for r in rows} == {
        f'id.fixture#{n}{suffix}' for n in (94, 95, 96) for suffix in ('', '(1)')
    }
    for row in rows:
        assert 'Pasal\n22\n' in row['text']
        assert 'tanggal\n15\n' in row['text']


def test_default_page_cleanup_remains_available_for_other_slicers():
    assert build.clean_lines('Legal text\n22\nMore text') == ['Legal text', 'More text']
