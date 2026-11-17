"""Web numeric content is not PDF pagination, including real split-span dates."""
import importlib.util
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'database/tools'))
spec = importlib.util.spec_from_file_location('library_builder_numbers', ROOT / 'database/tools/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def test_real_announcement_keeps_signing_date_and_all_three_items():
    file = 'raw/cn/cn.cs.2026-27.html'
    text, _, status = build.to_text(dict(id='cn.cs.2026-27', sha256='', jur='cn', file=file), 'html', None)
    assert status == 'ok'
    assert '2026年9月1日' in text.splitlines()
    rows, mode = build.slice_doc(dict(id='cn.cs.2026-27', type='regulation', jur='cn',
                                      real_kind='html', file=file), text, [])
    by = {r['cite_id']: r['text'] for r in rows}
    assert mode == 'cn_item' and set(by) == {'cn.cs.2026-27#i1', 'cn.cs.2026-27#i2', 'cn.cs.2026-27#i3'}
    assert '20%税率' in by['cn.cs.2026-27#i1']
    assert '次月15日' in by['cn.cs.2026-27#i2']
    assert '次年6月30日' in by['cn.cs.2026-27#i2']
    assert by['cn.cs.2026-27#i3'].count('2026年9月1日') == 2


def test_inline_markup_preserves_words_digits_spaces_and_real_breaks():
    raw = ('<body><p>Income <b>tax</b> applies to <span>20</span><span>%</span>.</p>'
           '<p><span>202</span><span>6</span>年<span>9</span>月<span>1</span>日<br>Next line</p>'
           '<p><span>first</span> <em>second</em></p></body>').encode()
    text = build.html_text(raw, preserve_inline=True)
    assert text.splitlines() == ['Income tax applies to 20%.', '2026年9月1日',
                                 'Next line', 'first second']


def test_html_numeric_cells_survive_item_and_article_slicing(tmp_path, monkeypatch):
    for heads, mode in [(('一、', '二、', '三、'), 'cn_item'),
                        (('第一条', '第二条', '第三条'), 'cn_article')]:
        raw = ('<body>' + ''.join(f'<p>{h}这是明确的税收规定，所有数值必须保留。</p>' for h in heads)
               + '<table><tr><td>税率</td><td>20</td></tr><tr><td>天数</td><td>15</td></tr></table></body>')
        (tmp_path / 'source.html').write_text(raw, encoding='utf-8')
        monkeypatch.setattr(build, 'ROOT', tmp_path)
        text = build.html_text(raw.encode(), preserve_inline=True)
        rows, actual = build.slice_doc(dict(id='cn.fixture', type='law', jur='cn',
                                            real_kind='html', file='source.html'), text, [])
        assert actual == mode
        lines = rows[-1]['text'].splitlines()
        assert lines[-4:] == ['税率', '20', '天数', '15']


def test_pdf_page_cleanup_is_unchanged():
    assert build.clean_lines('text\n12\n- 13 -\nmore') == ['text', 'more']
    assert build.clean_lines('20\n15', remove_page_numbers=False) == ['20', '15']


@pytest.mark.parametrize('doc_id,cite', [
    ('jp.nta.tsutatsu.cta.13-2-1', 'jp.nta.tsutatsu.cta.13-2-1#13_2-1-11'),
    ('jp.nta.tsutatsu.cta.9-1-3', 'jp.nta.tsutatsu.cta.9-1-3#9-1-15_2'),
    ('th.mof.fx.2548', 'th.mof.fx.2548#c4')])
def test_existing_japanese_and_thai_locators_are_preserved(doc_id, cite):
    row = next(r for r in build.read_csv(ROOT / 'database/doc.csv') if r['id'] == doc_id)
    path = ROOT / 'database' / row['file']
    row['real_kind'] = build.real_kind(path, path.suffix.lstrip('.'))
    text, pages, status = build.to_text(row, row['real_kind'], None)
    assert status == 'ok'
    clauses, _ = build.slice_doc(row, text, pages)
    assert cite in {c['cite_id'] for c in clauses}
