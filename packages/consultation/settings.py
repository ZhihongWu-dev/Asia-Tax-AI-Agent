"""Explicit, reversible workflow switch shared by runtime and API."""
import os
from pathlib import Path
import json
from dotenv import dotenv_values


def brief_enabled():
    root = Path(__file__).resolve().parents[2]
    local = dotenv_values(root / '.env')
    defaults = json.loads((root / 'config/runtime.json').read_text())
    return (os.environ.get('FSIE_ACTIVE_WORKFLOW') or local.get('FSIE_ACTIVE_WORKFLOW') or
            defaults.get('FSIE_ACTIVE_WORKFLOW', 'brief')) == 'brief'
