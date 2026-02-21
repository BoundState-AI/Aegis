#!/usr/bin/env python3
"""Tests for APAC regulatory assertion loading and API endpoints."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from boundstate_aegis.api.routes import regulatory_v1_route as reg_v1


def test_apac_loader_count() -> None:
    assertions = reg_v1._load_apac_assertions()
    assert len(assertions) >= 24


def test_apac_flags_pfoa() -> None:
    summaries = reg_v1._get_apac_assertion_summaries("PFOA")
    assert summaries
    assert any(s.country == "Japan" for s in summaries)


def test_apac_flags_ptfe() -> None:
    summaries = reg_v1._get_apac_assertion_summaries("PTFE")
    assert summaries
    assert any(s.compound_class in {"fluoropolymer", "PFAS_and_fluoropolymer"} for s in summaries)


def test_confidence_cap_secondary_only() -> None:
    assertions = reg_v1._load_apac_assertions()
    capped_checked = 0

    for assertion in assertions:
        citations = assertion.get("citations", []) or []
        raw_confidence = float(assertion.get("confidence", 0.0) or 0.0)
        all_secondary = citations and all(c.get("tier", "secondary") == "secondary" for c in citations)
        if all_secondary and raw_confidence >= 0.90:
            adjusted = reg_v1._adjust_apac_confidence(assertion)
            assert adjusted <= 0.89
            capped_checked += 1

    assert capped_checked >= 1


def test_status_mapping_complete() -> None:
    assertions = reg_v1._load_apac_assertions()
    for assertion in assertions:
        status = (assertion.get("status") or "monitoring").lower()
        confidence = reg_v1._adjust_apac_confidence(assertion)
        normalized, raw = reg_v1._normalize_apac_status(assertion, confidence)

        if status == "finalized":
            assert normalized in {"advisory", "enforceable"}
        else:
            assert status in reg_v1.APAC_STATUS_MAP
            assert normalized in {"banned", "enforceable", "advisory", "monitored"}
        assert isinstance(raw, str)


def test_apac_endpoint() -> None:
    app = FastAPI()
    app.include_router(reg_v1.router, prefix="/api/v1/regulatory")
    client = TestClient(app)
    response = client.get("/api/v1/regulatory/apac")
    assert response.status_code == 200
    data = response.json()
    assert data["total_assertions"] >= 24


def test_apac_endpoint_strict_mode_filters_unverified() -> None:
    app = FastAPI()
    app.include_router(reg_v1.router, prefix="/api/v1/regulatory")
    client = TestClient(app)
    response = client.get("/api/v1/regulatory/apac?min_confidence=0")
    assert response.status_code == 200
    data = response.json()
    assert all(a["status"] != "unverified" for a in data["assertions"])


def test_apac_endpoint_relaxed_mode_can_include_unverified() -> None:
    app = FastAPI()
    app.include_router(reg_v1.router, prefix="/api/v1/regulatory")
    client = TestClient(app)
    response = client.get(
        "/api/v1/regulatory/apac?strict_mode=false&require_primary_citation=false&min_confidence=0"
    )
    assert response.status_code == 200
    data = response.json()
    assert any(a["status"] == "unverified" for a in data["assertions"])


def test_apac_quality_audit_endpoint() -> None:
    app = FastAPI()
    app.include_router(reg_v1.router, prefix="/api/v1/regulatory")
    client = TestClient(app)
    response = client.get("/api/v1/regulatory/apac/quality-audit")
    assert response.status_code == 200
    data = response.json()
    assert data["total_assertions"] >= 24
    assert data["strict_excluded_count"] >= 1
    assert "issues" in data


def test_apac_country_filter() -> None:
    app = FastAPI()
    app.include_router(reg_v1.router, prefix="/api/v1/regulatory")
    client = TestClient(app)
    response = client.get("/api/v1/regulatory/apac?country=JPN")
    assert response.status_code == 200
    data = response.json()
    assert data["filtered_assertions"] >= 1
    for assertion in data["assertions"]:
        assert assertion["country"] == "Japan"


def test_check_pfoa_includes_apac() -> None:
    app = FastAPI()
    app.include_router(reg_v1.router, prefix="/api/v1/regulatory")
    client = TestClient(app)
    response = client.get("/api/v1/regulatory/check?material=PFOA&include_degradation=false")
    assert response.status_code == 200

    data = response.json()
    assert "apac_assertions" in data
    assert len(data["apac_assertions"]) >= 1
    assert any(a["country"] == "Japan" for a in data["apac_assertions"])
    assert all(a["status"] != "unverified" for a in data["apac_assertions"])
