"""Scoped, original-file provenance for the in-progress Vietnam policies."""
import json
from copy import deepcopy
from pathlib import Path


_MANIFEST = json.loads(Path(__file__).with_name('vn_2026_sources.json').read_text(encoding='utf-8'))


def sources_for(scope):
    if scope not in ('company', 'employment'):
        raise ValueError('Unknown Vietnam policy source scope')
    # Calculation consumers must not mutate provenance for future assessments.
    return deepcopy(_MANIFEST[scope])
