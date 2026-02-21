#!/usr/bin/env python3
"""
Alert formatting/routing for regulatory intelligence outputs.
"""

from __future__ import annotations

import json
import logging
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any, Dict, List

import requests

from boundstate_aegis.config import (
    MONITOR_ALERT_EMAIL_ENABLED,
    MONITOR_ALERT_EMAIL_FROM,
    MONITOR_ALERT_EMAIL_SMTP_HOST,
    MONITOR_ALERT_EMAIL_SMTP_PASSWORD,
    MONITOR_ALERT_EMAIL_SMTP_PORT,
    MONITOR_ALERT_EMAIL_SMTP_USER,
    MONITOR_ALERT_EMAIL_TO,
    MONITOR_ALERT_EMAIL_USE_TLS,
    MONITOR_PAGERDUTY_ROUTING_KEY,
)

from .models import RegulatorySignal

logger = logging.getLogger(__name__)


def route_for_impact(impact_rating: str) -> str:
    rating = (impact_rating or "").lower()
    if rating == "critical":
        return "critical"
    if rating == "high":
        return "high"
    if rating == "medium":
        return "weekly"
    if rating == "low":
        return "monthly"
    return "log_only"


def build_signal_slack_payload(signal: RegulatorySignal) -> Dict[str, Any]:
    impact = signal.impact or {}
    rating = (impact.get("impact_rating") or "none").upper()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    actions = impact.get("recommended_actions") or []
    action_text = "\n".join(f"{idx}. {item}" for idx, item in enumerate(actions[:4], start=1))
    if not action_text:
        action_text = "1. Review change in analyst queue."

    briefing = impact.get("briefing_summary") or signal.summary
    cascade = impact.get("cascade_risk") or "No cascade assessment available."
    provenance = signal.fetch_provenance or "direct"

    text = (
        f"🚨 AEGIS REGULATORY INTELLIGENCE — {rating}\n\n"
        f"📍 SOURCE: {signal.source_label} ({signal.country})\n"
        f"📅 DETECTED: {now}\n"
        f"⚡ SEVERITY: {signal.severity.upper()}\n\n"
        f"📋 WHAT CHANGED:\n{signal.summary}\n\n"
        f"🧾 PROVENANCE: {provenance}\n\n"
        f"🎯 CHEMOURS IMPACT: {rating}\n{briefing}\n\n"
        f"📌 RECOMMENDED ACTIONS:\n{action_text}\n\n"
        f"🔄 CASCADE: {cascade}"
    )

    return {
        "text": text,
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": text}},
        ],
    }


def build_weekly_digest(signals: List[Dict[str, Any]]) -> Dict[str, Any]:
    lines = ["*AEGIS Weekly Regulatory Digest*"]
    for idx, row in enumerate(signals[:12], start=1):
        sev = str(row.get("severity", "low")).upper()
        src = row.get("source_label", "Unknown source")
        summary = row.get("summary", "")
        lines.append(f"{idx}. [{sev}] {src} — {summary}")
    return {"text": "\n".join(lines)}


def _fallback_subject(signal: RegulatorySignal, reason: str) -> str:
    impact = (signal.impact or {}).get("impact_rating", "none")
    return (
        f"[AEGIS][{signal.severity.upper()}][{str(impact).upper()}] "
        f"Slack delivery failed for {signal.source_label} ({reason})"
    )


def _fallback_body(signal: RegulatorySignal, reason: str) -> str:
    return (
        f"Signal ID: {signal.signal_id}\n"
        f"Detected At: {signal.detected_at}\n"
        f"Source: {signal.source_label} ({signal.country})\n"
        f"URL: {signal.source_url}\n"
        f"Severity: {signal.severity}\n"
        f"Classification: {signal.classification}\n"
        f"Summary: {signal.summary}\n"
        f"Reason: {reason}\n"
        f"Impact: {json.dumps(signal.impact or {}, ensure_ascii=True)}\n"
    )


def _send_email_fallback(subject: str, body: str) -> bool:
    if not MONITOR_ALERT_EMAIL_ENABLED:
        return False
    recipients = [item.strip() for item in MONITOR_ALERT_EMAIL_TO.split(",") if item.strip()]
    if not (MONITOR_ALERT_EMAIL_SMTP_HOST and MONITOR_ALERT_EMAIL_FROM and recipients):
        logger.error("Email fallback enabled but SMTP host/from/to is not fully configured")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = MONITOR_ALERT_EMAIL_FROM
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    try:
        with smtplib.SMTP(MONITOR_ALERT_EMAIL_SMTP_HOST, MONITOR_ALERT_EMAIL_SMTP_PORT, timeout=20) as client:
            if MONITOR_ALERT_EMAIL_USE_TLS:
                client.starttls()
            if MONITOR_ALERT_EMAIL_SMTP_USER:
                client.login(MONITOR_ALERT_EMAIL_SMTP_USER, MONITOR_ALERT_EMAIL_SMTP_PASSWORD)
            client.send_message(msg)
        return True
    except Exception as exc:
        logger.error("Email fallback failed: %s", exc)
        return False


def _send_pagerduty_fallback(subject: str, body: str, signal: RegulatorySignal) -> bool:
    if not MONITOR_PAGERDUTY_ROUTING_KEY:
        return False
    severity = "critical" if signal.severity.lower() == "critical" else "error"
    payload = {
        "routing_key": MONITOR_PAGERDUTY_ROUTING_KEY,
        "event_action": "trigger",
        "dedup_key": f"aegis-monitor-{signal.signal_id}",
        "payload": {
            "summary": subject[:1024],
            "source": "aegis-monitor",
            "severity": severity,
            "custom_details": {
                "signal_id": signal.signal_id,
                "source_label": signal.source_label,
                "source_url": signal.source_url,
                "classification": signal.classification,
                "signal_severity": signal.severity,
                "impact": signal.impact or {},
                "reason": body[:4096],
            },
        },
    }
    try:
        resp = requests.post(
            "https://events.pagerduty.com/v2/enqueue",
            json=payload,
            timeout=15,
        )
        if 200 <= resp.status_code < 300:
            return True
        logger.error("PagerDuty fallback failed: status=%s body=%s", resp.status_code, resp.text[:300])
        return False
    except Exception as exc:
        logger.error("PagerDuty fallback request failed: %s", exc)
        return False


def dispatch_critical_fallback(signal: RegulatorySignal, reason: str) -> Dict[str, bool]:
    subject = _fallback_subject(signal, reason)
    body = _fallback_body(signal, reason)
    email_ok = _send_email_fallback(subject, body)
    pager_ok = _send_pagerduty_fallback(subject, body, signal)
    return {"email_sent": email_ok, "pagerduty_sent": pager_ok}
