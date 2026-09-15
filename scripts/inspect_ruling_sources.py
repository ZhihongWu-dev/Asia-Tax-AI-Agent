"""Replay literal content-retention probes against pinned official rulings.

Fetches only the four research-card sources through the existing snapshot loader.
Cached snapshots are reused; this is not a freshness check or an LLM evaluation.
Full text and runtime results remain in the git-ignored raw directory.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bs4 import BeautifulSoup
from packages.knowledge_pipeline.fetch import fetch_source, manifest
from packages.knowledge_pipeline.segment import segment_html


def main() -> int:
    package = ROOT / 'knowledge/hong_kong/fsie'
    cards = json.loads((package / 'ruling_research_cards.json').read_text(encoding='utf-8'))['cards']
    data = manifest()
    sources = {s['source_id']: s for s in data['sources']}
    reports = []
    failed = False
    for card in cards:
        sid = card['source_id']
        try:
            assert card['synthetic'] is False and card['model_input_authorized'] is False
            entry = sources[sid]
            result = fetch_source(entry, data['allowed_source_domains'], timeout=30)
            if result.sha256 != entry['content_sha256']:
                raise ValueError('Snapshot hash differs from the reviewed source; review before replay.')
            soup = BeautifulSoup(result.content, 'html.parser')
            article = soup.select_one('div#content')
            if article is None:
                raise ValueError('Expected IRD article container not found')
            title = f"Advance Ruling Case No. {card['case_number']}"
            text = ' '.join(article.get_text(' ', strip=True).split())
            if title not in text:
                raise ValueError('Unexpected document title')
            units = segment_html(result.content, sid)
            probes = []
            for key, needle, locator in card['probes']:
                found = needle in text
                failed |= not found
                probes.append(dict(key=key, locator=locator, raw_found=found,
                                   retained_in_units=any(needle in u.text for u in units)))
            reports.append(dict(source_id=sid, sha256=result.sha256,
                                snapshot=str(result.snapshot_path.relative_to(ROOT)),
                                reused_snapshot=result.reused, units=len(units), probes=probes))
        except Exception as exc:
            failed = True
            reports.append(dict(source_id=sid, error=str(exc)))
    report = dict(checked_at=datetime.now(timezone.utc).isoformat(),
                  mode='literal parser probes; no LLM, database or rule-engine execution',
                  cards_sha256=hashlib.sha256((package / 'ruling_research_cards.json').read_bytes()).hexdigest(),
                  reports=reports)
    output = package / 'raw/ruling_probe_report.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
