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


def _sanitize_visible_state(page_id: str, raw: dict[str, Any]) -> dict[str, Any]:
    if page_id == "fate-explorer":
        return _sanitize_fate_visible_state(raw)
    if page_id == "regulatory":
        return _sanitize_regulatory_visible_state(raw)
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
        page_label=policy["page_label"],
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
