#!/usr/bin/env python3
"""Tests for resolver HITL gates and API endpoints."""

from __future__ import annotations

import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from boundstate_aegis.api.routes import resolver_route
from boundstate_aegis.engines.hitl_gates import GateId, GateStatus, HITLGateStore


def _sample_result() -> dict:
    return {
        "query_compound": {"preferred_name": "HFO-1234yf", "cas": "754-12-1", "resolution_method": "product_manifest"},
        "direct_exposure": [],
        "class_exposure": [{"assertion_id": "EU_ECHA_PFAS_001", "severity": "HIGH"}],
        "degradation_tree": {
            "root": "HFO-1234yf",
            "nodes": [{"compound": {"preferred_name": "TFA"}, "cumulative_confidence": 0.4}],
            "total_nodes": 1,
            "max_depth_reached": 1,
            "truncated": False,
            "cycles_detected": [],
        },
        "inherited_exposure": [],
        "total_exposure": {
            "jurisdictions_affected": 1,
            "assertions_triggered": 1,
            "most_severe_id": "EU_ECHA_PFAS_001",
            "trajectory": "INCREASING",
        },
        "threat_flags": [{"flag_type": "DESTRUCTION_TECH_GAP", "severity": "CRITICAL", "detail": "No confirmed capability identified."}],
        "metadata": {
            "resolver_version": "1.0.0",
            "graph_version": "x",
            "assertion_version": "y",
            "manifest_version": "z",
            "resolved_at": "2026-01-01T00:00:00Z",
            "resolve_duration_ms": 10,
            "traversal_params": {"max_depth": 4, "max_nodes": 50, "max_branching": 10, "min_confidence": 0.3},
        },
    }


def test_gate_status_transition_flow(tmp_path) -> None:
    store = HITLGateStore(tmp_path / "resolver_hitl.db")
    created = store.create_resolution(_sample_result(), created_by="analyst-a")
    assert created["gate_status"] == GateStatus.PENDING_REVIEW.value

    reviewed = store.apply_gate_action(
        gate_id=GateId.HITL_1.value,
        resolution_id=created["resolution_id"],
        action="confirm",
        analyst_id="analyst-a",
    )
    assert reviewed["gate_status"] == GateStatus.PENDING_APPROVAL.value

    approved = store.apply_gate_action(
        gate_id=GateId.HITL_2.value,
        resolution_id=created["resolution_id"],
        action="approve",
        analyst_id="approver-a",
    )
    assert approved["gate_status"] == GateStatus.APPROVED.value


def test_override_captures_previous_and_new_values(tmp_path) -> None:
    store = HITLGateStore(tmp_path / "resolver_hitl.db")
    created = store.create_resolution(_sample_result(), created_by="analyst-a")
    prev_value = {"cumulative_confidence": 0.4}
    new_value = {"cumulative_confidence": 0.7}

    store.apply_gate_action(
        gate_id=GateId.HITL_1.value,
        resolution_id=created["resolution_id"],
        action="override",
        analyst_id="analyst-a",
        justification="Internal data supports higher confidence.",
        previous_value=prev_value,
        new_value=new_value,
    )
    history = store.list_gate_history(created["resolution_id"], limit=10)
    override_event = next(row for row in history if row["action"] == "override")
    assert override_event["previous_value"] == prev_value
    assert override_event["new_value"] == new_value


def test_dismiss_requires_justification(tmp_path) -> None:
    store = HITLGateStore(tmp_path / "resolver_hitl.db")
    created = store.create_resolution(_sample_result(), created_by="analyst-a")

    with pytest.raises(ValueError):
        store.apply_gate_action(
            gate_id=GateId.HITL_1.value,
            resolution_id=created["resolution_id"],
            action="dismiss",
            analyst_id="analyst-a",
            justification="",
        )


def test_gate_events_append_only(tmp_path) -> None:
    store = HITLGateStore(tmp_path / "resolver_hitl.db")
    store.create_resolution(_sample_result(), created_by="analyst-a")
    conn = sqlite3.connect(store.db_path)
    try:
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute("DELETE FROM resolver_gate_events")
            conn.commit()
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute("UPDATE resolver_gate_events SET action = 'tampered'")
            conn.commit()
    finally:
        conn.close()


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(resolver_route.router, prefix="/api/v1/resolver")
    return TestClient(app)


def test_gate_endpoints_require_auth(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AEGIS_MONITOR_API_AUTH_ENABLED", "true")
    monkeypatch.setenv("AEGIS_MONITOR_API_KEYS", "viewer-token:viewer,operator-token:operator,approver-token:approver")
    monkeypatch.setattr(resolver_route, "_HITL_STORE", HITLGateStore(tmp_path / "resolver_hitl.db"))
    monkeypatch.setattr(resolver_route, "resolve", lambda *args, **kwargs: _sample_result())

    client = _client()
    create_resp = client.post("/api/v1/resolver/resolve", json={"compound": "Opteon 1234yf"})
    assert create_resp.status_code == 401

    review_resp = client.post(
        "/api/v1/resolver/review",
        json={"resolution_id": "res_123", "action": "confirm"},
    )
    assert review_resp.status_code == 401

    pending_resp = client.get("/api/v1/resolver/pending")
    assert pending_resp.status_code == 401


def test_gate_endpoints_flow(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AEGIS_MONITOR_API_AUTH_ENABLED", "true")
    monkeypatch.setenv("AEGIS_MONITOR_API_KEYS", "viewer-token:viewer,operator-token:operator,approver-token:approver")
    monkeypatch.setattr(resolver_route, "_HITL_STORE", HITLGateStore(tmp_path / "resolver_hitl.db"))
    monkeypatch.setattr(resolver_route, "resolve", lambda *args, **kwargs: _sample_result())

    client = _client()
    create_resp = client.post(
        "/api/v1/resolver/resolve",
        json={"compound": "Opteon 1234yf"},
        headers={"X-AEGIS-API-Key": "operator-token"},
    )
    assert create_resp.status_code == 200
    resolution_id = create_resp.json()["resolution_id"]

    review_resp = client.post(
        "/api/v1/resolver/review",
        headers={"X-AEGIS-API-Key": "operator-token"},
        json={"resolution_id": resolution_id, "action": "confirm"},
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["gate_status"] == GateStatus.PENDING_APPROVAL.value

    approve_resp = client.post(
        "/api/v1/resolver/approve",
        headers={"X-AEGIS-API-Key": "approver-token"},
        json={"resolution_id": resolution_id, "action": "approve"},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["gate_status"] == GateStatus.APPROVED.value
