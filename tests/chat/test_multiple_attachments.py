import json

import pytest

from packages.chat.attachments import MARKER, attachment_source, model_attachment_text
from packages.chat.pdf_attachments import MARKER as LEGACY_MARKER


def file(text):
    return {'name': 'metadata is not evidence.pdf', 'pages': [{'page': 1, 'text': text}],
            'thumbnail': 'data:image/jpeg;base64,private-display-data'}


@pytest.mark.parametrize('marker', [MARKER, LEGACY_MARKER])
def test_all_files_supply_ordered_fact_evidence_without_metadata(marker):
    message = 'Compare the files' + marker + json.dumps([file('first\npage'), file('second page')])
    source = attachment_source(message)
    assert source.startswith('Compare the files')
    assert source.index('first\npage') < source.index('second page')
    assert 'Next attachment; unverified' in source
    assert 'metadata is not evidence' not in source
    assert 'private-display-data' not in source


def test_model_input_removes_every_thumbnail_and_keeps_all_text():
    message = 'Question' + MARKER + json.dumps([file('one'), file('two')])
    output = model_attachment_text(message)
    assert 'thumbnail' not in output and 'private-display-data' not in output
    assert [x['pages'][0]['text'] for x in json.loads(output.split(MARKER)[1])] == ['one', 'two']


@pytest.mark.parametrize('payload', [[], [file('valid'), None], [file('valid'), {'pages': []}],
                                    [file('valid'), {'pages': [{'text': 7}]}], [file('x')] * 31])
def test_invalid_batch_is_not_silently_reduced_to_valid_members(payload):
    assert attachment_source('Question' + MARKER + json.dumps(payload)) is None


def test_legacy_single_file_evidence_is_preserved():
    assert attachment_source('Q' + LEGACY_MARKER + json.dumps(file('unchanged'))).endswith('unchanged')
