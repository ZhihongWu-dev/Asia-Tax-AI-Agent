"""Fixture gate for future per-format slicers."""
from pathlib import Path

root = Path(__file__).parent
fixtures = [p for p in root.iterdir() if p.is_file() and p.name not in {'README.md', 'run_slicers.py'}]
if not fixtures:
    print('No slicer fixtures are present; automatic re-slicing remains disabled.')
    raise SystemExit(0)
print(f'{len(fixtures)} fixture(s) present. Add explicit expected-count assertions with each slicer.')
