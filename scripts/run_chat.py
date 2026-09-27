"""Start the built UI and API together on loopback; no secrets printed."""
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

if __name__ == '__main__':
    if not (ROOT / 'apps/web/dist/index.html').is_file():
        raise SystemExit('Build the frontend first: cd apps/web && npm ci && npm run build')
    import uvicorn
    uvicorn.run('apps.api.main:app', host='127.0.0.1', port=8000, log_level='info')
