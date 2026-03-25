#!/usr/bin/env python3
"""Tests for executive reports API route."""

from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from boundstate_aegis.api.routes import reports_route


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(reports_route.router, prefix="/api/v1/reports")
    return TestClient(app)


def test_executive_report_omits_none_section_fields(monkeypatch) -> None:
    monkeypatch.setattr(
        reports_route,
        "get_graph",
        lambda: SimpleNamespace(compounds={"PTFE": {}, "PFOA": {}}),
    )
    monkeypatch.setattr(
        reports_route,
        "_get_degradation_products",
        lambda graph, material: [
            {
                "product": "PFOA",
                "mechanism": "thermal_oxidation",
                "min_temp_c": 500.0,
                "max_temp_c": 600.0,
                "confidence": 0.9,
                "atmosphere": "air",
            }
        ],
    )
    monkeypatch.setattr(
        reports_route,
        "_get_regulatory_status",
        lambda material: {"flags": [], "is_regulated": False, "is_pfas": False},
    )
    monkeypatch.setattr(reports_route, "_get_evidence_count", lambda material: 3)
    monkeypatch.setattr(
        reports_route,
        "_determine_risk_level",
        lambda material, reg_status, products: "MEDIUM-HIGH",
    )

    client = _client()
    response = client.get(
        "/api/v1/reports/executive",
        params={
            "material": "PTFE",
            "include_litigation": "true",
            "include_regulatory": "true",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    sections = {section["title"]: section for section in payload["sections"]}

    assert "flags" not in sections["Executive Summary"]
    assert "similar_cases" not in sections["Executive Summary"]
    assert "data" not in sections["Regulatory Status"]
    assert "similar_cases" not in sections["Regulatory Status"]
    assert sections["Litigation Risk Assessment"]["similar_cases"] == [
        "Related: 3M PFAS Settlement ($10.3B, 2023)"
    ]
