#!/usr/bin/env python3
"""
Minimal evidence selection for deterministic AEGIS chat.
"""

from __future__ import annotations

from typing import Any

from boundstate_aegis.models.chat_models import AuthoritativeAnswerSurface


def _match_named_items(message: str, items: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    lowered = message.lower()
    matches: list[dict[str, Any]] = []
    for item in items:
        label = str(item.get(key) or "").strip()
        if label and label.lower() in lowered:
            matches.append(item)
    return matches


def select_evidence(
    message: str,
    surface: AuthoritativeAnswerSurface,
    question_type: str,
) -> dict[str, Any]:
    visible_state = surface.visible_state
    if surface.page_id == "fate-explorer":
        transformations = visible_state.get("visible_transformations", [])
        matched = _match_named_items(message, transformations, "product")
        return {
            "filters": {
                "parent": visible_state.get("parent"),
                "temp_min": visible_state.get("temp_min"),
                "temp_max": visible_state.get("temp_max"),
                "atmosphere": visible_state.get("atmosphere"),
                "min_observations": visible_state.get("min_observations"),
            },
            "matched_items": matched,
            "visible_transformations": transformations,
            "total_transformations": visible_state.get("total_transformations", 0),
            "citations": ["visible_transformations", "active_filters"],
        }

    if surface.page_id == "regulatory":
        findings = visible_state.get("sample_findings", [])
        matched = _match_named_items(message, findings, "framework")
        return {
            "summary": {
                "material": visible_state.get("material"),
                "include_degradation": visible_state.get("include_degradation"),
                "forecast_year": visible_state.get("forecast_year"),
                "active_subview": visible_state.get("active_subview"),
                "overall_risk": visible_state.get("overall_risk"),
                "frameworks_checked": visible_state.get("frameworks_checked"),
                "compliant_count": visible_state.get("compliant_count"),
                "warning_count": visible_state.get("warning_count"),
                "non_compliant_count": visible_state.get("non_compliant_count"),
            },
            "matched_items": matched,
            "sample_findings": findings,
            "cascade_predictions": visible_state.get("cascade_predictions", {}),
            "citations": ["regulatory_summary", "sample_findings", "cascade_predictions"],
        }

    return {"citations": []}
