import importlib.util
import csv
from pathlib import Path
import re
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'database/tools'))
spec = importlib.util.spec_from_file_location('korean_snapshot_builder', ROOT / 'database/tools/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def example(marker='[시행일: 2027. 1. 1.] 제2조제2항', header='[시행 2026. 7. 1.]'):
    return f'''{header}
제1조(목적) Purpose.
제2조(소득) ① Current first paragraph.
② Current second paragraph.
법제처       2       국가법령정보센터
소득세법
제2조(소득) ① Future first paragraph.
② Future second paragraph.
{marker}
제3조(납부) Payment.
부칙 <법률 제1호>
제1조(시행일) Addendum.
'''


def test_future_replacement_is_separate_from_current_article_and_paragraphs():
    excluded = []
    rows, mode = build.slice_kr_pdf('test', example(), excluded_versions=excluded)
    by = {r['cite_id']: r['text'] for r in rows}
    assert len(by) == len(rows)
    assert mode == 'kr_pdf_article'
    assert 'Current second' in by['test#2']
    assert by['test#2.2'] == '② Current second paragraph.'
    assert not any(word in '\n'.join(by.values()) for word in ['Future', '국가법령정보센터', 'Addendum'])
    assert excluded[0]['cite_id'] == 'test#2'
    assert excluded[0]['snapshot'] == '2026-07-01'
    assert excluded[0]['effective_dates'] == ['2027-01-01']
    assert len(excluded[0]['text_sha256']) == 64


@pytest.mark.parametrize('marker,header', [('', '[시행 2026. 7. 1.]'),
    ('[시행일: 2027. 1. 1.] 제2조', ''),
    ('[시행일: 2026. 7. 1.] 제2조', '[시행 2026. 7. 1.]'),
    ('[시행일: 2025. 1. 1.] 제2조', '[시행 2026. 7. 1.]')])
def test_unresolved_repeated_version_fails_instead_of_dropping_or_mixing(marker, header):
    with pytest.raises(ValueError, match='Unresolved Korean article versions'):
        build.slice_kr_pdf('test', example(marker, header))


def test_unpaired_future_paragraph_preserves_current_text_and_flags_review():
    text = '[시행 2026. 7. 1.]\n제1조(목적) Body.\n[시행일: 2027. 1. 1.] 제1조제2항'
    reviews = []
    rows, _ = build.slice_kr_pdf('test', text, date_reviews=reviews)
    assert reviews == ['test#1']
    assert 'Body.' in rows[0]['text']
    assert '[시행일: 2027. 1. 1.] 제1조제2항' in rows[0]['text']


def test_future_marker_for_another_article_is_not_authority_to_drop_a_version():
    with pytest.raises(ValueError, match='marker refers to another article'):
        build.slice_kr_pdf('test', example('[시행일: 2027. 1. 1.] 제20조'))


def original_text(doc_id):
    with (ROOT / 'database/doc.csv').open(encoding='utf-8-sig', newline='') as f:
        row = next(r for r in csv.DictReader(f) if r['id'] == doc_id)
    text, _, status = build.to_text(row, 'pdf', ROOT)
    assert status in ('ok', 'ocr')
    return text


def test_real_income_snapshot_has_24_separate_future_replacements():
    text = original_text('kr.income-tax-act.20260701.ko')
    excluded = []
    rows, mode = build.slice_kr_pdf('kr.income-tax-act.20260701.ko', text, excluded_versions=excluded)
    assert mode == 'kr_pdf_article'
    assert len({r['cite_id'] for r in rows}) == len(rows)
    assert len(excluded) == 24
    assert {d for e in excluded for d in e['effective_dates']} == {'2027-01-01', '2027-09-09', '2028-01-01'}
    for row in rows:
        if row['kind'] == 'article':
            assert len(re.findall(r'^제\d+조(?:의\d+)?\(', row['text'], re.M)) == 1
    article = next(r['text'] for r in rows if r['cite_id'].endswith('#17'))
    assert '[시행일: 2027.' not in article
    assert '국가법령정보센터' not in article


def test_real_corporate_snapshot_preserves_article_count_without_exclusions():
    text = original_text('kr.corporate-tax-act.20260701.ko')
    excluded = []
    rows, _ = build.slice_kr_pdf('kr.corporate-tax-act.20260701.ko', text, excluded_versions=excluded)
    assert not excluded
    assert sum(r['kind'] == 'article' for r in rows) == 181
    assert len({r['cite_id'] for r in rows}) == len(rows)
