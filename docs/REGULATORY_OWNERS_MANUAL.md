# AEGIS Regulatory Owner's Manual

## Purpose
This manual explains every control, status, and flag in the unified `Regulatory` workflow:
- `Landscape`
- `Signals`
- `Resolver`
- `Review Queue`

For full platform coverage across all modules, see `docs/AEGIS_OWNERS_MANUAL.md`.

## Top-Level Indicators
- `Regulatory nav red badge`: Number of items in HITL queue still in `PENDING_REVIEW` or `PENDING_APPROVAL`.
- `Human review required`: The item cannot be distributed without analyst action.
- `Critical flags: N`: Count of CRITICAL threat flags produced by resolver threat scoring.

## Landscape View
### Buttons and Inputs
- `Check Compliance`: Runs compliance check for selected material and forecast year.
- `Include Degradation Products`: Includes downstream degradation products in compliance result.
- `Forecast Year`: Controls projected view horizon in cascade/forecast output.

### Forecast Stage Badges
- `ENACTED`: Rule is in force.
- `FINAL PENDING`: Finalized but awaiting effective/compliance transition.
- `PROPOSED`: Formal proposal exists; not yet enacted.
- `UNDER CONSIDERATION`: Active agency process, pre-final.
- `MONITORING`: Watchlist or early motion; no active finalized action.

## Signals View
### Buttons
- `Refresh`: Reload latest signals.
- `Seed Demo`: Insert deterministic demo signals into store.
- `Clear Seeds`: Delete seeded demo signals only.

### Signal Badges
- `critical / high / medium / low`: L3/L4 priority levels from triage and impact scoring.

## Resolver View
### Buttons
- `Run Resolver`: Runs deterministic recursive regulatory resolver for input compound/product/CAS/SMILES.

### Output Meaning
- `Assertions`: Count of matched governed assertions.
- `Trajectory`: Regulatory direction (`STABLE`, `INCREASING`, `ACCELERATING`, `CONVERGING`).
- `Flags`: Threat flags (`INHERITED_LIABILITY`, `DESTRUCTION_TECH_GAP`, `REGULATORY_ACCELERATION`).

## Review Queue (HITL)
### Gate Status
- `PENDING_REVIEW` (HITL-1): Analyst must decide `Confirm`, `Escalate`, or `Dismiss`.
- `PENDING_APPROVAL` (HITL-2): Analyst must decide `Approve` or `Hold`.

### Actions
- `Confirm`: Moves item from `PENDING_REVIEW` to `PENDING_APPROVAL`.
- `Escalate`: Marks item for legal/regulatory escalation and keeps it active.
- `Dismiss`: Closes item. Requires written justification.
- `Approve`: Final approval; removes from pending queue.
- `Hold`: Keeps item pending for more evidence/review.

## Audit and Governance Behavior
- All HITL decisions are logged with analyst identity, action, timestamp, and justification when required.
- `Dismiss` without justification is rejected by design.
- Queue badge clears only when no items remain in pending states.

## Quick Triage Policy
- If any CRITICAL flag is present: escalate to legal/regulatory before approval.
- If class-level match only: confirm applicability to actual product scope.
- If evidence confidence is limited: hold and request additional validation before distribution.
