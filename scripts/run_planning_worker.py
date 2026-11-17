"""Run the durable planner worker; --once handles at most one claim."""
import argparse
import asyncio
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--check', action='store_true', help='Check queue schema and library reader without claiming jobs')
    args = parser.parse_args()
    try:
        from packages.domain_bridge.planning_daemon import start
        start(once=args.once, check_only=args.check)
    except (KeyboardInterrupt, asyncio.CancelledError):
        return 130
    except Exception:
        print('planning_worker_failed', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
