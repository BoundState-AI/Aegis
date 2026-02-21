# AEGIS Owner's Manual

## Scope
This is the full operator manual for the AEGIS platform UI and core workflows.
It covers:
- Navigation modules
- Main controls and status badges
- Regulatory Intelligence workflow (Signals -> Resolver -> HITL)
- Authentication requirements
- Demo seeding and queue handling

For production operations (env vars, RBAC matrix, runbooks, backup/restore, release checks), use `docs/AEGIS_PRODUCTION_OWNERS_MANUAL.md`.

For a deeper Regulatory-only reference, see `docs/REGULATORY_OWNERS_MANUAL.md`.

## Primary Navigation (bottom bar)
- `Fate Explorer` (`/`): PFAS degradation pathway browsing.
- `SENTINEL` (`/litigation`): litigation/publication dynamics signals.
- `Regulatory` (`/regulatory`): unified compliance + intelligence workflow.
- `Portfolio` (`/portfolio`): portfolio-level risk aggregation.
- `Reports` (`/reports`): executive report generation.
- `Evidence` (`/evidence`): evidence chain and traceability views.
- `Analysis` (`/analysis`): compound analysis workflow.
- `Tier 1` (`/tier1`): structural similarity and substructure intelligence.

## Global Indicators
- `Regulatory red number badge`: count of pending HITL queue items with status:
  - `PENDING_REVIEW`
  - `PENDING_APPROVAL`
- Badge clears only when both queues are empty.

## Authentication Model (UI/API)
- Control-plane endpoints require API key auth.
- Expected header:
  - `X-AEGIS-API-Key: <key>`
- Frontend key env var:
  - `VITE_AEGIS_API_KEY`
- Backend monitor auth env vars:
  - `AEGIS_MONITOR_API_AUTH_ENABLED=true`
  - `AEGIS_MONITOR_API_KEYS=<key>:<role>`

Minimum demo setup:
- One shared key with admin role.
- Same key value in frontend and backend envs.

## Regulatory Module (Unified Workflow)
The Regulatory tab is the operational center and has 4 subviews.

### 1) Landscape
Purpose:
- baseline compliance and jurisdiction forecast from governed assertions

Main controls:
- `Material` input
- `Include Degradation Products` toggle
- `Forecast Year`
- `Check Compliance` button

Forecast stage badges:
- `ENACTED`
- `FINAL PENDING`
- `PROPOSED`
- `UNDER CONSIDERATION`
- `MONITORING`

### 2) Signals
Purpose:
- show detected regulatory changes from monitor pipeline

Main controls:
- `Refresh`
- `Seed Demo`
- `Clear Seeds`

Signal severity badges:
- `critical`
- `high`
- `medium`
- `low`

### 3) Resolver
Purpose:
- run recursive exposure analysis for product/compound/CAS/SMILES

Main controls:
- input field (product, compound, CAS, or SMILES)
- `Run Resolver`

Output highlights:
- assertion counts
- trajectory label
- threat flags (`INHERITED_LIABILITY`, `DESTRUCTION_TECH_GAP`, `REGULATORY_ACCELERATION`)

### 4) Review Queue (HITL)
Purpose:
- analyst governance gate before distribution

Gate states:
- `PENDING_REVIEW` (HITL-1)
- `PENDING_APPROVAL` (HITL-2)

Actions:
- `Confirm`: move to `PENDING_APPROVAL`
- `Escalate`: mark for legal/regulatory escalation
- `Dismiss`: close item (justification required)
- `Approve`: final approval and queue removal
- `Hold`: keep item pending for further review

Special tags:
- `Human review required`: mandatory analyst intervention before distribution
- `Critical flags: N`: number of CRITICAL resolver flags

## Fate Explorer
Purpose:
- map parent compound to downstream degradation products with citations

Typical use:
- choose compound
- review pathways, conditions, and products
- trace evidence to cited literature

## SENTINEL (Litigation)
Purpose:
- track litigation-relevant momentum and publication dynamics

Typical use:
- review trajectory indicators
- inspect risk windows and key signal shifts

## Portfolio
Purpose:
- aggregate risk across multiple materials

Typical use:
- run a basket of compounds
- compare prioritization and risk concentration

## Reports
Purpose:
- generate executive-friendly output and summaries

Typical use:
- produce snapshots for leadership updates
- package evidence and compliance context

## Evidence
Purpose:
- inspect provenance and citation chain for claims and outputs

Typical use:
- validate supporting evidence for flagged items

## Analysis
Purpose:
- compound-level analysis workflow with supporting data cards

## Tier 1
Purpose:
- structural similarity and substructure signal exploration

Typical use:
- inspect nearest analogs and pattern-based flags

## In-app Help
Each major page includes a `?` help modal (header icon) with:
- what the page does
- how to use
- use cases
- tips
- flags/status explanations (where configured)
- actions/buttons explanations (where configured)

## Demo Runbook (Fast)
1. Confirm API key auth works:
   - `GET /api/v1/monitor/signals?limit=1`
2. Seed demo signals:
   - `POST /api/v1/monitor/seed-demo`
3. Open `Regulatory -> Signals` and verify populated feed.
4. Open `Regulatory -> Resolver`, run sample compound.
5. Open `Regulatory -> Review Queue`, process pending items.
6. Verify nav badge decreases to `0` after approvals/dismissals.

## Common Issues
- `401 Unauthorized`:
  - frontend and backend keys do not match
  - missing `VITE_AEGIS_API_KEY`
- `Invalid monitor API key`:
  - key format mismatch in `AEGIS_MONITOR_API_KEYS`
  - backend not restarted after env change
- empty Signals list:
  - monitor has not run yet, or no changes detected
  - seed demo signals for demo environments

## Data Governance Notes
- HITL actions are audit-logged.
- Dismiss actions require justification.
- Resolver and monitor outputs are designed for analyst review, not blind auto-distribution.
