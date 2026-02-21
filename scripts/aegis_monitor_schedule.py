#!/usr/bin/env python3
"""Railway cron scheduler for split monitor cadence.

Runs:
- critical profile daily
- active profile weekly (Monday UTC)
- sweep profile monthly (1st day UTC)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

from boundstate_aegis.monitoring.source_policy import RunProfile
from boundstate_aegis.monitoring.url_monitor import run_monitor


def _run(profile: str, dry_run: bool) -> Dict[str, Any]:
    summary = run_monitor(dry_run=dry_run, profile=profile)
    return {"profile": profile, "summary": summary}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run scheduled AEGIS monitor cadence.")
    parser.add_argument("--dry-run", action="store_true", help="Do not persist state or send alerts.")
    parser.add_argument(
        "--force-profiles",
        nargs="*",
        choices=[RunProfile.CRITICAL.value, RunProfile.ACTIVE.value, RunProfile.SWEEP.value],
        help="Override scheduler and run explicit profile list.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    now = datetime.now(timezone.utc)
    runs: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []

    # Daily high-priority watch.
    if args.force_profiles:
        plan = args.force_profiles
    else:
        plan = [RunProfile.CRITICAL.value]
        # Weekly active sources every Monday UTC.
        if now.weekday() == 0:
            plan.append(RunProfile.ACTIVE.value)
        # Monthly sweep on day 1 UTC.
        if now.day == 1:
            plan.append(RunProfile.SWEEP.value)

    for profile in plan:
        try:
            runs.append(_run(profile, dry_run=args.dry_run))
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            errors.append({"profile": profile, "error": str(exc)})

    payload = {
        "ran_at_utc": now.isoformat(),
        "dry_run": args.dry_run,
        "planned_profiles": plan,
        "runs": runs,
        "errors": errors,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
