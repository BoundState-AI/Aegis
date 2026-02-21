#!/usr/bin/env python3
"""Tests for monitor API route."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from boundstate_aegis.api.routes import monitor_route


def _app() -> TestClient:
    app = FastAPI()
    app.include_router(monitor_route.router, prefix="/api/v1/monitor")
    return TestClient(app)


def test_monitor_run_endpoint_queues_job(monkeypatch) -> None:
    monkeypatch.setenv("AEGIS_MONITOR_API_AUTH_ENABLED", "true")
    monkeypatch.setenv("AEGIS_MONITOR_API_KEYS", "viewer-token:viewer,operator-token:operator,approver-token:approver")
    monkeypatch.setenv("AEGIS_MONITOR_API_MANUAL_RUN_ENABLED", "true")

    # Reset run state for deterministic test behavior.
    monitor_route._RUN_STATE.clear()
    monitor_route._ACTIVE_RUN_ID = None

    def _fake_start(run_id: str) -> None:
        row = monitor_route._RUN_STATE[run_id]
        row["status"] = "completed"
        row["started_at"] = row["requested_at"]
        row["finished_at"] = row["requested_at"]
        row["summary"] = {"total": 1, "ok": 1, "changed": 0, "signals": 0}

    monkeypatch.setattr(monitor_route, "_start_monitor_run", _fake_start)

    client = _app()
    response = client.post(
        "/api/v1/monitor/run?dry_run=true",
        headers={"X-AEGIS-API-Key": "operator-token"},
    )
    assert response.status_code == 202
    data = response.json()
    assert data["status"] in {"queued", "completed"}

    run_id = data["run_id"]
    status_resp = client.get(
        f"/api/v1/monitor/runs/{run_id}",
        headers={"X-AEGIS-API-Key": "viewer-token"},
    )
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["run_id"] == run_id


def test_monitor_run_rejects_viewer_role(monkeypatch) -> None:
    monkeypatch.setenv("AEGIS_MONITOR_API_AUTH_ENABLED", "true")
    monkeypatch.setenv("AEGIS_MONITOR_API_KEYS", "viewer-token:viewer,operator-token:operator")
    monkeypatch.setenv("AEGIS_MONITOR_API_MANUAL_RUN_ENABLED", "true")

    client = _app()
    response = client.post(
        "/api/v1/monitor/run?dry_run=true",
        headers={"X-AEGIS-API-Key": "viewer-token"},
    )
    assert response.status_code == 403


def test_monitor_run_disabled_when_manual_flag_off(monkeypatch) -> None:
    monkeypatch.setenv("AEGIS_MONITOR_API_AUTH_ENABLED", "true")
    monkeypatch.setenv("AEGIS_MONITOR_API_KEYS", "operator-token:operator")
    monkeypatch.setenv("AEGIS_MONITOR_API_MANUAL_RUN_ENABLED", "false")

    client = _app()
    response = client.post(
        "/api/v1/monitor/run?dry_run=true",
        headers={"X-AEGIS-API-Key": "operator-token"},
    )
    assert response.status_code == 403


def test_monitor_signals_accepts_shorthand_single_key(monkeypatch) -> None:
    monkeypatch.setenv("AEGIS_MONITOR_API_AUTH_ENABLED", "true")
    monkeypatch.setenv("AEGIS_MONITOR_API_KEYS", "single-token")
    monkeypatch.delenv("AEGIS_MONITOR_API_KEY", raising=False)

    client = _app()
    response = client.get(
        "/api/v1/monitor/signals?limit=25",
        headers={"X-AEGIS-API-Key": "single-token"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "signals" in payload


def test_monitor_signals_accepts_legacy_single_key_env(monkeypatch) -> None:
    monkeypatch.setenv("AEGIS_MONITOR_API_AUTH_ENABLED", "true")
    monkeypatch.setenv("AEGIS_MONITOR_API_KEYS", "")
    monkeypatch.setenv("AEGIS_MONITOR_API_KEY", "legacy-token")
    monkeypatch.setenv("AEGIS_MONITOR_API_KEY_ROLE", "viewer")

    client = _app()
    response = client.get(
        "/api/v1/monitor/signals?limit=25",
        headers={"X-AEGIS-API-Key": "legacy-token"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "signals" in payload
