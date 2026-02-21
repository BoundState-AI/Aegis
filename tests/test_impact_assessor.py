#!/usr/bin/env python3
"""Tests for Chemours impact assessor."""

from __future__ import annotations

from boundstate_aegis.monitoring.impact_assessor import ImpactAssessor
from boundstate_aegis.monitoring.models import RegulatorySignal


def test_impact_assessor_loads_profile_and_scores_signal() -> None:
    assessor = ImpactAssessor(api_key=None, strict_mode=False)
    signal = RegulatorySignal(
        signal_id="sig1",
        source_url="https://example.com",
        source_label="ECHA PFAS",
        country="EU",
        detected_at="2026-02-20T00:00:00+00:00",
        classification="timeline_change",
        severity="high",
        summary="SEAC opinion updated with fluoropolymer derogation text.",
        compounds_affected=["PTFE", "PFAS"],
        jurisdictions_affected=["EU"],
        action_type="derogation",
        effective_date=None,
        confidence=0.91,
        raw_signal="Added text describing 12-year transition and derogation conditions.",
        diff_id="d1",
        triage={},
    )
    impact = assessor.assess(signal)
    assert impact.impact_rating in {"critical", "high", "medium", "low", "none"}
    assert impact.business_units_affected
    assert "priority_score" in impact.score_components


def test_impact_assessor_strict_mode_requires_api_key() -> None:
    assessor = ImpactAssessor(api_key=None, strict_mode=True)
    signal = RegulatorySignal(
        signal_id="sig2",
        source_url="https://example.com",
        source_label="EPA PFAS",
        country="US",
        detected_at="2026-02-20T00:00:00+00:00",
        classification="guidance_update",
        severity="low",
        summary="Guidance page text changed.",
        compounds_affected=[],
        jurisdictions_affected=["US"],
        action_type="guidance",
        effective_date=None,
        confidence=0.8,
        raw_signal="Updated FAQ section.",
        diff_id="d2",
        triage={},
    )
    try:
        assessor.assess(signal)
        assert False, "Expected strict mode to raise without API key"
    except RuntimeError as exc:
        assert "strict mode" in str(exc).lower()
