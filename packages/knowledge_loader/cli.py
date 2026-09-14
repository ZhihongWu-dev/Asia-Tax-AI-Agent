"""CLI: load the FSIE knowledge package into the configured database.

Usage:
    python -m packages.knowledge_loader.cli
    python -m packages.knowledge_loader.cli --skip-validation   # discouraged
"""

from __future__ import annotations

import argparse

from packages.persistence.db import session_scope
from packages.knowledge_loader.loader import persist_knowledge


def main() -> int:
    parser = argparse.ArgumentParser(description="Load the HK FSIE knowledge package.")
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip the contract validator (not recommended).",
    )
    args = parser.parse_args()

    with session_scope() as session:
        result = persist_knowledge(
            session, run_validation=not args.skip_validation
        )
        print("Knowledge package loaded:")
        for key, value in result.as_dict().items():
            print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
