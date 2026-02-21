# AEGIS Production Owner's Manual

## Document Control
- System: AEGIS (BoundState PFAS Intelligence Platform)
- Environment target: Production (Vercel + Railway)
- Last updated: 2026-02-21
- Owner audience: platform owner, ops lead, regulatory analyst lead, legal reviewer

## 1. Purpose
This is the production operating manual for AEGIS. It defines:
- how the system is deployed
- how it is operated day-to-day
- which controls are mandatory for production
- how to handle incidents, releases, and audits

This document is the source for operational behavior. Demo notes are secondary.

## 2. Platform Scope
AEGIS currently includes:
- UI modules: Fate Explorer, SENTINEL, Regulatory, Portfolio, Reports, Evidence, Analysis, Tier 1
- Unified Regulatory workflow under `Regulatory`:
  - `Landscape`
  - `Signals`
  - `Resolver`
  - `Review Queue` (HITL)
- API services:
  - `monitor` (signals, governance, source policy)
  - `resolver` (recursive exposure + HITL gates)
  - `regulatory` (landscape/check/forecast)

## 3. Production Architecture
### 3.1 Runtime topology
- Vercel:
  - Hosts frontend bundle
  - Proxies `/api/*` to backend (or uses explicit API base)
- Railway API service:
  - Runs FastAPI app (`boundstate_aegis.api.aegis_api:app`)
  - Serves all `/api/v1/*` endpoints
- Railway monitor cron service:
  - Runs `python scripts/aegis_monitor_schedule.py`
  - Executes tiered monitor cadence (daily/weekly/monthly)

### 3.2 Data planes
- Assertions governance store:
  - SQLite default: `monitor_data/assertions.db`
  - Source file bootstrap: APAC/Western/TFA YAML
- Monitor signal store:
  - SQLite default: `monitor_data/monitor.db`
  - Optional Postgres via `AEGIS_MONITOR_DB_URL`
- Resolver HITL store:
  - SQLite default: `monitor_data/resolver_hitl.db`
- Snapshot store:
  - `monitor_data/snapshots/*` (retention controlled by env)
- Hash store:
  - `monitor_data/url_hashes.json` (supports HMAC integrity signing)

## 4. Access Control and Security
### 4.1 API auth model
- Header accepted:
  - `X-AEGIS-API-Key: <key>`
  - `Authorization: Bearer <key>` (fallback)
- Auth is enabled by default:
  - `AEGIS_MONITOR_API_AUTH_ENABLED=true`

### 4.2 Roles
- `viewer`: read-only data access
- `operator`: viewer + run/review actions
- `approver`: viewer/operator + assertion approvals + HITL approval
- `admin`: full access (superset)

### 4.3 Key format
- `AEGIS_MONITOR_API_KEYS` format:
  - `key1:viewer,key2:operator,key3:approver,key4:admin`
- Demo minimum (single-user mode):
  - one admin key only

### 4.4 Additional security controls
- IP allowlist (optional but recommended):
  - `AEGIS_MONITOR_API_ALLOWLIST_CIDRS=...`
- Rate limiting:
  - `AEGIS_MONITOR_API_RATE_LIMIT_PER_MIN` (default 120)
  - anonymous requests further constrained
- Auth backoff/lock:
  - built-in exponential lockout after repeated failures
- HTTP security headers:
  - `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`, `Referrer-Policy`

## 5. Required Production Environment Variables
### 5.1 Frontend (Vercel)
| Variable | Required | Purpose |
|---|---|---|
| `VITE_AEGIS_API_KEY` | Yes | API key used by UI for protected monitor/resolver endpoints |
| `VITE_API_BASE` | Optional | Explicit backend base URL; default empty uses proxy |
| `VITE_RAILWAY_API_BASE` | Optional | Alternate explicit backend URL |
| `VITE_AEGIS_MONITOR_API_KEY` | Optional | Fallback key if `VITE_AEGIS_API_KEY` absent |

### 5.2 Backend API / monitor (Railway)
| Variable | Required | Purpose |
|---|---|---|
| `AEGIS_MONITOR_API_AUTH_ENABLED` | Yes | Enable/disable API key auth |
| `AEGIS_MONITOR_API_KEYS` | Yes | Key-to-role map |
| `AEGIS_MONITOR_API_RATE_LIMIT_PER_MIN` | Yes | Per-identity request cap |
| `AEGIS_MONITOR_API_MANUAL_RUN_ENABLED` | Recommended | Enable `/api/v1/monitor/run` control-plane endpoint |
| `AEGIS_MONITOR_API_ALLOWLIST_CIDRS` | Recommended | Restrict monitor control-plane by CIDR |
| `AEGIS_HASH_STORE_SECRET` | Yes | Enforce HMAC integrity on hash store |
| `MONITOR_SLACK_WEBHOOK` | Yes | Slack signal delivery |
| `AEGIS_MONITOR_DB_URL` | Recommended | Postgres or sqlite DSN for signal/lock store |
| `AEGIS_MONITOR_SQLITE_PATH` | If no DB URL | Explicit sqlite path |
| `AEGIS_ASSERTION_DB_PATH` | Yes | Assertion governance store path |
| `AEGIS_RESOLVER_HITL_DB_PATH` | Recommended | Resolver HITL store path |
| `AEGIS_ANTHROPIC_API_KEY` | Recommended | AI triage/impact execution |
| `ANTHROPIC_API_KEY` | Optional fallback | Alternate key name |
| `AEGIS_MONITOR_STRICT_AI_MODE` | Yes | Hard-fail if AI unavailable |
| `AEGIS_TRIAGE_MODEL` | Yes | L3 model ID |
| `AEGIS_ANALYST_MODEL` | Yes | L4 model ID |
| `AEGIS_TRIAGE_TOKEN_CAP` | Yes | Triage token cap |
| `AEGIS_MONITOR_PROXY_ENABLED` | Yes | Proxy fallback toggle |
| `AEGIS_MONITOR_PROXY_ALLOWLIST` | Yes | Proxy host allowlist |
| `AEGIS_MONITOR_RUN_LOCK_NAME` | Yes | Monitor run lock identifier |
| `AEGIS_MONITOR_RUN_LOCK_TTL_SECONDS` | Yes | Lock TTL to prevent overlap |
| `AEGIS_MONITOR_SNAPSHOT_RETENTION_MONTHS` | Yes | Snapshot retention window |

### 5.3 Alert fallbacks (optional but recommended for critical)
| Variable | Required | Purpose |
|---|---|---|
| `AEGIS_MONITOR_ALERT_EMAIL_ENABLED` | Optional | Email fallback toggle |
| `AEGIS_MONITOR_ALERT_EMAIL_SMTP_HOST` | If email enabled | SMTP host |
| `AEGIS_MONITOR_ALERT_EMAIL_SMTP_PORT` | If email enabled | SMTP port |
| `AEGIS_MONITOR_ALERT_EMAIL_SMTP_USER` | If email enabled | SMTP username |
| `AEGIS_MONITOR_ALERT_EMAIL_SMTP_PASSWORD` | If email enabled | SMTP password |
| `AEGIS_MONITOR_ALERT_EMAIL_USE_TLS` | If email enabled | TLS toggle |
| `AEGIS_MONITOR_ALERT_EMAIL_FROM` | If email enabled | Sender |
| `AEGIS_MONITOR_ALERT_EMAIL_TO` | If email enabled | Comma-delimited recipients |
| `AEGIS_MONITOR_PAGERDUTY_ROUTING_KEY` | Optional | PagerDuty Events v2 routing key |

## 6. Endpoint and Role Matrix
### 6.1 Monitor endpoints (`/api/v1/monitor`)
| Endpoint | Method | Minimum role |
|---|---|---|
| `/run` | POST | operator (and manual run enabled) |
| `/runs/{run_id}` | GET | viewer |
| `/signals` | GET | viewer |
| `/signals/{signal_id}` | GET | viewer |
| `/seed-demo` | POST | operator |
| `/seed-demo/clear` | POST | operator |
| `/digest/weekly` | GET | viewer |
| `/pending-assertions` | GET | approver |
| `/assertions` | GET | viewer |
| `/assertions/{id}/history` | GET | approver |
| `/assertions/{id}/approve` | POST | approver |
| `/assertions/{id}/reject` | POST | approver |
| `/sources/classification` | GET | viewer |
| `/sources/missing-priority` | GET | viewer |

### 6.2 Resolver endpoints (`/api/v1/resolver`)
| Endpoint | Method | Minimum role |
|---|---|---|
| `/resolve` | POST | viewer |
| `/resolve/{compound}` | GET | viewer |
| `/resolve/batch` | POST | viewer |
| `/products` | GET | viewer |
| `/pending` | GET | viewer |
| `/review` | POST | operator |
| `/approve` | POST | approver |

### 6.3 Regulatory endpoints (`/api/v1/regulatory`)
| Endpoint | Method | Auth |
|---|---|---|
| `/check` | GET | public API route |
| `/cascade` | GET | public API route |
| `/apac` | GET | public API route |
| `/apac/quality-audit` | GET | public API route |

## 7. Daily Operations
### 7.1 Morning health check (5 minutes)
1. `GET /health` returns `status=healthy`.
2. `GET /api/v1/monitor/signals?limit=1` returns 200 with valid auth.
3. `GET /api/v1/resolver/pending?limit=10` returns queue data.
4. Check Railway logs for monitor run lock errors or auth brute-force warnings.
5. Verify nav queue badge aligns with pending count.

### 7.2 Analyst workflow
1. Open `Regulatory -> Signals` and triage latest events.
2. Run Resolver on impacted materials.
3. Process `Review Queue`:
   - confirm/escalate/dismiss for `PENDING_REVIEW`
   - approve/hold for `PENDING_APPROVAL`
4. Ensure all dismiss/edit/reclassify actions include justification.

### 7.3 End-of-day checks
- No stuck monitor runs (`/runs/{run_id}` not left in running state).
- No unreviewed critical resolver items.
- Alert channels (Slack/email/PagerDuty) functioning.

## 8. Scheduled Execution and Cadence
Cron service (`railway.monitor.cron.json`) defaults:
- schedule: `0 6 * * *` UTC
- command: `python scripts/aegis_monitor_schedule.py`

Effective profile cadence:
- `critical`: daily
- `active`: weekly (Monday)
- `sweep`: monthly (day 1)

## 9. Demo Runbook (Operator-safe)
1. Validate auth (`/api/v1/monitor/signals?limit=1`).
2. Seed demo signals (`POST /api/v1/monitor/seed-demo`).
3. Show `Regulatory -> Signals`.
4. Run Resolver on a known compound.
5. Show queue transitions in `Review Queue`.
6. Clear demo seeds (`POST /api/v1/monitor/seed-demo/clear`) if required.

## 10. Backups and Recovery
### 10.1 What to back up
- `monitor_data/monitor.db` (signals + run locks, if sqlite)
- `monitor_data/assertions.db` (assertion governance)
- `monitor_data/resolver_hitl.db` (HITL decisions)
- `monitor_data/snapshots/` (evidence snapshots)
- `monitor_data/url_hashes.json` (hash baseline state)

### 10.2 Backup cadence
- DB files: daily snapshot + 30-day rolling retention
- Snapshots directory: weekly archive + policy retention
- Before each production deploy: one pre-deploy backup checkpoint

### 10.3 Restore checklist
1. Stop API and cron services.
2. Restore DB files and snapshot directory.
3. Verify file permissions.
4. Restart API then cron.
5. Run smoke tests (Section 7.1).
6. Validate queue integrity and latest signal reads.

## 11. Incident Response
### 11.1 Severity levels
- `SEV-1`: auth bypass/data corruption/no signal path for critical sources
- `SEV-2`: resolver/HITL outage or persistent 5xx on monitor endpoints
- `SEV-3`: degraded performance, non-critical feed delays

### 11.2 First 15-minute response
1. Freeze manual runs (`AEGIS_MONITOR_API_MANUAL_RUN_ENABLED=false` if needed).
2. Confirm database health and lock status.
3. Check auth/key validity and allowlist settings.
4. Verify model key availability if strict AI mode enabled.
5. Communicate incident state and ETA to stakeholders.

## 12. Release Management
### 12.1 Pre-release checklist
- All target tests pass in deployment env.
- Auth and RBAC smoke tested with non-admin + approver keys.
- `/health`, `/monitor/signals`, `/resolver/pending` verified.
- If `AEGIS_HASH_STORE_SECRET` enabled, ensure hash store is signed/migrated.
- Rollback plan and backup checkpoint created.

### 12.2 Post-release validation
1. Open UI and confirm module navigation.
2. Confirm `Regulatory` subviews render: Landscape, Signals, Resolver, Review Queue.
3. Seed and clear demo signals once in staging.
4. Verify queue badge increments/decrements correctly.
5. Verify no unauthorized endpoint access.

## 13. Data Governance and Audit
- Assertions use immutable event chain hashes in governance store.
- HITL gate events are append-only (DB triggers block update/delete).
- Justification is mandatory for override/dismiss/reclassify/edit actions.
- Use resolver IDs and assertion history endpoints for audit exports.

## 14. Operational Targets (SLO guidance)
- API availability target: 99.5% monthly
- Monitor run completion target: >99% scheduled runs
- Queue processing target: critical items acknowledged same business day
- Auth integrity target: zero unauthorized control-plane actions

These are operating targets and should be formalized in customer SLA language as needed.

## 15. Known Constraints
- First monitor run seeds baseline and may not generate signals.
- Signals appear when source content changes after baseline.
- Optional dependency issues in build environments can affect local frontend builds.
- External government source reliability varies by jurisdiction.

## 16. What Not To Do
- Do not disable auth in production.
- Do not use shared keys without role scoping beyond initial single-operator phase.
- Do not approve/dismiss without justification where required.
- Do not run cron and manual runs concurrently without lock controls.
- Do not treat seeded demo signals as real regulatory events.

## 17. Quick Verification Commands
### Linux/macOS
```bash
curl -sS -H "X-AEGIS-API-Key: <KEY>" "https://aegis.boundstate.ai/api/v1/monitor/signals?limit=1"
curl -sS -H "X-AEGIS-API-Key: <KEY>" "https://aegis.boundstate.ai/api/v1/resolver/pending?limit=5"
curl -sS -X POST -H "X-AEGIS-API-Key: <KEY>" "https://aegis.boundstate.ai/api/v1/monitor/seed-demo"
```

### Windows PowerShell
```powershell
$h = @{ "X-AEGIS-API-Key" = "<KEY>" }
Invoke-RestMethod -Method Get -Uri "https://aegis.boundstate.ai/api/v1/monitor/signals?limit=1" -Headers $h
Invoke-RestMethod -Method Get -Uri "https://aegis.boundstate.ai/api/v1/resolver/pending?limit=5" -Headers $h
Invoke-RestMethod -Method Post -Uri "https://aegis.boundstate.ai/api/v1/monitor/seed-demo" -Headers $h
```

## 18. Related Docs
- `docs/AEGIS_OWNERS_MANUAL.md` (general operator summary)
- `docs/REGULATORY_OWNERS_MANUAL.md` (Regulatory deep-dive)
- `docs/RAILWAY_MONITOR_CRON.md` (cron profile behavior)
