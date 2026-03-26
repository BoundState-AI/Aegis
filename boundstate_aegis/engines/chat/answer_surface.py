#!/usr/bin/env python3
"""
Surface verification and normalization for bounded AEGIS chat.
"""

from __future__ import annotations

import logging
from typing import Any

from boundstate_aegis.engines.chat.policies import get_page_policy
from boundstate_aegis.models.chat_models import (
    AnswerSurfaceHint,
    AuthoritativeAnswerSurface,
    ClarificationField,
    EvidenceBundle,
    EvidenceSource,
    SurfaceDiscrepancy,
)

LOGGER = logging.getLogger(__name__)


def _sanitize_fate_visible_state(raw: dict[str, Any]) -> dict[str, Any]:
    visible_transformations = raw.get("visible_transformations") or []
    cleaned_transformations: list[dict[str, Any]] = []
    for row in visible_transformations[:12]:
        if not isinstance(row, dict):
            continue
        cleaned_transformations.append({
            "product": str(row.get("product") or "").strip(),
            "hazard_level": str(row.get("hazard_level") or "").strip() or None,
            "confidence": float(row.get("confidence") or 0),
            "source_count": int(row.get("source_count") or 0),
            "is_regulated": bool(row.get("is_regulated") or False),
            "temp_range": str(row.get("temp_range") or "").strip(),
            "atmosphere": str(row.get("atmosphere") or "").strip(),
        })
    return {
        "parent": str(raw.get("parent") or "").strip().upper(),
        "temp_min": int(raw.get("temp_min") or 0),
        "temp_max": int(raw.get("temp_max") or 0),
        "atmosphere": str(raw.get("atmosphere") or "any").strip(),
        "min_observations": int(raw.get("min_observations") or 1),
        "total_transformations": int(raw.get("total_transformations") or 0),
        "visible_transformations": cleaned_transformations,
    }


def _sanitize_regulatory_visible_state(raw: dict[str, Any]) -> dict[str, Any]:
    sample_findings = raw.get("sample_findings") or []
    cleaned_findings: list[dict[str, Any]] = []
    for row in sample_findings[:10]:
        if not isinstance(row, dict):
            continue
        cleaned_findings.append({
            "framework": str(row.get("framework") or "").strip(),
            "status": str(row.get("status") or "").strip(),
            "notes": str(row.get("notes") or "").strip(),
        })

    cascade_predictions = raw.get("cascade_predictions") or {}
    cleaned_predictions: dict[str, dict[str, Any]] = {}
    if isinstance(cascade_predictions, dict):
        for key, value in list(cascade_predictions.items())[:10]:
            if not isinstance(value, dict):
                continue
            cleaned_predictions[str(key)] = {
                "status": str(value.get("status") or "").strip(),
                "regulatory_stage": str(value.get("regulatory_stage") or "").strip(),
                "affected_products": [
                    str(item).strip() for item in (value.get("affected_products") or [])[:8] if str(item).strip()
                ],
            }

    return {
        "material": str(raw.get("material") or "").strip().upper(),
        "include_degradation": bool(raw.get("include_degradation") or False),
        "forecast_year": int(raw.get("forecast_year") or 0),
        "active_subview": str(raw.get("active_subview") or "landscape").strip(),
        "overall_risk": str(raw.get("overall_risk") or "").strip(),
        "frameworks_checked": int(raw.get("frameworks_checked") or 0),
        "compliant_count": int(raw.get("compliant_count") or 0),
        "warning_count": int(raw.get("warning_count") or 0),
        "non_compliant_count": int(raw.get("non_compliant_count") or 0),
        "sample_findings": cleaned_findings,
        "cascade_predictions": cleaned_predictions,
    }


def _sanitize_litigation_visible_state(raw: dict[str, Any]) -> dict[str, Any]:
    cleaned_cases: list[dict[str, Any]] = []
    for row in (raw.get("visible_similar_cases") or [])[:8]:
        if not isinstance(row, dict):
            continue
        cleaned_cases.append({
            "case": str(row.get("case") or "").strip(),
            "year": int(row.get("year") or 0),
            "settlement": float(row.get("settlement") or 0),
            "relevance": float(row.get("relevance") or 0),
        })

    return {
        "selected_compound": str(raw.get("selected_compound") or "").strip().upper(),
        "chart_view": str(raw.get("chart_view") or "publications").strip(),
        "available_backtests": int(raw.get("available_backtests") or 0),
        "forecast_risk_level": str(raw.get("forecast_risk_level") or "").strip(),
        "probability_12_months": float(raw.get("probability_12_months") or 0),
        "probability_24_months": float(raw.get("probability_24_months") or 0),
        "probability_36_months": float(raw.get("probability_36_months") or 0),
        "estimated_exposure_usd": float(raw.get("estimated_exposure_usd") or 0),
        "key_drivers": [str(item).strip() for item in (raw.get("key_drivers") or [])[:8] if str(item).strip()],
        "visible_similar_cases": cleaned_cases,
        "backtest_publications": int(raw.get("backtest_publications") or 0),
        "first_lawsuit_year": int(raw.get("first_lawsuit_year") or 0),
        "lead_time_years": int(raw.get("lead_time_years") or 0),
        "paper_drilldown_year": int(raw.get("paper_drilldown_year") or 0),
        "paper_drilldown_total": int(raw.get("paper_drilldown_total") or 0),
    }


def _sanitize_portfolio_visible_state(raw: dict[str, Any]) -> dict[str, Any]:
    cleaned_items: list[dict[str, Any]] = []
    for row in (raw.get("items") or [])[:12]:
        if not isinstance(row, dict):
            continue
        cleaned_items.append({
            "material": str(row.get("material") or "").strip().upper(),
            "volume_lbs": int(row.get("volume_lbs") or 0),
        })

    cleaned_results: list[dict[str, Any]] = []
    for row in (raw.get("top_results") or [])[:12]:
        if not isinstance(row, dict):
            continue
        cleaned_results.append({
            "material": str(row.get("material") or "").strip().upper(),
            "risk_category": str(row.get("risk_category") or "").strip(),
            "risk_score": float(row.get("risk_score") or 0),
            "pfas_count": int(row.get("pfas_count") or 0),
            "regulatory_flags": int(row.get("regulatory_flags") or 0),
            "litigation_probability": float(row.get("litigation_probability") or 0),
        })

    return {
        "items": cleaned_items,
        "total_materials": int(raw.get("total_materials") or 0),
        "high_risk_count": int(raw.get("high_risk_count") or 0),
        "total_exposure_usd": float(raw.get("total_exposure_usd") or 0),
        "top_results": cleaned_results,
    }


def _sanitize_reports_visible_state(raw: dict[str, Any]) -> dict[str, Any]:
    cleaned_sections: list[dict[str, Any]] = []
    for row in (raw.get("visible_sections") or [])[:12]:
        if not isinstance(row, dict):
            continue
        cleaned_sections.append({
            "title": str(row.get("title") or "").strip(),
            "flags_count": int(row.get("flags_count") or 0),
            "similar_cases_count": int(row.get("similar_cases_count") or 0),
            "product_count": int(row.get("product_count") or 0),
        })

    return {
        "material": str(raw.get("material") or "").strip().upper(),
        "include_litigation": bool(raw.get("include_litigation") or False),
        "include_regulatory": bool(raw.get("include_regulatory") or False),
        "generated": str(raw.get("generated") or "").strip(),
        "classification": str(raw.get("classification") or "").strip(),
        "visible_sections": cleaned_sections,
    }


def _sanitize_evidence_visible_state(raw: dict[str, Any]) -> dict[str, Any]:
    cleaned_evidence: list[dict[str, Any]] = []
    for row in (raw.get("visible_evidence") or [])[:12]:
        if not isinstance(row, dict):
            continue
        cleaned_evidence.append({
            "source": str(row.get("source") or "").strip(),
            "year": int(row.get("year") or 0) if row.get("year") is not None else None,
            "confidence": float(row.get("confidence") or 0),
            "compound": str(row.get("compound") or "").strip().upper(),
        })

    return {
        "material": str(raw.get("material") or "").strip().upper(),
        "max_citations": int(raw.get("max_citations") or 0),
        "total_citations": int(raw.get("total_citations") or 0),
        "confidence_score": float(raw.get("confidence_score") or 0),
        "database_total_papers": int(raw.get("database_total_papers") or 0),
        "total_pathway_citations": int(raw.get("total_pathway_citations") or 0),
        "visible_evidence": cleaned_evidence,
    }


def _sanitize_analysis_visible_state(raw: dict[str, Any]) -> dict[str, Any]:
    cleaned_findings: list[dict[str, Any]] = []
    for row in (raw.get("visible_findings") or [])[:12]:
        if not isinstance(row, dict):
            continue
        evidence_strength = row.get("evidence_strength")
        cleaned_findings.append({
            "product": str(row.get("product") or "").strip(),
            "screening_classification": str(row.get("screening_classification") or "").strip(),
            "regulatory_flags_count": int(row.get("regulatory_flags_count") or 0),
            "evidence_strength": float(evidence_strength) if evidence_strength is not None else None,
        })

    return {
        "material": str(raw.get("material") or "").strip().upper(),
        "temperature_c": int(raw.get("temperature_c") or 0),
        "atmosphere": str(raw.get("atmosphere") or "").strip(),
        "time_hours": float(raw.get("time_hours") or 0),
        "findings_count": int(raw.get("findings_count") or 0),
        "summary": str(raw.get("summary") or "").strip(),
        "visible_findings": cleaned_findings,
    }


def _sanitize_tier1_visible_state(raw: dict[str, Any]) -> dict[str, Any]:
    cleaned_endpoints: list[dict[str, Any]] = []
    for row in (raw.get("top_endpoints") or [])[:8]:
        if not isinstance(row, dict):
            continue
        cleaned_endpoints.append({
            "endpoint": str(row.get("endpoint") or "").strip(),
            "count": int(row.get("count") or 0),
            "fraction": float(row.get("fraction") or 0),
        })

    cleaned_neighbors: list[dict[str, Any]] = []
    for row in (raw.get("similar_compounds") or [])[:10]:
        if not isinstance(row, dict):
            continue
        cleaned_neighbors.append({
            "name": str(row.get("name") or "").strip(),
            "similarity": float(row.get("similarity") or 0),
            "evidence_count": int(row.get("evidence_count") or 0),
        })

    return {
        "compound_name": str(raw.get("compound_name") or "").strip(),
        "query_smiles": str(raw.get("query_smiles") or "").strip(),
        "risk_signal": str(raw.get("risk_signal") or "").strip(),
        "neighbors_with_pathways": int(raw.get("neighbors_with_pathways") or 0),
        "avg_similarity": float(raw.get("avg_similarity") or 0),
        "top_endpoints": cleaned_endpoints,
        "similar_compounds": cleaned_neighbors,
        "tier2_pattern_count": int(raw.get("tier2_pattern_count") or 0),
        "tier2_rule_total": int(raw.get("tier2_rule_total") or 0),
        "coverage_resolution_rate": float(raw.get("coverage_resolution_rate") or 0),
    }


def _sanitize_visible_state(page_id: str, raw: dict[str, Any]) -> dict[str, Any]:
    if page_id == "fate-explorer":
        return _sanitize_fate_visible_state(raw)
    if page_id == "regulatory":
        return _sanitize_regulatory_visible_state(raw)
    if page_id == "litigation":
        return _sanitize_litigation_visible_state(raw)
    if page_id == "portfolio":
        return _sanitize_portfolio_visible_state(raw)
    if page_id == "reports":
        return _sanitize_reports_visible_state(raw)
    if page_id == "evidence":
        return _sanitize_evidence_visible_state(raw)
    if page_id == "analysis":
        return _sanitize_analysis_visible_state(raw)
    if page_id == "tier1":
        return _sanitize_tier1_visible_state(raw)
    return {}


def _build_evidence_bundle(page_id: str, visible_state: dict[str, Any]) -> EvidenceBundle:
    if page_id == "fate-explorer":
        return EvidenceBundle(
            sources=[
                EvidenceSource(
                    source_id="active_filters",
                    label="Active Fate Explorer filters",
                    claim_types=["filters", "query_context"],
                    payload={
                        "parent": visible_state.get("parent"),
                        "temp_min": visible_state.get("temp_min"),
                        "temp_max": visible_state.get("temp_max"),
                        "atmosphere": visible_state.get("atmosphere"),
                        "min_observations": visible_state.get("min_observations"),
                    },
                ),
                EvidenceSource(
                    source_id="visible_transformations",
                    label="Visible Fate Explorer transformations",
                    claim_types=["pathways", "hazards", "regulatory_flags"],
                    payload=visible_state.get("visible_transformations", []),
                ),
            ],
        )
    if page_id == "regulatory":
        return EvidenceBundle(
            sources=[
                EvidenceSource(
                    source_id="regulatory_summary",
                    label="Visible regulatory summary",
                    claim_types=["risk_summary", "counts", "filters"],
                    payload={
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
                ),
                EvidenceSource(
                    source_id="sample_findings",
                    label="Visible framework findings",
                    claim_types=["framework_status"],
                    payload=visible_state.get("sample_findings", []),
                ),
                EvidenceSource(
                    source_id="cascade_predictions",
                    label="Visible cascade predictions",
                    claim_types=["forecast"],
                    payload=visible_state.get("cascade_predictions", {}),
                ),
            ],
        )
    if page_id == "litigation":
        return EvidenceBundle(
            sources=[
                EvidenceSource(
                    source_id="litigation_summary",
                    label="Visible litigation summary",
                    claim_types=["forecast", "backtest", "filters"],
                    payload={
                        "selected_compound": visible_state.get("selected_compound"),
                        "chart_view": visible_state.get("chart_view"),
                        "forecast_risk_level": visible_state.get("forecast_risk_level"),
                        "probability_12_months": visible_state.get("probability_12_months"),
                        "probability_24_months": visible_state.get("probability_24_months"),
                        "probability_36_months": visible_state.get("probability_36_months"),
                        "estimated_exposure_usd": visible_state.get("estimated_exposure_usd"),
                        "backtest_publications": visible_state.get("backtest_publications"),
                        "lead_time_years": visible_state.get("lead_time_years"),
                    },
                ),
                EvidenceSource(
                    source_id="litigation_drivers",
                    label="Visible litigation drivers",
                    claim_types=["drivers"],
                    payload=visible_state.get("key_drivers", []),
                ),
                EvidenceSource(
                    source_id="litigation_cases",
                    label="Visible similar cases",
                    claim_types=["cases"],
                    payload=visible_state.get("visible_similar_cases", []),
                ),
            ],
        )
    if page_id == "portfolio":
        return EvidenceBundle(
            sources=[
                EvidenceSource(
                    source_id="portfolio_summary",
                    label="Visible portfolio summary",
                    claim_types=["summary", "exposure"],
                    payload={
                        "total_materials": visible_state.get("total_materials"),
                        "high_risk_count": visible_state.get("high_risk_count"),
                        "total_exposure_usd": visible_state.get("total_exposure_usd"),
                    },
                ),
                EvidenceSource(
                    source_id="portfolio_items",
                    label="Visible portfolio items",
                    claim_types=["materials", "volumes"],
                    payload=visible_state.get("items", []),
                ),
                EvidenceSource(
                    source_id="portfolio_results",
                    label="Visible portfolio results",
                    claim_types=["risk_rows"],
                    payload=visible_state.get("top_results", []),
                ),
            ],
        )
    if page_id == "reports":
        return EvidenceBundle(
            sources=[
                EvidenceSource(
                    source_id="report_summary",
                    label="Visible report summary",
                    claim_types=["summary", "toggles"],
                    payload={
                        "material": visible_state.get("material"),
                        "include_litigation": visible_state.get("include_litigation"),
                        "include_regulatory": visible_state.get("include_regulatory"),
                        "generated": visible_state.get("generated"),
                        "classification": visible_state.get("classification"),
                    },
                ),
                EvidenceSource(
                    source_id="report_sections",
                    label="Visible report sections",
                    claim_types=["sections"],
                    payload=visible_state.get("visible_sections", []),
                ),
            ],
        )
    if page_id == "evidence":
        return EvidenceBundle(
            sources=[
                EvidenceSource(
                    source_id="evidence_summary",
                    label="Visible evidence summary",
                    claim_types=["summary", "filters"],
                    payload={
                        "material": visible_state.get("material"),
                        "max_citations": visible_state.get("max_citations"),
                        "total_citations": visible_state.get("total_citations"),
                        "confidence_score": visible_state.get("confidence_score"),
                        "database_total_papers": visible_state.get("database_total_papers"),
                        "total_pathway_citations": visible_state.get("total_pathway_citations"),
                    },
                ),
                EvidenceSource(
                    source_id="evidence_rows",
                    label="Visible evidence rows",
                    claim_types=["citations", "findings"],
                    payload=visible_state.get("visible_evidence", []),
                ),
            ],
        )
    if page_id == "analysis":
        return EvidenceBundle(
            sources=[
                EvidenceSource(
                    source_id="analysis_summary",
                    label="Visible analysis summary",
                    claim_types=["summary", "filters"],
                    payload={
                        "material": visible_state.get("material"),
                        "temperature_c": visible_state.get("temperature_c"),
                        "atmosphere": visible_state.get("atmosphere"),
                        "time_hours": visible_state.get("time_hours"),
                        "findings_count": visible_state.get("findings_count"),
                        "summary": visible_state.get("summary"),
                    },
                ),
                EvidenceSource(
                    source_id="analysis_findings",
                    label="Visible analysis findings",
                    claim_types=["products", "classifications"],
                    payload=visible_state.get("visible_findings", []),
                ),
            ],
        )
    if page_id == "tier1":
        return EvidenceBundle(
            sources=[
                EvidenceSource(
                    source_id="tier1_summary",
                    label="Visible structural similarity summary",
                    claim_types=["summary", "risk_signal"],
                    payload={
                        "compound_name": visible_state.get("compound_name"),
                        "query_smiles": visible_state.get("query_smiles"),
                        "risk_signal": visible_state.get("risk_signal"),
                        "neighbors_with_pathways": visible_state.get("neighbors_with_pathways"),
                        "avg_similarity": visible_state.get("avg_similarity"),
                        "tier2_pattern_count": visible_state.get("tier2_pattern_count"),
                        "tier2_rule_total": visible_state.get("tier2_rule_total"),
                        "coverage_resolution_rate": visible_state.get("coverage_resolution_rate"),
                    },
                ),
                EvidenceSource(
                    source_id="tier1_endpoints",
                    label="Visible endpoint patterns",
                    claim_types=["endpoints"],
                    payload=visible_state.get("top_endpoints", []),
                ),
                EvidenceSource(
                    source_id="tier1_neighbors",
                    label="Visible similar compounds",
                    claim_types=["neighbors"],
                    payload=visible_state.get("similar_compounds", []),
                ),
            ],
        )
    return EvidenceBundle()


def build_authoritative_surface(
    page_id: str,
    hint: AnswerSurfaceHint,
) -> tuple[AuthoritativeAnswerSurface, list[SurfaceDiscrepancy]]:
    policy = get_page_policy(page_id)
    if policy is None:
        raise ValueError(f"Unsupported page_id '{page_id}'")

    discrepancies: list[SurfaceDiscrepancy] = []
    if hint.page_id and hint.page_id != page_id:
        discrepancies.append(
            SurfaceDiscrepancy(
                field="page_id",
                reason="Hint page_id did not match request page_id",
                hint_value=hint.page_id,
                authoritative_value=page_id,
            ),
        )

    if sorted(hint.supported_question_types) != sorted(policy["supported_question_types"]):
        discrepancies.append(
            SurfaceDiscrepancy(
                field="supported_question_types",
                reason="Frontend hint drifted from backend page policy",
                hint_value=hint.supported_question_types,
                authoritative_value=policy["supported_question_types"],
            ),
        )

    if sorted(hint.handoff_targets) != sorted(policy["handoff_targets"]):
        discrepancies.append(
            SurfaceDiscrepancy(
                field="handoff_targets",
                reason="Frontend handoff targets drifted from backend page policy",
                hint_value=hint.handoff_targets,
                authoritative_value=policy["handoff_targets"],
            ),
        )

    raw_visible = hint.visible_state if isinstance(hint.visible_state, dict) else {}
    for key in raw_visible.keys():
        if key not in policy["allowed_visible_state_keys"]:
            discrepancies.append(
                SurfaceDiscrepancy(
                    field=f"visible_state.{key}",
                    reason="Frontend sent a visible_state key not recognized by backend policy",
                    hint_value=raw_visible.get(key),
                    authoritative_value=None,
                ),
            )

    visible_state = _sanitize_visible_state(page_id, raw_visible)
    evidence_bundle = _build_evidence_bundle(page_id, visible_state)
    surface = AuthoritativeAnswerSurface(
        page_id=page_id,
        page_label=str(hint.page_label or policy["page_label"]),
        locale=str(hint.locale or "en"),
        module_version=str(hint.module_version or "1.0"),
        supported_question_types=list(policy["supported_question_types"]),
        forbidden_question_types=list(policy["forbidden_question_types"]),
        clarification_fields=[ClarificationField(**row) for row in policy["clarification_fields"]],
        allowed_actions=list(policy["allowed_actions"]),
        handoff_targets=list(policy["handoff_targets"]),
        visible_state=visible_state,
        evidence_bundle=evidence_bundle,
        starter_questions=list(hint.starter_questions or policy["starter_questions"]),
    )

    if discrepancies:
        LOGGER.info(
            "AegisChat surface drift detected for %s: %s",
            page_id,
            [d.model_dump() for d in discrepancies],
        )
    return surface, discrepancies
