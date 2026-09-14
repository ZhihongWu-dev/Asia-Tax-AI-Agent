"""Build the knowledge layer: snapshots + legal units.

Usage: make knowledge-build
"""

from __future__ import annotations

import argparse
import sys

from packages.knowledge_pipeline.build import build_knowledge
from packages.persistence.db import session_scope


def main(argv: list[str] | None = None) -> int:
    args = argparse.ArgumentParser(description="Fetch, snapshot and segment official sources.")
    args.add_argument("--no-fetch", action="store_true", help="register sources only")
    parsed = args.parse_args(argv)

    with session_scope() as session:
        summary = build_knowledge(session, fetch=not parsed.no_fetch)

    print(f"{'source':<38} {'status':<14} {'units':>6}  notes")
    print("-" * 78)
    for s in summary.sources:
        notes = []
        if s.reused_snapshot:
            notes.append("snapshot reused")
        if s.drift:
            notes.append("HASH DRIFT vs manifest")
        if s.error:
            notes.append(s.error)
        print(f"{s.source_id:<38} {s.parse_status:<14} {s.units:>6}  {'; '.join(notes)}")
    print("-" * 78)
    print(f"parsed {summary.parsed} sources, {summary.total_units} legal units")
    failed = [s for s in summary.sources if s.parse_status == "failed"]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
