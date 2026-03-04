#!/usr/bin/env python3
"""
Lightweight access request endpoints for frontend login approval flow.
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import smtplib
import threading
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, Literal, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr

from boundstate_aegis.config import (
    MONITOR_ALERT_EMAIL_FROM,
    MONITOR_ALERT_EMAIL_SMTP_HOST,
    MONITOR_ALERT_EMAIL_SMTP_PASSWORD,
    MONITOR_ALERT_EMAIL_SMTP_PORT,
    MONITOR_ALERT_EMAIL_SMTP_USER,
    MONITOR_ALERT_EMAIL_TO,
    MONITOR_ALERT_EMAIL_USE_TLS,
    MONITOR_DATA_DIR,
)

router = APIRouter()
logger = logging.getLogger(__name__)

_STORE_LOCK = threading.Lock()
_DEFAULT_NOTIFY_EMAIL = "joe@boundstate.ai"


class AccessRequestCreateRequest(BaseModel):
    email: EmailStr


class AccessRequestCreateResponse(BaseModel):
    request_id: str
    status: Literal["pending", "approved", "rejected"]
    email_sent: bool
    message: Optional[str] = None


class AccessRequestStatusResponse(BaseModel):
    request_id: str
    status: Literal["pending", "approved", "rejected"]
    created_at: str
    decided_at: Optional[str] = None


class AccessDecisionResponse(BaseModel):
    request_id: str
    status: Literal["pending", "approved", "rejected"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _truthy(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _store_path() -> Path:
    configured = os.getenv("AEGIS_ACCESS_REQUEST_STORE_PATH", "").strip()
    if configured:
        return Path(configured)
    return MONITOR_DATA_DIR / "access_requests.json"


def _load_rows() -> Dict[str, Dict[str, Any]]:
    path = _store_path()
    if not path.exists():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        logger.warning("Failed to parse access request store at %s: %s", path, exc)
        return {}

    if not isinstance(payload, dict):
        return {}

    rows = payload.get("rows")
    if not isinstance(rows, dict):
        return {}

    cleaned: Dict[str, Dict[str, Any]] = {}
    for request_id, row in rows.items():
        if not isinstance(request_id, str) or not isinstance(row, dict):
            continue
        cleaned[request_id] = row
    return cleaned


def _save_rows(rows: Dict[str, Dict[str, Any]]) -> None:
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {"rows": rows, "updated_at": _now_iso()}
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temp_path.replace(path)


def _normalized_email(value: str) -> str:
    return value.strip().lower()


def _find_latest_for_email(rows: Dict[str, Dict[str, Any]], email: str) -> Optional[Dict[str, Any]]:
    matching = [row for row in rows.values() if str(row.get("email", "")).lower() == email]
    if not matching:
        return None
    matching.sort(key=lambda row: str(row.get("created_at", "")), reverse=True)
    return matching[0]


def _send_access_email(row: Dict[str, Any]) -> bool:
    enabled = _truthy(os.getenv("AEGIS_ACCESS_EMAIL_ENABLED"), default=True)
    if not enabled:
        return False

    recipients_raw = (
        os.getenv("AEGIS_ACCESS_NOTIFY_EMAIL_TO", "").strip()
        or MONITOR_ALERT_EMAIL_TO
        or _DEFAULT_NOTIFY_EMAIL
    )
    recipients = [item.strip() for item in recipients_raw.split(",") if item.strip()]

    smtp_host = os.getenv("AEGIS_ACCESS_SMTP_HOST", "").strip() or MONITOR_ALERT_EMAIL_SMTP_HOST
    smtp_port = int(os.getenv("AEGIS_ACCESS_SMTP_PORT", str(MONITOR_ALERT_EMAIL_SMTP_PORT)))
    smtp_user = os.getenv("AEGIS_ACCESS_SMTP_USER", "").strip() or MONITOR_ALERT_EMAIL_SMTP_USER
    smtp_password = os.getenv("AEGIS_ACCESS_SMTP_PASSWORD", "") or MONITOR_ALERT_EMAIL_SMTP_PASSWORD
    smtp_use_tls = _truthy(os.getenv("AEGIS_ACCESS_SMTP_USE_TLS"), default=MONITOR_ALERT_EMAIL_USE_TLS)
    sender = os.getenv("AEGIS_ACCESS_EMAIL_FROM", "").strip() or MONITOR_ALERT_EMAIL_FROM

    if not (smtp_host and sender and recipients):
        logger.warning("Access request email not sent: SMTP host/from/to not fully configured")
        return False

    decision_base = os.getenv("AEGIS_ACCESS_APPROVAL_BASE_URL", "").strip().rstrip("/")
    token = str(row.get("approval_token", ""))

    approve_url = ""
    reject_url = ""
    if decision_base and token:
        approve_url = f"{decision_base}/api/v1/auth/access/decision?token={token}&decision=approve"
        reject_url = f"{decision_base}/api/v1/auth/access/decision?token={token}&decision=reject"

    email = row.get("email", "unknown")
    request_id = row.get("request_id", "unknown")

    body_lines = [
        "AEGIS access request received.",
        "",
        f"Email: {email}",
        f"Request ID: {request_id}",
        f"Created At (UTC): {row.get('created_at')}",
        "",
    ]

    if approve_url and reject_url:
        body_lines.extend([
            "Approve:",
            approve_url.replace("/api/v1/auth/access/decision?", "/api/v1/auth/access/decision/view?"),
            "",
            "Reject:",
            reject_url.replace("/api/v1/auth/access/decision?", "/api/v1/auth/access/decision/view?"),
            "",
        ])
    else:
        body_lines.extend([
            "Set AEGIS_ACCESS_APPROVAL_BASE_URL to include one-click approve/reject links in this email.",
            f"Approval token: {token}",
            "",
        ])

    msg = EmailMessage()
    msg["Subject"] = f"[AEGIS] Access request from {email}"
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content("\n".join(body_lines))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as client:
            if smtp_use_tls:
                client.starttls()
            if smtp_user:
                client.login(smtp_user, smtp_password)
            client.send_message(msg)
        return True
    except Exception as exc:  # pragma: no cover - depends on runtime SMTP
        logger.error("Failed sending access request email: %s", exc)
        return False


@router.post("/access-request", response_model=AccessRequestCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_access_request(payload: AccessRequestCreateRequest) -> AccessRequestCreateResponse:
    email = _normalized_email(str(payload.email))
    row_for_email: Optional[Dict[str, Any]] = None

    with _STORE_LOCK:
        rows = _load_rows()
        existing = _find_latest_for_email(rows, email)

        if existing and str(existing.get("status", "")).lower() in {"pending", "approved"}:
            request_id = str(existing.get("request_id"))
            response_status = str(existing.get("status", "pending")).lower()
            email_sent = False
            message = "Existing request found"
        else:
            request_id = uuid4().hex
            row = {
                "request_id": request_id,
                "email": email,
                "status": "pending",
                "created_at": _now_iso(),
                "decided_at": None,
                "decided_by": None,
                "approval_token": secrets.token_urlsafe(24),
            }
            rows[request_id] = row
            _save_rows(rows)
            response_status = "pending"
            row_for_email = dict(row)
            email_sent = False
            message = "Access request submitted"

    if row_for_email is not None:
        email_sent = _send_access_email(row_for_email)

    return AccessRequestCreateResponse(
        request_id=request_id,
        status=response_status,  # type: ignore[arg-type]
        email_sent=email_sent,
        message=message,
    )


@router.get("/access-request/{request_id}", response_model=AccessRequestStatusResponse)
async def get_access_request_status(request_id: str) -> AccessRequestStatusResponse:
    with _STORE_LOCK:
        rows = _load_rows()
        row = rows.get(request_id)

    if not row:
        raise HTTPException(status_code=404, detail="Access request not found")

    status_value = str(row.get("status", "pending")).lower()
    if status_value not in {"pending", "approved", "rejected"}:
        status_value = "pending"

    return AccessRequestStatusResponse(
        request_id=request_id,
        status=status_value,  # type: ignore[arg-type]
        created_at=str(row.get("created_at", "")),
        decided_at=row.get("decided_at"),
    )


@router.get("/access/decision", response_model=AccessDecisionResponse)
async def decide_access_request(
    token: str = Query(..., min_length=12),
    decision: Literal["approve", "reject"] = Query(...),
    actor: str = Query("email-link"),
) -> AccessDecisionResponse:
    with _STORE_LOCK:
        rows = _load_rows()
        matched_row: Optional[Dict[str, Any]] = None
        matched_request_id: Optional[str] = None

        for request_id, row in rows.items():
            if str(row.get("approval_token", "")) == token:
                matched_row = row
                matched_request_id = request_id
                break

        if not matched_row or not matched_request_id:
            raise HTTPException(status_code=404, detail="Invalid access decision token")

        current_status = str(matched_row.get("status", "pending")).lower()
        if current_status != "pending":
            return AccessDecisionResponse(
                request_id=matched_request_id,
                status=current_status,  # type: ignore[arg-type]
            )

        next_status = "approved" if decision == "approve" else "rejected"
        matched_row["status"] = next_status
        matched_row["decided_at"] = _now_iso()
        matched_row["decided_by"] = (actor or "email-link")[:120]
        rows[matched_request_id] = matched_row
        _save_rows(rows)

    return AccessDecisionResponse(request_id=matched_request_id, status=next_status)


@router.get("/access/decision/view")
async def decide_access_request_view(
    token: str = Query(..., min_length=12),
    decision: Literal["approve", "reject"] = Query(...),
    actor: str = Query("email-link"),
) -> HTMLResponse:
    result = await decide_access_request(token=token, decision=decision, actor=actor)
    color = "#166534" if result.status == "approved" else "#991b1b"
    html = (
        "<html><body style='font-family:system-ui;padding:24px;'>"
        f"<h2 style='color:{color};margin:0 0 12px 0;'>Access request {result.status}</h2>"
        f"<p>Request ID: <strong>{result.request_id}</strong></p>"
        "<p>You can close this window.</p>"
        "</body></html>"
    )
    return HTMLResponse(content=html)
