import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'database/tools'))
spec = importlib.util.spec_from_file_location('bilingual_builder', ROOT / 'database/tools/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

TEXT = '''Enacting order
Schedule
Part 1
Agreement title
Article 1
Persons covered.
Article 2
Taxes covered.
Article 3
1. Definitions.
(Chinese Translation)
第一條
適用的人。
第二條
適用的稅。
第三條
1. 定義。
Part 2
Protocol title
I General
Protocol words.
(Chinese Translation)
I 一般規定
議定書文字。
'''


def test_parallel_languages_and_protocol_are_separate_and_complete():
    row = dict(id='treaty.ae-hk.example', type='treaty', jur='ae-hk', real_kind='rtf')
    clauses, mode = build.slice_doc(row, TEXT, [])
    assert mode == 'hk_bilingual_treaty'
    by_id = {c['cite_id'].split('#')[1]: c for c in clauses}
    assert len(by_id) == len(clauses)
    assert 'Chinese Translation' not in by_id['3']['text']
    assert 'Protocol' not in by_id['zh.3']['text']
    assert by_id['3']['parent'].endswith('#agreement.en')
    assert by_id['zh.3']['parent'].endswith('#agreement.zh')
    assert by_id['3.1']['parent'].endswith('#3')
    sections = [c['text'] for c in clauses if c['kind'] == 'section']
    assert ''.join(''.join(sections).split()) == ''.join(TEXT.split())


@pytest.mark.parametrize('text', [
    TEXT.replace('Part 2', 'Part 3'),
    TEXT.replace('(Chinese Translation)', '', 1),
    TEXT.replace('第三條', '第四條'),
    TEXT + '\nPart 1\n',
])
def test_ambiguous_or_mismatched_sections_fail_instead_of_merging(text):
    with pytest.raises(ValueError, match='bilingual|Bilingual'):
        build.slice_hk_bilingual_treaty('treaty.hk-example', text)


def test_ordinary_english_treaty_is_not_intercepted():
    assert build.slice_hk_bilingual_treaty('treaty.hk-example', TEXT.split('(Chinese Translation)')[0]) == ([], 'none')


def test_english_agreement_with_separate_bilingual_notes_preserves_boundaries():
    text = TEXT.split('(Chinese Translation)')[0] + '''Part 2
Protocol provisions.
Schedule 2
Part 1
Note Dated 10 December 2014 from Consul-General
Exchange terms.
(Chinese Translation)
來照中文。
Part 2
Note Dated 10 December 2014 from Secretary
Reply terms.
(Chinese Translation)
覆照中文。
'''
    row = dict(id='treaty.hk-jp.example', type='treaty', jur='hk-jp', real_kind='rtf')
    clauses, mode = build.slice_doc(row, text, [])
    assert mode == 'hk_treaty_bilingual_notes'
    by_id = {c['cite_id'].split('#')[1]: c for c in clauses}
    assert 'Protocol' not in by_id['3']['text']
    assert 'Exchange terms' in by_id['note.en']['text']
    assert 'Reply terms' in by_id['reply.en']['text']
    sections = [c['text'] for c in clauses if c['kind'] == 'section']
    assert ''.join(''.join(sections).split()) == ''.join(text.split())
    assert len(by_id) == len(clauses)
    with pytest.raises(ValueError, match='note schedule'):
        build.slice_hk_bilingual_treaty(row['id'], text.replace('Schedule 2', 'Unknown appendix'))
