# Railway Monitor Cron Cadence

Use a dedicated Railway service for monitoring cron (separate from the API web service).

## Config

- File: `railway.monitor.cron.json`
- Command: `python scripts/aegis_monitor_schedule.py`
- Cron schedule: `0 6 * * *` (daily UTC)

## Effective cadence

`scripts/aegis_monitor_schedule.py` runs:

- `critical` profile: daily
- `active` profile: Mondays (weekly)
- `sweep` profile: day `1` of each month (monthly)

## Notes

- Keep API service on `railway.json`.
- Attach monitoring env vars (`MONITOR_SLACK_WEBHOOK`, model keys, storage paths) to the cron service.

## Monday Demo Seeding

Before cron has accumulated real diffs, seed realistic signals so the Intelligence/Regulatory workflow is populated:

```bash
python scripts/seed_monitor_signals.py
```

The seed is idempotent (stable `signal_id` values), so rerunning does not duplicate rows.

Recommended sequence:
1. Seed demo signals.
2. Trigger one manual monitor run (baseline).
3. Enable cron for organic accumulation.
