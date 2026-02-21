#!/usr/bin/env python3
"""CLI wrapper for AEGIS regulatory monitor."""

from __future__ import annotations

import argparse
import json

from boundstate_aegis.monitoring.source_policy import RunProfile
from boundstate_aegis.monitoring.url_monitor import run_monitor


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AEGIS regulatory monitor pipeline (L1-L4)")
    parser.add_argument("--dry-run", action="store_true", help="Do not persist state or send alerts.")
    parser.add_argument(
        "--profile",
        choices=[
            RunProfile.CRITICAL.value,
            RunProfile.ACTIVE.value,
            RunProfile.PRIORITY.value,
            RunProfile.FULL.value,
            RunProfile.SWEEP.value,
        ],
        default=RunProfile.PRIORITY.value,
        help="Source run profile (default: priority)",
    )
    args = parser.parse_args()

    summary = run_monitor(dry_run=args.dry_run, profile=args.profile)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
