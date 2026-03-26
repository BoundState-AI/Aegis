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

    if surface.page_id == "litigation":
        visible_cases = visible_state.get("visible_similar_cases", [])
        matched = _match_named_items(message, visible_cases, "case")
        return {
            "summary": {
                "selected_compound": visible_state.get("selected_compound"),
                "chart_view": visible_state.get("chart_view"),
                "available_backtests": visible_state.get("available_backtests"),
                "forecast_risk_level": visible_state.get("forecast_risk_level"),
                "probability_12_months": visible_state.get("probability_12_months"),
                "probability_24_months": visible_state.get("probability_24_months"),
                "probability_36_months": visible_state.get("probability_36_months"),
                "estimated_exposure_usd": visible_state.get("estimated_exposure_usd"),
                "backtest_publications": visible_state.get("backtest_publications"),
                "first_lawsuit_year": visible_state.get("first_lawsuit_year"),
                "lead_time_years": visible_state.get("lead_time_years"),
                "paper_drilldown_year": visible_state.get("paper_drilldown_year"),
                "paper_drilldown_total": visible_state.get("paper_drilldown_total"),
            },
            "matched_items": matched,
            "key_drivers": visible_state.get("key_drivers", []),
            "visible_similar_cases": visible_cases,
            "citations": ["litigation_summary", "litigation_drivers", "litigation_cases"],
        }

    if surface.page_id == "portfolio":
        results = visible_state.get("top_results", [])
        matched = _match_named_items(message, results, "material")
        return {
            "summary": {
                "total_materials": visible_state.get("total_materials"),
                "high_risk_count": visible_state.get("high_risk_count"),
                "total_exposure_usd": visible_state.get("total_exposure_usd"),
            },
            "items": visible_state.get("items", []),
            "matched_items": matched,
            "top_results": results,
            "citations": ["portfolio_summary", "portfolio_items", "portfolio_results"],
        }

    if surface.page_id == "reports":
        sections = visible_state.get("visible_sections", [])
        matched = _match_named_items(message, sections, "title")
        return {
            "summary": {
                "material": visible_state.get("material"),
                "include_litigation": visible_state.get("include_litigation"),
                "include_regulatory": visible_state.get("include_regulatory"),
                "generated": visible_state.get("generated"),
                "classification": visible_state.get("classification"),
            },
            "matched_items": matched,
            "visible_sections": sections,
            "citations": ["report_summary", "report_sections"],
        }

    if surface.page_id == "evidence":
        evidence_rows = visible_state.get("visible_evidence", [])
        matched = _match_named_items(message, evidence_rows, "source")
        return {
            "summary": {
                "material": visible_state.get("material"),
                "max_citations": visible_state.get("max_citations"),
                "total_citations": visible_state.get("total_citations"),
                "confidence_score": visible_state.get("confidence_score"),
                "database_total_papers": visible_state.get("database_total_papers"),
                "total_pathway_citations": visible_state.get("total_pathway_citations"),
            },
            "matched_items": matched,
            "visible_evidence": evidence_rows,
            "citations": ["evidence_summary", "evidence_rows"],
        }

    if surface.page_id == "analysis":
        findings = visible_state.get("visible_findings", [])
        matched = _match_named_items(message, findings, "product")
        return {
            "summary": {
                "material": visible_state.get("material"),
                "temperature_c": visible_state.get("temperature_c"),
                "atmosphere": visible_state.get("atmosphere"),
                "time_hours": visible_state.get("time_hours"),
                "findings_count": visible_state.get("findings_count"),
                "summary": visible_state.get("summary"),
            },
            "matched_items": matched,
            "visible_findings": findings,
            "citations": ["analysis_summary", "analysis_findings"],
        }

    if surface.page_id == "tier1":
        endpoints = visible_state.get("top_endpoints", [])
        neighbors = visible_state.get("similar_compounds", [])
        matched = _match_named_items(message, neighbors, "name")
        matched_endpoints = _match_named_items(message, endpoints, "endpoint")
        return {
            "summary": {
                "compound_name": visible_state.get("compound_name"),
                "query_smiles": visible_state.get("query_smiles"),
                "risk_signal": visible_state.get("risk_signal"),
                "neighbors_with_pathways": visible_state.get("neighbors_with_pathways"),
                "avg_similarity": visible_state.get("avg_similarity"),
                "tier2_pattern_count": visible_state.get("tier2_pattern_count"),
                "tier2_rule_total": visible_state.get("tier2_rule_total"),
                "coverage_resolution_rate": visible_state.get("coverage_resolution_rate"),
            },
            "matched_items": matched or matched_endpoints,
            "similar_compounds": neighbors,
            "top_endpoints": endpoints,
            "citations": ["tier1_summary", "tier1_endpoints", "tier1_neighbors"],
        }

    return {"citations": []}
