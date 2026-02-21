#!/usr/bin/env python3
"""
Seed realistic demo signals into the AEGIS monitor SignalStore.

Usage:
    python scripts/seed_monitor_signals.py
    python scripts/seed_monitor_signals.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure local package import works when running as `python scripts/...`.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from boundstate_aegis.monitoring.seeds import build_seed_signals, seed_signal_store


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed realistic demo monitor signals.")
    parser.add_argument("--dry-run", action="store_true", help="Print seed payloads without inserting.")
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print compact JSON during --dry-run.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    now = datetime.now(timezone.utc)

    if args.dry_run:
        payload = build_seed_signals(now=now)
        if args.compact:
            print(json.dumps(payload, separators=(",", ":"), ensure_ascii=True))
        else:
            print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0

    inserted, skipped, inserted_ids = seed_signal_store(now=now)
    print(f"Seed complete: inserted={inserted} skipped={skipped}")
    if inserted_ids:
        print("Inserted signal IDs:")
        for sid in inserted_ids:
            print(f"- {sid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
