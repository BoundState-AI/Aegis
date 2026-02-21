#!/usr/bin/env python3
"""
Monitor endpoints for L1-L4 regulatory intelligence pipeline.
"""

from __future__ import annotations

import ipaddress
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel

from boundstate_aegis.config import (
    MONITOR_API_ALLOWLIST_CIDRS,
    MONITOR_API_AUTH_ENABLED,
    MONITOR_API_KEYS,
    MONITOR_API_MANUAL_RUN_ENABLED,
    MONITOR_API_RATE_LIMIT_PER_MIN,
    PENDING_ASSERTIONS_DIR,
)
from boundstate_aegis.monitoring.alerts import build_weekly_digest
from boundstate_aegis.monitoring.assertions import AssertionStore
from boundstate_aegis.monitoring.seeds import build_seed_signals, seed_signal_store
from boundstate_aegis.monitoring.source_policy import (
    MISSING_PRIORITY_SOURCES,
    RunProfile,
    classify_all,
    classification_summary,
    select_sources,
)
from boundstate_aegis.monitoring.stores import SignalStore
from boundstate_aegis.monitoring.url_monitor import ALL_URLS, run_monitor

router = APIRouter()
logger = logging.getLogger(__name__)

_AUTH_LOCK = threading.Lock()
_RATE_LOCK = threading.Lock()
_RUN_LOCK = threading.Lock()

_AUTH_FAIL_STATE: Dict[str, Dict[str, Any]] = {}
_RATE_STATE: Dict[str, List[float]] = {}
_RUN_STATE: Dict[str, Dict[str, Any]] = {}
_ACTIVE_RUN_ID: Optional[str] = None

_BACKOFF_STEPS = (60, 120, 300)
_MAX_FAIL_BEFORE_BACKOFF = 5

_ASSERTION_STORE = AssertionStore()
_ASSERTION_STORE.bootstrap_from_yaml()


class MonitorRunAcceptedResponse(BaseModel):
    run_id: str
    status: str
    profile: str
    dry_run: bool
    accepted_at: str


class MonitorRunStatusResponse(BaseModel):
    run_id: str
    status: str
    profile: str
    dry_run: bool
    requested_by: str
    requested_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    summary: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class SignalListResponse(BaseModel):
    total: int
    signals: List[Dict[str, Any]]


class PendingActionRequest(BaseModel):
    reason: Optional[str] = None


class SeedDemoResponse(BaseModel):
    inserted: int
    skipped: int
    signal_ids: List[str]
    dry_run: bool = False


class ClearDemoResponse(BaseModel):
    deleted: int
    prefix: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_api_key_map(raw: str) -> Dict[str, str]:
    key_map: Dict[str, str] = {}
    for chunk in (raw or "").split(","):
        part = chunk.strip()
        if not part:
            continue
        # Preferred format: "token:role" pairs.
        if ":" in part:
            key, role = part.split(":", 1)
            norm_key = key.strip()
            norm_role = role.strip().lower()
        else:
            # Backward-compatible shorthand: "token" -> admin role.
            norm_key = part
            norm_role = os.getenv("AEGIS_MONITOR_API_DEFAULT_ROLE", "admin").strip().lower() or "admin"
        if norm_key and norm_role:
            key_map[norm_key] = norm_role
    # Additional compatibility path for single-key setups.
    if not key_map:
        single_key = os.getenv("AEGIS_MONITOR_API_KEY", "").strip()
        if single_key:
            single_role = os.getenv("AEGIS_MONITOR_API_KEY_ROLE", "admin").strip().lower() or "admin"
            key_map[single_key] = single_role
    return key_map


def _extract_key(x_aegis_api_key: Optional[str], authorization: Optional[str]) -> str:
    if x_aegis_api_key and x_aegis_api_key.strip():
        return x_aegis_api_key.strip()
    auth = (authorization or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return ""


def _key_prefix(key: str) -> str:
    if not key:
        return "anonymous"
    return f"{key[:6]}***"


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _rate_limit(identity: str, limit_per_minute: int) -> None:
    now = time.time()
    with _RATE_LOCK:
        events = [ts for ts in _RATE_STATE.get(identity, []) if now - ts < 60]
        if len(events) >= max(1, int(limit_per_minute)):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        events.append(now)
        _RATE_STATE[identity] = events


def _auth_failure(prefix: str) -> int:
    with _AUTH_LOCK:
        row = _AUTH_FAIL_STATE.get(prefix, {"count": 0, "step": 0, "locked_until": 0.0})
        row["count"] += 1
        if row["count"] >= _MAX_FAIL_BEFORE_BACKOFF:
            duration = _BACKOFF_STEPS[min(row["step"], len(_BACKOFF_STEPS) - 1)]
            row["locked_until"] = time.time() + duration
            row["step"] = min(row["step"] + 1, len(_BACKOFF_STEPS) - 1)
            row["count"] = 0
        _AUTH_FAIL_STATE[prefix] = row
        remaining = max(0, int(row["locked_until"] - time.time()))
        return remaining


def _auth_success(prefix: str) -> None:
    with _AUTH_LOCK:
        _AUTH_FAIL_STATE.pop(prefix, None)


def _auth_locked(prefix: str) -> int:
    with _AUTH_LOCK:
        row = _AUTH_FAIL_STATE.get(prefix)
        if not row:
            return 0
        return max(0, int(float(row.get("locked_until", 0.0)) - time.time()))


def _allowed_by_cidr(ip_raw: str) -> bool:
    allowlist = os.getenv("AEGIS_MONITOR_API_ALLOWLIST_CIDRS", MONITOR_API_ALLOWLIST_CIDRS).strip()
    if not allowlist:
        return True
    try:
        ip_obj = ipaddress.ip_address(ip_raw)
    except ValueError:
        return False

    cidrs = [item.strip() for item in allowlist.split(",") if item.strip()]
    for cidr in cidrs:
        try:
            if ip_obj in ipaddress.ip_network(cidr, strict=False):
                return True
        except ValueError:
            continue
    return False


def _authorize(required_roles: Set[str]) -> Callable[..., Dict[str, str]]:
    async def _dependency(
        request: Request,
        x_aegis_api_key: Optional[str] = Header(default=None, alias="X-AEGIS-API-Key"),
        authorization: Optional[str] = Header(default=None, alias="Authorization"),
    ) -> Dict[str, str]:
        client_ip = _client_ip(request)
        if not _allowed_by_cidr(client_ip):
            logger.warning("Monitor API denied by IP allowlist: ip=%s", client_ip)
            raise HTTPException(status_code=403, detail="IP not allowed for monitor API")

        supplied = _extract_key(x_aegis_api_key, authorization)
        prefix = _key_prefix(supplied)
        is_auth_enabled = os.getenv("AEGIS_MONITOR_API_AUTH_ENABLED", str(MONITOR_API_AUTH_ENABLED)).lower() in {
            "1", "true", "yes", "on",
        }

        # Apply per-identity rate limits before expensive logic.
        per_min = int(os.getenv("AEGIS_MONITOR_API_RATE_LIMIT_PER_MIN", str(MONITOR_API_RATE_LIMIT_PER_MIN)))
        identity = f"key:{prefix}" if supplied else f"ip:{client_ip}"
        anon_limit = min(5, per_min)
        _rate_limit(identity=identity, limit_per_minute=per_min if supplied else anon_limit)

        if not is_auth_enabled:
            return {"role": "admin", "auth": "disabled", "principal": "auth-disabled", "client_ip": client_ip}

        key_map = _parse_api_key_map(os.getenv("AEGIS_MONITOR_API_KEYS", MONITOR_API_KEYS))
        if not key_map:
            raise HTTPException(status_code=503, detail="Monitor API keys not configured")

        locked_seconds = _auth_locked(prefix)
        if supplied and locked_seconds > 0:
            logger.warning(
                "Monitor API auth locked: ip=%s key_prefix=%s wait=%ss",
                client_ip,
                prefix,
                locked_seconds,
            )
            raise HTTPException(status_code=429, detail=f"Too many failed auth attempts. Retry in {locked_seconds}s")

        if not supplied:
            _auth_failure("missing")
            logger.warning("Monitor API auth missing key: ip=%s", client_ip)
            raise HTTPException(status_code=401, detail="Missing monitor API key")

        role = key_map.get(supplied)
        if not role:
            locked = _auth_failure(prefix)
            logger.warning("Monitor API auth invalid key: ip=%s key_prefix=%s", client_ip, prefix)
            if locked > 0:
                raise HTTPException(status_code=429, detail=f"Invalid key. Temporarily locked for {locked}s")
            raise HTTPException(status_code=403, detail="Invalid monitor API key")

        if role != "admin" and role not in required_roles:
            _auth_failure(prefix)
            logger.warning(
                "Monitor API auth insufficient role: ip=%s key_prefix=%s role=%s required=%s",
                client_ip,
                prefix,
                role,
                ",".join(sorted(required_roles)),
            )
            raise HTTPException(status_code=403, detail="Insufficient role for endpoint")

        _auth_success(prefix)
        logger.info("Monitor API auth success: ip=%s key_prefix=%s role=%s", client_ip, prefix, role)
        return {"role": role, "auth": "api_key", "principal": prefix, "client_ip": client_ip}

    return _dependency


def _pending_files() -> List[Path]:
    if not PENDING_ASSERTIONS_DIR.exists():
        return []
    return sorted(PENDING_ASSERTIONS_DIR.glob("*.json")) + sorted(PENDING_ASSERTIONS_DIR.glob("*.yaml"))


def _manual_run_enabled() -> bool:
    return os.getenv("AEGIS_MONITOR_API_MANUAL_RUN_ENABLED", str(MONITOR_API_MANUAL_RUN_ENABLED)).lower() in {
        "1", "true", "yes", "on",
    }


def _execute_monitor_run(run_id: str) -> None:
    global _ACTIVE_RUN_ID
    with _RUN_LOCK:
        row = _RUN_STATE.get(run_id)
        if not row:
            return
        row["status"] = "running"
        row["started_at"] = _now_iso()

    try:
        summary = run_monitor(dry_run=bool(row["dry_run"]), profile=str(row["profile"]))
        with _RUN_LOCK:
            row = _RUN_STATE.get(run_id) or {}
            row["status"] = "completed"
            row["summary"] = summary
            row["finished_at"] = _now_iso()
            _RUN_STATE[run_id] = row
    except Exception as exc:  # pragma: no cover - runtime guard
        with _RUN_LOCK:
            row = _RUN_STATE.get(run_id) or {}
            row["status"] = "failed"
            row["error"] = str(exc)[:600]
            row["finished_at"] = _now_iso()
            _RUN_STATE[run_id] = row
    finally:
        with _RUN_LOCK:
            if _ACTIVE_RUN_ID == run_id:
                _ACTIVE_RUN_ID = None


def _start_monitor_run(run_id: str) -> None:
    worker = threading.Thread(target=_execute_monitor_run, args=(run_id,), daemon=True)
    worker.start()


require_viewer = _authorize({"viewer", "operator", "approver"})
require_operator = _authorize({"operator", "approver"})
require_approver = _authorize({"approver"})


@router.post("/run", response_model=MonitorRunAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
async def monitor_run(
    dry_run: bool = Query(False),
    profile: str = Query(RunProfile.PRIORITY.value),
    auth: Dict[str, str] = Depends(require_operator),
) -> MonitorRunAcceptedResponse:
    global _ACTIVE_RUN_ID
    if not _manual_run_enabled():
        raise HTTPException(status_code=403, detail="Manual monitor run endpoint is disabled")

    with _RUN_LOCK:
        if _ACTIVE_RUN_ID:
            active = _RUN_STATE.get(_ACTIVE_RUN_ID, {})
            if active.get("status") in {"queued", "running"}:
                raise HTTPException(
                    status_code=409,
                    detail=f"Another monitor run is already in progress (run_id={_ACTIVE_RUN_ID})",
                )
        run_id = f"run_{uuid4().hex[:12]}"
        _RUN_STATE[run_id] = {
            "run_id": run_id,
            "status": "queued",
            "profile": profile,
            "dry_run": dry_run,
            "requested_by": auth.get("principal", "unknown"),
            "requested_at": _now_iso(),
        }
        _ACTIVE_RUN_ID = run_id

    _start_monitor_run(run_id)
    logger.info(
        "Monitor run queued: run_id=%s profile=%s dry_run=%s requested_by=%s",
        run_id,
        profile,
        dry_run,
        auth.get("principal", "unknown"),
    )
    row = _RUN_STATE[run_id]
    return MonitorRunAcceptedResponse(
        run_id=run_id,
        status=row["status"],
        profile=profile,
        dry_run=dry_run,
        accepted_at=row["requested_at"],
    )


@router.get("/runs/{run_id}", response_model=MonitorRunStatusResponse)
async def monitor_run_status(
    run_id: str,
    _auth: Dict[str, str] = Depends(require_viewer),
) -> MonitorRunStatusResponse:
    row = _RUN_STATE.get(run_id)
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    return MonitorRunStatusResponse(**row)


@router.get("/signals", response_model=SignalListResponse)
async def list_signals(
    limit: int = Query(50, ge=1, le=500),
    _auth: Dict[str, str] = Depends(require_viewer),
) -> SignalListResponse:
    store = SignalStore()
    signals = store.list_recent(limit=limit)
    return SignalListResponse(total=len(signals), signals=signals)


@router.get("/signals/{signal_id}")
async def get_signal(
    signal_id: str,
    _auth: Dict[str, str] = Depends(require_viewer),
) -> Dict[str, Any]:
    store = SignalStore()
    signal = store.get(signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return signal


@router.post("/seed-demo", response_model=SeedDemoResponse)
async def seed_demo_signals(
    dry_run: bool = Query(False, description="Return demo payload without writing to SignalStore."),
    _auth: Dict[str, str] = Depends(require_operator),
) -> SeedDemoResponse:
    if dry_run:
        rows = build_seed_signals()
        return SeedDemoResponse(
            inserted=0,
            skipped=0,
            signal_ids=[str(r.get("signal_id")) for r in rows if r.get("signal_id")],
            dry_run=True,
        )

    inserted, skipped, inserted_ids = seed_signal_store()
    return SeedDemoResponse(
        inserted=inserted,
        skipped=skipped,
        signal_ids=inserted_ids,
        dry_run=False,
    )


@router.post("/seed-demo/clear", response_model=ClearDemoResponse)
async def clear_demo_signals(
    _auth: Dict[str, str] = Depends(require_operator),
) -> ClearDemoResponse:
    store = SignalStore()
    prefix = "SEED_DEMO_"
    deleted = store.delete_by_signal_id_prefix(prefix=prefix)
    return ClearDemoResponse(deleted=deleted, prefix=prefix)


@router.get("/digest/weekly")
async def get_weekly_digest(
    limit: int = Query(20, ge=1, le=100),
    _auth: Dict[str, str] = Depends(require_viewer),
) -> Dict[str, Any]:
    store = SignalStore()
    signals = store.list_recent(limit=limit)
    return build_weekly_digest(signals)


@router.get("/pending-assertions")
async def list_pending_assertions(
    _auth: Dict[str, str] = Depends(require_approver),
) -> Dict[str, Any]:
    files = _pending_files()
    payload = []
    for path in files:
        payload.append(
            {
                "id": path.stem,
                "filename": path.name,
                "path": str(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return {"total": len(payload), "pending": payload}


@router.get("/assertions")
async def list_assertions(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(100, ge=1, le=1000),
    _auth: Dict[str, str] = Depends(require_viewer),
) -> Dict[str, Any]:
    rows = _ASSERTION_STORE.list_assertions(status=status_filter, limit=limit)
    return {"total": len(rows), "assertions": rows}


@router.get("/assertions/{assertion_id}/history")
async def assertion_history(
    assertion_id: str,
    limit: int = Query(50, ge=1, le=200),
    _auth: Dict[str, str] = Depends(require_approver),
) -> Dict[str, Any]:
    rows = _ASSERTION_STORE.list_assertion_history(assertion_id, limit=limit)
    return {"assertion_id": assertion_id, "total": len(rows), "history": rows}


@router.get("/sources/classification")
async def source_classification(
    profile: str = Query(RunProfile.PRIORITY.value),
    _auth: Dict[str, str] = Depends(require_viewer),
) -> Dict[str, Any]:
    selected = select_sources(ALL_URLS, profile=profile)
    return {
        "profile": profile,
        "summary": classification_summary(selected),
        "sources": [row.__dict__ for row in classify_all(selected)],
    }


@router.get("/sources/missing-priority")
async def missing_priority_sources(
    _auth: Dict[str, str] = Depends(require_viewer),
) -> Dict[str, Any]:
    return {"total": len(MISSING_PRIORITY_SOURCES), "sources": MISSING_PRIORITY_SOURCES}


@router.post("/assertions/{assertion_id}/approve")
async def approve_pending_assertion(
    assertion_id: str,
    body: PendingActionRequest,
    auth: Dict[str, str] = Depends(require_approver),
) -> Dict[str, Any]:
    files = {path.stem: path for path in _pending_files()}
    if assertion_id not in files:
        raise HTTPException(status_code=404, detail="Pending assertion not found")

    path = files[assertion_id]
    decisions = _ASSERTION_STORE.approve_pending_file(
        path,
        actor=auth.get("principal", "unknown"),
        reason=body.reason or "",
    )
    return {
        "status": "approved",
        "id": assertion_id,
        "reason": body.reason,
        "acted_by_role": auth.get("role"),
        "decisions": [
            {
                "assertion_id": row.assertion_id,
                "version": row.version,
                "status": row.status,
                "content_hash": row.content_hash,
                "chain_hash": row.chain_hash,
            }
            for row in decisions
        ],
    }


@router.post("/assertions/{assertion_id}/reject")
async def reject_pending_assertion(
    assertion_id: str,
    body: PendingActionRequest,
    auth: Dict[str, str] = Depends(require_approver),
) -> Dict[str, Any]:
    files = {path.stem: path for path in _pending_files()}
    if assertion_id not in files:
        raise HTTPException(status_code=404, detail="Pending assertion not found")

    path = files[assertion_id]
    result = _ASSERTION_STORE.reject_pending_file(
        path,
        assertion_id=assertion_id,
        actor=auth.get("principal", "unknown"),
        reason=body.reason or "",
    )
    decision = result["decision"]
    return {
        "status": "rejected",
        "id": assertion_id,
        "reason": body.reason,
        "acted_by_role": auth.get("role"),
        "file": result["file"],
        "decision": {
            "assertion_id": decision.assertion_id,
            "version": decision.version,
            "status": decision.status,
            "content_hash": decision.content_hash,
            "chain_hash": decision.chain_hash,
        },
    }
