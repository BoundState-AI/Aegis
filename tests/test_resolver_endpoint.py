#!/usr/bin/env python3
"""Tests for resolver API route."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from boundstate_aegis.api.routes import resolver_route
from boundstate_aegis.engines.hitl_gates import HITLGateStore


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(resolver_route.router, prefix="/api/v1/resolver")
    return TestClient(app)


def test_resolve_endpoint(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AEGIS_MONITOR_API_AUTH_ENABLED", "false")
    monkeypatch.setattr(resolver_route, "_HITL_STORE", HITLGateStore(tmp_path / "resolver_hitl.db"))

    def _fake_resolve(*args, **kwargs):
        return {
            "query_compound": {"preferred_name": "HFO-1234yf", "cas": "754-12-1", "resolution_method": "product_manifest"},
            "direct_exposure": [],
            "class_exposure": [],
            "degradation_tree": {"root": "HFO-1234yf", "nodes": [], "total_nodes": 1, "max_depth_reached": 0, "truncated": False, "cycles_detected": []},
            "inherited_exposure": [],
            "total_exposure": {"jurisdictions_affected": 0, "assertions_triggered": 0, "most_severe_id": "", "trajectory": "STABLE"},
            "threat_flags": [],
            "metadata": {"resolver_version": "1.0.0", "graph_version": "x", "assertion_version": "y", "manifest_version": "1.0.0", "resolved_at": "2026-01-01T00:00:00Z", "resolve_duration_ms": 1, "traversal_params": {"max_depth": 4, "max_nodes": 50, "max_branching": 10, "min_confidence": 0.3}},
        }

    monkeypatch.setattr(resolver_route, "resolve", _fake_resolve)

    client = _client()
    response = client.post("/api/v1/resolver/resolve", json={"compound": "Opteon 1234yf"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["resolution_id"]
    assert payload["gate_status"] == "PENDING_REVIEW"
    assert payload["result"]["query_compound"]["cas"] == "754-12-1"


def test_products_endpoint(monkeypatch) -> None:
    monkeypatch.setenv("AEGIS_MONITOR_API_AUTH_ENABLED", "false")
    client = _client()
    response = client.get("/api/v1/resolver/products")
    assert response.status_code == 200
    payload = response.json()
    assert payload["version"]
    assert payload["products"]
